# Pre-registration v1 of question 2: do KPMP's released pathomics features recover known clinical gradients? (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

The plan of 2026-10-26 (`kpmp-q2-plan-v1-2026-10-26.md`, tag v0.9.12) fixed the features, clinical concepts and directions. Following its blinding protocol, this note fixes only the exact columns, codings, floors and pass rules, and does so before any feature value is joined to any clinical value. Code: `../kidney/kpmp_q2.py` 1.0 with offline tests `../kidney/test_kpmp_q2.py`, committed with this note. It runs in the same job as census pass 3 (`kpmp-census-prereg-v3-2026-10-27.md`), after it, and reads that pass's results.

## 1. What we have seen

- **The clinical file's marginals** (job `kpmp-clinical-peek-v1`, 2026-10-27). These are column names and counts only, with no feature attached. The open file is `20260930_OpenAccessClinicalData.csv` (212,249 bytes): 973 participants, one row each, 20 columns. All 250 participants with segmentation packages are in it. Among them: Diabetes History Yes 169, No 80, "Don't know" 1. Baseline eGFR is given as a number for all 250 (median 56.0), as well as in bins. Proteinuria is binned in 4 levels and filled for 153, and age is binned by decade for all 250.
- **Census pass 2:** tubule medians against pathologist scores on v2 participants (see its results note). It joined no clinical value.
- **The plan's "eGFR (range)" was too pessimistic.** The open file carries baseline eGFR as a number. That is a column choice, which this note may make, so C3 and C4 use the number.

## 2. Columns and codings (exact header text)

| Code | Column | Coding |
|---|---|---|
| diabetes | `Diabetes History` | Yes 1, No 0; "Don't know" and empty excluded |
| egfr | `Baseline eGFR (ml/min/1.73m2)` | the number as given |
| proteinuria | `Proteinuria (mg) (Binned)` | `<150 mg/g cr` 1, `150 to <500 mg/g cr` 2, `500 to <1000 mg/g cr` 3, `>=1000 mg/g cr` 4 |
| albuminuria | `Albuminuria (mg) (Binned)` | `<30` 1, `30 to <300` 2, `300 to <500` 3, `500 to <1000` 4, `>=1000` 5 (each followed by ` mg/g cr`) |
| a1c | `A1c (%) (Binned)` | `<6.5%` 1, `6.5 to <7.5%` 2, `7.5 to <8.5%` 3, `>=8.5%` 4 |
| hypertension | `Hypertension History` | Yes 1, No 0 |
| raas | `On RAAS Blockade` | Yes 1, No 0 |
| sex_male | `Sex` | Male 1, Female 0 |
| age_bin | `Age (Years) (Binned)` | the lower bound of "NN-NN Years" (10, 20, ... 80) |

Any other value is treated as missing. The file is named by a fresh Repository file-list export ("Clinical Study Data"; exactly one open .csv row is required) and is not re-hosted.

## 3. Features (from the plan; census 3's reader)

These are participant-level values pooled over all of a participant's packages. Every package belongs to one participant, and no participant mixes versions.
- **Glomerular tuft area:** `gloms` sheet (v1: non-globally-sclerotic workbook) column `Area`. The median over the participant's glomeruli, with at least 5 glomeruli.
- **Mesangial fraction:** `gloms`, `Mesangial Fraction`, median, at least 5 glomeruli.
- **Share of globally sclerotic glomeruli:** sclerotic rows / (non-sclerotic + sclerotic rows), with at least 5 glomeruli. A package counts only if it has a non-sclerotic glomerulus sheet. **A v1 package with that workbook but no sclerotic workbook counts as 0 sclerotic glomeruli** (rule for the 30 v1 packages without one). Sensitivity: the same test without participants who have such a package.
- **Average TBM thickness:** `tubs`, `Average TBM Thickness`, median, at least 20 tubules.
- Discovery only: average cell thickness and luminal fraction (`tubs`, at least 20 tubules) and arterial area (`arts`, `Arterial Area`, at least 3 vessels).

**Units.** "Converted" follows the plan: v1 values as given (microns per the README), v2 values times census 3's scanner pixel size (mpp_hat), or its square for areas. Census 3 tests whether that conversion is right:
- glomerular and arterial area are pooled as converted only if census 3's P5 passes;
- TBM and cell thickness are pooled as converted only if census 3's P3 passes;
- unitless features (mesangial fraction, luminal fraction, sclerotic share) are always pooled.

Otherwise a control is graded on the **version-stratified statistic**: Spearman rho within v1 and within v2 participants separately (a stratum needs at least 10 participants), combined as the participant-weighted mean, with the clinical codes shuffled only within each version. Within one version, a unit factor cannot change ranks, so this needs no conversion.

## 4. Positive controls: rules

| | Feature | Clinical code | Direction (from the plan) |
|---|---|---|---|
| C1 | glomerular tuft area | diabetes | rho > 0 (larger with diabetes) |
| C2 | mesangial fraction | diabetes | rho > 0 |
| C3 | sclerotic share | egfr | rho < 0 (higher at lower eGFR) |
| C4 | TBM thickness | egfr | rho < 0 |
| C5 | glomerular tuft area | proteinuria | rho > 0 |

- **Statistic:** Spearman rho between the participant feature and the clinical code. For a yes/no code this is a rank (Mann-Whitney-type) comparison. The one-sided permutation p in the fixed direction uses 10,000 shuffles, seed 20261027 + control number.
- **Floors:** at least 30 participants in total, and for diabetes at least 30 in each arm. Below a floor the control is untestable.
- **Pass:** rho in the fixed direction and p < 0.05. Each control is its own check, so there is no correction across the five. A failed control is published as a failure and weakens any discovery built on the same feature.
- **Reported, not graded:** each control pooled on converted values and on raw (unconverted) values; the stratified statistic; v1-only and v2-only rho; the share of v2 participants within each clinical level (eGFR: below vs at or above its median), so that the size and direction of any pooling artefact is visible; rho within age bands (under 50, 50-59, 60-69, 70 and over); and C3's sensitivity analysis.
- **Gate:** the analysis runs only if at least 95% of listed packages are read and the clinical file loads. Otherwise every control is "pending".

## 5. Discovery stage

- The participants who have a clinical row are sorted by ID, shuffled once with seed 20261027 and split in half (exploration, confirmation).
- **Pairs:** 7 features (the four above plus cell thickness, luminal fraction and arterial area) x 9 clinical codes, minus the 5 control pairs, gives 58 pairs. All use the version-stratified statistic on raw values, so there is no unit dependence.
- **Exploration:** a pair is carried forward if the half has at least 20 participants (at least 10 per arm for yes/no codes) and its two-sided permutation p is < 0.05 (10,000 shuffles).
- **Confirmation:** each carried pair is tested one-sided in the direction it showed in exploration, under the same floors. Holm adjustment is applied over all carried pairs; a pair failing a floor or reversing direction enters with p = 1. A pair is a **confirmed finding** only if its Holm-adjusted p is < 0.05. Everything else is exploratory and labelled so.
- Confirmed findings are associations in a convenience sample of biopsies, not causes. They will be checked against the literature before being called new.

## 6. Prediction

C1, C2, C3 and C5 pass, and C4 passes with the least confidence. Census pass 2 found v2 tubule medians unrelated to the pathologists' atrophy percentages, which makes a TBM gradient with eGFR less likely. We make no prediction for the discovery stage.

## 7. Limits

- Clinical values are baseline values, and some are bins. Diabetes history is coarse.
- Features are pooled over slides that may sample different tissue, and the 5-glomerulus and 20-tubule floors are low.
- Participants are a convenience sample of research biopsies, enriched for diabetic and hypertensive kidney disease and acute kidney injury.
- One model family wrote the code and will grade it; no human has reviewed it. Only aggregate statistics are published.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- `kpmp-q2-plan-v1-2026-10-26.md`, `kpmp-census-prereg-v3-2026-10-27.md`, `kpmp-census-results-v2-2026-10-27.md` (this folder)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (Clinical Study Data file-list export of 2026-10-26)
- https://www.kpmp.org/available-data
