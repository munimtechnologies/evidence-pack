#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_census2: second pass of the KPMP segmentation census.

Pre-registration: findings/kpmp-census-prereg-v2-2026-10-27.md.

Pass 1 (kidney.kpmp_census 1.0) read only the v2 workbook layout, found no pixel size in the
OME-XML and could not fetch the old TIV release. This pass reuses pass 1's cache and helpers and
  - reads the v1 workbooks (final_combined_features_<compartment>.xlsx, sheet "features"),
  - matches columns by exact name, so "Area (pixel^2)" never counts as "Area",
  - reads the scanner's MPP from the .svs ImageDescription of a seeded sample of packages,
  - takes the current TIV workbook from a fresh Repository file-list export.
Only aggregate measurements go to the output. No KPMP file is re-hosted.

Standard library only. Usage:
  python -m kidney.kpmp_census2 --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv --out-dir /out --data-dir /data
"""
import argparse
import csv
import json
import math
import os
import re
import shutil
import statistics
import struct
import sys
import tempfile
import time
import zipfile
from collections import Counter

from kidney import kpmp_census as kc

PREREG = "findings/kpmp-census-prereg-v2-2026-10-27.md"
CODE_VERSION = "2.0"
DESCRIPTOR_STRATEGY = "Pathology Descriptor Scoring"
V1_BOOK = re.compile(r"final_combined_features_(.+)\.xlsx$", re.I)
V1_SHEETS = {"tubules": "tubs", "non_globally_sclerotic_gloms": "gloms",
             "globally_sclerotic_gloms": "s_gloms", "muscular_vessels": "arts"}
# (sheet, exact column after col_key(), power of length); "Area (pixel^2)" is pixels in both versions.
COLUMNS = {"lumen": ("tubs", "luminal fraction", 0),
           "tbm": ("tubs", "average tbm thickness", 1),
           "cell": ("tubs", "average cell thickness", 1),
           "glom_area": ("gloms", "area", 2),
           "glom_area_px": ("gloms", "area (pixel^2)", None)}
PIXEL_AREA = "area (pixel^2)"
MPP_RE = re.compile(r"\bMPP\s*=\s*([0-9]*\.?[0-9]+)")
APPMAG_RE = re.compile(r"\bAppMag\s*=\s*([0-9]*\.?[0-9]+)")
SVS_PER_VERSION = 20
MIN_SVS = 10
MIN_MPP_V2 = 5
MAX_DESCRIPTION = 1_000_000


def col_key(name):
    """Trimmed, lower case, spaces collapsed; brackets kept: "Area (pixel^2)" -> "area (pixel^2)"."""
    return " ".join(str(name or "").lower().split())


def _cell(row, j):
    return kc.parse_float(row[j]) if j < len(row) else None


# ---- workbooks ----

def book_sheets(path, fn, version):
    """{sheet key: rows} for one workbook. v1 books hold one compartment in their "features" sheet."""
    book = kc.read_xlsx(path)
    if version == "v1":
        m = V1_BOOK.search(fn)
        if not m:
            return {"v1-book:" + fn.lower(): next(iter(book.values()), [])}
        comp = m.group(1).lower()
        return {V1_SHEETS.get(comp, "v1:" + comp): book.get("features") or []}
    return {kc.norm(name): rows for name, rows in book.items()}


def analyse_dir2(path, version):
    """Readme, OME and workbook facts plus raw feature values of one cached package."""
    out = {"readme": None, "ome": None, "xlsx": 0, "sheets": {}, "values": {}, "area_ratio": [], "errors": []}
    for fn in sorted(os.listdir(path)):
        full, ext = os.path.join(path, fn), kc.ext_of(fn)
        try:
            if ext == "md":
                with open(full, encoding="utf-8", errors="replace") as f:
                    out["readme"] = kc.readme_info(f.read())
            elif ext == "xml":
                with open(full, "rb") as f:
                    out["ome"] = kc.ome_info(f.read())
            elif ext == "xlsx":
                out["xlsx"] += 1
                for key, rows in book_sheets(full, fn, version).items():
                    header, data = kc.sheet_table(rows)
                    s = out["sheets"].setdefault(key, {"n_rows": 0, "header": header})
                    s["n_rows"] += len(data)
                    idx = {col_key(h): j for j, h in enumerate(header)}
                    for feat, (sheet, col, _) in COLUMNS.items():
                        if key == sheet and col in idx:
                            vals = (_cell(r, idx[col]) for r in data)
                            out["values"].setdefault(feat, []).extend(v for v in vals if v is not None)
                    if key == "gloms" and "area" in idx and PIXEL_AREA in idx:
                        for r in data:
                            a, p = _cell(r, idx["area"]), _cell(r, idx[PIXEL_AREA])
                            if a is not None and p:
                                out["area_ratio"].append(a / p)
        except Exception as e:
            out["errors"].append({"member": fn, "error": repr(e)[:300]})
    out["medians"] = {feat: kc._median(v) for feat, v in out["values"].items()}
    out["area_ratio_median"] = kc._median(out["area_ratio"])
    return out


# ---- scanner pixel size ----

def tiff_description(f):
    """ImageDescription (tag 270) of the first image directory of a TIFF or BigTIFF file object."""
    f.seek(0)
    head = f.read(16)
    if head[:2] == b"II":
        e = "<"
    elif head[:2] == b"MM":
        e = ">"
    else:
        return None
    magic = struct.unpack(e + "H", head[2:4])[0]
    if magic == 42:
        off, nfmt, efmt, size, inline = struct.unpack(e + "I", head[4:8])[0], "H", "HHII", 12, 4
    elif magic == 43:
        off, nfmt, efmt, size, inline = struct.unpack(e + "Q", head[8:16])[0], "Q", "HHQQ", 20, 8
    else:
        return None
    f.seek(off)
    nb = struct.calcsize(nfmt)
    n = struct.unpack(e + nfmt, f.read(nb))[0]
    raw = f.read(n * size)
    for i in range(n):
        entry = raw[i * size:(i + 1) * size]
        if len(entry) < size:
            break
        tag, typ, count, value = struct.unpack(e + efmt, entry)
        if tag != 270 or count > MAX_DESCRIPTION:
            continue
        if count <= inline:
            data = entry[size - inline:size - inline + count]
        else:
            f.seek(value)
            data = f.read(count)
        return data.split(b"\0")[0].decode("latin-1")
    return None


def svs_info(desc):
    """MPP and AppMag from an Aperio ImageDescription."""
    m, a = MPP_RE.search(desc or ""), APPMAG_RE.search(desc or "")
    return {"aperio": "aperio" in (desc or "").lower(),
            "mpp": kc.parse_float(m.group(1)) if m else None,
            "appmag": kc.parse_float(a.group(1)) if a else None}


def fetch_svs_mpp(p, tmp_dir, get=None, pause=None):
    """Download one package again, read its slide's MPP, delete the zip."""
    zpath = os.path.join(tmp_dir, "svs-package.zip")
    d = kc.download(kc.download_url(p["package"], p["name"]), zpath, get=get, pause=pause)
    rec = {"package": p["package"], "version": p["version"], "ok": d["ok"], "bytes": d["bytes"],
           "error": d.get("error"), "svs_members": 0, "aperio": False, "mpp": None, "appmag": None}
    if d["ok"]:
        try:
            with zipfile.ZipFile(zpath) as z:
                svs = [i for i in z.infolist() if kc.ext_of(i.filename) == "svs"]
                rec["svs_members"] = len(svs)
                if svs:
                    with z.open(max(svs, key=lambda i: i.file_size)) as f:
                        rec.update(svs_info(tiff_description(f)))
        except Exception as e:
            rec["error"] = repr(e)[:300]
        finally:
            if os.path.exists(zpath):
                os.remove(zpath)
    return rec


def svs_sample(order, per_version=SVS_PER_VERSION):
    """The first per_version v1 and v2 packages in the census order."""
    out, seen = [], Counter()
    for p in order:
        if seen[p["version"]] < per_version:
            seen[p["version"]] += 1
            out.append(p)
    return out


def mpp_summary(svs_recs):
    ok = [r for r in svs_recs if r["ok"]]
    out = {"sampled": len(svs_recs), "downloaded": len(ok), "with_mpp": 0,
           "appmag": [{"appmag": k, "packages": n} for k, n in sorted(Counter(r["appmag"] for r in ok).items(),
                                                                       key=lambda kv: str(kv[0]))]}
    for v in ("all", "v1", "v2"):
        m = [r["mpp"] for r in ok if r["mpp"] and (v == "all" or r["version"] == v)]
        out[v] = {"packages": len(m), "min": min(m) if m else None, "median": kc._median(m),
                  "max": max(m) if m else None,
                  "distinct": [{"mpp": k, "packages": n} for k, n in sorted(Counter(m).items())]}
    out["with_mpp"] = out["all"]["packages"]
    return out


# ---- census summaries ----

def version_ratio2(records, feat_v2, feat_v1, power, mpp):
    """Median of v2 package medians over the v1 one, raw and with v2 times mpp ** power."""
    meds = {"v1": [], "v2": []}
    for r in records:
        a = r.get("analysis") or {}
        feat = feat_v2 if r["version"] == "v2" else feat_v1
        m = (a.get("medians") or {}).get(feat)
        if m is not None:
            meds[r["version"]].append(m)
    v1, v2 = kc._median(meds["v1"]), kc._median(meds["v2"])
    out = {"v1": {"feature": feat_v1, "packages": len(meds["v1"]), "median": v1},
           "v2": {"feature": feat_v2, "packages": len(meds["v2"]), "median": v2}}
    ok = (len(meds["v1"]) >= kc.MIN_PACKAGES_PER_VERSION and len(meds["v2"]) >= kc.MIN_PACKAGES_PER_VERSION
          and v1 and v2 is not None)
    out["raw_ratio"] = v2 / v1 if ok else None
    out["converted_ratio"] = (v2 * mpp ** power / v1) if ok and mpp and power is not None else None
    return out


def area_ratio_summary(records):
    meds = [r["analysis"]["area_ratio_median"] for r in records
            if r["version"] == "v1" and (r.get("analysis") or {}).get("area_ratio_median") is not None]
    m = kc._median(meds)
    return {"packages": len(meds), "median": m, "min": min(meds) if meds else None,
            "max": max(meds) if meds else None, "implied_mpp": math.sqrt(m) if m and m > 0 else None}


def participant_table2(records, mpp):
    """Like kc.participant_table, with v2 values converted by one mpp (the scanner's, not the OME's)."""
    out = {}
    for r in records:
        a = r.get("analysis")
        if not a or len(r["participants"]) != 1:
            continue
        p = out.setdefault(r["participants"][0], {"versions": set(), "n_tubs": 0, "raw": {}, "conv": {}})
        p["versions"].add(r["version"])
        p["n_tubs"] += (a["sheets"].get("tubs") or {}).get("n_rows", 0)
        for feat in ("lumen", "tbm", "cell", "glom_area"):
            power = COLUMNS[feat][2]
            raw = a["values"].get(feat, [])
            p["raw"].setdefault(feat, []).extend(raw)
            conv = p["conv"].setdefault(feat, [])
            if r["version"] == "v1" or power == 0:
                conv.extend(raw)
            elif mpp:
                conv.extend(v * mpp ** power for v in raw)
    return out


def describe2(records):
    """Headers, row counts and IFTA-named channels by version and sheet."""
    sheets, ifta = {}, Counter()
    for r in records:
        a = r.get("analysis")
        if not a:
            continue
        v = r["version"]
        for name, s in a["sheets"].items():
            d = sheets.setdefault(v, {}).setdefault(name, {"present": 0, "empty": 0, "rows": 0, "headers": Counter()})
            d["present"] += 1
            d["empty"] += s["n_rows"] == 0
            d["rows"] += s["n_rows"]
            d["headers"]["|".join(s["header"])] += 1
        chans = (a.get("ome") or {}).get("channels", [])
        ifta[(v, any(kc.IFTA_RE.search(c or "") for c in chans))] += 1
    for v in sheets:
        for d in sheets[v].values():
            d["headers"] = [{"header": h, "packages": n} for h, n in d["headers"].most_common()]
    return {"sheets": sheets,
            "ifta_channel_by_version": [{"version": k[0], "ifta_channel": k[1], "packages": n}
                                        for k, n in sorted(ifta.items())]}


# ---- TIV workbook ----

def load_descriptor(path):
    """Open xlsx rows of the Pathology Descriptor Scoring file list."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Experimental Strategy") or "").strip() != DESCRIPTOR_STRATEGY:
                continue
            if (row.get("Access") or "").strip().lower() != "open":
                continue
            name = (row.get("File Name") or "").strip()
            if not name.lower().endswith(".xlsx"):
                continue
            out.append({"package": (row.get("Internal Package ID") or "").strip(), "name": name,
                        "listed": (row.get("Size") or "").strip()})
    return out


def tiv_sheet(sheets):
    """The sheet holding the scores: "Data Table", else the first with a "Participant ID" row."""
    if "Data Table" in sheets:
        return "Data Table"
    for name, rows in sheets.items():
        if any(r and str(r[0] or "").strip() == "Participant ID" for r in rows):
            return name
    return None


def tiv_scores(sheets):
    """(scores, info). The header is reported only when it is the "Participant ID" row (names only)."""
    name = tiv_sheet(sheets)
    info = {"sheet_names": sorted(sheets), "sheet": name}
    if name is None:
        info["error"] = "no sheet with a 'Participant ID' row"
        return {}, info
    rows = sheets[name]
    head = next((r for r in rows if r and str(r[0] or "").strip() == "Participant ID"), None)
    if head:
        info["header"] = [str(x).strip() for x in head if x not in (None, "")]
    scores, t = kc.tiv_table(sheets, name)
    info.update(t)
    return scores, info


# ---- grades ----

def _within(v, lo=None, hi=None):
    return kc._within(v, lo, hi)


def grade2(res):
    c, g = res["census"], {}
    keys = ("S1_svs_mpp", "U1_v1_area_microns", "U2_pixel_scale", "U3_mpp_agree", "P2_tbm_raw_ratio",
            "P3_tbm_converted_ratio", "P4_glom_area_raw_ratio", "P5_glom_area_converted_ratio",
            "P7_lumen_vs_abnormal_lumen", "P8_tbm_vs_atrophy", "P9_cell_vs_injury_other")
    if not c["listed"] or c["analysed"] < kc.GRADE_MIN_SHARE * c["listed"]:
        g.update({k: "pending" for k in keys})
        g["status"] = "incomplete"
        return g
    m = res["mpp"]
    if m["with_mpp"] < MIN_SVS or not m["downloaded"]:
        g["S1_svs_mpp"] = "untestable"
    else:
        a = m["all"]
        g["S1_svs_mpp"] = "pass" if (m["with_mpp"] >= 0.9 * m["downloaded"] and 0.24 <= a["median"] <= 0.26
                                     and a["max"] / a["min"] <= 1.10) else "fail"
    ar = res["area_ratio"]
    g["U1_v1_area_microns"] = (_within(ar["median"], 0.04, 0.10)
                               if ar["packages"] >= kc.MIN_PACKAGES_PER_VERSION else "untestable")
    g["U2_pixel_scale"] = _within(res["unit_checks"]["pixel_scale"]["raw_ratio"], 0.5, 2.0)
    v1_mpp = m["v1"]["median"]
    if ar["packages"] < kc.MIN_PACKAGES_PER_VERSION or not ar["implied_mpp"] or not v1_mpp:
        g["U3_mpp_agree"] = "untestable"
    else:
        g["U3_mpp_agree"] = "pass" if abs(ar["implied_mpp"] / v1_mpp - 1) <= 0.10 else "fail"
    u = res["unit_checks"]
    g["P2_tbm_raw_ratio"] = _within(u["tbm"]["raw_ratio"], 2.0)
    g["P3_tbm_converted_ratio"] = _within(u["tbm"]["converted_ratio"], 0.67, 1.5)
    g["P4_glom_area_raw_ratio"] = _within(u["glom_area"]["raw_ratio"], 4.0)
    g["P5_glom_area_converted_ratio"] = _within(u["glom_area"]["converted_ratio"], 0.5, 2.0)
    for key, _, _, direction in kc.TESTS:
        if not key.startswith("P"):
            continue
        a = res["agreement"][key]["conv"]
        if a["n"] < kc.MIN_AGREEMENT_N or a["rho"] is None or a.get("p_one_sided") is None:
            g[key] = "untestable"
        else:
            g[key] = "pass" if direction * a["rho"] > 0 and a["p_one_sided"] < 0.05 else "fail"
    g["status"] = "complete"
    return g


def package_row2(p, rec):
    """Per package: no participant ID, no feature values (package medians only)."""
    a = rec.get("analysis") or {}
    return {"package": p["package"], "version": p["version"], "slide": p["slide"], "ok": rec.get("ok", False),
            "cached": rec.get("cached"), "download": rec.get("download") if not rec.get("cached") else None,
            "sheets": {k: s["n_rows"] for k, s in (a.get("sheets") or {}).items()},
            "medians": a.get("medians"), "area_ratio_median": a.get("area_ratio_median"),
            "errors": a.get("errors", []) + ([rec["error"]] if rec.get("error") else [])}


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--svs-per-version", type=int, default=SVS_PER_VERSION)
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kpmp-census2-")
    order = kc.census_order(kc.load_packages(args.file_list))
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "census_code_version": kc.CODE_VERSION,
           "python": sys.version.split()[0], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "seed": kc.SEED}
    records = []
    with open(os.path.join(args.out_dir, "progress.jsonl"), "a", encoding="utf-8") as prog:
        for i, p in enumerate(order):
            try:
                rec = kc.fetch_package(p, cache, tmp, get=get, pause=pause)
            except Exception as e:
                rec = {"ok": False, "error": repr(e)[:300]}
            if rec.get("ok"):
                rec["analysis"] = analyse_dir2(os.path.join(cache, p["package"]), p["version"])
            records.append(dict(p, **rec))
            prog.write(json.dumps({"i": i, "package": p["package"], "ok": rec.get("ok", False),
                                   "cached": rec.get("cached")}) + "\n")
            prog.flush()
            if not rec.get("cached"):
                kc.log(f"{i + 1}/{len(order)} {p['package']} ok={rec.get('ok')}")
        res["census"] = {"listed": len(order),
                         "analysed": sum(1 for r in records if r.get("analysis")),
                         "cached": sum(1 for r in records if r.get("cached")),
                         "downloaded_this_run": sum(1 for r in records if r.get("ok") and not r.get("cached"))}
        svs_recs = []
        for p in svs_sample(order, args.svs_per_version):
            try:
                s = fetch_svs_mpp(p, tmp, get=get, pause=pause)
            except Exception as e:
                s = {"package": p["package"], "version": p["version"], "ok": False, "bytes": 0,
                     "error": repr(e)[:300], "svs_members": 0, "aperio": False, "mpp": None, "appmag": None}
            svs_recs.append(s)
            prog.write(json.dumps({"svs": p["package"], "ok": s["ok"], "mpp": s["mpp"]}) + "\n")
            prog.flush()
            kc.log(f"svs {len(svs_recs)} {p['package']} {p['version']} mpp={s['mpp']}")
    res["mpp"] = mpp_summary(svs_recs)
    res["svs"] = svs_recs
    mpp_hat = res["mpp"]["v2"]["median"] if res["mpp"]["v2"]["packages"] >= MIN_MPP_V2 else None
    res["mpp_hat"] = mpp_hat
    res["area_ratio"] = area_ratio_summary(records)
    res["unit_checks"] = {
        "tbm": version_ratio2(records, "tbm", "tbm", 1, mpp_hat),
        "cell": version_ratio2(records, "cell", "cell", 1, mpp_hat),
        "glom_area": version_ratio2(records, "glom_area", "glom_area", 2, mpp_hat),
        "lumen": version_ratio2(records, "lumen", "lumen", 0, mpp_hat),
        "pixel_scale": version_ratio2(records, "glom_area", "glom_area_px", None, None)}
    res["describe"] = describe2(records)
    scores = {}
    desc_rows = load_descriptor(args.descriptor_list)
    res["tiv_file"] = {"rows": len(desc_rows), "name": desc_rows[0]["name"] if len(desc_rows) == 1 else None,
                       "listed": desc_rows[0]["listed"] if len(desc_rows) == 1 else None}
    if len(desc_rows) == 1:
        t = desc_rows[0]
        tiv_path = os.path.join(cache, "tiv", t["package"] + ".xlsx")
        os.makedirs(os.path.dirname(tiv_path), exist_ok=True)
        if not os.path.exists(tiv_path):
            res["tiv_download"] = kc.download(kc.download_url(t["package"], t["name"]), tiv_path, get=get,
                                              pause=pause)
        if os.path.exists(tiv_path):
            try:
                scores, res["tiv"] = tiv_scores(kc.read_xlsx(tiv_path))
            except Exception as e:
                res["tiv"] = {"error": repr(e)[:300]}
    shutil.rmtree(tmp, ignore_errors=True)
    ptable = participant_table2(records, mpp_hat)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "both_versions": sum(1 for p in ptable.values() if len(p["versions"]) > 1),
                           "under_min_structures": sum(1 for p in ptable.values() if p["n_tubs"] < kc.MIN_STRUCTURES)}
    res["agreement"] = {}
    for k, (key, feature, score, direction) in enumerate(kc.TESTS):
        res["agreement"][key] = {
            "feature": feature, "score": score, "direction": direction,
            "conv": kc.agreement(ptable, scores, feature, score, direction, "conv", None, args.permutations,
                                 kc.SEED + k),
            "raw": kc.agreement(ptable, scores, feature, score, direction, "raw", None, args.permutations,
                                kc.SEED + k),
            "v1_only": kc.agreement(ptable, scores, feature, score, direction, "conv", {"v1"}, 0),
            "v2_only": kc.agreement(ptable, scores, feature, score, direction, "conv", {"v2"}, 0)}
    res["packages"] = [package_row2(p, r) for p, r in zip(order, records)]
    res["grades"] = grade2(res)
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"census": res["census"], "mpp": {k: res["mpp"][k] for k in ("sampled", "with_mpp")},
                      "grades": res["grades"], "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
