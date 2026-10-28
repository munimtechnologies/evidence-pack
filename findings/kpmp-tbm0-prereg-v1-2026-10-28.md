# Pre-registration v1: KPMP tubules without a TBM thickness (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

## Why

The object audit (`kpmp-objects-results-v1-2026-10-28.md`) found that 52,004 of the 518,756 tubule rows in KPMP's v2 pathomics files (10.0%) have an `Average TBM Thickness` of zero or less. The packages' README does not mention this. Every participant-level TBM median in our census passes and question 2 included those rows, and TBM thickness failed every clinical or pathology check we gave it: tubular atrophy % (census pass 2 P8, pass 3 V8 and T8) and baseline eGFR (question 2, C4). This study asks where the zero rows are, and whether TBM thickness, or the share of zero rows, tracks atrophy or eGFR once the two are separated.

Prior art (searched 2026-10-27/28): KPMP's segmentation and visualisation papers (e.g. Keller et al. 2025, arXiv 2510.19499) and HistoWAS (arXiv 2512.19954) do not report a share of tubules with no TBM measurement. We found no published description of it.

## What we have seen

- The v2 count above, and that the audit left these rows out of its rarity screen. Nothing else about them: not their slides, sizes, version-1 counterpart, or medulla status.
- Participant medians that **include** the zero rows, against atrophy % (pass 2 and 3) and eGFR (question 2). No median of positive values only, and no participant's share of zero rows, has been computed or joined to any score or clinical value.

## Data and code

- Data: the census data volume only (cached feature workbooks, the TIV descriptor-score release of 10.12.2026 and the open clinical file of 2026-09-30, all already cached). Nothing new is downloaded.
- Code: `../kidney/kpmp_tbm0.py` 1.0 with offline tests `../kidney/test_kpmp_tbm0.py`, published with this note before the job runs. It reuses `kpmp_census.py` 1.0, `kpmp_census2.py` 2.0, `kpmp_census3.py` 3.0 (readers, score table) and `kpmp_q2.py` 1.0 (clinical coding, version-stratified statistic, Holm), all unchanged.
- **Zero row:** a tubule row whose `Average TBM Thickness` parses to a number <= 0. Rows with no number are counted separately and left out.
- **Size:** box area (x2 - x1) x (y2 - y1) for v2; `Area (pixel^2)` for v1 (v1 files have no box columns in the feature sheet).
- **Medulla (v1 only):** `In Medulla` coded 1 for 1 / true / yes and 0 for 0 / false / no, case-insensitive; anything else uncoded. The raw values seen are reported.
- **Participant features:** `tbm_pos`, the median of the participant's positive TBM values (at least 20 of them); `zero_share`, zero rows / tubules with a TBM number (at least 20 tubules). Packages with more than one participant are left out, as before.
- **Gate:** at least 95% of the 361 listed packages read, and the score and clinical files load. Otherwise every grade is "pending".

## Predictions (graded exactly as written)

| | Check | Pass if | Prediction |
|---|---|---|---|
| Z1 | Zero rows exist in v1 too | v1 share >= 0.01 (at least 1,000 v1 tubules with a TBM number) | pass |
| Z2 | v2 zero rows are concentrated in some slides | Pearson chi-square / df of per-slide zero counts against one common rate > 2 (slides with >= 20 tubules; at least 20 slides) | pass |
| Z3 | v2 zero rows are smaller tubules | median size of zero rows / median size of other rows < 0.8 | pass (low confidence) |
| Z4 | v1 zero rows are commoner in the medulla | odds ratio (0.5 added per cell) >= 2 (at least 100 medulla tubules and 10 zero rows) | pass (low confidence) |
| Z5 | `tbm_pos` vs "Cortex: Tubular Atrophy: Common Type: Percent" | version-stratified Spearman rho > 0, one-sided permutation p < 0.05, n >= 30 | fail |
| Z6 | `tbm_pos` vs baseline eGFR | rho < 0, p < 0.05, n >= 30 | fail |
| Z7 | `zero_share` vs tubular atrophy % | rho > 0, p < 0.05, n >= 30 | fail |
| Z8 | `zero_share` vs baseline eGFR | rho < 0, p < 0.05, n >= 30 | fail |

The statistic for Z5-Z8 is question 2's version-stratified rho (within v1 and within v2 participants, each stratum at least 10, participant-weighted; 10,000 shuffles within version, seed 20261028 + test number). Within a version a pixel-to-micron factor cannot change ranks, so no unit conversion is needed. Each test is graded alone; Holm-adjusted p-values over Z5-Z8 are reported beside them.

Why we predict Z5-Z8 fail: TBM thickness failed five times with the zero rows in. Removing a tenth of rows moves a median only if the zero rows are unevenly spread across participants, which Z2 tests. We would rather be wrong here.

## What each outcome means

- **Z5 or Z6 passes:** the zero rows were hiding a real TBM signal. Anyone using KPMP tubule vectors should drop them first, and the Kidney AI entry can use TBM again.
- **Z5 and Z6 fail:** TBM thickness as released does not track atrophy or kidney function in this cohort even when cleaned. The entry leaves it out.
- **Z7 or Z8 passes:** the share of tubules the pipeline could not measure tracks disease. That may be biology (collapsed or atrophic tubules) or an artefact that travels with disease. Either way it would be a new, cheap marker to check by eye, and we would say plainly that we cannot tell which.
- **Z2 and Z3 pass:** zero rows look like a measurement failure that clusters by slide and in small tubules. **Z4 passes:** in v1 at least, much of it is medullary tubules, which a cortical atrophy score would not see.

## Reported, not graded

Exactly-zero vs negative counts; slide-level share range, slides with no zero rows and slides over half zero; cell thickness and luminal fraction medians of zero vs other rows; how many slides' median TBM moves by more than 5% when zero rows are left out; Z5-Z8 within v1 and within v2; raw `In Medulla` values.

## Limits

- Associations in a convenience sample of research biopsies; scores and segmentations may come from different sections of the same biopsy.
- The 20-tubule floors are low. Box area is a crude size for an irregular tubule.
- One model family wrote the code and will grade it; no human has reviewed it. Only aggregate statistics are published.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- `kpmp-objects-results-v1-2026-10-28.md`, `kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md`, `kpmp-q2-prereg-v1-2026-10-27.md` (this folder)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18, 2026-10-26 and 2026-10-27)
