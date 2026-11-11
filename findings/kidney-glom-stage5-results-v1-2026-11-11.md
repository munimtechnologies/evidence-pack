# Results: one fine-tuned HuBMAP kidney U-Net finds 0.950 of KPMP's globally sclerotic glomeruli, but over-calls them (stage 5, v1; 4 of 6 predictions held)

MV2 of Munim, Inc., 2026-11-11. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Grades the pre-registered plan `findings/kidney-glom-stage5-prereg-v1-2026-11-10.md` (published at tag v0.9.70
before any training slide was downloaded for this purpose and before any stage 5 model or detection existed) exactly
as written. Code: `kidney/gsdet.py` 0.1.0 and `kidney/compare5.py` 0.1.0, with `kidney/glom.py` 0.2.0,
`kidney/kmask.py` 0.3.0 and `kidney/compare4.py` 0.1.0, cloned from tag v0.9.70. Per the KPMP data use terms, only
pooled rates are given: no per-slide value, count, position, name, package id, image or crop. The fine-tuned
weights are not published.

## The run

Job kidney-5-v1, one CPU job on 3 cores, started 10 November 2026 22:08 UTC and finished 11 November 00:31 UTC
(2 h 22 min; peak memory 3.35 GB). The 76 offline tests of the five kidney modules passed first. `gsdet.py select`
reproduced the 12 frozen test slides as the first 12 packages of the rule's list (no problems reported) and took
the next 24 as training slides; 24 of 24 downloaded. Training crops (pooled over the 24 slides): 96 around globally
sclerotic objects, 424 around non-sclerotic objects, 600 at random tissue points. Training ran the planned 1,500
steps in 103.6 minutes (plan: 1,500 steps or 240 minutes, whichever first); the mean loss over 50 steps went from
0.272 (first 50 steps) to 0.043 (last 50). Detection ran on 12 of 12 test slides (24.7 minutes); KPMP's masks were
read on 12 of 12. Gate (at least 10 complete slides and at least 300 steps): **held**.

## Grades

| Prediction | As written | Result | Verdict |
|---|---|---|---|
| P1 the sclerotic class is found | recall(GS) >= 0.50 (stage 4: 0.000) | 0.950 | **held** |
| P2 no loss on the normal class | recall(NS) >= 0.734 | 0.932 | **held** |
| P3 what it finds is a glomerulus | precision >= 0.80 | 0.723 | **failed** |
| P4 it names the class | matched GS called GS >= 0.70 and matched NS called NS >= 0.90 | 0.965 / 0.990 | **held** |
| P5 the biopsy-report number | abs(D GS share - K GS share) <= 0.05 | D 0.255 vs K 0.157 (diff 0.098) | **failed** |
| P6 control | mean pooled recall over the 11 cyclic slide shifts <= 0.10 | mean 0.000, max 0.003 | **held**, so P1-P5 are informative |

4 of 6 predictions held. Reported, not graded: recall of all KPMP glomeruli 0.935; both classes at 0.70: yes;
median box IoU of matched pairs 0.938; at box IoU 0.3: recall(NS) 0.963, recall(GS) 0.950, precision 0.743;
Spearman's rho between per-biopsy GS shares of D and K: 0.402 over 12 biopsies (one aggregate only; several
biopsies have few or no GS objects, so it says little).

## What this says

- **The blind spot can be taught away cheaply.** A single released Deepflash2 U-Net, fine-tuned for 104 CPU minutes
  on KPMP's own open segmentation of 24 other biopsies (only 96 sclerotic crops), went from recall 0.000 to 0.950 on
  KPMP's globally sclerotic glomeruli, and from 0.734 to 0.932 on the non-sclerotic ones. When it matches a KPMP
  object it names the class the way KPMP does (0.965 and 0.990). The comparison with stage 4 changes two things at
  once (fine-tuning, and one model instead of five), so the gain in P2 cannot be split between them.
- **It also finds things KPMP does not.** Precision fell from 0.912 (stage 4) to 0.723: the model reports about
  1.29 objects for every KPMP object, and loosening the match to box IoU 0.3 only lifts precision to 0.743, so most
  unmatched detections are not near-misses of a KPMP outline.
- **The extra objects are mostly the ones it calls sclerotic** (post-hoc breakdown of the graded tallies, not
  pre-registered): of detections called globally sclerotic, 0.460 match a KPMP object; of those called
  non-sclerotic, 0.813 do. About half of all unmatched detections (0.496) are called sclerotic. That is why P5
  failed: counting only matched detections, the GS share would be 0.162 against KPMP's 0.157. As built, the model
  would overstate "percent globally sclerotic", the number a biopsy report uses, by about 10 percentage points
  pooled.
- **What the unmatched detections are is not known.** They could be sclerotic glomeruli that KPMP's segmentation
  (itself a model output) left out, scarred or fibrotic tissue, vessels, or fragments. Nobody has looked at them;
  only review of the images by a pathologist could tell. Agreement with KPMP's segmentation is not accuracy.
- Internal consistency check (done before publishing): precision x (D objects / K objects) equals the recall of all
  K objects, since every match is one-to-one (0.723 x 1.29 = 0.935 within rounding).

## What comes next

These 12 biopsies have now been used to grade stages 3b, 4 and 5, so any change to the recipe made because of this
result (for example more random-tissue crops, a minimum sclerotic probability, or a size floor for the sclerotic
class) will be pre-registered and graded on a **fresh** set of biopsies (the next packages of stage 3b's fixed rule),
never re-tuned on these 12. The fine-tuned weights stay local for now.

## Limits

Twelve test biopsies, one stain (PAS). Both sides are models. One model, one seed, a short CPU run with 96
sclerotic training crops, labels from a coarser pyramid level on large slides (up to about 4 um per pixel). The
comparison with stage 4 changes two things at once. The post-hoc breakdown above was not pre-registered and is
reported as description only.

## Acknowledgement

This work did not receive funding from the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) or the Kidney Precision Medicine Project (KPMP). However, it uses data generated by KPMP, and we acknowledge the support behind that data as follows.

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 10, 2026. https://www.kpmp.org.

The Kidney Precision Medicine Project (KPMP) is supported by the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK) through the following grants: U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01, 1U01DK144994-01. We gratefully acknowledge the essential contributions of our patient participants and the support of the American public through their tax dollars.

(KPMP's requested wording, copied from https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata on
2026-11-11. On 2026-11-11 this section replaced an earlier paraphrase; nothing else in this note changed. See
`findings/kpmp-acknowledgement.md`.)

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028). The
weights used here are team Deepflash2's.
