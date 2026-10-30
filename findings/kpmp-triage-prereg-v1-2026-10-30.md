# Pre-registration: blinded AI visual triage of KPMP tubules with no TBM thickness (2026-10-30)

MV2 of Munim, Inc. Planned, coded and to be read and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice. **This is AI triage, not a pathologist's reading.** Nobody on the team is a kidney pathologist. No human has reviewed this plan. Nobody at KPMP, NIDDK or HeroX has been contacted.

**Status:** fixed on 2026-10-30, before any crop for this study exists. Code: `kidney/kpmp_triage.py` 1.0 with offline tests (`kidney/test_kpmp_triage.py`), committed with this plan.

## 1. Why

In KPMP's open pathomics files about 10% of v2 tubule rows have an `Average TBM Thickness` of zero or less. Two pre-registered studies found that a participant's share of such rows tracks the consensus tubular atrophy % and baseline eGFR, survives adjustment for median tubule size, age band and the collapsed-lumen share, but is mostly shared with a simpler marker, the share of small tubules (`kpmp-zs-results-v1-2026-10-29.md`). The numbers cannot say what the zero rows are: atrophic tubules whose basement membrane the pipeline cannot trace, ordinary small tubules, oblique cuts, or boxes that are not on a tubule at all. Only looking can. The results note said this triage would be pre-registered before any image is viewed; this is that plan.

## 2. Prior art (search 2026-10-30)

- Our own v0.9.20-v0.9.22 notes are the only reports we found of unmeasured tubules in KPMP's pathomics vectors.
- Closest on method: "Vision-Language Models as Zero-Annotation Oracles in Histopathology" (arXiv 2606.16658) uses VLMs for quality control of kidney-transplant slides (tissue vs background, blur, segmentation-mask review), not for classifying what a pipeline failed to measure. Glo-VLMs (arXiv 2508.15960) fine-tunes VLMs to classify glomeruli on PAS slides. We found no study that used a general-purpose AI model, blinded and size-matched, to triage the objects a public kidney pathomics release failed to measure.

## 3. Sample (fixed in code; seed 20261030)

- **Packages:** the open v2 segmentation packages in the Repository export of 2026-10-18 (`Seg_Masks_Features_v2.zip`, one participant each, listed size at most 1.5 GB), sorted by package ID and shuffled with the seed. Taken in that order, at most one package per participant, until 12 qualify. A package qualifies if its one workbook's `tubs` sheet has at least 8 rows with TBM <= 0 and 40 rows with TBM > 0, each with a full box of positive area.
- **Pairs:** in each package, 4 zero-TBM rows drawn at random; each is paired with the not-yet-used measured row (TBM > 0) on the same slide whose box area is nearest on the log scale. 48 pairs, 96 crops.
- **Duplicates:** 8 of the 96 crops, drawn at random, are written a second time under new IDs, to measure the reader's consistency. 104 images.
- **Crops:** from the slide's `.svs` (the slide in the package), at full resolution where the window allows, with a margin of one box side (at least 128 pixels) around the box, the box outlined in green, at most 512 pixels on the long side. KPMP's x1|x2 are taken as image rows unless the slide's own boxes decide the orientation (`kp.orientation`); an earlier look at outlier crops found x runs along rows.
- **Blinding:** all 104 images get shuffled IDs `c001`-`c104`. The key (group, pair, package, box, TBM) goes to a separate `key/` folder.

## 4. Reading protocol

1. The reading run opens only `manifest.json` and the images, in ID order. It does not open anything in `key/` until step 4.
2. Each image gets exactly one category, chosen by the first rule that applies, in this order:
   - **F unreadable:** the crop is too blurred, dark, small or empty to judge anything.
   - **D not a tubule or artefact:** the outlined box is mainly on something other than a tubule (interstitium, glomerulus, vessel, capsule, empty glass) or on a fold, tear, bubble, debris, pen mark or a blurred patch.
   - **A atrophic:** a tubule with a thickened, wrinkled or very prominent PAS-positive basement membrane, or flattened, simplified epithelium, or "thyroidization" (round tubules filled with homogeneous cast material).
   - **B collapsed:** a tubule whose lumen is closed or slit-like, without the features of A.
   - **C tangential or partial:** part of a tubule, a grazing or oblique cut with no clear wall and lumen, or a tubule cut by the tissue edge.
   - **E normal-looking:** a recognisable tubule with intact epithelium and an ordinary lumen.
   Each reading gets a note of at most 15 words. First impressions stand: no image is re-read to change a category once all are read (typo fixes are logged).
3. The readings (`id,category,note`) are committed to this repository as `findings/kpmp-triage-readings-v1.csv` **before** the key is opened; the commit time records the order.
4. Only then is `key/pairs.csv` (ID, block, pair, group, duplicate-of; no package ID or box) opened and graded with `python -m kidney.kpmp_triage grade`.

## 5. Gate

At least 40 complete pairs from at least 10 packages; every image read exactly once; at most 10% of the 96 original crops unreadable (F). If the gate fails, every grade below is untestable and only the table is reported. Pairs with an F in either member are left out of the tests.

## 6. Grades and predictions

Tests V1-V3 are one-sided exact sign tests on discordant pairs (McNemar exact): pairs where only the zero-TBM member is in the category against pairs where only the measured member is. Pass if p < 0.05; each pass is also reported against 0.05 / 3 = 0.0167.

| ID | Zero-TBM member more often... | Untestable if discordant pairs below | Our prediction |
|---|---|---|---|
| V1 | abnormal (A, B, C or D) | 8 | pass |
| V2 | atrophic (A) | 5 | fail (unsure) |
| V3 | not a tubule or artefact (D) | 5 | pass (unsure) |
| V4 | (consistency) the reader gives the same category to a duplicate and its original in at least 75% of duplicates where neither is F; untestable under 6 | - | pass |

Why: zero rows are small and near-closed (v0.9.20), so we expect them to look abnormal even against size-matched measured tubules (V1). The zero share added only a little beyond the small-tubule share (partial rho +0.18 with atrophy), so we doubt that atrophic morphology is what sets them apart (V2) and lean towards boxes the pipeline drew on something it could not trace (V3).

## 7. Fixed readings

- **V1 and V3 pass, V2 fails:** the zero rows are mainly segmentation or measurement failures. Users of the files should treat them as missing for a reason linked to disease, not as atrophy; the zero share is a data-quality signal that happens to track damage.
- **V2 passes:** zero rows are enriched for atrophic-looking tubules even at matched size. MV2's Kidney AI entry may describe the zero share as an image-confirmed atrophy-linked marker, labelled as AI triage and not a pathologist's reading.
- **V1 fails:** at this sample size this reader sees no difference between zero rows and size-matched measured tubules; the marker's meaning is not visible in these crops.
- **V4 fails:** the reader is not consistent enough for its categories to carry weight; V1-V3 are reported but not interpreted.
- **Artifact readings:** one AI reader of one model family; it is not a pathologist and may know textbook pictures better than real PAS slides. Crops are from the package's slide, which may not be the section the segmentation was drawn on (section twins, v0.9.20). The outline can hide a thin basement membrane at the box edge. Duplicates are byte-identical, so the reader may recognise them. 48 pairs detect only large differences.

## 8. What is published

This plan, the code, the readings (blinded IDs and categories only), `pairs.csv` after grading, the grade output and a results note. **Never published:** the images, `key.json`, package IDs with boxes, or per-participant values.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list export of 2026-10-18)
- Vision-Language Models as Zero-Annotation Oracles in Histopathology, arXiv 2606.16658
- Glo-VLMs, arXiv 2508.15960
