# Results: can a small CPU sandbox fetch and read open KPMP kidney biopsy slides? (feasibility v1, run 2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody at KPMP, NIH or HeroX has been contacted.

Pre-registration: `kpmp-feasibility-prereg-v1-2026-10-18.md` (release v0.4.34). Code: `../kidney/kpmp_feasibility.py` v1.0 as committed there; the fix described below is v1.1 in this release. Job: `kpmp-feasibility-v1`, python:3.12 container, 2 CPUs, 3 GB memory cap, network on, queued 04:44 UTC, started 08:37:38 UTC, finished 08:46:40 UTC (541 s including package installation). All 27 offline tests passed in the container before the run. Versions: Python 3.12.15, tifffile 2026.10.15, imagecodecs 2026.10.10, numpy 2.5.4. The job reported 0 errors.

**Short version.** Five of six predictions held. The sixth, P4 (a mask lines up with the slide), was scored "fail" by our code, so the pre-registered rule gives the overall verdict **"not shown feasible"**. The cause is ours, not the data's: the mask file has seven planes, one per structure type, and our shape reader accepted at most four leading planes, so it never compared the mask's size with the slide's. By hand the mask is exactly the slide's full-resolution size (factor 1). The pre-registration says a failure caused by us is to be fixed; v1.1 fixes it, and a second run is queued with its expected outcome written below. We do not re-score run v1.

## 1. Verdict as scored by the pre-registered code

| Prediction | Rule (short) | Predicted | Measured | Scored |
|---|---|---|---|---|
| P1 access | `seg_small`, `pas_small`, `tiv` download without sign-in, within 2% of listed size | pass | all three, 0.1% or less off the listed size, HTTP 200, 1 try each | **pass** |
| P2 small slide | opens; low level < 60 s; >= 1 tile decoded; peak memory < 1,536 MB | pass | 0.33 s, 64 tiles, 202.6 MB | **pass** |
| P3 large slide | downloads within 2%; opens; low level reads; >= 1 tile; peak memory < 2,560 MB; download + read <= 60 min | pass (least confident) | 2,374,806,599 bytes (listed 2.37 GB), 1.14 s, 64 tiles, 383.3 MB, 3.5 min | **pass** |
| P4 mask alignment | at least one `tif` in `seg_small` lines up with `pas_small` at a factor in 1, 2, 4 ... 64 | pass | mask (7, 17750, 15943); slide (17750, 15943, 3); code computed no factor | **fail** (see section 2) |
| P5 TIV coverage | 335 to 345 distinct participant IDs | pass | 340 | **pass** |
| P6 package holds the slide | an `svs` in `seg_small` within 1% of `pas_small`'s size | pass | the member is 11,214,335 bytes, the same as `pas_small`, and its SHA-256 matches | **pass** |

Overall, by the rule "feasible if P1-P4 pass; feasible for small slides only if P1, P2, P4 pass; otherwise not shown feasible": **not shown feasible**.

## 2. Why P4 failed: our code, not the data

The package's mask `S-1904-008128_PAS_2of2.ome.tif` is a pyramidal OME-TIFF with shape (7, 17750, 15943), data type uint16, 6 pyramid levels, 14,598,037 bytes. Its OME-XML lists 7 `Channel` elements, and the package README says each layer holds one tissue unit or structure type, with each segmented unit a unique integer. The slide's full-resolution level is 17750 x 15943 x 3.

`hw_of()` in v1.0 returned (height, width) for shapes (h, w), (h, w, c) or (c, h, w) only when c <= 4. For (7, 17750, 15943) it returned None, so `aligned()` was never called and the mask's `factor` stayed None, which the verdict code reads as "does not line up". The mask was also not pixel-counted, because 17750 x 15943 = 283 million pixels is above the 200 million cap (AI arithmetic).

Hand check against the pre-registration's wording: 17750 = 17750 and 15943 = 15943, so the mask lines up at factor 1. The prediction was right about the data and wrong about our code. Per section 5 of the pre-registration ("report why, and fix the cause only if it is ours"):

- **v1.1** raises the leading-plane limit to 16 (`MAX_PLANES`); nothing else in the verdict path changes. `kidney/test_hw_of_v11.py` pins the measured shapes: `hw_of((7, 17750, 15943))` is (17750, 15943) and it aligns with (17750, 15943, 3) at factor 1. The 27 v1 tests still pass unchanged.
- **Run v2** (`kpmp-feasibility-v2`) is queued with the same four files and v1.1. **Expected, written before it runs:** P1 to P6 pass and overall "feasible"; `seg_small`, `pas_small` and `tiv` come from the job cache (`cached: true`, 0 s); `pas_large` downloads again, because v1 deleted it after measuring, at a speed that may differ from v1's. The job asks for 1 GB instead of 3 GB, because v1's peak was 383 MB; this makes the memory conditions stricter, not looser.
- v1.1 also adds one measurement that is not part of P1-P6 and does not enter any verdict: an HTTP Range probe on `seg_small`'s URL (first 1,024 bytes). If the server answers 206, a later study can read a package's small feature table from the zip without downloading the slide inside it (section 5).

## 3. Measurements

### Downloads

| Key | File | Listed | Bytes received | Seconds | Content-Type |
|---|---|---|---|---|---|
| seg_small | `..._S-1904-008128_Seg_Masks_Features_v2.zip` | 11.8 MB | 11,806,912 | 1.3 | application/octet-stream |
| pas_small | `..._S-1904-008128_PAS_2of2.svs` | 11.2 MB | 11,214,335 | 1.0 | application/octet-stream |
| tiv | `..._KPMP TIV Descriptor Scores 02.19.2026.xlsx` | 357 kB | 357,225 | 0.4 | application/octet-stream |
| pas_large | `..._S-2104-019032_PAS_1of2.svs` | 2.37 GB | 2,374,806,599 | 204.1 | application/octet-stream |

The large slide came at about 11.6 MB/s (2,374,806,599 bytes / 204.1 s; AI arithmetic). No sign-in, no redirect, no rate limit was met.

### Slides

| | pas_small | pas_large |
|---|---|---|
| TIFF pages | 6 | 7 |
| Level 0 (h, w, c) | 17750, 15943, 3 | 69578, 153460, 3 |
| Pyramid levels | 3 (17750x15943, 4437x3985, 2218x1992) | 4 (69578x153460, 17394x38365, 4348x9591, 1087x2397) |
| Level-0 compression (TIFF code) | 33003 (Aperio JPEG 2000 YCbCr) | 33005 (Aperio JPEG 2000 RGB) |
| Microns per pixel, magnification | 0.2527, 40x | 0.2527, 40x |
| Scanner description | Aperio Image Library v12.0.16, scanned 2020-10-07 | Aperio Image Library v12.0.16, scanned 2021-10-26 |
| Level read for the tissue estimate | level 1, 4437x3985, 0.33 s | level 2, 4348x9591, 1.14 s |
| Share of coloured (tissue) pixels at that level | 0.0728 | 0.0825 |
| Tile size, tiles at level 0 | 240x240, 4,958 | 240x240, 185,600 |
| Tiles decoded (8x8 grid), ms per tile | 64, 4.72 | 64, 5.10 |
| Tissue share inside the decoded grid | 0.768 | 0.0001 |
| Estimated minutes to decode all tissue tiles at level 0 | 0.0 | 1.3 |
| Peak memory after reading (MB) | 202.6 | 383.3 |
| Download + read (minutes) | - | 3.5 |

One flaw in our measurement: the tile grid is placed at the centre of mass of the coloured pixels. On the large slide (a "1of2" piece, most likely two separate tissue cores) that centre falls on glass, so the 64 decoded tiles were almost empty (tissue share 0.0001). The per-tile time of 5.1 ms is therefore for near-empty JPEG 2000 tiles and may understate full tissue tiles. On the small slide the grid was 77% tissue and took 4.7 ms per tile, so the gap is probably small, but a later version should put the grid on the densest tissue block rather than the centre of mass. This does not affect P3, whose rule only needs one decoded tile.

### The segmentation package (`seg_small`, participant 34-10050)

| Member | Bytes | Compressed | What it is |
|---|---|---|---|
| README.md | 6,820 | 2,911 | describes the three files and the segmentation protocol |
| S-1904-008128_PAS_2of2_features_v2.xlsx | 22,530 | 21,616 | per-structure feature tables |
| S-1904-008128_PAS_2of2.ome.tif | 14,598,037 | 1,405,327 | 7-plane pyramidal mask, uint16, 6 levels, 17750 x 15943 |
| S-1904-008128_PAS_2of2.ome.xml | 1,302 | 470 | OME 2016-06 metadata, 7 Channel elements, written by tifffile.py 2021.11.2 |
| S-1904-008128_PAS_2of2.svs | 11,214,335 | 10,375,658 | the PAS slide itself, byte-identical to `pas_small` |

The README (6,811 characters) says: the OME-TIFF has one layer per tissue unit or structure, each segmented unit a unique integer; the OME-XML carries layer names, slide dimensions, pixel resolution and channel order; the feature workbook holds measurements of the segmented units, "unitless, microns, microns squared", and "in v2 ... unitless, pixels, pixels squared"; and `ome.tif` files past S-2006-005094 (alphanumerically) do not contain annotations for interstitial fibrosis and tubular atrophy (IFTA). Its segmentation protocol was trained on 190 WSIs (53 diabetic nephropathy, 39 lupus nephritis, 11 transplant surveillance biopsies and others), annotated for viable and sclerotic glomeruli, cortical and medullary tubules and more (we read only the first 1,500 characters; the rest is in the package).

Feature workbook, four sheets, one row per segmented structure, type given by the sheet:

| Sheet | Rows | Columns |
|---|---|---|
| gloms | 0 | x1, x2, y1, y2, Area, Mesangial Area, Mesangial Fraction |
| s_gloms | 0 | same as gloms |
| tubs | 238 | x1, x2, y1, y2, Average TBM Thickness, Average Cell Thickness, Luminal Fraction |
| arts | 11 | x1, x2, y1, y2, Arterial Area |

So this slide piece has 238 segmented tubules and 11 arteries and no segmented glomeruli. The four coordinate columns are a bounding box in level-0 pixels (the artery boxes run from about x 11,967 to 12,973 and y 4,168 to 5,248, inside the 15,943 x 17,750 slide). All 238 tubule rows have all three measurements filled.

### The TIV descriptor workbook

Six sheets: ReadMe; KPMP Pathologists Authorship (10 pathologists from 9 departments); Data Table; Data Dictionary (153 variables); TIV Score Sheet (the form the pathologists used); Pathology Definitions (62 features).

Data Table: header in row 4; 341 data rows; 160 columns, of which 155 are named and 5 are empty; **340 distinct participant IDs, so one ID appears on two rows.** Release Date: "Q1 2025" 291 rows, "Q1 2026" 50 rows. Consensus Complete: "Y" 317, "y" 24. Column families: Cortex (interstitial fibrosis percent and focality; interstitial edema; tubular atrophy, common and endocrine type, percent; other tubular injury with 14 presence flags; luminal morphology; hypertrophy; intratubular changes; interstitial mononuclear cells, eosinophils, neutrophils, granulomas, foam cells), Medulla (the same families; 195 of 338 rows "n/a", so most biopsies have no scored medulla), and Cortex and Medulla (amyloidosis, microorganisms, arteriosclerosis and arteriolar hyalinosis on 0-3 scales, myxomatous change, vascular amyloid, necrosis, inflammation, thrombi, capillaritis, congestion, and "arteries/arterioles not well sampled").

Coding is mixed and needs cleaning rules before any analysis: numbers are stored as "0.0"/"1.0", yes/no as "N"/"Y"/"y"/"n", missing as "n/a", "not available" as "999.0" in the vascular columns, and a few stray cells ("4,", "7.0" in a yes/no column, "o", "0-", "?"). Percent columns use the dictionary's step set (0, 1, 2, 3, 4, 5, 10, 15 ... 100): "Cortex: Interstitial Fibrosis: Percent" has 29 distinct values and "Cortex: Tubular Atrophy: Common Type: Percent" 25.

## 4. What this changes

- The verdict rule was followed: run v1 is "not shown feasible" because P4 failed as coded. The cause is ours, it is fixed in v1.1, and run v2's expected outcome is written above. If v2 does not come back "feasible", that is reported next, and the pilot waits.
- For the planned pilot (draft in this repository once registered), the package answers the question it was waiting on: the feature workbooks are per-structure rows with a bounding box and 1-3 measurements, so a feature-only pilot (no slide decoding) is possible, at the cost of having only three tubule measurements per structure. The structure type is given by the sheet, not by a column, a small deviation from the draft's wording.
- Package sizes, from the Repository's file list (hand counts): 220 of the 361 packages carry the `_v2` suffix; 205 of those are under 1 GB and 15 are 1.0 to 2.4 GB; every package contains its slide. Fetching all 220 would be roughly 40 GB, about an hour at the speed measured here, within one job. If the v2 range probe shows the server honours HTTP Range, the 22 kB workbook can be read from the zip's central directory without the slide.
- The duplicate participant ID in the TIV table, the mixed coding and the "999" codes need rules fixed in the pilot pre-registration before the data are read.

## 5. Limits

- One small slide piece and one large slide. The small piece has no segmented glomeruli, so nothing here says how glomerular tables look when filled.
- The tile-timing grid landed on glass for the large slide (section 3).
- The mask's pixel values were not read (over the 200 million pixel cap), so we have not checked that its planes hold the integers the README describes, nor read the layer names from the OME-XML. The pilot code will.
- The 141 packages without `_v2` may hold features in microns rather than pixels (README). The pilot will use only v2 packages.
- `results.json` from this run is kept locally and is not published, because it contains value counts of the TIV score columns and the 11 arterial feature values, which are KPMP data rather than metadata about our code. Everything needed to reproduce the run is in `kidney/kpmp_feasibility.py` and the pre-registration; the published numbers above are measurements of our own process and headers of KPMP's files.
- Nobody on the team is a kidney pathologist.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 18, 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-feasibility-prereg-v1-2026-10-18.md` and `../kidney/kpmp_feasibility.py` (this repository)
- Job output `compete-results/kpmp-feasibility-v1/` (local; summary values quoted above)
- KPMP Atlas Repository file-list exports of 2026-10-18 (https://atlas.kpmp.org/repository/), not re-hosted
