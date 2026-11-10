#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""compare4: grade stage 4, object-by-object matching of the open HuBMAP glomerulus models' detections with KPMP's
released glomerulus segmentation, split by KPMP's two classes (non-globally-sclerotic and globally sclerotic).

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements findings/kidney-glom-stage4-prereg-v1-2026-11-10.md exactly as written; it was published before any
object position from these slides existed. D objects come from kidney/glom.py >= 0.2.0 (`objects`), K objects from
kidney/kmask.py >= 0.3.0 (`k_objects`); both are [cx, cy, x0, y0, x1, y1, area] in micrometres of the slide's
level-0 frame, after the same 2,000 um^2 floor.

Matching: on each slide, every (D, K) pair whose bounding-box IoU is at least 0.5 is a candidate; candidates are
taken greedily by IoU (highest first; ties by D index, then K index) so that each object is used at most once. K
holds both classes together, non-sclerotic first.

  O1  pooled recall of K's non-sclerotic objects >= 0.70
  O2  pooled precision (share of D objects matched to any K object) >= 0.70
  O3  recall(non-sclerotic) - recall(globally sclerotic) >= 0.20      (only if >= 10 sclerotic objects in all)
  O4  recall(globally sclerotic) <= 0.50                               (only if >= 10 sclerotic objects in all)
  O5  control: D of slide i matched with K of slide i+s, for all n-1 non-zero cyclic shifts s; the mean pooled
      recall over all K objects is <= 0.10. If O5 fails, O1-O4 are reported as uninformative.
  O6  alignment: over matched pairs (at least 20), |median(K cx - D cx)| <= 8 um and |median(K cy - D cy)| <= 8 um

Graded only if at least 10 of the 12 planned slides are complete. grade_o() returns aggregates only (rates, never
counts or per-slide values) and main() refuses any output that names a slide, per the KPMP data use terms. Standard
library only. Usage:
  python -m kidney.compare4 --glom glom.json --k k.json --out compare4.json
"""
import argparse
import json
import statistics

from kidney.compare import check_aggregate, merge

CODE_VERSION = "0.1.0"
N_PLANNED = 12
MIN_COMPLETE = 10
IOU_MIN = 0.5
IOU_LOOSE = 0.3
O1_MIN = 0.70
O2_MIN = 0.70
O3_GAP = 0.20
O4_MAX = 0.50
GS_MIN = 10
O5_MAX = 0.10
O6_MAX_UM = 8.0
O6_MIN_PAIRS = 20
PREDICTIONS = ("o1", "o2", "o3", "o4", "o5", "o6")


def plan_names(n=N_PLANNED):
    """Private slide names used in the job (the stage 3b list): slide3b01 ... slide3b12."""
    return tuple("slide3b%02d" % (i + 1) for i in range(n))


def box_iou(a, b):
    """Intersection over union of the bounding boxes of two objects [cx, cy, x0, y0, x1, y1, area]."""
    ix = min(a[4], b[4]) - max(a[2], b[2])
    iy = min(a[5], b[5]) - max(a[3], b[3])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    union = (a[4] - a[2]) * (a[5] - a[3]) + (b[4] - b[2]) * (b[5] - b[3]) - inter
    return inter / union if union > 0 else 0.0


def match(ds, ks, min_iou=IOU_MIN):
    """Greedy one-to-one matching: [(D index, K index, IoU)] for pairs with IoU >= min_iou, highest IoU first, ties
    by D index then K index."""
    cand = []
    for i, d in enumerate(ds):
        for j, k in enumerate(ks):
            v = box_iou(d, k)
            if v > 0 and v >= min_iou:
                cand.append((-v, i, j))
    cand.sort()
    used_d, used_k, out = set(), set(), []
    for neg, i, j in cand:
        if i in used_d or j in used_k:
            continue
        used_d.add(i)
        used_k.add(j)
        out.append((i, j, -neg))
    return out


def tally(ds, kns, kgs, min_iou=IOU_MIN):
    """Counts and offsets of one slide (local only)."""
    ks = list(kns) + list(kgs)
    m = match(ds, ks, min_iou)
    t = {"d": len(ds), "d_hit": len(m), "ns": len(kns), "ns_hit": 0, "gs": len(kgs), "gs_hit": 0,
         "dx": [], "dy": [], "iou": []}
    for i, j, v in m:
        if j < len(kns):
            t["ns_hit"] += 1
        else:
            t["gs_hit"] += 1
        t["dx"].append(ks[j][0] - ds[i][0])
        t["dy"].append(ks[j][1] - ds[i][1])
        t["iou"].append(v)
    return t


def pool(tallies):
    out = {"d": 0, "d_hit": 0, "ns": 0, "ns_hit": 0, "gs": 0, "gs_hit": 0, "dx": [], "dy": [], "iou": []}
    for t in tallies:
        for key in ("d", "d_hit", "ns", "ns_hit", "gs", "gs_hit"):
            out[key] += t[key]
        for key in ("dx", "dy", "iou"):
            out[key].extend(t[key])
    return out


def rate(a, b):
    return a / float(b) if b else None


def _r3(x):
    return None if x is None else round(x, 3)


def _not_graded(why):
    return {"graded": False, "why": why}


def _complete(r):
    ko = r.get("k_objects")
    return (isinstance(r.get("d_objects"), list) and isinstance(ko, dict)
            and isinstance(ko.get("glom"), list) and isinstance(ko.get("gs"), list))


def shift_recalls(sides):
    """Pooled recall over all K objects when D of slide i is matched with K of slide i+s, for s = 1 .. n-1.
    `sides` is [(ds, ks)]; None if there are no K objects."""
    n = len(sides)
    total_k = sum(len(ks) for _, ks in sides)
    if not total_k:
        return None
    return [sum(len(match(sides[i][0], sides[(i + s) % n][1])) for i in range(n)) / float(total_k)
            for s in range(1, n)]


def grade_o(slides, order=None):
    """Aggregate grades O1-O6 and exploratory rates. `slides` maps a plan slide name to {"d_objects": [...],
    "k_objects": {"glom": [...], "gs": [...]}}. Returns aggregates only."""
    order = tuple(order or plan_names())
    ok = [slides[s] for s in order if s in slides and _complete(slides[s])]
    n = len(ok)
    out = {"code_version": CODE_VERSION, "planned": len(order), "complete": n, "gate": n >= MIN_COMPLETE,
           "iou_min": IOU_MIN}
    if not out["gate"]:
        why = "fewer than %d complete slides" % MIN_COMPLETE
        for o in PREDICTIONS:
            out[o] = _not_graded(why)
        return out

    p = pool([tally(r["d_objects"], r["k_objects"]["glom"], r["k_objects"]["gs"]) for r in ok])
    rec_ns, rec_gs, prec = rate(p["ns_hit"], p["ns"]), rate(p["gs_hit"], p["gs"]), rate(p["d_hit"], p["d"])

    sh = shift_recalls([(r["d_objects"], r["k_objects"]["glom"] + r["k_objects"]["gs"]) for r in ok])
    if sh is None:
        out["o5"] = _not_graded("no KPMP objects")
        informative = None
    else:
        mean_sh = statistics.mean(sh)
        informative = mean_sh <= O5_MAX
        out["o5"] = {"graded": True, "shift_mean_recall": _r3(mean_sh), "shift_max_recall": _r3(max(sh)),
                     "max": O5_MAX, "held": informative}

    if rec_ns is None:
        out["o1"] = _not_graded("no non-sclerotic KPMP objects")
    else:
        out["o1"] = {"graded": True, "recall_ns": _r3(rec_ns), "min": O1_MIN, "held": rec_ns >= O1_MIN,
                     "informative": informative}
    if prec is None:
        out["o2"] = _not_graded("no D objects")
    else:
        out["o2"] = {"graded": True, "precision": _r3(prec), "min": O2_MIN, "held": prec >= O2_MIN,
                     "informative": informative}
    if p["gs"] < GS_MIN or rec_ns is None:
        why = "fewer than %d globally sclerotic objects in all" % GS_MIN if p["gs"] < GS_MIN else "no NS objects"
        out["o3"] = _not_graded(why)
        out["o4"] = _not_graded(why)
    else:
        gap = rec_ns - rec_gs
        out["o3"] = {"graded": True, "recall_gap": _r3(gap), "min": O3_GAP, "held": gap >= O3_GAP,
                     "informative": informative}
        out["o4"] = {"graded": True, "recall_gs": _r3(rec_gs), "max": O4_MAX, "held": rec_gs <= O4_MAX,
                     "informative": informative}

    if len(p["dx"]) < O6_MIN_PAIRS:
        out["o6"] = _not_graded("fewer than %d matched pairs" % O6_MIN_PAIRS)
    else:
        mx, my = statistics.median(p["dx"]), statistics.median(p["dy"])
        out["o6"] = {"graded": True, "median_dx_um": round(mx, 1), "median_dy_um": round(my, 1),
                     "max_um": O6_MAX_UM, "held": abs(mx) <= O6_MAX_UM and abs(my) <= O6_MAX_UM}

    loose = pool([tally(r["d_objects"], r["k_objects"]["glom"], r["k_objects"]["gs"], IOU_LOOSE) for r in ok])
    out["exploratory"] = {
        "recall_gs_at_0_5": _r3(rec_gs),
        "gs_share_of_k": _r3(rate(p["gs"], p["gs"] + p["ns"])),
        "median_iou_matched": _r3(statistics.median(p["iou"])) if p["iou"] else None,
        "iou_0_3": {"recall_ns": _r3(rate(loose["ns_hit"], loose["ns"])),
                    "recall_gs": _r3(rate(loose["gs_hit"], loose["gs"])),
                    "precision": _r3(rate(loose["d_hit"], loose["d"]))},
    }
    out["held"] = sum(1 for o in PREDICTIONS if out[o].get("held") is True)
    return out


def d_objects_side(glom_doc):
    """{slide: {"d_objects": [...]}} for the ok rows of a glom.json that carry `objects` (glom.py >= 0.2.0)."""
    return {r["slide"]: {"d_objects": r["objects"]} for r in glom_doc.get("rows", [])
            if r.get("ok") and isinstance(r.get("objects"), list)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade stage 4 (object matching) from local glom.json and k.json.")
    ap.add_argument("--glom", required=True, help="glom.json from kidney/glom.py >= 0.2.0 (local)")
    ap.add_argument("--k", required=True, help="k.json from kidney/kmask.py >= 0.3.0 (local)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.glom, encoding="utf-8") as f:
        glom_doc = json.load(f)
    with open(a.k, encoding="utf-8") as f:
        k = json.load(f)
    doc = grade_o(merge(d_objects_side(glom_doc), k))
    check_aggregate(doc, names=plan_names())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
