# Pre-registration v3: the KPMP segmentation census, third pass (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Code: `../kidney/kpmp_census3.py` 3.0, which reuses `../kidney/kpmp_census2.py` 2.0 and `../kidney/kpmp_census.py` 1.0 unchanged. Offline tests: `../kidney/test_kpmp_census3.py` (plus the earlier two test files). All are committed with this note before the job runs. Pass 2 and its grades: `kpmp-census-results-v2-2026-10-27.md` (this folder).

## 1. What changes from pass 2

Exactly one thing changes in how the data are read. Each v1 workbook's sheet is the one whose name, after pass 1's normaliser (lower case, bracketed text dropped, spaces collapsed), is `features`. Pass 2 asked for the exact name `features` and read nothing. The job also records every raw sheet name it sees. Everything else is pass 2's procedure, unchanged: the same 361-package frame and seeded order, the same cache, the same 20 + 20 slide sample for the scanner pixel size, the same score release (10.12.2026), the same column matching, floors and statistics.

What we have seen before writing this note: pass 2's aggregates (its results note), including P7-P9 on v2 participants. No v1 feature value and no tail statistic (90th or 10th percentile) has been computed by any pass.

## 2. Graded checks and predictions

Graded only if at least 95% of the 361 packages are analysed.

**Carried over from pass 2 with identical rules** (pre-registration v2, section 3): S1, U1, U2, U3, P2, P3, P4, P5. Predictions unchanged: all pass. S1 already passed in pass 2. It is re-graded here only because the same sample is drawn again, and its pass-2 grade stands whatever happens.

**P7-P9 are not re-graded.** Their grade of record is pass 2's: fail, fail, fail. The pooled versions (v1 + v2) are reported here, not graded, because the v2 half of the pool has already been seen.

**V7-V9: pass 2's P7-P9 rules on participants whose packages are all v1** (none of their values has been read). These are the same feature, score, direction and thresholds: one-sided permutation p < 0.05 in the stated direction, 10,000 shuffles, at least 30 participants, at least 20 tubules each.
- V7 luminal fraction vs "Cortex: Abnormal Tubular Luminal Morphology: Abnormal Luminal Morphology: Percent", rho > 0.
- V8 average TBM thickness vs "Cortex: Tubular Atrophy: Common Type: Percent", rho > 0.
- V9 average cell thickness vs "Cortex: Tubular Injury Other: Percent", rho < 0.
- Prediction: **fail, fail, fail.** The same rules failed on v2. A pass would mean the v1 pipeline's features behave differently from v2's, which would itself matter to anyone pooling the two.

**T7-T9: tails instead of medians, graded on v2-only participants** (no tail has been computed). A participant's 90th percentile (T7, T8) or 10th percentile (T9) of the per-tubule values, by linear interpolation, against the same score, direction and thresholds as above. Within one version a pixel-to-micron factor does not change ranks, so raw values are used.
- T7 90th percentile of luminal fraction vs abnormal luminal morphology %, rho > 0. Prediction: pass (low confidence). Dilated or cystic tubules would sit in the upper tail.
- T8 90th percentile of TBM thickness vs tubular atrophy (common type) %, rho > 0. Prediction: **pass.** Atrophic tubules have thick basement membranes but are a minority of tubules, which a median hides.
- T9 10th percentile of cell thickness vs tubular injury other %, rho < 0. Prediction: fail. Pass 2's median rule came out with the opposite sign (rho +0.157).
- The same tail statistics within v1-only participants are reported, not graded.

Six agreement tests are graded (V7-V9, T7-T9), each at 0.05 one-sided with no correction. The results note will also give Holm-adjusted p-values over the six, worked out from the job's p-values.

**Reported, not predicted:** every raw sheet name by version; every v1 header by compartment, including the tubule workbooks, which no pass has read yet; D1 (TBM vs cortical interstitial fibrosis %), pooled and by version; participant counts by version.

## 3. What each outcome changes

- **U1-U3 and P2-P5 pass:** the README's units hold. Entrants convert v2 with one scanner pixel size (about 0.2527 microns), and the results note gives the size of the error from pooling without converting. This feeds question 2's conversion rule (`kpmp-q2-prereg-v1-2026-10-27.md`).
- **U1 fails with a ratio near 1:** v1 `Area` is in pixels, so the README's v1 unit claim fails for areas. Question 2 then grades its glomerular-area controls on its version-stratified statistic, as its pre-registration states.
- **V7-V9 and T7-T9 all fail:** a participant-level summary of KPMP's released tubule vectors does not track the consensus pathologists' tubular percentages, in either layout or in the tails. That will be published as a negative result, and the Kidney AI entry will not rest a discovery on tubule vectors.
- **T8 passes while P8 failed:** the signal sits in the tail, not the median. That will be reported as a finding about how to summarise these vectors, with the caveat that it is one of six tests.
- Every outcome will be published. Only aggregate counts and statistics leave the job, never a KPMP file, image or per-participant value.

## 4. Limits

- The fix is ours, and so were the two reader errors before it. A third error is possible. To catch one, the job records raw sheet names and every header.
- Tail percentiles of a few dozen tubules are noisy, and the 20-tubule floor is low for a 90th percentile.
- v1 slides include a second scanner pixel size (4 of 20 sampled at about 0.263 microns), which a single conversion factor ignores.
- One model family wrote the code and will grade it; no human has reviewed it.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- `kpmp-census-prereg-v2-2026-10-27.md`, `kpmp-census-results-v2-2026-10-27.md`, `kpmp-census-results-v1-2026-10-27.md` (this folder)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
