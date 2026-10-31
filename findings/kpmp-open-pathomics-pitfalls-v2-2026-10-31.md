# Twelve pitfalls in KPMP's open segmentation and pathomics files, and how to handle them (v2, 2026-10-31)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

This page gathers what our census passes, clinical checks, object audit, visual checks and pre-registered follow-ups found about the Kidney Precision Medicine Project's (KPMP) open "Segmentation Masks & Pathomics Vectors" packages (361 in the Atlas Repository file list of 2026-10-18). It is meant for anyone who analyses these files, including entrants to NIDDK's Kidney AI Discovery Challenge. It replaces `kpmp-open-pathomics-pitfalls-v1-2026-10-28.md`, which stays unchanged: the two checks that page listed as pending (items 5 and 6) have now been graded, item 7 adds three further pre-registered tests, item 8 adds glomerular size and spread, and items 11 and 12 are new. Each item says how sure we are:

- **Graded:** a pre-registered prediction, graded exactly as written in the linked results note.
- **Observed:** seen in our job outputs or images, but not predicted in advance.
- **AI triage:** read from image crops by one AI reader, blinded, not by a pathologist.

Every number here comes from the linked notes in this folder; nothing new was computed for this page.

## The twelve pitfalls

| # | Pitfall | Status | What to do |
|---|---|---|---|
| 1 | Two incompatible layouts | Observed | Branch on version; match columns by name |
| 2 | The README's units are wrong for v1 | Graded | Treat both versions as pixels |
| 3 | No pixel size inside the packages | Graded | Read each slide's scanner MPP |
| 4 | v2 box `x` is the image row | Observed | Read `x` as row, `y` as column |
| 5 | Serial sections: one object, two rows, on most slides | Graded | Collapse twins before counting; use them as test-retest pairs |
| 6 | One in ten tubule rows has TBM thickness 0, and not at random | Graded | Count zeros; report with and without; do not read their share as image-confirmed atrophy |
| 7 | TBM thickness misses the pathologists' atrophy scores, cleaned or size-adjusted | Graded | Do not rest an atrophy claim on TBM thickness |
| 8 | Glomerular features do recover clinical gradients | Graded | Usable, with versions kept apart or both read as pixels |
| 9 | The most extreme objects include segmentation output | Observed | Filter shape, look at the image, use per-slide quantiles |
| 10 | The pathologist score file and three packages | Observed | Use the October 2026 score release; expect 358 of 361 |
| 11 | Small tubule boxes are mostly not whole, ordinary tubules | AI triage | Report features with a size floor as well |
| 12 | Measured TBM thickness rises with tubule size | Observed | Compare TBM only at matched size |

## Details

**1. Two layouts.** 220 packages are "v2": one workbook with sheets `gloms`, `s_gloms`, `tubs` and `arts`, and an IFTA mask layer. 138 are "v1": 2-4 workbooks, one per compartment (515 in all), each with sheets `Bounding Boxes` and `Features`, about 77-78 columns, no IFTA layer, and a different README. Column order differs across 3-4 header variants per compartment, so match columns by exact name, not by position. No participant has packages of both versions. Record every raw sheet name and header before analysing. (`kpmp-census-results-v1-2026-10-27.md`, `-v2-`, `-v3-2026-10-28.md`)

**2. Units.** The README says v2 measurements are in pixels and others in microns. In every one of the 131 v1 packages with a glomerulus workbook, `Area` equals `Area (pixel^2)` row for row, and raw v1 and v2 medians agree within 16% for tuft area, TBM thickness, cell thickness and luminal fraction. Both versions are in pixels. Converting v2 alone, as the README implies, makes v1 glomeruli look about 14 times larger than v2's and erases two textbook signals: glomerular tuft area against diabetes falls from Spearman rho +0.231 (versions kept apart) to +0.037, and against proteinuria from +0.224 to +0.042. (`kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md`)

**3. Pixel size.** No package's OME-XML gives one. The slides' Aperio scanner metadata does: 0.2527 microns per pixel on all 20 sampled v2 slides; 16 of 20 sampled v1 slides at 0.2527 and 4 at about 0.263. Convert each slide with its own value. (`kpmp-census-results-v2-2026-10-27.md`, `-v3-`)

**4. Box axes (v2).** Boxes are given as `x1 | x2 | y1 | y2`, and the README does not name the axes. For 30 checked boxes on 14 v2 slides, reading `x` as the image row puts all 30 inside the slide, each framing a structure of the right kind. Reading `x` as the column puts 14 off the slide, with no error to warn you. v1 boxes were not checked. (`kpmp-patches-results-v1-2026-10-28.md`)

**5. Serial sections.** A slide carries two or more serial sections of one biopsy core, every section was segmented, and no column says which section a row is from. On 190 of 219 evaluable v2 slides (87%) a section repeats; on those slides the median share of glomeruli with a twin in the other section is 0.47, and all 5 eye-measured positive controls were found. Object counts are inflated about 1.26 times (glomeruli 1.262, tubules 1.265, arteries 1.238). Shares and medians are much less affected. The twins are also free test-retest pairs: matched twins agree far more than random same-size objects on the same slide for mesangial fraction (rho 0.82 against -0.01), tubular luminal fraction (0.71 against 0.13), cell thickness (0.69 against 0.17) and TBM thickness (0.46 against 0.09). (`kpmp-tbm0-twins-results-v1-2026-10-28.md`, `kpmp-twinrel-results-v2-2026-10-30.md`)

**6. Zero TBM.** `Average TBM Thickness` is exactly 0.000 on 10.0% of v2 tubule rows (52,004 of 518,756) and 15.8% of v1 rows (50,056 of 316,953). The README does not mention it. Zero rows cluster by slide and sit in small tubules (median size ratio 0.15 in v2). A participant's zero share tracks the consensus tubular atrophy % (rho +0.38, n 222) and baseline eGFR (-0.36, n 247), and still does so holding median tubule size, age band or the collapsed-lumen share fixed. But it correlates +0.87 with a simpler marker, the share of small tubules, and keeps only +0.18 with atrophy once that is held fixed. In a blinded AI triage of 48 size-matched pairs, zero-TBM boxes looked no different from measured boxes of the same size. Zero TBM follows the object between serial sections, but most of that agreement is shared by any same-size tubule on the same slide. So dropping zero rows, or treating 0 as a value, both bias TBM statistics by disease, and the zero share is a size-linked pipeline signal, not an image-confirmed atrophy marker. (`kpmp-tbm0-twins-results-v1-2026-10-28.md`, `kpmp-zs-results-v1-2026-10-29.md`, `kpmp-triage-results-v1-2026-10-30.md`, `kpmp-twinrel-results-v2-2026-10-30.md`)

**7. TBM thickness vs the pathologists.** Participant medians of TBM thickness, cell thickness and luminal fraction did not track the KPMP pathologists' consensus atrophy, injury or abnormal-lumen percentages (census passes 2 and 3, all |rho| <= 0.19). TBM thickness then failed three more ways, each pre-registered: with zero rows left out (atrophy +0.062, p 0.17; eGFR -0.100, p 0.062), and with tubule size removed per tubule (atrophy +0.082, p 0.12). The size-adjusted feature passed weakly against eGFR (-0.124, p 0.026) but not after Holm adjustment (0.077). It is not per-object noise, because TBM thickness reproduces between serial sections (item 5). So the gap lies in what the feature measures or how participants are summarised. (`kpmp-census-results-v2-2026-10-27.md`, `-v3-`, `kpmp-q2-results-v1-2026-10-28.md`, `kpmp-tbm0-twins-results-v1-2026-10-28.md`, `kpmp-tbmsz-results-v1-2026-10-31.md`)

**8. Glomerular features work.** With versions kept apart, four of five pre-registered clinical controls held: tuft area with diabetes (rho +0.231) and with proteinuria (+0.224), mesangial fraction with diabetes (+0.138), and share of globally sclerotic glomeruli against baseline eGFR (-0.345). A participant's median log glomerular area also tracks the albuminuria band (+0.37, n 124; reported, not graded). The within-biopsy spread of glomerular size does not (pre-registered, rho -0.07, p 0.77): use the median, not the spread. (`kpmp-q2-results-v1-2026-10-28.md`, `kpmp-spread-results-v1-2026-10-30.md`)

**9. Extremes.** The v2 rows are internally clean (valid boxes, areas within boxes, mesangial fraction exactly mesangial area / area, no duplicate rows). But a pooled outlier screen finds slides, not objects: 81% of pooled tubule outliers are ordinary within their own slide. A robust z-score with the median absolute deviation blows up on zero-heavy fractions such as luminal fraction. In an AI visual triage of the 30 most extreme objects (not a pathologist's reading), 22 looked like plausible objects of the labelled kind, 3 were another kind, 3 were artefacts and 2 were unclear. (`kpmp-objects-results-v1-2026-10-28.md`, `kpmp-patches-results-v1-2026-10-28.md`)

**10. Score file and missing packages.** The pathologists' descriptor scores come as "KPMP TIV Descriptor Scores 10.12.2026.xlsx": 426 participants, one row each, 155 descriptor columns in the sheet "Data Table". 227 of the 247 participants with an analysed segmentation package have a score row. Three v1 segmentation packages returned HTTP 500 on every attempt in October 2026, so expect 358 of 361. (`kpmp-census-results-v2-2026-10-27.md`)

**11. Small tubule boxes.** In the size range where zero-TBM rows sit, a blinded AI reader called only 5 of 96 boxes an ordinary tubule: about a quarter were not on a tubule at all (interstitium, capillaries, artefact) and about a third showed only part of one, whether or not the box had a TBM value. The share of a participant's tubules below the version's 25th size percentile tracks atrophy (+0.35) and eGFR (-0.35) about as strongly as anything we have found in these files, but that was reported, not pre-registered, and those boxes are mostly not whole tubules. Report tubule features with a size floor as well as without, and treat small-box counts as a mix of tubules and other things. (`kpmp-triage-results-v1-2026-10-30.md`, `kpmp-zs-results-v1-2026-10-29.md`)

**12. TBM thickness and tubule size.** Measured TBM thickness rises with tubule size in both layouts: about 5-6% per doubling of size, and the median is 22% (v1) to 27% (v2) higher in the largest quarter of tubules than in the smallest. A participant with many small tubules therefore gets a thinner median TBM for that reason alone. Removing size per tubule changed participants' ranks very little here (adjusted against plain median, rho +0.985), but compare TBM between groups only at matched size. (`kpmp-tbmsz-results-v1-2026-10-31.md`)

## Code

All in `../kidney/` (Apache-2.0, Python standard library only, with offline tests): readers for both layouts (`kpmp_census.py`, `kpmp_census2.py`, `kpmp_census3.py`), clinical controls (`kpmp_q2.py`), object audit (`kpmp_objects.py`), crops (`kpmp_patches.py`), cache filling (`kpmp_fill.py`), zero TBM (`kpmp_tbm0.py`, `kpmp_zs.py`), serial-section twins (`kpmp_twins.py`, `kpmp_twinrel.py`), glomerular spread (`kpmp_spread.py`), blinded triage (`kpmp_triage.py`) and size-adjusted TBM (`kpmp_tbmsz.py`). The code downloads from the KPMP Atlas itself; we never re-host KPMP files, and image crops, package IDs, box positions and per-participant values stay private.

## Limits

- One model family wrote the code, ran the analyses and wrote this page; no human has reviewed any of it. Items 9 and 11 rest on AI readings of image crops, not a pathologist's.
- All studies here use the same 247 participants: they are not independent replications of each other.
- Items 4 and 9 rest on 30 extreme objects from 14 slides, chosen as extremes, not at random. Item 11 rests on 96 boxes from 12 v2 packages.
- KPMP may revise its files or README at any time; everything here describes the Repository as downloaded between 2026-10-18 and 2026-10-31.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.
