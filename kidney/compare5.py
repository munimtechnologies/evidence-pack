#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""compare5: grade stage 5, a released HuBMAP Deepflash2 kidney U-Net fine-tuned on KPMP's open segmentation of
other biopsies (kidney/gsdet.py), matched object by object with KPMP's released glomerulus segmentation of the 12
frozen stage 3b/4 test slides.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements findings/kidney-glom-stage5-prereg-v1-2026-11-10.md exactly as written; it was published before any
training or test output existed. D objects and their classes come from kidney/gsdet.py `detect` (det5.json), K
objects from kidney/kmask.py >= 0.3.0 (`k_objects`); both are [cx, cy, x0, y0, x1, y1, area] in micrometres of the
slide's level-0 frame after the same 2,000 um^2 floor. Matching is kidney/compare4.py's: bounding-box IoU >= 0.5,
greedy by IoU, one-to-one, both K classes in one pool (non-sclerotic first).

  P1  pooled recall of K's globally sclerotic (GS) objects >= 0.50                 (needs >= 10 GS objects)
  P2  pooled recall of K's non-sclerotic (NS) objects >= 0.734 (stage 4's value for the released weights)
  P3  pooled precision (share of D objects matched to any K object) >= 0.80
  P4  class on matched pairs: share of matched GS objects that D calls GS >= 0.70, and share of matched NS objects
      that D calls NS >= 0.90                                                         (needs >= 10 matched GS)
  P5  pooled GS share: abs(D objects called GS / all D objects - K GS / all K) <= 0.05  (needs >= 10 GS objects)
  P6  control: D of slide i matched with K of slide i+s for all n-1 non-zero cyclic shifts; mean pooled recall over
      all K objects <= 0.10. If P6 fails, P1-P5 are reported as uninformative.

Graded only if at least 10 of the 12 planned slides are complete and the model trained for at least 300 steps.
grade_p() returns aggregates only (rates, never counts or per-slide values) and main() refuses any output that
names a slide, per the KPMP data use terms. Standard library only. Usage:
  python -m kidney.compare5 --det det5.json --k k.json --out compare5.json
"""
import argparse
import json
import statistics

from kidney.compare import check_aggregate, merge
from kidney.compare3b import spearman
from kidney.compare4 import IOU_LOOSE, IOU_MIN, match, plan_names, rate, shift_recalls

CODE_VERSION = "0.1.0"
MIN_COMPLETE = 10
MIN_STEPS = 300
GS_MIN = 10
P1_MIN = 0.50
P2_MIN = 0.734
P3_MIN = 0.80
P4_GS_MIN = 0.70
P4_NS_MIN = 0.90
P4_MIN_PAIRS = 10
P5_MAX = 0.05
P6_MAX = 0.10
BOTH_MIN = 0.70
PREDICTIONS = ("p1", "p2", "p3", "p4", "p5", "p6")
KEYS = ("d", "d_gs", "d_hit", "ns", "ns_hit", "gs", "gs_hit", "gs_as_gs", "ns_as_ns")


def tally5(ds, classes, kns, kgs, min_iou=IOU_MIN):
    """Counts of one slide (local only)."""
    ks = list(kns) + list(kgs)
    m = match(ds, ks, min_iou)
    t = {"d": len(ds), "d_gs": sum(1 for c in classes if c == "gs"), "d_hit": len(m), "ns": len(kns), "ns_hit": 0,
         "gs": len(kgs), "gs_hit": 0, "gs_as_gs": 0, "ns_as_ns": 0, "iou": []}
    for i, j, v in m:
        if j < len(kns):
            t["ns_hit"] += 1
            t["ns_as_ns"] += classes[i] == "ns"
        else:
            t["gs_hit"] += 1
            t["gs_as_gs"] += classes[i] == "gs"
        t["iou"].append(v)
    return t


def pool5(tallies):
    out = {k: 0 for k in KEYS}
    out["iou"] = []
    for t in tallies:
        for k in KEYS:
            out[k] += t[k]
        out["iou"].extend(t["iou"])
    return out


def _r3(x):
    return None if x is None else round(x, 3)


def _not_graded(why):
    return {"graded": False, "why": why}


def _complete(r):
    ko = r.get("k_objects")
    d, c = r.get("d_objects"), r.get("d_classes")
    return (isinstance(d, list) and isinstance(c, list) and len(d) == len(c) and isinstance(ko, dict)
            and isinstance(ko.get("glom"), list) and isinstance(ko.get("gs"), list))


def grade_p(slides, train_steps, order=None):
    """Aggregate grades P1-P6 and exploratory rates. `slides` maps a plan slide name to {"d_objects": [...],
    "d_classes": ["ns" | "gs", ...], "k_objects": {"glom": [...], "gs": [...]}}. Returns aggregates only."""
    order = tuple(order or plan_names())
    ok = [slides[s] for s in order if s in slides and _complete(slides[s])]
    n = len(ok)
    steps_ok = isinstance(train_steps, int) and train_steps >= MIN_STEPS
    out = {"code_version": CODE_VERSION, "planned": len(order), "complete": n, "train_steps": train_steps,
           "gate": n >= MIN_COMPLETE and steps_ok, "iou_min": IOU_MIN}
    if not out["gate"]:
        why = ("fewer than %d complete slides" % MIN_COMPLETE if n < MIN_COMPLETE
               else "fewer than %d training steps" % MIN_STEPS)
        for p in PREDICTIONS:
            out[p] = _not_graded(why)
        return out

    tallies = [tally5(r["d_objects"], r["d_classes"], r["k_objects"]["glom"], r["k_objects"]["gs"]) for r in ok]
    p = pool5(tallies)
    rec_ns, rec_gs, prec = rate(p["ns_hit"], p["ns"]), rate(p["gs_hit"], p["gs"]), rate(p["d_hit"], p["d"])

    sh = shift_recalls([(r["d_objects"], r["k_objects"]["glom"] + r["k_objects"]["gs"]) for r in ok])
    if sh is None:
        out["p6"] = _not_graded("no KPMP objects")
        informative = None
    else:
        mean_sh = statistics.mean(sh)
        informative = mean_sh <= P6_MAX
        out["p6"] = {"graded": True, "shift_mean_recall": _r3(mean_sh), "shift_max_recall": _r3(max(sh)),
                     "max": P6_MAX, "held": informative}

    if p["gs"] < GS_MIN:
        out["p1"] = _not_graded("fewer than %d globally sclerotic objects in all" % GS_MIN)
    else:
        out["p1"] = {"graded": True, "recall_gs": _r3(rec_gs), "min": P1_MIN, "held": rec_gs >= P1_MIN,
                     "informative": informative}
    if rec_ns is None:
        out["p2"] = _not_graded("no non-sclerotic KPMP objects")
    else:
        out["p2"] = {"graded": True, "recall_ns": _r3(rec_ns), "min": P2_MIN, "held": rec_ns >= P2_MIN,
                     "informative": informative}
    if prec is None:
        out["p3"] = _not_graded("no D objects")
    else:
        out["p3"] = {"graded": True, "precision": _r3(prec), "min": P3_MIN, "held": prec >= P3_MIN,
                     "informative": informative}
    if p["gs_hit"] < P4_MIN_PAIRS or not p["ns_hit"]:
        out["p4"] = _not_graded("fewer than %d matched globally sclerotic objects" % P4_MIN_PAIRS
                                if p["gs_hit"] < P4_MIN_PAIRS else "no matched non-sclerotic objects")
    else:
        gs_c, ns_c = p["gs_as_gs"] / float(p["gs_hit"]), p["ns_as_ns"] / float(p["ns_hit"])
        out["p4"] = {"graded": True, "gs_called_gs": _r3(gs_c), "ns_called_ns": _r3(ns_c), "gs_min": P4_GS_MIN,
                     "ns_min": P4_NS_MIN, "held": gs_c >= P4_GS_MIN and ns_c >= P4_NS_MIN,
                     "informative": informative}
    if p["gs"] < GS_MIN or not p["d"]:
        out["p5"] = _not_graded("fewer than %d globally sclerotic objects in all" % GS_MIN
                                if p["gs"] < GS_MIN else "no D objects")
    else:
        share_d, share_k = p["d_gs"] / float(p["d"]), p["gs"] / float(p["gs"] + p["ns"])
        diff = share_d - share_k
        out["p5"] = {"graded": True, "gs_share_d": _r3(share_d), "gs_share_k": _r3(share_k), "diff": _r3(diff),
                     "max_abs": P5_MAX, "held": abs(diff) <= P5_MAX, "informative": informative}

    loose = pool5([tally5(r["d_objects"], r["d_classes"], r["k_objects"]["glom"], r["k_objects"]["gs"], IOU_LOOSE)
                   for r in ok])
    sd, sk = [], []
    for t in tallies:
        if t["d"] and (t["ns"] + t["gs"]):
            sd.append(t["d_gs"] / float(t["d"]))
            sk.append(t["gs"] / float(t["ns"] + t["gs"]))
    rho = spearman(sd, sk)
    out["exploratory"] = {
        "recall_all_k": _r3(rate(p["ns_hit"] + p["gs_hit"], p["ns"] + p["gs"])),
        "both_classes_at_0_70": (rec_ns is not None and rec_gs is not None and rec_ns >= BOTH_MIN
                                 and rec_gs >= BOTH_MIN),
        "median_iou_matched": _r3(statistics.median(p["iou"])) if p["iou"] else None,
        "iou_0_3": {"recall_ns": _r3(rate(loose["ns_hit"], loose["ns"])),
                    "recall_gs": _r3(rate(loose["gs_hit"], loose["gs"])),
                    "precision": _r3(rate(loose["d_hit"], loose["d"]))},
        "spearman_gs_share": _r3(rho),
        "slides_in_spearman": len(sd),
    }
    out["held"] = sum(1 for q in PREDICTIONS if out[q].get("held") is True)
    return out


def det_side(det_doc):
    """{slide: {"d_objects": [...], "d_classes": [...]}} for the ok rows of a det5.json."""
    return {r["slide"]: {"d_objects": r["objects"], "d_classes": r["classes"]} for r in det_doc.get("rows", [])
            if r.get("ok") and isinstance(r.get("objects"), list) and isinstance(r.get("classes"), list)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade stage 5 from local det5.json and k.json.")
    ap.add_argument("--det", required=True, help="det5.json from kidney/gsdet.py detect (local)")
    ap.add_argument("--k", required=True, help="k.json from kidney/kmask.py >= 0.3.0 (local)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.det, encoding="utf-8") as f:
        det = json.load(f)
    with open(a.k, encoding="utf-8") as f:
        k = json.load(f)
    doc = grade_p(merge(det_side(det), k), det.get("train_steps"))
    check_aggregate(doc, names=plan_names())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
