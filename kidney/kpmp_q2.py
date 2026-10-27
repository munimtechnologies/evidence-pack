#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_q2: do KPMP's released pathomics features recover known clinical gradients?

Plan (features, concepts, directions): findings/kpmp-q2-plan-v1-2026-10-26.md.
Pre-registration (columns, codings, floors, rules): findings/kpmp-q2-prereg-v1-2026-10-27.md.

Reads the segmentation packages cached by the census (kidney.kpmp_census*), with census 3's v1 reader,
and KPMP's open clinical file, named by a Repository file-list export. Takes the pixel size and
the unit checks from census 3's results.json. Writes aggregate statistics only: no participant ID, no
participant-level value, no KPMP file.

Standard library only. Usage (after kidney.kpmp_census3 has written /out/results.json):
  python -m kidney.kpmp_q2 --file-list inputs/kpmp-segmentation-files.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --census-results /out/results.json \
      --out-dir /out/q2 --data-dir /data
"""
import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_census3 as k3

PREREG = "findings/kpmp-q2-prereg-v1-2026-10-27.md"
CODE_VERSION = "1.0"
SEED = 20261027
ALPHA = 0.05
MIN_TOTAL = 30
MIN_ARM = 30
MIN_STRATUM = 10
HALF_MIN_TOTAL = 20
HALF_MIN_ARM = 10
MIN_ALL_GLOMS = 5
# feature: (sheet, exact column after k2.col_key(), power of length, census check that must pass before
# v1 values are pooled as microns with v2 values times the scanner pixel size)
FEATURES = {"glom_area": ("gloms", "area", 2, "P5_glom_area_converted_ratio"),
            "mesangial_fraction": ("gloms", "mesangial fraction", 0, None),
            "tbm": ("tubs", "average tbm thickness", 1, "P3_tbm_converted_ratio"),
            "cell": ("tubs", "average cell thickness", 1, "P3_tbm_converted_ratio"),
            "lumen": ("tubs", "luminal fraction", 0, None),
            "arterial_area": ("arts", "arterial area", 2, "P5_glom_area_converted_ratio")}
# feature: (structure count, floor per participant)
FLOORS = {"glom_area": ("gloms", 5), "mesangial_fraction": ("gloms", 5), "tbm": ("tubs", 20),
          "cell": ("tubs", 20), "lumen": ("tubs", 20), "arterial_area": ("arts", 3)}
CLINICAL = {
    "diabetes": ("Diabetes History", "binary", {"Yes": 1, "No": 0}),
    "hypertension": ("Hypertension History", "binary", {"Yes": 1, "No": 0}),
    "raas": ("On RAAS Blockade", "binary", {"Yes": 1, "No": 0}),
    "sex_male": ("Sex", "binary", {"Male": 1, "Female": 0}),
    "age_bin": ("Age (Years) (Binned)", "ordinal", None),
    "egfr": ("Baseline eGFR (ml/min/1.73m2)", "numeric", None),
    "proteinuria": ("Proteinuria (mg) (Binned)", "ordinal",
                    {"<150 mg/g cr": 1, "150 to <500 mg/g cr": 2, "500 to <1000 mg/g cr": 3, ">=1000 mg/g cr": 4}),
    "albuminuria": ("Albuminuria (mg) (Binned)", "ordinal",
                    {"<30 mg/g cr": 1, "30 to <300 mg/g cr": 2, "300 to <500 mg/g cr": 3,
                     "500 to <1000 mg/g cr": 4, ">=1000 mg/g cr": 5}),
    "a1c": ("A1c (%) (Binned)", "ordinal", {"<6.5%": 1, "6.5 to <7.5%": 2, "7.5 to <8.5%": 3, ">=8.5%": 4}),
}
AGE_RE = re.compile(r"^(\d+)-(\d+) Years$")
AGE_STRATA = (("under 50", 0, 49), ("50-59", 50, 59), ("60-69", 60, 69), ("70 and over", 70, 999))
CONTROLS = (("C1_glom_area_vs_diabetes", "glom_area", "diabetes", 1),
            ("C2_mesangial_fraction_vs_diabetes", "mesangial_fraction", "diabetes", 1),
            ("C3_sclerotic_share_vs_egfr", "sclerotic_share", "egfr", -1),
            ("C4_tbm_vs_egfr", "tbm", "egfr", -1),
            ("C5_glom_area_vs_proteinuria", "glom_area", "proteinuria", 1))
DISC_FEATURES = ("glom_area", "mesangial_fraction", "sclerotic_share", "tbm", "cell", "lumen", "arterial_area")
DISC_CLINICAL = ("diabetes", "hypertension", "raas", "sex_male", "age_bin", "egfr", "proteinuria", "albuminuria",
                 "a1c")


# ---- clinical file ----

def code_value(var, text):
    """A clinical cell coded as fixed in the pre-registration; None if empty or not codable."""
    _, kind, levels = CLINICAL[var]
    t = (text or "").strip()
    if not t:
        return None
    if kind == "numeric":
        return kc.parse_float(t)
    if var == "age_bin":
        m = AGE_RE.match(t)
        return int(m.group(1)) if m else None
    return levels.get(t)


def load_clinical_list(path):
    """Open .csv rows of the Repository's Clinical Study Data file-list export."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Access") or "").strip().lower() != "open":
                continue
            name = (row.get("File Name") or "").strip()
            if name.lower().endswith(".csv"):
                out.append({"package": (row.get("Internal Package ID") or "").strip(), "name": name,
                            "listed": (row.get("Size") or "").strip()})
    return out


def clinical_table(path):
    """({participant: {variable: code}}, info). info holds counts only."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip() for h in (reader.fieldnames or [])]
        rows = list(reader)
    info = {"rows": len(rows), "missing_columns": [c[0] for c in CLINICAL.values() if c[0] not in header]}
    out = {}
    for r in rows:
        r = {(k or "").strip(): v for k, v in r.items()}
        pid = (r.get("Participant ID") or "").strip()
        if pid:
            out[pid] = {v: code_value(v, r.get(CLINICAL[v][0])) for v in CLINICAL}
    info["participants"] = len(out)
    info["coded"] = {v: sum(1 for c in out.values() if c[v] is not None) for v in CLINICAL}
    return out, info


# ---- features ----

def extract_package(path, version):
    """Per-structure feature values, structure counts and sheet keys of one cached package."""
    out = {"values": {}, "n": Counter(), "books": set(), "errors": []}
    for fn in sorted(os.listdir(path)):
        if kc.ext_of(fn) != "xlsx":
            continue
        try:
            for key, rows in k3.book_sheets3(os.path.join(path, fn), fn, version).items():
                out["books"].add(key)
                header, data = kc.sheet_table(rows)
                out["n"][key] += len(data)
                idx = {k2.col_key(h): j for j, h in enumerate(header)}
                for feat, (sheet, col, _, _) in FEATURES.items():
                    if key == sheet and col in idx:
                        vals = (k2._cell(r, idx[col]) for r in data)
                        out["values"].setdefault(feat, []).extend(v for v in vals if v is not None)
        except Exception as e:
            out["errors"].append({"member": fn, "error": repr(e)[:300]})
    return out


def participant_table(packages, mpp):
    """{participant: versions, structure counts, raw and converted values, sclerotic counts}.
    packages: [(participant, version, extract_package output)]. Converted = v1 as given (microns per
    the README), v2 times mpp to the feature's power. A package counts towards the sclerotic share
    only if it has a non-sclerotic glomerulus sheet; a v1 package without a sclerotic workbook then
    counts as 0 sclerotic glomeruli, and its participant is flagged for the sensitivity analysis."""
    out = {}
    for pid, version, ex in packages:
        p = out.setdefault(pid, {"versions": set(), "n": Counter(), "raw": {}, "conv": {}, "scl": [0, 0],
                                 "scl_ok": True})
        p["versions"].add(version)
        for k, n in ex["n"].items():
            p["n"][k] += n
        for feat, (_, _, power, _) in FEATURES.items():
            raw = ex["values"].get(feat, [])
            p["raw"].setdefault(feat, []).extend(raw)
            conv = p["conv"].setdefault(feat, [])
            if version == "v1" or power == 0:
                conv.extend(raw)
            elif mpp:
                conv.extend(v * mpp ** power for v in raw)
        if "gloms" in ex["books"]:
            p["scl"][0] += ex["n"].get("gloms", 0)
            p["scl"][1] += ex["n"].get("s_gloms", 0)
            if version == "v1" and "s_gloms" not in ex["books"]:
                p["scl_ok"] = False
    return out


def feature_value(p, feat, mode="conv"):
    """A participant's feature: the median over its structures, or the sclerotic share; None below floor."""
    if feat == "sclerotic_share":
        g, s = p["scl"]
        return s / (g + s) if g + s >= MIN_ALL_GLOMS else None
    sheet, floor = FLOORS[feat]
    if p["n"].get(sheet, 0) < floor:
        return None
    return kc._median(p[mode].get(feat, []))


def rows_for(ptable, clin, feat, var, mode="conv", pids=None, require_scl_ok=False):
    """[(version stratum, feature, clinical code, age bin)] in participant-ID order."""
    out = []
    for pid in sorted(ptable):
        if pids is not None and pid not in pids:
            continue
        p = ptable[pid]
        if require_scl_ok and not p["scl_ok"]:
            continue
        c = clin.get(pid) or {}
        y = c.get(var)
        x = feature_value(p, feat, mode) if y is not None else None
        if x is None:
            continue
        out.append(("+".join(sorted(p["versions"])), x, y, c.get("age_bin")))
    return out


# ---- statistics ----

def _combined(pairs):
    """n-weighted mean of the Pearson correlations of rank pairs; strata with no variation are skipped."""
    num = den = 0.0
    for rx, ry in pairs:
        r = kc.pearson(rx, ry)
        if r is not None:
            num += len(rx) * r
            den += len(rx)
    return num / den if den else None


def stat_test(rows, direction, n_perm, seed, stratified, two_sided=False, min_stratum=MIN_STRATUM):
    """Spearman rho, pooled or n-weighted within version strata (strata under min_stratum dropped),
    with a permutation p that shuffles clinical codes within each stratum."""
    groups = {}
    for r in rows:
        xs, ys = groups.setdefault(r[0] if stratified else "all", ([], []))
        xs.append(r[1])
        ys.append(r[2])
    floor = min_stratum if stratified else 3
    used = [(kc.ranks(xs), kc.ranks(ys)) for _, (xs, ys) in sorted(groups.items()) if len(xs) >= floor]
    obs = _combined(used)
    out = {"n": sum(len(rx) for rx, _ in used), "strata": [len(rx) for rx, _ in used], "rho": obs}
    if not n_perm or obs is None:
        return out
    rng, perm, hits = random.Random(seed), [list(ry) for _, ry in used], 0
    for _ in range(n_perm):
        for ry in perm:
            rng.shuffle(ry)
        r = _combined([(rx, ry) for (rx, _), ry in zip(used, perm)])
        if r is None:
            continue
        if two_sided:
            hits += abs(r) >= abs(obs) - 1e-12
        else:
            hits += direction * r >= direction * obs - 1e-12
    out["p"] = (hits + 1) / (n_perm + 1)
    return out


def arms(rows, kind):
    if kind != "binary":
        return None
    c = Counter(r[2] for r in rows)
    return {"0": c[0], "1": c[1]}


def floor_ok(rows, kind, min_total=MIN_TOTAL, min_arm=MIN_ARM):
    if len(rows) < min_total:
        return False
    if kind == "binary":
        a = arms(rows, kind)
        return a["0"] >= min_arm and a["1"] >= min_arm
    return True


def grade_test(t, direction):
    if t.get("rho") is None or t.get("p") is None:
        return "untestable"
    return "pass" if direction * t["rho"] > 0 and t["p"] < ALPHA else "fail"


def holm(ps):
    """Holm-adjusted p-values, in the input order."""
    m, run = len(ps), 0.0
    adj = [0.0] * m
    for rank, i in enumerate(sorted(range(m), key=lambda i: ps[i])):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj


def v2_share(rows, kind):
    """Share of v2 participants within each clinical level (numeric: below / at or above the median)."""
    if not rows:
        return []
    if kind == "numeric":
        med = statistics.median(r[2] for r in rows)

        def level(y):
            return "below median" if y < med else "at or above median"
    else:
        def level(y):
            return str(y)
    c = {}
    for r in rows:
        d = c.setdefault(level(r[2]), [0, 0])
        d[0] += 1
        d[1] += r[0] == "v2"
    return [{"level": k, "n": n, "v2_share": v2 / n} for k, (n, v2) in sorted(c.items())]


def control_mode(feat, census_grades, mpp):
    """"pooled" (converted values) when the feature is unitless or census 3 validated its conversion,
    else "stratified" (within-version ranks, which need no conversion)."""
    if feat == "sclerotic_share" or FEATURES[feat][2] == 0:
        return "pooled"
    return "pooled" if mpp and census_grades.get(FEATURES[feat][3]) == "pass" else "stratified"


def run_control(ptable, clin, feat, var, direction, mode, n_perm, seed):
    kind = CLINICAL[var][1]
    conv_rows = rows_for(ptable, clin, feat, var, "conv")
    raw_rows = rows_for(ptable, clin, feat, var, "raw")
    graded_rows = conv_rows if mode == "pooled" else raw_rows
    out = {"feature": feat, "clinical": var, "column": CLINICAL[var][0], "direction": direction, "graded_on": mode,
           "floor_ok": floor_ok(graded_rows, kind), "arms": arms(graded_rows, kind),
           "pooled_conv": stat_test(conv_rows, direction, n_perm, seed, False),
           "pooled_raw": stat_test(raw_rows, direction, n_perm, seed, False),
           "stratified": stat_test(raw_rows, direction, n_perm, seed, True),
           "v1_only": stat_test([r for r in raw_rows if r[0] == "v1"], direction, 0, 0, False),
           "v2_only": stat_test([r for r in raw_rows if r[0] == "v2"], direction, 0, 0, False),
           "v2_share": v2_share(raw_rows, kind),
           "age_strata": [dict(stat_test([r for r in graded_rows if r[3] is not None and lo <= r[3] <= hi],
                                         direction, 0, 0, mode == "stratified"), stratum=name)
                          for name, lo, hi in AGE_STRATA]}
    if feat == "sclerotic_share":
        out["sensitivity_v1_with_sclerotic_book"] = stat_test(
            rows_for(ptable, clin, feat, var, "conv", require_scl_ok=True), direction, n_perm, seed, False)
    test = out["pooled_conv"] if mode == "pooled" else out["stratified"]
    out["grade"] = grade_test(test, direction) if out["floor_ok"] else "untestable"
    return out


def split_halves(pids, seed=SEED):
    order = sorted(pids)
    random.Random(seed).shuffle(order)
    h = len(order) // 2
    return set(order[:h]), set(order[h:])


def discovery(ptable, clin, n_perm, seed=SEED):
    """Screen every feature x clinical pair (controls excluded) in one half, confirm in the other."""
    control_pairs = {(c[1], c[2]) for c in CONTROLS}
    explore, confirm = split_halves([p for p in ptable if p in clin], seed)
    pairs = []
    for i, (feat, var) in enumerate((f, v) for f in DISC_FEATURES for v in DISC_CLINICAL
                                    if (f, v) not in control_pairs):
        kind = CLINICAL[var][1]
        rows_e = rows_for(ptable, clin, feat, var, "raw", explore)
        e = stat_test(rows_e, 1, n_perm, seed + 100 + i, True, two_sided=True)
        row = {"feature": feat, "clinical": var, "explore": e,
               "explore_floor_ok": floor_ok(rows_e, kind, HALF_MIN_TOTAL, HALF_MIN_ARM)}
        row["carried"] = bool(row["explore_floor_ok"] and e.get("p") is not None and e["p"] < ALPHA and e["rho"])
        if row["carried"]:
            sign = 1 if e["rho"] > 0 else -1
            rows_c = rows_for(ptable, clin, feat, var, "raw", confirm)
            c = stat_test(rows_c, sign, n_perm, seed + 200 + i, True)
            row.update({"direction": sign, "confirm": c,
                        "confirm_floor_ok": floor_ok(rows_c, kind, HALF_MIN_TOTAL, HALF_MIN_ARM)})
        pairs.append(row)
    carried = [r for r in pairs if r["carried"]]
    ps = [r["confirm"]["p"] if r["confirm_floor_ok"] and r["confirm"].get("p") is not None
          and r["direction"] * (r["confirm"]["rho"] or 0) > 0 else 1.0 for r in carried]
    for r, a in zip(carried, holm(ps)):
        r["holm_p"] = a
        r["confirmed"] = a < ALPHA
    return {"halves": [len(explore), len(confirm)], "pairs": pairs,
            "carried": len(carried), "confirmed": sum(1 for r in carried if r["confirmed"])}


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--census-results", required=True)
    ap.add_argument("--out-dir", default="/out/q2")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "census3_code_version": k3.CODE_VERSION,
           "python": sys.version.split()[0], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "seed": SEED}
    census = {}
    if os.path.exists(args.census_results):
        with open(args.census_results, encoding="utf-8") as f:
            census = json.load(f)
    grades, mpp = census.get("grades") or {}, census.get("mpp_hat")
    res["census"] = {"found": bool(census), "prereg": census.get("prereg"), "mpp_hat": mpp,
                     "checks": {k: grades.get(k) for k in ("P3_tbm_converted_ratio", "P5_glom_area_converted_ratio")}}
    order = kc.census_order(kc.load_packages(args.file_list))
    packages, status = [], Counter()
    for p in order:
        pdir = os.path.join(cache, p["package"])
        rec_path = os.path.join(pdir, "record.json")
        if len(p["participants"]) != 1 or not os.path.exists(rec_path):
            status["not_cached_or_shared"] += 1
            continue
        with open(rec_path, encoding="utf-8") as f:
            if not json.load(f).get("ok"):
                status["not_ok"] += 1
                continue
        ex = extract_package(pdir, p["version"])
        status["read"] += 1
        status["with_errors"] += bool(ex["errors"])
        packages.append((p["participants"][0], p["version"], ex))
    res["packages"] = dict(status, listed=len(order))
    clin, files = {}, load_clinical_list(args.clinical_list)
    res["clinical_file"] = {"rows": len(files), "name": files[0]["name"] if len(files) == 1 else None}
    if len(files) == 1:
        path = os.path.join(cache, "clinical", files[0]["package"] + ".csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            res["clinical_download"] = kc.download(kc.download_url(files[0]["package"], files[0]["name"]), path,
                                                   get=get, pause=pause)
        if os.path.exists(path):
            clin, res["clinical"] = clinical_table(path)
    ptable = participant_table(packages, mpp)
    res["participants"] = {"with_packages": len(ptable), "with_clinical": sum(1 for p in ptable if p in clin),
                           "by_version": {v: sum(1 for p in ptable.values() if p["versions"] == {v})
                                          for v in ("v1", "v2")},
                           "v1_without_sclerotic_book": sum(1 for p in ptable.values() if not p["scl_ok"])}
    complete = bool(order) and status["read"] >= kc.GRADE_MIN_SHARE * len(order) and bool(clin)
    res["controls"], g = {}, {}
    for k, (key, feat, var, direction) in enumerate(CONTROLS, 1):
        mode = control_mode(feat, grades, mpp)
        res["controls"][key] = run_control(ptable, clin, feat, var, direction, mode, args.permutations, SEED + k)
        g[key] = res["controls"][key]["grade"] if complete else "pending"
    g["status"] = "complete" if complete else "incomplete"
    res["grades"] = g
    res["discovery"] = discovery(ptable, clin, args.permutations) if complete else None
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"packages": res["packages"], "participants": res["participants"], "grades": g,
                      "discovery": {k: res["discovery"][k] for k in ("halves", "carried", "confirmed")}
                      if res["discovery"] else None, "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
