#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""compare: grade the stage-3 plan (HuBMAP glomerulus models vs KPMP's released segmentation) from per-slide counts.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements the predictions of findings/kidney-glom-compare-plan-v0-2026-11-09.md exactly as written, with the rules
for missing slides and boundaries fixed in findings/kidney-glom-compare-plan-v0-addendum-1-2026-11-09.md. Both were
published before any graded slide was processed.

  C1  on at least 3 of the 4 slides, |D - K| <= max(3, 0.25 x K)
  C2  sum(D) / sum(K) in [0.80, 1.25]
  C3  median area of D's glomeruli (pooled) / median area of K's objects (pooled) in [0.70, 1.43],
      graded only if K's areas are in um^2
  C4  shifted pairing (D of 01 with K of 03, 03->04, 04->05, 05->01) leaves fewer slides within the C1 tolerance
      than the true pairing; if not, C1 is reported as uninformative

D comes from kidney/glom.py (glom.json: `glomeruli`, `areas_um2`). K comes from KPMP's masks through count_k(); the
format-specific reader that turns a mask into (kind, area in pixels) objects is added once the package format is
known. The input with per-slide values stays local. grade() returns aggregates only, and check_aggregate() refuses
any output that names a slide, per the KPMP data use terms. Standard library only. Usage:
  python -m kidney.compare --glom glom.json --k k.json [--names names.json] --out compare.json
"""
import argparse
import json
import statistics

CODE_VERSION = "0.1.0"
SLIDES = ("slide01", "slide03", "slide04", "slide05")
MIN_AREA_UM2 = 2000.0
C1_NEEDED = 3
C2_RANGE = (0.80, 1.25)
C3_RANGE = (0.70, 1.43)
GS_MIN = 3
KINDS = ("glom", "gs")


def tolerance(k):
    """The C1 tolerance for a slide with K KPMP objects."""
    return max(3.0, 0.25 * k)


def within(d, k):
    """True when D is within the C1 tolerance of K; a missing side is never within."""
    if d is None or k is None:
        return False
    return abs(d - k) <= tolerance(k)


def shifted(order=SLIDES):
    """(D slide, K slide) pairs of the C4 control: each slide's D with the next slide's K, the last with the first."""
    return [(order[i], order[(i + 1) % len(order)]) for i in range(len(order))]


def in_range(x, bounds):
    return bounds[0] <= x <= bounds[1]


def count_k(objects, mask_mpp=None, min_area_um2=MIN_AREA_UM2):
    """KPMP side of one slide from its glomerulus objects [(kind, area in mask pixels)], kind 'glom'
    (non-globally-sclerotic) or 'gs' (globally sclerotic); other classes must be left out by the reader.
    The area floor is applied only when the mask's pixel size `mask_mpp` (um) is known."""
    k = k_gs = 0
    areas = []
    for kind, area_px in objects:
        if kind not in KINDS:
            raise ValueError("unknown kind: %r" % (kind,))
        if mask_mpp:
            a = area_px * mask_mpp * mask_mpp
            if a < min_area_um2:
                continue
            areas.append(round(a, 1))
        k += 1
        if kind == "gs":
            k_gs += 1
    return {"k": k, "k_gs": k_gs, "floor_applied": bool(mask_mpp), "k_areas_um2": sorted(areas) if mask_mpp else None}


def d_side(glom_doc, names=None):
    """{slide name: {"d": count, "d_areas_um2": [...] or None}} from a glom.json document; failed slides are left
    out. `names` maps glom.json slide names to plan names (slide01 ...)."""
    names = names or {}
    out = {}
    for r in glom_doc.get("rows", []):
        if not r.get("ok"):
            continue
        out[names.get(r["slide"], r["slide"])] = {"d": r["glomeruli"], "d_areas_um2": r.get("areas_um2")}
    return out


def merge(d, k):
    """Per-slide records with both sides' fields (a side may be missing)."""
    out = {}
    for name in set(d) | set(k):
        rec = {}
        rec.update(d.get(name, {}))
        rec.update(k.get(name, {}))
        out[name] = rec
    return out


def _not_graded(why):
    return {"graded": False, "why": why}


def grade(slides, order=SLIDES):
    """Aggregate grade of C1-C4 and the globally-sclerotic note. `slides` maps a plan slide name to
    {"d", "d_areas_um2", "k", "k_gs", "k_areas_um2", "floor_applied"}. Returns aggregates only."""
    rows = [slides.get(s) or {} for s in order]
    complete = all(r.get("d") is not None and r.get("k") is not None for r in rows)
    true_within = sum(within(r.get("d"), r.get("k")) for r in rows)
    out = {"code_version": CODE_VERSION, "slides": len(order), "complete": complete,
           "c1": {"graded": True, "within": true_within, "needed": C1_NEEDED, "held": true_within >= C1_NEEDED,
                  "informative": None}}
    if not complete:
        why = "incomplete: a slide lacks D or K"
        out.update(c2=_not_graded(why), c3=_not_graded(why), c4=_not_graded(why),
                   k_floor_applied=None, gs_note={"reported": False, "why": why})
        return out
    by = dict(zip(order, rows))
    sh_within = sum(within(by[a]["d"], by[b]["k"]) for a, b in shifted(order))
    c4_held = sh_within < true_within
    out["c4"] = {"graded": True, "shifted_within": sh_within, "held": c4_held}
    out["c1"]["informative"] = c4_held

    sd = sum(r["d"] for r in rows)
    sk = sum(r["k"] for r in rows)
    if sk == 0:
        out["c2"] = _not_graded("sum(K) = 0")
    else:
        ratio = sd / float(sk)
        out["c2"] = {"graded": True, "ratio": round(ratio, 3), "range": list(C2_RANGE),
                     "held": in_range(ratio, C2_RANGE)}

    if any(r.get("k_areas_um2") is None for r in rows):
        out["c3"] = _not_graded("KPMP object areas could not be put in um^2")
    elif any(r.get("d_areas_um2") is None for r in rows):
        out["c3"] = _not_graded("glom.json has no per-glomerulus areas (glom.py older than 0.1.1)")
    else:
        da = [a for r in rows for a in r["d_areas_um2"]]
        ka = [a for r in rows for a in r["k_areas_um2"]]
        if not da or not ka:
            out["c3"] = _not_graded("no objects on one side")
        else:
            ratio = statistics.median(da) / float(statistics.median(ka))
            out["c3"] = {"graded": True, "ratio": round(ratio, 3), "range": list(C3_RANGE),
                         "held": in_range(ratio, C3_RANGE)}

    fl = [bool(r.get("floor_applied")) for r in rows]
    out["k_floor_applied"] = "yes" if all(fl) else ("no" if not any(fl) else "mixed")

    sgs = sum(r.get("k_gs") or 0 for r in rows)
    if sgs >= GS_MIN:
        gap_ns = abs(sd - (sk - sgs))
        gap_all = abs(sd - sk)
        closer = "K minus globally sclerotic" if gap_ns < gap_all else ("K" if gap_all < gap_ns else "tie")
        out["gs_note"] = {"reported": True, "closer_to": closer}
    else:
        out["gs_note"] = {"reported": False, "why": "fewer than %d globally sclerotic objects in all" % GS_MIN}
    return out


def check_aggregate(doc, names=SLIDES, extra=()):
    """Raise ValueError if the JSON text of `doc` contains any slide name or other private string."""
    text = json.dumps(doc)
    for s in tuple(names) + tuple(extra):
        if s and s in text:
            raise ValueError("output names a slide or private string")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade the stage-3 plan from local glom.json and KPMP-side counts.")
    ap.add_argument("--glom", required=True, help="glom.json from kidney/glom.py (local)")
    ap.add_argument("--k", required=True, help="JSON {slide name: count_k() output} (local)")
    ap.add_argument("--names", default="", help="JSON {glom.json slide name: plan slide name} (local)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.glom, encoding="utf-8") as f:
        glom_doc = json.load(f)
    with open(a.k, encoding="utf-8") as f:
        k = json.load(f)
    names = {}
    if a.names:
        with open(a.names, encoding="utf-8") as f:
            names = json.load(f)
    doc = grade(merge(d_side(glom_doc, names), k))
    check_aggregate(doc, extra=tuple(names))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
