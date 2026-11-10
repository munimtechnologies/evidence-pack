# Pre-registration: can one released HuBMAP kidney U-Net learn KPMP's globally sclerotic glomeruli on a CPU? (stage 5, v1)

MV2 of Munim, Inc., 2026-11-10. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Written and published **before** any training slide has been downloaded by us for this purpose, before any model
has been trained, and before any stage 5 detection exists on the test slides. Code: `kidney/gsdet.py` 0.1.0
(training-set selection, crops, training, detection) and `kidney/compare5.py` 0.1.0 (grading), with offline tests
(`kidney/test_gsdet.py`, `kidney/test_compare5.py`; invented numbers and random weights only).

## Why

Stage 4 (`findings/kidney-glom-stage4-results-v1-2026-11-10.md`) found that the five released HuBMAP "Hacking the
Kidney" U-Nets of team Deepflash2 find about 73% of KPMP's non-globally-sclerotic (NS) glomeruli and **none** of its
globally sclerotic (GS) glomeruli on 12 independent biopsies (recall 0.000, also at box IoU 0.3). Their training
labels left GS glomeruli out on purpose. A pipeline built on these weights therefore cannot report a total
glomerulus count or the share of globally sclerotic glomeruli, a standard item in a kidney biopsy report. Stage 5
asks whether a cheap fix works: fine-tune **one** of the released U-Nets on KPMP's own open segmentation of other
biopsies, on CPU only, and test it on the same 12 biopsies as stage 4, which nothing in this recipe was tuned on.

## Data

- **Test slides (frozen):** the 12 open KPMP "Segmentation Masks & Pathomics Vectors" v2 packages chosen by stage 3b's
  rule (`findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md`) and used in stages 3b and 4. Their KPMP counts and
  stage 4 match rates are already known to us (published as rates); no stage 5 setting below was chosen by looking
  at their images or objects, and none will be changed after this note.
- **Training slides:** stage 3b's rule without its final cut (open v2 packages; the five packages of stages 1-3 and
  every package of those five participants dropped; at most 300 MB; sorted by KPMP's package id; first package per
  participant). The first 12 packages of that list must be exactly the frozen test slides: `gsdet.py select` checks
  this and the job stops if it fails. The training set is the **next 24** packages. One package per participant
  means no training biopsy comes from a test participant (also checked). The job reads the rows of KPMP's open file
  list (saved 2026-10-18) whose package id starts with 0-4, plus the five excluded packages' rows; by hand, the 36th
  package of the list falls in that range, and under this rule rows with later ids cannot change the first 36.
  Package and participant ids stay in a private input file, per the KPMP data use terms.
- **Labels:** KPMP's released segmentation of each training slide (two channels: non-globally-sclerotic and globally
  sclerotic glomeruli), read from the pyramid level `kidney/kmask.py` reads (at most 100 million pixels) and resized
  with nearest neighbour to the working scale of 1.5 um per pixel. KPMP's segmentation is itself a model output, so
  the model learns to agree with KPMP's pipeline, not with pathologists.

## Recipe (fixed now; see `kidney/gsdet.py`)

- **Crops:** 288 x 288 pixels (432 um) around every GS object (up to 50 per slide), up to 25 NS objects and up to 25
  random tissue points per slide (objects of at least 2,000 um^2; centres moved at random by up to 32 pixels).
- **Model:** `smp.Unet(efficientnet-b2)` started from `unet_model-1.pth` of the released Deepflash2 kidney weights
  (Zenodo 10.5281/zenodo.7730028, CC BY 4.0), its 2-class head widened to 3 classes (background, NS, GS; the GS class
  starts as a copy of the glomerulus class). Batch-norm statistics stay fixed. Adam, learning rate 1e-4, class weights
  1/1/2, batches of 8 random 256 x 256 windows with random 90-degree turns and flips; crop kinds drawn with
  probabilities GS 0.4, NS 0.3, random 0.3. **1,500 steps or 240 minutes, whichever comes first**, on 3 CPU threads.
  Seed 5.
- **Detection:** `kidney/glom.py`'s tiling at 1.5 um per pixel (512-pixel tiles, step 0.8, Gaussian blending,
  empty-tile rule), this single model with horizontal and vertical flips. A detected glomerulus (D) is an 8-connected
  region where P(background) < 0.5, with an area of at least 2,000 um^2; it is called **GS** when its summed P(GS)
  exceeds its summed P(NS), otherwise NS. No threshold is tuned.
- **K:** KPMP's objects from `kidney/kmask.py` 0.3.0 after the same 2,000 um^2 floor, as in stage 4.
- **Matching:** stage 4's: bounding-box IoU >= 0.5, greedy by IoU, one-to-one, both K classes in one pool.

## Predictions (graded exactly as written by `kidney/compare5.py`)

Gate: at least 10 of the 12 test slides complete (D and K both exist) **and** at least 300 training steps done.
A setup or infrastructure failure (download, memory, timeout, a crash before grading) is fixed and re-run, not
graded. All bounds are inclusive; rates are graded unrounded and published to three decimals.

- **P1 (the sclerotic class is found):** pooled recall of K's GS objects >= 0.50 (stage 4: 0.000). Graded only if the
  test slides hold at least 10 GS objects.
- **P2 (no loss on the normal class):** pooled recall of K's NS objects >= 0.734 (stage 4's value for the five-model
  released ensemble).
- **P3 (what it finds is a glomerulus):** pooled precision (share of D objects matched to any K object) >= 0.80.
- **P4 (it names the class):** among matched pairs, the share of K's GS objects that D calls GS is >= 0.70 **and** the
  share of K's NS objects that D calls NS is >= 0.90. Graded only if at least 10 GS objects are matched.
- **P5 (the biopsy-report number):** the pooled share of D objects called GS is within 0.05 of the pooled share of K
  objects that are GS (absolute difference <= 0.05).
- **P6 (control):** D of slide i matched with K of slide i+s, for all 11 non-zero cyclic shifts s; mean pooled recall
  over all K objects <= 0.10. If P6 fails, P1-P5 are reported as uninformative whatever their results.

Reported, not graded: recall over all K objects; whether both classes reach recall 0.70; median IoU of matched
pairs; recall and precision at box IoU 0.3; Spearman's rho between the per-biopsy GS shares of D and K (a single
aggregate); training steps, minutes and the loss curve; the number of training crops by kind (pooled).

## What will be published

Only `compare5.py`'s aggregate output, aggregate lines of the other steps and the run settings. No per-slide count,
area, position, name, package id, image or crop. The fine-tuned weights stay local for now.

## Limits

Twelve test biopsies, one stain (PAS). Both sides are models: agreement with KPMP's segmentation is not accuracy.
One model instead of five, a short CPU training run and a few hundred GS examples at most; a negative result would
say this cheap recipe is not enough, not that the task cannot be done. Labels come from a coarser pyramid level on
large slides (up to about 4 um per pixel), so boundaries are approximate. The comparison with stage 4 changes two
things at once (fine-tuning and one model instead of five), so P2 cannot separate them.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028). The
weights used here are team Deepflash2's.
