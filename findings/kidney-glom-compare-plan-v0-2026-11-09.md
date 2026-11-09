# Plan, fixed in advance: open HuBMAP glomerulus models vs KPMP's released segmentation on four open KPMP slides (v0)

MV2 of Munim, Inc., 2026-11-09. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0. Research code and methods, not a medical device, not for diagnosis, not medical advice.

## Status of this plan

This plan was written and published **before** the stage-2 dry run (`kidney-glom-v3`, pre-registered in
`findings/kidney-glom-dryrun-prereg-v1-2026-11-08.md`) produced any output. When this was written, no glomerulus had
been counted on any KPMP slide by us, and no KPMP mask had been opened. It becomes a binding pre-registration only if
that dry run passes D1 (models load and run) and D4 (the package holds a countable glomerulus class). Anything the
dry run teaches us about the mask format may change **how** the KPMP objects are read. Such changes go in a dated
addendum, published before any of the four graded slides is processed. The tolerances and predictions below do not
change.

## Question

How closely do the open Deepflash2 kidney U-Nets from the HuBMAP "Hacking the Kidney" competition, run unchanged on
CPU at 1.5 um/px by `kidney/glom.py`, agree with the glomerulus objects in KPMP's own released segmentation
("Seg_Masks_Features" packages) on open KPMP PAS biopsy slides?

Both sides are model outputs. KPMP describes its masks as coming from a model trained without KPMP data, and the
HuBMAP models were trained on 15 HuBMAP kidney slides: wedge resections, partly fresh-frozen. So this measures
**agreement between two open models**, not accuracy against a pathologist.

## Prior art (searched 2026-11-09)

- Zhang et al. (AstraZeneca), arXiv 2406.16900 (2024), trained supervised glomerulus segmenters on HuBMAP Kidney
  (3,706 patches from 15 slides) and used KPMP (20,868 patches from 210 annotated slides) as an external
  validation set, at patch level (Dice, recall; numbers only in a figure). It did not use the released competition
  weights or count glomeruli per whole slide.
- We found no published whole-slide count comparison between the released HuBMAP winning weights and KPMP's
  released masks. That is a search result, not proof that none exists.

## Slides and settings (fixed)

- Graded slides: the open KPMP packages we call slide01, slide03, slide04 and slide05 (the same five used by stage 1,
  minus slide02, the development slide). Package IDs stay in a private input file.
- Our side, D: the `glomeruli` count of `kidney/glom.py` (8-connected regions of the 5-model mean probability at 0.5,
  area >= 2,000 um^2), with the settings that passed the dry run. **No setting is tuned to KPMP's masks.** If the dry
  run fails D1, D2 or D3, a fix may be made using slide02 only. It is published as an addendum with its reason, and
  before any graded slide is run.
- KPMP side, K: the number of objects in KPMP's glomerulus classes (non-globally-sclerotic plus globally sclerotic).
  We use the same 2,000 um^2 floor when the mask's pixel size can be tied to the slide's microns per pixel; if it
  can't, all objects are counted and the floor is reported as not applied. K_GS is the globally sclerotic part.
- Both sides count every tissue piece on the slide. Stage 1 found a median of 2 pieces per slide, probably serial
  sections, so neither side collapses them, and the comparison is like for like.

## Predictions (graded exactly as written, on the four graded slides)

- **C1 (per-slide agreement):** on at least 3 of the 4 slides, |D - K| <= max(3, 0.25 x K).
- **C2 (pooled ratio):** sum(D) / sum(K) is between 0.80 and 1.25.
- **C3 (size):** the median area of D's glomeruli over the pooled slides divided by the median area of K's objects is
  between 0.70 and 1.43. Graded only if K's areas can be put in um^2; otherwise reported as not graded.
- **C4 (negative control):** pairing each slide's D with the next slide's K (01->03->04->05->01) gives fewer slides
  within the C1 tolerance than the true pairing. If C4 fails, the slides' counts are too alike for C1 to mean much,
  and C1 is reported as uninformative whatever its result.

Reported, not graded: whether sum(D) sits closer to sum(K - K_GS) or to sum(K), i.e. whether the HuBMAP models seem to
miss globally sclerotic glomeruli. We report it only if sum(K_GS) >= 3, and we make no prediction.

## What will be published

Only aggregates and code: how many of 4 slides fall within tolerance (true and shifted pairing), the pooled ratio, the
pooled median-area ratio, whether a 2,000 um^2 floor was applied to K, and the run's settings. No per-slide counts, no
per-slide rows, no image patches, no package IDs or member names, per the KPMP data use terms.

## Limits

Four biopsies and one stain; all five stage-1 slides report 0.2527 um/px, so probably one scanner type. Counts can agree while objects do not:
false positives and misses cancel out in C1 and C2. Matching objects one by one needs `glom.py` to export positions,
which is planned for a later version and would get its own pre-registration. Both sides are models. The 1.5 um/px
working scale is carried over from the competition's colon inference code (an assumption, disclosed in the dry-run
pre-registration).

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028).
Prior art: Zhang I. et al., "Utilising Weak-to-Strong Consistency for Semi-Supervised Glomeruli Segmentation",
arXiv 2406.16900 (2024).
