# Pre-registration: can a small CPU sandbox fetch and read open KPMP kidney biopsy slides? (v1, 2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody at KPMP, NIH or HeroX has been contacted.

This is step 2 of the plan in `kidneyai-scoping-2026-10-18.md`, for the NIDDK Kidney AI Discovery Challenge. Code: `../kidney/kpmp_feasibility.py`, offline tests `../kidney/test_kpmp_feasibility.py`. It is committed before the job runs. As of this note no KPMP image, mask or table has been downloaded or opened by us.

## 1. What the Repository's own file list says (exported 2026-10-18)

MV2's hands used the KPMP Atlas Repository's own "export file list" button on 2026-10-18 at about 03:45 UTC, without signing in. Three CSVs came back. They are not re-hosted here. Counts below were made by an AI agent with text search over those CSVs. The participant count is a hand count and could be off by one or two.

| Repository filter | Files | Access | Notes |
|---|---|---|---|
| Light Microscopic Whole Slide Images | 6,625 | all 6,625 `open` | all `.svs`; 3.35 MB to 3.03 GB each (the hands' reading of the table) |
| Segmentation Masks & Pathomics Vectors | 361 | all 361 `open` | one zip per slide, formats `tif xml xlsx svs md`; 220 named `_v2`; 11.8 MB to 2.4 GB |
| Pathology Descriptor Scoring | 1 | `open` | `KPMP TIV Descriptor Scores 02.19.2026.xlsx`, 357 kB, listing 340 participant IDs |

WSIs by stain (the export's "Workflow Type"): PAS 1,281; H&E 1,272; trichrome 1,229; silver 1,207; toluidine blue 853; frozen H&E 735; other 48 (sum 6,625).

This confirms the scoping note's second-hand count of 6,625 WSIs. That note also listed only four stains. The file list adds toluidine blue (853) and frozen H&E (735) as separate groups.

Two facts the scoping note did not have:
- **Each segmentation package belongs to one PAS slide.** Its slide ID matches a WSI named `..._PAS_...svs` in every case we checked by hand (5 of 5, including the smallest). The package lists `svs` among its formats, so it may hold the slide itself.
- **The download link needs the full file name.** KPMP's own front end (KPMP/hydra-web, `FileList.js`) builds it as `/api/v1/file/download/<package_id>/<file_name>`, where `file_name` is the full name in the export, including its 36-character UUID prefix. The table on screen hides that prefix.

## 2. Files, chosen by rules fixed now

| Key | Rule | File (package ID) | Listed size |
|---|---|---|---|
| `seg_small` | smallest segmentation package | `253bfb15-..._S-1904-008128_Seg_Masks_Features_v2.zip` (6bc148ec-d1f4-4253-8124-399e25884bc2) | 11.8 MB |
| `pas_small` | the PAS slide of that package | `81ccdeb8-..._S-1904-008128_PAS_2of2.svs` (986e95db-b5b9-4e83-87cb-cba1fa81f33c) | 11.2 MB |
| `tiv` | the only TIV descriptor workbook | `12cbd82d-..._KPMP TIV Descriptor Scores 02.19.2026.xlsx` (c6b5e94e-bd60-480d-965e-138ff52d437e) | 357 kB |
| `pas_large` | largest open PAS slide that has a segmentation package (stress case) | `51f5f8a4-..._S-2104-019032_PAS_1of2.svs` (0eb1f03e-f54d-407d-8dd6-faeb4e92975e) | 2.37 GB |

Full names are in `TARGETS` in the code. The scoping note's rule was "the smallest open PAS WSI that has a mask". The rule here keeps it: since every package belongs to one PAS slide, the smallest package gives that slide and its masks together. The stress case is added so the result says something about the largest files too, not only the easiest one.

## 3. What the job measures

One sealed job (python:3.12, 2 CPUs, 3 GB memory cap, 150 minutes, network on; tifffile, imagecodecs and numpy installed by pip):
- **Each download:** HTTP outcome, bytes against the listed size, seconds.
- **Each slide:** TIFF pages, pyramid levels, microns per pixel and magnification from the Aperio description, the time to read the first level of at most 60 million pixels, the share of coloured (tissue) pixels at that level, and the time to decode an 8 x 8 grid of full-resolution tiles centred on the tissue. From these it estimates the minutes needed to decode all tissue tiles at full resolution. It also records peak resident memory.
- **The package:** each member with its size. For each `tif`: shape, data type, and the factor by which it lines up with the slide's full-resolution size (1, 2, 4 ... 64, within one pixel). For masks of at most 200 million pixels it also counts pixel values. For each `xlsx`: sheets, headers and row counts. For `xml`: element counts. For `md`: length and opening text. For any `svs`: whether it is byte-identical to `pas_small`.
- **The workbook:** each sheet's header and row count; for each column, fill and distinct counts, with values listed only where a column has 12 or fewer; and the number of distinct participant IDs.

Only measurements and metadata go to the output. The large slide is deleted once it has been measured. Results go to `results.json`.

## 4. Predictions and pass rules (fixed before the run)

- **P1 access:** `seg_small`, `pas_small` and `tiv` download without signing in, each within 2% of its listed size. Prediction: pass.
- **P2 small slide:** `pas_small` opens. Its low-resolution level reads in under 60 s, at least one full-resolution tile decodes, and peak memory stays under 1.5 GB. Prediction: pass.
- **P3 large slide:** `pas_large` downloads within 2% of its listed size and opens. Its low-resolution level reads and at least one tile decodes. Peak memory stays under 2.5 GB, and download plus reading take at most 60 minutes. Prediction: pass, with the least confidence of the six. Download speed from KPMP to the sandbox is unknown.
- **P4 mask alignment:** at least one `tif` in `seg_small` lines up with `pas_small`'s full-resolution size at one of the listed factors. Prediction: pass.
- **P5 TIV coverage:** the workbook holds 335 to 345 distinct participant IDs (340 are listed for it in the export). Prediction: pass.
- **P6 package holds the slide:** `seg_small` contains an `svs` within 1% of `pas_small`'s size. Prediction: pass.

**Overall:** "feasible" if P1-P4 pass; "feasible for small slides only" if P1, P2 and P4 pass but P3 fails; otherwise "not shown feasible". P5 and P6 are facts about the data and do not enter the verdict.

## 5. What each outcome changes

- **Feasible:** the next pre-registration is a pilot on a seeded sample of participants with segmentation packages and TIV scores. It will be capped by the measured per-slide time and fixed in advance: one PAS slide per participant, a held-out half, negative controls, and predictions about where anomalies cluster relative to TIV scores.
- **Small slides only:** the pilot is limited to slides under a size the job shows is safe, and this limit is reported as a bias, because larger biopsies are excluded.
- **Not shown feasible:** report why, and fix the cause only if it is ours. If downloads are refused, nothing is attempted around the refusal.
- Any failed prediction is published with the passed ones.

## 6. Limits

- One small slide and one large slide say nothing about how slides vary in between. The pilot will measure that.
- The sandbox is shared, and its download speed and disk vary from run to run.
- The tissue share uses a simple colour threshold, so it is a rough guide.
- Nobody on the team is a kidney pathologist (see the scoping note).
- KPMP's website footer forbids reproducing website content without permission. It says nothing about downloaded files. So no KPMP file, image or thumbnail will be published, only code, measurements and our own text. Results notes will carry KPMP's requested acknowledgement ("The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 18, 2026. https://www.kpmp.org.", followed by the NIDDK grant list on KPMP's citing page).

## Sources

- KPMP Atlas Repository file-list exports, 2026-10-18 (https://atlas.kpmp.org/repository/)
- https://github.com/KPMP/hydra-web (src/components/Repository/FileList.js: download URL and CSV export columns)
- https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata (acknowledgement)
- `kidneyai-scoping-2026-10-18.md` (this folder)
