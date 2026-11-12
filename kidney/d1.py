#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""d1: grader of the pre-registered D1 lane of MV2's open entry for the NIDDK Kidney AI Discovery Challenge, a
technical control: does the share of globally sclerotic (GS) glomeruli that the detector reads straight from open KPMP
whole-slide images (no KPMP labels at inference) reproduce the clinical gradient that KPMP's own released
segmentation shows on the same participants?

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical
device, not for diagnosis or patient care. Implements findings/kidney-d1-prereg-v1-2026-11-12.md, written before any
D1 output existed.

Inputs (all local; KPMP data use terms):
  --det      one or more detector documents with rows {"slide", "ok", "classes": ["gs" / "ns", ...]}: the output of
             kidney/emb.py `run` (D2's slide pass) or of kidney/gsdet.py `detect`. Several batch files are merged; a
             slide seen twice counts once (its first successful row).
  --k        one or more k.json files of kidney/kmask.py >= 0.3.0 (KPMP's released segmentation per slide:
             `k_objects` {"glom": [...], "gs": [...]}), merged.
  --groups   JSON {slide name: participant}
  --train    JSON [participant, ...] whose slides trained the detector: never in the graded set
  --dev      optional JSON [participant, ...] whose slides graded earlier stages: kept in the graded set; a
             sensitivity result without them is reported, not graded
  --clinical JSON {participant: {field: code}} or --clinical-csv (KPMP open clinical file, coded by
             kidney/kpmp_q2.py `clinical_table`)
Steps, each fixed in the pre-registration:
  1. Slides used: a successful detector row AND a group AND KPMP objects (kmask). Per participant, over those slides:
     detector GS share = objects the detector calls "gs" / all its objects; label GS share = KPMP "gs" / all KPMP
     glomeruli (same slides). Eligible: not in --train, >= MIN_OBJ detector objects and >= MIN_OBJ KPMP objects.
  2. D1a  Spearman rho of detector GS share vs baseline eGFR < 0 with one-sided shuffle p < ALPHA_EGFR.
     D1b  |rho(detector) - rho(label)| <= RHO_GAP_MAX on exactly the same participants.
     D1c  rho of detector GS share vs hypertension history > 0 with one-sided shuffle p < ALPHA_HTN.
     D1d  Spearman rho of detector vs label GS share across participants >= AGREE_MIN (mean and median bias
          reported).
     Shuffles: N_PERM shuffles of the clinical field, random.Random(SEED), p = (1 + #{as or more extreme}) /
     (1 + N_PERM). Each reading is "not graded" with fewer than MIN_PART participants.
Output: rates, correlations, p-values and participant numbers only; never names, object counts, per-slide or
per-participant values (main() refuses any output containing a slide or participant name).
Usage:
  python -m kidney.d1 --det emb-1.json emb-2.json --k k-1.json k-2.json --groups groups.json \\
      --train train.json [--dev dev.json] --clinical-csv clinical.csv --out d1.json [--n-perm 9999]
"""
import argparse
import json
import random
import statistics

from kidney import anom
from kidney.compare import check_aggregate

CODE_VERSION = "0.1.0"
PREREG = "findings/kidney-d1-prereg-v1-2026-11-12.md"
SEED = 11
N_PERM = 9999
MIN_OBJ = 5
MIN_PART = 60
ALPHA_EGFR = 0.01
RHO_GAP_MAX = 0.10
ALPHA_HTN = 0.05
AGREE_MIN = 0.70
EPS = 1e-9
TIE_EPS = 1e-12
READINGS = ("d1a", "d1b", "d1c", "d1d")
ND = 4


def tally(det_docs, k_doc, groups):
    """({participant: [detector gs, detector all, KPMP gs, KPMP all]}, slide stats). PRIVATE: keep local."""
    per, seen, names = {}, set(), set()
    st = {"slides": 0, "failed": 0, "no_group": 0, "no_k": 0, "used": 0}
    for doc in det_docs:
        for r in doc.get("rows", []):
            s = r.get("slide")
            names.add(s)
            if not r.get("ok") or s in seen:
                continue
            seen.add(s)
            g = groups.get(s)
            if g is None:
                st["no_group"] += 1
                continue
            kobj = (k_doc.get(s) or {}).get("k_objects")
            if not kobj:
                st["no_k"] += 1
                continue
            st["used"] += 1
            cl = r.get("classes") or []
            kg = len(kobj.get("gs") or [])
            c = per.setdefault(g, [0, 0, 0, 0])
            c[0] += sum(1 for x in cl if x == "gs")
            c[1] += len(cl)
            c[2] += kg
            c[3] += kg + len(kobj.get("glom") or [])
    st["slides"] = len(names)
    st["failed"] = len(names - seen)
    return per, st


def shares(per, exclude=(), min_obj=MIN_OBJ):
    """{participant: (detector GS share, label GS share)} for participants not in `exclude` with >= min_obj objects
    on both sides. PRIVATE: keep local."""
    ex = set(exclude)
    return {g: (c[0] / c[1], c[2] / c[3]) for g, c in per.items()
            if g not in ex and c[1] >= min_obj and c[3] >= min_obj}


def one_sided(x, y, direction, n_perm=N_PERM, seed=SEED):
    """(rho, p): Spearman rho of x and y, and its one-sided shuffle p-value in `direction` (-1 when rho < 0 is
    expected, +1 when rho > 0): y is shuffled and p = (1 + #{direction * rho_perm >= direction * rho - 1e-12}) /
    (1 + n_perm). Shuffles with an undefined rho count as not extreme. (None, None) when rho is undefined."""
    r = anom.spearman(x, y)
    if r is None:
        return None, None
    rng = random.Random(seed)
    yy = list(y)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(yy)
        rp = anom.spearman(x, yy)
        if rp is not None and direction * rp >= direction * r - TIE_EPS:
            count += 1
    return r, (1 + count) / (1 + n_perm)


def clin_test(sh, clinical, field, direction, pids, n_perm=N_PERM, seed=SEED):
    """Detector and label sides of one clinical field on the participants of `pids` (sorted) that have the field."""
    ps = sorted(g for g in pids if g in sh and (clinical.get(g) or {}).get(field) is not None)
    y = [clinical[g][field] for g in ps]
    rd, pd = one_sided([sh[g][0] for g in ps], y, direction, n_perm, seed)
    rl, pl = one_sided([sh[g][1] for g in ps], y, direction, n_perm, seed)
    return {"n": len(ps), "rho_detector": rd, "p_detector": pd, "rho_label": rl, "p_label": pl}


def agreement(sh, pids):
    """Pooled agreement of detector and label GS shares over `pids` (no per-participant values)."""
    ps = sorted(g for g in pids if g in sh)
    if not ps:
        return {"n": 0, "rho": None, "mean_detector": None, "mean_label": None, "mean_bias": None,
                "median_bias": None}
    d = [sh[g][0] for g in ps]
    lab = [sh[g][1] for g in ps]
    diffs = [a - b for a, b in zip(d, lab)]
    return {"n": len(ps), "rho": anom.spearman(d, lab), "mean_detector": sum(d) / len(d),
            "mean_label": sum(lab) / len(lab), "mean_bias": sum(diffs) / len(diffs),
            "median_bias": statistics.median(diffs)}


def readings(egfr, htn, agree, min_part=MIN_PART):
    """{"d1a".."d1d": "pass" / "fail" / "not graded"}."""
    def pf(ok):
        return "pass" if ok else "fail"
    out = {}
    rd, rl = egfr["rho_detector"], egfr["rho_label"]
    if egfr["n"] < min_part or rd is None:
        out["d1a"] = "not graded"
    else:
        out["d1a"] = pf(rd < 0 and egfr["p_detector"] < ALPHA_EGFR)
    if egfr["n"] < min_part or rd is None or rl is None:
        out["d1b"] = "not graded"
    else:
        out["d1b"] = pf(abs(rd - rl) <= RHO_GAP_MAX + EPS)
    if htn["n"] < min_part or htn["rho_detector"] is None:
        out["d1c"] = "not graded"
    else:
        out["d1c"] = pf(htn["rho_detector"] > 0 and htn["p_detector"] < ALPHA_HTN)
    if agree["n"] < min_part or agree["rho"] is None:
        out["d1d"] = "not graded"
    else:
        out["d1d"] = pf(agree["rho"] >= AGREE_MIN - EPS)
    return out


def _round(x):
    if isinstance(x, float):
        return round(x, ND)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def grade(det_docs, k_doc, groups, train, clinical, dev=None, n_perm=N_PERM, seed=SEED, min_obj=MIN_OBJ,
          min_part=MIN_PART):
    """The public D1 document (aggregates only)."""
    per, st = tally(det_docs, k_doc, groups)
    trset = set(train)
    sh = shares(per, trset, min_obj)
    pids = sorted(sh)
    egfr = clin_test(sh, clinical, "egfr", -1, pids, n_perm, seed)
    htn = clin_test(sh, clinical, "hypertension", 1, pids, n_perm, seed)
    agree = agreement(sh, pids)
    sh_all = shares(per, (), min_obj)
    reported = {"train_agreement": agreement(sh_all, [g for g in sh_all if g in trset]),
                "egfr_without_dev": None, "hypertension_without_dev": None}
    if dev is not None:
        devset = set(dev)
        keep = [g for g in pids if g not in devset]
        reported["egfr_without_dev"] = clin_test(sh, clinical, "egfr", -1, keep, n_perm, seed)
        reported["hypertension_without_dev"] = clin_test(sh, clinical, "hypertension", 1, keep, n_perm, seed)
    n = st["slides"]
    return _round({"code_version": CODE_VERSION, "prereg": PREREG, "anom_code_version": anom.CODE_VERSION,
                   "detector_documents": sorted({"%s/%s" % (d.get("code_version"), d.get("gsdet"))
                                                 for d in det_docs}),
                   "n_perm": n_perm, "seed": seed, "min_objects": min_obj, "min_participants": min_part,
                   "share_slides_failed": st["failed"] / n if n else None,
                   "share_slides_unusable": (st["no_group"] + st["no_k"]) / n if n else None,
                   "n_participants": len(pids), "n_train_participants_excluded": len(trset & set(per)),
                   "egfr": egfr, "hypertension": htn, "agreement": agree, "reported": reported,
                   "readings": readings(egfr, htn, agree, min_part)})


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade the pre-registered D1 lane (aggregate output only).")
    ap.add_argument("--det", nargs="+", required=True)
    ap.add_argument("--k", nargs="+", required=True)
    ap.add_argument("--groups", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--dev")
    c = ap.add_mutually_exclusive_group(required=True)
    c.add_argument("--clinical")
    c.add_argument("--clinical-csv")
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    det_docs = [_load(p) for p in a.det]
    k_doc = {}
    for p in a.k:
        for s, v in _load(p).items():
            k_doc.setdefault(s, v)
    groups, train = _load(a.groups), _load(a.train)
    dev = _load(a.dev) if a.dev else None
    if a.clinical:
        clinical = _load(a.clinical)
    else:
        from kidney.kpmp_q2 import clinical_table
        clinical, _ = clinical_table(a.clinical_csv)
    out = grade(det_docs, k_doc, groups, train, clinical, dev, a.n_perm)
    names = tuple(groups) + tuple(set(groups.values())) + tuple(
        r.get("slide") or "" for d in det_docs for r in d.get("rows", []))
    check_aggregate(out, names=names)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out["readings"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
