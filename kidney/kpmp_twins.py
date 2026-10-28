#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_twins: how often does KPMP's v2 pathomics release measure the same object twice, once in each
serial section on a slide?

Pre-registration: findings/kpmp-twins-prereg-v1-2026-10-28.md.

The visual check of the 30 most extreme objects (findings/kpmp-patches-results-v1-2026-10-28.md) found
6 pairs of the same tubule or artery in two sections of one slide, and that the boxes' x columns index
image rows. This census looks for such repeats on every cached v2 slide, from workbook boxes only:
  1. Landmarks are glomeruli, sclerotic glomeruli and arteries. Every pair of landmarks of one sheet
     whose box height and width agree within SIZE_TOL gives a displacement, its sign fixed so the
     column part is positive, kept if it is at least MIN_SHIFT pixels long.
  2. Displacements are binned at BIN pixels. The mode is the bin holding the most displacements in it
     and its 8 neighbours. Null: the same mode after shuffling box sizes among the landmarks of each
     sheet, NULL_SHUFFLES times (seeded). A slide has a repeated section if its mode is at least
     MIN_PAIRS and larger than every null mode.
  3. The offset is the median displacement in the mode. In every sheet, an object has a twin if an
     object of the same sheet and size sits within TOL pixels of its centre plus or minus the offset.
Only the dominant offset is used, so slides with three or more sections are undercounted.

Reads only the data volume (run kidney.kpmp_fill first). results.json holds aggregates; slides.json
names packages and stays with the job. Standard library only. Usage:
  python -m kidney.kpmp_twins --file-list inputs/kpmp-segmentation-files.csv \
      --controls inputs/twin-controls.json --data-dir /data --out-dir /out/twins
"""
import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_census3 as k3

PREREG = "findings/kpmp-twins-prereg-v1-2026-10-28.md"
CODE_VERSION = "1.0"
SEED = 20261028
SHEETS = ("gloms", "s_gloms", "tubs", "arts")
LANDMARKS = ("gloms", "s_gloms", "arts")
BOX = ("x1", "x2", "y1", "y2")
SIZE_TOL = 0.15
MIN_SHIFT = 2000
BIN = 250
MIN_PAIRS = 5
NULL_SHUFFLES = 20
TOL = 500
MIN_LANDMARKS = 10
MIN_GLOMS = 5
MIN_SLIDES = 150
MIN_REPEAT_SLIDES = 10
MIN_CONTROLS = 3
CONTROL_TOL = 1000
T1_SHARE, T2_SHARE = 0.5, 0.3


def objects(path):
    """{sheet: [(row, col, height, width)]} from one cached v2 package folder: box centres and sizes in
    image pixels, reading x as the row axis. Rows without a valid box are skipped."""
    out = {s: [] for s in SHEETS}
    for fn in sorted(os.listdir(path)):
        if kc.ext_of(fn) != "xlsx":
            continue
        for key, sheet in k3.book_sheets3(os.path.join(path, fn), fn, "v2").items():
            if key not in out:
                continue
            header, data = kc.sheet_table(sheet)
            idx = {k2.col_key(h): j for j, h in enumerate(header)}
            if not all(b in idx for b in BOX):
                continue
            for r in data:
                x1, x2, y1, y2 = (k2._cell(r, idx[b]) for b in BOX)
                if None in (x1, x2, y1, y2) or x2 < x1 or y2 < y1:
                    continue
                out[key].append(((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1))
    return out


def same_size(a, b, tol=SIZE_TOL):
    return abs(a[2] - b[2]) <= tol * max(a[2], b[2], 1) and abs(a[3] - b[3]) <= tol * max(a[3], b[3], 1)


def displacements(objs, sizes=None):
    """[(d_row, d_col)] over same-size pairs of one sheet's objects, signed so d_col > 0 (or d_col == 0
    and d_row >= 0), at least MIN_SHIFT long. sizes, if given, replaces each object's (height, width)."""
    if sizes is not None:
        objs = [(t[0], t[1]) + tuple(s) for t, s in zip(objs, sizes)]
    out = []
    for i in range(len(objs)):
        a = objs[i]
        for j in range(i + 1, len(objs)):
            b = objs[j]
            if not same_size(a, b):
                continue
            dr, dc = b[0] - a[0], b[1] - a[1]
            if dc < 0 or (dc == 0 and dr < 0):
                dr, dc = -dr, -dc
            if dr * dr + dc * dc >= MIN_SHIFT * MIN_SHIFT:
                out.append((dr, dc))
    return out


def mode(disps):
    """(count, displacements) of the BIN-pixel bin whose 3 x 3 neighbourhood holds the most."""
    bins = defaultdict(list)
    for d in disps:
        bins[(int(d[0] // BIN), int(d[1] // BIN))].append(d)
    best, key = 0, None
    for br, bc in bins:
        c = sum(len(bins.get((br + i, bc + j), ())) for i in (-1, 0, 1) for j in (-1, 0, 1))
        if c > best:
            best, key = c, (br, bc)
    if key is None:
        return 0, []
    return best, [d for i in (-1, 0, 1) for j in (-1, 0, 1) for d in bins.get((key[0] + i, key[1] + j), ())]


def landmark_disps(objs, rng=None):
    """Displacements over the landmark sheets; with rng, sizes are first shuffled within each sheet."""
    out = []
    for s in LANDMARKS:
        o = objs.get(s, [])
        sizes = None
        if rng is not None:
            sizes = [(t[2], t[3]) for t in o]
            rng.shuffle(sizes)
        out.extend(displacements(o, sizes))
    return out


def detect(objs, seed=SEED, shuffles=NULL_SHUFFLES):
    """{"landmarks", "mode", "null_max", "repeat", "offset"} for one slide; offset only if repeat."""
    m, pairs = mode(landmark_disps(objs))
    rng = random.Random(seed)
    null_max = max([mode(landmark_disps(objs, rng))[0] for _ in range(shuffles)] or [0])
    repeat = m >= MIN_PAIRS and m > null_max
    offset = [statistics.median(d[0] for d in pairs), statistics.median(d[1] for d in pairs)] if repeat else None
    return {"landmarks": sum(len(objs.get(s, [])) for s in LANDMARKS), "mode": m, "null_max": null_max,
            "repeat": repeat, "offset": offset}


def _partner(o, grid, k, r, c, tol):
    gr, gc = int(r // tol), int(c // tol)
    return any(m != k and (o[m][0] - r) ** 2 + (o[m][1] - c) ** 2 <= tol * tol and same_size(o[k], o[m])
               for i in (-1, 0, 1) for j in (-1, 0, 1) for m in grid.get((gr + i, gc + j), ()))


def twins(objs, offset, tol=TOL):
    """{sheet: [objects, with a twin]}: a twin is an object of the same sheet and size whose centre is
    within tol of this object's centre plus or minus offset."""
    out = {}
    for s in SHEETS:
        o = objs.get(s, [])
        grid = defaultdict(list)
        for k, t in enumerate(o):
            grid[(int(t[0] // tol), int(t[1] // tol))].append(k)
        n = sum(1 for k, t in enumerate(o)
                if any(_partner(o, grid, k, t[0] + sg * offset[0], t[1] + sg * offset[1], tol) for sg in (1, -1)))
        out[s] = [len(o), n]
    return out


def offset_error(found, expected):
    """Distance from found to expected or to -expected, whichever is nearer."""
    return min(((found[0] - sg * expected[0]) ** 2 + (found[1] - sg * expected[1]) ** 2) ** 0.5 for sg in (1, -1))


def summarise(slides, min_slides=MIN_SLIDES):
    evaluable = [s for s in slides if s["landmarks"] >= MIN_LANDMARKS]
    rep = [s for s in evaluable if s["repeat"]]
    out = {"read": len(slides), "evaluable": len(evaluable), "repeat": len(rep),
           "repeat_share": len(rep) / len(evaluable) if evaluable else None, "gate": len(evaluable) >= min_slides,
           "mode_median": {"repeat": kc._median([s["mode"] for s in rep]),
                           "other": kc._median([s["mode"] for s in evaluable if not s["repeat"]])},
           "offset_length_median": kc._median([(s["offset"][0] ** 2 + s["offset"][1] ** 2) ** 0.5 for s in rep]),
           "sheets": {}}
    for sh in SHEETS:
        shares = [s["twins"][sh][1] / s["twins"][sh][0] for s in rep
                  if s["twins"][sh][0] >= (MIN_GLOMS if sh in LANDMARKS else MIN_LANDMARKS)]
        objects_all = sum(s["counts"][sh] for s in slides)
        with_twin = sum(s["twins"][sh][1] for s in rep)
        out["sheets"][sh] = {"objects_all_slides": objects_all,
                             "objects_repeat_slides": sum(s["twins"][sh][0] for s in rep),
                             "with_twin": with_twin, "slide_median_share": kc._median(shares),
                             "slides_in_median": len(shares),
                             "count_inflation": (objects_all / (objects_all - with_twin / 2))
                             if objects_all > with_twin / 2 else None}
    return out


def check_controls(slides, controls):
    by_pkg = {s["package"]: s for s in slides}
    out = []
    for c in controls:
        s = by_pkg.get(c["package"])
        row = {"read": s is not None, "repeat": bool(s and s["repeat"]), "error_px": None, "ok": False}
        if s and s["repeat"]:
            row["error_px"] = round(offset_error(s["offset"], c["offset"]), 1)
            row["ok"] = row["error_px"] <= CONTROL_TOL
        out.append(row)
    return out


def grade(summary, ctrl):
    if not summary["gate"]:
        return {"T1_repeat_share": "pending", "T2_glom_twin_share": "pending", "T3_controls": "pending",
                "status": "incomplete"}
    g = {"T1_repeat_share": "pass" if summary["repeat_share"] >= T1_SHARE else "fail"}
    glom = summary["sheets"]["gloms"]
    if glom["slides_in_median"] < MIN_REPEAT_SLIDES:
        g["T2_glom_twin_share"] = "untestable"
    else:
        g["T2_glom_twin_share"] = "pass" if glom["slide_median_share"] >= T2_SHARE else "fail"
    read = [c for c in ctrl if c["read"]]
    if len(read) < MIN_CONTROLS:
        g["T3_controls"] = "untestable"
    else:
        g["T3_controls"] = "pass" if sum(c["ok"] for c in read) >= len(read) - 1 else "fail"
    g["status"] = "complete"
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--controls", default="")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out/twins")
    ap.add_argument("--min-slides", type=int, default=MIN_SLIDES)
    args = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    controls = []
    if args.controls and os.path.exists(args.controls):
        with open(args.controls, encoding="utf-8") as f:
            controls = json.load(f)["controls"]
    order = [p for p in kc.census_order(kc.load_packages(args.file_list)) if p["version"] == "v2"]
    slides, status, errors = [], Counter(), []
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
        d = detect(objs)
        d["package"] = p["package"]
        d["counts"] = {s: len(objs[s]) for s in SHEETS}
        d["twins"] = twins(objs, d["offset"]) if d["repeat"] else {s: [len(objs[s]), 0] for s in SHEETS}
        slides.append(d)
    summary = summarise(slides, args.min_slides)
    ctrl = check_controls(slides, controls)
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_start)), "seed": SEED,
           "packages": dict(status, listed_v2=len(order)), "errors": errors[:10], "summary": summary,
           "controls": [{k: c[k] for k in ("read", "repeat", "error_px", "ok")} for c in ctrl],
           "grades": grade(summary, ctrl), "minutes": round((time.time() - t_start) / 60, 1)}
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(args.out_dir, "slides.json"), "w", encoding="utf-8") as f:
        json.dump(slides, f)
    print(json.dumps({"packages": res["packages"], "repeat_share": summary["repeat_share"], "grades": res["grades"],
                      "minutes": res["minutes"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
