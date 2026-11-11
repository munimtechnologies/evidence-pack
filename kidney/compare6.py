#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""compare6: grade stage 6. Two models fine-tuned from one released HuBMAP Deepflash2 kidney U-Net with
kidney/gsdet.py 0.2.0 (arm A: the stage 5 recipe unchanged; arm B: the same plus hard negatives mined from arm A's
false detections on the training slides) are matched object by object with KPMP's released glomerulus segmentation
of 12 FRESH open biopsies that no earlier stage has used.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements findings/kidney-glom-stage6-prereg-v1-2026-11-11.md exactly as written; it was published before any
stage 6 training or test output existed. Objects, matching (box IoU >= 0.5, greedy, one-to-one, both K classes in
one pool) and per-slide tallies are kidney/compare5.py's. Both arms are graded on the same slides: those complete
for both arms.

  Q1  arm A pooled recall of K's globally sclerotic (GS) objects >= 0.80        (needs >= 10 GS objects)
  Q2  arm A pooled precision < 0.80 (stage 5's precision failure replicates on fresh biopsies)
  Q3  arm B pooled precision >= 0.80
  Q4  arm B pooled recall of K's GS objects >= 0.80                             (needs >= 10 GS objects)
  Q5  arm B pooled recall of K's non-sclerotic (NS) objects >= 0.85
  Q6  arm B abs(share of D objects called GS - share of K objects that are GS) <= 0.05 (needs >= 10 GS objects)
  Q7  arm B precision - arm A precision >= 0.05
  Q8  control: for each arm, D of slide i matched with K of slide i+s for all n-1 non-zero cyclic shifts; mean
      pooled recall over all K objects <= 0.10 for both arms. If Q8 fails, Q1-Q7 are reported as uninformative.

Graded only if at least 10 of the 12 planned slides are complete for both arms and each arm trained for at least 300
steps. Rates are graded unrounded and published to three decimals. grade() returns aggregates only (rates, never
counts or per-slide values) and main() refuses any output that names a slide, per the KPMP data use terms.
Standard library only. Usage:
  python -m kidney.compare6 --det-a detA.json --det-b detB.json --k k6.json --out compare6.json
"""
import argparse
import json
import statistics

from kidney import compare5
from kidney.compare import check_aggregate, merge
from kidney.compare4 import IOU_LOOSE, IOU_MIN, rate, shift_recalls

CODE_VERSION = "0.1.0"
N_PLANNED = 12
PREFIX = "test6"
MIN_COMPLETE = 10
MIN_STEPS = 300
GS_MIN = 10
Q1_MIN = 0.80
Q2_BELOW = 0.80
Q3_MIN = 0.80
Q4_MIN = 0.80
Q5_MIN = 0.85
Q6_MAX = 0.05
Q7_GAIN = 0.05
Q8_MAX = 0.10
PREDICTIONS = ("q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8")


def plan_names6(n=N_PLANNED):
    """Private slide names used in the job (the fresh stage 6 list): test601 ... test612."""
    return tuple("%s%02d" % (PREFIX, i + 1) for i in range(n))


def _r3(x):
    return None if x is None else round(x, 3)


def _not_graded(why):
    return {"graded": False, "why": why}


def common_slides(a, b, order):
    """Plan slides complete (D, classes and K) for both arms, in plan order."""
    return [s for s in order if s in a and s in b and compare5._complete(a[s]) and compare5._complete(b[s])]


def arm_raw(slides, order, min_iou=IOU_MIN):
    """Unrounded pooled rates of one arm over the slides `order` (local; includes the GS object count used only
    for the >= 10 floor)."""
    rows = [slides[s] for s in order]
    t = [compare5.tally5(r["d_objects"], r["d_classes"], r["k_objects"]["glom"], r["k_objects"]["gs"], min_iou)
         for r in rows]
    p = compare5.pool5(t)
    sh = shift_recalls([(r["d_objects"], r["k_objects"]["glom"] + r["k_objects"]["gs"]) for r in rows])
    return {"recall_gs": rate(p["gs_hit"], p["gs"]), "recall_ns": rate(p["ns_hit"], p["ns"]),
            "recall_all": rate(p["gs_hit"] + p["ns_hit"], p["gs"] + p["ns"]),
            "precision": rate(p["d_hit"], p["d"]), "share_d": rate(p["d_gs"], p["d"]),
            "share_k": rate(p["gs"], p["gs"] + p["ns"]), "gs_call_precision": rate(p["gs_as_gs"], p["d_gs"]),
            "gs_called_gs": rate(p["gs_as_gs"], p["gs_hit"]), "ns_called_ns": rate(p["ns_as_ns"], p["ns_hit"]),
            "median_iou": statistics.median(p["iou"]) if p["iou"] else None,
            "shift": statistics.mean(sh) if sh else None, "gs_k": p["gs"], "d": p["d"]}


def _public(raw, loose):
    """Rounded rates of one arm for the published output (no counts)."""
    keys = ("recall_gs", "recall_ns", "recall_all", "precision", "share_d", "share_k", "gs_call_precision",
            "gs_called_gs", "ns_called_ns", "median_iou", "shift")
    out = {k: _r3(raw[k]) for k in keys}
    out["iou_0_3"] = {"recall_gs": _r3(loose["recall_gs"]), "recall_ns": _r3(loose["recall_ns"]),
                      "precision": _r3(loose["precision"])}
    return out


def _q(value, held, informative, **bounds):
    out = {"graded": True, "value": _r3(value), "held": held, "informative": informative}
    out.update(bounds)
    return out


def grade(slides_a, slides_b, steps_a, steps_b, order=None):
    """Aggregate grades Q1-Q8 and exploratory rates. Each `slides_*` maps a plan slide name to {"d_objects": [...],
    "d_classes": ["ns" | "gs", ...], "k_objects": {"glom": [...], "gs": [...]}}. Returns aggregates only."""
    order = tuple(order or plan_names6())
    common = common_slides(slides_a, slides_b, order)
    n = len(common)
    steps_ok = all(isinstance(s, int) and s >= MIN_STEPS for s in (steps_a, steps_b))
    out = {"code_version": CODE_VERSION, "planned": len(order), "complete_both": n, "train_steps_a": steps_a,
           "train_steps_b": steps_b, "gate": n >= MIN_COMPLETE and steps_ok, "iou_min": IOU_MIN}
    if not out["gate"]:
        why = ("fewer than %d slides complete for both arms" % MIN_COMPLETE if n < MIN_COMPLETE
               else "fewer than %d training steps in an arm" % MIN_STEPS)
        for q in PREDICTIONS:
            out[q] = _not_graded(why)
        out["held"] = 0
        return out

    a, b = arm_raw(slides_a, common), arm_raw(slides_b, common)
    gs_ok = a["gs_k"] >= GS_MIN
    no_gs = "fewer than %d globally sclerotic objects in all" % GS_MIN

    if a["shift"] is None or b["shift"] is None:
        out["q8"] = _not_graded("no KPMP objects")
        inf = None
    else:
        inf = max(a["shift"], b["shift"]) <= Q8_MAX
        out["q8"] = {"graded": True, "shift_mean_recall_a": _r3(a["shift"]), "shift_mean_recall_b": _r3(b["shift"]),
                     "max": Q8_MAX, "held": inf}

    out["q1"] = (_q(a["recall_gs"], a["recall_gs"] >= Q1_MIN, inf, min=Q1_MIN) if gs_ok else _not_graded(no_gs))
    out["q2"] = (_q(a["precision"], a["precision"] < Q2_BELOW, inf, below=Q2_BELOW) if a["precision"] is not None
                 else _not_graded("no arm A detections"))
    out["q3"] = (_q(b["precision"], b["precision"] >= Q3_MIN, inf, min=Q3_MIN) if b["precision"] is not None
                 else _not_graded("no arm B detections"))
    out["q4"] = (_q(b["recall_gs"], b["recall_gs"] >= Q4_MIN, inf, min=Q4_MIN) if gs_ok else _not_graded(no_gs))
    out["q5"] = (_q(b["recall_ns"], b["recall_ns"] >= Q5_MIN, inf, min=Q5_MIN) if b["recall_ns"] is not None
                 else _not_graded("no non-sclerotic KPMP objects"))
    if not gs_ok:
        out["q6"] = _not_graded(no_gs)
    elif b["share_d"] is None:
        out["q6"] = _not_graded("no arm B detections")
    else:
        diff = b["share_d"] - b["share_k"]
        out["q6"] = _q(diff, abs(diff) <= Q6_MAX, inf, max_abs=Q6_MAX, gs_share_d=_r3(b["share_d"]),
                       gs_share_k=_r3(b["share_k"]))
    if a["precision"] is None or b["precision"] is None:
        out["q7"] = _not_graded("an arm has no detections")
    else:
        gain = b["precision"] - a["precision"]
        out["q7"] = _q(gain, gain >= Q7_GAIN, inf, min_gain=Q7_GAIN)

    out["gs_floor_met"] = gs_ok
    out["arm_a"] = _public(a, arm_raw(slides_a, common, IOU_LOOSE))
    out["arm_b"] = _public(b, arm_raw(slides_b, common, IOU_LOOSE))
    out["held"] = sum(1 for q in PREDICTIONS if out[q].get("held") is True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade stage 6 from local detection files of both arms and k.json.")
    ap.add_argument("--det-a", required=True, help="arm A detections from kidney/gsdet.py detect (local)")
    ap.add_argument("--det-b", required=True, help="arm B detections from kidney/gsdet.py detect (local)")
    ap.add_argument("--k", required=True, help="k.json from kidney/kmask.py >= 0.3.0 (local)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    docs = []
    for path in (a.det_a, a.det_b, a.k):
        with open(path, encoding="utf-8") as f:
            docs.append(json.load(f))
    det_a, det_b, k = docs
    doc = grade(merge(compare5.det_side(det_a), k), merge(compare5.det_side(det_b), k), det_a.get("train_steps"),
                det_b.get("train_steps"))
    check_aggregate(doc, names=plan_names6())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
