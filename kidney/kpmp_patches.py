#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_patches: image patches around KPMP objects, for private visual review.

The Kidney AI Discovery Challenge asks for image evidence (patches) and artefact control. The
object audit (kidney.kpmp_objects 1.0) lists the most extreme within-slide outliers by package and
bounding box. For each target this job downloads the package once, opens its .svs slide and writes
  - a crop around the box with the box outlined (level 0, or a lower level for very large boxes),
  - the same for two typical objects of the same sheet on the same slide (closest to the slide
    median of the target's feature), as a visual baseline,
  - one low-resolution overview of the slide with every target marked.
It also checks which way KPMP's x1|x2|y1|y2 columns run, from how many of the slide's boxes fit
inside the image either way, and that each target box is present in the package's workbook.

Patches are KPMP image data. They stay in the job output for review and are never published;
results.json holds no pixels.

numpy, tifffile, imagecodecs and Pillow are imported only where pixels are read or written, so the
standard-library parts and their tests run without them. Usage:
  python -m kidney.kpmp_patches --targets inputs/patch-targets.json --data-dir /data --out-dir /out
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

CODE_VERSION = "1.0"
DOWNLOAD = "https://atlas.kpmp.org/api/v1/file/download/{package}/{name}"
UA = "mv2-kpmp-patches/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
CACHE = "kpmp-census"
SHEETS = ("gloms", "s_gloms", "tubs", "arts")
COORDS = ("x1", "x2", "y1", "y2")
TYPICAL_PER_TARGET = 2
MIN_MARGIN = 128
MAX_CROP = 2048
OUT_SIDE = 1024
OVERVIEW_SIDE = 1600
OVERVIEW_MAX_PIXELS = 40_000_000
CHUNK = 1 << 20

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---- targets and workbooks ----

def load_targets(path):
    """({package: zip name}, [target]) from the targets file; each target has id, package, sheet,
    box (x1, x2, y1, y2), feature and direction."""
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    names = {p["package"]: p["name"] for p in doc["packages"]}
    targets = []
    for t in doc["targets"]:
        if t["package"] not in names:
            raise ValueError("target %s names an unlisted package" % t["id"])
        targets.append(dict(t, box=tuple(float(v) for v in t["box"])))
    return names, targets


def _num(text):
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _col_index(ref):
    m = CELL_REF.match(ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """{sheet name: rows} from an xlsx file; each row a list of cell texts (None if empty)."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(MAIN_NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(MAIN_NS + "t")))
        targets = {}
        if "xl/_rels/workbook.xml.rels" in names:
            for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).iter(PKG_REL):
                t = rel.get("Target", "")
                targets[rel.get("Id")] = t.lstrip("/") if t.startswith("/") else "xl/" + t
        out = {}
        for sheet in ET.fromstring(z.read("xl/workbook.xml")).iter(MAIN_NS + "sheet"):
            part = targets.get(sheet.get(REL_ID), "")
            if part not in names:
                continue
            rows = []
            for row in ET.fromstring(z.read(part)).iter(MAIN_NS + "row"):
                cells = {}
                for k, c in enumerate(row.findall(MAIN_NS + "c")):
                    i = _col_index(c.get("r"))
                    kind, v = c.get("t"), c.find(MAIN_NS + "v")
                    if kind == "s" and v is not None:
                        val = shared[int(v.text)]
                    elif kind == "inlineStr":
                        val = "".join(t.text or "" for t in c.iter(MAIN_NS + "t"))
                    else:
                        val = v.text if v is not None else None
                    cells[k if i is None else i] = val
                width = max(cells) + 1 if cells else 0
                rows.append([cells.get(i) for i in range(width)])
            out[sheet.get("name")] = rows
    return out


def sheet_objects(rows):
    """[{"box": (x1, x2, y1, y2), "values": {column: number}}] from a sheet whose first row is the header."""
    if not rows:
        return []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    idx = {h: j for j, h in enumerate(header) if h}
    if not all(c in idx for c in COORDS):
        return []
    out = []
    for r in rows[1:]:
        vals = {h: (_num(r[j]) if j < len(r) else None) for h, j in idx.items()}
        box = tuple(vals[c] for c in COORDS)
        if None in box:
            continue
        out.append({"box": box, "values": {h: v for h, v in vals.items() if h not in COORDS}})
    return out


def package_objects(pdir):
    """{sheet: objects} from the one v2 workbook in a cached package folder ({} if there is none)."""
    books = sorted(fn for fn in os.listdir(pdir) if fn.lower().endswith(".xlsx")) if os.path.isdir(pdir) else []
    if len(books) != 1:
        return {}
    book = read_xlsx(os.path.join(pdir, books[0]))
    return {name.strip().lower(): sheet_objects(rows) for name, rows in book.items()
            if name.strip().lower() in SHEETS}


# ---- geometry ----

def orientation(boxes, width, height):
    """Which way KPMP's columns run. "xy": x is the image column and y the row; "yx": the reverse.
    Decided only when every box fits one way and not every box fits the other."""
    fit_xy = sum(1 for x1, x2, y1, y2 in boxes if min(x1, y1) >= 0 and x2 <= width and y2 <= height)
    fit_yx = sum(1 for x1, x2, y1, y2 in boxes if min(x1, y1) >= 0 and x2 <= height and y2 <= width)
    n = len(boxes)
    pick = None
    if n and fit_xy == n and fit_yx < n:
        pick = "xy"
    elif n and fit_yx == n and fit_xy < n:
        pick = "yx"
    return {"boxes": n, "fit_xy": fit_xy, "fit_yx": fit_yx, "orientation": pick}


def to_rect(box, orient):
    """(left, top, right, bottom) in image pixels for a KPMP box."""
    x1, x2, y1, y2 = box
    return (x1, y1, x2, y2) if orient == "xy" else (y1, x1, y2, x2)


def crop_window(rect, width, height, factor=1.0, min_margin=MIN_MARGIN):
    """Integer window around rect with a margin of factor x its longer side (at least min_margin),
    clipped to the image."""
    left, top, right, bottom = rect
    m = max(min_margin, factor * max(right - left, bottom - top))
    return (max(0, int(math.floor(left - m))), max(0, int(math.floor(top - m))),
            min(width, int(math.ceil(right + m))), min(height, int(math.ceil(bottom + m))))


def pick_level(level_sizes, window, max_crop=MAX_CROP):
    """(index, downsample) of the first level at which the window's longer side is at most max_crop
    pixels; the last level if none is small enough."""
    w0 = level_sizes[0][0]
    side = max(window[2] - window[0], window[3] - window[1])
    for i, (w, _) in enumerate(level_sizes):
        ds = w0 / w
        if side / ds <= max_crop:
            return i, ds
    return len(level_sizes) - 1, w0 / level_sizes[-1][0]


def typical(objects, feature, exclude, n=TYPICAL_PER_TARGET):
    """The n objects whose feature is closest to the sheet's median, skipping the box `exclude`."""
    vals = [o for o in objects if o["values"].get(feature) is not None and o["box"] != exclude]
    if not vals:
        return []
    med = statistics.median(o["values"][feature] for o in vals)
    return sorted(vals, key=lambda o: (abs(o["values"][feature] - med), o["box"]))[:n]


# ---- download ----

def download_url(package, name):
    return DOWNLOAD.format(package=urllib.parse.quote(package, safe=""), name=urllib.parse.quote(name, safe=""))


def _open(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=300)


def download(url, dest, get=None, pause=None, tries=3):
    """Stream url to dest with its SHA-256. 401, 403 and 404 are final; other failures are retried."""
    get, pause = get or _open, pause or time.sleep
    last, k = "", 0
    for k in range(tries):
        t0 = time.time()
        try:
            h, n = hashlib.sha256(), 0
            with get(url) as resp:
                with open(dest + ".part", "wb") as f:
                    while True:
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        h.update(chunk)
                        n += len(chunk)
            os.replace(dest + ".part", dest)
            return {"ok": True, "bytes": n, "sha256": h.hexdigest(), "seconds": round(time.time() - t0, 1),
                    "tries": k + 1}
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            if e.code in (401, 403, 404):
                break
        except Exception as e:  # network hiccups: retry
            last = repr(e)[:300]
        if k + 1 < tries:
            pause(5 * (k + 1))
    if os.path.exists(dest + ".part"):
        os.remove(dest + ".part")
    return {"ok": False, "bytes": 0, "error": last, "tries": k + 1}


def extract_svs(zpath, dest):
    """Copy the zip's largest .svs member to dest; its member name, or None if there is none."""
    with zipfile.ZipFile(zpath) as z:
        svs = [i for i in z.infolist() if i.filename.lower().endswith(".svs")]
        if not svs:
            return None
        member = max(svs, key=lambda i: i.file_size)
        with z.open(member) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst, CHUNK)
        return member.filename


# ---- pixels (numpy, tifffile, Pillow) ----

def read_region(page, left, top, width, height):
    """Pixels [top:top+height, left:left+width] of a tiled TIFF page, decoding only the tiles needed."""
    import numpy as np
    if not page.is_tiled:
        raise ValueError("page is not tiled")
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
            seg = np.asarray(seg).reshape(shape)[0]
            y0, x0 = row * tl, col * tw
            ys, xs = max(top, y0), max(left, x0)
            ye, xe = min(top + height, y0 + seg.shape[0]), min(left + width, x0 + seg.shape[1])
            if ye > ys and xe > xs:
                out[ys - top:ye - top, xs - left:xe - left] = seg[ys - y0:ye - y0, xs - x0:xe - x0]
    return out


def save_image(arr, path, rects=(), side=OUT_SIDE):
    """Write arr as a JPEG no longer than side, with rects (in arr pixels) outlined in green."""
    import numpy as np
    from PIL import Image, ImageDraw
    a = np.asarray(arr)
    if a.ndim == 3 and a.shape[2] == 1:
        a = a[:, :, 0]
    elif a.ndim == 3 and a.shape[2] > 3:
        a = a[:, :, :3]
    if a.dtype != np.uint8:
        hi = float(a.max()) or 1.0
        a = (a.astype("float64") * (255.0 / hi)).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(a).convert("RGB")
    s = min(1.0, side / max(img.size))
    if s < 1.0:
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))))
    draw = ImageDraw.Draw(img)
    for l, t, r, b in rects:
        draw.rectangle([l * s, t * s, max(l * s + 1, r * s), max(t * s + 1, b * s)], outline=(0, 255, 0), width=3)
    img.save(path, quality=88)
    return list(img.size)


def slide_levels(tif):
    """[(page, width, height)] of the slide's pyramid, level 0 first."""
    out = []
    for lev in tif.series[0].levels:
        page = lev.keyframe if getattr(lev, "keyframe", None) is not None else lev.pages[0]
        out.append((page, page.imagewidth, page.imagelength))
    return out


def write_crop(levels, rect, path):
    """Crop around rect (level-0 pixels) at a level small enough, outline rect, write it. Returns facts."""
    w0, h0 = levels[0][1], levels[0][2]
    win = crop_window(rect, w0, h0)
    li, ds = pick_level([(w, h) for _, w, h in levels], win)
    page = levels[li][0]
    l, t = int(win[0] / ds), int(win[1] / ds)
    w = max(1, min(page.imagewidth - l, int(math.ceil((win[2] - win[0]) / ds))))
    h = max(1, min(page.imagelength - t, int(math.ceil((win[3] - win[1]) / ds))))
    arr = read_region(page, l, t, w, h)
    box = ((rect[0] - win[0]) / ds, (rect[1] - win[1]) / ds, (rect[2] - win[0]) / ds, (rect[3] - win[1]) / ds)
    size = save_image(arr, path, [box])
    return {"file": os.path.basename(path), "window": list(win), "level": li, "downsample": round(ds, 4),
            "written": size}


def write_overview(levels, rects, path):
    """Whole slide at the smallest level at least OVERVIEW_SIDE wide or tall, with rects marked."""
    pick = None
    for page, w, h in reversed(levels):
        if w * h <= OVERVIEW_MAX_PIXELS:
            pick = (page, w, h)
            if max(w, h) >= OVERVIEW_SIDE:
                break
    if pick is None:
        return None
    page, w, h = pick
    ds = levels[0][1] / w
    pad = 8 * ds
    marks = [((l - pad) / ds, (t - pad) / ds, (r + pad) / ds, (b + pad) / ds) for l, t, r, b in rects]
    size = save_image(read_region(page, 0, 0, w, h), path, marks, side=OVERVIEW_SIDE)
    return {"file": os.path.basename(path), "level_size": [w, h], "downsample": round(ds, 4), "written": size}


def compression_name(page):
    c = getattr(page, "compression", None)
    return getattr(c, "name", str(c))


# ---- one package ----

def process_package(package, name, targets, objects, tmp_dir, patch_dir, get=None, pause=None):
    """Download, open the slide, write every crop for this package's targets. Returns its record."""
    import tifffile
    rec = {"package": package, "targets": [t["id"] for t in targets], "workbook_sheets": sorted(objects),
           "ok": False, "crops": [], "errors": []}
    zpath, spath = os.path.join(tmp_dir, "package.zip"), os.path.join(tmp_dir, "slide.svs")
    try:
        rec["download"] = download(download_url(package, name), zpath, get=get, pause=pause)
        if not rec["download"]["ok"]:
            return rec
        rec["svs_member"] = extract_svs(zpath, spath)
        os.remove(zpath)
        if not rec["svs_member"]:
            rec["errors"].append("no .svs member")
            return rec
        with tifffile.TiffFile(spath) as tif:
            levels = slide_levels(tif)
            p0 = levels[0][0]
            rec["slide"] = {"width": levels[0][1], "height": levels[0][2], "levels": [[w, h] for _, w, h in levels],
                            "tile": [p0.tilewidth, p0.tilelength], "compression": compression_name(p0),
                            "photometric": getattr(getattr(p0, "photometric", None), "name", None),
                            "aperio": bool(getattr(tif, "is_svs", False))}
            boxes = [o["box"] for objs in objects.values() for o in objs]
            orient = orientation(boxes, levels[0][1], levels[0][2])
            rec["orientation"] = orient
            use = orient["orientation"] or ("xy" if orient["fit_xy"] >= orient["fit_yx"] else "yx")
            alt = None if orient["orientation"] else ("yx" if use == "xy" else "xy")
            marks = []
            for t in targets:
                sheet_objs = objects.get(t["sheet"], [])
                match = [o for o in sheet_objs if o["box"] == t["box"]]
                jobs = [("target", t["box"], use)]
                jobs += [("typical%d" % (k + 1), o["box"], use)
                         for k, o in enumerate(typical(sheet_objs, t["feature"], t["box"]))]
                if alt:
                    jobs.append(("alt", t["box"], alt))
                for role, box, way in jobs:
                    rect = to_rect(box, way)
                    entry = {"target": t["id"], "role": role, "box": list(box), "orientation": way}
                    try:
                        entry.update(write_crop(levels, rect, os.path.join(patch_dir, "%s_%s.jpg" % (t["id"], role))))
                    except Exception as e:
                        entry["error"] = repr(e)[:300]
                    if role == "target":
                        entry["in_workbook"] = len(match)
                        entry["values"] = match[0]["values"] if match else None
                        marks.append(rect)
                    rec["crops"].append(entry)
            try:
                rec["overview"] = write_overview(levels, marks, os.path.join(patch_dir, "%s_overview.jpg" % package[:8]))
            except Exception as e:
                rec["errors"].append("overview: " + repr(e)[:300])
        rec["ok"] = True
    except Exception as e:
        rec["errors"].append(repr(e)[:300])
    finally:
        for p in (zpath, spath, zpath + ".part"):
            if os.path.exists(p):
                os.remove(p)
    return rec


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--budget-minutes", type=float, default=150)
    args = ap.parse_args(argv)
    t_start = time.time()
    names, targets = load_targets(args.targets)
    patch_dir = os.path.join(args.out_dir, "patches")
    os.makedirs(patch_dir, exist_ok=True)
    res = {"code_version": CODE_VERSION, "note": "Patches are KPMP image data for private review; never publish them.",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "targets": len(targets), "packages": []}
    order = []
    for t in targets:
        if t["package"] not in order:
            order.append(t["package"])
    with tempfile.TemporaryDirectory() as tmp:
        for k, package in enumerate(order):
            mine = [t for t in targets if t["package"] == package]
            if time.time() - t_start > args.budget_minutes * 60:
                res["packages"].append({"package": package, "targets": [t["id"] for t in mine], "ok": False,
                                        "status": "not_attempted"})
                continue
            objects = package_objects(os.path.join(args.data_dir, CACHE, package))
            rec = process_package(package, names[package], mine, objects, tmp, patch_dir, get=get, pause=pause)
            res["packages"].append(rec)
            log("%d/%d %s ok=%s crops=%d" % (k + 1, len(order), package[:8], rec["ok"], len(rec["crops"])))
    res["summary"] = {"packages": len(order), "ok": sum(1 for r in res["packages"] if r.get("ok")),
                      "crops": sum(1 for r in res["packages"] for c in r.get("crops", []) if "file" in c),
                      "crop_errors": sum(1 for r in res["packages"] for c in r.get("crops", []) if "error" in c),
                      "targets_in_workbook": sum(1 for r in res["packages"] for c in r.get("crops", [])
                                                 if c["role"] == "target" and c.get("in_workbook")),
                      "orientations": sorted({(r.get("orientation") or {}).get("orientation") or "undecided"
                                              for r in res["packages"] if r.get("ok")})}
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res["summary"]))
    return res


if __name__ == "__main__":
    main()
