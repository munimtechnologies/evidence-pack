#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""d2: grader of the pre-registered D2 lane of MV2's open entry for the NIDDK Kidney AI Discovery Challenge:
rank glomeruli that KPMP's own segmentation calls non-sclerotic by how far they sit from a reference of normal
glomeruli, then ask whether a participant's share of such unusual glomeruli goes with open clinical fields beyond
what the globally sclerotic (GS) share already explains.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical
device, not for diagnosis or patient care. Implements findings/kidney-d2-prereg-v1-2026-11-12.md, written before any
D2 output existed. Prior art it builds on (cited, not copied): NoRDeC (Hasko et al., arXiv 2609.19444, 2026), the
normal-reference Mahalanobis idea; GloPath (He et al., arXiv 2603.02926, 2026), KPMP morphometry vs clinical fields.

Inputs (all local; KPMP data use terms):
  --emb      embedding document of kidney/emb.py `run` (objects, classes, `emb` and `base` vectors, `clipped`)
  --k        k.json of kidney/kmask.py >= 0.3.0 (KPMP's released segmentation: `k_objects` {"glom", "gs"})
  --groups   JSON {slide name: participant}
  --train    JSON [participant, ...] whose slides trained the detector (always in the reference split)
  --clinical JSON {participant: {field: code}} or --clinical-csv (KPMP open clinical file, coded by
             kidney/kpmp_q2.py `clinical_table`)
Steps, each fixed in the pre-registration:
  1. Label: every detected object is matched one to one with KPMP's objects of the same slide (kidney/compare4.py
     `match`, box IoU >= 0.5, non-sclerotic list first): label "ns", "gs" or None (no KPMP object).
  2. Split: participants are sorted, shuffled with random.Random(SEED); the first ceil(30%) of those not in --train,
     plus every --train participant present, form the reference split; the rest are the evaluation split.
  3. Score (per feature kind, "emb" and the hand-crafted "base"): columns standardized with the mean and population
     SD of the reference rows (KPMP "ns", not clipped, reference participants), then the Mahalanobis distance from
     those rows with shrinkage SHRINK (kidney/anom.py `mahalanobis_np`).
  4. On evaluation participants, unclipped objects only:
     G1  AUROC of the emb score for KPMP "gs" vs KPMP "ns" >= 0.80 (the positive control; needs >= 30 "gs").
         If G1 does not pass, every other reading is reported as uninformative.
     R1  emb AUROC - base AUROC >= 0.05 (enrichment over the baseline method).
     Discovery set: objects KPMP labels "ns" AND the detector calls "ns". Top set: the top 5% of their emb scores.
     R2  no participant holds more than 20% of the top set.
     Burden: each participant's share of its discovery-set objects in the top set (>= 5 such objects).
     R3  partial Spearman of burden vs each open clinical field in FIELDS, controlling KPMP's label-derived GS share,
         two-sided shuffle p (N_PERM shuffles, SEED), Holm across the graded fields (>= 50 participants each):
         passes if any field has Holm p < 0.05. The base side is computed the same way and reported, not graded.
  The whole lane is "not graded" with fewer than 50 evaluation participants.
Output: rates, AUROCs, correlations, p-values and participant numbers only; never names, per-object or
per-participant values (main() refuses any output containing a slide or participant name).
Usage:
  python -m kidney.d2 --emb emb.json --k k.json --groups groups.json --train train.json \\
      --clinical-csv clinical.csv --out d2.json [--n-perm 9999]
"""
import argparse
import json
import math
import random

from kidney import anom
from kidney.compare import check_aggregate
from kidney.compare4 import IOU_MIN, match

CODE_VERSION = "0.1.0"
PREREG = "findings/kidney-d2-prereg-v1-2026-11-12.md"
SEED = 11
REF_PERMILLE = 300
SHRINK = 0.1
TOP_PERMILLE = 50
GATE_AUROC = 0.80
R1_MARGIN = 0.05
CONC_MAX = 0.20
ALPHA = 0.05
MIN_GS = 30
MIN_EVAL = 50
MIN_ELIGIBLE = 5
MIN_FIELD_N = 50
N_PERM = 9999
EPS = 1e-9
FIELDS = ("egfr", "proteinuria", "albuminuria", "a1c", "diabetes", "hypertension")
READINGS = ("g1", "r1", "r2", "r3")
ND = 4


def kpmp_labels(ds, kobj, min_iou=IOU_MIN):
    """Per detected object: "ns" / "gs" when matched one to one with a KPMP object of that class, else None.
    kobj is kmask's {"glom": [...], "gs": [...]} (or None)."""
    if not kobj:
        return [None] * len(ds)
    kns = list(kobj.get("glom") or [])
    kgs = list(kobj.get("gs") or [])
    out = [None] * len(ds)
    for i, j, _ in match(ds, kns + kgs, min_iou):
        out[i] = "ns" if j < len(kns) else "gs"
    return out


def split(pids, train, seed=SEED, permille=REF_PERMILLE):
    """(reference, evaluation) sorted participant lists. Reference = the --train participants present in pids plus
    the first ceil(n * permille / 1000) of the other participants after a seeded shuffle of their sorted list."""
    pset = set(pids)
    tr = set(train) & pset
    rest = sorted(pset - tr)
    random.Random(seed).shuffle(rest)
    m = (len(rest) * permille + 999) // 1000
    return sorted(tr | set(rest[:m])), sorted(rest[m:])


def collect(emb_doc, k_doc, groups, kind="emb"):
    """(objects, skipped). objects: {"group", "x", "det", "lab", "clipped"} for every object of every successful
    slide that has a group and a `kind` vector. PRIVATE: keep local."""
    objs, skipped = [], {"no_group": 0, "no_vector": 0, "no_k": 0}
    for r in emb_doc.get("rows", []):
        if not r.get("ok"):
            continue
        g = groups.get(r["slide"])
        ds = r.get("objects") or []
        kobj = (k_doc.get(r["slide"]) or {}).get("k_objects")
        labs = kpmp_labels(ds, kobj)
        vecs = r.get(kind) or []
        classes = r.get("classes") or []
        clip = r.get("clipped") or []
        for j in range(len(ds)):
            v = vecs[j] if j < len(vecs) else None
            if g is None:
                skipped["no_group"] += 1
                continue
            if v is None:
                skipped["no_vector"] += 1
                continue
            if not kobj:
                skipped["no_k"] += 1
            objs.append({"group": g, "x": list(v), "det": classes[j] if j < len(classes) else None,
                         "lab": labs[j], "clipped": bool(clip[j]) if j < len(clip) else False})
    return objs, skipped


def gs_share(k_doc, groups):
    """{participant: KPMP label-derived GS share over all its slides} (participants with >= 1 KPMP object)."""
    tot, gs = {}, {}
    for s, kd in k_doc.items():
        g = groups.get(s)
        kobj = (kd or {}).get("k_objects")
        if g is None or not kobj:
            continue
        a = len(kobj.get("gs") or [])
        tot[g] = tot.get(g, 0) + a + len(kobj.get("glom") or [])
        gs[g] = gs.get(g, 0) + a
    return {g: gs[g] / tot[g] for g in tot if tot[g] > 0}


def ref_standardize(ref_rows, rows):
    """rows standardized with the reference rows' column means and population SDs (a constant column -> 0.0)."""
    n, d = len(ref_rows), len(ref_rows[0])
    mu = [sum(r[j] for r in ref_rows) / n for j in range(d)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in ref_rows) / n) for j in range(d)]
    return [[(r[j] - mu[j]) / sd[j] if sd[j] > 0 else 0.0 for j in range(d)] for r in rows]


def reference_rows(objs, ref):
    refset = set(ref)
    return [o["x"] for o in objs if o["group"] in refset and o["lab"] == "ns" and not o["clipped"]]


def ref_scores(objs, ref, shrink=SHRINK):
    """Normal-reference Mahalanobis score of every object (numpy)."""
    rr = reference_rows(objs, ref)
    if len(rr) < 2:
        raise ValueError("fewer than 2 reference rows")
    z_ref = ref_standardize(rr, rr)
    z_all = ref_standardize(rr, [o["x"] for o in objs])
    return anom.mahalanobis_np(z_ref, z_all, shrink)


def field_tests(bur, share, clinical, n_perm=N_PERM, seed=SEED, min_n=MIN_FIELD_N):
    """{field: {"n", "graded", "partial_rho", "p", "holm_p"}}: partial Spearman of burden vs field controlling GS
    share over participants (sorted) that have all three; Holm across graded fields in FIELDS order."""
    out = {}
    for f in FIELDS:
        ps = sorted(g for g in bur if g in share and (clinical.get(g) or {}).get(f) is not None)
        if len(ps) < min_n:
            out[f] = {"n": len(ps), "graded": False}
            continue
        x = [bur[g] for g in ps]
        y = [clinical[g][f] for g in ps]
        z = [share[g] for g in ps]
        r, p = anom.perm_p(x, y, z, n_perm, seed)
        out[f] = {"n": len(ps), "graded": r is not None, "partial_rho": r, "p": p}
    graded = [f for f in FIELDS if out[f]["graded"]]
    for f, a in zip(graded, anom.holm([out[f]["p"] for f in graded])):
        out[f]["holm_p"] = a
    return out


def side(objs, scores, ev, share, clinical, n_perm=N_PERM, seed=SEED, permille=TOP_PERMILLE, min_gs=MIN_GS,
         min_eligible=MIN_ELIGIBLE, min_field_n=MIN_FIELD_N):
    """Aggregate readings of one feature kind on the evaluation participants (no names, no per-object values)."""
    evs = set(ev)
    use = [i for i, o in enumerate(objs) if o["group"] in evs and not o["clipped"] and scores[i] is not None]
    lab = [(scores[i], 1 if objs[i]["lab"] == "gs" else 0) for i in use if objs[i]["lab"] in ("gs", "ns")]
    n_gs = sum(v for _, v in lab)
    au = anom.auroc([s for s, _ in lab], [v for _, v in lab]) if n_gs >= min_gs and len(lab) > n_gs else None
    disc = [i for i in use if objs[i]["lab"] == "ns" and objs[i]["det"] == "ns"]
    d_scores = [scores[i] for i in disc]
    d_groups = [objs[i]["group"] for i in disc]
    conc = anom.concentration(d_scores, d_groups, permille)
    counts = {}
    for g in d_groups:
        counts[g] = counts.get(g, 0) + 1
    bur = {g: b for g, b in anom.burden(d_scores, d_groups, permille).items() if counts[g] >= min_eligible}
    return {"auroc_gs_vs_ns": au, "top_concentration": conc,
            "burden_participants": len(bur),
            "fields": field_tests(bur, share, clinical, n_perm, seed, min_field_n)}


def readings(n_eval, emb, base, min_eval=MIN_EVAL):
    """{"g1".."r3": "pass" / "fail" / "not graded", "informative": bool} from the two sides."""
    if n_eval < min_eval:
        out = {r: "not graded" for r in READINGS}
        out["informative"] = False
        return out

    def pf(ok):
        return "pass" if ok else "fail"
    a, b = emb["auroc_gs_vs_ns"], base["auroc_gs_vs_ns"]
    out = {"g1": "not graded" if a is None else pf(a >= GATE_AUROC - EPS),
           "r1": "not graded" if a is None or b is None else pf(a - b >= R1_MARGIN - EPS),
           "r2": "not graded" if emb["top_concentration"] is None else pf(emb["top_concentration"] <= CONC_MAX + EPS)}
    graded = [f for f in FIELDS if emb["fields"][f]["graded"]]
    out["r3"] = "not graded" if not graded else pf(any(emb["fields"][f]["holm_p"] < ALPHA for f in graded))
    out["informative"] = out["g1"] == "pass"
    return out


def _round(x):
    if isinstance(x, float):
        return round(x, ND)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def coverage(objs, ev):
    """Shares of evaluation-split objects that are clipped / have no KPMP label (None without objects)."""
    evs = set(ev)
    e = [o for o in objs if o["group"] in evs]
    if not e:
        return {"share_clipped_eval": None, "share_unlabelled_eval": None}
    return {"share_clipped_eval": sum(1 for o in e if o["clipped"]) / len(e),
            "share_unlabelled_eval": sum(1 for o in e if o["lab"] is None) / len(e)}


def grade(emb_doc, k_doc, groups, train, clinical, n_perm=N_PERM, seed=SEED, score_fn=ref_scores, min_eval=MIN_EVAL,
          side_args=None):
    """The public D2 document (aggregates only). The split is drawn once, from the participants with emb vectors."""
    share = gs_share(k_doc, groups)
    sides, info = {}, {}
    objs_e, _ = collect(emb_doc, k_doc, groups, "emb")
    ref, ev = split({o["group"] for o in objs_e}, train, seed)
    for kind in ("emb", "base"):
        objs = objs_e if kind == "emb" else collect(emb_doc, k_doc, groups, kind)[0]
        scores = score_fn(objs, ref)
        sides[kind] = side(objs, scores, ev, share, clinical, n_perm, seed, **(side_args or {}))
        info[kind] = coverage(objs, ev)
    rd = readings(len(ev), sides["emb"], sides["base"], min_eval)
    return _round({"code_version": CODE_VERSION, "prereg": PREREG, "emb_code_version": emb_doc.get("code_version"),
                   "gsdet_code_version": emb_doc.get("gsdet"), "anom_code_version": anom.CODE_VERSION,
                   "n_ref_participants": len(ref), "n_eval_participants": len(ev), "n_perm": n_perm, "seed": seed,
                   "emb": sides["emb"], "base": sides["base"], "coverage": info, "readings": rd})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade the pre-registered D2 lane (aggregate output only).")
    ap.add_argument("--emb", required=True)
    ap.add_argument("--k", required=True)
    ap.add_argument("--groups", required=True)
    ap.add_argument("--train", required=True)
    c = ap.add_mutually_exclusive_group(required=True)
    c.add_argument("--clinical")
    c.add_argument("--clinical-csv")
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    docs = []
    for p in (a.emb, a.k, a.groups, a.train):
        with open(p, encoding="utf-8") as f:
            docs.append(json.load(f))
    emb_doc, k_doc, groups, train = docs
    if a.clinical:
        with open(a.clinical, encoding="utf-8") as f:
            clinical = json.load(f)
    else:
        from kidney.kpmp_q2 import clinical_table
        clinical, _ = clinical_table(a.clinical_csv)
    out = grade(emb_doc, k_doc, groups, train, clinical, a.n_perm)
    names = tuple(groups) + tuple(set(groups.values())) + tuple(r.get("slide", "") for r in emb_doc.get("rows", []))
    check_aggregate(out, names=names)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out["readings"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
