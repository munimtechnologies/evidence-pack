#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_tbmsz: does KPMP's tubular basement membrane (TBM) thickness track atrophy once tubule size is
taken out?

Pre-registration (measures, floors, rules, predictions): findings/kpmp-tbmsz-prereg-v1-2026-10-30.md.

A participant's median positive TBM thickness tracked neither the KPMP pathologists' tubular atrophy %
nor baseline eGFR (kpmp-tbm0-v2, Z5 and Z6), yet per tubule it is reproducible between serial sections
(kpmp-twinrel-v4, R2: rho 0.46). Atrophic tubules are small, and a participant's share of small tubules
tracks atrophy (kpmp-zs-v2). If measured TBM thickness changes with tubule size, a median over all tubules
mixes the two. Here each tubule's ln TBM is replaced by its residual from one least-squares line of ln TBM
on ln size per version (all tubules of that version), and the participant feature is the median residual.

Reuses the tubule reader of kidney.kpmp_tbm0 1.0, the score, clinical and statistics code of
kidney.kpmp_census, kpmp_census2 and kpmp_q2, and kpmp_zs's rank partial correlation, all unchanged and
imported in main(), so the tests need no other module. Reads only the cached data volume (run
kidney.kpmp_fill first). Writes aggregate statistics only: no participant ID, no participant-level value,
no KPMP file. Standard library only. Usage:
  python -m kidney.kpmp_tbmsz --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --out-dir /out/tbmsz --data-dir /data
"""
import argparse
import json
import math
import os
import statistics
import sys
import time
from collections import Counter

PREREG = "findings/kpmp-tbmsz-prereg-v1-2026-10-30.md"
CODE_VERSION = "1.0"
SEED = 20261031
ALPHA = 0.05
MIN_TUBULES = 20
MIN_TOTAL = 60
SMALL_Q = 0.25
QUARTILES = (0.25, 0.5, 0.75)
# participant feature: the list in the participant table it is the median of
MEDIAN_OF = {"tbm_adj": "resid", "tbm_pos": "tbm_ln", "tbm_adj_floor": "resid_floor",
             "tbm_pos_floor": "tbm_ln_floor"}
# (key, feature, outcome source, outcome, covariate feature or None, predicted sign)
TESTS = (("A1_tbm_adj_vs_atrophy", "tbm_adj", "tiv", "atrophy", None, 1),
         ("A2_tbm_adj_vs_egfr", "tbm_adj", "clinical", "egfr", None, -1),
         ("A3_tbm_adj_vs_atrophy_given_small", "tbm_adj", "tiv", "atrophy", "small_share", 1))
GRADE_KEYS = tuple(t[0] for t in TESTS)
# Descriptive only, two-sided: (key, feature, outcome source, outcome, covariate feature or None)
DESCRIBE = tuple(("D_%s_vs_%s" % (f, o), f, s, o, None)
                 for f in ("tbm_pos", "tbm_adj_floor", "tbm_pos_floor", "small_share")
                 for o, s in (("atrophy", "tiv"), ("egfr", "clinical"))) + (
    ("D_tbm_adj_vs_fibrosis", "tbm_adj", "tiv", "fibrosis", None),
    ("D_tbm_adj_vs_age", "tbm_adj", "clinical", "age_bin", None),
    ("D_tbm_adj_vs_diabetes", "tbm_adj", "clinical", "diabetes", None),
    ("D_tbm_adj_vs_albuminuria", "tbm_adj", "clinical", "albuminuria", None),
    ("D_tbm_adj_vs_proteinuria", "tbm_adj", "clinical", "proteinuria", None),
    ("D_tbm_adj_vs_small_share", "tbm_adj", "feature", "small_share", None),
    ("D_tbm_adj_vs_tbm_pos", "tbm_adj", "feature", "tbm_pos", None),
    ("D_tbm_adj_vs_egfr_given_small", "tbm_adj", "clinical", "egfr", "small_share"))


# ---- per-tubule size adjustment ----

def fit_line(xs, ys):
    """(intercept, slope) of the least-squares line of ys on xs; None below 2 points or if xs do not vary."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 1e-12:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - slope * mx, slope


def usable(row):
    """(ln size, ln TBM) of a kpmp_tbm0 tubule row (tbm, cell, lumen, size, medulla) when both are
    positive; else None."""
    tbm, size = row[0], row[3]
    if tbm is None or size is None or tbm <= 0 or size <= 0:
        return None
    return math.log(size), math.log(tbm)


def version_fits(packages):
    """{version: {"intercept", "slope", "n"}}: ln TBM on ln size over every usable tubule of the version,
    in every package read (shared or not). A version with no fit is left out."""
    pts = {}
    for _, version, rows in packages:
        for r in rows:
            u = usable(r)
            if u is None:
                continue
            xs, ys = pts.setdefault(version, ([], []))
            xs.append(u[0])
            ys.append(u[1])
    out = {}
    for v, (xs, ys) in sorted(pts.items()):
        f = fit_line(xs, ys)
        if f is not None:
            out[v] = {"intercept": f[0], "slope": f[1], "n": len(xs)}
    return out


def quantile(v, q):
    """The value at index floor(q * (n - 1)) of the sorted values (the kpmp_zs rule); None if empty."""
    if not v:
        return None
    s = sorted(v)
    return s[int(q * (len(s) - 1))]


def size_cuts(packages, q=SMALL_Q):
    """{version: q quantile of the positive sizes of tubules with a TBM number} (as kpmp_zs.size_cuts)."""
    return {v: quantile([r[3] for _, ver, rows in packages if ver == v for r in rows
                         if r[0] is not None and r[3] is not None and r[3] > 0], q) for v in ("v1", "v2")}


def quartile_medians(packages):
    """{version: median TBM of the usable tubules in each quarter of that version's sizes}, smallest
    quarter first (TBM in the file's own unit)."""
    out = {}
    for v in ("v1", "v2"):
        pts = [(r[3], r[0]) for _, ver, rows in packages if ver == v for r in rows if usable(r) is not None]
        if len(pts) < 4:
            continue
        sizes = [s for s, _ in pts]
        cuts = [quantile(sizes, q) for q in QUARTILES]
        bins = [[], [], [], []]
        for s, t in pts:
            bins[sum(s > c for c in cuts)].append(t)
        out[v] = [statistics.median(b) if b else None for b in bins]
    return out


# ---- participants ----

def participant_table(packages, owner, fits, cuts):
    """{participant: values} from packages with exactly one participant (owner maps package to participant).
    For each usable tubule: ln TBM ("tbm_ln") and its residual from the version's line ("resid"), and the
    same two again for tubules at or above the version's size cut ("tbm_ln_floor", "resid_floor"). "n"
    and "small" count tubules with a TBM number (zero included) and a positive size, as kpmp_zs does."""
    out = {}
    for package, version, rows in packages:
        pid = owner.get(package)
        if pid is None:
            continue
        p = out.setdefault(pid, {"versions": set(), "tbm_ln": [], "resid": [], "tbm_ln_floor": [],
                                 "resid_floor": [], "n": 0, "small": 0})
        p["versions"].add(version)
        fit, cut = fits.get(version), cuts.get(version)
        for r in rows:
            if r[0] is not None and r[3] is not None and r[3] > 0:
                p["n"] += 1
                p["small"] += cut is not None and r[3] < cut
            u = usable(r)
            if u is None or fit is None:
                continue
            res = u[1] - fit["intercept"] - fit["slope"] * u[0]
            p["tbm_ln"].append(u[1])
            p["resid"].append(res)
            if cut is not None and r[3] >= cut:
                p["tbm_ln_floor"].append(u[1])
                p["resid_floor"].append(res)
    return out


def feature(p, name):
    """A participant feature; None below MIN_TUBULES of the tubules it uses. tbm_adj: median residual;
    tbm_pos: median ln TBM (the plain comparator); *_floor: the same over tubules at or above the size
    cut; small_share: share of tubules below the cut."""
    if name in MEDIAN_OF:
        v = p[MEDIAN_OF[name]]
        return statistics.median(v) if len(v) >= MIN_TUBULES else None
    if name == "small_share":
        return p["small"] / p["n"] if p["n"] >= MIN_TUBULES else None
    raise KeyError(name)


def lookup(ptable, pid, source, key, scores, clin):
    if source == "tiv":
        return (scores.get(pid) or {}).get(key)
    if source == "clinical":
        return (clin.get(pid) or {}).get(key)
    return feature(ptable[pid], key)


def test_rows(ptable, feat, source, key, cov, scores, clin):
    """[(version stratum, feature, outcome, covariate)] in participant order; participants missing any of
    them are left out. cov is a participant feature name, or None (covariate None)."""
    out = []
    for pid in sorted(ptable):
        x = feature(ptable[pid], feat)
        y = lookup(ptable, pid, source, key, scores, clin)
        z = None if cov is None else feature(ptable[pid], cov)
        if x is None or y is None or (cov is not None and z is None):
            continue
        out.append(("+".join(sorted(ptable[pid]["versions"])), x, y, z))
    return out


def grade_one(stat, direction, min_total=MIN_TOTAL, alpha=ALPHA):
    """pass / fail / untestable for one pre-registered test (n counts participants in the strata used)."""
    if stat.get("n", 0) < min_total or stat.get("rho") is None or stat.get("p") is None:
        return "untestable"
    return "pass" if direction * stat["rho"] > 0 and stat["p"] < alpha else "fail"


# ---- job ----

def main(argv=None):
    from kidney import kpmp_census as kc
    from kidney import kpmp_census2 as k2
    from kidney import kpmp_q2 as q2
    from kidney import kpmp_tbm0 as kt
    from kidney import kpmp_zs as zs
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--out-dir", default="/out/tbmsz")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    score_key = {"atrophy": kc.ATROPHY_SCORE, "fibrosis": kc.FIBROSIS_SCORE}
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
    fits = version_fits(packages)
    cuts = size_cuts(packages)
    res["fits"], res["size_cut"] = fits, cuts
    res["size_quarter_tbm_medians"] = quartile_medians(packages)
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
    ptable = participant_table(packages, owner, fits, cuts)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "with_clinical": sum(1 for p in ptable if p in clin),
                           "with_tbm_adj": sum(1 for p in ptable.values() if feature(p, "tbm_adj") is not None)}

    def rows_for(feat, source, key, cov):
        return test_rows(ptable, feat, source, score_key.get(key, key) if source == "tiv" else key, cov,
                         scores, clin)

    def stat(rows, direction, cov, n_perm, seed, two_sided=False):
        if cov is None:
            return q2.stat_test(rows, direction, n_perm, seed, True, two_sided=two_sided)
        return zs.partial_test(rows, direction, n_perm, seed, two_sided=two_sided)

    res["tests"] = {}
    for k, (key, feat, source, outcome, cov, direction) in enumerate(TESTS, 1):
        rows = rows_for(feat, source, outcome, cov)
        t = {"feature": feat, "outcome": outcome, "covariate": cov, "direction": direction, "rows": len(rows),
             "test": stat(rows, direction, cov, args.permutations, SEED + k),
             "v1_only": stat([r for r in rows if r[0] == "v1"], direction, cov, 0, 0),
             "v2_only": stat([r for r in rows if r[0] == "v2"], direction, cov, 0, 0)}
        if cov is not None:
            t["unadjusted_same_rows"] = q2.stat_test(rows, direction, 0, 0, True)
        res["tests"][key] = t
    ps = [res["tests"][k]["test"].get("p") for k in GRADE_KEYS]
    if all(p is not None for p in ps):
        res["holm"] = dict(zip(GRADE_KEYS, q2.holm(ps)))
    res["describe"] = {}
    for k, (key, feat, source, outcome, cov) in enumerate(DESCRIBE, 101):
        rows = rows_for(feat, source, outcome, cov)
        res["describe"][key] = dict(stat(rows, 1, cov, args.permutations, SEED + k, two_sided=True),
                                    covariate=cov, rows=len(rows))
    complete = bool(order) and status["read"] >= kc.GRADE_MIN_SHARE * len(order) and bool(scores) and bool(clin)
    res["grades"] = ({key: grade_one(res["tests"][key]["test"], d) for key, _, _, _, _, d in TESTS} if complete
                     else {k: "pending" for k in GRADE_KEYS})
    res["grades"]["status"] = "complete" if complete else "incomplete"
    res["minutes"] = round((time.time() - t_start) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=sorted)
    print(json.dumps({"packages": res["packages"], "participants": res["participants"], "fits": fits,
                      "grades": res["grades"], "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
