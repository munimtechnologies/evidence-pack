# ctgov_audit v0.6: prediction written before the run

MV2 of Munim, Inc., 2026-10-16 (~13:00Z). Research and drafting by AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.

Written before job ctgov-sd-audit-v6 runs. It is not to be edited after the results arrive.

## What changed from v0.5
These are the three rule changes from the hand triage of the 23 v0.5 se_implied studies (`findings/ctgov-se-tier-triage-2026-10-16.md`):

1. **R1.** The SE check skips any bound that the measure's own means do not fit. A mean that is above the ceiling, or below the floor by more than the width, does not fit.
2. **R2.** A study whose posted analyses mention clusters or clustering has its SE-tier flags moved to a new check, `se_implied_cluster`, in the "suspect" tier.
3. **R3.** "average range" in an outcome description stops the text from being read as a score range.

## Predictions for the same registry snapshot (80,533 studies at v0.5)
- **Impossible tier: 51 studies**, the same 51 NCT IDs as v0.5, 15 of them with a primary outcome. R1-R3 do not touch this tier.
- **se_implied tier: 19 studies.** These are the 23 from v0.5 minus four:
  - NCT01881373, moved by R2;
  - NCT03674892 and NCT02405962, removed by R1;
  - NCT00085202, removed by R3.

  The other 19 stay:
  - NCT04723719, NCT01198691, NCT02155608, NCT01367860, NCT02629991;
  - NCT03985098, NCT04335136, NCT05618912, NCT02037126, NCT03953612;
  - NCT03371732, NCT01942733, NCT02163434, NCT04059185, NCT02874144;
  - NCT05498870, NCT00528996, NCT06019299, NCT03841357.
- **se_implied_cluster: 1 study** (NCT01881373).
- **Scale tier: 210 studies** (211 minus NCT01149538, whose "Average Range 85-115" was read as a scale).
- **Suspect tier: 205 or 206 studies.** It is 206 if NCT01881373 had no suspect flag before.
- **Tests: 30 of 30 pass.**

## How it is scored
- Results posted after v0.5 can add studies. Any flagged study not in the v0.5 lists is counted separately, as "new postings", and is not a miss.
- A study from the 19 that is missing, or one of the four that remains, is a miss. Each miss gets a reason in the results file.
- `summary.json` now lists the studies in each non-suspect tier (`studies_by_tier`), so the comparison can be made by list, not by eye.
