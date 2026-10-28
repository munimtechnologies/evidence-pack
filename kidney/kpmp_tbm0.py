#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_tbm0: KPMP tubules without a TBM thickness.

Pre-registration: findings/kpmp-tbm0-prereg-v1-2026-10-28.md.

The object audit (kidney.kpmp_objects 1.0) found that 10.0% of v2 tubule rows have an "Average TBM
Thickness" of zero or less, and every participant median in the census and question 2 included them.
This job asks where those rows are (versions, slides, medulla, tubule size) and whether TBM thickness
tracks tubular atrophy or eGFR once they are left out, and whether their share does.

Reuses the census readers (kidney.kpmp_census 1.0, kpmp_census2 2.0, kpmp_census3 3.0) and question 2's
clinical coding and statistics (kidney.kpmp_q2 1.0), all unchanged. Reads only the data volume the
census filled; downloads nothing that is not already cached. Writes aggregate statistics only.

Standard library only. Usage:
  python -m kidney.kpmp_tbm0 --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --out-dir /out --data-dir /data
"""
import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_census3 as k3
from kidney import kpmp_q2 as q2

PREREG = "findings/kpmp-tbm0-prereg-v1-2026-10-28.md"
CODE_VERSION = "1.0"
SEED = 20261028
MIN_TUBULES = 20
MIN_SLIDES = 20
MIN_MEDULLA = 100
MIN_MEDULLA_ZERO = 10
SHIFT = 0.05
TBM, CELL, LUMEN = "average tbm thickness", "average cell thickness", "luminal fraction"
PIXEL_AREA, MEDULLA = "area (pixel^2)", "in medulla"
BOX = ("x1", "x2", "y1", "y2")
TRUE = {"1", "1.0", "true", "yes"}
FALSE = {"0", "0.0", "false", "no"}
# (key, participant feature, clinical source, score column or clinical code, predicted sign)
TESTS = (("Z5_tbm_pos_vs_atrophy", "tbm_pos", "tiv", kc.ATROPHY_SCORE, 1),
         ("Z6_tbm_pos_vs_egfr", "tbm_pos", "clinical", "egfr", -1),
         ("Z7_zero_share_vs_atrophy", "zero_share", "tiv", kc.ATROPHY_SCORE, 1),
         ("Z8_zero_share_vs_egfr", "zero_share", "clinical", "egfr", -1))
GRADE_KEYS = ("Z1_v1_zero_share", "Z2_v2_slide_dispersion", "Z3_v2_zero_smaller", "Z4_v1_medulla_odds") + tuple(
    t[0] for t in TESTS)


def medulla_code(text):
    t = str(text if text is not None else "").strip().lower()
    return 1 if t in TRUE else 0 if t in FALSE else None


def tubules(path, version):
    """[(tbm, cell, lumen, size, medulla)] for every tubule row of one cached package. size is the box
    area (v2) or "Area (pixel^2)" (v1); medulla is 1, 0 or None (v2 has no such column). Also the raw
    "In Medulla" values seen (a Counter) and read errors."""
    rows, raw_med, errors = [], Counter(), []
    for fn in sorted(os.listdir(path)):
        if kc.ext_of(fn) != "xlsx":
            continue
        try:
            for key, sheet in k3.book_sheets3(os.path.join(path, fn), fn, version).items():
                if key != "tubs":
                    continue
                header, data = kc.sheet_table(sheet)
                idx = {k2.col_key(h): j for j, h in enumerate(header)}
                if TBM not in idx:
                    continue
                for r in data:
                    def cell(col):
                        return k2._cell(r, idx[col]) if col in idx else None
                    if all(b in idx for b in BOX):
                        x1, x2, y1, y2 = (cell(b) for b in BOX)
                        size = (x2 - x1) * (y2 - y1) if None not in (x1, x2, y1, y2) else None
                    else:
                        size = cell(PIXEL_AREA)
                    med = None
                    if MEDULLA in idx:
                        v = r[idx[MEDULLA]] if idx[MEDULLA] < len(r) else None
                        raw_med[str(v)] += 1
                        med = medulla_code(v)
                    rows.append((cell(TBM), cell(CELL), cell(LUMEN), size, med))
        except Exception as e:
            errors.append({"member": fn, "error": repr(e)[:300]})
    return rows, raw_med, errors


def is_zero(tbm):
    return tbm is not None and tbm <= 0


def dispersion(slides):
    """Pearson chi-square / df of per-slide zero counts against one common rate; slides = [(zero, n)]."""
    n_all = sum(n for _, n in slides)
    if len(slides) < 2 or not n_all:
        return None
    rate = sum(z for z, _ in slides) / n_all
    if rate in (0, 1):
        return None
    chi = sum((z - n * rate) ** 2 / (n * rate * (1 - rate)) for z, n in slides)
    return chi / (len(slides) - 1)


def odds_ratio(a, b, c, d):
    """(a/b) / (c/d) with 0.5 added to each cell."""
    return ((a + 0.5) / (b + 0.5)) / ((c + 0.5) / (d + 0.5))


def summarise(packages):
    """Version, slide, medulla and size facts. packages: [(package, version, rows)]."""
    out = {}
    for v in ("v1", "v2"):
        rows = [t for _, ver, rs in packages if ver == v for t in rs]
        with_tbm = [t for t in rows if t[0] is not None]
        zero = [t for t in with_tbm if is_zero(t[0])]
        pos = [t for t in with_tbm if not is_zero(t[0])]
        slides = [(sum(1 for t in rs if is_zero(t[0])), sum(1 for t in rs if t[0] is not None))
                  for _, ver, rs in packages if ver == v]
        slides = [s for s in slides if s[1] >= MIN_TUBULES]
        shares = [z / n for z, n in slides]
        shifts = []
        for _, ver, rs in packages:
            if ver != v:
                continue
            allv = [t[0] for t in rs if t[0] is not None]
            posv = [t[0] for t in rs if t[0] is not None and t[0] > 0]
            if len(allv) >= MIN_TUBULES and posv and statistics.median(allv) > 0:
                shifts.append(statistics.median(posv) / statistics.median(allv) - 1)
        zs = [t[3] for t in zero if t[3] is not None and t[3] > 0]
        ps = [t[3] for t in pos if t[3] is not None and t[3] > 0]
        d = {"rows": len(rows), "with_tbm": len(with_tbm), "zero_or_less": len(zero),
             "exactly_zero": sum(1 for t in zero if t[0] == 0),
             "share": len(zero) / len(with_tbm) if with_tbm else None,
             "slides": len(slides), "dispersion": dispersion(slides),
             "slide_share": {"min": min(shares), "median": statistics.median(shares), "max": max(shares),
                             "over_half": sum(1 for s in shares if s > 0.5),
                             "none": sum(1 for z, _ in slides if z == 0)} if shares else None,
             "size_median": {"zero": kc._median(zs), "positive": kc._median(ps)},
             "size_ratio": (kc._median(zs) / kc._median(ps)) if zs and ps else None,
             "cell_median": {"zero": kc._median([t[1] for t in zero if t[1] is not None]),
                             "positive": kc._median([t[1] for t in pos if t[1] is not None])},
             "lumen_median": {"zero": kc._median([t[2] for t in zero if t[2] is not None]),
                              "positive": kc._median([t[2] for t in pos if t[2] is not None])},
             "slide_median_shift": {"slides": len(shifts), "over_5pct": sum(1 for s in shifts if abs(s) > SHIFT),
                                    "median": kc._median(shifts)}}
        if v == "v1":
            m = Counter((t[4], is_zero(t[0])) for t in with_tbm)
            d["medulla"] = {"medulla_zero": m[(1, True)], "medulla_pos": m[(1, False)],
                            "cortex_zero": m[(0, True)], "cortex_pos": m[(0, False)],
                            "uncoded": m[(None, True)] + m[(None, False)]}
            d["medulla"]["odds_ratio"] = odds_ratio(m[(1, True)], m[(1, False)], m[(0, True)], m[(0, False)])
        out[v] = d
    return out


def participant_table(packages, owner):
    """{participant: {"versions", "n", "zero", "tbm_pos"}} from packages with exactly one participant."""
    out = {}
    for package, version, rows in packages:
        pid = owner.get(package)
        if pid is None:
            continue
        p = out.setdefault(pid, {"versions": set(), "n": 0, "zero": 0, "tbm_pos": []})
        p["versions"].add(version)
        for t in rows:
            if t[0] is None:
                continue
            p["n"] += 1
            if is_zero(t[0]):
                p["zero"] += 1
            else:
                p["tbm_pos"].append(t[0])
    return out


def feature(p, name):
    """tbm_pos: median of positive TBM values (at least MIN_TUBULES of them); zero_share: share of the
    participant's tubules with a TBM value that are zero or less (at least MIN_TUBULES tubules)."""
    if name == "tbm_pos":
        return statistics.median(p["tbm_pos"]) if len(p["tbm_pos"]) >= MIN_TUBULES else None
    return p["zero"] / p["n"] if p["n"] >= MIN_TUBULES else None


def test_rows(ptable, feat, source, key, scores, clin):
    """[(version stratum, feature, outcome, None)] in participant order, for q2.stat_test."""
    out = []
    for pid in sorted(ptable):
        y = (scores.get(pid) or {}).get(key) if source == "tiv" else (clin.get(pid) or {}).get(key)
        x = feature(ptable[pid], feat) if y is not None else None
        if x is None:
            continue
        out.append(("+".join(sorted(ptable[pid]["versions"])), x, y, None))
    return out


def _grade(value, ok, untestable=False):
    if untestable or value is None:
        return "untestable"
    return "pass" if ok else "fail"


def grade(res):
    s, g = res["summary"], {}
    v1, v2 = s["v1"], s["v2"]
    g["Z1_v1_zero_share"] = _grade(v1["share"], (v1["share"] or 0) >= 0.01, v1["with_tbm"] < 1000)
    g["Z2_v2_slide_dispersion"] = _grade(v2["dispersion"], (v2["dispersion"] or 0) > 2, v2["slides"] < MIN_SLIDES)
    g["Z3_v2_zero_smaller"] = _grade(v2["size_ratio"], (v2["size_ratio"] or 1) < 0.8)
    m = v1.get("medulla") or {}
    few = (m.get("medulla_zero", 0) + m.get("medulla_pos", 0) < MIN_MEDULLA
           or m.get("medulla_zero", 0) + m.get("cortex_zero", 0) < MIN_MEDULLA_ZERO)
    g["Z4_v1_medulla_odds"] = _grade(m.get("odds_ratio"), (m.get("odds_ratio") or 0) >= 2, few)
    for key, _, _, _, direction in TESTS:
        t = res["tests"][key]
        g[key] = q2.grade_test(t["stratified"], direction) if t["floor_ok"] else "untestable"
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--permutations", type=int, default=kc.PERMUTATIONS)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": SEED}
    order = kc.census_order(kc.load_packages(args.file_list))
    packages, owner, status, raw_med, errors = [], {}, Counter(), Counter(), []
    for p in order:
        rec_path = os.path.join(cache, p["package"], "record.json")
        if not os.path.exists(rec_path):
            status["not_cached"] += 1
            continue
        with open(rec_path, encoding="utf-8") as f:
            if not json.load(f).get("ok"):
                status["not_ok"] += 1
                continue
        rows, med, err = tubules(os.path.join(cache, p["package"]), p["version"])
        status["read"] += 1
        status["with_errors"] += bool(err)
        errors.extend(err[:2])
        raw_med.update(med)
        packages.append((p["package"], p["version"], rows))
        if len(p["participants"]) == 1:
            owner[p["package"]] = p["participants"][0]
    res["packages"] = dict(status, listed=len(order))
    res["errors"] = errors[:20]
    res["in_medulla_raw_values"] = [{"value": k, "rows": n} for k, n in raw_med.most_common(10)]
    res["summary"] = summarise(packages)
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
    ptable = participant_table(packages, owner)
    res["participants"] = {"with_packages": len(ptable), "with_tiv": sum(1 for p in ptable if p in scores),
                           "with_clinical": sum(1 for p in ptable if p in clin)}
    res["tests"] = {}
    for k, (key, feat, source, col, direction) in enumerate(TESTS, 5):
        rows = test_rows(ptable, feat, source, col, scores, clin)
        res["tests"][key] = {
            "feature": feat, "outcome": col, "direction": direction, "floor_ok": len(rows) >= q2.MIN_TOTAL,
            "stratified": q2.stat_test(rows, direction, args.permutations, SEED + k, True),
            "v1_only": q2.stat_test([r for r in rows if r[0] == "v1"], direction, 0, 0, False),
            "v2_only": q2.stat_test([r for r in rows if r[0] == "v2"], direction, 0, 0, False)}
    ps = [res["tests"][t[0]]["stratified"].get("p") for t in TESTS]
    if all(p is not None for p in ps):
        res["holm"] = dict(zip([t[0] for t in TESTS], q2.holm(ps)))
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
