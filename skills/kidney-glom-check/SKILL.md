---
name: kidney-glom-check
description: Use when counting or segmenting glomeruli on PAS-stained kidney whole-slide images (.svs) with the open HuBMAP "Hacking the Kidney" models, when running quality checks on a folder of kidney biopsy slides, or when judging glomerulus counts that came from these public weights. Gives one-command slide QC and glomerulus detection (CPU is enough), a 300 MB weights download instead of 16.5 GB, and the measured limits from pre-registered tests on 12 independent KPMP biopsies - above all, the released Deepflash2 weights found none of the globally sclerotic glomeruli (recall 0.000) and about 73% of the non-sclerotic ones.
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

## Step 1: know what the models count (read this before you report any number)

Pre-registered tests on 12 open KPMP biopsies (stages 3b and 4, November 2026), compared with KPMP's own released
segmentation, which labels non-globally-sclerotic (NS) and globally sclerotic (GS) glomeruli separately:

| Measure (box IoU >= 0.5 unless noted) | Result |
|---|---|
| Recall of KPMP's NS glomeruli | 0.734 (0.777 at IoU 0.3) |
| Recall of KPMP's GS glomeruli | **0.000** (also 0.000 at IoU 0.3) |
| Precision (detections that are a KPMP glomerulus) | 0.912 (0.965 at IoU 0.3) |
| Total detections / KPMP's NS count | 0.805 |
| Median box IoU of matched pairs; median centre offset | 0.813; about 4 um per axis |
| Recall of all KPMP glomeruli, both classes (derived) | about 0.62 on these slides (GS share 0.157) |

What to tell the user:
- The count is **not** a total glomerulus count. It leaves out globally sclerotic glomeruli entirely (the training
  labels excluded them on purpose; Jain et al., Communications Biology 2023), and it misses about a quarter of the
  others. Never compute a "percent globally sclerotic" from it.
- It is a research measurement from one team's weights on 12 biopsies, one stain, both sides being models. Say so.
  Notes: `findings/kidney-glom-stage3b-results-v1-2026-11-10.md`, `findings/kidney-glom-stage4-results-v1-2026-11-10.md`.
- Nothing here is a diagnosis or a biopsy adequacy judgement; send clinical questions to a pathologist.

## Step 2: get the code and the weights

Run these from one working folder (`<skill-dir>` is where this SKILL.md is installed):

```
git clone --depth 1 --branch v0.9.67 https://github.com/munimtechnologies/evidence-pack.git ep
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

## Report a problem

Open an issue in https://github.com/munimtechnologies/evidence-pack. Contact: MV2, Munim, Inc., mv2@munimtech.com.
