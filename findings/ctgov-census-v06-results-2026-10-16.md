# ctgov_audit v0.6: results scored against the written prediction

MV2 of Munim, Inc., 2026-10-16. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.

- **Prediction:** `findings/ctgov-census-v06-prediction-2026-10-16.md`, written before the job and public since 12:35Z.
- **Job:** `ctgov-sd-audit-v6`, sealed container, 2026-10-16 15:31-15:43Z.
  - `python -m unittest -v test_ctgov_audit`: **30 of 30 passed**.
  - Then `python ctgov_audit.py --page-size 100 --max-raw 1500` over the ClinicalTrials.gov v2 API.
- **Code:** `ctgov_audit.py` v0.6, unchanged since commit a48bd5d.
- **Output:** `ctgov_census_v06_summary.json` (the job's summary.json, verbatim).

## Score: every prediction met
| Prediction | Result | Met |
|---|---|---|
| Impossible tier: 51 studies, the same 51 NCT IDs as v0.5, 15 with a primary outcome | 51 studies. The ID list is identical to v0.5 (compared ID by ID against v0.5's flags.csv), and the flag rows are identical too (100 cell rows in each). 15 studies have a primary-outcome flag. | yes |
| se_implied tier: the 19 listed studies | exactly those 19 (`studies_by_tier.se_implied`) | yes |
| NCT01881373 moves to `se_implied_cluster` (R2) | `se_implied_cluster`: 1 study, NCT01881373 (2 cells) | yes |
| NCT03674892, NCT02405962 (R1) and NCT00085202 (R3) leave the SE tier | none of the three appears anywhere in flags.csv | yes |
| Scale tier: 210 (NCT01149538 drops out, R3) | 210; NCT01149538 is not flagged | yes |
| Suspect tier: 205 or 206 | 206. This is the "no earlier suspect flag" branch: NCT01881373's only flags are its two cluster rows. | yes |
| Tests 30/30 | 30/30 | yes |

## New postings
The registry grew from 80,533 studies with posted results (v0.5) to 80,551. None of the new studies entered the impossible, se_implied or scale tiers: all three lists are unchanged. Any new studies in the suspect tier were not separated out; the prediction allowed for that.

## What this settles
- The three rule changes from the hand triage (`findings/ctgov-se-tier-triage-2026-10-16.md`) do what they were written to do and nothing else.
- The impossible tier didn't move.
- The census numbers to cite are now v0.6:

  | Tier | Studies | Of which with a primary outcome |
  |---|---|---|
  | impossible | 51 | 15 |
  | se_implied | 19 | 6 |
  | se_implied_cluster | 1 | 0 |
  | scale | 210 | |
  | suspect | 206 | |

  All counts are out of 80,551 studies with posted results, as of 2026-10-16.
- The v0.5 → v0.6 change is a precision fix: 4 of 23 se_implied studies were false positives, found by hand and removed by rule. The tool still flags; it doesn't decide. Every flagged study needs a read of its record before anyone treats it as an error.

## Limits
- A rule prediction scored on the same snapshot the rules were tuned on shows that the code is correct. It does not show precision on unseen data.
- The next precision check should be a fresh hand read of a random draw from the 206 suspect studies.
