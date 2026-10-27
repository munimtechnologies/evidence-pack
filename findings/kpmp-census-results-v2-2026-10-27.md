# Results: KPMP segmentation census, pass 2 (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-census-prereg-v2-2026-10-27.md` (tag v0.9.13). Code: `../kidney/kpmp_census2.py` 2.0 on `../kidney/kpmp_census.py` 1.0, both unchanged since that tag. Job `kpmp-census2-v1`: python:3.12 container, 2 CPUs, 1 GB memory cap (peak 0.24 GB), network on. It started 2026-10-27 08:24 UTC and finished at 08:47 UTC. The 17 offline tests passed in the container first. The census read pass 1's cache (358 packages, nothing downloaded again). The run took 20.9 minutes.

## Grades, exactly as pre-registered

The 95% gate was met: 358 of 361 packages analysed. The three v1 packages that answered HTTP 500 in pass 1 answered HTTP 500 three more times each.

| | Prediction | Grade | Numbers |
|---|---|---|---|
| S1 scanner pixel size | pass | **pass** | 40 of 40 sampled slides (20 v1, 20 v2) downloaded and gave an Aperio `MPP`; median 0.2527, min 0.2527, max 0.262968, max/min 1.04; all AppMag 40 |
| U1 v1 area in square microns | pass | **untestable** | 0 v1 packages gave a row (our error, below) |
| U2 one pixel scale across versions | pass | **untestable** | same |
| U3 internal and scanner pixel sizes agree | pass | **untestable** | same |
| P2-P5 units of TBM thickness and glomerular area | pass | **untestable** | same |
| P7 luminal fraction vs abnormal luminal morphology %, rho > 0 | pass | **fail** | rho 0.062, one-sided p 0.27, n 105 |
| P8 TBM thickness vs tubular atrophy (common type) %, rho > 0 | pass | **fail** | rho -0.010, p 0.55, n 105 |
| P9 cell thickness vs tubular injury other %, rho < 0 | pass (least confident) | **fail** | rho +0.157 (the opposite sign), p 0.94 for the predicted direction, n 106 |

These grades are recorded unchanged. None of the untestable predictions is counted as passed.

**What the P7-P9 participants were.** Because no v1 row was read, every participant who reached the 20-tubule floor had v2 packages only. So P7-P9 were tested, as written, on v2 participants alone (105-106 of the 227 participants who have both packages and a consensus score). Spearman correlation does not change when every value is multiplied by the same pixel size, so the result does not depend on any unit question. Reported, not predicted: TBM thickness vs cortical interstitial fibrosis % (D1), rho -0.094, n 105.

## Why the unit checks were untestable again: our second reader error

Pass 2 asked each v1 workbook for a sheet named exactly `features`. Pass 1 had reported that name only after its own name normaliser had lower-cased it, so we never saw the sheet's real name. The real name differs from `features` in letter case or in bracketed text, which pass 1's normaliser drops. Pass 2 therefore found no matching sheet in any of the 138 v1 packages: 138 tubule, 131 glomerulus, 108 sclerotic-glomerulus and 138 vessel workbooks were opened and read as empty. Our offline tests built their v1 fixtures with the same assumed name, so they passed. Pass 3 (below) matches the sheet the way pass 1 named it and records every raw sheet name.

## What pass 2 did measure (descriptive)

- **One scanner setting for v2; two for v1.** All 20 sampled v2 slides report MPP 0.2527. 16 of the 20 sampled v1 slides report 0.2527 and 4 report 0.2628-0.2630 (about 4% larger pixels, 8% larger pixel area). All 40 are 40x. A single pixel size is therefore close for v2 but only approximate for v1, which matters if v1 values are in pixels.
- **The October 2026 score release.** "KPMP TIV Descriptor Scores 10.12.2026.xlsx" (468,577 bytes) has six sheets (Data Dictionary, Data Table, KPMP Pathologists Authorship, Pathology Definitions, ReadMe, TIV Score Sheet). "Data Table" holds 426 participants, one row each, all marked consensus complete, with 155 columns covering cortex, medulla and vascular descriptors. 227 of the 247 participants with an analysed segmentation package have a score row.
- **v2 package medians in microns, now with a measured pixel size** (v2 medians from pass 1 times 0.2527, or its square for area; AI arithmetic): TBM thickness about 1.30 microns, cell thickness about 7.60 microns, glomerular tuft area about 26,300 square microns. These assume the v2 README is right that v2 values are pixels, which pass 3 tests against v1.

## What this changes

- **For the planned Kidney AI entry:** in v2, a participant's median tubule TBM thickness, cell thickness and luminal fraction from KPMP's released vectors do not track the consensus pathologists' percentages for atrophy, injury or abnormal lumens. Medians over all tubules may dilute focal lesions. Pass 3 tests that reading with pre-registered tail features (90th and 10th percentiles) and re-tests the median rules on v1 participants, whom no analysis has seen yet.
- **Pass 3** (`kpmp-census-prereg-v3-2026-10-27.md`, published with this note before it runs) fixes the sheet match and runs pass 2's procedure again, so the unit checks U1-U3 and P2-P5 finally see v1 data.
- **Lesson recorded:** a normaliser that reports names must also keep the raw names. Our tests passed because their fixtures shared our assumption, so build fixtures from raw names a job has recorded, not from names we have typed.

## Limits

- P7-P9 failed on v2 participants only. Most v2 slide IDs sort before most v1 slide IDs (pass 1: 143 of 220 v2 and 3 of 138 v1 at or before S-2006-005094), so v1 may differ.
- Participant medians over all tubules are a coarse summary, and scores and segmentations may come from different sections of the same biopsy.
- `results.json` stays local because it holds per-slide feature medians, which are KPMP data. Only the aggregates above are published.
- One model family wrote the code and graded it; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-census-prereg-v2-2026-10-27.md`, `kpmp-census-results-v1-2026-10-27.md`, `../kidney/kpmp_census2.py` (this repository)
- Job output `compete-results/kpmp-census2-v1/` (local; aggregates quoted above)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
