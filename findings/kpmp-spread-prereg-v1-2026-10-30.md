# Pre-registration: is the within-biopsy spread of glomerular size higher at higher albuminuria in KPMP's open pathomics vectors? (2026-10-30)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Written and published before the job that runs it (`kpmp-spread-v1`) is filed, and before any spread value has been computed. Code: `../kidney/kpmp_spread.py` 1.0 with offline tests on synthetic participants (`../kidney/test_kpmp_spread.py`).

## Why

A 2026 glomerulus foundation-model paper (GloPath, arXiv 2603.02926) segmented 28,242 glomeruli from 1,352 KPMP slides with its own pipeline and reported that "albuminuria was linked to increased heterogeneity in glomerular area". As far as we could read, the comparison was between whole distributions of glomeruli pooled by clinical group (Kolmogorov-Smirnov and Kruskal-Wallis tests), and the spread measure is not defined in the text we read. Pooling glomeruli from many people can make a group's distribution wider simply because the people in it differ in median size, so a pooled comparison does not show that each person's biopsy is more heterogeneous.

This plan tests the participant-level version of that claim on a different segmentation: KPMP's own released pathomics vectors. One number per participant, the spread of that person's glomerular sizes, is ranked against albuminuria. It also checks whether any association survives removing the participant's median size, because median tuft area already tracks proteinuria in these files (our control C5: version-stratified rho +0.224, `kpmp-q2-results-v1-2026-10-28.md`).

**Prior art** (searched 2026-10-30; web and arXiv):
- GloPath (above): KPMP-G cohort, own segmentation, group-level distribution tests; no participant-level spread statistic that we could find.
- A NEPTUNE/CureGN study of minimal change disease and FSGS (PMC12632648; medRxiv 10.1101/2025.10.01.25336172) aggregated glomerulus-level features per patient as mean and standard deviation; the SD of major axis length and the SD of a texture feature were associated with proteinuria remission after adjustment. It did not use KPMP, and cross-sectional albuminuria was not reported.
- Our own KPMP work has joined only participant medians and shares to clinical data (`kpmp-q2-results-v1-2026-10-28.md`). In that study's discovery screen, median glomerular area against albuminuria was a near miss (Holm 0.56 in the confirmation half). No spread value has been computed.

We found no participant-level test of glomerular size heterogeneity against albuminuria in KPMP's released vectors. That is the new part; the question itself is not new.

## Data (fixed now)

- **Packages:** every package in the Repository segmentation file-list export used by the section-twin studies (`inputs/kpmp-segmentation-files.csv`, 82,530 bytes; file names and package IDs only, not re-hosted), read from the census cache (`kidney.kpmp_fill` first fills it if needed, without whole-zip downloads). Packages shared by several participants are skipped, as in Q2.
- **Glomeruli:** the `gloms` sheet (non-globally-sclerotic glomeruli; for v1, the non-sclerotic workbook), column `Area`, read with `kidney.kpmp_q2.extract_package` unchanged. Only positive values. All packages of a participant are pooled.
- **Clinical:** KPMP's open clinical file located through the clinical file-list export, coded exactly as in the Q2 pre-registration: `Albuminuria (mg) (Binned)` 1-5, `Proteinuria (mg) (Binned)` 1-4, `Baseline eGFR (ml/min/1.73m2)` numeric, `Diabetes History` 0/1, `A1c (%) (Binned)` 1-4.

## Measure

- Per participant with **at least 10 glomeruli**: the **interquartile range of ln(area)** (quantiles by linear interpolation). Also kept: the median and standard deviation of ln(area).
- A spread of logs does not depend on the unit or on the scanner's pixel size, so the v1/v2 unit problem in these files (`kpmp-open-pathomics-pitfalls-v1-2026-10-28.md`) cancels within a participant. Version is still kept apart: every statistic is the **version-stratified Spearman rho** of Q2 (rho within v1 and within v2, strata of at least 10 participants, participant-weighted mean), with a one-sided permutation p from 10,000 shuffles of the clinical code within each stratum (seed 20261030 + test number).
- **Adjusted test:** within each stratum the ranks of the spread and of the clinical code are each replaced by their residuals on the ranks of the participant's median ln(area); rho is the correlation of the residuals (a partial Spearman), and the permutation shuffles the clinical residuals (Kennedy 1995). This permutation is approximate.

## Gates

- At least 95% of listed packages read and the clinical file loaded; otherwise every grade is **pending**.
- At least 60 participants in the strata used; otherwise that grade is **untestable**.

## Predictions

A hypothesis passes if rho is in the predicted direction and its one-sided p < 0.05. The note will also give Holm-adjusted p across H1-H3 and call a result "confirmed" only if that is < 0.05.

| | Test | Prediction |
|---|---|---|
| H1 | IQR of ln(glomerular area) vs albuminuria bin, rho > 0 (primary) | pass (low confidence) |
| H2 | IQR of ln(glomerular area) vs proteinuria bin, rho > 0 | pass (low confidence) |
| H3 | H1 after removing the participant median ln(area), partial rho > 0 | fail (low confidence) |

Why: nephron loss and compensatory hypertrophy should make some glomeruli larger while others shrink, and GloPath saw wider area distributions with albuminuria in KPMP. But a two-dimensional profile area depends heavily on where the section cuts each glomerulus, which adds a large, disease-free spread to every biopsy and may drown the signal. If a spread signal exists, we expect much of it to travel with median size (C5), so H3 is predicted to fail.

**Readings fixed in advance:**
- **H1 pass, H3 pass:** within-biopsy spread carries information beyond median size. It becomes a candidate image feature for MV2's Kidney AI Discovery Challenge entry, to be checked next for reliability (serial-section twins) and in a fresh split. Cross-sectional association only.
- **H1 pass, H3 fail:** the participant-level version of GloPath's observation holds in KPMP's own vectors, but here spread adds nothing beyond median size.
- **H1 fail:** the pooled observation does not reproduce as a per-participant spread in KPMP's vectors. Possible reasons, not to be chosen between without new data: between-person differences inflating pooled distributions, a different segmentation, or sectioning noise. This is reported as a negative result, not as evidence against GloPath.
- If H1 and H2 disagree, the difference is read against their different coverage (both are binned and partly missing) before anything else.

**Descriptive (not graded):** the same statistic for median ln(area) vs albuminuria and proteinuria (the plain comparator); SD of ln(area) vs both; the adjusted test for proteinuria; spread vs eGFR (rho < 0), diabetes, A1c and the number of glomeruli (if |rho| with the count is 0.3 or more, the note will say spread is tied to biopsy size); IQR of mesangial fraction (not logged) vs albuminuria and proteinuria; H1 with at least 20 glomeruli; v1-only and v2-only rho for every test; participants per clinical level.

## Outputs and privacy

`results.json` holds aggregates only: counts, rho, p and participants per clinical level. No participant ID, participant-level value or KPMP file is written or published. No image is used.

## Limits

- Convenience sample enriched for diabetic and hypertensive kidney disease and AKI; clinical values are baseline and binned; albuminuria is missing for part of the sample.
- Serial-section repeats on some v2 slides measure the same glomerulus twice (`kpmp-twinrel-prereg-v1-2026-10-28.md`); that weights those glomeruli double inside the spread. v1-only and v2-only results are reported for this reason.
- Glomeruli flagged as globally sclerotic are excluded by the files' own split, so loss through sclerosis is not in the spread.
- One model family wrote, tests and will grade this; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-q2-prereg-v1-2026-10-27.md`, `kpmp-q2-results-v1-2026-10-28.md`, `kpmp-open-pathomics-pitfalls-v1-2026-10-28.md`, `kpmp-twinrel-prereg-v1-2026-10-28.md` (this folder)
- He Q, et al. GloPath: An Entity-Centric Foundation Model for Glomerular Lesion Assessment and Clinicopathological Insights. arXiv 2603.02926 (2026), https://arxiv.org/abs/2603.02926
- Glomerular Segmentation, Classification, and Pathomic Feature-based Prediction of Clinical Outcomes in Minimal Change Disease and Focal Segmental Glomerulosclerosis, https://pmc.ncbi.nlm.nih.gov/articles/PMC12632648/ (medRxiv 10.1101/2025.10.01.25336172)
- Kennedy PE. Randomization tests in econometrics. Journal of Business and Economic Statistics 1995;13(1):85-94.
