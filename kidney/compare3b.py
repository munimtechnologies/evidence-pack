#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""compare3b: grade stage 3b (open HuBMAP glomerulus models vs KPMP's NON-globally-sclerotic glomeruli on 12 fresh
open KPMP slides) from local per-slide values.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md exactly as written; it was published before any of
the 12 slides was downloaded. D is kidney/glom.py's count; K_NS = k - k_gs from kidney/kmask.py (both after the
2,000 um^2 floor). Graded only on complete slides, and only if at least 10 of the 12 are complete.

  B1  sum(D) / sum(K_NS) in [0.80, 1.25]
  B2  abs(D - K_NS) <= max(3, 0.25 x K_NS) on at least ceil(2n/3) of the n complete slides
  B3  B2's count >= (mean count over all n-1 non-zero cyclic shifts of the K_NS list) + 2; else B2 is uninformative
  B4  sum(D) strictly closer to sum(K_NS) than to sum(K); graded only if sum(K_GS) >= 5
  B5  Spearman rho(D, K_NS) >= 0.50 (average ranks for ties); not graded if either side is constant
  B6  pooled median area of D / pooled median area of K's non-sclerotic objects in [0.70, 1.43]

grade_b() returns aggregates only and main() refuses any output that names a slide, per the KPMP data use terms.
Standard library only. Usage:
  python -m kidney.compare3b --glom glom.json --k k.json --out compare3b.json
"""
import argparse
import json
import math
import statistics

from kidney.compare import check_aggregate, d_side, in_range, merge, within

CODE_VERSION = "0.1.0"
N_PLANNED = 12
MIN_COMPLETE = 10
B1_RANGE = (0.80, 1.25)
B3_MARGIN = 2
GS_MIN = 5
B5_MIN_RHO = 0.50
B6_RANGE = (0.70, 1.43)
PREDICTIONS = ("b1", "b2", "b3", "b4", "b5", "b6")


def plan_names(n=N_PLANNED):
    """Private slide names used in the job: slide3b01 ... slide3b12 (selection order)."""
    return tuple("slide3b%02d" % (i + 1) for i in range(n))


def needed_b2(n):
    """ceil(2n/3) in integer arithmetic."""
    return (2 * n + 2) // 3


def cyclic_shift_counts(ds, ks):
    """Slides within tolerance when D of slide i is paired with K of slide i+s (mod n), for s = 1 .. n-1."""
    n = len(ds)
    return [sum(within(ds[i], ks[(i + s) % n]) for i in range(n)) for s in range(1, n)]


def ranks(xs):
    """1-based ranks; tied values share their mean rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            r[order[t]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    """Spearman's rho (Pearson correlation of average ranks); None if n < 3 or either side is constant."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _not_graded(why):
    return {"graded": False, "why": why}


def _complete(r):
    return r.get("d") is not None and r.get("k") is not None and r.get("k_gs") is not None


def grade_b(slides, order=None):
    """Aggregate grades B1-B6. `slides` maps a plan slide name to {"d", "d_areas_um2", "k", "k_gs",
    "k_areas_by_kind", ...}. Returns aggregates only."""
    order = tuple(order or plan_names())
    ok = [slides[s] for s in order if s in slides and _complete(slides[s])]
    n = len(ok)
    out = {"code_version": CODE_VERSION, "planned": len(order), "complete": n, "gate": n >= MIN_COMPLETE}
    if not out["gate"]:
        why = "fewer than %d complete slides" % MIN_COMPLETE
        for b in PREDICTIONS:
            out[b] = _not_graded(why)
        return out

    ds = [r["d"] for r in ok]
    kns = [r["k"] - r["k_gs"] for r in ok]
    sd, sns, sk = sum(ds), sum(kns), sum(r["k"] for r in ok)
    sgs = sk - sns

    if sns == 0:
        out["b1"] = _not_graded("sum(K_NS) = 0")
    else:
        ratio = sd / float(sns)
        out["b1"] = {"graded": True, "ratio": round(ratio, 3), "range": list(B1_RANGE),
                     "held": in_range(ratio, B1_RANGE)}

    w = sum(within(d, k) for d, k in zip(ds, kns))
    need = needed_b2(n)
    out["b2"] = {"graded": True, "within": w, "of": n, "needed": need, "held": w >= need, "informative": None}

    sh = cyclic_shift_counts(ds, kns)
    mean_sh = statistics.mean(sh)
    b3 = w >= mean_sh + B3_MARGIN
    out["b3"] = {"graded": True, "shift_mean_within": round(mean_sh, 3), "shift_max_within": max(sh),
                 "margin": B3_MARGIN, "held": b3}
    out["b2"]["informative"] = b3

    if sgs < GS_MIN:
        out["b4"] = _not_graded("fewer than %d globally sclerotic objects in all" % GS_MIN)
    else:
        out["b4"] = {"graded": True, "ratio_to_all_k": round(sd / float(sk), 3),
                     "held": abs(sd - sns) < abs(sd - sk)}

    rho = spearman(ds, kns)
    if rho is None:
        out["b5"] = _not_graded("a side is constant")
    else:
        out["b5"] = {"graded": True, "rho": round(rho, 3), "min": B5_MIN_RHO, "held": rho >= B5_MIN_RHO}

    if any(r.get("d_areas_um2") is None for r in ok):
        out["b6"] = _not_graded("glom.json has no per-glomerulus areas")
    elif any((r.get("k_areas_by_kind") or {}).get("glom") is None for r in ok):
        out["b6"] = _not_graded("KPMP non-sclerotic areas could not be put in um^2")
    else:
        da = [a for r in ok for a in r["d_areas_um2"]]
        ka = [a for r in ok for a in r["k_areas_by_kind"]["glom"]]
        if not da or not ka:
            out["b6"] = _not_graded("no objects on one side")
        else:
            ratio = statistics.median(da) / float(statistics.median(ka))
            out["b6"] = {"graded": True, "ratio": round(ratio, 3), "range": list(B6_RANGE),
                         "held": in_range(ratio, B6_RANGE)}

    out["gs_share_of_k"] = round(sgs / float(sk), 3) if sk else None
    out["held"] = sum(1 for b in PREDICTIONS if out[b].get("held") is True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade stage 3b from local glom.json and k.json.")
    ap.add_argument("--glom", required=True, help="glom.json from kidney/glom.py (local)")
    ap.add_argument("--k", required=True, help="k.json from kidney/kmask.py >= 0.2.0 (local)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.glom, encoding="utf-8") as f:
        glom_doc = json.load(f)
    with open(a.k, encoding="utf-8") as f:
        k = json.load(f)
    doc = grade_b(merge(d_side(glom_doc), k))
    check_aggregate(doc, names=plan_names())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
