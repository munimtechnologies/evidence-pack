# Results: object-level audit of KPMP's released v2 pathomics vectors (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-objects-prereg-v1-2026-10-27.md` (tag v0.9.15). Code: `../kidney/kpmp_objects.py` 1.0, unchanged since that tag. Job `kpmp-objects-v1`: python:3.12 container, 2 CPUs, 2 GB memory cap, **no network**. It ran on 2026-10-28 from 00:27 to 00:30 UTC; the 11 offline tests passed first, and the audit itself took 0.4 minutes. It read only the feature workbooks already cached by census pass 1.

## Grades, exactly as pre-registered

Gate met: 220 v2 packages read (at least 200 required), no read errors. Raw sheet names and headers matched the pre-registration exactly in all 220 workbooks. Objects: 5,243 glomeruli, 1,365 globally sclerotic glomeruli, 518,756 tubules and 27,176 arteries (552,540 in all).

| | Check | Pass if | Result | Prediction | Grade |
|---|---|---|---|---|---|
| I1 | Valid boxes, all sheets | share >= 0.999 | 552,540 of 552,540 (1.0) | pass | **pass** |
| I2 | Median glomerular fill, area / box area (README pixel check) | 0.45-1.0 | 0.759 | pass | **pass** |
| I3 | Area fits its box (fill <= 1.05), glomeruli and arteries | share >= 0.99 | 33,784 of 33,784 (1.0) | pass | **pass** |
| I4 | Mesangial Fraction = Mesangial Area / Area | share >= 0.99 | 6,608 of 6,608 (1.0) | pass | **pass** |
| I5 | Luminal and mesangial fractions in [0, 1] | share >= 0.999 | 0.999996 (2 of 6,608 mesangial fractions out of range; all 518,756 luminal fractions in range) | pass | **pass** |
| I6 | Glomeruli in a double segmentation (box IoU >= 0.5) | share < 0.01 | 0 | pass | **pass** |
| I7 | Tubule rows exactly repeating another row on the slide | share < 0.001 | 0 | pass | **pass** |
| R1 | Tubule pooled outliers that are not within-slide outliers | share >= 0.5 | 42 of 52 (0.81) | pass | **pass** |
| R2 | Over-dispersion of within-slide tubule outliers across slides | > 2 | 309 (220 slides, 4,733 outliers) | pass | **pass** |
| R3 | Outlier glomeruli misshapen more often than others (odds ratio) | >= 2 | 6.97 (6 of 119 outliers vs 33 of 4,112 others) | pass (least sure) | **pass** |
| R4 | Outlier tubules cluster in space (nearest-neighbour vs random) | share >= 0.6 and sign-test p < 0.05 | 42 of 47 slides (0.89), p 1.2e-8 | pass | **pass** |

All 11 predictions held.

## What the audit shows

1. **The v2 rows are internally clean.** Every box is valid, every area fits its box, every mesangial fraction is exactly Mesangial Area / Area, and nothing is duplicated or double-segmented. Fill is 0.76 for glomeruli, sclerotic glomeruli and arteries alike, and slide medians range only from 0.63 to 0.80 over 211 slides. That confirms the README for v2: areas and boxes share a unit, pixels. (Census pass 3 shows that v1 is in pixels too, against the README.)
2. **One in ten tubules has no TBM thickness.** 52,004 of the 518,756 v2 tubule rows (10.0%) have an `Average TBM Thickness` of zero or less, and 3 have a non-positive cell thickness. The README does not mention this. The audit left these rows out of its rarity screen as pre-registered (logs need positive values), but census and question-2 participant medians include them. That may be why TBM thickness tracked neither the pathologists' atrophy scores nor eGFR; it is a hypothesis to test, not a result.
3. **A naive pooled screen finds slides, not objects.** 81% of pooled tubule outliers are ordinary within their own slide (R1), and within-slide outliers are spread very unevenly over slides (R2 dispersion 309; slide rates from 0 to 38%, median 0.1%). Glomeruli and arteries are less extreme (dispersion 3.6 and 3.8).
4. **Within-slide outliers are mostly one kind.** Tubules: 4,467 of 4,733 are high luminal fraction (dilated or open lumens). Glomeruli: 75 of 119 are small tufts, 22 high and 22 low mesangial fraction. Arteries: 587 of 597 are large. Outlier glomeruli are 7 times as likely as others to be misshapen (fill < 0.5 or aspect > 2.5), so shape filters have to come before any claim of a rare lesion. Outlier tubules sit closer to each other than random tubules on 42 of 47 slides (median distance ratio 0.85), which fits focal disease and regional artefacts alike.
5. **Some "rare objects" are plainly segmentation output, not anatomy.** Among the 30 most extreme artery candidates, the smallest covers 4 pixels, and the two largest cover about 10.2-10.6 million square pixels (about 0.65-0.67 square millimetres at 0.2527 microns per pixel, boxes over 1 mm across). All 30 of the most extreme tubule candidates come from a single slide. These go to visual review next.

## A lesson about our own screen

The robust z-score divides by each slide's median absolute deviation. Luminal fraction is often near zero for most tubules on a slide, so its spread is tiny and ordinary open lumens score z above 100 (the top tubule candidates scored 70-136). Much of R2's over-dispersion and finding 4's dominance of high-lumen tubules may come from this, not from rare lumens. The next screen should use a transform suited to bounded, zero-heavy fractions (for example, per-slide quantiles), fixed in advance.

## Next

- **Visual review.** Job `kpmp-patches-v1` (code `../kidney/kpmp_patches.py` 1.0 with offline tests, published with this note) crops the top 10 candidates per compartment, two typical objects of the same kind from the same slide, and an overview of each slide, and checks which way KPMP's x and y columns run against each slide's size. The patches are KPMP image data and stay private; only counts of what they show will be published.
- **Zero-TBM tubules.** A pre-registered follow-up will ask how they are spread across slides and participants and whether excluding them changes the TBM tests.

## Limits

- v2 only; KPMP's segmentation is the reference here, not ground truth, so "rare" means rare in the released vectors.
- The z cut of 4 and the 20-object floor were fixed choices, not tuned.
- Slide-level shifts mix disease with process (stain, scanner, section thickness); this audit does not separate them.
- One model family wrote the code and graded it; no human has reviewed it. `results.json` holds only aggregates but stays local with the job; `candidates.json` names packages and box positions and is never published.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-objects-prereg-v1-2026-10-27.md`, `kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md` (this folder)
- Job output `compete-results/kpmp-objects-v1/` (local; aggregates quoted above)
- Keller et al. 2025, Interactive visualization of kidney micro-compartmental segmentations and associated pathomics on whole slide images, arXiv 2510.19499
