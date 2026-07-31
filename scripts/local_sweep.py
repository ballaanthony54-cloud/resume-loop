#!/usr/bin/env python3
"""
local_sweep.py -- the reliable, verified ATS sweep.

Runs the SAME ATS-API sweep the cloud agent runs, but from Desiree's Windows
machine, where the ATS JSON APIs return 200 (the cloud sandbox usually gets 403).
This is the SOURCE OF TRUTH for live apply links.

What it does:
  1. Probes every candidate ATS slug and keeps only the boards that return 200.
  2. Pulls postings, filters to target titles + London-eligible + last 14 days,
     drops excluded role-types and VP+ seniority.
  3. Dedupes against ../seen-roles.json (does not silently mutate it unless you
     pass --update-seen).
  4. Prints verified direct apply links, grouped by tier.

Usage (from the repo root or the scripts/ folder), in PowerShell:
    python .\scripts\local_sweep.py                 # sweep + print
    python .\scripts\local_sweep.py --probe-only    # just show which boards are live
    python .\scripts\local_sweep.py --update-seen   # also append new roles to seen-roles.json
    python .\scripts\local_sweep.py --days 21       # widen freshness window

Portability notes (this file and the cloud agent share the repo):
  - Uses pathlib for all paths, never hardcoded "/".
  - Opens files with encoding="utf-8", newline="\n".
  - Writes seen-roles.json sorted, LF, trailing newline (matches agent STEP 9).
  - Uses requests, never shelled-out curl.
"""

from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install -r scripts/requirements.txt")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
REPO = Path(__file__).resolve().parent.parent
SEEN = REPO / "seen-roles.json"
UA = {"User-Agent": "Mozilla/5.0 (resume-loop local sweep)"}
TIMEOUT = 20

# Candidate slugs per ATS. Confirmed-live are just candidates that pass the probe.
GREENHOUSE_SLUGS = [
    "point72", "p72pi", "exoduspoint", "xpcampus", "balyasny", "citadel",
    "millennium", "marshallwace", "mangroup", "brevanhoward", "cqs", "sona",
    "chenavari", "cheyne", "hayfin", "schonfeld", "qube", "verition", "squarepoint",
]
LEVER_SLUGS = [
    "citadel", "millennium", "marshallwace", "brevanhoward", "cqs", "sona", "hayfin",
]
ASHBY_SLUGS = ["citadel", "point72", "kkr", "schonfeld", "balyasny"]

# Tier-A companies (lowercased contains-match on the org/company name).
TIER_A = [
    "jp morgan", "jpmorgan", "citi", "kkr", "bluebay", "millennium", "citadel",
    "point72", "balyasny", "exoduspoint", "marshall wace", "man group",
    "brevan howard", "cqs", "sona", "chenavari", "cheyne", "hayfin",
]

# Title keep-keywords (any hit) and drop-keywords (any hit -> drop).
TITLE_KEEP = [
    "loan clos", "loan admin", "loan servic", "loan execution", "syndicated loan",
    "par loan", "private credit", "credit analyst", "credit associate",
    "credit risk", "transaction manage", "settlement", "trade support",
    "loan settlement", "agency", "leveraged finance", "asset management operation",
    "trading analyst",
]
TITLE_DROP_ROLETYPE = [
    "sales", "business development", "bd ", "origination", "compliance", "audit",
    "kyc", "aml", "regulatory report", "software", "engineer", "developer",
    "quant dev", "data engineer", "devops", "recruit", "human resources",
    " hr ", "procurement", "facilities", "marketing",
]
SENIORITY_DROP = [
    "vp", "vice president", "director", "managing director", " md", "executive director",
    " ed ", "head of", "lead ", "graduate", "intern", "internship", "placement",
    "apprentice", "trainee",
]

LONDON_OK = ["london", "united kingdom", "uk", "remote", "hybrid"]
LONDON_BAD_HINT = ["new york", "hong kong", "singapore", "dubai", "paris", "geneva",
                   "zurich", "frankfurt", "milan", "madrid", "dublin", "amsterdam",
                   "chicago", "boston", "miami", "houston", "tokyo", "mumbai"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def is_fresh(posted: dt.datetime | None, days: int) -> bool:
    if posted is None:
        return True  # keep undated rather than silently drop; flagged downstream
    return (now_utc() - posted).days <= days


def parse_iso(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        d = dt.datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def parse_epoch_ms(ms) -> dt.datetime | None:
    try:
        return dt.datetime.fromtimestamp(int(ms) / 1000, tz=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def title_ok(title: str) -> bool:
    t = f" {title.lower()} "
    if any(k in t for k in SENIORITY_DROP):
        return False
    if any(k in t for k in TITLE_DROP_ROLETYPE):
        return False
    return any(k in t for k in TITLE_KEEP)


def location_ok(loc: str) -> bool:
    l = loc.lower()
    if any(b in l for b in LONDON_BAD_HINT) and "london" not in l:
        return False
    return any(g in l for g in LONDON_OK)


def tier_of(company: str, loc: str) -> str:
    c = company.lower()
    if any(a in c for a in TIER_A) and "london" in loc.lower():
        return "A"
    return "B"


def key_for(company: str, title: str, link: str) -> str:
    return hashlib.sha256(f"{company}|{title}|{link}".encode("utf-8")).hexdigest()


# Map a role title to the best-fit resume variant (keyword-first, ordered).
VARIANT_RULES = [
    ("private-credit", ["private credit", "credit analyst", "credit associate"]),
    ("leveraged-finance", ["leveraged finance", "loan execution", "lev fin", "syndicated loan", "par loan"]),
    ("transaction-management", ["transaction manage", "trade support", "settlement", "loan clos", "trading analyst"]),
    ("credit-risk", ["credit risk", "risk strateg", "operational risk"]),
    ("asset-management-ops", ["asset management operation", "loan servic", "loan admin", "agency", "fund operation"]),
]


def guess_variant(title: str) -> str:
    t = title.lower()
    for variant, kws in VARIANT_RULES:
        if any(k in t for k in kws):
            return variant
    return "private-credit"  # sensible default for this candidate


def get_json(url: str):
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    if r.status_code == 200:
        return r.json()
    return None


# --------------------------------------------------------------------------- #
# Per-ATS fetchers -> normalised dicts
# --------------------------------------------------------------------------- #
def sweep_greenhouse(slug: str) -> list[dict]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if not data:
        return []
    out = []
    for j in data.get("jobs", []):
        out.append({
            "company": slug,
            "title": j.get("title", ""),
            "link": j.get("absolute_url", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "posted": parse_iso(j.get("first_published") or j.get("updated_at")),
            "ats": "greenhouse",
        })
    return out


def sweep_lever(slug: str) -> list[dict]:
    data = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if not data:
        return []
    out = []
    for j in data:
        cats = j.get("categories", {}) or {}
        loc = cats.get("location") or " ".join(cats.get("allLocations", []) or [])
        out.append({
            "company": slug,
            "title": j.get("text", ""),
            "link": j.get("hostedUrl", ""),
            "location": loc or "",
            "posted": parse_epoch_ms(j.get("createdAt")),
            "ats": "lever",
        })
    return out


def sweep_ashby(slug: str) -> list[dict]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not data:
        return []
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        secs = " ".join(j.get("secondaryLocations", []) or []) \
            if isinstance(j.get("secondaryLocations"), list) else ""
        out.append({
            "company": slug,
            "title": j.get("title", ""),
            "link": j.get("jobUrl", ""),
            "location": f"{j.get('location','')} {secs}".strip(),
            "posted": parse_iso(j.get("publishedAt")),
            "ats": "ashby",
        })
    return out


ATS = [
    ("greenhouse", GREENHOUSE_SLUGS, sweep_greenhouse,
     lambda s: f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs"),
    ("lever", LEVER_SLUGS, sweep_lever,
     lambda s: f"https://api.lever.co/v0/postings/{s}?mode=json"),
    ("ashby", ASHBY_SLUGS, sweep_ashby,
     lambda s: f"https://api.ashbyhq.com/posting-api/job-board/{s}"),
]


# --------------------------------------------------------------------------- #
# seen-roles.json IO (matches agent STEP 9 formatting)
# --------------------------------------------------------------------------- #
def load_seen() -> dict:
    if not SEEN.exists():
        return {"roles": {}}
    with SEEN.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_seen(seen: dict) -> None:
    seen["roles"] = dict(sorted(seen["roles"].items()))
    with SEEN.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def write_pulse(kept: list[dict], stats: dict, days: int) -> None:
    """Write a markdown pulse to latest-pulse.md and archive/YYYY-MM-DD-pulse.md."""
    today = f"{now_utc():%Y-%m-%d}"
    lines = [
        f"# Resume Loop pulse - {today} (UTC)",
        "",
        "_Automated Windows sweep (verified ATS links). Warm-intro drafts and the "
        "Gmail response scan are not part of this automated run; trigger an on-demand "
        "pulse in Cowork for those._",
        "",
        f"**{len(kept)} fresh role(s)** matching your titles, London-eligible, posted "
        f"in the last {days} days, after dedup.",
        "",
    ]
    for tier, label in (("A", "Tier A - priority companies"),
                        ("B", "Tier B - strong match")):
        rows = [k for k in kept if k["tier"] == tier]
        if not rows:
            continue
        lines.append(f"## {label} ({len(rows)})")
        lines.append("")
        for j in rows:
            d = f"{j['posted']:%Y-%m-%d}" if j["posted"] else "date n/a"
            lines.append(f"### {j['title']}")
            lines.append(f"- **Company / board:** {j['company']} ({j['ats']})")
            lines.append(f"- **Location:** {j['location']}  |  **Posted:** {d}")
            lines.append(f"- **Resume to attach:** `resumes/{j['variant']}.pdf`")
            lines.append(f"- **Apply:** {j['link']}")
            lines.append("")
    if not kept:
        lines.append("_No new roles this run. Nothing to apply to today._")
        lines.append("")
    lines += [
        "---",
        "## Dedup stats",
        "",
        f"- Boards scanned: {stats['boards']}",
        f"- Postings seen: {stats['scanned']}",
        f"- Dropped (title/role-type/seniority): {stats['dropped_title']}",
        f"- Dropped (location): {stats['dropped_loc']}",
        f"- Dropped (stale >{days}d): {stats['dropped_stale']}",
        f"- Dropped (already seen): {stats['dropped_dupe']}",
        f"- Final kept: {len(kept)}",
        "",
    ]
    text = "\n".join(lines)
    (REPO / "latest-pulse.md").write_text(text, encoding="utf-8", newline="\n")
    archive = REPO / "archive"
    archive.mkdir(exist_ok=True)
    (archive / f"{today}-pulse.md").write_text(text, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Local verified ATS sweep for resume-loop.")
    ap.add_argument("--days", type=int, default=14, help="freshness window in days")
    ap.add_argument("--probe-only", action="store_true", help="only show live boards")
    ap.add_argument("--update-seen", action="store_true",
                    help="append new roles to seen-roles.json")
    ap.add_argument("--write-pulse", action="store_true",
                    help="write latest-pulse.md and archive/YYYY-MM-DD-pulse.md")
    args = ap.parse_args()

    print(f"Resume Loop local sweep  |  {now_utc():%Y-%m-%d %H:%M UTC}\n")

    # 1. Probe boards.
    live = {}
    for name, slugs, fetch, url_for in ATS:
        live[name] = []
        for slug in slugs:
            try:
                r = requests.get(url_for(slug), headers=UA, timeout=TIMEOUT)
                if r.status_code == 200:
                    live[name].append(slug)
                    print(f"  [live]  {name:10} {slug}")
                else:
                    print(f"  [{r.status_code:>3}]  {name:10} {slug}")
            except requests.RequestException as e:
                print(f"  [ERR]  {name:10} {slug}  ({type(e).__name__})")
    print()

    if args.probe_only:
        return

    # 2. Sweep live boards.
    raw = []
    for name, slugs, fetch, _ in ATS:
        for slug in live[name]:
            try:
                raw.extend(fetch(slug))
            except requests.RequestException as e:
                print(f"  sweep failed: {name}/{slug} ({type(e).__name__})")

    scanned = len(raw)

    # 3. Filter.
    seen = load_seen()
    seen_keys = set(seen["roles"].keys())
    kept, dropped_title, dropped_loc, dropped_stale, dropped_dupe = [], 0, 0, 0, 0

    for j in raw:
        if not j["link"] or not j["title"]:
            continue
        if not title_ok(j["title"]):
            dropped_title += 1
            continue
        if not location_ok(j["location"]):
            dropped_loc += 1
            continue
        if not is_fresh(j["posted"], args.days):
            dropped_stale += 1
            continue
        k = key_for(j["company"], j["title"], j["link"])
        if k in seen_keys:
            dropped_dupe += 1
            continue
        j["key"] = k
        j["tier"] = tier_of(j["company"], j["location"])
        j["variant"] = guess_variant(j["title"])
        kept.append(j)

    kept.sort(key=lambda x: (x["tier"], x["company"]))

    # 4. Print.
    print("=" * 70)
    print(f"VERIFIED LIVE ROLES ({len(kept)})")
    print("=" * 70)
    for tier in ("A", "B"):
        rows = [k for k in kept if k["tier"] == tier]
        if not rows:
            continue
        print(f"\n----- Tier {tier} -----")
        for j in rows:
            d = f"{j['posted']:%Y-%m-%d}" if j["posted"] else "date n/a"
            print(f"  {j['title']}  [{j['company']} / {j['ats']}]")
            print(f"    {j['location']}  |  posted {d}")
            print(f"    {j['link']}")

    print("\n" + "-" * 70)
    print("DEDUP STATS")
    print(f"  boards scanned : {sum(len(v) for v in live.values())}")
    print(f"  postings seen  : {scanned}")
    print(f"  dropped title  : {dropped_title}")
    print(f"  dropped loc    : {dropped_loc}")
    print(f"  dropped stale  : {dropped_stale}")
    print(f"  dropped dupe   : {dropped_dupe}")
    print(f"  final kept     : {len(kept)}")

    stats = {
        "boards": sum(len(v) for v in live.values()), "scanned": scanned,
        "dropped_title": dropped_title, "dropped_loc": dropped_loc,
        "dropped_stale": dropped_stale, "dropped_dupe": dropped_dupe,
    }

    # 5. Optionally write the pulse markdown.
    if args.write_pulse:
        write_pulse(kept, stats, args.days)
        print(f"\n  pulse written to latest-pulse.md and archive/{now_utc():%Y-%m-%d}-pulse.md")

    # 6. Optionally persist.
    if args.update_seen and kept:
        for j in kept:
            seen["roles"][j["key"]] = {
                "company": j["company"], "title": j["title"], "link": j["link"],
                "first_seen": f"{now_utc():%Y-%m-%d}", "variant": "", "tier": j["tier"],
            }
        write_seen(seen)
        print(f"\n  seen-roles.json updated (+{len(kept)} roles)")
    elif kept:
        print("\n  (run with --update-seen to record these in seen-roles.json)")


if __name__ == "__main__":
    main()
