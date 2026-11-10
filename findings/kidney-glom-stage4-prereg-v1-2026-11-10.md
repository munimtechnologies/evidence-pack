# Pre-registration: object by object, which KPMP glomeruli do the open HuBMAP models find, and do they miss the sclerotic ones? (stage 4, v1)

MV2 of Munim, Inc., 2026-11-10. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code Apache-2.0. Research code and methods, not a medical device, not for diagnosis, not medical
advice.

Written and published **before any object position from these slides exists**. Code: `kidney/glom.py` 0.2.0 and
`kidney/kmask.py` 0.3.0 now also write each counted object's centroid and bounding box (counting is unchanged);
`kidney/compare4.py` 0.1.0 matches and grades. All three have offline tests that use invented numbers only
(`kidney/test_glom.py`, `kidney/test_kmask.py`, `kidney/test_compare4.py`).

## Why

Stages 3 and 3b compare **counts**. Counts can agree while the objects do not, and the stage 3 result
(`findings/kidney-glom-compare-results-v1-2026-11-09.md`) raised a sharper question. The released HuBMAP "Hacking
the Kidney" models were trained on labels that left out globally sclerotic glomeruli on purpose (Jain et al.,
Communications Biology 2023). The organisers' 2023 Nature Communications paper on their later multi-organ competition
(Jain et al., doi:10.1038/s41467-023-40291-0) notes that, for the kidney, "sometimes the algorithm predicts
sclerotic (diseased/unhealthy) glomeruli which were not included in the ground truth". So how often do these models detect a globally sclerotic glomerulus in an independent biopsy, compared with a
non-sclerotic one? KPMP's released segmentation labels the two classes separately, so this can be measured object
by object.

Prior work we found (search on 2026-11-10): a 2024 paper (arXiv 2406.16900) used the winning architecture as a
baseline, apparently trained in its own pipeline, and validated it on KPMP image patches. Its text does not split
glomeruli by sclerosis. We found no
object-level measurement of the **released** HuBMAP weights against KPMP's two glomerulus classes.

## Slides

These are the same 12 open KPMP "Segmentation Masks & Pathomics Vectors" packages that stage 3b selected by its
fixed rule (`findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md`; package ids stay private). Stage 3b's job was
still running when this was written, and none of its output had been read. That output holds counts only, never
positions. The stage 4 job downloads the packages again and re-runs both sides.

## Objects and matching (fixed now)

- **D:** `glom.py` 0.2.0 `objects`, the glomeruli it counts (same settings as stages 3 and 3b: 5-model mean
  probability at 0.5, 8-connected, area >= 2,000 um^2, working scale 1.5 um per pixel).
- **K:** `kmask.py` 0.3.0 `k_objects`, KPMP's objects after the same 2,000 um^2 floor: class "non-globally-sclerotic
  glomeruli" (NS) and class "globally-sclerotic glomeruli" (GS).
- **Frame:** micrometres from the top-left corner of the slide's full-resolution image. A box runs from the first
  pixel's edge to the last pixel's far edge. A centroid is the mean pixel index + 0.5. The KPMP mask is used only
  when its full-resolution size equals the slide's, as in stage 3.
- **Match:** on each slide, a D object and a K object can match when their bounding boxes overlap with IoU >= 0.5.
  Candidate pairs are taken greedily by IoU, highest first (ties: D index, then K index). Each object is used at
  most once. NS and GS objects are matched together in one pool.
- **Pooled rates:** recall(NS) = matched NS / all NS; recall(GS) likewise; precision = matched D / all D. All are
  pooled over complete slides.

## Predictions (graded exactly as written)

A slide is complete when it has both D objects and K objects (with pixel sizes linked). The predictions are graded
only if at least 10 of the 12 slides are complete. A setup or infrastructure failure is fixed and re-run, not
graded. Rates are graded unrounded and published to three decimals. All bounds are inclusive.

- **O1 (finds the normal ones):** recall(NS) >= 0.70.
- **O2 (what it finds is a glomerulus):** precision >= 0.70.
- **O3 (sclerotic blind spot, relative):** recall(NS) - recall(GS) >= 0.20.
- **O4 (sclerotic blind spot, absolute):** recall(GS) <= 0.50.
  O3 and O4 are graded only if the complete slides hold at least 10 GS objects in all.
- **O5 (control):** match D of slide i with K of slide i + s, for every non-zero cyclic shift s (11 shifts for 12
  slides). The mean pooled recall over all K objects is <= 0.10. If O5 fails, O1-O4 are reported as uninformative.
- **O6 (alignment):** over all matched pairs (at least 20), |median(K cx - D cx)| <= 8 um and
  |median(K cy - D cy)| <= 8 um. If O6 fails, the coordinate frames may disagree, and this is said beside O1-O4.

Why these thresholds: stage 3 found the two sides' glomerulus sizes agree (median-area ratio 0.986), and D's count
was about 0.84 of KPMP's NS count. If most D objects are the same glomeruli, recall(NS) should be near 0.75-0.85,
and a box IoU of 0.5 should hold for same-size objects whose centres are close. The GS predictions follow from the
training labels. They are a hypothesis, not a known result.

Reported, not graded: recall(GS) at IoU 0.5; the GS share of KPMP's objects; the median IoU of matched pairs; recall
and precision at IoU 0.3. As a reproducibility check, the job also re-runs stage 3b's grader on these outputs; its
result should equal stage 3b's own.

## What will be published

Only `compare4.py`'s aggregate output (rates and medians, no counts), the `kmask.py` aggregate line and the run
settings. No per-slide value, position, name, package id or image.

## Limits

These are 12 biopsies with one stain and one area floor. Both sides are models, not pathologists, so agreement is
not accuracy. A box IoU is cruder than a pixel IoU, and two touching glomeruli merged into one D region can match
at most one of them. A missed GS object may be a detection with a poor box rather than no detection; the IoU 0.3
figures help separate the two. The slides were chosen by stage 3b's rule, not for this question.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed November 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

HuBMAP models: Jain Y. et al., "Segmentation of human functional tissue units in support of a Human Reference
Atlas", Communications Biology 2023 (doi:10.1038/s42003-023-04848-5), and the "Hacking the Kidney" winning teams;
code MIT (github.com/cns-iu/ccf-research-kaggle-2021), weights CC BY 4.0 (Zenodo 10.5281/zenodo.7730028).
