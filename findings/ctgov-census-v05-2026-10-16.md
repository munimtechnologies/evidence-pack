# ClinicalTrials.gov impossible-statistics census, v0.5: the prediction held (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

This updates two files in this folder:
- `ctgov-impossible-statistics-census-2026-10-15.md` (the v0.2 census, 45 studies);
- `ctgov-census-v04-triage-2026-10-16.md` (the v0.4 rerun, the hand triage of 12 new flags, and the v0.5 fix).

The two earlier files are kept unchanged as the record of what was claimed and when. **Where they differ from this file, this file is current.**

## What ran

`ctgov_audit.py` v0.5 (in this repo, standard library only) ran in a sealed job (`ctgov-sd-audit-v5`, 2026-10-16 10:16-10:28 UTC). It read every ClinicalTrials.gov study with posted results: **80,533 studies** (the API's own total was 80,533), 670,671 outcome measures and 4,984,221 numeric cells. All 25 of its tests passed in the job.

## The prediction, and what happened

Before the job ran, the triage file stated: *"the impossible tier will hold about 51 studies, the 45 above plus the six remaining non-false-positive rows."*

**Result: 51 studies.** They are the same 51 named in advance:

| Check | Studies (v0.5) | Cells | Studies with it in a primary outcome |
|---|---|---|---|
| center_outside_interval | 16 | 30 | 7 |
| inverted_interval | 18 | 38 | 2 |
| negative_dispersion | 8 | 15 | 3 |
| sd_above_width | 3 | 3 | 2 |
| mean_outside_bounds | 2 | 7 | 0 |
| sd_above_max | 6 | 6 | 2 |
| **Any impossible check** | **51** (from the job's own union count) | | **15** (by hand) |

- The four v0.2 checks gave exactly the counts of the 10-15 census (16, 18, 8, 3) for the third time, on a registry that had gained 29 studies with results since then.
- `mean_outside_bounds` holds NCT02967367 (sleep stages posted as "a percentage of total sleep time", with means of 163-243) and NCT02899962 ("proportion of days" posted as 70.2 and 60.8).
- `sd_above_max` holds six studies. NCT06380179 was already in the 45 and NCT02967367 is also under `mean_outside_bounds`. The other four are new: NCT05135676, NCT03808909, NCT03806491 and NCT03833245. NCT03806491 is over the bound by only 1%, and its record mentions multiple imputation. NCT03833245 is still **unresolved** (it may be a change score); it stays in until a human reads its paper.
- So 45 + 6 = 51 (NCT02967367, NCT02899962, NCT05135676, NCT03808909, NCT03806491, NCT03833245).

**All six false positives found by hand were removed as designed.** Four (NCT05785832, NCT02365064, NCT04623086, NCT03477838) moved to the new *suspect* check `sd_above_max_if_level`, because each is a change score. The possession-ratio record (NCT06033521) and the rate record (NCT01687400) are no longer flagged at all.

**Headline, as of v0.5: 51 of 80,533 studies with posted results (about 1 in 1,600) post at least one summary statistic that is impossible as written; 15 of them have it in a primary outcome** (counted by hand: the 14 of 10-15 plus NCT03833245; NCT06380179 is primary under two checks, so the column above sums to 16). This replaces the 45-study headline of 10-15. One of the 51 (NCT03833245) is unresolved, and one (NCT03806491) is marginal.

## The SE tier after v0.5 (a screening result, not a finding)

`se_implies_sd_above_width` (a posted SE times sqrt(n) wider than the whole scale) now flags **115 cells in 23 studies, 6 of them with a primary outcome**. That is down from 26 studies in v0.4, because areas under a curve are now excluded.

This tier still needs hand triage before any count is quoted. The v0.5 list contains at least two kinds of probable false positive:
- **NCT00085202**: the "bounds" 85-115 look like a normal range quoted in the description, not the scale's limits. Several posted means lie outside them.
- **NCT03674892** and **NCT04335136**: the range appears to come from a single item, not from the total score.

One SE-tier record has been checked in full by hand and by a sealed job: NCT02037126 (`ctgov-se-tier-case-NCT02037126-2026-10-16.md`).

## Limits

- Each flag shows that a posted number, or its label, is wrong as written. It doesn't say which one, and it is no judgement on a trial's conclusions.
- The census is a floor. Wrong numbers that are still possible pass every check.
- The hand triage used the live API records, not the papers.
- The registry is live: sponsors can correct records, so a later run may differ by a study or two.

## Reproduce

- `python ctgov_audit.py --out-dir out --page-size 100` (about 12 minutes; public API only).
- `python -m unittest -v test_ctgov_audit` (25 tests, offline).
