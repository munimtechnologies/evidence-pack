#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_census3: pass 2 of the KPMP segmentation census again, with its v1 reader fixed.

Pre-registration: findings/kpmp-census-prereg-v3-2026-10-27.md.

Pass 2 (kidney.kpmp_census2 2.0) asked each v1 workbook for a sheet named exactly "features". Pass 1
had only ever seen that name after norm() lower-cased it, and pass 2 read 0 rows from all 138 v1
packages. This pass
  - takes the v1 sheet whose name norm()s to "features", and reports every raw sheet name it saw,
  - re-runs pass 2's procedure unchanged otherwise (same cache, svs sample, score release, rules),
  - adds the pre-registered v1-only agreement tests (V7-V9) and the tail-feature tests (T7-T9).
Pass 2's grades for P7-P9 stand as graded; the pooled P7-P9 here are reported, not graded.
Only aggregate measurements go to the output. No KPMP file is re-hosted.

Standard library only. Usage:
  python -m kidney.kpmp_census3 --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv --out-dir /out --data-dir /data
"""
import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2

PREREG = "findings/kpmp-census-prereg-v3-2026-10-27.md"
CODE_VERSION = "3.0"
V1_SHEET = "features"
FROM_PASS2 = ("S1_svs_mpp", "U1_v1_area_microns", "U2_pixel_scale", "U3_mpp_agree", "P2_tbm_raw_ratio",
              "P3_tbm_converted_ratio", "P4_glom_area_raw_ratio", "P5_glom_area_converted_ratio")
# Pass 2's P7-P9 rules on participants with v1 packages only (none of them was read in pass 2).
V_TESTS = (("V7_lumen_vs_abnormal_lumen_v1", "lumen", kc.LUMEN_SCORE, 1),
           ("V8_tbm_vs_atrophy_v1", "tbm", kc.ATROPHY_SCORE, 1),
           ("V9_cell_vs_injury_other_v1", "cell", kc.INJURY_SCORE, -1))
# (key, feature, score, direction, quantile): a participant's tail instead of its median; graded on v2.
TAIL_TESTS = (("T7_lumen_p90_vs_abnormal_lumen", "lumen", kc.LUMEN_SCORE, 1, 0.9),
              ("T8_tbm_p90_vs_atrophy", "tbm", kc.ATROPHY_SCORE, 1, 0.9),
              ("T9_cell_p10_vs_injury_other", "cell", kc.INJURY_SCORE, -1, 0.1))


# ---- workbooks ----

def book_sheets3(path, fn, version, seen=None):
    """{sheet key: rows} for one workbook, like k2.book_sheets but with the v1 sheet matched by norm().
    seen (a Counter) gets (version, raw sheet names) and, for v1 books, the raw name that matched."""
    book = kc.read_xlsx(path)
    if seen is not None:
        seen[(version, "names", "|".join(sorted(book)))] += 1
    if version != "v1":
        return {kc.norm(name): rows for name, rows in book.items()}
    m = k2.V1_BOOK.search(fn)
    if not m:
        return {"v1-book:" + fn.lower(): next(iter(book.values()), [])}
    names = [name for name in book if kc.norm(name) == V1_SHEET]
    if seen is not None:
        seen[(version, "matched", names[0] if names else "")] += 1
    comp = m.group(1).lower()
    return {k2.V1_SHEETS.get(comp, "v1:" + comp): book[names[0]] if names else []}


def analyse_dir3(path, version, seen=None):
    """k2.analyse_dir2 with book_sheets3."""
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
                for key, rows in book_sheets3(full, fn, version, seen).items():
                    header, data = kc.sheet_table(rows)
                    s = out["sheets"].setdefault(key, {"n_rows": 0, "header": header})
                    s["n_rows"] += len(data)
                    idx = {k2.col_key(h): j for j, h in enumerate(header)}
                    for feat, (sheet, col, _) in k2.COLUMNS.items():
                        if key == sheet and col in idx:
                            vals = (k2._cell(r, idx[col]) for r in data)
                            out["values"].setdefault(feat, []).extend(v for v in vals if v is not None)
                    if key == "gloms" and "area" in idx and k2.PIXEL_AREA in idx:
                        for r in data:
                            a, p = k2._cell(r, idx["area"]), k2._cell(r, idx[k2.PIXEL_AREA])
                            if a is not None and p:
                                out["area_ratio"].append(a / p)
        except Exception as e:
            out["errors"].append({"member": fn, "error": repr(e)[:300]})
    out["medians"] = {feat: kc._median(v) for feat, v in out["values"].items()}
    out["area_ratio_median"] = kc._median(out["area_ratio"])
    return out


def sheet_names_report(seen):
    return [{"version": v, "kind": kind, "names": names, "books": n}
            for (v, kind, names), n in sorted(seen.items())]


# ---- tail agreement ----

def quantile(v, q):
    """Linear-interpolation quantile (the usual "type 7"); None for an empty list."""
    if not v:
        return None
    s = sorted(v)
    h = (len(s) - 1) * q
    lo = int(math.floor(h))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (h - lo)


def agreement_q(ptable, scores, feature, score, direction, q, versions=None, n_perm=kc.PERMUTATIONS,
                seed=kc.SEED, mode="raw"):
    """kc.agreement with a participant's q-quantile in place of its median. Raw values: within one
    version a pixel-to-micron factor does not change ranks."""
    xs, ys = [], []
    for pid in sorted(ptable):
        p = ptable[pid]
        if pid not in scores or scores[pid].get(score) is None or p["n_tubs"] < kc.MIN_STRUCTURES:
            continue
        if versions is not None and p["versions"] != versions:
            continue
        m = quantile(p[mode].get(feature, []), q)
        if m is None:
            continue
        xs.append(m)
        ys.append(scores[pid][score])
    out = {"n": len(xs), "rho": kc.spearman(xs, ys) if len(xs) >= 3 else None}
    if n_perm and out["rho"] is not None:
        out["p_one_sided"] = kc.perm_p(xs, ys, direction, n_perm, seed)
    return out


# ---- grades ----

def _agree_grade(a, direction):
    if a["n"] < kc.MIN_AGREEMENT_N or a["rho"] is None or a.get("p_one_sided") is None:
        return "untestable"
    return "pass" if direction * a["rho"] > 0 and a["p_one_sided"] < 0.05 else "fail"


def grade3(res):
    g2 = k2.grade2(res)
    g = {k: g2[k] for k in FROM_PASS2}
    keys = [t[0] for t in V_TESTS] + [t[0] for t in TAIL_TESTS]
    if g2["status"] != "complete":
        g.update({k: "pending" for k in keys})
        g["status"] = g2["status"]
        return g
    for key, _, _, direction in V_TESTS:
        g[key] = _agree_grade(res["agreement"][key]["v1_only"], direction)
    for key, _, _, direction, _ in TAIL_TESTS:
        g[key] = _agree_grade(res["agreement"][key]["v2_only"], direction)
    g["status"] = "complete"
    return g


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--svs-per-version", type=int, default=k2.SVS_PER_VERSION)
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kpmp-census3-")
    order = kc.census_order(kc.load_packages(args.file_list))
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "census2_code_version": k2.CODE_VERSION,
           "census_code_version": kc.CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": kc.SEED}
    records, seen = [], Counter()
    with open(os.path.join(args.out_dir, "progress.jsonl"), "a", encoding="utf-8") as prog:
        for i, p in enumerate(order):
            try:
                rec = kc.fetch_package(p, cache, tmp, get=get, pause=pause)
            except Exception as e:
                rec = {"ok": False, "error": repr(e)[:300]}
            if rec.get("ok"):
                rec["analysis"] = analyse_dir3(os.path.join(cache, p["package"]), p["version"], seen)
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
        for p in k2.svs_sample(order, args.svs_per_version):
            try:
                s = k2.fetch_svs_mpp(p, tmp, get=get, pause=pause)
            except Exception as e:
                s = {"package": p["package"], "version": p["version"], "ok": False, "bytes": 0,
                     "error": repr(e)[:300], "svs_members": 0, "aperio": False, "mpp": None, "appmag": None}
            svs_recs.append(s)
            prog.write(json.dumps({"svs": p["package"], "ok": s["ok"], "mpp": s["mpp"]}) + "\n")
            prog.flush()
            kc.log(f"svs {len(svs_recs)} {p['package']} {p['version']} mpp={s['mpp']}")
    res["sheet_names"] = sheet_names_report(seen)
    res["mpp"] = k2.mpp_summary(svs_recs)
    res["svs"] = svs_recs
    mpp_hat = res["mpp"]["v2"]["median"] if res["mpp"]["v2"]["packages"] >= k2.MIN_MPP_V2 else None
    res["mpp_hat"] = mpp_hat
    res["area_ratio"] = k2.area_ratio_summary(records)
    res["unit_checks"] = {
        "tbm": k2.version_ratio2(records, "tbm", "tbm", 1, mpp_hat),
        "cell": k2.version_ratio2(records, "cell", "cell", 1, mpp_hat),
        "glom_area": k2.version_ratio2(records, "glom_area", "glom_area", 2, mpp_hat),
        "lumen": k2.version_ratio2(records, "lumen", "lumen", 0, mpp_hat),
        "pixel_scale": k2.version_ratio2(records, "glom_area", "glom_area_px", None, None)}
    res["describe"] = k2.describe2(records)
    scores = {}
    desc_rows = k2.load_descriptor(args.descriptor_list)
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
                scores, res["tiv"] = k2.tiv_scores(kc.read_xlsx(tiv_path))
            except Exception as e:
                res["tiv"] = {"error": repr(e)[:300]}
    shutil.rmtree(tmp, ignore_errors=True)
    ptable = k2.participant_table2(records, mpp_hat)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "both_versions": sum(1 for p in ptable.values() if len(p["versions"]) > 1),
                           "under_min_structures": sum(1 for p in ptable.values() if p["n_tubs"] < kc.MIN_STRUCTURES),
                           "by_version": {v: sum(1 for p in ptable.values() if p["versions"] == {v})
                                          for v in ("v1", "v2")}}
    res["agreement"] = {}
    for k, (key, feature, score, direction) in enumerate(kc.TESTS):
        res["agreement"][key] = {
            "feature": feature, "score": score, "direction": direction, "graded": False,
            "conv": kc.agreement(ptable, scores, feature, score, direction, "conv", None, args.permutations,
                                 kc.SEED + k),
            "raw": kc.agreement(ptable, scores, feature, score, direction, "raw", None, args.permutations,
                                kc.SEED + k),
            "v1_only": kc.agreement(ptable, scores, feature, score, direction, "conv", {"v1"}, 0),
            "v2_only": kc.agreement(ptable, scores, feature, score, direction, "conv", {"v2"}, 0)}
    for k, (key, feature, score, direction) in enumerate(V_TESTS):
        res["agreement"][key] = {
            "feature": feature, "score": score, "direction": direction, "graded_on": "v1_only",
            "v1_only": kc.agreement(ptable, scores, feature, score, direction, "conv", {"v1"}, args.permutations,
                                    kc.SEED + 10 + k)}
    for k, (key, feature, score, direction, q) in enumerate(TAIL_TESTS):
        res["agreement"][key] = {
            "feature": feature, "score": score, "direction": direction, "quantile": q, "graded_on": "v2_only",
            "v2_only": agreement_q(ptable, scores, feature, score, direction, q, {"v2"}, args.permutations,
                                   kc.SEED + 20 + k),
            "v1_only": agreement_q(ptable, scores, feature, score, direction, q, {"v1"}, args.permutations,
                                   kc.SEED + 30 + k)}
    res["packages"] = [k2.package_row2(p, r) for p, r in zip(order, records)]
    res["grades"] = grade3(res)
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"census": res["census"], "mpp": {k: res["mpp"][k] for k in ("sampled", "with_mpp")},
                      "sheet_names": res["sheet_names"], "grades": res["grades"], "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
