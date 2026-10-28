#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_twinrel: do KPMP's v2 pathomics features agree between the two measurements of one object, one
in each serial section on a slide?

Pre-registration: findings/kpmp-twinrel-prereg-v1-2026-10-28.md.

The section-twins census (kidney.kpmp_twins, findings/kpmp-twins-prereg-v1-2026-10-28.md) finds slides
whose workbook repeats a section at a fixed offset. Every object measured in both sections is a natural
replicate: the same structure, cut a few microns apart and segmented twice. This study uses those
replicates as a test-retest design:
  1. Slides: v2 slides that kpmp_twins.detect flags (same code, same seed), so the slide set is the
     census's own.
  2. Twin pairs: object i and the same-size object j of the same sheet closest to i's centre + offset,
     within kpmp_twins.TOL pixels; closest candidates first, each object at most once as i and once as j.
  3. Null pairs: for each twin pair, i with a random same-size object of the same sheet and slide that is
     neither j nor within TOL of i's centre plus or minus the offset (seeded; NULL_TRIES draws).
  4. Values: each feature transformed (log for sizes and thicknesses, positive values only) and centred on
     its slide median, so agreement is within-slide. Agreement is the Spearman rho over all pairs pooled;
     the null rho is the same over null pairs; uncertainty is a slide-level bootstrap of the difference.
  5. Zero TBM: whether a tubule with TBM thickness <= 0 has a twin with TBM <= 0 more often than a random
     same-size partner (odds ratios, twin vs null).
Every grade waits for the census's positive-control check (T3): if the detector failed it, nothing here
is graded.

Reads only the data volume (run kidney.kpmp_fill first). results.json holds aggregates only, without
package IDs. Standard library only. Usage:
  python -m kidney.kpmp_twinrel --file-list inputs/kpmp-segmentation-files.csv \
      --twins-results /out/twins/results.json --data-dir /data --out-dir /out/twinrel
"""
import argparse
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_census3 as k3
from kidney import kpmp_twins as kw

PREREG = "findings/kpmp-twinrel-prereg-v1-2026-10-28.md"
CODE_VERSION = "1.0"
SEED = 20261028
# (column, transform) per sheet; "log" keeps positive values only.
FEATURES = {"gloms": (("Mesangial Fraction", "raw"), ("Area", "log"), ("Mesangial Area", "log")),
            "s_gloms": (("Mesangial Fraction", "raw"), ("Area", "log")),
            "tubs": (("Average TBM Thickness", "log"), ("Average Cell Thickness", "log"), ("Luminal Fraction", "raw")),
            "arts": (("Arterial Area", "log"),)}
# key: (sheet, column, minimum twin pairs with both values)
GRADED = {"R1_glom_mesangial_fraction": ("gloms", "Mesangial Fraction", 100),
          "R2_tub_tbm_thickness": ("tubs", "Average TBM Thickness", 500),
          "R3_tub_luminal_fraction": ("tubs", "Luminal Fraction", 500),
          "R4_tub_cell_thickness": ("tubs", "Average Cell Thickness", 500)}
RHO_MIN = 0.3
DIFF_LOW = 0.1
BOOT = 200
NULL_TRIES = 100
MIN_REPEAT_SLIDES = 10
ZERO_SHEET, ZERO_COLUMN = "tubs", "Average TBM Thickness"
ZERO_MIN = 50
ZERO_RATIO = 2.0


def objects(path):
    """{sheet: [(row, col, height, width, {column: value})]} from one cached v2 package folder, reading x
    as the row axis (as kpmp_twins.objects). Rows without a valid box are skipped."""
    out = {s: [] for s in FEATURES}
    for fn in sorted(os.listdir(path)):
        if kc.ext_of(fn) != "xlsx":
            continue
        for key, sheet in k3.book_sheets3(os.path.join(path, fn), fn, "v2").items():
            if key not in out:
                continue
            header, data = kc.sheet_table(sheet)
            idx = {k2.col_key(h): j for j, h in enumerate(header)}
            if not all(b in idx for b in kw.BOX):
                continue
            cols = [(name, idx.get(k2.col_key(name))) for name, _ in FEATURES[key]]
            for r in data:
                x1, x2, y1, y2 = (k2._cell(r, idx[b]) for b in kw.BOX)
                if None in (x1, x2, y1, y2) or x2 < x1 or y2 < y1:
                    continue
                vals = {name: (k2._cell(r, j) if j is not None else None) for name, j in cols}
                out[key].append(((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1, vals))
    return out


def tval(v, how):
    if v is None:
        return None
    if how == "log":
        return math.log(v) if v > 0 else None
    return v


def pair_up(objs, offset, tol=kw.TOL):
    """[(i, j)]: object j has the size of object i and its centre within tol of i's centre + offset.
    Closest candidates are taken first; each object is used at most once as i and once as j."""
    grid = defaultdict(list)
    for k, t in enumerate(objs):
        grid[(int(t[0] // tol), int(t[1] // tol))].append(k)
    cand = []
    for i, t in enumerate(objs):
        r, c = t[0] + offset[0], t[1] + offset[1]
        gr, gc = int(r // tol), int(c // tol)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for j in grid.get((gr + a, gc + b), ()):
                    d2 = (objs[j][0] - r) ** 2 + (objs[j][1] - c) ** 2
                    if j != i and d2 <= tol * tol and kw.same_size(t, objs[j]):
                        cand.append((d2, i, j))
    cand.sort()
    used_i, used_j, out = set(), set(), []
    for _, i, j in cand:
        if i in used_i or j in used_j:
            continue
        used_i.add(i)
        used_j.add(j)
        out.append((i, j))
    return sorted(out)


def null_partners(objs, pairs, offset, rng, tol=kw.TOL, tries=NULL_TRIES):
    """[(i, k)]: for each twin pair (i, j), a random object k of i's size, not i or j, whose centre is not
    within tol of i's centre plus or minus offset. Pairs with no such k in `tries` draws are dropped."""
    out = []
    n = len(objs)
    for i, j in pairs:
        t = objs[i]
        for _ in range(tries):
            k = rng.randrange(n)
            o = objs[k]
            if k in (i, j) or not kw.same_size(t, o):
                continue
            if any((o[0] - t[0] - sg * offset[0]) ** 2 + (o[1] - t[1] - sg * offset[1]) ** 2 <= tol * tol
                   for sg in (1, -1)):
                continue
            out.append((i, k))
            break
    return out


def slide_records(objs, offset, rng):
    """({(sheet, column): {"twin": [(a, b)], "null": [(a, b)]}}, {sheet: [objects, twin pairs, null pairs]},
    {"twin": [z, z], "null": [...]}) for one slide. Values are transformed and centred on the slide
    median; the zero tables count [both <= 0, only i <= 0, only j <= 0, both > 0]."""
    recs, counts, zero = {}, {}, {"twin": [0, 0, 0, 0], "null": [0, 0, 0, 0]}
    for sheet, feats in FEATURES.items():
        o = objs.get(sheet, [])
        pairs = pair_up(o, offset)
        nulls = null_partners(o, pairs, offset, rng)
        counts[sheet] = [len(o), len(pairs), len(nulls)]
        for name, how in feats:
            vals = [tval(t[4].get(name), how) for t in o]
            med = kc._median([v for v in vals if v is not None])
            recs[(sheet, name)] = {kind: [(vals[i] - med, vals[j] - med) for i, j in pp
                                          if vals[i] is not None and vals[j] is not None]
                                   for kind, pp in (("twin", pairs), ("null", nulls))}
        if sheet == ZERO_SHEET:
            raw = [t[4].get(ZERO_COLUMN) for t in o]
            for kind, pp in (("twin", pairs), ("null", nulls)):
                for i, j in pp:
                    if raw[i] is None or raw[j] is None:
                        continue
                    zero[kind][(0 if raw[i] <= 0 else 2) + (0 if raw[j] <= 0 else 1)] += 1
    return recs, counts, zero


def rho(pairs):
    if len(pairs) < 3:
        return None
    return kc.spearman([a for a, _ in pairs], [b for _, b in pairs])


def _pct(v, q):
    return v[min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))]


def boot_diff(twin, null, boot=BOOT, seed=SEED):
    """(2.5th, 97.5th percentile) of rho(twin) - rho(null) over slide-level bootstrap resamples. twin and
    null are {slide: [(a, b)]}."""
    slides = sorted(set(twin) | set(null))
    if not slides:
        return None, None
    rng, diffs = random.Random(seed), []
    for _ in range(boot):
        pick = [slides[rng.randrange(len(slides))] for _ in slides]
        rt = rho([p for s in pick for p in twin.get(s, ())])
        rn = rho([p for s in pick for p in null.get(s, ())])
        if rt is not None and rn is not None:
            diffs.append(rt - rn)
    if not diffs:
        return None, None
    diffs.sort()
    return _pct(diffs, 0.025), _pct(diffs, 0.975)


def odds_ratio(t):
    """Concordance odds ratio of a [both, only i, only j, neither] table, 0.5 added to every cell."""
    return (t[0] + 0.5) * (t[3] + 0.5) / ((t[1] + 0.5) * (t[2] + 0.5))


def feature_summary(twin, null, boot, seed):
    """twin and null are {slide: [(a, b)]}."""
    tw = [p for v in twin.values() for p in v]
    nu = [p for v in null.values() for p in v]
    rt, rn = rho(tw), rho(nu)
    low, high = boot_diff(twin, null, boot, seed)
    return {"twin_pairs": len(tw), "null_pairs": len(nu), "slides": sum(1 for v in twin.values() if v),
            "rho_twin": rt, "rho_null": rn, "diff": (rt - rn) if rt is not None and rn is not None else None,
            "diff_ci95": [low, high]}


def grade(features, zero, repeat_slides, t3, min_repeat=MIN_REPEAT_SLIDES, min_pairs=None):
    keys = list(GRADED) + ["R5_zero_tbm_concordance"]
    if t3 is None:
        return dict({k: "pending" for k in keys}, status="incomplete: no twins census result")
    if t3 != "pass":
        return dict({k: "untestable" for k in keys}, status="detector not validated (T3 %s)" % t3)
    if repeat_slides < min_repeat:
        return dict({k: "untestable" for k in keys}, status="fewer than %d repeat slides" % min_repeat)
    g = {}
    for key, (sheet, name, need) in GRADED.items():
        f = features["%s|%s" % (sheet, name)]
        if f["twin_pairs"] < (need if min_pairs is None else min_pairs) or f["rho_twin"] is None \
                or f["diff_ci95"][0] is None:
            g[key] = "untestable"
        else:
            g[key] = "pass" if f["rho_twin"] >= RHO_MIN and f["diff_ci95"][0] >= DIFF_LOW else "fail"
    t = zero["twin"]
    if t[0] + t[1] + t[2] < (ZERO_MIN if min_pairs is None else min(ZERO_MIN, min_pairs)):
        g["R5_zero_tbm_concordance"] = "untestable"
    else:
        g["R5_zero_tbm_concordance"] = "pass" if odds_ratio(t) >= ZERO_RATIO * odds_ratio(zero["null"]) else "fail"
    g["status"] = "complete"
    return g


def read_t3(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return (json.load(f).get("grades") or {}).get("T3_controls")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--twins-results", default="")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out/twinrel")
    ap.add_argument("--boot", type=int, default=BOOT)
    ap.add_argument("--min-repeat-slides", type=int, default=MIN_REPEAT_SLIDES)
    ap.add_argument("--min-pairs", type=int, default=None)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    order = [p for p in kc.census_order(kc.load_packages(args.file_list)) if p["version"] == "v2"]
    rng = random.Random(SEED)
    status, errors = Counter(), []
    pooled = defaultdict(lambda: {"twin": {}, "null": {}})
    counts = {s: [0, 0, 0] for s in FEATURES}
    zero = {"twin": [0, 0, 0, 0], "null": [0, 0, 0, 0]}
    repeat = 0
    for p in order:
        pdir = os.path.join(cache, p["package"])
        rec_path = os.path.join(pdir, "record.json")
        if not os.path.exists(rec_path):
            status["not_cached"] += 1
            continue
        with open(rec_path, encoding="utf-8") as f:
            if not json.load(f).get("ok"):
                status["not_ok"] += 1
                continue
        try:
            objs = objects(pdir)
        except Exception as e:
            status["read_error"] += 1
            errors.append(repr(e)[:200])
            continue
        status["read"] += 1
        d = kw.detect(objs)
        if not d["repeat"]:
            continue
        slide = repeat
        repeat += 1
        recs, c, z = slide_records(objs, d["offset"], rng)
        for s in FEATURES:
            counts[s] = [a + b for a, b in zip(counts[s], c[s])]
        for kind in zero:
            zero[kind] = [a + b for a, b in zip(zero[kind], z[kind])]
        for key, rr in recs.items():
            for kind in ("twin", "null"):
                pooled[key][kind][slide] = rr[kind]
    features = {}
    for sheet, feats in FEATURES.items():
        for name, _ in feats:
            r = pooled[(sheet, name)]
            features["%s|%s" % (sheet, name)] = feature_summary(r["twin"], r["null"], args.boot, SEED)
    t3 = read_t3(args.twins_results)
    zero_out = {"twin_table": zero["twin"], "null_table": zero["null"],
                "or_twin": odds_ratio(zero["twin"]), "or_null": odds_ratio(zero["null"])}
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_start)), "seed": SEED,
           "packages": dict(status, listed_v2=len(order)), "errors": errors[:10], "repeat_slides": repeat,
           "twins_T3": t3, "sheets": {s: dict(zip(("objects", "twin_pairs", "null_pairs"), counts[s])) for s in counts},
           "features": features, "zero_tbm": zero_out,
           "grades": grade(features, zero, repeat, t3, args.min_repeat_slides, args.min_pairs),
           "minutes": round((time.time() - t_start) / 60, 1)}
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"packages": res["packages"], "repeat_slides": repeat, "grades": res["grades"],
                      "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
