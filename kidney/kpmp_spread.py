#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_spread: is the within-biopsy spread of glomerular size higher at higher albuminuria?

Pre-registration (measures, floors, rules, predictions): findings/kpmp-spread-prereg-v1-2026-10-30.md.

Per participant, the interquartile range (IQR) of ln(glomerular tuft area) over the non-sclerotic
glomeruli in KPMP's released pathomics workbooks. A log spread does not depend on the unit, so the v1/v2
pixel-size problem cancels within a participant. Tested against KPMP's open clinical file with the
version-stratified Spearman statistic of kidney.kpmp_q2, and once more after removing the participant's
median ln(area) from both ranks (Kennedy permutation of the residuals).

The statistics are standard library only and tested offline. main() reads the census cache with
kpmp_q2's readers, which are imported there so the tests need no other module. Writes aggregate
statistics only: no participant ID, no participant-level value, no KPMP file.

Usage (after kidney.kpmp_fill, or with the census cache already filled):
  python -m kidney.kpmp_spread --file-list inputs/kpmp-segmentation-files.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --data-dir /data --out-dir /out/spread
"""
import argparse
import json
import math
import os
import random
import sys
import time
from collections import Counter

PREREG = "findings/kpmp-spread-prereg-v1-2026-10-30.md"
CODE_VERSION = "1.0"
SEED = 20261030
ALPHA = 0.05
PERMUTATIONS = 10_000
MIN_GLOMS = 10
MIN_GLOMS_SENSITIVITY = 20
MIN_TOTAL = 60
MIN_STRATUM = 10
GRADE_MIN_SHARE = 0.95
# feature: log-transform before the spread (positive values only) or not
FEATURES = {"glom_area": True, "mesangial_fraction": False}
# (key, feature, measure, clinical code, direction, adjusted for the median)
HYPOTHESES = (("H1_area_iqr_vs_albuminuria", "glom_area", "iqr", "albuminuria", 1, False),
              ("H2_area_iqr_vs_proteinuria", "glom_area", "iqr", "proteinuria", 1, False),
              ("H3_area_iqr_vs_albuminuria_given_median", "glom_area", "iqr", "albuminuria", 1, True))
DESCRIPTIVE = (("median_area_vs_albuminuria", "glom_area", "median", "albuminuria", 1, False),
               ("median_area_vs_proteinuria", "glom_area", "median", "proteinuria", 1, False),
               ("area_sd_vs_albuminuria", "glom_area", "sd", "albuminuria", 1, False),
               ("area_sd_vs_proteinuria", "glom_area", "sd", "proteinuria", 1, False),
               ("area_iqr_vs_proteinuria_given_median", "glom_area", "iqr", "proteinuria", 1, True),
               ("area_iqr_vs_egfr", "glom_area", "iqr", "egfr", -1, False),
               ("area_iqr_vs_diabetes", "glom_area", "iqr", "diabetes", 1, False),
               ("area_iqr_vs_a1c", "glom_area", "iqr", "a1c", 1, False),
               ("area_iqr_vs_n_gloms", "glom_area", "iqr", "n_gloms", 1, False),
               ("mesangial_iqr_vs_albuminuria", "mesangial_fraction", "iqr", "albuminuria", 1, False),
               ("mesangial_iqr_vs_proteinuria", "mesangial_fraction", "iqr", "proteinuria", 1, False))


# ---- per-participant spread ----

def quantile(sorted_v, q):
    """Linear-interpolation quantile (type 7) of an already sorted list."""
    h = (len(sorted_v) - 1) * q
    lo = int(math.floor(h))
    hi = min(lo + 1, len(sorted_v) - 1)
    return sorted_v[lo] + (h - lo) * (sorted_v[hi] - sorted_v[lo])


def spread_stats(values, log=True, min_n=MIN_GLOMS):
    """{"n", "median", "iqr", "sd"} of one participant's values (ln of the positive ones if log);
    None below min_n."""
    v = sorted(math.log(x) for x in values if x is not None and x > 0) if log else \
        sorted(x for x in values if x is not None)
    if len(v) < min_n:
        return None
    mean = sum(v) / len(v)
    return {"n": len(v), "median": quantile(v, 0.5), "iqr": quantile(v, 0.75) - quantile(v, 0.25),
            "sd": math.sqrt(sum((x - mean) ** 2 for x in v) / (len(v) - 1))}


def add_package(ptable, pid, version, values):
    """Pool one package's {feature: [values]} into its participant."""
    p = ptable.setdefault(pid, {"versions": set(), "vals": {f: [] for f in FEATURES}})
    p["versions"].add(version)
    for f in FEATURES:
        p["vals"][f].extend(values.get(f, []))
    return p


def rows_for(ptable, clin, feat, measure, var, min_n=MIN_GLOMS):
    """[(version stratum, spread measure, clinical code, participant median)] in participant-ID order.
    var "n_gloms" uses the participant's count of measured glomeruli as the clinical code."""
    out = []
    for pid in sorted(ptable):
        p = ptable[pid]
        s = spread_stats(p["vals"][feat], FEATURES[feat], min_n)
        if s is None:
            continue
        y = s["n"] if var == "n_gloms" else (clin.get(pid) or {}).get(var)
        if y is None:
            continue
        out.append(("+".join(sorted(p["versions"])), s[measure], y, s["median"]))
    return out


# ---- statistics ----

def ranks(v):
    """Ranks from 1, ties sharing their average rank."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    """Pearson correlation; None if either side has no variation."""
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    if saa <= 1e-12 or sbb <= 1e-12:
        return None
    return sab / math.sqrt(saa * sbb)


def residual(y, z):
    """Residuals of the least-squares line of y on z (y minus its mean if z has no variation)."""
    n = len(y)
    my, mz = sum(y) / n, sum(z) / n
    szz = sum((b - mz) ** 2 for b in z)
    slope = sum((a - my) * (b - mz) for a, b in zip(y, z)) / szz if szz > 1e-12 else 0.0
    return [a - my - slope * (b - mz) for a, b in zip(y, z)]


def _combined(pairs):
    """n-weighted mean of the per-stratum correlations; strata with no variation are skipped."""
    num = den = 0.0
    for a, b in pairs:
        r = pearson(a, b)
        if r is not None:
            num += len(a) * r
            den += len(a)
    return num / den if den else None


def strat_test(rows, direction, n_perm, seed, adjusted=False, min_stratum=MIN_STRATUM):
    """Spearman rho, n-weighted within version strata (strata under min_stratum dropped). If adjusted,
    the ranks of the spread and of the clinical code are each replaced by their residuals on the ranks
    of the participant median (a partial Spearman). One-sided permutation p that shuffles the clinical
    side within each stratum (for adjusted: its residuals, Kennedy 1995)."""
    groups = {}
    for r in rows:
        g = groups.setdefault(r[0], ([], [], []))
        g[0].append(r[1])
        g[1].append(r[2])
        g[2].append(r[3])
    used = []
    for _, (xs, ys, zs) in sorted(groups.items()):
        if len(xs) < min_stratum:
            continue
        rx, ry = ranks(xs), ranks(ys)
        if adjusted:
            rz = ranks(zs)
            rx, ry = residual(rx, rz), residual(ry, rz)
        used.append((rx, ry))
    obs = _combined(used)
    out = {"n": sum(len(a) for a, _ in used), "strata": [len(a) for a, _ in used], "rho": obs}
    if not n_perm or obs is None:
        return out
    rng, perm, hits = random.Random(seed), [list(b) for _, b in used], 0
    for _ in range(n_perm):
        for b in perm:
            rng.shuffle(b)
        r = _combined([(a, b) for (a, _), b in zip(used, perm)])
        if r is not None and direction * r >= direction * obs - 1e-12:
            hits += 1
    out["p"] = (hits + 1) / (n_perm + 1)
    return out


def holm(ps):
    """Holm-adjusted p-values, in the input order."""
    m, run = len(ps), 0.0
    adj = [0.0] * m
    for rank, i in enumerate(sorted(range(m), key=lambda i: ps[i])):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj


def grade(t, direction, min_total=MIN_TOTAL):
    """pass / fail / untestable for one pre-registered test."""
    if t.get("n", 0) < min_total or t.get("rho") is None or t.get("p") is None:
        return "untestable"
    return "pass" if direction * t["rho"] > 0 and t["p"] < ALPHA else "fail"


def level_counts(rows):
    """Participants per clinical level (ordinal codes only)."""
    return {str(k): v for k, v in sorted(Counter(r[2] for r in rows).items())}


def run_test(ptable, clin, spec, n_perm, seed):
    key, feat, measure, var, direction, adjusted = spec
    rows = rows_for(ptable, clin, feat, measure, var)
    out = {"feature": feat, "measure": measure, "clinical": var, "direction": direction,
           "adjusted_for_median": adjusted, "rows": len(rows),
           "test": strat_test(rows, direction, n_perm, seed, adjusted),
           "v1_only": strat_test([r for r in rows if r[0] == "v1"], direction, 0, 0, adjusted),
           "v2_only": strat_test([r for r in rows if r[0] == "v2"], direction, 0, 0, adjusted)}
    if var in ("albuminuria", "proteinuria", "a1c", "diabetes"):
        out["levels"] = level_counts(rows)
    return out


# ---- job ----

def main(argv=None, get=None, pause=None):
    from kidney import kpmp_census as kc
    from kidney import kpmp_q2 as q2
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--out-dir", default="/out/spread")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--permutations", type=int, default=PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "q2_code_version": q2.CODE_VERSION,
           "python": sys.version.split()[0], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "seed": SEED}
    order = kc.census_order(kc.load_packages(args.file_list))
    ptable, status = {}, Counter()
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
        ex = q2.extract_package(pdir, p["version"])
        status["read"] += 1
        status["with_errors"] += bool(ex["errors"])
        add_package(ptable, p["participants"][0], p["version"], ex["values"])
    res["packages"] = dict(status, listed=len(order))
    clin, files = {}, q2.load_clinical_list(args.clinical_list)
    res["clinical_file"] = {"rows": len(files), "name": files[0]["name"] if len(files) == 1 else None}
    if len(files) == 1:
        path = os.path.join(cache, "clinical", files[0]["package"] + ".csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            res["clinical_download"] = kc.download(kc.download_url(files[0]["package"], files[0]["name"]), path,
                                                   get=get, pause=pause)
        if os.path.exists(path):
            clin, res["clinical"] = q2.clinical_table(path)
    res["participants"] = {
        "with_packages": len(ptable), "with_clinical": sum(1 for p in ptable if p in clin),
        "by_version": {v: sum(1 for p in ptable.values() if p["versions"] == {v}) for v in ("v1", "v2")},
        "with_min_gloms": sum(1 for p in ptable.values() if spread_stats(p["vals"]["glom_area"]) is not None)}
    complete = bool(order) and status["read"] >= GRADE_MIN_SHARE * len(order) and bool(clin)
    res["hypotheses"], grades = {}, {}
    for k, spec in enumerate(HYPOTHESES, 1):
        res["hypotheses"][spec[0]] = run_test(ptable, clin, spec, args.permutations, SEED + k)
        grades[spec[0]] = grade(res["hypotheses"][spec[0]]["test"], spec[4]) if complete else "pending"
    ps = [res["hypotheses"][s[0]]["test"].get("p") or 1.0 for s in HYPOTHESES]
    signed = [p if s[4] * (res["hypotheses"][s[0]]["test"].get("rho") or 0) > 0 else 1.0
              for p, s in zip(ps, HYPOTHESES)]
    for s, a in zip(HYPOTHESES, holm(signed)):
        res["hypotheses"][s[0]]["holm_p"] = a
    grades["status"] = "complete" if complete else "incomplete"
    res["grades"] = grades
    res["descriptive"] = {spec[0]: run_test(ptable, clin, spec, args.permutations, SEED + 100 + k)
                          for k, spec in enumerate(DESCRIPTIVE)}
    sens = rows_for(ptable, clin, "glom_area", "iqr", "albuminuria", MIN_GLOMS_SENSITIVITY)
    res["descriptive"]["H1_with_at_least_20_gloms"] = {"rows": len(sens),
                                                       "test": strat_test(sens, 1, args.permutations, SEED + 200)}
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"packages": res["packages"], "participants": res["participants"], "grades": grades,
                      "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
