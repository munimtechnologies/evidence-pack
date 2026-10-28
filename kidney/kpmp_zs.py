#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_zs: is the share of KPMP tubules without a TBM thickness more than small or collapsed tubules?

Pre-registration: findings/kpmp-zs-prereg-v1-2026-10-28.md.

kpmp-tbm0-v2 found that a participant's share of tubule rows with "Average TBM Thickness" <= 0 tracks
tubular atrophy % (rho +0.38) and baseline eGFR (rho -0.36), against our prediction. Those rows are
small (median size 0.15-0.23 of the others) and have near-closed lumens (median luminal fraction 0.02
against 0.12-0.15). This job asks whether the share still tracks atrophy and eGFR once a participant's
median tubule size, share of collapsed lumens or age is held fixed (rank partial correlation).

Reuses the readers of kidney.kpmp_tbm0 1.0 and the score, clinical and statistics code of
kidney.kpmp_census 1.0, kpmp_census2 2.0 and kpmp_q2 1.0, all unchanged. Reads only the cached data
volume; downloads nothing. Writes aggregate statistics only.

Standard library only. Usage:
  python -m kidney.kpmp_zs --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --out-dir /out/zs --data-dir /data
"""
import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_q2 as q2
from kidney import kpmp_tbm0 as kt

PREREG = "findings/kpmp-zs-prereg-v1-2026-10-28.md"
CODE_VERSION = "1.0"
SEED = 20261029
MIN_TUBULES = kt.MIN_TUBULES
LUMEN_COLLAPSED = 0.05
SMALL_Q = 0.25
# (key, outcome source, outcome, covariate, predicted sign)
TESTS = (("S1_zero_share_vs_atrophy_given_size", "tiv", kc.ATROPHY_SCORE, "size_med", 1),
         ("S2_zero_share_vs_egfr_given_size", "clinical", "egfr", "size_med", -1),
         ("S3_zero_share_vs_atrophy_given_age", "tiv", kc.ATROPHY_SCORE, "age_bin", 1),
         ("S4_zero_share_vs_egfr_given_age", "clinical", "egfr", "age_bin", -1),
         ("S5_zero_share_vs_atrophy_given_collapsed", "tiv", kc.ATROPHY_SCORE, "collapsed_share", 1),
         ("S6_zero_share_vs_egfr_given_collapsed", "clinical", "egfr", "collapsed_share", -1))
GRADE_KEYS = tuple(t[0] for t in TESTS)
# Descriptive only: (key, feature, outcome source, outcome, covariate or None)
DESCRIBE = tuple(("D_%s_vs_%s" % (f, o), f, s, c, None)
                 for f in ("zero_share", "zero_share_cortex", "size_med", "small_share", "collapsed_share")
                 for o, s, c in (("atrophy", "tiv", kc.ATROPHY_SCORE), ("egfr", "clinical", "egfr"))) + (
    ("D_zero_share_vs_fibrosis", "zero_share", "tiv", kc.FIBROSIS_SCORE, None),
    ("D_zero_share_vs_diabetes", "zero_share", "clinical", "diabetes", None),
    ("D_zero_share_vs_proteinuria", "zero_share", "clinical", "proteinuria", None),
    ("D_zero_share_vs_albuminuria", "zero_share", "clinical", "albuminuria", None),
    ("D_zero_share_vs_age", "zero_share", "clinical", "age_bin", None),
    ("D_zero_share_vs_small_share", "zero_share", "feature", "small_share", None),
    ("D_zero_share_vs_collapsed_share", "zero_share", "feature", "collapsed_share", None),
    ("D_zero_share_vs_atrophy_given_small", "zero_share", "tiv", kc.ATROPHY_SCORE, "small_share"),
    ("D_zero_share_vs_egfr_given_small", "zero_share", "clinical", "egfr", "small_share"))


def quantile(v, q):
    """The value at index floor(q * (n - 1)) of the sorted values; None if empty."""
    if not v:
        return None
    s = sorted(v)
    return s[int(q * (len(s) - 1))]


def size_cuts(packages):
    """{version: SMALL_Q quantile of positive sizes of tubules with a TBM number}."""
    return {v: quantile([t[3] for _, ver, rs in packages if ver == v for t in rs
                         if t[0] is not None and t[3] is not None and t[3] > 0], SMALL_Q) for v in ("v1", "v2")}


def participant_table(packages, owner, cuts):
    """{participant: counts} from packages with exactly one participant. Only tubules with a TBM number
    count. Cortex counts leave out v1 rows coded as medulla (v2 has no medulla column)."""
    out = {}
    for package, version, rows in packages:
        pid = owner.get(package)
        if pid is None:
            continue
        p = out.setdefault(pid, {"versions": set(), "n": 0, "zero": 0, "n_cortex": 0, "zero_cortex": 0,
                                 "sizes": [], "small": 0, "lumen_n": 0, "collapsed": 0})
        p["versions"].add(version)
        cut = cuts.get(version)
        for tbm, _, lumen, size, med in rows:
            if tbm is None:
                continue
            z = kt.is_zero(tbm)
            p["n"] += 1
            p["zero"] += z
            if med != 1:
                p["n_cortex"] += 1
                p["zero_cortex"] += z
            if size is not None and size > 0:
                p["sizes"].append(size)
                p["small"] += cut is not None and size < cut
            if lumen is not None:
                p["lumen_n"] += 1
                p["collapsed"] += lumen < LUMEN_COLLAPSED
    return out


def feature(p, name):
    """Participant features; None below MIN_TUBULES of the rows each one uses."""
    if name == "zero_share":
        return p["zero"] / p["n"] if p["n"] >= MIN_TUBULES else None
    if name == "zero_share_cortex":
        return p["zero_cortex"] / p["n_cortex"] if p["n_cortex"] >= MIN_TUBULES else None
    if name == "size_med":
        return statistics.median(p["sizes"]) if len(p["sizes"]) >= MIN_TUBULES else None
    if name == "small_share":
        return p["small"] / len(p["sizes"]) if len(p["sizes"]) >= MIN_TUBULES else None
    if name == "collapsed_share":
        return p["collapsed"] / p["lumen_n"] if p["lumen_n"] >= MIN_TUBULES else None
    raise KeyError(name)


def lookup(ptable, pid, source, key, scores, clin):
    if source == "tiv":
        return (scores.get(pid) or {}).get(key)
    if source == "clinical":
        return (clin.get(pid) or {}).get(key)
    return feature(ptable[pid], key)


def test_rows(ptable, feat, source, key, cov, scores, clin):
    """[(version stratum, feature, outcome, covariate)] in participant order; participants missing any
    of them are left out. The covariate is None when cov is None."""
    out = []
    for pid in sorted(ptable):
        x = feature(ptable[pid], feat)
        y = lookup(ptable, pid, source, key, scores, clin)
        z = None if cov is None else lookup(ptable, pid, "clinical" if cov == "age_bin" else "feature", cov,
                                             scores, clin)
        if x is None or y is None or (cov is not None and z is None):
            continue
        out.append(("+".join(sorted(ptable[pid]["versions"])), x, y, z))
    return out


def residuals(y, z):
    """Residuals of the least-squares line of y on z (y minus its mean when z does not vary)."""
    n = len(y)
    my, mz = sum(y) / n, sum(z) / n
    szz = sum((b - mz) ** 2 for b in z)
    if szz == 0:
        return [a - my for a in y]
    beta = sum((a - my) * (b - mz) for a, b in zip(y, z)) / szz
    return [a - my - beta * (b - mz) for a, b in zip(y, z)]


def partial_test(rows, direction, n_perm, seed, min_stratum=q2.MIN_STRATUM, two_sided=False):
    """Rank partial correlation of feature and outcome given the covariate: within each version stratum
    (strata under min_stratum dropped), ranks of feature and outcome are each regressed on ranks of the
    covariate and the residuals correlated; strata are combined n-weighted as in kidney.kpmp_q2. The
    permutation p shuffles the outcome residuals within each stratum."""
    groups = {}
    for s, x, y, z in rows:
        g = groups.setdefault(s, ([], [], []))
        g[0].append(x)
        g[1].append(y)
        g[2].append(z)
    used = []
    for _, (xs, ys, zs) in sorted(groups.items()):
        if len(xs) < min_stratum:
            continue
        rz = kc.ranks(zs)
        used.append((residuals(kc.ranks(xs), rz), residuals(kc.ranks(ys), rz)))
    obs = q2._combined(used)
    out = {"n": sum(len(ex) for ex, _ in used), "strata": [len(ex) for ex, _ in used], "rho": obs}
    if not n_perm or obs is None:
        return out
    rng, perm, hits = random.Random(seed), [list(ey) for _, ey in used], 0
    for _ in range(n_perm):
        for ey in perm:
            rng.shuffle(ey)
        r = q2._combined([(ex, ey) for (ex, _), ey in zip(used, perm)])
        if r is None:
            continue
        if two_sided:
            hits += abs(r) >= abs(obs) - 1e-12
        else:
            hits += direction * r >= direction * obs - 1e-12
    out["p"] = (hits + 1) / (n_perm + 1)
    return out


def grade(res):
    g = {}
    for key, _, _, _, direction in TESTS:
        t = res["tests"][key]
        g[key] = q2.grade_test(t["partial"], direction) if t["floor_ok"] else "untestable"
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--out-dir", default="/out/zs")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": SEED}
    order = kc.census_order(kc.load_packages(args.file_list))
    packages, owner, status, errors = [], {}, Counter(), []
    for p in order:
        rec_path = os.path.join(cache, p["package"], "record.json")
        if not os.path.exists(rec_path):
            status["not_cached"] += 1
            continue
        with open(rec_path, encoding="utf-8") as f:
            if not json.load(f).get("ok"):
                status["not_ok"] += 1
                continue
        rows, _, err = kt.tubules(os.path.join(cache, p["package"]), p["version"])
        status["read"] += 1
        status["with_errors"] += bool(err)
        errors.extend(err[:2])
        packages.append((p["package"], p["version"], rows))
        if len(p["participants"]) == 1:
            owner[p["package"]] = p["participants"][0]
    res["packages"] = dict(status, listed=len(order))
    res["errors"] = errors[:20]
    cuts = size_cuts(packages)
    res["size_cut"] = cuts
    scores, clin = {}, {}
    desc = k2.load_descriptor(args.descriptor_list)
    if len(desc) == 1:
        path = os.path.join(cache, "tiv", desc[0]["package"] + ".xlsx")
        if os.path.exists(path):
            scores, info = k2.tiv_scores(kc.read_xlsx(path))
            res["tiv"] = {k: info.get(k) for k in ("sheet", "participants", "usable", "missing_columns")}
    files = q2.load_clinical_list(args.clinical_list)
    if len(files) == 1:
        path = os.path.join(cache, "clinical", files[0]["package"] + ".csv")
        if os.path.exists(path):
            clin, info = q2.clinical_table(path)
            res["clinical"] = {k: info.get(k) for k in ("participants", "missing_columns")}
    ptable = participant_table(packages, owner, cuts)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "with_clinical": sum(1 for p in ptable if p in clin)}
    res["tests"] = {}
    for k, (key, source, col, cov, direction) in enumerate(TESTS, 1):
        rows = test_rows(ptable, "zero_share", source, col, cov, scores, clin)
        res["tests"][key] = {
            "outcome": col, "covariate": cov, "direction": direction, "floor_ok": len(rows) >= q2.MIN_TOTAL,
            "partial": partial_test(rows, direction, args.permutations, SEED + k),
            "v1_only": partial_test([r for r in rows if r[0] == "v1"], direction, 0, 0),
            "v2_only": partial_test([r for r in rows if r[0] == "v2"], direction, 0, 0),
            "unadjusted_same_rows": q2.stat_test(rows, direction, 0, 0, True)}
    ps = [res["tests"][t[0]]["partial"].get("p") for t in TESTS]
    if all(p is not None for p in ps):
        res["holm"] = dict(zip(GRADE_KEYS, q2.holm(ps)))
    res["describe"] = {}
    for k, (key, feat, source, col, cov) in enumerate(DESCRIBE, 101):
        rows = test_rows(ptable, feat, source, col, cov, scores, clin)
        stat = (partial_test(rows, 1, args.permutations, SEED + k, two_sided=True) if cov is not None
                else q2.stat_test(rows, 1, args.permutations, SEED + k, True, two_sided=True))
        res["describe"][key] = dict(stat, covariate=cov)
    complete = bool(order) and status["read"] >= kc.GRADE_MIN_SHARE * len(order) and bool(scores) and bool(clin)
    res["grades"] = grade(res) if complete else {k: "pending" for k in GRADE_KEYS}
    res["grades"]["status"] = "complete" if complete else "incomplete"
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"packages": res["packages"], "participants": res["participants"], "grades": res["grades"],
                      "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
