# Pre-registration v1: an object-level audit of KPMP's released v2 pathomics vectors (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

## Why

The NIDDK Kidney AI Discovery Challenge scores entries on finding rare or unexpected features in KPMP biopsies, and on separating real findings from artefacts of staining, scanning, preparation or segmentation. KPMP releases, for every segmented PAS slide, one row per detected glomerulus, tubule and artery, with a bounding box and a few measurements. Our census passes so far looked at participant-level medians. This audit looks at the objects themselves, and asks two things before anyone builds a rare-object detector on them:

1. **Integrity:** are the rows internally consistent?
2. **Rarity:** how much of what a naive screen calls "rare" is really a slide-level shift, and do the objects that stay rare within their own slide look like segmentation errors or like focal lesions?

Prior art (searched 2026-10-27): KPMP's segmentation papers and its Atlas documentation describe pathologist review and visual inspection (Keller et al. 2025, arXiv 2510.19499, which adds interactive histograms and colouring by feature in Vitessce). We found no published statistical audit of the released per-object vectors, and no published rate of internal inconsistencies, double segmentations or slide-explained outliers in them.

## Data and code

- **Data:** only the feature workbooks that census pass 1 kept in its data volume (`kpmp-census/<package>/`, from KPMP's open "Segmentation Masks & Pathomics Vectors" packages). Nothing is downloaded. No participant ID, clinical value or pathologist score is read.
- **Scope: v2 packages only** (220 packages, one workbook each). Census pass 2 recorded their exact headers. v1 packages wait for census pass 3, which records their raw sheet names and headers.
- **Code:** `../kidney/kpmp_objects.py` 1.0, standard library only, with offline tests `../kidney/test_kpmp_objects.py`. Both are committed with this note, before the job runs. Job `kpmp-objects-v1` runs the tests, then the audit, in a sealed container with no network.
- **Reading.** A folder counts as v2 if it holds exactly one workbook whose sheet names, lower-cased and with bracketed text dropped, include `gloms`, `s_gloms`, `tubs` and `arts`. Columns are matched by their exact header text: `x1|x2|y1|y2|Area|Mesangial Area|Mesangial Fraction` (gloms and s_gloms), `x1|x2|y1|y2|Average TBM Thickness|Average Cell Thickness|Luminal Fraction` (tubs) and `x1|x2|y1|y2|Arterial Area` (arts). Raw sheet names and headers are recorded.
- **Gate:** at least 200 v2 packages read. Otherwise every grade is "pending".

## Definitions

- **Box:** valid if all four coordinates are numbers and x2 > x1 and y2 > y1. Width = x2 - x1, height = y2 - y1.
- **Fill:** Area (or Arterial Area) / (width x height). If area and box share a unit (KPMP's README says v2 values are pixels), a roundish object fills about 0.6-0.8 of its box. If the area were in square microns, the fill would be about 0.064 times that (0.2527 microns per pixel, squared).
- **Misshapen:** fill below 0.5 or box aspect (long side / short side) above 2.5.
- **Double segmentation:** a glomerulus (gloms or s_gloms) whose box has intersection-over-union of at least 0.5 with the box of another glomerulus on the same slide. Same-sheet and cross-sheet pairs (one glomerulus called both sclerotic and non-sclerotic) are counted separately.
- **Screened features:** glomeruli (non-sclerotic sheet): log Area and Mesangial Fraction. Tubules: log TBM thickness, log cell thickness and Luminal Fraction. Arteries: log Arterial Area. An object is eligible if all its screened features are defined (logs need positive values) and its slide has at least 20 such objects with non-zero spread on every feature.
- **Robust z:** (value - median) / (1.4826 x median absolute deviation). The **pooled z** uses all v2 objects of that compartment. The **slide z** uses that slide's objects only. An object is a pooled outlier if its largest absolute pooled z is at least 4, and a within-slide outlier if its largest absolute slide z is at least 4.

## Predictions (graded exactly as written)

| | Check | Pass if | Prediction |
|---|---|---|---|
| I1 | Valid boxes, all four sheets | share >= 0.999 | pass |
| I2 | Median glomerular fill (unit check of the README) | 0.45 <= median <= 1.0 | pass |
| I3 | Area fits in its box (fill <= 1.05), glomeruli and arteries | share >= 0.99 | pass |
| I4 | Mesangial Fraction = Mesangial Area / Area within 0.001 x (1 + fraction) | share >= 0.99 | pass |
| I5 | Luminal and mesangial fractions within [0, 1] | share >= 0.999 | pass |
| I6 | Glomeruli in a double segmentation | share < 0.01 | pass |
| I7 | Tubule rows that exactly repeat another row of the same slide | share < 0.001 | pass |
| R1 | Tubule pooled outliers that are not within-slide outliers ("slide-explained") | share >= 0.5 (at least 30 pooled outliers) | pass |
| R2 | Over-dispersion of within-slide tubule outliers across slides: Pearson chi-square / df against one common rate | > 2 (at least 20 slides, 30 outliers) | pass |
| R3 | Within-slide outlier glomeruli are misshapen more often than other glomeruli: odds ratio with 0.5 added to each cell | >= 2 (at least 10 outliers) | pass |
| R4 | Within-slide outlier tubules cluster in space: on each slide with at least 10 outlier tubules (and at least twice as many eligible tubules), the mean nearest-neighbour distance between outlier box centres is compared with the mean over 20 random samples of the same size from the slide's eligible tubules (at most 500 points, seed 20261027 + slide index) | share of slides with the smaller outlier distance >= 0.6 and one-sided sign test p < 0.05 (at least 20 slides) | pass |

How confident we are: I1, I3, I5 and I7 test bookkeeping and should pass easily. We are less sure of I4 (the fraction may be defined against another area) and I6 (glomeruli are segmented as two classes, which could overlap). R1-R4 are our best guesses, and R3 is the least certain. Each check is graded alone, with no correction across checks: only R4 has a p-value. A failed prediction is published as a failure.

**What each result would mean.** If R1 passes, a naive pooled anomaly screen on these vectors mostly finds slides, not objects, and any rare-object method needs slide-level normalisation. If R3 passes, within-slide outlier glomeruli are enriched for segmentation errors, so shape filters must come before any claim of a rare lesion. If R4 passes, outlier tubules sit in clumps, which fits focal disease and also regional artefacts (folds, edges, blur). The audit cannot tell those apart: that needs a person looking at the slide, which is what the internal candidate list is for.

## Reported, not graded

Counts per sheet; fill by sheet; the slide-level range of median glomerular fill; Mesangial Fraction against Mesangial Area / box area, as an alternative definition; outliers by feature and direction; R1 and R2 for glomeruli and arteries; the number of outlier glomeruli that are double-segmented; and the median ratio of outlier to random nearest-neighbour distance.

`candidates.json` (box coordinates of the 30 most extreme within-slide outliers per compartment that are neither misshapen nor double-segmented) is written for expert review. It is **not** published, because it names packages and positions; only aggregates are.

## Limits

- v2 only. The boxes and measurements are KPMP's segmentation output, not ground truth, so "rare" here means rare in the released vectors.
- Robust z on a few features is a deliberately simple screen. A z cut of 4 and a 20-object floor are fixed choices, not tuned.
- Slide-level shifts mix biology (a participant's disease) with process (stain, scanner, section thickness). This audit separates object-level from slide-level rarity; it does not say which slide-level shifts are artefacts.
- One model family wrote the code and will grade it; no human has reviewed it. Nobody on the team is a kidney pathologist.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- `kpmp-census-results-v2-2026-10-27.md` (exact v2 headers; scanner pixel size 0.2527 microns), `kpmp-census-prereg-v3-2026-10-27.md` (this folder)
- KPMP Atlas help, technologies: https://www.kpmp.org/help-docs/technologies
- Keller et al. 2025, Interactive visualization of kidney micro-compartmental segmentations and associated pathomics on whole slide images, arXiv 2510.19499
- NIDDK Kidney AI Discovery Challenge: https://www.herox.com/KidneyAI
