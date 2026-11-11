# Pre-registration: do hard negatives fix the false sclerotic calls of a CPU-fine-tuned HuBMAP kidney U-Net, on fresh KPMP biopsies? (stage 6, v1)

MV2 of Munim, Inc., 2026-11-11. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Written and published **before** any stage 6 model has been trained and before any of the 12 fresh test biopsies
below has been downloaded by us. Code: `kidney/gsdet.py` 0.2.0 (fresh test-set selection, hard-negative mining,
training on several crop folders; every stage 5 default unchanged) and `kidney/compare6.py` 0.1.0 (grading), with
offline tests (`kidney/test_gsdet.py`, `kidney/test_compare6.py`; invented numbers and random weights only).

## Why

Stage 5 (`findings/kidney-glom-stage5-results-v1-2026-11-11.md`) fine-tuned one released HuBMAP "Hacking the
Kidney" U-Net of team Deepflash2 on KPMP's open segmentation of 24 biopsies, on CPU. On the 12 frozen biopsies of
stages 3b-5 it found 0.950 of KPMP's globally sclerotic (GS) glomeruli (the released weights: 0.000) and 0.932 of
the non-sclerotic (NS) ones, and named the class of matched glomeruli well (0.965 / 0.990). It **failed** on
precision (0.723, bar 0.80) and on the share of glomeruli called GS (0.255 against KPMP's 0.157): most extra
detections were called GS. A post-hoc breakdown, labelled as such, put the precision of its GS calls at 0.460.

Stage 6 asks two things on **fresh** biopsies: does that pattern replicate on slides nothing has been tuned or
graded on, and does a standard fix, training on hard negatives mined from the model's own false detections, raise
precision without losing recall? The 12 frozen biopsies have now graded three stages and motivated this change, so
from here on they are a development set only.

## Data

- **Fresh test slides:** stage 3b's selection rule (`findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md`) without
  its final cut, as in stage 5: open v2 "Segmentation Masks & Pathomics Vectors" packages of KPMP's open file list
  (saved 2026-10-18); the five packages of stages 1-3 and every package of those five participants dropped; at most
  300 MB; sorted by KPMP's package id; first package per participant. Items 1-12 of that list are the frozen test
  slides and items 13-36 are stage 5's 24 training slides; `gsdet.py select-test` checks both and the job stops if
  either differs. The fresh test set is **items 37-48** (12 packages). By hand, item 48 has a package id starting
  with 5; the job reads the rows of the saved list whose package id starts with 0-5, and under this rule rows with
  later ids cannot change the first 48. One package per participant means no test biopsy shares a participant with
  a training or frozen biopsy (also checked). Package and participant ids stay in a private input file, per the
  KPMP data use terms.
- **Training slides:** stage 5's 24, unchanged, with the same labels (KPMP's released segmentation; two channels,
  NS and GS), read and resized as in stage 5.

## Recipe (fixed now; see `kidney/gsdet.py` 0.2.0)

Both arms start from `unet_model-1.pth` of the released Deepflash2 kidney weights (Zenodo 10.5281/zenodo.7730028,
CC BY 4.0), widened to 3 classes, and train with stage 5's settings: batch-norm statistics fixed, Adam 1e-4, class
weights 1/1/2, batches of 8 random 256 x 256 windows from 288 x 288 crops with random turns and flips, **1,500
steps or 240 minutes**, 3 CPU threads, seed 5.

- **Arm A (replication):** stage 5's recipe unchanged: crops around every GS object (up to 50 per slide), up to 25
  NS objects and up to 25 random tissue points per slide; kinds drawn GS 0.4 / NS 0.3 / random 0.3. With the same
  data and seed this is meant to reproduce the stage 5 model; whether the loss log matches stage 5's is reported.
- **Arm B (hard negatives):** arm A's model is run over each of the 24 training slides exactly as in detection
  (below). Every detected region of at least 2,000 um^2 with **less than 10%** of its pixels on a KPMP glomerulus
  of either class is a hard-negative candidate; up to **25 per slide** (random order) become 288 x 288 crops of kind
  "hard", labelled from KPMP's segmentation like every other crop. Arm B then trains from the released weights
  (not from arm A) on arm A's crops plus the hard crops, kinds drawn **GS 0.35 / NS 0.25 / random 0.20 / hard
  0.20**. Nothing else changes. No threshold is tuned in either arm.
- **Detection (both arms):** `kidney/glom.py`'s tiling at 1.5 um per pixel (512-pixel tiles, step 0.8, Gaussian
  blending, empty-tile rule), the single model with horizontal and vertical flips. A detected glomerulus (D) is an
  8-connected region where P(background) < 0.5 of at least 2,000 um^2; it is called GS when its summed P(GS) exceeds
  its summed P(NS), otherwise NS.
- **K and matching:** KPMP's objects from `kidney/kmask.py` 0.3.0 after the same 2,000 um^2 floor; bounding-box IoU
  >= 0.5, greedy by IoU, one-to-one, both K classes in one pool (stages 4-5).

## Predictions (graded exactly as written by `kidney/compare6.py`)

Gate: at least 10 of the 12 fresh slides complete for **both** arms (D of each arm and K exist; both arms are graded
on the same slides) **and** at least 300 training steps in each arm. A setup or infrastructure failure (download,
memory, timeout, a crash before grading) is fixed and re-run, not graded. Bounds are inclusive unless written as
"<"; rates are graded unrounded and published to three decimals. Q1, Q4 and Q6 need at least 10 GS objects in K
over the graded slides; otherwise they are reported as not graded.

- **Q1 (stage 5's success replicates):** arm A pooled recall of K's GS objects >= 0.80.
- **Q2 (stage 5's failure replicates):** arm A pooled precision (share of D matched to any K object) < 0.80.
- **Q3 (the fix works):** arm B pooled precision >= 0.80.
- **Q4 (without losing the sclerotic class):** arm B pooled recall of K's GS objects >= 0.80.
- **Q5 (or the normal class):** arm B pooled recall of K's NS objects >= 0.85.
- **Q6 (the biopsy-report number):** arm B's pooled share of D called GS is within 0.05 of the pooled share of K
  objects that are GS.
- **Q7 (the difference is the hard negatives):** arm B precision minus arm A precision >= 0.05.
- **Q8 (control):** for each arm, D of slide i matched with K of slide i+s for all non-zero cyclic shifts s; mean
  pooled recall over all K objects <= 0.10 in both arms. If Q8 fails, Q1-Q7 are reported as uninformative.

Reported, not graded: for each arm, recall over all K, the class agreement on matched pairs, the precision of GS
calls (D called GS that match a K GS object, over all D called GS), median IoU of matched pairs, rates at box IoU
0.3; training steps, minutes and loss curves; pooled crop counts by kind; the pooled number of hard-negative
candidates found on the training slides; and arm B on the 12 frozen development slides (graded by
`kidney/compare5.py`'s rules for continuity, not as a test).

## What will be published

Only `compare6.py`'s aggregate output, aggregate lines of the other steps and the run settings. No per-slide
count, area, position, name, package id, image or crop. Fine-tuned weights stay local until KPMP's terms on models
trained on its open data have been read.

## Limits

Twelve test biopsies, one stain (PAS). Both sides are models: agreement with KPMP's segmentation is not accuracy,
and a "false" detection may be a real glomerulus KPMP's pipeline missed; hard-negative mining then teaches the model
to miss it too, which Q5 is there to catch. Arm B changes two linked things at once (the hard crops and the kind
mix needed to draw them), so Q7 credits the pair, not the crops alone. One seed per arm: a precision gain near 0.05
could be seed noise. Twelve biopsies hold few GS objects, and some biopsies hold none, so recall of the GS class
is coarse.

## Acknowledgement

This work did not receive funding from the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) or the Kidney Precision Medicine Project (KPMP). The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 11, 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18; the opening and closing sentences re-checked against that page on 2026-11-11). We gratefully acknowledge the essential contributions of our patient participants and the support of the American public through their tax dollars.

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028). The
weights used here are team Deepflash2's. Hard-negative mining for glomerulosclerosis has been used before (for
example "Holistic Fine-grained GGS Characterization: From Detection to Unbalanced Classification", arXiv
2202.00087, as a post-hoc classifier); this stage tests it inside the fine-tuning of the released HuBMAP weights against KPMP's
labels, pre-registered, on fresh biopsies.
