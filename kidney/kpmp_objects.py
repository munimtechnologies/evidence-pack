#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_objects: an object-level audit of KPMP's released v2 pathomics vectors.

Pre-registration: findings/kpmp-objects-prereg-v1-2026-10-27.md.

Reads only the feature workbooks that census pass 1 kept in the data volume
(/data/kpmp-census/<package>/): no download, no file list, no participant or clinical data.
For every v2 package (one workbook with the sheets gloms, s_gloms, tubs and arts) it asks
  - integrity: are the boxes valid, do areas fit in their boxes, does the mesangial fraction equal
    mesangial area / area, are fractions within [0, 1], is any glomerulus segmented twice, are
    tubule rows duplicated?
  - rarity: which objects are rare against all v2 objects (pooled) and which against their own
    slide, how unevenly within-slide outliers spread over slides, whether outlier glomeruli have
    the shape of segmentation errors, and whether outlier tubules cluster in space.
Only aggregate measurements go to results.json. candidates.json (box coordinates of the most
extreme within-slide outliers) is for expert review only and is not published.

Standard library only. Usage:
  python -m kidney.kpmp_objects --data-dir /data --out-dir /out
"""
import argparse
import json
import math
import os
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

PREREG = "findings/kpmp-objects-prereg-v1-2026-10-27.md"
CODE_VERSION = "1.0"
SEED = 20261027
COORDS = ("x1", "x2", "y1", "y2")
# Exact header text that census pass 2 recorded for all 220 v2 packages (describe.sheets.v2).
COLUMNS = {"gloms": COORDS + ("Area", "Mesangial Area", "Mesangial Fraction"),
           "s_gloms": COORDS + ("Area", "Mesangial Area", "Mesangial Fraction"),
           "tubs": COORDS + ("Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"),
           "arts": COORDS + ("Arterial Area",)}
SHEETS = tuple(COLUMNS)
# Features screened for rarity, per compartment: (column, transform); "log" needs a positive value.
SCREEN = {"gloms": (("Area", "log"), ("Mesangial Fraction", "raw")),
          "tubs": (("Average TBM Thickness", "log"), ("Average Cell Thickness", "log"),
                   ("Luminal Fraction", "raw")),
          "arts": (("Arterial Area", "log"),)}
Z_CUT = 4.0
MAD_SCALE = 1.4826
MIN_PACKAGES = 200
MIN_SLIDE_OBJECTS = 20
FILL_MAX = 1.05
FILL_LOW = 0.5
ASPECT_HIGH = 2.5
IOU_DUP = 0.5
MES_TOL = 1e-3
MIN_R1_OUTLIERS = 30
MIN_R2_SLIDES = 20
MIN_R3_OUTLIERS = 10
NN_MIN_OUTLIERS = 10
NN_CAP = 500
NN_DRAWS = 20
MIN_NN_SLIDES = 20
CANDIDATES = 30
# (key, prediction): every integrity check is graded on its own threshold.
PREDICTIONS = {"I1_box_valid": "share >= 0.999",
               "I2_glom_fill_median": "0.45 <= median <= 1.0",
               "I3_area_in_box": "share >= 0.99",
               "I4_mesangial_consistent": "share >= 0.99",
               "I5_fractions_in_range": "share >= 0.999",
               "I6_glom_double_segmentation": "share < 0.01",
               "I7_tubule_duplicates": "share < 0.001",
               "R1_tubule_pooled_outliers_slide_explained": "share >= 0.5",
               "R2_tubule_outlier_overdispersion": "dispersion > 2",
               "R3_glom_outliers_misshapen": "odds ratio >= 2",
               "R4_tubule_outliers_cluster": "clustered share >= 0.6 and sign-test p < 0.05"}

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---- reading ----

def col_index(ref):
    m = CELL_REF.match(ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx(path):
    """{sheet name: rows} from an xlsx path; each row a list of cell texts (None if empty)."""
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
    """Lower case, text in brackets dropped, spaces collapsed (used for sheet names only)."""
    s = re.sub(r"[\(\[].*?[\)\]]", " ", str(name or ""))
    return " ".join(s.lower().split())


def sheet_table(rows):
    """(header, data rows): the header is the fullest of the first 10 non-empty rows."""
    filled = [r for r in rows if any(_filled(x) for x in r)]
    if not filled:
        return [], []
    counts = [sum(1 for x in r if _filled(x)) for r in filled[:10]]
    head_i = counts.index(max(counts))
    header = [str(x).strip() if _filled(x) else f"col{j + 1}" for j, x in enumerate(filled[head_i])]
    return header, filled[head_i + 1:]


def package_dirs(cache):
    """Package folders of the census cache whose record.json says ok (skips tiv/, clinical/)."""
    out = []
    if not os.path.isdir(cache):
        return out
    for name in sorted(os.listdir(cache)):
        d = os.path.join(cache, name)
        rec = os.path.join(d, "record.json")
        if not os.path.isfile(rec):
            continue
        try:
            with open(rec, encoding="utf-8") as f:
                ok = json.load(f).get("ok")
        except Exception:
            ok = False
        if ok:
            out.append(d)
    return out


def load_v2(d, seen=None):
    """(status, tables) for one package folder. status is "v2", "not_v2" or "v2_missing_columns";
    tables maps each sheet key to a list of row tuples of floats (None if empty) in COLUMNS order.
    seen (a Counter) gets the raw sheet names and raw headers."""
    books = [fn for fn in sorted(os.listdir(d)) if fn.lower().endswith(".xlsx")]
    if len(books) != 1:  # v1 packages carry 2-4 workbooks
        return "not_v2", None
    book = read_xlsx(os.path.join(d, books[0]))
    keyed = {}
    for raw in book:
        keyed.setdefault(norm(raw), raw)
    if not all(k in keyed for k in SHEETS):
        if seen is not None:
            seen[("other_sheet_names", "|".join(sorted(book)))] += 1
        return "not_v2", None
    if seen is not None:
        seen[("sheet_names", "|".join(sorted(book)))] += 1
    tables, status = {}, "v2"
    for key in SHEETS:
        header, data = sheet_table(book[keyed[key]])
        if seen is not None:
            seen[("header:" + key, "|".join(header))] += 1
        idx = {h: j for j, h in enumerate(header)}
        if any(c not in idx for c in COLUMNS[key]):
            status = "v2_missing_columns"
            continue
        cols = [idx[c] for c in COLUMNS[key]]
        tables[key] = [tuple(parse_float(r[j]) if j < len(r) else None for j in cols) for r in data]
    return status, (tables if status == "v2" else None)


# ---- geometry ----

def box(r):
    """(x1, x2, y1, y2) of a row if all four are numbers and x2 > x1, y2 > y1; else None."""
    x1, x2, y1, y2 = r[0], r[1], r[2], r[3]
    if None in (x1, x2, y1, y2) or x2 <= x1 or y2 <= y1:
        return None
    return (x1, x2, y1, y2)


def fill(r):
    """Area / box area (index 4 is Area or Arterial Area), or None."""
    b = box(r)
    if b is None or r[4] is None:
        return None
    return r[4] / ((b[1] - b[0]) * (b[3] - b[2]))


def aspect(r):
    b = box(r)
    if b is None:
        return None
    w, h = b[1] - b[0], b[3] - b[2]
    return max(w, h) / min(w, h)


def iou(a, b):
    ix = min(a[1], b[1]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[2], b[2])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    return inter / ((a[1] - a[0]) * (a[3] - a[2]) + (b[1] - b[0]) * (b[3] - b[2]) - inter)


def misshapen(r):
    """Shape of a likely segmentation error: fill below FILL_LOW or aspect above ASPECT_HIGH."""
    f, a = fill(r), aspect(r)
    return (f is not None and f < FILL_LOW) or (a is not None and a > ASPECT_HIGH)


def centre(r):
    b = box(r)
    return None if b is None else ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2)


def mean_nn(points):
    """Mean nearest-neighbour distance of 2+ points (sweep over x)."""
    pts = sorted(points)
    n, total = len(pts), 0.0
    for i, (x, y) in enumerate(pts):
        best = float("inf")
        j = i - 1
        while j >= 0 and x - pts[j][0] < best:
            best = min(best, math.hypot(x - pts[j][0], y - pts[j][1]))
            j -= 1
        j = i + 1
        while j < n and pts[j][0] - x < best:
            best = min(best, math.hypot(x - pts[j][0], y - pts[j][1]))
            j += 1
        total += best
    return total / n


# ---- statistics ----

def median(v):
    if not v:
        return None
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def robust(vals):
    """(median, MAD * 1.4826); the scale is None if it is zero or there are under 2 values."""
    if len(vals) < 2:
        return median(vals), None
    med = median(vals)
    mad = median([abs(v - med) for v in vals]) * MAD_SCALE
    return med, (mad if mad > 0 else None)


def binom_tail(m, s):
    """P(X >= s) for X ~ Binomial(m, 1/2)."""
    return sum(math.comb(m, k) for k in range(s, m + 1)) / 2 ** m


def dispersion(counts):
    """Pearson chi-square / df of (outliers, objects) per slide against one common rate."""
    n = sum(t for _, t in counts)
    o = sum(k for k, _ in counts)
    if n == 0 or o == 0 or o == n or len(counts) < 2:
        return None
    p = o / n
    chi2 = sum((k - t * p) ** 2 / (t * p * (1 - p)) for k, t in counts)
    return chi2 / (len(counts) - 1)


def _share(k, n):
    return round(k / n, 6) if n else None


# ---- integrity ----

def integrity(packages):
    c = Counter()
    fills = {"gloms": [], "s_gloms": [], "arts": []}
    pkg_fill = []
    dup_gloms = set()
    for i, (_, t) in enumerate(packages):
        for key in SHEETS:
            for r in t[key]:
                c["objects"] += 1
                c["box_valid"] += box(r) is not None
        for key in fills:
            for r in t[key]:
                f = fill(r)
                if f is not None:
                    fills[key].append(f)
                    c["fill_n"] += 1
                    c["fill_ok"] += f <= FILL_MAX
        pf = median([f for f in (fill(r) for r in t["gloms"]) if f is not None])
        if pf is not None:
            pkg_fill.append(pf)
        for key in ("gloms", "s_gloms"):
            for r in t[key]:
                area, mes, frac = r[4], r[5], r[6]
                if frac is not None:
                    c["mes_frac_n"] += 1
                    c["mes_frac_in_range"] += 0 <= frac <= 1
                if area and area > 0 and mes is not None and frac is not None:
                    c["mes_n"] += 1
                    c["mes_ok"] += abs(frac - mes / area) <= MES_TOL * (1 + abs(frac))
                    b = box(r)
                    if b is not None:
                        c["mes_box_n"] += 1
                        c["mes_box_ok"] += abs(frac - mes / ((b[1] - b[0]) * (b[3] - b[2]))) <= MES_TOL * (1 + abs(frac))
        for r in t["tubs"]:
            if r[6] is not None:
                c["lumen_n"] += 1
                c["lumen_in_range"] += 0 <= r[6] <= 1
            c["tubs_nonpositive_tbm"] += r[4] is not None and r[4] <= 0
            c["tubs_nonpositive_cell"] += r[5] is not None and r[5] <= 0
        c["tubs_rows"] += len(t["tubs"])
        c["tubs_duplicate_rows"] += len(t["tubs"]) - len(set(t["tubs"]))
        gl = [(key, j, box(r)) for key in ("gloms", "s_gloms") for j, r in enumerate(t[key]) if box(r) is not None]
        c["gloms_boxed"] += len(gl)
        for a in range(len(gl)):
            for b in range(a + 1, len(gl)):
                if iou(gl[a][2], gl[b][2]) >= IOU_DUP:
                    c["dup_pairs_same_sheet" if gl[a][0] == gl[b][0] else "dup_pairs_cross_sheet"] += 1
                    dup_gloms.add((i, gl[a][0], gl[a][1]))
                    dup_gloms.add((i, gl[b][0], gl[b][1]))
    fr = (c["mes_frac_in_range"] + c["lumen_in_range"], c["mes_frac_n"] + c["lumen_n"])
    out = {"counts": dict(c),
           "I1_box_valid": _share(c["box_valid"], c["objects"]),
           "I2_glom_fill_median": median(fills["gloms"]),
           "I3_area_in_box": _share(c["fill_ok"], c["fill_n"]),
           "I4_mesangial_consistent": _share(c["mes_ok"], c["mes_n"]),
           "I4_alt_mesangial_over_box": _share(c["mes_box_ok"], c["mes_box_n"]),
           "I5_fractions_in_range": _share(*fr),
           "I6_glom_double_segmentation": _share(len(dup_gloms), c["gloms_boxed"]),
           "I7_tubule_duplicates": _share(c["tubs_duplicate_rows"], c["tubs_rows"]),
           "fill_by_sheet": {k: {"n": len(v), "median": median(v),
                                 "over_max": sum(1 for f in v if f > FILL_MAX),
                                 "under_low": sum(1 for f in v if f < FILL_LOW)} for k, v in fills.items()},
           "package_glom_fill_median": {"packages": len(pkg_fill), "min": min(pkg_fill, default=None),
                                        "median": median(pkg_fill), "max": max(pkg_fill, default=None)}}
    return out, dup_gloms


# ---- rarity ----

def screen_vector(r, comp):
    out = []
    for col, kind in SCREEN[comp]:
        v = r[COLUMNS[comp].index(col)]
        if v is not None and kind == "log":
            v = math.log(v) if v > 0 else None
        out.append(v)
    return out


def score_objects(packages, comp, min_slide=MIN_SLIDE_OBJECTS):
    """(summary, objects). objects: (package index, row index, max |pooled z|, max |slide z|,
    slide feature, slide sign) for every eligible object: all screened features defined, in a
    slide with at least min_slide such objects and non-zero spread on every feature."""
    feats = [col for col, _ in SCREEN[comp]]
    vecs = []
    for _, t in packages:
        pk = []
        for j, r in enumerate(t[comp]):
            v = screen_vector(r, comp)
            if None not in v:
                pk.append((j, v))
        vecs.append(pk)
    summary = {"objects": sum(len(t[comp]) for _, t in packages), "complete": sum(len(pk) for pk in vecs)}
    pooled = [robust([v[f] for pk in vecs for _, v in pk]) for f in range(len(feats))]
    summary["pooled"] = {feats[f]: {"median": pooled[f][0], "scale": pooled[f][1]} for f in range(len(feats))}
    objs = []
    if any(s is None for _, s in pooled):
        summary["error"] = "zero pooled spread"
        return summary, objs
    slides = 0
    for i, pk in enumerate(vecs):
        if len(pk) < min_slide:
            continue
        st = [robust([v[f] for _, v in pk]) for f in range(len(feats))]
        if any(s is None for _, s in st):
            continue
        slides += 1
        for j, v in pk:
            zp = max(abs(v[f] - pooled[f][0]) / pooled[f][1] for f in range(len(feats)))
            zs = [(v[f] - st[f][0]) / st[f][1] for f in range(len(feats))]
            f_max = max(range(len(feats)), key=lambda f: abs(zs[f]))
            objs.append((i, j, zp, abs(zs[f_max]), f_max, 1 if zs[f_max] > 0 else -1))
    po = [o for o in objs if o[2] >= Z_CUT]
    so = [o for o in objs if o[3] >= Z_CUT]
    by = Counter((feats[o[4]], "high" if o[5] > 0 else "low") for o in so)
    summary.update({"slides": slides, "eligible": len(objs), "pooled_outliers": len(po),
                    "slide_outliers": len(so), "both": sum(1 for o in po if o[3] >= Z_CUT),
                    "slide_outliers_by_feature": [{"feature": f, "direction": d, "n": n}
                                                  for (f, d), n in sorted(by.items())]})
    return summary, objs


def r1(objs):
    po = [o for o in objs if o[2] >= Z_CUT]
    k = sum(1 for o in po if o[3] < Z_CUT)
    return {"pooled_outliers": len(po), "not_slide_outliers": k, "share": _share(k, len(po))}


def r2(objs, min_slides=MIN_R2_SLIDES):
    per = {}
    for o in objs:
        k, t = per.get(o[0], (0, 0))
        per[o[0]] = (k + (o[3] >= Z_CUT), t + 1)
    counts = list(per.values())
    rates = sorted(k / t for k, t in counts)
    return {"slides": len(counts), "outliers": sum(k for k, _ in counts), "objects": sum(t for _, t in counts),
            "dispersion": dispersion(counts) if len(counts) >= min_slides else None,
            "slide_rate": {"min": rates[0] if rates else None, "median": median(rates),
                           "max": rates[-1] if rates else None}}


def r3(objs, packages, dup_gloms):
    tab = Counter()
    for o in objs:
        r = packages[o[0]][1]["gloms"][o[1]]
        tab[(o[3] >= Z_CUT, misshapen(r))] += 1
    a, b = tab[(True, True)], tab[(True, False)]
    c, d = tab[(False, True)], tab[(False, False)]
    odds = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    outl = [o for o in objs if o[3] >= Z_CUT]
    return {"outliers_misshapen": a, "outliers_other": b, "rest_misshapen": c, "rest_other": d,
            "odds_ratio": round(odds, 4),
            "outliers_double_segmented": sum(1 for o in outl if (o[0], "gloms", o[1]) in dup_gloms)}


def r4(objs, packages, seed=SEED, min_outliers=NN_MIN_OUTLIERS):
    by = {}
    for o in objs:
        by.setdefault(o[0], []).append(o)
    m = s = 0
    ratios = []
    for i in sorted(by):
        rows = packages[i][1]["tubs"]
        pts = [centre(rows[o[1]]) for o in by[i]]
        allp = [p for p in pts if p is not None]
        out = [p for o, p in zip(by[i], pts) if p is not None and o[3] >= Z_CUT]
        if len(out) < min_outliers or len(allp) < 2 * len(out):
            continue
        rng = random.Random(seed + i)
        if len(out) > NN_CAP:
            out = rng.sample(out, NN_CAP)
        d_o = mean_nn(out)
        d_r = sum(mean_nn(rng.sample(allp, len(out))) for _ in range(NN_DRAWS)) / NN_DRAWS
        m += 1
        s += d_o < d_r
        if d_r > 0:
            ratios.append(d_o / d_r)
    return {"slides": m, "clustered": s, "share": _share(s, m),
            "p_sign": binom_tail(m, s) if m else None, "nn_ratio_median": median(ratios)}


def candidates(objs, packages, comp, dup_gloms, n=CANDIDATES):
    """The n most extreme within-slide outliers that are neither misshapen nor double-segmented."""
    feats = [col for col, _ in SCREEN[comp]]
    keep = []
    for o in sorted(objs, key=lambda o: -o[3]):
        if o[3] < Z_CUT:
            break
        name, t = packages[o[0]]
        r = t[comp][o[1]]
        if comp != "tubs" and misshapen(r):
            continue
        if (o[0], comp, o[1]) in dup_gloms:
            continue
        keep.append({"package": name, "sheet": comp, "box": list(r[:4]),
                     "values": dict(zip(COLUMNS[comp][4:], r[4:])), "pooled_z": round(o[2], 2),
                     "slide_z": round(o[3], 2), "feature": feats[o[4]], "direction": "high" if o[5] > 0 else "low"})
        if len(keep) >= n:
            break
    return keep


# ---- grades ----

def grade(res, min_packages=MIN_PACKAGES):
    g = {}
    if res["read"]["v2"] < min_packages:
        g.update({k: "pending" for k in PREDICTIONS})
        g["status"] = "gate failed: v2 packages read %d < %d" % (res["read"]["v2"], min_packages)
        return g
    it = res["integrity"]

    def at_least(v, t):
        return "untestable" if v is None else ("pass" if v >= t else "fail")

    def below(v, t):
        return "untestable" if v is None else ("pass" if v < t else "fail")
    g["I1_box_valid"] = at_least(it["I1_box_valid"], 0.999)
    m = it["I2_glom_fill_median"]
    g["I2_glom_fill_median"] = "untestable" if m is None else ("pass" if 0.45 <= m <= 1.0 else "fail")
    g["I3_area_in_box"] = at_least(it["I3_area_in_box"], 0.99)
    g["I4_mesangial_consistent"] = at_least(it["I4_mesangial_consistent"], 0.99)
    g["I5_fractions_in_range"] = at_least(it["I5_fractions_in_range"], 0.999)
    g["I6_glom_double_segmentation"] = below(it["I6_glom_double_segmentation"], 0.01)
    g["I7_tubule_duplicates"] = below(it["I7_tubule_duplicates"], 0.001)
    ra = res["rarity"]
    a = ra["R1"]
    g["R1_tubule_pooled_outliers_slide_explained"] = (
        "untestable" if a["pooled_outliers"] < MIN_R1_OUTLIERS else at_least(a["share"], 0.5))
    b = ra["R2"]
    g["R2_tubule_outlier_overdispersion"] = (
        "untestable" if b["dispersion"] is None or b["outliers"] < MIN_R1_OUTLIERS
        else ("pass" if b["dispersion"] > 2 else "fail"))
    c = ra["R3"]
    g["R3_glom_outliers_misshapen"] = (
        "untestable" if c["outliers_misshapen"] + c["outliers_other"] < MIN_R3_OUTLIERS
        else ("pass" if c["odds_ratio"] >= 2 else "fail"))
    d = ra["R4"]
    g["R4_tubule_outliers_cluster"] = (
        "untestable" if d["slides"] < MIN_NN_SLIDES
        else ("pass" if d["share"] >= 0.6 and d["p_sign"] < 0.05 else "fail"))
    g["status"] = "complete"
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--min-packages", type=int, default=MIN_PACKAGES)
    ap.add_argument("--min-slide-objects", type=int, default=MIN_SLIDE_OBJECTS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": SEED,
           "predictions": PREDICTIONS,
           "settings": {"z_cut": Z_CUT, "min_packages": args.min_packages,
                        "min_slide_objects": args.min_slide_objects, "fill_max": FILL_MAX,
                        "fill_low": FILL_LOW, "aspect_high": ASPECT_HIGH, "iou_dup": IOU_DUP,
                        "mes_tol": MES_TOL, "nn_cap": NN_CAP, "nn_draws": NN_DRAWS}}
    dirs = package_dirs(os.path.join(args.data_dir, "kpmp-census"))
    packages, status, errors, seen = [], Counter(), [], Counter()
    for k, d in enumerate(dirs):
        try:
            st, tables = load_v2(d, seen)
        except Exception as e:
            st, tables = "error", None
            errors.append({"package": os.path.basename(d), "error": repr(e)[:300]})
        status[st] += 1
        if tables is not None:
            packages.append((os.path.basename(d), tables))
        if (k + 1) % 50 == 0:
            log(f"{k + 1}/{len(dirs)} read; v2 {len(packages)}")
    res["read"] = {"package_dirs": len(dirs), "v2": len(packages), "status": dict(status), "errors": errors,
                   "objects": {key: sum(len(t[key]) for _, t in packages) for key in SHEETS}}
    res["raw_names"] = [{"kind": kind, "names": names, "packages": n} for (kind, names), n in sorted(seen.items())]
    res["integrity"], dup_gloms = integrity(packages)
    log("integrity done")
    res["rarity"], objs = {}, {}
    for comp in SCREEN:
        res["rarity"][comp], objs[comp] = score_objects(packages, comp, args.min_slide_objects)
        log(f"rarity {comp}: {res['rarity'][comp].get('slide_outliers')} slide outliers")
    res["rarity"]["R1"] = r1(objs["tubs"])
    res["rarity"]["R1_descriptive"] = {c: r1(objs[c]) for c in ("gloms", "arts")}
    res["rarity"]["R2"] = r2(objs["tubs"])
    res["rarity"]["R2_descriptive"] = {c: r2(objs[c]) for c in ("gloms", "arts")}
    res["rarity"]["R3"] = r3(objs["gloms"], packages, dup_gloms)
    res["rarity"]["R4"] = r4(objs["tubs"], packages)
    res["grades"] = grade(res, args.min_packages)
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(args.out_dir, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "For expert review only; not for publication.",
                   "candidates": {c: candidates(objs[c], packages, c, dup_gloms) for c in SCREEN}}, f, indent=1)
    print(json.dumps({"read": {k: res["read"][k] for k in ("package_dirs", "v2", "status")},
                      "grades": res["grades"], "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
