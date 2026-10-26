#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_census: do KPMP's open segmentation packages match their own README, and do their
features agree with KPMP's pathologist TIV descriptor scores?

Pre-registration: findings/kpmp-census-prereg-v1-2026-10-26.md.

Every "Segmentation Masks & Pathomics Vectors" package in the KPMP Atlas Repository's own
file-list export (2026-10-18; 361 zips, one per PAS slide) is downloaded once, in a seeded
order. Only the package's small members (feature workbook, OME-XML, README) are kept in the
data volume; the zip, its slide and its masks are deleted straight away. The census then asks:
  - do the workbooks follow the README's units (v1 in microns, v2 in pixels)?
  - does the README's note on IFTA annotations match the mask layer names in the OME-XML?
  - do participant-level tubule features agree with KPMP's TIV descriptor scores?
Only aggregate measurements go to the output. No KPMP file is re-hosted.

A run stops starting downloads after --budget-minutes. A later job with the same data volume
resumes from the cache, so a partial census is always a seeded random subset.

Standard library only. Usage:
  python -m kidney.kpmp_census --file-list inputs/kpmp-segmentation-files.csv --out-dir /out --data-dir /data
"""
import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

PREREG = "findings/kpmp-census-prereg-v1-2026-10-26.md"
CODE_VERSION = "1.0"
DOWNLOAD = "https://atlas.kpmp.org/api/v1/file/download/{package}/{name}"
UA = "mv2-kpmp-census/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
STRATEGY = "Segmentation Masks & Pathomics Vectors"
TIV = {"package": "c6b5e94e-bd60-480d-965e-138ff52d437e",
       "name": "12cbd82d-2533-4706-ba24-de8b23c441dd_KPMP TIV Descriptor Scores 02.19.2026.xlsx",
       "listed": "357 kB"}
SEED = 20261026
IFTA_CUTOFF = "S-2006-005094"
SLIDE_RE = re.compile(r"(S-\d{4}-\d{6})")
IFTA_RE = re.compile(r"ifta|fibros|atroph", re.I)
KEEP_EXT = ("xlsx", "xml", "md")
KEEP_MAX_BYTES = 50_000_000
COORDS = ("x1", "x2", "y1", "y2")
SIZE_TOLERANCE = 0.02
PERMUTATIONS = 10_000
MIN_STRUCTURES = 20
MIN_PACKAGES_PER_VERSION = 10
MIN_AGREEMENT_N = 30
GRADE_MIN_SHARE = 0.95
CHUNK = 1 << 20
UNITS = {"B": 1, "kB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
MICRON_UNITS = ("um", "micron", "microns", "micrometer", "micrometre", chr(0xB5) + "m", chr(0x3BC) + "m")

# (sheet, column) after norm(); the README names the sheets gloms, s_gloms, tubs and arts.
FEATURES = {"lumen": ("tubs", "luminal fraction"),
            "tbm": ("tubs", "average tbm thickness"),
            "cell": ("tubs", "average cell thickness"),
            "glom_area": ("gloms", "area")}
LUMEN_SCORE = "Cortex: Abnormal Tubular Luminal Morphology: Abnormal Luminal Morphology: Percent"
ATROPHY_SCORE = "Cortex: Tubular Atrophy: Common Type: Percent"
INJURY_SCORE = "Cortex: Tubular Injury Other: Percent"
FIBROSIS_SCORE = "Cortex: Interstitial Fibrosis: Percent"
SCORE_COLUMNS = (LUMEN_SCORE, ATROPHY_SCORE, INJURY_SCORE, FIBROSIS_SCORE)
# (key, feature, score, predicted sign); P7-P9 are graded, D1 is descriptive only.
TESTS = (("P7_lumen_vs_abnormal_lumen", "lumen", LUMEN_SCORE, 1),
         ("P8_tbm_vs_atrophy", "tbm", ATROPHY_SCORE, 1),
         ("P9_cell_vs_injury_other", "cell", INJURY_SCORE, -1),
         ("D1_tbm_vs_fibrosis", "tbm", FIBROSIS_SCORE, 1))

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---- file list ----

def parse_size(text):
    """Bytes from the Repository's size column ("11.8 MB", "1 GB"; decimal units)."""
    num, unit = text.strip().split()
    return int(round(float(num) * UNITS[unit]))


def size_ok(actual, listed, tol=SIZE_TOLERANCE):
    want = parse_size(listed)
    return want > 0 and abs(actual - want) <= tol * want


def version_of(name):
    return "v2" if name.lower().endswith("_v2.zip") else "v1"


def slide_of(name):
    m = SLIDE_RE.search(name)
    return m.group(1) if m else ""


def load_packages(path):
    """Open segmentation packages from the Repository's CSV export, in file order."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Experimental Strategy") or "").strip() != STRATEGY:
                continue
            if (row.get("Access") or "").strip().lower() != "open":
                continue
            name = (row.get("File Name") or "").strip()
            pids = [p.strip() for p in (row.get("Participant ID") or "").split(",") if p.strip()]
            out.append({"package": (row.get("Internal Package ID") or "").strip(), "name": name,
                        "listed": (row.get("Size") or "").strip(), "participants": pids,
                        "version": version_of(name), "slide": slide_of(name)})
    return out


def census_order(packages, seed=SEED):
    """Packages sorted by package ID, then shuffled with a fixed seed."""
    order = sorted(packages, key=lambda p: (p["package"], p["name"]))
    random.Random(seed).shuffle(order)
    return order


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
            last = f"HTTP {e.code}"
            if e.code in (401, 403, 404):
                break
        except Exception as e:  # network hiccups: retry
            last = repr(e)[:300]
        if k + 1 < tries:
            pause(5 * (k + 1))
    if os.path.exists(dest + ".part"):
        os.remove(dest + ".part")
    return {"ok": False, "bytes": 0, "error": last, "tries": k + 1}


def ext_of(name):
    base = name.rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def fetch_package(p, cache_root, tmp_dir, get=None, pause=None):
    """Download one package, keep its small members under cache_root/<package>/, delete the zip.
    A package already cached with ok=True is not downloaded again."""
    pdir = os.path.join(cache_root, p["package"])
    rec_path = os.path.join(pdir, "record.json")
    if os.path.exists(rec_path):
        with open(rec_path, encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("ok"):
            rec["cached"] = True
            return rec
    zpath = os.path.join(tmp_dir, "package.zip")
    d = download(download_url(p["package"], p["name"]), zpath, get=get, pause=pause)
    rec = {"ok": False, "download": d, "size_ok": bool(d["ok"]) and size_ok(d["bytes"], p["listed"]),
           "members": [], "kept": [], "cached": False}
    if d["ok"]:
        try:
            os.makedirs(pdir, exist_ok=True)
            with zipfile.ZipFile(zpath) as z:
                for i in z.infolist():
                    if i.is_dir():
                        continue
                    base, ext = os.path.basename(i.filename), ext_of(i.filename)
                    rec["members"].append({"name": i.filename, "bytes": i.file_size, "ext": ext})
                    if ext in KEEP_EXT and i.file_size <= KEEP_MAX_BYTES and base not in rec["kept"]:
                        with z.open(i) as src, open(os.path.join(pdir, base), "wb") as dst:
                            shutil.copyfileobj(src, dst, CHUNK)
                        rec["kept"].append(base)
            rec["ok"] = True
        except Exception as e:
            rec["error"] = repr(e)[:300]
        finally:
            if os.path.exists(zpath):
                os.remove(zpath)
        if rec["ok"]:
            with open(rec_path, "w", encoding="utf-8") as f:
                json.dump(rec, f)
    return rec


# ---- reading kept members ----

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


def parse_float(x):
    try:
        v = float(str(x).strip())
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def norm(name):
    """Lower case, text in brackets dropped, spaces collapsed: "Area (pixels)" -> "area"."""
    s = re.sub(r"[\(\[].*?[\)\]]", " ", str(name or ""))
    return " ".join(s.lower().split())


def unit_power(column):
    """Power of length a feature carries: 0 unitless, 1 length, 2 area, None unknown."""
    c = norm(column)
    if "fraction" in c or "ratio" in c:
        return 0
    if "area" in c:
        return 2
    if any(w in c for w in ("thickness", "length", "diameter", "perimeter", "distance", "width")):
        return 1
    return None


def convert(value, version, power, mpp):
    """A feature value in microns: v1 values are taken as microns already (README), v2 values
    are pixels and are multiplied by mpp ** power. None if that cannot be done."""
    if value is None:
        return None
    if version == "v1" or power == 0:
        return value
    if power is None or not mpp:
        return None
    return value * mpp ** power


def sheet_table(rows):
    """(header, data rows): the header is the fullest of the first 10 non-empty rows."""
    filled = [r for r in rows if any(_filled(x) for x in r)]
    if not filled:
        return [], []
    counts = [sum(1 for x in r if _filled(x)) for r in filled[:10]]
    head_i = counts.index(max(counts))
    header = [str(x).strip() if _filled(x) else f"col{j + 1}" for j, x in enumerate(filled[head_i])]
    return header, filled[head_i + 1:]


def ome_info(data):
    """Microns per pixel, size and channel names from an OME-XML document."""
    root = ET.fromstring(data)
    out = {"mpp_x": None, "mpp_y": None, "unit": None, "size_x": None, "size_y": None, "channels": []}
    seen_pixels = False
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "Pixels" and not seen_pixels:
            seen_pixels = True
            out["mpp_x"], out["mpp_y"] = parse_float(el.get("PhysicalSizeX")), parse_float(el.get("PhysicalSizeY"))
            out["unit"] = el.get("PhysicalSizeXUnit")
            out["size_x"], out["size_y"] = parse_float(el.get("SizeX")), parse_float(el.get("SizeY"))
        elif tag == "Channel":
            out["channels"].append(el.get("Name") or el.get("ID") or "")
    unit = (out["unit"] or chr(0xB5) + "m").strip().lower()
    out["mpp"] = out["mpp_x"] if unit in MICRON_UNITS else None
    return out


def readme_info(text):
    low = text.lower()
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "chars": len(text),
            "v2_pixels_sentence": "in v2 measurements" in low and "pixels" in low,
            "ifta_note": "do not contain annotations for interstitial fibrosis" in low}


def analyse_dir(path, version):
    """Readme, OME and workbook facts plus raw values of the FEATURES from one cached package."""
    out = {"readme": None, "ome": None, "xlsx": 0, "sheets": {}, "values": {}, "errors": []}
    for fn in sorted(os.listdir(path)):
        full, ext = os.path.join(path, fn), ext_of(fn)
        try:
            if ext == "md":
                with open(full, encoding="utf-8", errors="replace") as f:
                    out["readme"] = readme_info(f.read())
            elif ext == "xml":
                with open(full, "rb") as f:
                    out["ome"] = ome_info(f.read())
            elif ext == "xlsx":
                out["xlsx"] += 1
                for name, rows in read_xlsx(full).items():
                    header, data = sheet_table(rows)
                    s = out["sheets"].setdefault(norm(name), {"n_rows": 0, "header": header, "medians": {}})
                    s["n_rows"] += len(data)
                    for j, col in enumerate(header):
                        if norm(col) in COORDS:
                            continue
                        vals = [v for v in (parse_float(r[j]) if j < len(r) else None for r in data) if v is not None]
                        if vals:
                            s["medians"][col] = statistics.median(vals)
                        for key, (sheet, column) in FEATURES.items():
                            if norm(name) == sheet and norm(col) == column:
                                out["values"].setdefault(key, []).extend(vals)
        except Exception as e:
            out["errors"].append({"member": fn, "error": repr(e)[:300]})
    mpp = (out["ome"] or {}).get("mpp")
    out["features"] = {}
    for key, (sheet, column) in FEATURES.items():
        raw = out["values"].get(key, [])
        conv = [c for c in (convert(v, version, unit_power(column), mpp) for v in raw) if c is not None]
        out["features"][key] = {"n": len(raw), "median_raw": statistics.median(raw) if raw else None,
                                "median_conv": statistics.median(conv) if conv else None}
    return out


# ---- TIV workbook ----

def tiv_table(sheets, sheet_name="Data Table"):
    """({participant: {score column: value}}, info). Participants with more than one row, or
    whose row is not marked consensus complete, are left out."""
    rows = sheets.get(sheet_name) or []
    head_i = next((i for i, r in enumerate(rows) if r and str(r[0] or "").strip() == "Participant ID"), None)
    if head_i is None:
        return {}, {"error": "no 'Participant ID' header row"}
    header = [str(x).strip() if x is not None else "" for x in rows[head_i]]
    by_pid = {}
    for r in rows[head_i + 1:]:
        if not r or not _filled(r[0]):
            continue
        by_pid.setdefault(str(r[0]).strip(), []).append({h: (r[j] if j < len(r) else None)
                                                         for j, h in enumerate(header) if h})
    info = {"rows": sum(len(v) for v in by_pid.values()), "participants": len(by_pid), "duplicated": 0,
            "not_consensus": 0, "missing_columns": [c for c in SCORE_COLUMNS if c not in header]}
    scores = {}
    for pid, rs in by_pid.items():
        if len(rs) > 1:
            info["duplicated"] += 1
            continue
        if str(rs[0].get("Consensus Complete") or "").strip().upper() != "Y":
            info["not_consensus"] += 1
            continue
        scores[pid] = {c: parse_float(rs[0].get(c)) for c in SCORE_COLUMNS}
    info["usable"] = len(scores)
    return scores, info


# ---- statistics ----

def ranks(v):
    """Average ranks (1-based), ties share the mean rank."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    if saa == 0 or sbb == 0:
        return None
    return sab / (saa * sbb) ** 0.5


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def perm_p(x, y, direction, n_perm=PERMUTATIONS, seed=SEED):
    """One-sided permutation p for Spearman rho in the predicted direction (+1 or -1)."""
    rx, ry = ranks(x), ranks(y)
    obs = pearson(rx, ry)
    if obs is None:
        return None
    rng, ry, hits = random.Random(seed), list(ry), 0
    for _ in range(n_perm):
        rng.shuffle(ry)
        r = pearson(rx, ry)
        if r is not None and direction * r >= direction * obs - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def _median(v):
    return statistics.median(v) if v else None


# ---- census summaries ----

def participant_table(records):
    """{participant: {"versions", "n_tubs", "raw": {feature: [..]}, "conv": {feature: [..]}}} from
    analysed packages that belong to exactly one participant."""
    out = {}
    for r in records:
        a = r.get("analysis")
        if not a or len(r["participants"]) != 1:
            continue
        p = out.setdefault(r["participants"][0], {"versions": set(), "n_tubs": 0, "raw": {}, "conv": {}})
        p["versions"].add(r["version"])
        p["n_tubs"] += (a["sheets"].get("tubs") or {}).get("n_rows", 0)
        mpp = (a.get("ome") or {}).get("mpp")
        for key, (sheet, column) in FEATURES.items():
            raw = a.get("values", {}).get(key, [])
            p["raw"].setdefault(key, []).extend(raw)
            p["conv"].setdefault(key, []).extend(
                c for c in (convert(v, r["version"], unit_power(column), mpp) for v in raw) if c is not None)
    return out


def agreement(ptable, scores, feature, score, direction, mode="conv", versions=None, n_perm=PERMUTATIONS,
              seed=SEED):
    """Spearman rho (and permutation p if n_perm) between participant medians of a feature and a TIV score."""
    xs, ys = [], []
    for pid in sorted(ptable):
        p = ptable[pid]
        if pid not in scores or scores[pid].get(score) is None or p["n_tubs"] < MIN_STRUCTURES:
            continue
        if versions is not None and p["versions"] != versions:
            continue
        m = _median(p[mode].get(feature, []))
        if m is None:
            continue
        xs.append(m)
        ys.append(scores[pid][score])
    out = {"n": len(xs), "rho": spearman(xs, ys) if len(xs) >= 3 else None}
    if n_perm and out["rho"] is not None:
        out["p_one_sided"] = perm_p(xs, ys, direction, n_perm, seed)
    return out


def version_ratio(records, feature):
    """Median of package medians in v2 over v1, raw and with v2 converted to microns."""
    meds = {"v1": [], "v2": [], "v2_conv": []}
    for r in records:
        f = ((r.get("analysis") or {}).get("features") or {}).get(feature) or {}
        if f.get("median_raw") is None:
            continue
        meds[r["version"]].append(f["median_raw"])
        if r["version"] == "v2" and f.get("median_conv") is not None:
            meds["v2_conv"].append(f["median_conv"])
    out = {k: {"packages": len(v), "median": _median(v)} for k, v in meds.items()}
    v1 = out["v1"]["median"]
    ok = out["v1"]["packages"] >= MIN_PACKAGES_PER_VERSION and v1
    out["raw_ratio"] = (out["v2"]["median"] / v1
                        if ok and out["v2"]["packages"] >= MIN_PACKAGES_PER_VERSION else None)
    out["converted_ratio"] = (out["v2_conv"]["median"] / v1
                              if ok and out["v2_conv"]["packages"] >= MIN_PACKAGES_PER_VERSION else None)
    return out


def ifta_check(records, cutoff=IFTA_CUTOFF):
    """README: masks of slides after the cutoff (alphanumerically) have no IFTA layer."""
    rows = []
    for r in records:
        ome = (r.get("analysis") or {}).get("ome")
        if ome is None or not r["slide"]:
            continue
        rows.append((r["slide"] > cutoff, any(IFTA_RE.search(c or "") for c in ome["channels"])))
    after = [h for a, h in rows if a]
    before = [h for a, h in rows if not a]
    out = {"packages": len(rows), "after": len(after), "after_with_ifta": sum(after),
           "before": len(before), "before_with_ifta": sum(before)}
    if not any(h for _, h in rows):
        out["grade"] = "untestable"
    elif not after or not before:
        out["grade"] = "untestable"
    else:
        out["grade"] = "pass" if sum(after) == 0 and sum(before) >= 0.9 * len(before) else "fail"
    return out


def _within(v, lo=None, hi=None):
    if v is None:
        return "untestable"
    return "pass" if (lo is None or v >= lo) and (hi is None or v <= hi) else "fail"


def grade(res):
    c, g = res["census"], {}
    if c["attempted"] < c["listed"]:
        g["P1_access"] = "pending"
    else:
        g["P1_access"] = "pass" if c["listed"] and c["download_ok_size_ok"] >= GRADE_MIN_SHARE * c["listed"] else "fail"
    keys = ("P2_tbm_raw_ratio", "P3_tbm_converted_ratio", "P4_glom_area_raw_ratio",
            "P5_glom_area_converted_ratio", "P6_ifta_note") + tuple(t[0] for t in TESTS if t[0].startswith("P"))
    if not c["listed"] or c["analysed"] < GRADE_MIN_SHARE * c["listed"]:
        g.update({k: "pending" for k in keys})
        g["status"] = "incomplete"
        return g
    u = res["unit_checks"]
    g["P2_tbm_raw_ratio"] = _within(u["tbm"]["raw_ratio"], 2.0)
    g["P3_tbm_converted_ratio"] = _within(u["tbm"]["converted_ratio"], 0.67, 1.5)
    g["P4_glom_area_raw_ratio"] = _within(u["glom_area"]["raw_ratio"], 4.0)
    g["P5_glom_area_converted_ratio"] = _within(u["glom_area"]["converted_ratio"], 0.5, 2.0)
    g["P6_ifta_note"] = res["ifta"]["grade"]
    for key, _, _, direction in TESTS:
        if not key.startswith("P"):
            continue
        a = res["agreement"][key]["conv"]
        if a["n"] < MIN_AGREEMENT_N or a["rho"] is None or a.get("p_one_sided") is None:
            g[key] = "untestable"
        else:
            g[key] = "pass" if direction * a["rho"] > 0 and a["p_one_sided"] < 0.05 else "fail"
    g["status"] = "complete"
    return g


def describe(records):
    """Aggregate facts about the analysed packages, by version."""
    sheets, readmes, mpps, channels, nchan, errors = {}, Counter(), {}, Counter(), Counter(), Counter()
    for r in records:
        a = r.get("analysis")
        if not a:
            continue
        v = r["version"]
        for name, s in a["sheets"].items():
            d = sheets.setdefault(v, {}).setdefault(name, {"present": 0, "empty": 0, "headers": Counter()})
            d["present"] += 1
            d["empty"] += s["n_rows"] == 0
            d["headers"]["|".join(s["header"])] += 1
        if a["readme"]:
            rd = a["readme"]
            readmes[(v, rd["sha256"][:12], rd["v2_pixels_sentence"], rd["ifta_note"])] += 1
        else:
            readmes[(v, "none", False, False)] += 1
        ome = a.get("ome") or {}
        if ome.get("mpp"):
            mpps.setdefault(v, []).append(ome["mpp"])
        for ch in ome.get("channels", []):
            channels[(v, ch)] += 1
        nchan[(v, len(ome.get("channels", [])))] += 1
        errors[(v, len(a["errors"]), a["xlsx"])] += 1
    for v in sheets:
        for d in sheets[v].values():
            d["headers"] = [{"header": h, "packages": n} for h, n in d["headers"].most_common()]
    return {"sheets": sheets,
            "readmes": [{"version": k[0], "sha256_12": k[1], "v2_pixels_sentence": k[2], "ifta_note": k[3],
                         "packages": n} for k, n in sorted(readmes.items())],
            "mpp": {v: {"packages": len(m), "min": min(m), "median": statistics.median(m), "max": max(m)}
                    for v, m in mpps.items()},
            "channel_names": [{"version": k[0], "name": k[1], "packages": n} for k, n in sorted(channels.items())],
            "channel_counts": [{"version": k[0], "channels": k[1], "packages": n} for k, n in sorted(nchan.items())],
            "errors_and_workbooks": [{"version": k[0], "errors": k[1], "xlsx": k[2], "packages": n}
                                     for k, n in sorted(errors.items())]}


def package_row(p, rec):
    """What goes to the output for one package: no participant ID, no feature values."""
    a = rec.get("analysis") or {}
    return {"package": p["package"], "version": p["version"], "slide": p["slide"], "listed": p["listed"],
            "ok": rec.get("ok", False), "size_ok": rec.get("size_ok", False), "cached": rec.get("cached"),
            "status": rec.get("status", "attempted"), "download": rec.get("download"),
            "members": len(rec.get("members", [])), "kept": rec.get("kept", []),
            "mpp": (a.get("ome") or {}).get("mpp"), "channels": len((a.get("ome") or {}).get("channels", [])),
            "sheets": {k: s["n_rows"] for k, s in (a.get("sheets") or {}).items()},
            "features": a.get("features"), "errors": a.get("errors", []) + ([rec["error"]] if rec.get("error") else [])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--permutations", type=int, default=PERMUTATIONS)
    ap.add_argument("--limit", type=int, default=0, help="for smoke tests only")
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kpmp-census-")
    packages = load_packages(args.file_list)
    order = census_order(packages)
    if args.limit:
        order = order[:args.limit]
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": SEED,
           "file_list": {"packages": len(packages), "by_version": dict(Counter(p["version"] for p in packages)),
                         "multi_participant": sum(len(p["participants"]) != 1 for p in packages)}}
    deadline = t_start + args.budget_minutes * 60
    records = []
    with open(os.path.join(args.out_dir, "progress.jsonl"), "a", encoding="utf-8") as prog:
        for i, p in enumerate(order):
            cached = os.path.exists(os.path.join(cache, p["package"], "record.json"))
            if not cached and time.time() > deadline:
                rec = {"ok": False, "status": "not_attempted"}
            else:
                try:
                    rec = fetch_package(p, cache, tmp)
                except Exception as e:
                    rec = {"ok": False, "error": repr(e)[:300]}
                if rec.get("ok"):
                    rec["analysis"] = analyse_dir(os.path.join(cache, p["package"]), p["version"])
            records.append(dict(p, **rec))
            row = package_row(p, rec)
            prog.write(json.dumps({"i": i, "package": p["package"], "ok": row["ok"], "status": row["status"],
                                   "cached": row["cached"], "seconds": (rec.get("download") or {}).get("seconds")})
                       + "\n")
            prog.flush()
            if not row["cached"] and row["status"] != "not_attempted":
                log(f"{i + 1}/{len(order)} {p['package']} ok={row['ok']} size_ok={row['size_ok']}")
    shutil.rmtree(tmp, ignore_errors=True)
    listed = len(order)
    res["census"] = {"listed": listed,
                     "attempted": sum(r.get("status") != "not_attempted" for r in records),
                     "download_ok_size_ok": sum(bool(r.get("ok") and r.get("size_ok")) for r in records),
                     "analysed": sum(1 for r in records if r.get("analysis")),
                     "cached_before_this_run": sum(1 for r in records if r.get("cached")),
                     "bytes_downloaded_this_run": sum((r.get("download") or {}).get("bytes", 0)
                                                      for r in records if not r.get("cached"))}
    res["packages"] = [package_row(p, r) for p, r in zip(order, records)]
    res["describe"] = describe(records)
    res["unit_checks"] = {k: version_ratio(records, k) for k in ("tbm", "cell", "glom_area", "lumen")}
    res["ifta"] = ifta_check(records)
    tiv_dir = os.path.join(cache, "tiv")
    os.makedirs(tiv_dir, exist_ok=True)
    tiv_path = os.path.join(tiv_dir, "tiv.xlsx")
    scores = {}
    if not os.path.exists(tiv_path):
        d = download(download_url(TIV["package"], TIV["name"]), tiv_path)
        res["tiv_download"] = d
    if os.path.exists(tiv_path):
        try:
            scores, res["tiv"] = tiv_table(read_xlsx(tiv_path))
        except Exception as e:
            res["tiv"] = {"error": repr(e)[:300]}
    ptable = participant_table(records)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "both_versions": sum(1 for p in ptable.values() if len(p["versions"]) > 1),
                           "under_min_structures": sum(1 for p in ptable.values() if p["n_tubs"] < MIN_STRUCTURES)}
    res["agreement"] = {}
    for k, (key, feature, score, direction) in enumerate(TESTS):
        res["agreement"][key] = {
            "feature": feature, "score": score, "direction": direction,
            "conv": agreement(ptable, scores, feature, score, direction, "conv", None, args.permutations, SEED + k),
            "raw": agreement(ptable, scores, feature, score, direction, "raw", None, args.permutations, SEED + k),
            "v1_only": agreement(ptable, scores, feature, score, direction, "conv", {"v1"}, 0),
            "v2_only": agreement(ptable, scores, feature, score, direction, "conv", {"v2"}, 0)}
    res["grades"] = grade(res)
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"census": res["census"], "grades": res["grades"], "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
