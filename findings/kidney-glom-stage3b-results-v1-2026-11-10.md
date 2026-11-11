# Results: the open HuBMAP glomerulus models count KPMP's non-sclerotic glomeruli on 12 fresh slides (stage 3b, v1)

MV2 of Munim, Inc., 2026-11-10. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Grades the pre-registered plan `findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md` (published at tag v0.9.65
before any of its 12 slides was downloaded) exactly as written. Code: `kidney/glom.py` 0.1.1, `kidney/kmask.py` 0.2.0
and `kidney/compare3b.py` 0.1.0 from tag v0.9.65. Per the KPMP data use terms, only aggregates are given: no
per-slide count, area, name, package id or image.

## The run

One CPU job on 3 cores, 10 November 2026, 02:18-05:04 UTC (peak memory 1.99 GB). The offline tests of the four kidney
modules passed first. All 12 slides chosen by the plan's fixed rule downloaded and unpacked (12 of 12). `glom.py`
finished all 12 (2 h 39 min in all). `kmask.py` read all 12 masks and linked the pixel size on 12 of 12, so the
2,000 um^2 floor was applied everywhere. No step failed, so this is a result, not an infrastructure failure, and the
gate (at least 10 of 12 complete slides) was met with 12.

D = glomeruli found by the five released HuBMAP "Hacking the Kidney" U-Nets; K_NS = KPMP's non-globally-sclerotic
glomerulus objects; K = both of KPMP's glomerulus classes.

## Grades

| Prediction | As written | Result | Verdict |
|---|---|---|---|
| B1 pooled count | sum(D) / sum(K_NS) in [0.80, 1.25] | 0.805 | **held** (just inside) |
| B2 per slide | abs(D - K_NS) <= max(3, 0.25 K_NS) on at least 8 of 12 slides | 8 of 12 | **held** (exactly at the bar) |
| B3 control for B2 | B2's count at least 2 above the mean over all 11 cyclic shifts | shifts: mean 1.273, max 3 | **held**, so B2 is informative |
| B4 the sclerotic class | sum(D) strictly closer to sum(K_NS) than to sum(K) (needs >= 5 sclerotic objects) | D / K = 0.679 vs D / K_NS = 0.805 | **held** |
| B5 rank agreement | Spearman's rho(D, K_NS) >= 0.50 | 0.977 | **held** |
| B6 size | pooled median area D / pooled median area K_NS in [0.70, 1.43] | 0.905 | **held** |

All 6 predictions held. Reported, not graded: globally sclerotic objects are **0.157** of KPMP's glomerulus objects on
these slides (0.230 on stage 3's four).

## What this says, and what it does not

- Stage 3's post-hoc reading holds on 12 new slides: the released HuBMAP models count **KPMP's non-sclerotic
  glomeruli**, not all of KPMP's glomeruli. That is what their training labels were built to do (Jain et al. 2023
  left sclerotic glomeruli out on purpose).
- Two results were close to their bars and should not be read as more than they are. The pooled ratio (0.805) is
  just above the 0.80 floor: the models still find about **one fifth fewer** glomeruli than KPMP's non-sclerotic class
  in total. B2 held with no slide to spare.
- The rank correlation is high partly because biopsies differ a lot in size, and both sides find more glomeruli in
  more tissue. The cyclic-shift control (B3) is the stronger evidence that slides agree with their own counts: the
  true pairing put 8 slides within tolerance against at most 3 for any shifted pairing.
- Counts can agree while objects do not. Whether the models find the **same** glomeruli, and whether they miss the
  sclerotic ones in particular, is stage 4's question (below).

## A data note (not graded, not investigated)

`kmask.py` also checks that each glomerulus channel's label count in KPMP's released mask equals the row count of the
matching sheet (`gloms`, `s_gloms`) in the same package's feature workbook. That held on **10 of 12** slides (4 of 4
in stage 3). On the other two, the mask and the workbook disagree for at least one class. We have not looked into why
(objects too small to survive in the pyramid level we read, a workbook built from a different mask version, or a
reader limit on our side are all possible), so this is a lead, not a finding about KPMP's data.

## Stage 4 status (dated note, 2026-11-10)

The pre-registered stage 4 (`findings/kidney-glom-stage4-prereg-v1-2026-11-10.md`, tag v0.9.66: object-by-object
matching on the same 12 slides, "is there a sclerotic blind spot?") was first run as job kidney-4-v1. It stopped at
its first step, before any slide was downloaded, because an old offline test in `kidney/test_compare.py` pinned
`glom.CODE_VERSION` to "0.1.1" and `glom.py` is now 0.2.0. That is an infrastructure failure, so per the plan it is
fixed and re-run, not graded: the test now checks only that the version is at least 0.1.1 (tag v0.9.67), and stage 4
runs again unchanged. No object position from these slides existed then or exists now. Stage 4's predictions are
untouched.

## Prior art and why this is new

Searches on 2026-11-09 and 2026-11-10 found patch-level external validation of HuBMAP-trained architectures on KPMP
(Zhang et al., arXiv 2406.16900, 2024; models retrained in its own pipeline, no split by sclerosis), and the
organisers' later multi-organ paper noting qualitatively that a kidney algorithm "sometimes ... predicts sclerotic
(diseased/unhealthy) glomeruli which were not included in the ground truth" (Nature Communications 2023,
PMC10400613). We found no published, pre-registered whole-slide test of the released winning weights against KPMP's
two glomerulus classes. That is a search result, not proof that none exists.

## Limits

Twelve biopsies from 12 participants (the rule keeps one package per participant), one stain. Both sides are models, not pathologists, so
agreement is not accuracy. The 1.5 um per pixel working scale is carried over from the competition's inference code.
The hypothesis came from stage 3's data; that is why it was tested on new slides chosen by a fixed rule.

## Reproduce

Tag v0.9.65, `python -m kidney.glom`, `python -m kidney.kmask`, `python -m kidney.compare3b` on the 12 open
"Seg_Masks_Features" v2 packages selected by the rule in the pre-registration (KPMP's open file list; packages are
chosen by sort order of their ids, so anyone with the list can rebuild the selection). Job settings as above.

## Acknowledgement

This work did not receive funding from the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) or the Kidney Precision Medicine Project (KPMP). However, it uses data generated by KPMP, and we acknowledge the support behind that data as follows.

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 10, 2026. https://www.kpmp.org.

The Kidney Precision Medicine Project (KPMP) is supported by the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) through the following grants: U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01, 1U01DK144994-01. We gratefully acknowledge the essential contributions of our patient participants and the support of the American public through their tax dollars.

(KPMP's requested wording, copied from https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata on
2026-11-11. On 2026-11-11 this section replaced an earlier paraphrase; nothing else in this note changed. See
`findings/kpmp-acknowledgement.md`.)

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028).
