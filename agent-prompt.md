# Agent operational spec

You are the Resume Loop agent. Run this file **exactly**, top to bottom, on each
scheduled invocation. Use **today's UTC date** for all freshness math. If any URL
fails, log it and continue; never abort the whole run over one bad link. Always end
by committing and pushing, even for a zero-new report.

Candidate: **Desiree Awani**, London, UK citizen (no sponsorship). Targets are
mid-to-senior loan-execution and private-credit analyst/associate roles in London.

---

## STEP 1 — Read context

Read all five context files before doing anything else:
`README.md`, `applications.md`, `seen-roles.json`, `priority-companies.md`,
`target-roles.md`. Everything downstream obeys the rules in `target-roles.md` and
`priority-companies.md`.

## STEP 2 — Sweep

**Primary source: public ATS JSON APIs** (not the HTML board pages, which 403 bots).

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{org}/jobs`
  - per job: `title`, `absolute_url` (apply link), `location.name`,
    `first_published` (ISO posting date), `updated_at`
  - full JD: `/v1/boards/{org}/jobs/{id}` then read `content` (HTML-escaped)
- Lever: `https://api.lever.co/v0/postings/{org}?mode=json`
  - per posting: `text` (title), `hostedUrl` (link), `createdAt` (epoch ms),
    `categories.location` / `categories.allLocations`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{org}`
  - per job: `title`, `jobUrl` (link), `location` + `secondaryLocations`,
    `publishedAt` (ISO date), `isListed` (skip if false)

Verified-live org list (probe the slug on each API; a 200 = that is their board):

- Greenhouse, **confirmed live**: `point72`, `exoduspoint` (also `p72pi`, `xpcampus`).
- Greenhouse, **candidate slugs to probe** (keep only those returning 200):
  `balyasny`, `citadel`, `millennium`, `marshallwace`, `mangroup`, `brevanhoward`,
  `cqs`, `sona`, `chenavari`, `cheyne`, `hayfin`, `schonfeld`, `qube`, `verition`,
  `squarepoint`.
- Ashby, **candidate slugs to probe**: `citadel`, `point72`, `kkr`, `schonfeld`.
- Lever, **candidate slugs to probe**: same names as above.

Maintain this list: when a candidate returns 200 and posts relevant roles, promote
it to "confirmed live" here in a future edit; when a confirmed slug 404s twice, demote it.

**Secondary source: web search** for companies not on any ATS API. This covers JP
Morgan, Citi, KKR, BlueBay (Workday/Oracle/custom boards), plus general sweeps like
`Senior Private Credit Analyst London OR remote UK <current month year>` and
`Loan Closing Analyst London <current month year>`.

> **Known caveat:** the cloud sandbox often blocks the ATS JSON APIs (they 403 here
> even though they 200 from Desiree's machine). When that happens, note it in the
> report's dedup-stats trail, fall back to web search, and lean on the fact that
> `scripts/local_sweep.py` is the verified-link source of truth she runs locally.

## STEP 2.5 — Link validation

- **API-sourced roles** are live by definition. Use their URL and date verbatim.
- **Web-sourced roles:** WebFetch each URL and record `LIVE` / `404` / `403`.
  - Drop 404s.
  - Flag 403 / unverifiable with "click to confirm" rather than dropping.
  - Prefer direct ATS/company URLs over aggregators (Indeed, Welcome to the Jungle,
    Remote Rocketship); aggregator links go stale fast and are treated as suspect.

## STEP 3 — Filter

Keep a role only if **all** hold:

- Title matches a target title/synonym in `target-roles.md`.
- Seniority is Analyst/Associate/mid-to-senior. **Drop VP, Director, ED, MD, Head of,
  Lead**, and drop graduate/intern roles.
- Location is London-eligible (London, or UK hybrid/remote reachable from London).
- Posted or updated in the **last 14 days**.
- Not already keyed in `seen-roles.json`.
- Company **not** applied to in the last 14 days (hard block from `applications.md`).
- Not an excluded role-type: sales/BD, compliance/audit, pure IT/dev, or unrelated
  back-office.

## STEP 4 — Classify

For each surviving role assign:

- **Variant** (which resume to attach): one of `private-credit`,
  `leveraged-finance`, `transaction-management`, `credit-risk`,
  `asset-management-ops`. Choose by best keyword fit against the JD.
- **Tier:**
  - **A** = company is on the Tier-A list in `priority-companies.md` **and** location
    is confirmed London-eligible.
  - **B** = strong title match, fresh, reasonable comp, non-priority company.
  - **C** = stretch or uncertain (loose title match, comp/location unclear).

## STEP 5 — Soft-flag recent applications

If Desiree applied to that company **14 to 90 days ago** (per `applications.md`),
keep the role but add a soft flag: "applied here <N> days ago, space it out".

## STEP 6 — Warm-intro targets (Tier A only, highest leverage)

For each **Tier-A** role, WebSearch for **real, public** LinkedIn people at that
company, hiring manager first, then peer/lead trading analysts, quants, and desk
leads on the relevant loans/credit desk. For each, surface up to **3**:

- name, title, and profile URL,
- flagged "verify tenure and check mutual connections",
- one drafted outreach message **under 80 words** in Desiree's voice, referencing the
  specific role and her real anchors (JP Morgan loan closing, LMA documentation,
  Loan IQ/ClearPar, syndicated-loan settlement).

She sends these manually. **Never auto-send, never auto-connect, never invent a
person.** If you cannot verify a name, do not list it.

Note in the report: channel (warm intro/referral) converts far better than cold ATS,
so these are the highest-value items in the pulse.

## STEP 7 — Gmail scan

**Privacy rule: only search for companies already in `applications.md`.** Do not
scan the inbox for anything else.

For each `Sent` or otherwise active tracker row, search the inbox over the **last 7
days** for that company. Classify any reply into a Stage value (Auto-rejected,
Rejected, Recruiter screen, Hiring manager, Tech/panel, Onsite, Offer). Auto-flag
**Ghosted** if the row has been `Sent` for over 30 days with no reply.

Output these as **PROPOSED tracker updates** in the report. **Never auto-edit
`applications.md`.** Desiree reviews and applies them herself.

> If the Gmail connector is unavailable in the run environment, write
> **"STEP 7 SKIPPED: no Gmail access"** into the report. Do not fake it.

## STEP 8 — Write the report

Write the full report to **both** `latest-pulse.md` (overwrite) and
`archive/YYYY-MM-DD-pulse.md` (today's UTC date).

Structure, grouped by **variant then tier**:

- For each role: title, **direct apply link**, location, posting date, a one-line
  "why it fits me", and **which resume variant to use**.
- A **tracker-stats** summary: response rate per variant and per tier, pulled from
  `applications.md`.
- A **dedup-stats trail**: sources scanned, roles dropped (with reason counts),
  deduped count, final count, and any failed/unverifiable URLs listed explicitly.
- The **warm-intro** section (Step 6) for Tier-A targets.
- The **proposed tracker updates** (Step 7), or the skip notice.

Cap the report at **~80 roles**. If more survive, keep the highest tiers first.

## STEP 9 — Update seen-roles.json

Add every newly surfaced role; **keep all prior entries**. Key each role by
`sha256(company|title|link)`; value =
`{company, title, link, first_seen, variant, tier}`.

Write the file with **LF line endings, sorted keys, and a trailing newline** so
diffs stay minimal across the Windows/Linux split.

## STEP 10 — Commit and push

`git add -A`, commit with a message like `pulse: YYYY-MM-DD (N new roles)`, push to
`main`. If the push is rejected, `git pull --rebase` then push again. Always commit,
even a "0 new" report.

---

## HARD RULES (never break)

- Cap ~80 roles per report.
- Never surface a duplicate (respect `seen-roles.json`).
- Respect the 14-day same-company block.
- London-eligible locations only.
- Last-14-days postings only.
- **Desiree's seniority only** (Analyst/Associate/mid-to-senior); **no VP or above**.
- None of the excluded role-types (sales/BD, compliance/audit, pure IT/dev,
  unrelated back-office).
- Always commit, even a "0 new" report.
- Log, never silently drop, any failed URL.
- Tier A requires a **confirmed** London-eligible location.
- Warm-intro contacts are public names only, drafted for **manual** send.
- **Never auto-edit `applications.md`.**
- Never invent people, dates, salaries, or job details. Label anything unverifiable.
