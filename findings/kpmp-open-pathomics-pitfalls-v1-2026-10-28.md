# Ten pitfalls in KPMP's open segmentation and pathomics files, and how to handle them (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

This page gathers, in one place, what our census passes, clinical checks, object audit and visual check found about the Kidney Precision Medicine Project's (KPMP) open "Segmentation Masks & Pathomics Vectors" packages (361 in the Atlas Repository file list of 2026-10-18). It is meant for anyone who analyses these files, including entrants to NIDDK's Kidney AI Discovery Challenge. Each item says how sure we are:

- **Graded:** a pre-registered prediction, graded exactly as written in the linked results note.
- **Observed:** seen in our job outputs or images, but not predicted in advance.
- **Pending:** a pre-registered check that has not run yet.

Every number here comes from the linked notes in this folder; nothing new was computed for this page.

## The ten pitfalls

| # | Pitfall | Status | What to do |
|---|---|---|---|
| 1 | Two incompatible layouts | Observed | Branch on version; match columns by name |
| 2 | The README's units are wrong for v1 | Graded | Treat both versions as pixels |
| 3 | No pixel size inside the packages | Graded | Read each slide's scanner MPP |
| 4 | v2 box `x` is the image row | Observed | Read `x` as row, `y` as column |
| 5 | Serial sections: one object, two rows | Observed; prevalence pending | Do not treat rows as independent |
| 6 | One in ten v2 tubules has TBM thickness <= 0 | Observed; effect pending | Count non-positive values before summarising |
| 7 | Tubule summary features miss the pathologists' scores | Graded | Do not rest a claim on tubule medians |
| 8 | Glomerular features do recover clinical gradients | Graded | Usable, with versions kept apart or both read as pixels |
| 9 | The most extreme objects include segmentation output | Observed | Filter shape, look at the image, use per-slide quantiles |
| 10 | The pathologist score file and three packages | Observed | Use the October 2026 score release; expect 358 of 361 |

## Details

**1. Two layouts.** 220 packages are "v2": one workbook with sheets `gloms`, `s_gloms`, `tubs` and `arts`, and an IFTA mask layer. 138 are "v1": 2-4 workbooks, one per compartment (515 in all), each with sheets `Bounding Boxes` and `Features`, about 77-78 columns, no IFTA layer, and a different README. Column order differs across 3-4 header variants per compartment, so match columns by exact name, not by position. No participant has packages of both versions. Two reader errors of our own came from assuming names instead of recording them: pass 1 missed the v1 layout, and pass 2 looked for a lower-cased sheet name that does not exist. Record every raw sheet name and header before analysing. (`kpmp-census-results-v1-2026-10-27.md`, `-v2-`, `-v3-2026-10-28.md`)

**2. Units.** The README says v2 measurements are in pixels and others in microns. In every one of the 131 v1 packages with a glomerulus workbook, `Area` equals `Area (pixel^2)` row for row (median ratio exactly 1.0), and raw v1 and v2 medians agree within 16% for tuft area, TBM thickness, cell thickness and luminal fraction. Both versions are in pixels. Converting v2 alone, as the README implies, makes v1 glomeruli look about 14 times larger than v2's. It also erases two textbook signals: glomerular tuft area against diabetes falls from Spearman rho +0.231 (versions kept apart) to +0.037, and against proteinuria from +0.224 to +0.042. (`kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md`)

**3. Pixel size.** No package's OME-XML gives one. The slides' Aperio scanner metadata does: 0.2527 microns per pixel on all 20 sampled v2 slides; 16 of 20 sampled v1 slides at 0.2527 and 4 at about 0.263. Convert each slide with its own value. Read as pixels at 0.2527 microns, median tuft area is about 22,800 (v1) and 26,300 (v2) square microns and median TBM about 1.3-1.4 microns. (`kpmp-census-results-v2-2026-10-27.md`, `-v3-`)

**4. Box axes (v2).** Boxes are given as `x1 | x2 | y1 | y2`, and the README does not name the axes. For 30 checked boxes on 14 v2 slides, reading `x` as the image row puts all 30 inside the slide, each framing a structure of the right kind. Reading `x` as the column puts 14 off the slide, and the in-slide crops we checked show glass or the wrong tissue, with no error to warn you. v1 boxes were not checked. (`kpmp-patches-results-v1-2026-10-28.md`)

**5. Serial sections.** A slide carries two or more serial sections of the same biopsy core, and every section was segmented, with no column saying which section a row is from. Among the 30 most extreme objects, 12 were 6 pairs of the same tubule or artery seen once in each section, with a consistent shift between copies. So per-slide counts can be inflated, an outlier list can name one structure twice, and per-object samples are not independent. How common this is across all 220 v2 slides is pre-registered (`kpmp-twins-prereg-v1-2026-10-28.md`: T1 share of slides with a repeated section, T2 share of glomeruli with a twin, T3 five positive controls) and waiting for compute.

**6. Zero TBM.** 52,004 of 518,756 v2 tubule rows (10.0%) have an `Average TBM Thickness` of zero or less. The README does not mention it. Participant medians include these rows unless you drop them. Whether dropping them changes the tests in item 7 is pre-registered (`kpmp-tbm0-prereg-v1-2026-10-28.md`, Z1-Z8) and waiting for compute. (`kpmp-objects-results-v1-2026-10-28.md`)

**7. Tubule features vs pathologists.** Participant medians of TBM thickness, cell thickness and luminal fraction did not track the KPMP pathologists' consensus atrophy, injury or abnormal-lumen percentages: v2 medians in pass 2 (rho 0.06, -0.01, +0.16), v1 medians and v2 90th/10th percentiles in pass 3 (all |rho| <= 0.19, every Holm-adjusted p 1.0). TBM thickness also did not track baseline eGFR (rho -0.036, n 247). (`kpmp-census-results-v2-2026-10-27.md`, `-v3-`, `kpmp-q2-results-v1-2026-10-28.md`)

**8. Glomerular features work.** With versions kept apart, four of five pre-registered clinical controls held: tuft area with diabetes (rho +0.231) and with proteinuria (+0.224), mesangial fraction with diabetes (+0.138), and share of globally sclerotic glomeruli against baseline eGFR (-0.345). A split-half discovery stage confirmed one further pair, sclerotic share with hypertension history, which is textbook, not new. (`kpmp-q2-results-v1-2026-10-28.md`)

**9. Extremes.** The v2 rows are internally clean (valid boxes, areas within boxes, mesangial fraction exactly mesangial area / area, no duplicate rows). But a pooled outlier screen finds slides, not objects: 81% of pooled tubule outliers are ordinary within their own slide. Outlier glomeruli are about 7 times as likely as others to be misshapen. A robust z-score with the median absolute deviation blows up on zero-heavy fractions such as luminal fraction (ordinary open lumens scored z over 100). In an AI visual triage of the 30 most extreme objects (not a pathologist's reading), 22 looked like plausible objects of the labelled kind, 3 were another kind (including a 4-pixel "artery"), 3 were artefacts (tissue tears, a detached fragment) and 2 were unclear. (`kpmp-objects-results-v1-2026-10-28.md`, `kpmp-patches-results-v1-2026-10-28.md`)

**10. Score file and missing packages.** The pathologists' descriptor scores now come as "KPMP TIV Descriptor Scores 10.12.2026.xlsx": 426 participants, one row each, 155 descriptor columns in the sheet "Data Table". 227 of the 247 participants with an analysed segmentation package have a score row. Three v1 segmentation packages returned HTTP 500 on every attempt in October 2026, so expect 358 of 361. (`kpmp-census-results-v2-2026-10-27.md`)

## Code

All in `../kidney/` (Apache-2.0, Python standard library only, with offline tests): `kpmp_census.py`, `kpmp_census2.py` and `kpmp_census3.py` (readers for both layouts, raw sheet names, scanner MPP), `kpmp_q2.py` (clinical controls), `kpmp_objects.py` (object audit), `kpmp_patches.py` (crops, both axis readings), `kpmp_fill.py` (fills a local cache with HTTP range reads of the small zip members), `kpmp_tbm0.py` and `kpmp_twins.py` (the two pending checks). The code downloads from the KPMP Atlas itself; we never re-host KPMP files, and image crops, package IDs, box positions and per-participant values stay private.

## Limits

- One model family wrote the code, ran the analyses and wrote this page; no human has reviewed any of it.
- Items 4, 5 and 9 rest on 30 extreme objects from 14 slides, chosen as extremes, not at random.
- KPMP may revise its files or README at any time; everything here describes the Repository as downloaded on 2026-10-18 to 2026-10-28.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.
