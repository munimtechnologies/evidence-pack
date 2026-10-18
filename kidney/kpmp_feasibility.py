#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_feasibility: can a small CPU sandbox fetch and read open KPMP kidney biopsy slides?

Pre-registration: findings/kpmp-feasibility-prereg-v1-2026-10-18.md.

Four open files of the KPMP Kidney Tissue Atlas Repository, chosen before the run by
rules applied to the Repository's own file-list export of 2026-10-18:
  seg_small   the smallest "Segmentation Masks & Pathomics Vectors" package (a zip)
  pas_small   the PAS whole-slide image (SVS) that package belongs to
  tiv         the pathologist TIV descriptor score workbook (xlsx)
  pas_large   the largest open PAS WSI that has a segmentation package (stress case)

For each file: download time and bytes against the listed size. For the slides:
pyramid levels, microns per pixel, time to read a low-resolution level, time to
decode a grid of full-resolution tiles, and peak memory. For the package: its
members, whether a mask lines up with the slide, and the headers of its feature
tables. For the workbook: sheets, headers and how many participants are scored.

No KPMP file is copied to the output folder, only measurements and metadata. The
large slide is deleted after it is measured. Download and table code use the
standard library; slide reading uses tifffile + imagecodecs + numpy.

Usage: python -m kidney.kpmp_feasibility --out-dir /out --data-dir /data
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

PREREG = "findings/kpmp-feasibility-prereg-v1-2026-10-18.md"
DOWNLOAD = "https://atlas.kpmp.org/api/v1/file/download/{package}/{name}"
UA = "mv2-kpmp-feasibility/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
TARGETS = (
    {"key": "seg_small", "package": "6bc148ec-d1f4-4253-8124-399e25884bc2",
     "name": "253bfb15-4b81-42f7-a4d9-6c6ddd74489e_S-1904-008128_Seg_Masks_Features_v2.zip",
     "listed": "11.8 MB", "participant": "34-10050"},
    {"key": "pas_small", "package": "986e95db-b5b9-4e83-87cb-cba1fa81f33c",
     "name": "81ccdeb8-3be8-4599-93da-37db3d7350cf_S-1904-008128_PAS_2of2.svs",
     "listed": "11.2 MB", "participant": "34-10050"},
    {"key": "tiv", "package": "c6b5e94e-bd60-480d-965e-138ff52d437e",
     "name": "12cbd82d-2533-4706-ba24-de8b23c441dd_KPMP TIV Descriptor Scores 02.19.2026.xlsx",
     "listed": "357 kB", "participant": ""},
    {"key": "pas_large", "package": "0eb1f03e-f54d-407d-8dd6-faeb4e92975e",
     "name": "51f5f8a4-d873-4726-aa1c-39aa7e869ca0_S-2104-019032_PAS_1of2.svs",
     "listed": "2.37 GB", "participant": "29-10408"},
)
SMALL_KEYS = ("seg_small", "pas_small", "tiv")
SIZE_TOLERANCE = 0.02
TIV_EXPECTED, TIV_WINDOW = 340, 5   # participant IDs listed for the workbook in the export (hand count)
MASK_FACTORS = (1, 2, 4, 8, 16, 32, 64)
READ_MAX_PIXELS = 60_000_000
MASK_READ_MAX_PIXELS = 200_000_000
TILE_GRID = 8
TISSUE_SAT = 20
SMALL_RSS_MB, LARGE_RSS_MB, LARGE_MINUTES = 1536, 2560, 60
CHUNK = 1 << 20
MD_HEAD = 1500
UNITS = {"B": 1, "kB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
ID_RE = re.compile(r"^\d{2,3}-\d{1,5}$")
MPP_RE = re.compile(r"MPP\s*=\s*([0-9.]+)")
MAG_RE = re.compile(r"AppMag\s*=\s*([0-9.]+)")
CELL_REF = re.compile(r"([A-Z]+)(\d+)")
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def parse_size(text):
    """Bytes from the Repository's size column ("11.8 MB", "357 kB"; decimal units)."""
    num, unit = text.strip().split()
    return int(round(float(num) * UNITS[unit]))


def size_ok(actual, listed, tol=SIZE_TOLERANCE):
    want = parse_size(listed)
    return want > 0 and abs(actual - want) <= tol * want


def download_url(package, name):
    return DOWNLOAD.format(package=urllib.parse.quote(package, safe=""), name=urllib.parse.quote(name, safe=""))


def _open(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=300)


def download(url, dest, listed=None, get=None, pause=None, tries=3):
    """Stream url to dest. A file already there with the listed size is reused.
    401, 403 and 404 are final; other failures are retried."""
    get, pause = get or _open, pause or time.sleep
    if listed and os.path.exists(dest) and size_ok(os.path.getsize(dest), listed):
        return {"ok": True, "cached": True, "bytes": os.path.getsize(dest), "seconds": 0.0, "tries": 0}
    last, k = "", 0
    for k in range(tries):
        t0 = time.time()
        try:
            with get(url) as resp:
                headers = getattr(resp, "headers", None)
                ctype = headers.get("Content-Type", "") if headers is not None else ""
                n = 0
                with open(dest + ".part", "wb") as f:
                    while True:
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        n += len(chunk)
            os.replace(dest + ".part", dest)
            return {"ok": True, "cached": False, "bytes": n, "seconds": round(time.time() - t0, 1),
                    "content_type": ctype, "tries": k + 1}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (401, 403, 404):
                break
        except Exception as e:  # network hiccups: retry
            last = repr(e)[:300]
        if k + 1 < tries:
            pause(5 * (k + 1))
    if os.path.exists(dest + ".part"):
        os.remove(dest + ".part")
    return {"ok": False, "cached": False, "bytes": 0, "seconds": None, "error": last, "tries": k + 1}


def aligned(mask_hw, slide_hw, factors=MASK_FACTORS, slack=1):
    """The factor f for which mask (h, w) equals slide (h, w) / f within slack pixels, or None."""
    for f in factors:
        if all(abs(m - s / f) <= slack for m, s in zip(mask_hw, slide_hw)):
            return f
    return None


def hw_of(shape):
    """(height, width) of an image shape: (h, w), (h, w, c) or (c, h, w) with c <= 4; else None."""
    dims = list(shape)
    while len(dims) > 2 and dims[0] == 1:
        dims = dims[1:]
    if len(dims) == 2:
        return tuple(dims)
    if len(dims) == 3:
        if dims[-1] <= 4:
            return tuple(dims[:2])
        if dims[0] <= 4:
            return tuple(dims[1:])
    return None


def mpp_from_description(desc):
    m = MPP_RE.search(desc or "")
    return float(m.group(1)) if m else None


def mag_from_description(desc):
    m = MAG_RE.search(desc or "")
    return float(m.group(1)) if m else None


def ext_of(name):
    base = name.rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def list_zip(z):
    """Members (name, bytes, compressed, ext) of an open ZipFile, directories left out."""
    members = [{"name": i.filename, "bytes": i.file_size, "compressed": i.compress_size, "ext": ext_of(i.filename)}
               for i in z.infolist() if not i.is_dir()]
    return {"members": members, "by_ext": dict(sorted(Counter(m["ext"] for m in members).items()))}


def col_index(ref):
    m = CELL_REF.match(ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """{sheet name: rows} from an xlsx path or file object; each row a list of cell texts (None if empty)."""
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
                    i = col_index(c.get("r"))
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


def _filled(x):
    return x not in (None, "")


def summarise_table(rows, max_values=8, max_columns=300):
    """Header, row count and per-column fill and distinct counts. The header is the fullest
    of the first 10 non-empty rows. Values are listed only for columns with <= 12 distinct values."""
    filled = [r for r in rows if any(_filled(x) for x in r)]
    if not filled:
        return {"n_rows": 0, "width": 0, "header_row": None, "header": [], "columns": []}
    width = max(len(r) for r in filled)
    counts = [sum(1 for x in r if _filled(x)) for r in filled[:10]]
    head_i = counts.index(max(counts))
    head = filled[head_i] + [None] * (width - len(filled[head_i]))
    header = [str(x) if _filled(x) else f"col{j + 1}" for j, x in enumerate(head)]
    data = filled[head_i + 1:]
    columns = []
    for j, name in enumerate(header[:max_columns]):
        vals = Counter(r[j] for r in data if j < len(r) and _filled(r[j]))
        col = {"name": name, "filled": sum(vals.values()), "distinct": len(vals)}
        if len(vals) <= 12:
            col["values"] = dict(vals.most_common(max_values))
        columns.append(col)
    return {"n_rows": len(data), "width": width, "header_row": head_i, "header": header[:max_columns],
            "columns": columns}


def participants(sheets):
    """(distinct participant IDs over all sheets, {sheet: {"column", "ids"}}). Per sheet the
    column with the most distinct cells shaped like a KPMP participant ID (e.g. 34-10050)."""
    found, per_sheet = set(), {}
    for name, rows in sheets.items():
        cols = {}
        for r in rows:
            for j, x in enumerate(r):
                if isinstance(x, str) and ID_RE.match(x.strip()):
                    cols.setdefault(j, set()).add(x.strip())
        if cols:
            j = max(cols, key=lambda c: (len(cols[c]), -c))
            per_sheet[name] = {"column": j, "ids": len(cols[j])}
            found |= cols[j]
    return len(found), per_sheet


def xml_summary(data):
    root = ET.fromstring(data)
    tags = Counter(el.tag for el in root.iter())
    return {"root": root.tag, "elements": sum(tags.values()), "top_tags": dict(tags.most_common(12)),
            "root_attrs": dict(list(root.attrib.items())[:10])}


def verdicts(res):
    """P1-P6 of the pre-registration and the overall verdict (P5 and P6 do not enter it)."""
    d, s = res.get("downloads", {}), res.get("slides", {})
    pkg, tiv = res.get("package", {}) or {}, res.get("tiv", {}) or {}

    def got(k):
        return bool(d.get(k, {}).get("ok") and d.get(k, {}).get("size_ok"))

    p1 = "pass" if all(got(k) for k in SMALL_KEYS) else "fail"
    a = s.get("pas_small", {}) or {}
    if not got("pas_small"):
        p2 = "untestable"
    else:
        p2 = "pass" if (a.get("ok") and a.get("low_read_seconds") is not None and a["low_read_seconds"] < 60
                        and a.get("tiles_decoded", 0) > 0
                        and (a.get("rss_mb_after") or 1e9) < SMALL_RSS_MB) else "fail"
    b = s.get("pas_large", {}) or {}
    p3 = "pass" if (got("pas_large") and b.get("ok") and b.get("low_read_seconds") is not None
                    and b.get("tiles_decoded", 0) > 0 and (b.get("rss_mb_after") or 1e9) < LARGE_RSS_MB
                    and (res.get("large_minutes") or 1e9) <= LARGE_MINUTES) else "fail"
    if not (got("seg_small") and a.get("levels")):
        p4 = "untestable"
    else:
        p4 = "pass" if any(m.get("factor") is not None for m in pkg.get("masks", [])) else "fail"
    if not got("tiv"):
        p5 = "untestable"
    else:
        n = tiv.get("participants")
        p5 = "pass" if n is not None and abs(n - TIV_EXPECTED) <= TIV_WINDOW else "fail"
    small_bytes = d.get("pas_small", {}).get("bytes") or 0
    if not (got("seg_small") and small_bytes):
        p6 = "untestable"
    else:
        p6 = "pass" if any(abs(m["bytes"] - small_bytes) <= 0.01 * small_bytes
                           for m in pkg.get("svs_members", [])) else "fail"
    if p1 == p2 == p3 == p4 == "pass":
        overall = "feasible"
    elif p1 == p2 == p4 == "pass":
        overall = "feasible for small slides only"
    else:
        overall = "not shown feasible"
    return {"P1_access": p1, "P2_small_slide": p2, "P3_large_slide": p3, "P4_mask_alignment": p4,
            "P5_tiv_participants": p5, "P6_package_holds_slide": p6, "overall": overall}


# ---- slide reading (tifffile, numpy; not used by the offline tests) ----

def rss_mb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except Exception:
        return None


def tissue_fraction(arr):
    """Share of pixels that are coloured (max - min channel > TISSUE_SAT): tissue, not glass."""
    import numpy as np
    if arr is None or arr.ndim != 3 or arr.shape[-1] < 3:
        return None
    coloured, total = 0, 0
    for y in range(0, arr.shape[0], 1024):
        block = arr[y:y + 1024, :, :3].astype(np.int16)
        sat = block.max(-1) - block.min(-1)
        coloured += int((sat > TISSUE_SAT).sum())
        total += sat.size
    return round(coloured / total, 4) if total else None


def tissue_centre(arr):
    """(y, x) centre of the coloured pixels, as fractions of height and width."""
    import numpy as np
    ys, xs, n = 0.0, 0.0, 0
    for y in range(0, arr.shape[0], 1024):
        block = arr[y:y + 1024, :, :3].astype(np.int16)
        yy, xx = np.nonzero((block.max(-1) - block.min(-1)) > TISSUE_SAT)
        ys, xs, n = ys + float((yy + y).sum()), xs + float(xx.sum()), n + yy.size
    if not n:
        return 0.5, 0.5
    return ys / n / arr.shape[0], xs / n / arr.shape[1]


def read_slide(path, grid=TILE_GRID):
    """Levels, mpp, a low-resolution read and a grid of decoded full-resolution tiles."""
    import numpy as np
    import tifffile
    out = {"ok": False, "bytes": os.path.getsize(path)}
    t0 = time.time()
    with tifffile.TiffFile(path) as tf:
        out["pages"] = [{"index": i, "shape": list(p.shape), "tiled": bool(p.is_tiled),
                         "compression": int(p.compression)} for i, p in enumerate(tf.pages)]
        desc = tf.pages[0].description or ""
        out["description_head"] = desc[:300]
        out["mpp"], out["app_mag"] = mpp_from_description(desc), mag_from_description(desc)
        levels = tf.series[0].levels
        out["levels"] = [list(lv.shape) for lv in levels]
        out["open_seconds"] = round(time.time() - t0, 2)
        idx = next((i for i, lv in enumerate(levels) if lv.shape[0] * lv.shape[1] <= READ_MAX_PIXELS), None)
        centre = (0.5, 0.5)
        if idx is not None:
            t = time.time()
            low = levels[idx].asarray()
            out["low_read_seconds"] = round(time.time() - t, 2)
            out["low_level"], out["low_shape"] = idx, list(low.shape)
            out["tissue_fraction"] = tissue_fraction(low)
            centre = tissue_centre(low)
            del low
        out["rss_mb_after_low"] = rss_mb()
        page = levels[0].keyframe
        out["tiles_decoded"] = 0
        if page.is_tiled:
            th, tw = page.tilelength, page.tilewidth
            down, across = -(-page.imagelength // th), -(-page.imagewidth // tw)
            out["tile"], out["tiles_total_level0"] = [th, tw], down * across
            r0 = min(max(int(centre[0] * down) - grid // 2, 0), max(down - grid, 0))
            c0 = min(max(int(centre[1] * across) - grid // 2, 0), max(across - grid, 0))
            fh, fractions, t = tf.filehandle, [], time.time()
            for r in range(r0, min(r0 + grid, down)):
                for c in range(c0, min(c0 + grid, across)):
                    i = r * across + c
                    if not page.databytecounts[i]:
                        continue
                    fh.seek(page.dataoffsets[i])
                    tile, _, _ = page.decode(fh.read(page.databytecounts[i]), i, jpegtables=page.jpegtables)
                    out["tiles_decoded"] += 1
                    if tile is not None:
                        fractions.append(tissue_fraction(np.squeeze(np.asarray(tile))) or 0.0)
            secs = time.time() - t
            if out["tiles_decoded"]:
                out["tile_ms"] = round(1000 * secs / out["tiles_decoded"], 2)
                out["grid_tissue_fraction"] = round(sum(fractions) / len(fractions), 4) if fractions else None
                if out.get("tissue_fraction") is not None:
                    est = out["tiles_total_level0"] * out["tissue_fraction"] * out["tile_ms"] / 60000
                    out["est_tissue_decode_minutes_level0"] = round(est, 1)
        else:
            out["note"] = "level 0 is not tiled"
    out["ok"] = True
    out["seconds"] = round(time.time() - t0, 2)
    out["rss_mb_after"] = rss_mb()
    return out


def value_counts(a, limit=50):
    """{value: count} of an integer or boolean 2-D array, counted in row blocks to cap memory."""
    import numpy as np
    if a.dtype == bool:
        a = a.view(np.uint8)
    rows = max(1, 8_000_000 // max(1, a.shape[1]))
    total = None
    for y in range(0, a.shape[0], rows):
        c = np.bincount(a[y:y + rows].ravel())
        if total is None:
            total = c
        else:
            if c.size > total.size:
                c[:total.size] += total
                total = c
            else:
                total[:c.size] += c
    nz = [(int(v), int(total[v])) for v in np.nonzero(total)[0]] if total is not None else []
    return {str(v): n for v, n in nz[:limit]}


def mask_info(path, slide_hw):
    import tifffile
    info = {"name": os.path.basename(path), "bytes": os.path.getsize(path)}
    try:
        with tifffile.TiffFile(path) as tf:
            s = tf.series[0]
            info["shape"], info["dtype"], info["levels"] = list(s.shape), str(s.dtype), len(s.levels)
            hw = hw_of(s.shape)
            info["factor"] = aligned(hw, slide_hw) if (hw and slide_hw) else None
            if hw and hw[0] * hw[1] <= MASK_READ_MAX_PIXELS and s.dtype.kind in "uib":
                a = s.asarray()
                if a.ndim == 2 and a.dtype.kind in "ub":
                    info["values"] = value_counts(a)
                del a
            else:
                info["note"] = "not read (too large or not integer)"
    except Exception as e:
        info["error"] = repr(e)[:300]
    return info


def _sha256_stream(f):
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(CHUNK), b""):
        h.update(chunk)
    return h.hexdigest()


def analyse_package(zip_path, work_dir, slide_hw=None, pas_path=None):
    out = {"ok": False}
    os.makedirs(work_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        out.update(list_zip(z))
        out["svs_members"] = [m for m in out["members"] if m["ext"] == "svs"]
        out["masks"], out["tables"], out["md"], out["xml"] = [], {}, {}, {}
        for m in out["members"]:
            ext, base = m["ext"], os.path.basename(m["name"])
            try:
                if ext in ("tif", "tiff"):
                    dest = os.path.join(work_dir, base)
                    with z.open(m["name"]) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst, CHUNK)
                    out["masks"].append(mask_info(dest, slide_hw))
                    os.remove(dest)
                elif ext == "xlsx":
                    sheets = read_xlsx(io.BytesIO(z.read(m["name"])))
                    out["tables"][base] = {name: summarise_table(rows) for name, rows in sheets.items()}
                elif ext == "md":
                    text = z.read(m["name"]).decode("utf-8", "replace")
                    out["md"][base] = {"chars": len(text), "head": text[:MD_HEAD]}
                elif ext == "xml":
                    out["xml"][base] = xml_summary(z.read(m["name"]))
                elif ext == "svs" and pas_path and os.path.exists(pas_path):
                    with z.open(m["name"]) as src:
                        inner = _sha256_stream(src)
                    with open(pas_path, "rb") as f:
                        m["same_as_pas_small"] = inner == _sha256_stream(f)
            except Exception as e:
                out.setdefault("member_errors", []).append({"member": m["name"], "error": repr(e)[:300]})
    out["ok"] = True
    return out


def tiv_report(path):
    sheets = read_xlsx(path)
    n, per_sheet = participants(sheets)
    return {"ok": True, "sheets": {name: summarise_table(rows) for name, rows in sheets.items()},
            "participants": n, "participant_columns": per_sheet}


def versions():
    out = {"python": sys.version.split()[0]}
    for mod in ("tifffile", "numpy", "imagecodecs"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as e:
            out[mod] = f"unavailable: {e!r}"[:120]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--skip-large", action="store_true", help="for smoke tests only")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    store = os.path.join(args.data_dir, "kpmp")
    os.makedirs(store, exist_ok=True)
    t_start = time.time()
    res = {"prereg": PREREG, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "versions": versions(), "targets": list(TARGETS), "downloads": {}, "slides": {},
           "package": {}, "tiv": {}, "errors": []}
    by_key = {t["key"]: t for t in TARGETS}

    def step(name, fn):
        try:
            return fn()
        except Exception as e:
            res["errors"].append({"step": name, "error": repr(e)[:500]})
            log(f"{name}: {e!r}")
            return None

    def fetch(key):
        t = by_key[key]
        dest = os.path.join(store, t["name"])
        r = download(download_url(t["package"], t["name"]), dest, t["listed"])
        r["listed"], r["size_ok"] = t["listed"], bool(r["ok"]) and size_ok(r["bytes"], t["listed"])
        res["downloads"][key] = r
        log(f"{key}: {json.dumps(r)}")
        return dest if r["ok"] else None

    seg = step("download seg_small", lambda: fetch("seg_small"))
    pas = step("download pas_small", lambda: fetch("pas_small"))
    tiv = step("download tiv", lambda: fetch("tiv"))
    if pas:
        res["slides"]["pas_small"] = step("read pas_small", lambda: read_slide(pas)) or {"ok": False}
    if seg:
        level0 = (res["slides"].get("pas_small", {}).get("levels") or [None])[0]
        slide_hw = hw_of(level0) if level0 else None
        res["package"] = step("package", lambda: analyse_package(seg, os.path.join(store, "extract"),
                                                                 slide_hw, pas)) or {"ok": False}
    if tiv:
        res["tiv"] = step("tiv", lambda: tiv_report(tiv)) or {"ok": False}
    res["rss_mb_after_small"] = rss_mb()
    if not args.skip_large:
        t0 = time.time()
        big = step("download pas_large", lambda: fetch("pas_large"))
        if big:
            res["slides"]["pas_large"] = step("read pas_large", lambda: read_slide(big)) or {"ok": False}
        res["large_minutes"] = round((time.time() - t0) / 60, 1)
        if big and os.path.exists(big):
            os.remove(big)
            res["pas_large_deleted"] = True
    res["verdicts"] = verdicts(res)
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"verdicts": res["verdicts"], "errors": len(res["errors"]), "minutes": res["minutes"],
                      "rss_mb_after_small": res["rss_mb_after_small"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
