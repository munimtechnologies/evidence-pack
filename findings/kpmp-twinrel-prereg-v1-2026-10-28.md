# Pre-registration: do KPMP's pathomics features agree between two serial sections of the same object? (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Written and published before the job that runs it (`kpmp-twinrel-v1`) is filed, and before any result of the section-twins census it builds on. Code: `../kidney/kpmp_twinrel.py` 1.0 with offline tests on synthetic slides.

## Why

KPMP's open v2 segmentation workbooks measure each serial section on a slide separately, with no section column (`kpmp-patches-results-v1-2026-10-28.md`). That is a problem for counts, but it also gives something useful: **every object measured in both sections is a free replicate.** It is the same glomerulus or tubule, cut a few microns deeper and segmented again by the same pipeline. If a feature reflects the object, its two measurements should agree more than two random objects of the same size on the same slide do. If it is mostly segmentation noise, they should not.

This matters for two open questions:

1. The tubular basement membrane (TBM) thickness feature tracked neither the KPMP pathologists' atrophy scores nor baseline eGFR (`kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md`). Is it noise at the level of a single tubule, or reproducible but summarised badly?
2. 10.0% of v2 tubule rows have a TBM thickness of zero or less (`kpmp-objects-results-v1-2026-10-28.md`). Is that a property of certain tubules, or random per-section failure?

**Prior art** (searched 2026-10-28; web and arXiv): no published test-retest or serial-section reproducibility analysis of KPMP's pathomics vectors was found. Pathomics robustness work exists for radiomics (CT segmentation variability) and for slide batch effects (FUSION, Nature Communications 2025, checked its glomerular clusters against slide identity). Keller et al. 2025 (arXiv 2510.19499) visualise KPMP segmentations and pathomics, and a 2026 Mayo Clinic study of transplant surveillance biopsies describes computing features across all tissue sections (methods as quoted in search results; full text not read). None of these matches the same object across sections to measure agreement.

## Data and method (fixed now)

- **Slides:** v2 packages (220) in the Repository file-list export of 2026-10-18, read from the job's cache after `kidney.kpmp_fill` fills it. Only slides that the section-twins census rule flags as repeating a section (`kpmp-twins-prereg-v1-2026-10-28.md`; same code `kpmp_twins.detect`, same seed 20261028) are used, with the census's offset.
- **Twin pairs:** in each sheet (`gloms`, `s_gloms`, `tubs`, `arts`), object i is paired with the object j of the same sheet whose box height and width agree within 15% and whose centre is closest to i's centre plus the offset, within 500 pixels. The closest candidates are paired first, and each object is used at most once on each side.
- **Null pairs:** for each twin pair, i is paired with a random object of the same sheet and slide whose height and width agree within 15%, that is not j, and whose centre is not within 500 pixels of i's centre plus or minus the offset (up to 100 seeded draws; seed 20261028).
- **Values:** `Mesangial Fraction` and `Luminal Fraction` raw. `Average TBM Thickness`, `Average Cell Thickness`, `Area`, `Mesangial Area` and `Arterial Area` are log-transformed, keeping only positive values. Each is centred on its slide median over all objects of the sheet, so agreement is measured within slides.
- **Agreement:** Spearman rho between the two members, pooled over all pairs on all repeat slides (rho_twin), and the same for null pairs (rho_null). **Uncertainty:** 200 slide-level bootstrap resamples (seed 20261028) of rho_twin - rho_null; the 95% interval uses the 2.5th and 97.5th percentiles.
- **Zero TBM:** over tubule twin pairs with both TBM values present, a 2 x 2 table (i <= 0 or > 0, j <= 0 or > 0) and its concordance odds ratio, with 0.5 added to every cell. The same for null pairs.

## Gates

- **Detector check:** every grade waits for the twins census's positive-control check T3. If T3 is anything but pass, the detector is not validated, and every grade here is **untestable**. The job re-runs the census (identical code, data and seed) to read T3. If the zero-TBM job `kpmp-tbm0-v2` also runs the census, the two results should be identical; any difference will be reported.
- At least 10 repeat slides; otherwise all grades are untestable.
- Per feature: at least 100 twin pairs with both values for glomeruli, and 500 for tubules; otherwise that grade is untestable. R5 needs at least 50 twin pairs with a zero in either member.

## Predictions

A feature passes if **rho_twin >= 0.30 and the lower 95% bound of rho_twin - rho_null >= 0.10**.

| | Feature (sheet) | Prediction |
|---|---|---|
| R1 | Mesangial fraction (glomeruli) | pass |
| R2 | Average TBM thickness (tubules) | pass (least sure) |
| R3 | Luminal fraction (tubules) | pass (most sure) |
| R4 | Average cell thickness (tubules) | pass |
| R5 | Zero TBM is concordant between twins: odds ratio (twin) >= 2 x odds ratio (null) | pass (low confidence) |

Why: the visual check saw repeated tubules with the same dilated lumen in both sections (R3). Glomerular features passed clinical controls (R1). TBM thickness behaves plausibly in its medians (about 1.3-1.4 microns) even though it misses the pathologists' scores, so we expect it to be reproducible per object but are unsure (R2). Zero TBM may come from tubules whose appearance defeats the measurement, which would follow the object (R5), but per-section failure is just as plausible.

**Readings fixed in advance:**
- **R2 fail, R3 pass:** the same tubule is matched (its lumen reproduces), but its TBM thickness does not. Per-object TBM is mostly measurement noise, which is enough to explain its failure against atrophy and eGFR. The Kidney AI entry will not use it.
- **R2 pass:** per-object TBM is reproducible, so its failures lie in how it is summarised (medians over all tubules, zero rows) or in what it measures, not in random per-object noise.
- **R3 fail:** either the pairing mixes different tubules or luminal fraction itself is unstable. R2 and R4 then cannot be read as reliability, whatever their grades.
- **R5 pass:** zero TBM follows the object, so dropping zero rows removes particular tubules and can bias summaries. **R5 fail:** zero TBM is per-section failure, and dropping those rows is safe.
- Size features (`Area`, `Mesangial Area`, `Arterial Area`) are reported, not graded, because twins are matched on box size and their agreement is partly built in.

**Descriptive (not graded):** rho_twin, rho_null and the bootstrap interval for every feature in every sheet (including sclerotic glomeruli); pairs, null pairs and objects per sheet; the zero-TBM tables.

## Outputs and privacy

`results.json` holds aggregates only, without package IDs. The census's `slides.json` and `twin-controls.json` name packages and stay with the job. No image is used.

## Limits

- Serial sections are a few microns apart, so twins are close replicates, not identical. Real biological change between sections (for example, a tubule that narrows) lowers agreement, so rho_twin is a lower bound on measurement reliability.
- Twins come only from slides where the detector finds a repeat, and only from the dominant offset. Pairs are matched on size, which may favour objects that segment consistently.
- Pooling over slides weights slides with many pairs more heavily; the slide-level bootstrap accounts for clustering in the interval, not in the point estimate.
- One model family wrote, tests and will grade this; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-twins-prereg-v1-2026-10-28.md`, `kpmp-patches-results-v1-2026-10-28.md`, `kpmp-objects-results-v1-2026-10-28.md`, `kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md` (this folder)
- FUSION: a web-based application for in-depth exploration of multi-omics data with brightfield histology, Nature Communications 2025, https://www.nature.com/articles/s41467-025-63050-9
- Keller et al. 2025, Interactive visualization of kidney micro-compartmental segmentations and associated pathomics on whole slide images, arXiv 2510.19499
- Pathomic analysis of 5-year surveillance biopsies as predictors of kidney allograft loss, American Journal of Transplantation 2026, https://www.amjtransplant.org/article/S1600-6135(26)00994-9/fulltext
- Radiomics feature reproducibility under inter-rater variability in segmentations of CT images, Scientific Reports 2020, https://www.nature.com/articles/s41598-020-69534-6
