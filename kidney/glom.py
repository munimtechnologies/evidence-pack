#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""glom: glomerulus segmentation on .svs whole-slide images with the open HuBMAP 2021 Deepflash2 kidney models.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Stage 2 of a one-command kidney WSI pipeline (stage 1: kidney/wsi_qc.py). Pre-registration of the first run:
findings/kidney-glom-dryrun-prereg-v1-2026-11-08.md (evidence-pack).

Models: the five kidney U-Nets (efficientnet-b2 encoder, 2 classes) of team Deepflash2 from the HuBMAP "Hacking the
Kidney" Kaggle competition (2021), as released by the competition's organisers: code github.com/cns-iu/
ccf-research-kaggle-2021 (MIT), weights Zenodo 10.5281/zenodo.7730028 (CC BY 4.0), file models/5-deepflash/kidney/
unet_model-1..5.pth. They were trained on PAS-stained kidney sections at 0.5 um per pixel; their inference code
reads tiles at a zoom factor of 3, i.e. about 1.5 um per pixel. This module follows that code: 512 x 512 tiles at
1.5 um/px, a step of 0.8 tile, Gaussian blending, the checkpoint's own mean/std, softmax class 1 averaged over the
models and horizontal/vertical flips, threshold 0.5, and its empty-tile rule (HSV saturation > 40 on more than 4,000
pixels). Unlike that code, it counts glomeruli: connected regions (8-connectivity) of the thresholded mask with an
area of at least MIN_AREA_UM2 square micrometres.

Outputs: glom.json (settings, per-slide counts and areas, timings). No pixels are written.
0.1.1 (2026-11-09) also writes `areas_um2`, the sorted area of every counted glomerulus, so that the stage-3 plan's
pooled median-area check (C3, findings/kidney-glom-compare-plan-v0-2026-11-09.md) can be computed. Counting is
unchanged. glom.json stays local: per-slide values from KPMP slides are never published.
0.2.0 (2026-11-10, stage 4: findings/kidney-glom-stage4-prereg-v1-2026-11-10.md) also writes `objects`: one
[cx, cy, x0, y0, x1, y1, area] per counted glomerulus, in micrometres of the slide's level-0 frame (origin at the
top-left corner; centroid and bounding box of the region; box edges are pixel edges), so that each object can be
matched with another segmentation of the same slide. Counting and areas are unchanged.
Standard-library parts and their tests run without numpy, torch or OpenCV. Usage:
  python -m kidney.glom --in-dir /input --out-dir /output --models /models/kidney
"""
import argparse
import glob
import json
import math
import os
import statistics
import time

CODE_VERSION = "0.2.0"
TRAIN_MPP = 0.5
ZOOM = 3
TARGET_MPP = TRAIN_MPP * ZOOM
TILE = 512
SHIFT = 0.8
S_TH = 40
P_TH = 1000 * (TILE // 256) ** 2
THRESHOLD = 0.5
MIN_AREA_UM2 = 2000.0
SIGMA_SCALE = 1.0 / 8


# ---- standard-library parts ----

def tile_starts(length, tile=TILE, shift=SHIFT):
    """Start offsets of tiles covering [0, length): step int(tile * shift), the last tile flush with the end.
    One tile at 0 if length <= tile (the image is padded to a full tile)."""
    if length <= tile:
        return [0]
    step = max(1, int(tile * shift))
    starts = list(range(0, length - tile + 1, step))
    if starts[-1] != length - tile:
        starts.append(length - tile)
    return starts


def pick_level(sizes, mpp0, target=TARGET_MPP):
    """(level index, residual zoom): the coarsest pyramid level whose pixel size is at most `target`, and the factor
    by which that level must still be shrunk. `sizes` is [(width, height)], level 0 first."""
    w0 = float(sizes[0][0])
    best = 0
    for i, (w, _) in enumerate(sizes):
        if mpp0 * (w0 / w) <= target + 1e-9:
            best = i
    return best, target / (mpp0 * (w0 / sizes[best][0]))


def strip_prefix(state_dict, prefix="module."):
    """Keys without a DataParallel prefix (a no-op when no key has it)."""
    if all(k.startswith(prefix) for k in state_dict):
        return {k[len(prefix):]: v for k, v in state_dict.items()}
    return dict(state_dict)


def summarize_regions(areas_px, mpp, min_area_um2=MIN_AREA_UM2):
    """Glomerulus count and areas (um^2) from region pixel areas at pixel size `mpp`."""
    um2 = [a * mpp * mpp for a in areas_px]
    kept = sorted(a for a in um2 if a >= min_area_um2)
    return {"regions": len(um2), "glomeruli": len(kept),
            "median_area_um2": round(statistics.median(kept), 1) if kept else None,
            "total_area_um2": round(sum(kept), 1),
            "small_regions": len(um2) - len(kept)}


def kept_areas(areas_px, mpp, min_area_um2=MIN_AREA_UM2):
    """Sorted areas (um^2, rounded to 0.1) of the regions that count as glomeruli, the same regions that
    summarize_regions counts. For the local glom.json only."""
    return [round(a, 1) for a in sorted(p * mpp * mpp for p in areas_px) if a >= min_area_um2]


def y_scale(sx, size0, image_size):
    """Micrometres per working-image pixel along y, given sx along x, the slide's level-0 (width, height) and the
    working image's (width, height): sx x (w / w0) x (h0 / h), integers multiplied first."""
    w0, h0 = int(size0[0]), int(size0[1])
    w, h = int(image_size[0]), int(image_size[1])
    return sx * (w * h0) / float(w0 * h)


def region_records(rows, sx, sy, min_area_um2=MIN_AREA_UM2):
    """[[cx, cy, x0, y0, x1, y1, area]] (um, rounded to 0.1) of the regions that count as glomeruli, in input order.
    `rows` are (left, top, width, height, area_px, cx_px, cy_px) in working-image pixels (centroid in pixel-index
    coordinates, as OpenCV gives it). A region counts exactly as in summarize_regions: area_px x sx x sx >= floor.
    Pixel i covers [i, i + 1), so a centroid maps to (c + 0.5) x scale and a box to [left, left + width) x scale."""
    out = []
    for left, top, width, height, area_px, cx, cy in rows:
        area = area_px * sx * sx
        if area < min_area_um2:
            continue
        out.append([round((cx + 0.5) * sx, 1), round((cy + 0.5) * sy, 1), round(left * sx, 1), round(top * sy, 1),
                    round((left + width) * sx, 1), round((top + height) * sy, 1), round(area, 1)])
    return out


def model_paths(models_dir):
    """unet_model-*.pth in a folder, sorted (merged_scale_models/ is not read)."""
    return sorted(glob.glob(os.path.join(models_dir, "unet_model-*.pth")))


# ---- numpy / torch / OpenCV parts ----

def gaussian_weight(tile=TILE, sigma_scale=SIGMA_SCALE):
    import numpy as np
    c = (tile - 1) / 2.0
    sigma = tile * sigma_scale
    g = np.exp(-((np.arange(tile) - c) ** 2) / (2 * sigma * sigma))
    w = np.outer(g, g)
    w = w / w.max()
    return np.maximum(w, 1e-4).astype("float32")


def load_models(paths):
    """([models], mean, std, info). Each checkpoint must load strictly into smp.Unet(efficientnet-b2, 2 classes)."""
    import numpy as np
    import segmentation_models_pytorch as smp
    import torch
    models, info, mean, std = [], [], None, None
    for p in paths:
        state = torch.load(p, map_location="cpu", weights_only=False)
        sd = state["model"] if isinstance(state, dict) and "model" in state else state
        m = smp.Unet(encoder_name="efficientnet-b2", encoder_weights=None, in_channels=3, classes=2)
        m.load_state_dict(strip_prefix(sd), strict=True)
        m.eval()
        models.append(m)
        if isinstance(state, dict) and "stats" in state:
            mean, std = (np.asarray(s, dtype="float32").reshape(-1) for s in state["stats"])
        info.append({"file": os.path.basename(p), "keys": len(sd)})
    if mean is None:
        raise ValueError("no 'stats' (mean, std) in any checkpoint")
    return models, mean, std, info


def predict(img, models, mean, std, tta=True):
    """Probability map (float32, same height/width as img) of class 1 and the tile counts."""
    import cv2
    import numpy as np
    import torch
    h, w = img.shape[:2]
    ph, pw = max(h, TILE), max(w, TILE)
    if (ph, pw) != (h, w):
        pad = np.full((ph, pw, 3), 255, dtype=img.dtype)
        pad[:h, :w] = img
        img = pad
    pred = np.zeros((ph, pw), dtype="float32")
    wsum = np.zeros((ph, pw), dtype="float32")
    gw = gaussian_weight()
    flips = [None, 3, 2] if tta else [None]   # none, horizontal (width axis), vertical (height axis)
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
            x_t = torch.from_numpy(np.ascontiguousarray(t.transpose(2, 0, 1)))[None]
            acc = torch.zeros((TILE, TILE))
            with torch.no_grad():
                for m in models:
                    for f in flips:
                        inp = x_t if f is None else torch.flip(x_t, dims=[f])
                        out = torch.softmax(m(inp), dim=1)
                        if f is not None:
                            out = torch.flip(out, dims=[f])
                        acc += out[0, 1]
            prob = acc.numpy() / (len(models) * len(flips))
            pred[y:y + TILE, x:x + TILE] += prob * gw
            wsum[y:y + TILE, x:x + TILE] += gw
    out = np.where(wsum > 0, pred / np.maximum(wsum, 1e-6), 0.0).astype("float32")
    return out[:h, :w], used, skipped


def components(mask):
    """(left, top, width, height, area_px, cx, cy) of each 8-connected region of a binary mask, in label order."""
    import cv2
    import numpy as np
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    return [(int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]), int(stats[i, cv2.CC_STAT_WIDTH]),
             int(stats[i, cv2.CC_STAT_HEIGHT]), int(stats[i, cv2.CC_STAT_AREA]), float(cents[i, 0]),
             float(cents[i, 1])) for i in range(1, n)]


def regions(mask):
    """Pixel areas of the 8-connected regions of a binary mask."""
    return [r[4] for r in components(mask)]


def slide_image(path):
    """(RGB image at TARGET_MPP, mpp actually reached, level, residual zoom, level-0 size)."""
    import cv2
    import tifffile
    from kidney.wsi_qc import parse_aperio, read_region, slide_levels
    with tifffile.TiffFile(path) as tif:
        levels = slide_levels(tif)
        p0, w0, h0 = levels[0]
        mpp0 = parse_aperio(getattr(p0, "description", "") or "").get("mpp")
        if not mpp0:
            raise ValueError("no MPP in the slide header")
        li, zoom = pick_level([(w, h) for _, w, h in levels], mpp0)
        page, w, h = levels[li]
        img = read_region(page, 0, 0, w, h)[..., :3]
    tw, th = max(1, int(round(w / zoom))), max(1, int(round(h / zoom)))
    if (tw, th) != (w, h):
        img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
    mpp = mpp0 * (w0 / float(tw))
    return img, mpp, li, zoom, (w0, h0)


def run_slide(path, models, mean, std, tta=True):
    import numpy as np
    t0 = time.time()
    rec = {"slide": os.path.splitext(os.path.basename(path))[0], "ok": False, "errors": []}
    try:
        img, mpp, li, zoom, size0 = slide_image(path)
        sy = y_scale(mpp, size0, (img.shape[1], img.shape[0]))
        rec.update(level=li, residual_zoom=round(zoom, 4), mpp=round(mpp, 4), mpp_y=round(sy, 4),
                   width=img.shape[1], height=img.shape[0], level0=list(size0))
        prob, used, skipped = predict(img, models, mean, std, tta=tta)
        rec.update(tiles_used=used, tiles_skipped=skipped,
                   positive_fraction=round(float((prob > THRESHOLD).mean()), 6),
                   prob_p99=round(float(np.percentile(prob, 99)), 4))
        comps = components(prob > THRESHOLD)
        areas_px = [c[4] for c in comps]
        rec.update(summarize_regions(areas_px, mpp))
        rec["areas_um2"] = kept_areas(areas_px, mpp)
        rec["objects"] = region_records(comps, mpp, sy)
        rec["ok"] = True
    except Exception as e:  # one bad slide must not stop the folder
        rec["errors"].append(repr(e)[:300])
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Glomerulus counts on a folder of .svs slides (HuBMAP Deepflash2).")
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--models", required=True, help="folder holding unet_model-1..5.pth")
    ap.add_argument("--only", default="", help="comma-separated slide names (without .svs); default all")
    ap.add_argument("--no-tta", action="store_true")
    ap.add_argument("--threads", type=int, default=0)
    a = ap.parse_args(argv)
    t0 = time.time()
    paths = model_paths(a.models)
    if not paths:
        print("no unet_model-*.pth in", a.models)
        return 2
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    models, mean, std, info = load_models(paths)
    print(json.dumps({"models": info, "mean": [round(float(v), 4) for v in mean],
                      "std": [round(float(v), 4) for v in std]}), flush=True)
    only = set(s for s in a.only.split(",") if s)
    files = sorted(f for f in os.listdir(a.in_dir) if f.lower().endswith(".svs")
                   and (not only or os.path.splitext(f)[0] in only))
    os.makedirs(a.out_dir, exist_ok=True)
    rows = []
    for fn in files:
        rec = run_slide(os.path.join(a.in_dir, fn), models, mean, std, tta=not a.no_tta)
        rows.append(rec)
        short = {k: v for k, v in rec.items() if k not in ("areas_um2", "objects")}
        print(json.dumps(short), flush=True)
    doc = {"code_version": CODE_VERSION,
           "settings": {"train_mpp": TRAIN_MPP, "zoom": ZOOM, "target_mpp": TARGET_MPP, "tile": TILE, "shift": SHIFT,
                        "s_th": S_TH, "p_th": P_TH, "threshold": THRESHOLD, "min_area_um2": MIN_AREA_UM2,
                        "tta": not a.no_tta, "models": info},
           "rows": rows, "minutes": round((time.time() - t0) / 60, 2)}
    with open(os.path.join(a.out_dir, "glom.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    return 0 if rows and all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
