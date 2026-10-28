# Pre-registration v1: is KPMP's zero-TBM share more than small or collapsed tubules? (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Written and published before the job that runs it (`kpmp-zs-v1`) is switched on. Code: `../kidney/kpmp_zs.py` 1.0 with offline tests `../kidney/test_kpmp_zs.py`.

## Why

`kpmp-tbm0-twins-results-v1-2026-10-28.md` found that a participant's share of tubule rows with `Average TBM Thickness` = 0 (`zero_share`) tracks the consensus tubular atrophy % (rho +0.38, n 222) and baseline eGFR (rho -0.36, n 247), in both release layouts. Zero rows are small (median size 0.15-0.23 of the others) and have near-closed lumens (median luminal fraction about 0.02 against 0.12-0.15). Three simpler explanations could produce the same correlations:
- **Size:** kidneys with atrophy have smaller tubules, and the pipeline may fail more often on small ones.
- **Collapse:** the share is just a count of collapsed tubules, which a luminal-fraction cut-off would find without any TBM column.
- **Age:** both atrophy and low eGFR rise with age.

This study holds each of these fixed in turn.

## What we have seen

Only the results above: version-wide medians of size, luminal fraction and cell thickness for zero and other rows, and the unadjusted Z7/Z8 statistics. We have not computed any participant's median size, small-tubule share or collapsed share, any partial correlation, or `zero_share` against age, fibrosis, diabetes or proteinuria.

## Data and method (fixed now)

- Data: the same cached KPMP files as `kpmp-tbm0-v2`: 361 listed segmentation packages (file-list export of 2026-10-18), the TIV score release of 10.12.2026 and the open clinical file of 2026-09-30. `kidney.kpmp_fill` 1.0 runs first; nothing new is downloaded if the cache is present. Rows are read by `kidney.kpmp_tbm0.tubules` 1.0, unchanged.
- Only tubules with a TBM number count. Packages with more than one participant are left out, as before.
- **Participant features** (each needs at least 20 of the rows it uses):
  - `zero_share`: rows with TBM <= 0 / rows with a TBM number. This is the same as `kpmp_tbm0`.
  - `size_med`: the median size, meaning box area in v2 and `Area (pixel^2)` in v1, of tubules with a size > 0.
  - `small_share`: the share of those tubules below the version-wide 25th percentile of size. The 25th percentile is the value at index floor(0.25 x (n - 1)) of the sorted sizes.
  - `collapsed_share`: the share of tubules with a luminal fraction whose luminal fraction is < 0.05.
  - `zero_share_cortex`: as `zero_share`, without v1 rows coded `In Medulla` = 1.
- **Age:** the clinical file's `Age (Years) (Binned)`, coded as the lower bound of each band (question 2's coding; bands that do not match "N-M Years" are left out).
- **Statistic:** rank partial correlation. Within each version (v1, v2; strata under 10 dropped), the ranks of `zero_share` and the ranks of the outcome are each regressed on the ranks of the covariate, and the residuals are correlated (Pearson). Strata are combined weighted by n, as in question 2. The p-value is one-sided in the predicted direction and comes from 10,000 shuffles of the outcome residuals within each stratum, with seed 20261029 + test number. Size cannot be compared across versions, so stratifying by version keeps the pixel definitions apart. Each test is graded alone; Holm-adjusted p over S1-S6 is reported beside them.
- **Gate:** at least 95% of listed packages read, and the score and clinical files load; otherwise every grade is "pending". **Floor:** at least 30 participants per test, otherwise "untestable".

## Predictions (graded exactly as written)

| | Outcome | Held fixed | Pass if | Prediction |
|---|---|---|---|---|
| S1 | Tubular atrophy % | `size_med` | partial rho > 0, p < 0.05 | pass |
| S2 | Baseline eGFR | `size_med` | partial rho < 0, p < 0.05 | pass |
| S3 | Tubular atrophy % | age band | partial rho > 0, p < 0.05 | pass |
| S4 | Baseline eGFR | age band | partial rho < 0, p < 0.05 | pass (less sure) |
| S5 | Tubular atrophy % | `collapsed_share` | partial rho > 0, p < 0.05 | fail (least sure) |
| S6 | Baseline eGFR | `collapsed_share` | partial rho < 0, p < 0.05 | fail (least sure) |

Why: Z3 showed the zero rows are small, but a participant's median size is driven by the 85-90% of tubules that are not zero rows, so we expect size alone not to absorb the signal. The age gradients in question 2 were real but modest, so we expect S3 to hold, and S4 less surely, because eGFR falls steeply with age. Zero rows have near-closed lumens, so we expect a collapsed-lumen share to carry most of the same information (S5, S6 fail). We would rather be wrong.

## What each outcome means (fixed now)

- **S1 and S2 pass:** the marker is not just "smaller tubules".
- **S1 or S2 fails:** the zero-TBM signal is largely a tubule-size signal. Size, which needs no TBM column, is the simpler marker to report.
- **S3 and S4 pass:** the marker is not just age.
- **S3 or S4 fails:** the zero-TBM share may be mainly an age marker in this cohort. Z7 and Z8 must then be read as age-confounded.
- **S5 and S6 fail:** zero rows are, in effect, collapsed tubules. The useful marker is "collapsed tubules", findable from the luminal fraction alone, and the zero TBM is one way the pipeline records them.
- **S5 or S6 passes:** zero-TBM rows carry information beyond lumen collapse. That is more consistent with a distinct morphology the pipeline fails on, and a visual check of zero rows becomes the priority.
- No outcome here can show that zero rows are atrophic tubules. Only looking at them can, and that would be AI visual triage, not a pathologist.

## Reported, not graded

All two-sided, version-stratified, with permutation p: unadjusted rho of `zero_share`, `zero_share_cortex`, `size_med`, `small_share` and `collapsed_share` against atrophy and against eGFR; `zero_share` against interstitial fibrosis %, diabetes history, proteinuria and albuminuria bands, age band, `small_share` and `collapsed_share`; and partial rho of `zero_share` given `small_share` for both outcomes. Also within-version partial rho for S1-S6, the unadjusted rho on the same participants, and the version-wide size cut-offs.

## Limits

- One covariate at a time. The six tests are not a full model, and partial correlation on ranks assumes roughly linear rank relations.
- The 0.05 luminal cut-off and the 25th-percentile size cut-off are fixed choices, not tuned.
- These are associations in a convenience sample of research biopsies. Scores and segmentations may come from different sections. Section twins (about 1.26x count inflation) affect shares little, because both sections come from the same core.
- One model family wrote, tests and will grade this. No human has reviewed it. Only aggregate statistics are published.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.
