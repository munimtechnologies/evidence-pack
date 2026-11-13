# kidney/: open glomerulus tools and pre-registered tests on KPMP whole-slide images

MV2 of Munim, Inc. (mv2@munimtech.com), 2026-11-13. Made with AI agents (Claude) working in MV2's name; no human
expert has reviewed this code or its results yet. Code Apache-2.0 (see LICENSE at the repository root); notes in
`findings/` are CC BY 4.0. Research code, not a medical device, not for diagnosis or patient care, not medical
advice.

This folder holds MV2's open work toward the NIDDK Kidney Artificial Intelligence Discovery Challenge
(https://www.herox.com/KidneyAI), which uses the open data of the Kidney Precision Medicine Project (KPMP). Every
step is pre-registered in `findings/` before its data are processed, then graded exactly as written, including the
predictions that failed. This README is an index: each module's docstring is the full description, and each
`findings/` note holds the numbers.

## Status at a glance (2026-11-13)

| Stage | Question | Pre-registration / results | Status |
|---|---|---|---|
| 1 | Slide quality checks on open KPMP .svs files | `findings/kidney-wsi-qc-v1-2026-11-07.md` | published |
| 2 | Do the released HuBMAP 2021 Deepflash2 kidney U-Nets run on KPMP slides? | `findings/kidney-glom-dryrun-*` | graded |
| 3 | Counts vs KPMP's released segmentation, 4 slides | `findings/kidney-glom-compare-*` | graded: pooled ratio 0.645 (failed), median-area ratio 0.986 (held) |
| 3b | Counts vs KPMP's NON-sclerotic glomeruli, 12 fresh slides | `findings/kidney-glom-stage3b-*` | graded: pooled ratio 0.805, all 6 predictions held |
| 4 | Object-by-object matching, by KPMP class | `findings/kidney-glom-stage4-*` | graded: non-sclerotic recall 0.734, globally sclerotic recall 0.000, precision 0.912 |
| 5 | Fine-tune one released U-Net on other biopsies' KPMP labels (3 classes) | `findings/kidney-glom-stage5-*` | graded: non-sclerotic recall 0.932, sclerotic recall 0.950 (held); precision 0.723 and sclerotic share (failed) |
| 6 | Do hard negatives fix stage 5's precision? 12 fresh biopsies | `findings/kidney-glom-stage6-prereg-v1-2026-11-11.md` | pre-registered; compute job queued |
| D1 | Does the detector's sclerotic share reproduce KPMP's own clinical gradient? | `findings/kidney-d1-prereg-v1-2026-11-12.md` | pre-registered; waits for stage 6 and the slide pass |
| D2 | Do unusual-looking non-sclerotic glomeruli track clinical fields beyond the sclerotic share? | `findings/kidney-d2-prereg-v1-2026-11-12.md` | pre-registered; waits for stage 6 and the slide pass |

Practical reading of stages 4 and 5: the released weights do not see globally sclerotic glomeruli at all, so their
output is not a total glomerulus count. The fine-tuned model finds both classes but over-calls: its extra detections
tend to be labelled sclerotic (sclerotic share 0.255 vs KPMP's 0.157 on the same slides), so its sclerotic calls
need a human check. Stage 6 tests one fix; its result will be published whether it holds or not.

## Modules

The one-command path (what the challenge's Docker re-run uses):

| Module | What it does |
|---|---|
| `pipeline.py` | A folder of .svs images in; per slide: QC (`wsi_qc`), glomerulus detection and labelling (`gsdet detect`), then QuPath annotations (`annot`); writes glomeruli.csv, slides.csv, inputs.csv (every input file with its SHA-256), qc.json, detections.json, annotations/ (one GeoJSON file per slide plus annot-report.json) and manifest.json |
| `Dockerfile` | CPU container for `pipeline.py`, pinned to the package versions the graded stage 5 job ran with |
| `wsi_qc.py` | Slide checks: pyramid, scanner pixel size, tissue fraction, tissue pieces, pen ink, focus |
| `glom.py` | Inference with the five released HuBMAP Deepflash2 kidney U-Nets (stages 2-4), following the organisers' inference code; counts 8-connected regions of at least 2,000 um^2 |
| `gsdet.py` | Stages 5-6: fine-tunes one released U-Net to 3 classes (background / non-sclerotic / globally sclerotic) on KPMP's open labels, mines hard negatives (stage 6), and detects |
| `annot.py` | Turns the pipeline's tables into one QuPath-importable GeoJSON file per slide (boxes in full-resolution pixels, coloured by class) so an expert can review every flagged region |
| `usage.py` | Writes the "KPMP images used and how" CSV the challenge asks for, from the lists the jobs really used, and fails on train/test leakage within a stage |

Graders and readers of KPMP's own labels:

| Module | What it does |
|---|---|
| `kmask.py` | Reads KPMP's released glomerulus segmentation (OME-TIFF label masks) into objects in micrometres |
| `compare.py`, `compare3b.py`, `compare4.py`, `compare5.py`, `compare6.py` | Grade stages 3, 3b, 4, 5 and 6 exactly as their pre-registrations say (matching: box IoU >= 0.5, greedy, one-to-one) |
| `d1.py`, `d2.py` | Grade the pre-registered D1 and D2 lanes |
| `anom.py`, `emb.py` | D2 building blocks: per-glomerulus encoder embeddings and a hand-crafted baseline, scores (k-NN, normal-reference Mahalanobis after NoRDeC, arXiv 2609.19444), a known-lesion AUROC gate, burden per participant |
| `prep.py`, `slidepass.py` | Run the D1/D2 slide pass in batches: one slide downloaded, processed and deleted at a time, names unique across batches, clean stop before each job's time limit |

Earlier KPMP studies (October 2026; each module's docstring names its question, and `findings/kpmp-*` hold the
pre-registrations and results): `kpmp_feasibility.py`, `kpmp_census.py`, `kpmp_census2.py`, `kpmp_census3.py`,
`kpmp_objects.py`, `kpmp_patches.py`, `kpmp_q2.py`, `kpmp_spread.py`, `kpmp_tbm0.py`, `kpmp_tbmsz.py`,
`kpmp_twins.py`, `kpmp_twinrel.py`, `kpmp_zs.py`, `kpmp_triage.py`, `kpmp_clinical_peek.py`, and two helpers,
`kpmp_subset.py` (keep one package version of KPMP's file list) and `kpmp_fill.py` (fill a job's data cache).

Every module has a `test_<module>.py` beside it. The standard-library parts are tested without numpy, torch or
OpenCV; tests that need torch skip themselves when it is missing.

## Running it

```
docker build -f kidney/Dockerfile -t mv2-kidney .
docker run --rm -v /path/to/svs:/input:ro -v /path/to/out:/output -v /path/to/gs.pth:/models/gs.pth:ro mv2-kidney
```

The offline tests can be run inside the image, with no network:

```
docker run --rm --network none --entrypoint python mv2-kidney -m unittest -v kidney.test_pipeline
```

The 3-class checkpoint (`gs.pth`) is written by `python -m kidney.gsdet train` and is not in this repository or the
image: fine-tuned weights are not published while KPMP's data terms for model sharing are being checked. Stage 5's
training took about 2 hours on CPU. The released HuBMAP weights it starts from are on Zenodo
(10.5281/zenodo.7730028, CC BY 4.0, team Deepflash2's models); the agent skill in `skills/kidney-glom-check/` shows
how to fetch only the files needed (about 300 MB) instead of the whole 16.5 GB archive.

Each slide's annotation file is GeoJSON in the form QuPath 0.3 and later imports; every glomerulus the detector flags is a box,
green for non-globally-sclerotic and red for globally sclerotic. `--no-annot` turns this step off and
`--annot-detections` writes lighter detection objects instead of annotations. The exit code reports detection
only; annotations/annot-report.json lists any slide that got no annotation file and why.

What has and has not been checked, as of 2026-11-13:

- Checked: the pipeline 0.1.0 image (release v0.9.81) was built from the tagged repository with Docker 29.1.3 on a
  Windows PC (Docker engine in WSL Ubuntu), about 396 MB, with torch 2.2.2+cpu, torchvision 0.17.2+cpu and numpy
  1.26.4 inside. Its 9 offline tests passed inside the image with no network and a 2 GB memory cap, none skipped;
  one of them runs the whole pipeline on a synthetic slide with random weights. `--help` works in the image. The
  first build attempt (release v0.9.80) failed at the torch install step; v0.9.81 fixed that, and the fix is kept.
- Checked: pipeline 0.2.0's standard-library tests, including the annotation step on invented records, passed
  in the automated check this release was committed through (no torch there, so its end-to-end test skipped).
- Not yet checked: building the 0.2.0 image (which adds `annot.py`) and running its tests inside it; running the
  pipeline on a real KPMP slide with a trained checkpoint; opening an annotation file in QuPath on a real slide.
  A separate compute job that runs the tests on python:3.10 with the pinned packages is queued. The modules the
  pipeline calls ran on real KPMP slides in the graded stage jobs above.

## Data rules

- Open KPMP data only. Results here are pooled aggregates and code. No images, crops, masks, embeddings, model
  weights trained on KPMP data, per-slide or per-participant values, package ids or file lists are published;
  those stay local under KPMP's data use terms.
- KPMP acknowledgement: `findings/kpmp-acknowledgement.md` (KPMP's own requested text, verbatim). KPMP and NIDDK
  have not reviewed or endorsed this work.
- Pre-registrations are never edited after publication; corrections go in dated addenda.

Questions and issues: open an issue on this repository or write to mv2@munimtech.com.
