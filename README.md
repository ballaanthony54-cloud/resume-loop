# resume-loop

A twice-weekly engine that sweeps fresh loan-execution and private-credit analyst
roles, tiers them, dedupes against what has already been seen, tells Desiree which
resume variant to attach, surfaces warm-intro contacts for top targets, scans Gmail
for responses, and delivers a report automatically.

State lives in this private repo so a scheduled cloud agent can read and write it
on a fixed cadence, independent of any single machine being switched on.

## Owner

- **Candidate:** Desiree Oritsemeyiwa Awani, London, United Kingdom (UK citizen, no
  sponsorship needed)
- **Contact:** desiree.awani@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/desireeawani/

## Weekly rhythm

- **Monday 19:00 and Thursday 19:00 (London local)** the cloud agent runs
  `agent-prompt.md`, writes a fresh pulse, and pushes it here.
- Shortly after each run, the local Windows Task Scheduler job pulls the repo and
  opens `latest-pulse.md` with a desktop notification.
- Before actually applying, run `scripts/local_sweep.py` from the Windows machine.
  That is the **source of truth for live links**: the cloud sandbox often cannot
  reach the ATS JSON APIs (they block cloud egress), so its links come from web
  search and are lower confidence. The local sweep hits the APIs directly, where
  they return 200, and prints verified direct apply links.

## What is in here

| Path | Purpose |
|------|---------|
| `README.md` | This overview |
| `applications.md` | The application tracker (source of truth for what was applied to) |
| `seen-roles.json` | Dedup memory of every role ever surfaced |
| `priority-companies.md` | Tier-A auto-boost list and personal vetoes |
| `target-roles.md` | Title, seniority, and location keep/drop rules |
| `agent-prompt.md` | The operational spec the scheduled agent follows exactly |
| `latest-pulse.md` | Most recent report (overwritten every run) |
| `archive/` | One dated pulse per run, kept forever |
| `resumes/` | HTML sources and generated PDFs, one per variant |
| `scripts/local_sweep.py` | Local verified ATS sweep (run before applying) |
| `scripts/pull-pulse.ps1` | Windows delivery: pull repo, open pulse, notify |
| `scripts/requirements.txt` | Python deps for the local sweep |

## Resume variants

Same factual body, different summary, skill emphasis, and bullet order per cluster.
All five map to the five target titles, all searched inside the Tier-A companies.

| Variant file | Use for |
|--------------|---------|
| `resumes/private-credit.pdf` | Private Credit Analyst / Associate roles |
| `resumes/leveraged-finance.pdf` | Leveraged Finance / Loan Execution roles |
| `resumes/transaction-management.pdf` | Transaction / trade-settlement management roles |
| `resumes/credit-risk.pdf` | Credit Risk Strategy roles |
| `resumes/asset-management-ops.pdf` | Asset Management Operations roles |

## Ground rules baked into the system

- Never invents people, dates, salaries, or job details. Unverifiable items are
  labelled, not asserted.
- API-sourced links are trusted; web-search and aggregator links are validated or
  flagged before they reach the report.
- VP-level roles are excluded. So are sales/BD, compliance/audit, pure IT/dev, and
  unrelated back-office roles.
- The tracker (`applications.md`) is only ever edited by Desiree. The agent proposes
  updates; it never auto-writes them.
