# Results of question 2: do KPMP's released pathomics features recover known clinical gradients? (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-q2-prereg-v1-2026-10-27.md` (tag v0.9.14), with the plan `kpmp-q2-plan-v1-2026-10-26.md` (tag v0.9.12). Code: `../kidney/kpmp_q2.py` 1.0, unchanged since that tag. It ran in job `kpmp-census3-v1` right after census pass 3 (`kpmp-census-results-v3-2026-10-28.md`) and read that pass's results. Its offline tests passed first. Run time 3.4 minutes.

## Inputs

- Gate met: 358 of 361 packages read, none with errors; the clinical file loaded (`20260930_OpenAccessClinicalData.csv`, 212,249 bytes, SHA-256 293e3175...e6, 973 participants, all 20 expected columns present).
- 247 participants have both an analysed package and a clinical row: 136 with v1 packages only, 111 with v2 only, none with both. 25 v1 participants have a package without a sclerotic-glomerulus workbook (the pre-registered rule counts it as 0 sclerotic glomeruli; see C3's sensitivity analysis).
- Census pass 3 graded P3 and P5 as fail, so, as pre-registered, glomerular area and TBM thickness were graded on the **version-stratified statistic** (Spearman rho within v1 and within v2, participant-weighted, shuffles within version). Mesangial fraction and sclerotic share are unitless and were graded pooled.

## Grades, exactly as pre-registered

| | Feature vs clinical code | Predicted | Graded on | rho | one-sided p | n | Grade |
|---|---|---|---|---|---|---|---|
| C1 | glomerular tuft area vs diabetes, rho > 0 | pass | stratified | +0.231 | 0.0003 | 216 (67 no, 149 yes) | **pass** |
| C2 | mesangial fraction vs diabetes, rho > 0 | pass | pooled | +0.138 | 0.021 | 216 | **pass** |
| C3 | share of globally sclerotic glomeruli vs baseline eGFR, rho < 0 | pass | pooled | -0.345 | 0.0001 | 226 | **pass** |
| C4 | TBM thickness vs baseline eGFR, rho < 0 | pass (least confident) | stratified | -0.036 | 0.29 | 247 | **fail** |
| C5 | glomerular tuft area vs proteinuria (4 bins), rho > 0 | pass | stratified | +0.224 | 0.0053 | 129 | **pass** |

Four of five predictions held. p = 0.0001 is the floor of 10,000 shuffles. C3's sensitivity analysis, without the participants who have a v1 package lacking a sclerotic workbook: rho -0.291, p 0.0001, n 208.

**So KPMP's glomerular features recover three textbook gradients** (larger glomeruli with diabetes and with proteinuria, more mesangial matrix with diabetes, more global sclerosis at lower eGFR), and the tubular basement-membrane feature recovers none, here or against the pathologists' atrophy scores in census passes 2 and 3.

## The cost of following the README's units

Reported, not graded. Each control was also computed by pooling v1 and v2 participants, both raw and "converted" the way the README implies (v1 taken as microns, v2 multiplied by the scanner pixel size):

| | Converted as the README implies | Raw (both in pixels) | Stratified (graded) |
|---|---|---|---|
| C1 glomerular area vs diabetes | rho +0.037, p 0.29 | rho +0.244, p 0.0001 | rho +0.231, p 0.0003 |
| C5 glomerular area vs proteinuria | rho +0.042, p 0.32 | rho +0.238, p 0.0029 | rho +0.224, p 0.0053 |
| C4 TBM thickness vs eGFR | rho -0.031, p 0.32 | rho -0.040, p 0.27 | rho -0.036, p 0.29 |

Following the README makes the two glomerular-size signals disappear. The mechanism is visible in the data: the conversion shrinks every v2 area about 16-fold relative to v1, so the pooled ranks mostly sort participants by file version, and v2 participants are more common among people with diabetes (51% vs 42%) and with the highest proteinuria bin (52% vs 35-45%). Within each version the signal is the same size (C1: v1 rho +0.225, v2 +0.238; C5: v1 +0.212, v2 +0.239). Census pass 3 shows why the raw pool works: both versions are in pixels.

## Other reported values (not graded)

- **Age bands.** The glomerular-size and sclerosis gradients are strongest in younger participants: C1 rho +0.49 under 50 (n 63), +0.34 at 50-59, +0.06 at 60-69, +0.09 at 70 and over; C3 -0.38, -0.32, -0.24 and +0.02 (n 38). These bands are small and not corrected for anything; they are a lead, not a finding.
- **By version.** C2 is carried mostly by v2 (v1 rho +0.079, v2 +0.256). C3 holds in both (v1 -0.316, v2 -0.373). C4 is null in both (v1 +0.004, v2 -0.085).

## Discovery stage

As pre-registered: 247 participants split by a seeded shuffle into halves of 123 (exploration) and 124 (confirmation); 58 feature-clinical pairs on the version-stratified raw statistic.

- 20 pairs passed exploration (two-sided p < 0.05) and were carried. All 20 met the floors in confirmation.
- **One pair was confirmed** (Holm-adjusted p < 0.05 over the 20): **share of globally sclerotic glomeruli vs hypertension history**, exploration rho +0.397 (n 111), confirmation rho +0.273, one-sided p 0.0019, Holm p 0.038 (n 114: 58 v1, 56 v2).
- This is not new. Global glomerulosclerosis with hypertension (hypertensive arterionephrosclerosis) is standard renal pathology. We report it as a further check that the released glomerular classes behave as expected, not as a discovery.
- Closest misses (exploratory only): mesangial fraction vs proteinuria (confirmation rho +0.305, p 0.0056, Holm 0.11), mesangial fraction vs albuminuria (Holm 0.40), TBM thickness vs proteinuria (Holm 0.44), glomerular area vs albuminuria (Holm 0.56). Twelve carried pairs fell to p > 0.1 in confirmation, including three sclerotic-share pairs that looked strong in exploration (diabetes, RAAS blockade, proteinuria; exploration p 0.0002-0.008).

## What this changes for the Kidney AI entry

1. **Glomerular features are usable, with units fixed.** Glomerular area, mesangial fraction and the sclerotic share pass clinical positive controls once versions are not mixed. Rare-glomerulus work can lean on them.
2. **Tubule summary features are not, as released and summarised.** TBM thickness failed against atrophy (pass 2 P8, pass 3 V8 and T8) and against eGFR (C4). The object audit found that 10.0% of v2 tubule rows have a TBM thickness of zero or less, which every participant median here includes. Whether excluding them changes anything is the next pre-registered question, not something we claim now.
3. **Every entrant pooling v1 and v2 needs this.** A unit mismatch that silently erases a textbook gradient is exactly the "artefact control" the challenge scores.

## Limits

- Associations in a convenience sample of research biopsies, enriched for diabetic and hypertensive kidney disease and acute kidney injury. Baseline clinical values; proteinuria and albuminuria are bins; diabetes history is coarse.
- Participant values pool slides that may sample different tissue; the 5-glomerulus and 20-tubule floors are low.
- Age-band and by-version values are many small descriptive cuts.
- One model family wrote the code and graded it; no human has reviewed it. Only aggregate statistics are published; `q2/results.json` stays local.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-q2-prereg-v1-2026-10-27.md`, `kpmp-q2-plan-v1-2026-10-26.md`, `kpmp-census-results-v3-2026-10-28.md`, `kpmp-objects-results-v1-2026-10-28.md` (this folder)
- Job output `compete-results/kpmp-census3-v1/out/q2/` (local; aggregates quoted above)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (Clinical Study Data file-list export of 2026-10-26)
