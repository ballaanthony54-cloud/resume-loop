# Priority companies

## Tier-A auto-boost

A role is **Tier A** only when the company is on this list **and** its location is
confirmed as London-eligible. Everything else is B or C.

### Banks
- JP Morgan (current employer, still surfaced; not vetoed)
- Citi / Citigroup

### Private credit / asset managers
- KKR
- BlueBay Asset Management (RBC BlueBay)

### Hedge funds (London-relevant, credit specialists + multi-strats)
- Millennium
- Citadel
- Point72
- Balyasny
- ExodusPoint
- Marshall Wace
- Man Group
- Brevan Howard
- CQS
- Sona Asset Management
- Chenavari
- Cheyne Capital
- Hayfin

## Personal vetoes (never surface)

_None._ (Desiree opted to keep JP Morgan, her current employer, in the sweep.)

## Notes for the agent

- The five target titles are all searched **inside these Tier-A companies** as the
  priority pass, then broadened to the open market.
- Confirmed ATS boards (verified live): `point72`, `exoduspoint` on Greenhouse.
  Additional hedge-fund slugs are probed and verified by `scripts/local_sweep.py`.
- JP Morgan, Citi, KKR, and BlueBay run Workday/Oracle/custom systems with no clean
  public JSON API, so those come through the secondary web-search path and must be
  link-validated before appearing in a report.
