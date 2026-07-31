# Resume Loop pulse - 2026-07-31 (UTC) - RETRACTION + policy update

## The previous enriched pulse has been withdrawn

The roles shown earlier (Citi loan-documentation, RBC BlueBay leveraged finance, and
the eFinancialCareers Tier-B list) were **not confirmed live** and you found them
dead. They should never have been listed as targets with only a "click to confirm"
flag. That is fixed at the system level, not just apologised for.

## Two hard gates are now enforced everywhere

**1. Age gate (max 14 days).** A role is dropped unless it has a *confirmable*
posting/update date within the last 14 days. Undated roles are dropped, not kept.
Previously undated roles were kept and flagged; now they are removed.

**2. Liveness gate (must be currently live).** Every role in a report must be
confirmed reachable before it is shown:

- ATS-API roles (`local_sweep.py`): each apply link is re-checked for HTTP 200 at
  sweep time; dead links (404/410) are dropped. See the new "Dropped (dead link)"
  line in the dedup stats.
- Web-sourced roles (on-demand enriched pulse): JavaScript career sites (Citi,
  BlueBay, Workday, banks) are now **rendered in a real browser and confirmed the
  posting still displays** before listing. If it cannot be rendered and confirmed,
  it is dropped. No more "click to confirm" entries. Aggregator links
  (eFinancialCareers, Indeed) are only used if the same live req is confirmed on the
  company's own site.

Where enforced: `agent-prompt.md` (STEP 2.5, STEP 3, HARD RULES) and
`scripts/local_sweep.py` (`is_fresh` age gate + `is_live` liveness gate, both
unit-tested).

## To get a clean, verified list right now

Run the local sweep on your machine, where the ATS APIs respond and links can be
checked:

```powershell
C:\dev\venvs\resume-loop\Scripts\Activate.ps1
python C:\dev\resume-loop\scripts\local_sweep.py --write-pulse
```

Every role it prints has passed both gates: posted within 14 days and returning
HTTP 200 at run time. For the priority firms (JPM, Citi, KKR, BlueBay) that are not
on the ATS APIs, ask for an on-demand enriched pulse and each link will be
browser-verified live before it reaches you.
