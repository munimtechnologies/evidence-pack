# Pre-registration: does KPMP's tubular basement membrane thickness track atrophy once tubule size is taken out? (2026-10-30)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Written and published before the job that runs it (`kpmp-tbmsz-v1`) is filed, and before any size-adjusted value has been computed. Code: `../kidney/kpmp_tbmsz.py` 1.0 with offline tests on synthetic tubules (`../kidney/test_kpmp_tbmsz.py`).

## Why

Thickened, wrinkled tubular basement membranes (TBM) are a textbook sign of tubular atrophy, and a 2025 NEPTUNE study measured thicker TBM in pre-atrophic and atrophic tubules (Kidney International 2025, PMC12302419). In KPMP's released pathomics vectors, however, a participant's median positive `Average TBM Thickness` tracked neither the KPMP pathologists' tubular atrophy % (rho +0.062, p 0.17, n 222) nor baseline eGFR (-0.100, p 0.062, n 247) (`kpmp-tbm0-twins-results-v1-2026-10-28.md`, Z5 and Z6).

Two later results narrow the reasons:
- Per tubule, TBM thickness is reproducible between serial sections (rho 0.46 against 0.09 for random same-size tubules; `kpmp-twinrel-results-v2-2026-10-30.md`, R2). So the null is not per-object noise; its pre-registered reading points to how the feature is summarised or what it measures.
- A participant's share of small tubules tracks atrophy (+0.346) and eGFR (-0.349) (`kpmp-zs-results-v1-2026-10-29.md`, not pre-registered), and a blinded AI triage found small boxes are mostly not ordinary whole tubules (`kpmp-triage-results-v1-2026-10-30.md`).

If measured TBM thickness changes with tubule size, a median over all tubules mixes thickness with the participant's size mix, and the two can cancel. This plan removes size per tubule before summarising.

**Prior art** (searched 2026-10-30; web): the NEPTUNE study above reports tubule-level TBM thickness by IFTA stage and the SD of TBM thickness against remission, in its own segmentation; Next-Generation Morphometry (FLASH) reports tubular diameter falling with kidney function. We found no size-adjusted TBM thickness in KPMP's released vectors, and no test of it against the KPMP pathologists' atrophy scores. Our own earlier tests used unadjusted medians only.

## Data (fixed now)

- **Packages:** every package in the Repository segmentation file-list export used by the earlier studies (`inputs/kpmp-segmentation-files.csv`, 82,530 bytes; file names and package IDs only, not re-hosted), read from the census cache after `kidney.kpmp_fill` (with `--allow-full`). Packages shared by several participants are used for the size lines but not for participant features, as in `kpmp_zs`.
- **Tubules:** the `tubs` sheet read with `kidney.kpmp_tbm0.tubules` 1.0 unchanged: `Average TBM Thickness`, and size = box area (v2) or `Area (pixel^2)` (v1). Sizes therefore differ in kind between versions, so every line and every statistic is kept within version.
- **Scores and clinical:** the KPMP descriptor-score file (`Cortex: Tubular Atrophy: Common Type: Percent`, `Cortex: Interstitial Fibrosis: Percent`) and the open clinical file, coded exactly as in the Q2 pre-registration (eGFR numeric; age band, diabetes, albuminuria and proteinuria as coded there).

## Measure

- **Size line:** per version, the least-squares line of ln(TBM) on ln(size) over every tubule of that version with both values positive (zero-TBM rows are left out, as in Z5).
- **Residual:** each such tubule's ln(TBM) minus its line value.
- **Participant feature `tbm_adj`:** the median residual over the participant's tubules, for participants with at least 20 such tubules.
- **Small share** (covariate, as in `kpmp_zs`): the share of the participant's tubules with a TBM number and a positive size that lie below the version's 25th size percentile (index floor(0.25 (n - 1)) of the sorted sizes).
- **Statistics:** the version-stratified Spearman rho of Q2 (within v1 and within v2, strata of at least 10 participants, participant-weighted) with a one-sided permutation p from 10,000 shuffles of the outcome within each stratum (seed 20261031 + test number). The adjusted test (A3) is `kpmp_zs`'s rank partial correlation: within each stratum, the ranks of feature and outcome are each regressed on the ranks of the small share and the residuals correlated; the permutation shuffles the outcome residuals (approximate).

## Gates

- At least 95% of listed packages read, and both the score file and the clinical file loaded; otherwise every grade is **pending**.
- At least 60 participants in the strata used; otherwise that grade is **untestable**.

## Predictions

A test passes if rho is in the predicted direction and its one-sided p < 0.05. Holm-adjusted p across A1-A3 will also be given, and a result called "confirmed" only if that is < 0.05.

| | Test | Prediction |
|---|---|---|
| A1 | `tbm_adj` vs tubular atrophy %, rho > 0 (primary) | pass (low confidence) |
| A2 | `tbm_adj` vs baseline eGFR, rho < 0 | pass (low confidence) |
| A3 | A1 holding small share fixed, partial rho > 0 | fail (low confidence) |

Why: atrophic tubules should have thicker TBM for their size, so removing size should uncover the textbook gradient if the size mix was hiding it. But we do not know the sign of the size line yet, and the zero-TBM and small-tubule shares already carry most of the size-linked atrophy signal in these files, so we expect little to remain once small share is held fixed (A3).

**Readings fixed in advance:**
- **A1 pass:** the size mix was hiding an atrophy gradient in KPMP's TBM thickness. Size-adjusted TBM becomes a candidate feature for MV2's Kidney AI Discovery Challenge entry, reported beside small-tubule share. Cross-sectional association only.
- **A1 pass, A3 pass:** size-adjusted TBM carries atrophy information beyond the small-tubule share. **A1 pass, A3 fail:** it tracks atrophy but adds nothing measurable beyond small share, so the entry uses small share and reports `tbm_adj` as a check.
- **A1 fail:** the size mix does not explain the earlier null. With R2 (reproducible per tubule), KPMP's TBM thickness, adjusted or not, does not track the pathologists' atrophy scores at participant level in these files. It is dropped from the entry's discovery features and the finding goes into the public pitfalls guide.
- **If the size line is nearly flat** (|slope| < 0.05 in both versions), adjustment barely changes the feature and A1 is read as a repeat of Z5, not as a new test.
- If A1 and A2 disagree, A1 (the pathologists' own score) is primary; eGFR reflects much more than atrophy and covers more participants.

**Descriptive (not graded; two-sided p):** the fitted lines (intercept, slope, tubules) per version; median TBM in each quarter of each version's sizes; the plain median ln(TBM) on the same participants against atrophy and eGFR (the comparator, a repeat of Z5 and Z6); the same features computed only over tubules at or above the 25th size percentile (a size floor, because small boxes are mostly not ordinary tubules), adjusted and not; small share against atrophy and eGFR; `tbm_adj` against fibrosis, age band, diabetes, albuminuria, proteinuria, small share and the plain median; A2 holding small share fixed; v1-only and v2-only rho for every graded test.

## Outputs and privacy

`results.json` holds aggregates only: counts, line coefficients, quarter medians, rho and p. No participant ID, participant-level value, package ID or KPMP file is written or published. No image is used.

## Limits

- One straight line per version on the log scale; a curved relation would leave some size in the residuals. The quarter medians show how far the line is from the data.
- The v2 size is a bounding box, not the tubule's area, and box area depends on orientation. Pixel sizes differ slightly between scanners; a different pixel size shifts a slide's residuals.
- Zero-TBM rows are left out, and they are not random (`kpmp-twinrel-results-v2-2026-10-30.md`, R5). Serial-section repeats count some tubules twice on v2 slides; a median is little affected, and v1-only and v2-only results are reported.
- Convenience sample enriched for diabetic and hypertensive kidney disease and AKI; scores and clinical values are baseline only. Same participants as the earlier studies, so this is not an independent replication.
- One model family wrote, tests and will grade this; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-tbm0-twins-results-v1-2026-10-28.md`, `kpmp-zs-results-v1-2026-10-29.md`, `kpmp-twinrel-results-v2-2026-10-30.md`, `kpmp-triage-results-v1-2026-10-30.md`, `kpmp-q2-prereg-v1-2026-10-27.md` (this folder)
- Clinical relevance of computationally derived tubular features and their spatial relationships with the interstitial microenvironment in minimal change disease/focal segmental glomerulosclerosis, Kidney International 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC12302419/
- Next-Generation Morphometry for pathomics-data mining in histopathology, https://d-nb.info/1279397020/34
