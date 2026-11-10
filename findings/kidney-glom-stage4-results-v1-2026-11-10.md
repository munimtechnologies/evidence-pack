# Results: the open HuBMAP Deepflash2 kidney models find none of KPMP's globally sclerotic glomeruli (stage 4, v1)

MV2 of Munim, Inc., 2026-11-10. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Grades the pre-registered plan `findings/kidney-glom-stage4-prereg-v1-2026-11-10.md` (published at tag v0.9.66
before any object position from these slides existed) exactly as written. Code: `kidney/glom.py` 0.2.0,
`kidney/kmask.py` 0.3.0 and `kidney/compare4.py` 0.1.0, cloned from tag v0.9.67. Per the KPMP data use terms, only
aggregate rates are given: no per-slide value, count, position, name, package id or image.

## The run

Job kidney-4-v2, one CPU job on 3 cores, 10 November 2026, about 10:49-13:13 UTC (2 h 24 min; peak memory 2.05 GB).
All 72 offline tests of the five kidney modules passed first. The 12 open KPMP "Segmentation Masks & Pathomics
Vectors" packages chosen by stage 3b's fixed rule were downloaded again (12 of 12), `glom.py` ran the five released
HuBMAP "Hacking the Kidney" U-Nets of team Deepflash2 on all 12 slides, and `kmask.py` read all 12 KPMP masks with
the pixel size linked on 12 of 12. So 12 of 12 slides were complete (the gate needed 10), and the slides held more
than the 10 globally sclerotic objects that O3 and O4 needed. (The first attempt, kidney-4-v1, stopped at its unit
tests on a stale version pin before any slide was read; see the stage 3b results note. That was an infrastructure
failure, fixed and re-run as the plan says.)

D = glomeruli found by the HuBMAP models; K = KPMP's glomerulus objects after the same 2,000 um^2 floor, in two
classes: non-globally-sclerotic (NS) and globally sclerotic (GS). A D object and a K object match when their bounding
boxes overlap with IoU >= 0.5 (greedy, one-to-one, both K classes in one pool).

## Grades

| Prediction | As written | Result | Verdict |
|---|---|---|---|
| O1 finds the normal ones | recall(NS) >= 0.70 | 0.734 | **held** (0.034 above the bar) |
| O2 what it finds is a glomerulus | precision >= 0.70 | 0.912 | **held** |
| O3 sclerotic blind spot, relative | recall(NS) - recall(GS) >= 0.20 | 0.734 | **held** |
| O4 sclerotic blind spot, absolute | recall(GS) <= 0.50 | **0.000** | **held** |
| O5 control | mean pooled recall over the 11 cyclic slide shifts <= 0.10 | mean 0.000, max 0.000 | **held**, so O1-O4 are informative |
| O6 alignment | abs(median offset) <= 8 um on each axis (>= 20 pairs) | dx -4.0 um, dy -4.3 um | **held** |

All 6 predictions held. Reported, not graded: the median box IoU of matched pairs is **0.813**; globally sclerotic
objects are **0.157** of KPMP's glomerulus objects on these slides; at the looser box IoU of 0.3, recall(NS) is
**0.777**, recall(GS) is still **0.000**, and precision is **0.965**.

## What this says

- **The released Deepflash2 kidney models did not find a single one of KPMP's globally sclerotic glomeruli** on
  these 12 biopsies, at either overlap threshold. Their training labels left globally sclerotic glomeruli out on
  purpose (Jain et al., Communications Biology 2023), and the models behave exactly that way on independent data.
  Because recall(GS) stays at 0 when the overlap bar drops to 0.3, these are not detections with poor boxes. A hand
  look at the local object lists of one slide found no detection anywhere near the sclerotic glomeruli checked.
- **They find most, but not all, non-sclerotic glomeruli:** about 73% at box IoU 0.5 and 78% at 0.3. When they do
  find one, the box agrees closely with KPMP's (median IoU 0.81, median centre offset about 4 um on each axis), and
  91-97% of what they report is one of KPMP's glomeruli.
- **This explains stage 3b's count gap object by object.** Every match was a non-sclerotic glomerulus, so
  precision x (D / K_NS count ratio) should equal recall(NS): 0.912 x 0.805 = 0.734, which is what was measured.
- Against all of KPMP's glomeruli, both classes together, the models find about 0.734 x (1 - 0.157), or roughly
  **62%**. A glomerulus count from these weights is therefore neither a total glomerulus count nor a basis for the
  share of globally sclerotic glomeruli, which is a standard item in a kidney biopsy report. Anyone using these
  public weights for whole-slide glomerulus counts should know that.
- O1 held by a small margin (0.734 vs 0.70); read it as "about three quarters", not more.

## Reproducibility check (reported, not graded)

The job also re-ran stage 3b's grader (`kidney/compare3b.py`) on its own fresh downloads and fresh CPU inference.
The output was **identical** to stage 3b's own run (job kidney-3b-v1, the same day): every graded value matched
(B1 0.805, B2 8 of 12, B3 shifts mean 1.273 and max 3, B4 0.679, B5 0.977, B6 0.905, sclerotic share 0.157). So
the pipeline's counts reproduce from scratch on the same slides with the same software versions.

## Prior art and why this is new

It is documented that the competition's labels excluded globally sclerotic glomeruli (Jain et al. 2023, doi:10.1038/
s42003-023-04848-5). The organisers' later multi-organ paper says qualitatively that a kidney algorithm "sometimes
... predicts sclerotic (diseased/unhealthy) glomeruli which were not included in the ground truth" (Jain et al.,
Nature Communications 2023, doi:10.1038/s41467-023-40291-0), which concerns their own production model, not the
Deepflash2 weights tested here. External validation of HuBMAP-trained architectures on KPMP patches exists (arXiv
2406.16900, models retrained in its own pipeline, no split by sclerosis), and other work trains models to segment
sclerosed glomeruli (for example He et al., Scientific Reports 2024, doi:10.1038/s41598-024-51651-1). Searches on
2026-11-09 and 2026-11-10 found no published, pre-registered, object-level whole-slide measurement of the
**released** winning weights against KPMP's two glomerulus classes. That is a search result, not proof that none
exists.

## Limits

- Twelve biopsies from 12 participants, one stain (PAS), one area floor, one team's weights (Deepflash2). Other
  winning teams' released weights were not tested.
- Both sides are models, not pathologists: KPMP's released segmentation is itself a model output, so agreement is
  not accuracy, and a glomerulus KPMP's segmentation missed cannot be seen here.
- A box IoU is cruder than a pixel IoU. Two touching glomeruli merged into one detection can match at most one.
- The slides were chosen by stage 3b's rule, not for this question. The pooled sclerotic share (0.157) varies a lot
  between biopsies, so a biopsy-level miss rate depends on how sclerotic the biopsy is.
- A data lead from stage 3b still stands, not investigated: on 2 of 12 slides KPMP's mask label count and its
  feature-workbook row count disagree for at least one class.

## Reproduce

Tag v0.9.67: `python -m unittest kidney.test_glom kidney.test_compare kidney.test_kmask kidney.test_compare3b
kidney.test_compare4`, then `python -m kidney.glom --in-dir <svs> --out-dir <out> --models <folder with
unet_model-1..5.pth> --threads 3`, `python -m kidney.kmask --masks <masks> --wsi <svs> --out k.json --diag
kmask-diag.json`, `python -m kidney.compare4 --glom glom.json --k k.json --out compare4.json`, on the 12 open
"Seg_Masks_Features" v2 packages selected by the rule in the stage 3b pre-registration (KPMP's open file list;
packages are chosen by sort order of their ids). Weights: `models/5-deepflash/kidney/` in `trained_models.zip` of
Zenodo record 7730028.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028).
