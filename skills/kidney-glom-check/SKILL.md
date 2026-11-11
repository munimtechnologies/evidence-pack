---
name: kidney-glom-check
description: Use when counting or segmenting glomeruli on PAS-stained kidney whole-slide images (.svs) with the open HuBMAP "Hacking the Kidney" models, when running quality checks on a folder of kidney biopsy slides, or when judging glomerulus counts that came from these public weights. Gives one-command slide QC and glomerulus detection (CPU is enough), a 300 MB weights download instead of 16.5 GB, the measured limits from pre-registered tests on 12 independent KPMP biopsies - above all, the released Deepflash2 weights found none of the globally sclerotic glomeruli (recall 0.000) and about 73% of the non-sclerotic ones - and a tested CPU recipe that fine-tunes one of them on KPMP's open labels to find both classes (recall 0.950 sclerotic, 0.932 non-sclerotic, but precision 0.723 and an overstated sclerotic share).
license: Apache-2.0
---

# Kidney slide QC and glomerulus check (HuBMAP Deepflash2 weights)

Made with AI agents (Claude) working in MV2's name at Munim, Inc. Skill, script and pipeline code: Apache-2.0.
Results notes: CC BY 4.0. Source: https://github.com/munimtechnologies/evidence-pack (folder `kidney/`, notes in
`findings/kidney-glom-*`). Research code, not a medical device, not for diagnosis, not medical advice. No person at
Munim has reviewed the results, and the model authors and KPMP have not been contacted about them.

## When to use

- A user wants glomerulus counts, areas or positions from PAS-stained kidney biopsy whole-slide images (.svs) and
  asks for open models, or mentions HuBMAP, "Hacking the Kidney" or the Deepflash2 kidney weights.
- A user wants quick quality checks on a folder of .svs slides (pixel size, tissue, pen ink, focus) before analysis.
- You are about to interpret, compare or publish glomerulus counts made with these weights.
- A user wants the open weights to also find globally sclerotic glomeruli (Step 5).

## Step 1: know what the models count (read this before you report any number)

Pre-registered tests on 12 open KPMP biopsies (stages 3b, 4 and 5, November 2026), compared with KPMP's own released
segmentation, which labels non-globally-sclerotic (NS) and globally sclerotic (GS) glomeruli separately:

| Measure (box IoU >= 0.5 unless noted) | Released weights, 5 models (stage 4) | One model fine-tuned on KPMP labels (stage 5) |
|---|---|---|
| Recall of KPMP's NS glomeruli | 0.734 (0.777 at IoU 0.3) | 0.932 |
| Recall of KPMP's GS glomeruli | **0.000** (also 0.000 at IoU 0.3) | 0.950 |
| Precision (detections that are a KPMP glomerulus) | 0.912 (0.965 at IoU 0.3) | **0.723** (0.743 at IoU 0.3) |
| Class agreement on matched pairs (GS / NS) | no GS class | 0.965 / 0.990 |
| Pooled GS share, detections vs KPMP | not available | **0.255 vs 0.157** |
| Total detections / KPMP's NS count | 0.805 | - |
| Median box IoU of matched pairs | 0.813 (centre offset about 4 um per axis) | 0.938 |
| Recall of all KPMP glomeruli, both classes | about 0.62 (derived; GS share 0.157) | 0.935 |

What to tell the user:
- With the **released weights** the count is **not** a total glomerulus count. It leaves out globally sclerotic
  glomeruli entirely (the training labels excluded them on purpose; Jain et al., Communications Biology 2023), and it
  misses about a quarter of the others. Never compute a "percent globally sclerotic" from it.
- The **fine-tuned model** (Step 5) finds both classes, but about a quarter of what it reports matches no KPMP
  object, and those extras are mostly called sclerotic: only 0.460 of its "sclerotic" calls match a KPMP object,
  against 0.813 of its "non-sclerotic" calls. Its pooled sclerotic share overstated KPMP's by about 10 points, so do
  not report a "percent globally sclerotic" from it either without checking the sclerotic calls by eye. Nobody has yet
  checked what the extra objects are.
- These are research measurements on 12 biopsies, one stain, both sides being models. Say so. Notes:
  `findings/kidney-glom-stage4-results-v1-2026-11-10.md`, `findings/kidney-glom-stage5-results-v1-2026-11-11.md`.
- Nothing here is a diagnosis or a biopsy adequacy judgement; send clinical questions to a pathologist.

## Step 2: get the code and the weights

Run these from one working folder (`<skill-dir>` is where this SKILL.md is installed):

```
git clone --depth 1 --branch v0.9.71 https://github.com/munimtechnologies/evidence-pack.git ep
python <skill-dir>/scripts/zip_range.py --url https://zenodo.org/records/7730028/files/trained_models.zip \
  --out-dir weights-log --prefix models/5-deepflash/kidney/ --dest weights --max-bytes 400000000
```

`scripts/zip_range.py` (this skill; Python 3.8+, standard library only) reads the 16.5 GB Zenodo archive's central
directory with HTTP Range requests and extracts only the 8 Deepflash2 kidney files (about 300 MB), checking each
one's CRC-32. It stops at once if the server does not honour Range, and `--max-bytes` caps the selection. The five
files the pipeline uses end up in `weights/models/5-deepflash/kidney/unet_model-1.pth` ... `-5.pth`. Weights: CC BY
4.0 (Zenodo 10.5281/zenodo.7730028); original competition code MIT (github.com/cns-iu/ccf-research-kaggle-2021).

Python packages that ran the published results (Python 3.10, CPU):

```
pip install "numpy<2" six tifffile imagecodecs openpyxl opencv-python-headless==4.10.0.84
pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu
pip install segmentation-models-pytorch==0.3.3
```

## Step 3: run

From inside `ep/`:

```
python -m unittest kidney.test_wsi_qc kidney.test_glom              # offline tests, seconds
python -m kidney.wsi_qc --in-dir /slides --out-dir /out             # qc.csv + qc.json, one row per slide
python -m kidney.glom --in-dir /slides --out-dir /out --models ../weights/models/5-deepflash/kidney --threads 3
```

- Input: a folder of Aperio `.svs` files whose ImageDescription carries the pixel size (MPP). `wsi_qc` reports it;
  a slide without it cannot be scaled to the models' working resolution (1.5 um per pixel) and should be skipped.
- `glom.json` holds, per slide: `glomeruli` (count of regions >= 2,000 um^2), `areas_um2`, and `objects` as
  `[cx, cy, x0, y0, x1, y1, area]` in micrometres of the slide's full-resolution frame. No pixels are written.
- Time and memory: 12 KPMP biopsies took about 2 h 40 min of inference on 3 CPU cores with a peak of about 2 GB.
- Settings follow the competition's inference code (512-pixel tiles, step 0.8, flips, mean of five models,
  threshold 0.5). Changing them makes the numbers in Step 1 no longer apply.

## Step 4: compare with another segmentation (optional)

`kidney/compare4.py` matches two sets of objects by bounding-box IoU (greedy, one-to-one) and reports pooled recall
and precision with a cyclic slide-shift control. Its reader expects KPMP's mask format via `kidney/kmask.py`; for
other formats write the objects in the same `[cx, cy, x0, y0, x1, y1, area]` form. If you work with KPMP data, follow
its data use terms: publish aggregates only and cite KPMP as its citing page asks.

## Step 5: fine-tune for both classes (optional, CPU, about 2 hours)

No fine-tuned weights are published; the user trains their own from KPMP's open data (follow KPMP's data use terms).
Put each training biopsy's `<name>.svs` in one folder and KPMP's released segmentation `<name>.ome.tif` (two
channels: non-sclerotic and globally sclerotic glomeruli) in another, then from inside `ep/`:

```
python -m unittest kidney.test_gsdet kidney.test_compare5                       # offline tests
python -m kidney.gsdet crops --wsi /trwsi --masks /trmasks --out-dir /crops --diag crops-diag.json
python -m kidney.gsdet train --crops /crops --init ../weights/models/5-deepflash/kidney/unet_model-1.pth \
  --out gs5.pth --log train-log.json --threads 3
python -m kidney.gsdet detect --in-dir /slides --model gs5.pth --out det5.json --threads 3
```

- The measured run used 24 KPMP biopsies (96 sclerotic, 424 non-sclerotic and 600 random crops), 1,500 steps in
  104 minutes and a peak of 3.35 GB; detection on 12 biopsies took 25 minutes. Other data or settings change the
  numbers in Step 1.
- `det5.json` holds per slide `objects` (same form as above) and `classes` (`"ns"` or `"gs"`). Treat `"gs"` calls as
  candidates to check, not as a sclerosis count (Step 1).
- Keep any test biopsies out of the training folders, and never use a participant's biopsies on both sides.

## Report a problem

Open an issue in https://github.com/munimtechnologies/evidence-pack. Contact: MV2, Munim, Inc., mv2@munimtech.com.
