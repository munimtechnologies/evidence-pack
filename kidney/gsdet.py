#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""gsdet: stages 5 and 6 of MV2's open kidney pipeline. Teach one released HuBMAP Deepflash2 kidney U-Net to find and
label globally sclerotic glomeruli, which the released weights miss entirely (stage 4: recall 0.000 on 12 KPMP
biopsies), and (stage 6) test whether hard negatives mined from the model's own false detections fix its precision.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Stage 5: findings/kidney-glom-stage5-prereg-v1-2026-11-10.md (0.1.0, graded by kidney/compare5.py).
Stage 6: findings/kidney-glom-stage6-prereg-v1-2026-11-11.md (0.2.0, graded by kidney/compare6.py). Both were
published before any of their training or test output existed. 0.2.0 keeps every stage 5 default, so the stage 5
recipe (arm A of stage 6) is unchanged.

Recipe (fixed in the pre-registrations; nothing is tuned on the test slides):
- Training slides: stage 3b's selection rule (findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md) applied to
  KPMP's open file list without the final cut. Its first 12 packages must be exactly the frozen stage 3b/4 test
  slides (checked; the job stops otherwise); the training set is the next N_TRAIN packages, none from a test
  participant. Stage 6's fresh test set is the next N_TEST packages after those (`select-test`, which also checks
  that the training packages are exactly stage 5's).
- Labels: KPMP's released segmentation, 0 background, 1 non-globally-sclerotic glomerulus, 2 globally sclerotic,
  read from the mask pyramid level kidney/kmask.py reads and resized (nearest neighbour) to the working image at
  1.5 um per pixel, the scale of kidney/glom.py.
- Crops: CROP x CROP pixels around every globally sclerotic object (up to 50 per slide), up to 25 non-sclerotic
  objects and up to 25 random tissue points per slide (objects of at least 2,000 um^2; centres moved at random by
  up to JITTER pixels).
- Hard negatives (stage 6, `hard`): a trained model is run over each training slide exactly as `detect` does; every
  detected region of at least 2,000 um^2 with less than HARD_MAX_OVERLAP of its pixels on a KPMP glomerulus (either
  class) is a candidate, and up to HARD_CAP of them per slide (random order) become crops of kind "hard", labelled
  from KPMP's segmentation like every other crop.
- Model: smp.Unet(efficientnet-b2) started from unet_model-1.pth of the released Deepflash2 kidney weights, its
  2-class head widened to 3 classes (the new class starts as a copy of the glomerulus class). Batch-norm layers stay
  in inference mode. Adam, learning rate 1e-4, class weights (1, 1, 2), batches of 8 random PATCH x PATCH windows
  with random 90-degree turns and flips, crop kinds drawn with probabilities KIND_PROBS (GS 0.4, NS 0.3, random 0.3;
  stage 6 arm B: KIND_PROBS_B); STEPS steps or MINUTES minutes, whichever comes first. Seed 5.
- Detection: kidney/glom.py's tiling (512-pixel tiles at 1.5 um, step 0.8, Gaussian blending, empty-tile rule),
  this one model with horizontal and vertical flips. A glomerulus is an 8-connected region where P(background) < 0.5
  with an area of at least 2,000 um^2; it is globally sclerotic when its summed P(GS) exceeds its summed P(NS).

Outputs stay local (KPMP data use terms): crop files, trained models and detection files are never published; the
command line prints aggregates only. Standard-library parts and their tests run without numpy, torch or OpenCV.
Usage:
  python -m kidney.gsdet select --csv files.csv --exclude excluded.json --frozen slides.json --out train.json
  python -m kidney.gsdet select-test --csv files.csv --exclude excluded.json --frozen slides.json \
      --train stage5-train.json --out test.json
  python -m kidney.gsdet crops --wsi /trwsi --masks /trmasks --out-dir /crops [--diag d.json] [--delete]
  python -m kidney.gsdet hard --wsi /trwsi --masks /trmasks --model a.pth --out-dir /hard [--diag d.json] [--delete]
  python -m kidney.gsdet train --crops /crops [/hard] --init unet_model-1.pth --out m.pth [--kind-probs gs=0.4,...]
  python -m kidney.gsdet detect --in-dir /wsi --model m.pth --out det.json
"""
import argparse
import csv
import json
import os
import time

CODE_VERSION = "0.2.0"
V2_SUFFIX = "_Seg_Masks_Features_v2.zip"
MAX_MB = 300.0
N_TRAIN = 24
N_TEST = 12
MIN_TEST = 10
TEST_PREFIX = "test6"
CROP = 288
PATCH = 256
JITTER = 32
CAPS = (("gs", 50), ("ns", 25), ("rand", 25))
KIND_CODE = {"rand": 0, "ns": 1, "gs": 2, "hard": 3}
KIND_PROBS = (("gs", 0.4), ("ns", 0.3), ("rand", 0.3))
KIND_PROBS_B = (("gs", 0.35), ("ns", 0.25), ("rand", 0.2), ("hard", 0.2))
HARD_CAP = 25
HARD_MAX_OVERLAP = 0.10
HARD_SEED_OFFSET = 500
CLASS_WEIGHTS = (1.0, 1.0, 2.0)
LR = 1e-4
STEPS = 1500
MINUTES = 240.0
BATCH = 8
SEED = 5
TISSUE_STRIDE = 16
FG_MAX_BG = 0.5
MASK_SUFFIX = ".ome.tif"


# ---- standard-library parts ----

def size_mb(text):
    """Size in MB from KPMP's file list ('57.6 MB', '1.06 GB', '980 KB'); 1 GB = 1000 MB. None if unreadable."""
    parts = str(text).strip().split()
    if len(parts) != 2:
        return None
    try:
        v = float(parts[0])
    except ValueError:
        return None
    scale = {"B": 1e-6, "KB": 1e-3, "MB": 1.0, "GB": 1000.0, "TB": 1e6}.get(parts[1].upper())
    return None if scale is None else v * scale


def select_packages(rows, exclude_packages=(), max_mb=MAX_MB, suffix=V2_SUFFIX):
    """Stage 3b's selection rule without its final cut. `rows` are dicts with KPMP's column names. Keeps open
    packages whose file name ends in `suffix`, drops the excluded packages and every package of their participants,
    drops packages over `max_mb`, sorts by package id (ascending) and keeps the first package of each participant.
    Returns the kept rows in that order."""
    excl = set(exclude_packages)
    excl_part = set(r["Participant ID"] for r in rows if r["Internal Package ID"] in excl)
    keep = []
    for r in rows:
        if str(r.get("Access", "")).strip().lower() != "open":
            continue
        if not str(r["File Name"]).endswith(suffix):
            continue
        if r["Internal Package ID"] in excl or r["Participant ID"] in excl_part:
            continue
        mb = size_mb(r.get("Size", ""))
        if mb is None or mb > max_mb:
            continue
        keep.append(r)
    keep.sort(key=lambda r: (r["Internal Package ID"], r["File Name"]))
    seen, out = set(), []
    for r in keep:
        if r["Participant ID"] in seen:
            continue
        seen.add(r["Participant ID"])
        out.append(r)
    return out


def split(rows, selected, frozen, n_train=N_TRAIN):
    """(training rows, problems). The first len(frozen) selected packages must be exactly the frozen test packages,
    in order; the training set is the next n_train selected packages, and none may come from a participant of any
    frozen test package (looked up in all `rows`)."""
    n = len(frozen)
    problems = []
    if [r["Internal Package ID"] for r in selected[:n]] != list(frozen):
        problems.append("the rule does not reproduce the frozen test list")
    frozen_set = set(frozen)
    test_parts = set(r["Participant ID"] for r in rows if r["Internal Package ID"] in frozen_set)
    train = selected[n:n + n_train]
    if any(r["Participant ID"] in test_parts for r in train):
        problems.append("a training package comes from a test participant")
    if len(train) < n_train:
        problems.append("only %d training packages" % len(train))
    return train, problems


def fresh_split(rows, selected, frozen, train_ids, n_test=N_TEST, min_test=MIN_TEST):
    """(fresh test rows, problems) for stage 6. The selected list must start with exactly the frozen packages and
    then exactly the training packages `train_ids`, in order; the fresh test set is the next n_test packages. It
    needs at least min_test packages, and none may come from a participant of a frozen or training package (looked
    up in all `rows`)."""
    ids = [r["Internal Package ID"] for r in selected]
    n, t = len(frozen), len(train_ids)
    problems = []
    if ids[:n] != list(frozen):
        problems.append("the rule does not reproduce the frozen test list")
    if ids[n:n + t] != list(train_ids):
        problems.append("the rule does not reproduce the stage 5 training list")
    test = selected[n + t:n + t + n_test]
    if len(test) < min_test:
        problems.append("only %d test packages" % len(test))
    used = set(frozen) | set(train_ids)
    used_parts = set(r["Participant ID"] for r in rows if r["Internal Package ID"] in used)
    if any(r["Participant ID"] in used_parts for r in test):
        problems.append("a test package comes from a frozen or training participant")
    return test, problems


def fetch_list(rows, prefix="train"):
    """The job's download list: [{"slide": "<prefix>01", "package": ..., "name": ...}] in list order."""
    return [{"slide": "%s%02d" % (prefix, i + 1), "package": r["Internal Package ID"], "name": r["File Name"]}
            for i, r in enumerate(rows)]


def parse_probs(text):
    """Crop-kind probabilities from 'gs=0.35,ns=0.25,rand=0.2,hard=0.2', as ((kind, p), ...) in the order given.
    Raises ValueError for an unknown or repeated kind, a negative or unreadable value, or an all-zero list."""
    out, seen = [], set()
    for part in str(text).split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError("expected kind=probability, got %r" % part)
        k, v = (s.strip() for s in part.split("=", 1))
        if k not in KIND_CODE or k in seen:
            raise ValueError("unknown or repeated kind %r" % k)
        p = float(v)
        if not p >= 0.0:
            raise ValueError("negative probability for %r" % k)
        seen.add(k)
        out.append((k, p))
    if not out or sum(p for _, p in out) <= 0.0:
        raise ValueError("no positive probability")
    return tuple(out)


def pick_kind(u, available, probs=KIND_PROBS):
    """The crop kind for a uniform draw u in [0, 1): `probs` renormalised over the kinds in `available`, taken in
    the order of `probs`. None if none is available."""
    items = [(k, p) for k, p in probs if k in available and p > 0]
    if not items:
        return None
    total = sum(p for _, p in items)
    acc = 0.0
    for k, p in items:
        acc += p / total
        if u < acc:
            return k
    return items[-1][0]


def crop_origin(cx, cy, size=CROP, jx=0, jy=0):
    """(left, top) of a size x size window centred on pixel-index point (cx, cy), moved by (jx, jy)."""
    return int(round(cx)) - size // 2 + jx, int(round(cy)) - size // 2 + jy


def class_of(score):
    """'gs' when a region's summed (P(GS) - P(NS)) is positive, else 'ns'."""
    return "gs" if score > 0 else "ns"


def slide_pairs(wsi_dir, mask_dir):
    """Slide names with both <name>.svs in wsi_dir and <name>.ome.tif in mask_dir, sorted."""
    svs = set(os.path.splitext(f)[0] for f in os.listdir(wsi_dir) if f.lower().endswith(".svs"))
    masks = set(f[:-len(MASK_SUFFIX)] for f in os.listdir(mask_dir) if f.lower().endswith(MASK_SUFFIX))
    return sorted(svs & masks)


def crops_aggregate(diag):
    """Totals over slides only (no names, no per-slide values)."""
    ok = [r for r in diag.values() if r.get("ok")]
    tot = {k: sum(r["crops"].get(k, 0) for r in ok) for k in KIND_CODE}
    out = {"code_version": CODE_VERSION, "slides": len(diag), "ok": len(ok), "crops": tot}
    if any("hard_found" in r for r in ok):
        out["hard_found"] = sum(r.get("hard_found", 0) for r in ok)
    return out


# ---- numpy / OpenCV / tifffile parts ----

def crop(a, left, top, size, fill):
    """size x size window of array `a` (H x W or H x W x C) at (left, top); outside the array is `fill`."""
    import numpy as np
    h, w = a.shape[:2]
    out = np.full((size, size) + tuple(a.shape[2:]), fill, dtype=a.dtype)
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(w, left + size), min(h, top + size)
    if x1 > x0 and y1 > y0:
        out[y0 - top:y1 - top, x0 - left:x1 - left] = a[y0:y1, x0:x1]
    return out


def centers(cmap, img, mpp, rng, caps=CAPS, stride=TISSUE_STRIDE):
    """[(kind, cx, cy)] crop centres of one slide in pixel-index coordinates of the working image: the centroids of
    up to `cap` objects of each glomerulus class (8-connected regions of at least MIN_AREA_UM2, in random order), and
    up to `cap` random tissue points (HSV saturation > S_TH on a grid of `stride` pixels)."""
    import cv2
    import numpy as np
    from kidney.glom import MIN_AREA_UM2, S_TH
    floor_px = MIN_AREA_UM2 / (mpp * mpp)
    out = []
    for kind, cap in caps:
        if kind == "rand":
            sub = np.ascontiguousarray(img[::stride, ::stride, :3])
            sat = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)[..., 1]
            ys, xs = np.nonzero(sat > S_TH)
            if ys.size == 0:
                continue
            pick = rng.choice(ys.size, size=min(cap, ys.size), replace=False)
            out.extend(("rand", float(xs[i] * stride), float(ys[i] * stride)) for i in pick)
            continue
        binary = (cmap == KIND_CODE[kind]).astype(np.uint8)
        n, _, stats, cents = cv2.connectedComponentsWithStats(binary, connectivity=8)
        del binary
        idx = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= floor_px]
        rng.shuffle(idx)
        out.extend((kind, float(cents[i, 0]), float(cents[i, 1])) for i in idx[:cap])
    return out


def crops_at(img, cmap, cents, rng):
    """(images, label maps, kind codes) of crops around the centres `cents` [(kind, cx, cy)], each moved at random
    by up to JITTER pixels."""
    xs, ys, kinds = [], [], []
    for kind, cx, cy in cents:
        jx, jy = (int(v) for v in rng.randint(-JITTER, JITTER + 1, size=2))
        left, top = crop_origin(cx, cy, CROP, jx, jy)
        xs.append(crop(img[..., :3], left, top, CROP, 255))
        ys.append(crop(cmap, left, top, CROP, 0))
        kinds.append(KIND_CODE[kind])
    return xs, ys, kinds


def slide_crops(img, cmap, mpp, rng, caps=CAPS):
    """(images, label maps, kind codes) of one slide's crops (the same random draws as gsdet 0.1.0)."""
    return crops_at(img, cmap, centers(cmap, img, mpp, rng, caps), rng)


def hard_centers(pbg, cmap, mpp, rng, cap=HARD_CAP, max_overlap=HARD_MAX_OVERLAP, strip_rows=1024):
    """([("hard", cx, cy)], candidates): centroids of up to `cap` detected regions (8-connected, P(background) <
    FG_MAX_BG, at least MIN_AREA_UM2) of which fewer than `max_overlap` of the pixels lie on a KPMP glomerulus of
    either class (cmap > 0), in random order, and the number of such candidate regions before the cap."""
    import cv2
    import numpy as np
    from kidney.glom import MIN_AREA_UM2
    floor_px = MIN_AREA_UM2 / (mpp * mpp)
    fg = (pbg < FG_MAX_BG).astype(np.uint8)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(fg, connectivity=8)
    del fg
    on = np.zeros(n, dtype="float64")
    for r in range(0, labels.shape[0], strip_rows):
        lab = labels[r:r + strip_rows].ravel()
        w = (cmap[r:r + strip_rows] > 0).ravel().astype("float64")
        on += np.bincount(lab, weights=w, minlength=n)[:n]
    idx = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= floor_px
           and on[i] < max_overlap * float(stats[i, cv2.CC_STAT_AREA])]
    found = len(idx)
    rng.shuffle(idx)
    return [("hard", float(cents[i, 0]), float(cents[i, 1])) for i in idx[:cap]], found


def read_class_map(path, size0, width, height):
    """uint8 label map (0 background, 1 non-sclerotic, 2 globally sclerotic) of KPMP's OME-TIFF mask at the working
    image's (width, height). The mask's level 0 must have the slide's level-0 (width, height) `size0`."""
    import cv2
    import numpy as np
    import tifffile
    from kidney.kmask import channel_kinds, ome_channel_names, pick_level
    out = np.zeros((height, width), dtype=np.uint8)
    with tifffile.TiffFile(path) as tif:
        s = tif.series[0]
        axes = str(getattr(s, "axes", ""))
        if not (axes.endswith("YX") and "C" in axes and len(s.shape) == 3):
            raise ValueError("expected CYX axes, got %r %r" % (axes, s.shape))
        kinds = channel_kinds(ome_channel_names(tif.pages[0].description or ""))
        levels = list(getattr(s, "levels", [s]))
        shapes = [(lv.shape[-2], lv.shape[-1]) for lv in levels]
        if (int(shapes[0][1]), int(shapes[0][0])) != (int(size0[0]), int(size0[1])):
            raise ValueError("mask level 0 %r differs from the slide's %r" % (shapes[0], tuple(size0)))
        li = pick_level(shapes)
        for c, kind in sorted(kinds.items()):
            try:
                plane = levels[li].pages[c].asarray()
            except Exception:  # noqa: BLE001  (fall back to tifffile's own page selection)
                plane = levels[li].asarray(key=c)
            m = (np.asarray(plane).reshape(shapes[li]) > 0).astype(np.uint8)
            del plane
            m = cv2.resize(m, (int(width), int(height)), interpolation=cv2.INTER_NEAREST)
            out[m > 0] = KIND_CODE["ns"] if kind == "glom" else KIND_CODE["gs"]
    return out


def _save_npz(path, xs, ys, kinds):
    import numpy as np
    x = np.stack(xs) if xs else np.zeros((0, CROP, CROP, 3), np.uint8)
    y = np.stack(ys) if ys else np.zeros((0, CROP, CROP), np.uint8)
    np.savez(path, x=x, y=y, k=np.asarray(kinds, dtype=np.uint8))


def run_crops(wsi_dir, mask_dir, out_dir, seed=SEED, delete=False, caps=CAPS):
    """Write <slide>.npz (x: crops, y: labels, k: kinds) per slide into out_dir; returns the local diagnostics."""
    import numpy as np
    from kidney.glom import slide_image
    os.makedirs(out_dir, exist_ok=True)
    diag = {}
    for i, name in enumerate(slide_pairs(wsi_dir, mask_dir)):
        t0 = time.time()
        svs, mask = os.path.join(wsi_dir, name + ".svs"), os.path.join(mask_dir, name + MASK_SUFFIX)
        rec = {"ok": False, "errors": []}
        try:
            img, mpp, _, _, size0 = slide_image(svs)
            cmap = read_class_map(mask, size0, img.shape[1], img.shape[0])
            rng = np.random.RandomState(seed * 1000 + i)
            xs, ys, kinds = slide_crops(img, cmap, mpp, rng, caps)
            del img, cmap
            _save_npz(os.path.join(out_dir, name + ".npz"), xs, ys, kinds)
            rec.update(ok=True, mpp=round(mpp, 4), crops={k: kinds.count(c) for k, c in KIND_CODE.items()})
        except Exception as e:  # one bad slide must not stop the folder
            rec["errors"].append(repr(e)[:300])
        if delete:
            for p in (svs, mask):
                if os.path.exists(p):
                    os.remove(p)
        rec["seconds"] = round(time.time() - t0, 1)
        diag[name] = rec
    return diag


def run_hard(wsi_dir, mask_dir, model_path, out_dir, seed=SEED, cap=HARD_CAP, delete=False, tta=True):
    """Stage 6 hard negatives: run the model at `model_path` over each training slide as `detect` does and write
    <slide>.npz of "hard" crops (see hard_centers) into out_dir; returns the local diagnostics."""
    import numpy as np
    from kidney.glom import slide_image
    model, mean, std, _ = load_model3(model_path)
    os.makedirs(out_dir, exist_ok=True)
    diag = {}
    for i, name in enumerate(slide_pairs(wsi_dir, mask_dir)):
        t0 = time.time()
        svs, mask = os.path.join(wsi_dir, name + ".svs"), os.path.join(mask_dir, name + MASK_SUFFIX)
        rec = {"ok": False, "errors": []}
        try:
            img, mpp, _, _, size0 = slide_image(svs)
            cmap = read_class_map(mask, size0, img.shape[1], img.shape[0])
            pbg, _, _, _ = predict3(img, model, mean, std, tta=tta)
            rng = np.random.RandomState(seed * 1000 + HARD_SEED_OFFSET + i)
            cents, found = hard_centers(pbg, cmap, mpp, rng, cap)
            del pbg
            xs, ys, kinds = crops_at(img, cmap, cents, rng)
            del img, cmap
            _save_npz(os.path.join(out_dir, name + ".npz"), xs, ys, kinds)
            rec.update(ok=True, mpp=round(mpp, 4), hard_found=found,
                       crops={k: kinds.count(c) for k, c in KIND_CODE.items()})
        except Exception as e:  # one bad slide must not stop the folder
            rec["errors"].append(repr(e)[:300])
        if delete:
            for p in (svs, mask):
                if os.path.exists(p):
                    os.remove(p)
        rec["seconds"] = round(time.time() - t0, 1)
        diag[name] = rec
    return diag


def draw_indices(kinds, batch, rng, probs=KIND_PROBS):
    """`batch` crop indices: a kind drawn with pick_kind, then a crop of that kind uniformly."""
    import numpy as np
    kinds = np.asarray(kinds)
    pools = {k: np.nonzero(kinds == KIND_CODE[k])[0] for k, _ in probs}
    avail = set(k for k, v in pools.items() if v.size)
    out = []
    for _ in range(batch):
        pool = pools[pick_kind(float(rng.random_sample()), avail, probs)]
        out.append(int(pool[rng.randint(0, pool.size)]))
    return out


def make_batch(xs, ys, idx, rng, mean, std, patch=PATCH):
    """(N x 3 x patch x patch float32 normalised images, N x patch x patch int64 labels): a random window of each
    crop, turned by a random multiple of 90 degrees and flipped left-right with probability 1/2."""
    import numpy as np
    span = xs.shape[1] - patch
    bx, by = [], []
    for i in idx:
        ox, oy = (int(v) for v in rng.randint(0, span + 1, size=2))
        x = xs[i, oy:oy + patch, ox:ox + patch]
        y = ys[i, oy:oy + patch, ox:ox + patch]
        k = int(rng.randint(0, 4))
        x, y = np.rot90(x, k, axes=(0, 1)), np.rot90(y, k, axes=(0, 1))
        if int(rng.randint(0, 2)):
            x, y = x[:, ::-1], y[:, ::-1]
        bx.append(np.ascontiguousarray(x))
        by.append(np.ascontiguousarray(y))
    xb = (np.stack(bx).astype("float32") / 255.0 - mean) / std
    return np.ascontiguousarray(xb.transpose(0, 3, 1, 2).astype("float32")), np.stack(by).astype("int64")


# ---- torch parts ----

def new_model(classes=3):
    import segmentation_models_pytorch as smp
    return smp.Unet(encoder_name="efficientnet-b2", encoder_weights=None, in_channels=3, classes=classes)


def expand_head(state_dict, n_classes=3, copy_from=1):
    """A 2-class state dict with its segmentation head widened to n_classes; each new class starts as a copy of
    class `copy_from`. Other tensors are unchanged."""
    import torch
    out = {}
    for k, v in state_dict.items():
        if k.startswith("segmentation_head.") and getattr(v, "ndim", 0) >= 1 and v.shape[0] == 2:
            v = torch.cat([v] + [v[copy_from:copy_from + 1]] * (n_classes - 2), dim=0)
        out[k] = v
    return out


def load_init(path):
    """(state dict without a DataParallel prefix, mean, std) of a released Deepflash2 checkpoint."""
    import numpy as np
    import torch
    from kidney.glom import strip_prefix
    state = torch.load(path, map_location="cpu", weights_only=False)
    if not (isinstance(state, dict) and "stats" in state):
        raise ValueError("no 'stats' (mean, std) in the checkpoint")
    sd = state["model"] if "model" in state else state
    mean, std = (np.asarray(s, dtype="float32").reshape(-1) for s in state["stats"])
    return strip_prefix(sd), mean, std


def freeze_bn(model):
    """Put every batch-norm layer in inference mode (running statistics fixed); returns how many."""
    import torch
    n = 0
    for m in model.modules():
        if isinstance(m, torch.nn.modules.batchnorm._BatchNorm):
            m.eval()
            n += 1
    return n


def train_step(model, opt, xb, yb, weight):
    import torch
    import torch.nn.functional as F
    logits = model(torch.from_numpy(xb))
    loss = F.cross_entropy(logits, torch.from_numpy(yb), weight=weight)
    opt.zero_grad()
    loss.backward()
    opt.step()
    return float(loss.item())


def load_crops(crops_dirs):
    """(images, labels, kinds) of every .npz in one folder or a list of folders (folders in the order given, files
    sorted by name within each)."""
    import numpy as np
    if isinstance(crops_dirs, str):
        crops_dirs = [crops_dirs]
    xs, ys, ks = [], [], []
    for d in crops_dirs:
        for f in sorted(f for f in os.listdir(d) if f.endswith(".npz")):
            with np.load(os.path.join(d, f)) as z:
                if z["x"].shape[0]:
                    xs.append(z["x"])
                    ys.append(z["y"])
                    ks.append(z["k"])
    if not xs:
        raise ValueError("no crops in %s" % ", ".join(crops_dirs))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ks)


def train(crops_dirs, init_path, out_path, steps=STEPS, minutes=MINUTES, batch=BATCH, seed=SEED, log=None,
          probs=KIND_PROBS):
    """Fine-tune as the module docstring says and save {"model", "stats", "classes", "steps"} to out_path. Returns
    a summary with the loss log (means over 50 steps)."""
    import numpy as np
    import torch
    xs, ys, ks = load_crops(crops_dirs)
    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)
    sd, mean, std = load_init(init_path)
    model = new_model(3)
    model.load_state_dict(expand_head(sd), strict=True)
    model.train()
    n_bn = freeze_bn(model)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    weight = torch.tensor(CLASS_WEIGHTS, dtype=torch.float32)
    t0, losses, rows = time.time(), [], []
    for _ in range(steps):
        if (time.time() - t0) / 60.0 >= minutes:
            break
        idx = draw_indices(ks, batch, rng, probs)
        xb, yb = make_batch(xs, ys, idx, rng, mean, std)
        losses.append(train_step(model, opt, xb, yb, weight))
        if len(losses) % 50 == 0:
            row = {"step": len(losses), "loss50": round(sum(losses[-50:]) / 50.0, 4),
                   "minutes": round((time.time() - t0) / 60.0, 1)}
            rows.append(row)
            if log:
                log(json.dumps(row))
    torch.save({"model": model.state_dict(), "stats": [mean, std], "classes": 3, "steps": len(losses),
                "code_version": CODE_VERSION}, out_path)
    return {"code_version": CODE_VERSION, "crops": int(xs.shape[0]),
            "crops_by_kind": {k: int((ks == c).sum()) for k, c in KIND_CODE.items()}, "bn_frozen": n_bn,
            "kind_probs": [[k, p] for k, p in probs],
            "steps": len(losses), "minutes": round((time.time() - t0) / 60.0, 1), "log": rows,
            "first_loss": round(losses[0], 4) if losses else None}


def load_model3(path):
    """(model in eval mode, mean, std, training steps) from a checkpoint written by train()."""
    import numpy as np
    import torch
    state = torch.load(path, map_location="cpu", weights_only=False)
    model = new_model(int(state.get("classes", 3)))
    model.load_state_dict(state["model"], strict=True)
    model.eval()
    mean, std = (np.asarray(s, dtype="float32").reshape(-1) for s in state["stats"])
    return model, mean, std, int(state.get("steps", 0))


def predict3(img, model, mean, std, tta=True):
    """(P(background), P(globally sclerotic), tiles used, tiles skipped): float32 maps with img's height and width,
    blended over tiles as in kidney/glom.py. Pixels no tile covered get P(background) 1 and P(GS) 0."""
    import cv2
    import numpy as np
    import torch
    from kidney.glom import P_TH, S_TH, TILE, gaussian_weight, tile_starts
    img = img[..., :3]
    h, w = img.shape[:2]
    ph, pw = max(h, TILE), max(w, TILE)
    if (ph, pw) != (h, w):
        pad = np.full((ph, pw, 3), 255, dtype=img.dtype)
        pad[:h, :w] = img
        img = pad
    bg = np.zeros((ph, pw), dtype="float32")
    gs = np.zeros((ph, pw), dtype="float32")
    wsum = np.zeros((ph, pw), dtype="float32")
    gw = gaussian_weight()
    flips = [None, 3, 2] if tta else [None]
    used = skipped = 0
    for y in tile_starts(ph):
        for x in tile_starts(pw):
            tile = img[y:y + TILE, x:x + TILE]
            sat = cv2.cvtColor(np.ascontiguousarray(tile), cv2.COLOR_RGB2HSV)[..., 1]
            if (sat > S_TH).sum() <= P_TH or tile.sum() <= P_TH:
                skipped += 1
                continue
            used += 1
            t = (tile.astype("float32") / 255.0 - mean) / std
            x_t = torch.from_numpy(np.ascontiguousarray(t.transpose(2, 0, 1).astype("float32")))[None]
            acc = torch.zeros((3, TILE, TILE))
            with torch.no_grad():
                for f in flips:
                    inp = x_t if f is None else torch.flip(x_t, dims=[f])
                    out = torch.softmax(model(inp), dim=1)
                    if f is not None:
                        out = torch.flip(out, dims=[f])
                    acc += out[0]
            prob = acc.numpy() / float(len(flips))
            bg[y:y + TILE, x:x + TILE] += prob[0] * gw
            gs[y:y + TILE, x:x + TILE] += prob[2] * gw
            wsum[y:y + TILE, x:x + TILE] += gw
    seen = wsum > 0
    np.divide(bg, wsum, out=bg, where=seen)
    np.divide(gs, wsum, out=gs, where=seen)
    del wsum
    bg[~seen] = 1.0
    gs[~seen] = 0.0
    return bg[:h, :w], gs[:h, :w], used, skipped


def decode(pbg, pgs, sx, sy, strip_rows=1024):
    """(objects, classes): one [cx, cy, x0, y0, x1, y1, area] (um, as kidney/glom.py's region_records) per
    8-connected region where P(background) < FG_MAX_BG with an area of at least MIN_AREA_UM2, in label order, and its
    class from class_of(sum over its pixels of P(GS) - P(NS)), where P(NS) = 1 - P(background) - P(GS)."""
    import cv2
    import numpy as np
    from kidney.glom import region_records
    fg = (pbg < FG_MAX_BG).astype(np.uint8)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(fg, connectivity=8)
    del fg
    score = np.zeros(n, dtype="float64")
    for r in range(0, labels.shape[0], strip_rows):
        lab = labels[r:r + strip_rows].ravel()
        v = (2.0 * pgs[r:r + strip_rows].astype("float64") + pbg[r:r + strip_rows].astype("float64") - 1.0).ravel()
        score += np.bincount(lab, weights=v, minlength=n)[:n]
    objs, classes = [], []
    for i in range(1, n):
        row = (int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]), int(stats[i, cv2.CC_STAT_WIDTH]),
               int(stats[i, cv2.CC_STAT_HEIGHT]), int(stats[i, cv2.CC_STAT_AREA]), float(cents[i, 0]),
               float(cents[i, 1]))
        rec = region_records([row], sx, sy)
        if rec:
            objs.append(rec[0])
            classes.append(class_of(float(score[i])))
    return objs, classes


def run_detect(in_dir, model_path, tta=True):
    """Detection document for every .svs in in_dir (local only)."""
    from kidney.glom import slide_image, y_scale
    model, mean, std, steps = load_model3(model_path)
    rows = []
    for fn in sorted(f for f in os.listdir(in_dir) if f.lower().endswith(".svs")):
        t0 = time.time()
        rec = {"slide": os.path.splitext(fn)[0], "ok": False, "errors": []}
        try:
            img, mpp, li, zoom, size0 = slide_image(os.path.join(in_dir, fn))
            sy = y_scale(mpp, size0, (img.shape[1], img.shape[0]))
            pbg, pgs, used, skipped = predict3(img, model, mean, std, tta=tta)
            del img
            objs, classes = decode(pbg, pgs, mpp, sy)
            rec.update(ok=True, mpp=round(mpp, 4), tiles_used=used, tiles_skipped=skipped, objects=objs,
                       classes=classes)
        except Exception as e:  # one bad slide must not stop the folder
            rec["errors"].append(repr(e)[:300])
        rec["seconds"] = round(time.time() - t0, 1)
        rows.append(rec)
    return {"code_version": CODE_VERSION, "train_steps": steps, "tta": tta, "fg_max_bg": FG_MAX_BG, "rows": rows}


# ---- command line ----

def _write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)


def _read_inputs(a):
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with open(a.exclude, encoding="utf-8") as f:
        excl = json.load(f)
    with open(a.frozen, encoding="utf-8") as f:
        frozen = [s["package"] for s in json.load(f)]
    return rows, excl, frozen


def cmd_select(a):
    rows, excl, frozen = _read_inputs(a)
    sel = select_packages(rows, excl)
    train_rows, problems = split(rows, sel, frozen, a.n_train)
    _write(a.out, fetch_list(train_rows))
    print(json.dumps({"code_version": CODE_VERSION, "rows": len(rows), "selected": len(sel), "frozen": len(frozen),
                      "train": len(train_rows), "problems": problems}))
    return 0 if not problems else 3


def cmd_select_test(a):
    rows, excl, frozen = _read_inputs(a)
    with open(a.train, encoding="utf-8") as f:
        train_ids = [s["package"] for s in json.load(f)]
    sel = select_packages(rows, excl)
    test_rows, problems = fresh_split(rows, sel, frozen, train_ids, a.n_test)
    _write(a.out, fetch_list(test_rows, TEST_PREFIX))
    print(json.dumps({"code_version": CODE_VERSION, "rows": len(rows), "selected": len(sel), "frozen": len(frozen),
                      "train": len(train_ids), "test": len(test_rows), "problems": problems}))
    return 0 if not problems else 3


def cmd_crops(a):
    caps = tuple((k, a.rand_cap if k == "rand" else c) for k, c in CAPS)
    diag = run_crops(a.wsi, a.masks, a.out_dir, delete=a.delete, caps=caps)
    if a.diag:
        _write(a.diag, diag)
    agg = crops_aggregate(diag)
    print(json.dumps(agg))
    return 0 if agg["ok"] else 1


def cmd_hard(a):
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    diag = run_hard(a.wsi, a.masks, a.model, a.out_dir, cap=a.cap, delete=a.delete)
    if a.diag:
        _write(a.diag, diag)
    agg = crops_aggregate(diag)
    print(json.dumps(agg))
    return 0 if agg["ok"] else 1


def cmd_train(a):
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    probs = parse_probs(a.kind_probs) if a.kind_probs else KIND_PROBS
    s = train(a.crops, a.init, a.out, steps=a.steps, minutes=a.minutes, log=lambda t: print(t, flush=True),
              probs=probs)
    if a.log:
        _write(a.log, s)
    print(json.dumps({k: v for k, v in s.items() if k != "log"}))
    return 0


def cmd_detect(a):
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    doc = run_detect(a.in_dir, a.model)
    _write(a.out, doc)
    ok = [r for r in doc["rows"] if r["ok"]]
    print(json.dumps({"code_version": CODE_VERSION, "train_steps": doc["train_steps"], "slides": len(doc["rows"]),
                      "ok": len(ok), "minutes": round(sum(r["seconds"] for r in doc["rows"]) / 60.0, 1)}))
    return 0 if ok and len(ok) == len(doc["rows"]) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stages 5-6: globally sclerotic glomerulus detection (local outputs).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("select", "select-test"):
        p = sub.add_parser(name)
        p.add_argument("--csv", required=True)
        p.add_argument("--exclude", required=True, help="JSON list of package ids already used")
        p.add_argument("--frozen", required=True, help="JSON list of {slide, package, name}: the frozen test slides")
        p.add_argument("--out", required=True)
        if name == "select":
            p.add_argument("--n-train", type=int, default=N_TRAIN)
        else:
            p.add_argument("--train", required=True, help="JSON list of {slide, package, name}: stage 5 training")
            p.add_argument("--n-test", type=int, default=N_TEST)
    p = sub.add_parser("crops")
    p.add_argument("--wsi", required=True)
    p.add_argument("--masks", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--diag", default="")
    p.add_argument("--delete", action="store_true", help="delete each slide and mask after cropping")
    p.add_argument("--rand-cap", type=int, default=dict(CAPS)["rand"])
    p = sub.add_parser("hard")
    p.add_argument("--wsi", required=True)
    p.add_argument("--masks", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--diag", default="")
    p.add_argument("--delete", action="store_true", help="delete each slide and mask after mining")
    p.add_argument("--cap", type=int, default=HARD_CAP)
    p.add_argument("--threads", type=int, default=0)
    p = sub.add_parser("train")
    p.add_argument("--crops", required=True, nargs="+")
    p.add_argument("--init", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--log", default="")
    p.add_argument("--steps", type=int, default=STEPS)
    p.add_argument("--minutes", type=float, default=MINUTES)
    p.add_argument("--kind-probs", default="", help="e.g. gs=0.35,ns=0.25,rand=0.2,hard=0.2 (default: stage 5's)")
    p.add_argument("--threads", type=int, default=0)
    p = sub.add_parser("detect")
    p.add_argument("--in-dir", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=0)
    a = ap.parse_args(argv)
    return {"select": cmd_select, "select-test": cmd_select_test, "crops": cmd_crops, "hard": cmd_hard,
            "train": cmd_train, "detect": cmd_detect}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
