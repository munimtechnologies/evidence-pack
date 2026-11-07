#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""wsi_qc: quality checks for a folder of whole-slide images (.svs), one command, no manual steps.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for
diagnosis. The NIDDK Kidney AI Discovery Challenge asks for code that runs end to end on a directory
of SVS whole-slide images and writes its results to an output directory. This module is the first
stage of such a pipeline: before any feature is measured, every slide is described and checked.

For each slide it records
  - the pyramid (size, levels, compression) and the scanner's own MPP and magnification (Aperio
    ImageDescription), so that a feature measured in pixels can be put in micrometres;
  - on a thumbnail level (longer side about 2,048 pixels): the tissue fraction, the number of
    separate tissue pieces (serial sections on one slide show up as several pieces), the share of
    green-ink and near-black pixels (pen marks, debris), and the mean optical density of tissue
    per RGB channel (a crude stain-intensity measure);
  - on up to 16 level-0 tiles spread over the tissue: the variance of the Laplacian, a common
    focus measure. It is uncalibrated: compare slides of one scanner and compression only.
Blue ink is not separated from hematoxylin at thumbnail resolution, so it is not reported.

Outputs: qc.csv (one row per slide) and qc.json (settings, rows, medians). No pixels are written.
numpy, tifffile and imagecodecs are imported only where pixels are read, so the standard-library
parts and their tests run without them. Usage:
  python -m kidney.wsi_qc --in-dir /input --out-dir /output
"""
import argparse
import csv
import json
import math
import os
import statistics
import time

CODE_VERSION = "0.1.0"
THUMB_SIDE = 2048
THUMB_MAX_PIXELS = 40_000_000
SAT_MIN = 15          # max-min of RGB: below this a pixel is grey (background, black ink)
WHITE = 220           # mean RGB at or above this is background
BLACK = 40            # mean RGB below this is near-black (ink, debris, folds)
GRID = 128            # coarse grid cells along the thumbnail's longer side
PIECE_MIN_SHARE = 0.01
BLUR_TILES = 16
BLUR_TILE = 512
BLUR_MIN_TISSUE = 0.5

FIELDS = ["slide", "ok", "bytes", "width", "height", "n_levels", "compression", "aperio", "mpp", "appmag",
          "scanner", "thumb_level", "thumb_width", "thumb_height", "tissue_fraction", "pieces", "piece_cells_top3",
          "green_ink_fraction", "black_fraction", "od_r", "od_g", "od_b", "blur_tiles", "blur_median",
          "blur_min", "seconds", "errors"]


def _num(text):
    try:
        v = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ---- standard-library parts ----

def parse_aperio(desc):
    """MPP, magnification and scanner ID from an Aperio ImageDescription ("header|Key = value|...")."""
    kv = {}
    for part in (desc or "").split("|")[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    return {"mpp": _num(kv.get("mpp")), "appmag": _num(kv.get("appmag")), "scanner": kv.get("scanscope id")}


def pick_thumb_level(sizes, side=THUMB_SIDE, max_pixels=THUMB_MAX_PIXELS):
    """Index of the smallest level whose longer side is at least `side`, among levels of at most
    `max_pixels` pixels; the largest such level if none is that big; None if every level is too big.
    `sizes` is [(width, height)], level 0 (largest) first."""
    best = None
    for i in range(len(sizes) - 1, -1, -1):
        w, h = sizes[i]
        if w * h > max_pixels:
            break
        best = i
        if max(w, h) >= side:
            break
    return best


def pick_spread(n, k):
    """k indices spread evenly over range(n), first and last included; all of them if n <= k."""
    if n <= 0 or k <= 0:
        return []
    if n <= k:
        return list(range(n))
    if k == 1:
        return [0]
    return sorted({int(round(i * (n - 1) / (k - 1))) for i in range(k)})


def count_components(grid):
    """Sizes (in cells, largest first) of the 4-connected groups of true cells in a list-of-lists grid."""
    rows = len(grid)
    seen = [[False] * len(r) for r in grid]
    sizes = []
    for i in range(rows):
        for j in range(len(grid[i])):
            if not grid[i][j] or seen[i][j]:
                continue
            seen[i][j] = True
            stack, n = [(i, j)], 0
            while stack:
                a, b = stack.pop()
                n += 1
                for c, d in ((a - 1, b), (a + 1, b), (a, b - 1), (a, b + 1)):
                    if 0 <= c < rows and 0 <= d < len(grid[c]) and grid[c][d] and not seen[c][d]:
                        seen[c][d] = True
                        stack.append((c, d))
            sizes.append(n)
    return sorted(sizes, reverse=True)


def piece_count(sizes, min_share=PIECE_MIN_SHARE, min_cells=2):
    """Pieces of at least min_cells cells and at least min_share of all tissue cells."""
    total = sum(sizes)
    if not total:
        return 0
    thr = max(min_cells, min_share * total)
    return sum(1 for s in sizes if s >= thr)


def tile_origins(grid, cell, ds, w0, h0, k=BLUR_TILES, tile=BLUR_TILE):
    """Level-0 (left, top) of up to k tiles centred on tissue cells spread over the grid (row order).
    cell: thumbnail pixels per grid cell; ds: level-0 pixels per thumbnail pixel."""
    cells = [(i, j) for i, row in enumerate(grid) for j, v in enumerate(row) if v]
    out = []
    for idx in pick_spread(len(cells), k):
        i, j = cells[idx]
        cx, cy = (j + 0.5) * cell * ds, (i + 0.5) * cell * ds
        left = int(max(0, min(w0 - tile, cx - tile / 2)))
        top = int(max(0, min(h0 - tile, cy - tile / 2)))
        out.append((left, top))
    return out


def median_or_none(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


# ---- numpy parts ----

def tissue_mask(rgb):
    """True where a pixel is coloured (max-min >= SAT_MIN), not white (mean < WHITE) and not green ink."""
    import numpy as np
    a = np.asarray(rgb)[..., :3].astype(np.int16)
    sat = a.max(axis=2) - a.min(axis=2)
    gray = a.mean(axis=2)
    return (sat >= SAT_MIN) & (gray < WHITE) & ~green_ink_mask(a)


def green_ink_mask(rgb):
    """True where green clearly dominates (green marker ink; absent from H&E, PAS, trichrome and silver)."""
    import numpy as np
    a = np.asarray(rgb)[..., :3].astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (g > r + 20) & (g > b + 10)


def black_mask(rgb):
    import numpy as np
    return np.asarray(rgb)[..., :3].astype(np.int16).mean(axis=2) < BLACK


def od_means(rgb, mask):
    """Mean optical density -log10((I+1)/256) per RGB channel over masked pixels; Nones if none."""
    import numpy as np
    m = np.asarray(mask, dtype=bool)
    if not m.any():
        return [None, None, None]
    a = np.asarray(rgb)[..., :3].astype(np.float64)
    od = -np.log10((a + 1.0) / 256.0)
    return [round(float(od[..., c][m].mean()), 4) for c in range(3)]


def laplacian_var(gray):
    """Population variance of the 4-neighbour Laplacian over interior pixels; None if under 3x3."""
    import numpy as np
    g = np.asarray(gray, dtype=np.float64)
    if g.ndim != 2 or g.shape[0] < 3 or g.shape[1] < 3:
        return None
    lap = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]) - 4.0 * g[1:-1, 1:-1]
    return float(lap.var())


def coarse_grid(mask, grid=GRID):
    """(list-of-lists of bools, cell side): a cell is tissue when at least half its pixels are."""
    import numpy as np
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    cell = max(1, int(math.ceil(max(h, w) / float(grid))))
    rows, cols = int(math.ceil(h / float(cell))), int(math.ceil(w / float(cell)))
    out = [[bool(m[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell].mean() >= 0.5) for j in range(cols)]
           for i in range(rows)]
    return out, cell


# ---- slides (tifffile) ----

def slide_levels(tif):
    """[(page, width, height)] of the slide's pyramid, level 0 first."""
    out = []
    for lev in tif.series[0].levels:
        page = lev.keyframe if getattr(lev, "keyframe", None) is not None else lev.pages[0]
        out.append((page, page.imagewidth, page.imagelength))
    return out


def compression_name(page):
    c = getattr(page, "compression", None)
    return getattr(c, "name", str(c))


def read_region(page, left, top, width, height):
    """Pixels [top:top+height, left:left+width] of a page, decoding only the tiles needed."""
    import numpy as np
    if not page.is_tiled:
        return np.asarray(page.asarray())[top:top + height, left:left + width]
    tw, tl = page.tilewidth, page.tilelength
    across = -(-page.imagewidth // tw)
    out = np.zeros((height, width, page.samplesperpixel), dtype=page.dtype)
    fh, decode = page.parent.filehandle, page.decode
    for row in range(top // tl, (top + height - 1) // tl + 1):
        for col in range(left // tw, (left + width - 1) // tw + 1):
            i = row * across + col
            offset, count = page.dataoffsets[i], page.databytecounts[i]
            if not count:
                continue
            fh.seek(offset)
            seg, _, shape = decode(fh.read(count), i, jpegtables=page.jpegtables)
            if seg is None:
                continue
            seg = np.asarray(seg).reshape(shape)
            while seg.ndim > 3:  # (planes, depth, length, width, samples) -> (length, width, samples)
                seg = seg[0]
            if seg.ndim == 2:
                seg = seg[:, :, None]
            y0, x0 = row * tl, col * tw
            ys, xs = max(top, y0), max(left, x0)
            ye, xe = min(top + height, y0 + seg.shape[0]), min(left + width, x0 + seg.shape[1])
            if ye > ys and xe > xs:
                out[ys - top:ye - top, xs - left:xe - left] = seg[ys - y0:ye - y0, xs - x0:xe - x0]
    return out


def qc_slide(path):
    """One slide's QC record (see FIELDS)."""
    import tifffile
    t0 = time.time()
    rec = {"slide": os.path.splitext(os.path.basename(path))[0], "ok": False, "bytes": os.path.getsize(path),
           "errors": []}
    try:
        with tifffile.TiffFile(path) as tif:
            levels = slide_levels(tif)
            p0, w0, h0 = levels[0]
            meta = parse_aperio(getattr(p0, "description", "") or "")
            rec.update(width=w0, height=h0, n_levels=len(levels), compression=compression_name(p0),
                       aperio=bool(getattr(tif, "is_svs", False)), **meta)
            li = pick_thumb_level([(w, h) for _, w, h in levels])
            if li is None:
                rec["errors"].append("no pyramid level small enough for a thumbnail")
                return rec
            page, w, h = levels[li]
            thumb = read_region(page, 0, 0, w, h)
            tm = tissue_mask(thumb)
            n = float(tm.size)
            rec.update(thumb_level=li, thumb_width=w, thumb_height=h,
                       tissue_fraction=round(float(tm.sum()) / n, 4),
                       green_ink_fraction=round(float(green_ink_mask(thumb).sum()) / n, 5),
                       black_fraction=round(float(black_mask(thumb).sum()) / n, 5))
            rec["od_r"], rec["od_g"], rec["od_b"] = od_means(thumb, tm)
            grid, cell = coarse_grid(tm)
            sizes = count_components(grid)
            rec["pieces"] = piece_count(sizes)
            rec["piece_cells_top3"] = " ".join(str(s) for s in sizes[:3])
            ds = w0 / float(w)
            blurs = []
            for left, top in tile_origins(grid, cell, ds, w0, h0):
                tw, th = min(BLUR_TILE, w0 - left), min(BLUR_TILE, h0 - top)
                tile = read_region(p0, left, top, tw, th)
                if float(tissue_mask(tile).mean()) < BLUR_MIN_TISSUE:
                    continue
                v = laplacian_var(tile[..., :3].astype("float64").mean(axis=2))
                if v is not None:
                    blurs.append(v)
            rec["blur_tiles"] = len(blurs)
            rec["blur_median"] = round(median_or_none(blurs), 2) if blurs else None
            rec["blur_min"] = round(min(blurs), 2) if blurs else None
            rec["ok"] = True
    except Exception as e:  # one bad slide must not stop the folder
        rec["errors"].append(repr(e)[:300])
    finally:
        rec["seconds"] = round(time.time() - t0, 1)
    return rec


def summarize(rows):
    ok = [r for r in rows if r.get("ok")]
    med = {}
    for f in ("tissue_fraction", "pieces", "green_ink_fraction", "black_fraction", "od_r", "od_g", "od_b",
              "blur_median", "mpp", "appmag", "seconds"):
        m = median_or_none(r.get(f) for r in ok)
        med[f] = round(m, 5) if isinstance(m, float) else m
    return {"slides": len(rows), "ok": len(ok), "failed": len(rows) - len(ok),
            "with_mpp": sum(1 for r in ok if r.get("mpp") is not None),
            "multi_piece": sum(1 for r in ok if (r.get("pieces") or 0) >= 2),
            "with_green_ink": sum(1 for r in ok if (r.get("green_ink_fraction") or 0) >= 0.001),
            "compressions": sorted({str(r.get("compression")) for r in ok}), "medians": med}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Quality checks for a folder of .svs whole-slide images.")
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--suffix", default=".svs")
    ap.add_argument("--budget-minutes", type=float, default=0, help="0 = no limit")
    a = ap.parse_args(argv)
    t0 = time.time()
    files = sorted(f for f in os.listdir(a.in_dir) if f.lower().endswith(a.suffix.lower()))
    os.makedirs(a.out_dir, exist_ok=True)
    rows = []
    for k, fn in enumerate(files):
        if a.budget_minutes and time.time() - t0 > a.budget_minutes * 60:
            rows.append({"slide": os.path.splitext(fn)[0], "ok": False, "errors": ["not attempted: time budget"]})
            continue
        rec = qc_slide(os.path.join(a.in_dir, fn))
        rows.append(rec)
        print("%d/%d %s ok=%s %.1fs" % (k + 1, len(files), rec["slide"], rec["ok"], rec.get("seconds", 0)), flush=True)
    with open(os.path.join(a.out_dir, "qc.csv"), "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow(dict(r, errors="; ".join(r.get("errors", []))))
    doc = {"code_version": CODE_VERSION,
           "settings": {"thumb_side": THUMB_SIDE, "sat_min": SAT_MIN, "white": WHITE, "black": BLACK, "grid": GRID,
                        "piece_min_share": PIECE_MIN_SHARE, "blur_tiles": BLUR_TILES, "blur_tile": BLUR_TILE,
                        "blur_min_tissue": BLUR_MIN_TISSUE},
           "summary": summarize(rows), "rows": rows, "minutes": round((time.time() - t0) / 60, 2)}
    with open(os.path.join(a.out_dir, "qc.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc["summary"]))
    return 0 if files else 2


if __name__ == "__main__":
    raise SystemExit(main())
