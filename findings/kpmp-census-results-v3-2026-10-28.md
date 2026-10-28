# Results: KPMP segmentation census, pass 3 (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-census-prereg-v3-2026-10-27.md` (tag v0.9.14). Code: `../kidney/kpmp_census3.py` 3.0 on `../kidney/kpmp_census2.py` 2.0 and `../kidney/kpmp_census.py` 1.0, all unchanged since that tag. Job `kpmp-census3-v1`: python:3.12 container, 2 CPUs, 2 GB memory cap (peak 0.74 GB). It started 2026-10-27 23:33 UTC and finished at 23:55 UTC. The 51 offline tests passed in the container first. The census read the cached packages (nothing downloaded again) and took 16.4 minutes.

## Headline

**KPMP's older (v1) pathomics files are in pixels, not microns.** The README inside the segmentation packages says v2 measurements are in pixels and, otherwise, in microns. In every one of the 131 v1 packages with a glomerulus workbook, the median row ratio of `Area` to `Area (pixel^2)` is exactly 1.0. v1 and v2 medians agree in raw values (ratios 0.95-1.16), and both match the scanner's pixel size only when both are read as pixels. Anyone who follows the README and converts only v2 makes v1 glomeruli look about 14 times larger and v1 basement membranes about 4 times thicker than v2's. Our clinical check (`kpmp-q2-results-v1-2026-10-28.md`) shows that this conversion erases the textbook link between diabetes and glomerular size.

## Grades, exactly as pre-registered

The 95% gate was met: 358 of 361 packages analysed (the same three v1 packages answer HTTP 500). This time the reader found the v1 sheet: 515 v1 workbooks, each with the sheets `Bounding Boxes` and `Features`.

| | Prediction | Grade | Numbers |
|---|---|---|---|
| S1 scanner pixel size | pass | **pass** | 40 of 40 sampled slides give an Aperio MPP; median 0.2527, max/min 1.04 (pass 2's grade stands) |
| U1 v1 `Area` in square microns: median `Area` / `Area (pixel^2)` in [0.04, 0.10] | pass | **fail** | 1.0 in all 131 packages (min = median = max = 1.0) |
| U2 one pixel scale: v2 `Area` / v1 `Area (pixel^2)` in [0.5, 2.0] | pass | **pass** | 1.145 (v2 411,918 vs v1 359,791 square pixels, medians of package medians) |
| U3 implied and scanner pixel size within 10% | pass | **fail** | implied 1.0 vs scanner 0.2527 |
| P2 TBM thickness v2/v1 raw >= 2.0 | pass | **fail** | 0.951 (v2 5.16 vs v1 5.43) |
| P3 the same, v2 converted, in [0.67, 1.5] | pass | **fail** | 0.240 |
| P4 glomerular area v2/v1 raw >= 4.0 | pass | **fail** | 1.155 (v2 411,918 vs v1 356,568) |
| P5 the same, v2 converted, in [0.5, 2.0] | pass | **fail** | 0.074 |
| V7 luminal fraction vs abnormal luminal morphology %, v1 participants, rho > 0 | fail | **fail** | rho -0.039, one-sided p 0.66, n 117 |
| V8 TBM thickness vs tubular atrophy %, v1, rho > 0 | fail | **fail** | rho +0.004, p 0.48, n 117 |
| V9 cell thickness vs tubular injury other %, v1, rho < 0 | fail | **fail** | rho +0.016, p 0.56, n 117 |
| T7 90th percentile of luminal fraction vs abnormal lumen %, v2, rho > 0 | pass (low confidence) | **fail** | rho +0.012, p 0.46, n 105 |
| T8 90th percentile of TBM thickness vs atrophy %, v2, rho > 0 | pass | **fail** | rho +0.007, p 0.48, n 105 |
| T9 10th percentile of cell thickness vs injury other %, v2, rho < 0 | fail | **fail** | rho +0.190, p 0.97, n 106 |

Holm adjustment over the six agreement tests (V7-V9, T7-T9), worked out by hand from the job's p-values: the smallest p is 0.456, so every adjusted p is 1.0.

Score: 4 of the 6 agreement predictions held (V7-V9 and T9 fail as predicted; T7 and T8 did not pass). Of the 8 unit checks, only S1 and U2 held. The unit predictions all assumed the README was right, and the pre-registration named this exact outcome: "U1 fails with a ratio near 1: v1 `Area` is in pixels, so the README's v1 unit claim fails for areas."

## What the numbers say

1. **Both versions are in pixels.** Three independent lines agree. (a) Inside v1 files, `Area` equals `Area (pixel^2)`. (b) Raw v1 and v2 medians agree within 16% for TBM thickness (0.95), cell thickness (1.07), luminal fraction (1.09, unitless) and glomerular area (1.16). If v1 were in microns and v2 in pixels at 0.2527 microns, lengths would differ about 4-fold and areas about 16-fold. (c) Read as pixels at 0.2527 microns, the medians are biologically plausible: glomerular tuft area about 22,800 (v1) and 26,300 (v2) square microns, TBM about 1.4 and 1.3 microns, tubular cell height about 7.1 and 7.6 microns. Read as microns, v1 tufts would be about 0.36 square millimetres and tubular cells 28 microns tall. The object audit (`kpmp-objects-results-v1-2026-10-28.md`) adds a fourth line for v2: glomerular areas fill a median 0.76 of their pixel bounding boxes.
2. **The tubule vectors do not track the consensus pathologists' tubular percentages, in either layout or in the tails.** Pass 2 found this for v2 medians; pass 3 finds it for v1 medians (V7-V9) and for v2 tails (T7-T9). Pooled over both versions (reported, not graded, because v2 had been seen): luminal fraction rho +0.019 (n 222), TBM thickness -0.021 raw, cell thickness +0.060 raw. As pre-registered, the Kidney AI entry will not rest a discovery on these tubule vectors as summarised here.
3. **Reported, not predicted:** D1 TBM thickness vs cortical interstitial fibrosis %: pooled raw rho -0.083 (n 221), v1 -0.054, v2 -0.094. The v1 workbooks carry about 75 image features per object (distance transforms, colour and texture statistics of nuclei, eosinophilic and luminal space, shape) plus compartment columns: tubules add `In Medulla`, `Average TBM Thickness`, `Average Cell Thickness` and `Luminal Fraction`; glomeruli carry both `Area (pixel^2)` and `Area`, `Mesangial Area`, `Mesangial Fraction`; arteries carry `Area (pixel^2)` and `Arterial Area`. Column order differs across 3-4 header variants per compartment, so columns must be matched by name, not position. No v1 package has an IFTA mask layer and every v2 package does.

A possible reason for finding 2, from the object audit and not yet tested: 10.0% of v2 tubule rows (52,004 of 518,756) have a TBM thickness of zero or less, and every participant median here includes them.

## What this changes

- **For anyone using KPMP pathomics vectors:** treat v1 and v2 `Area`, `Arterial Area`, `Average TBM Thickness` and `Average Cell Thickness` as pixels, and convert both versions with each slide's own scanner MPP (0.2527 microns for all 20 sampled v2 slides; 16 of 20 sampled v1 slides at 0.2527 and 4 at about 0.263). Do not convert v2 alone.
- **For question 2:** its conversion rule pooled converted values only if P3 and P5 passed. They failed, so the glomerular-area and TBM controls were graded on the version-stratified statistic, as written.
- **For KPMP:** the README's unit sentence for non-v2 files looks wrong for these columns. We have not contacted KPMP. That needs Sheehan's approval and a human check of this note first.

## Limits

- One model family wrote the code and graded it; no human has reviewed it.
- Package medians are medians over objects, so a minority of odd rows (such as zero TBM) can shift them without showing up here.
- `results.json` stays local because it holds per-package feature medians, which are KPMP data. Only the aggregates above are published.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-census-prereg-v3-2026-10-27.md`, `kpmp-census-prereg-v2-2026-10-27.md`, `kpmp-census-results-v2-2026-10-27.md`, `kpmp-census-prereg-v1-2026-10-26.md` (this folder)
- Job output `compete-results/kpmp-census3-v1/` (local; aggregates quoted above)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
