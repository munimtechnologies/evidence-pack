# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R1: can the 26 published percentages of MEPS Statistical Brief #569 (bone density scans among
women 50+, 2022) be recomputed from the public MEPS HC-243 file alone?

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r569-prereg-v1-2026-11-01.md (evidence-pack).
Reads the HC-243 public-use file from a local zip (never downloads it). Writes aggregate estimates for
the brief's published cells only. Research information about published statistics, not medical advice.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
import zipfile

VERSION = "0.1.0"

COLUMNS = ["DUPERSID", "SAQWT22F", "VARSTR", "VARPSU", "SEX", "ADSEX42", "AGELAST", "AGE22X", "AGE42X",
           "AGE31X", "ADAGE42", "ADOSTP42", "ADBNDN42", "INSURC22", "HAVEUS42", "RACETHX", "REGION22",
           "REGION42", "REGION31", "POVCAT22"]
MSA_NAMES = ["MSA22", "MSA53", "MSA42", "MSA31"]

AGES = ("AGE22X", "AGE42X", "AGE31X")
REGS = ("REGION22", "REGION42", "REGION31")


def first_nonneg(p, names):
    for k in names:
        v = p.get(k)
        if v is not None and v >= 0:
            return v
    return None


def age_primary(p):
    """AGELAST if present and >= 0, else first non-negative of AGE22X, AGE42X, AGE31X."""
    v = p.get("AGELAST")
    if v is not None and v >= 0:
        return v
    return first_nonneg(p, AGES)


def age_saq(p):
    v = p.get("ADAGE42")
    return v if v is not None and v >= 0 else None


# Definition variants: (name, female predicate, age function). Variant A is primary.
VARIANTS = [
    ("A", lambda p: p.get("SEX") == 2, age_primary),
    ("B", lambda p: p.get("ADSEX42") == 2, age_primary),
    ("C", lambda p: p.get("SEX") == 2, age_saq),
]


def osteo_universe(p):
    return p.get("ADOSTP42") in (1, 2)


def osteo_yes(p):
    return p.get("ADOSTP42") == 1


def dexa_universe(p):
    return p.get("ADOSTP42") == 2 and p.get("ADBNDN42") in (1, 2)


def dexa_universe_b(p):
    return p.get("ADBNDN42") in (1, 2)


def dexa_yes(p):
    return p.get("ADBNDN42") == 1


def _ins(*codes):
    return lambda p: p.get("INSURC22") in codes


def _eq(var, *codes):
    return lambda p: p.get(var) in codes


def _reg(code):
    return lambda p: p.get("REGION22") == code


ALL = lambda p: True  # noqa: E731

# (cell id, figure, label, published %, outcome, age band, subgroup predicate)
# outcome: "osteo" or "dexa"; age band: "50+", "50-64", "65+".
CELLS = [
    ("F1a", 1, "50+", 21.5, "osteo", "50+", ALL),
    ("F1b", 1, "50-64", 9.2, "osteo", "50-64", ALL),
    ("F1c", 1, "65+", 33.8, "osteo", "65+", ALL),
    ("F2a", 2, "50+", 42.8, "dexa", "50+", ALL),
    ("F2b", 2, "50-64", 24.8, "dexa", "50-64", ALL),
    ("F2c", 2, "65+", 67.6, "dexa", "65+", ALL),
    ("F3a", 3, "50-64 any private", 27.9, "dexa", "50-64", _ins(1)),
    ("F3b", 3, "50-64 public only", 17.4, "dexa", "50-64", _ins(2)),
    ("F4a", 4, "65+ Medicare only", 69.4, "dexa", "65+", _ins(4)),
    ("F4b", 4, "65+ Medicare and private", 72.4, "dexa", "65+", _ins(5)),
    ("F4c", 4, "65+ Medicare and other public", 45.8, "dexa", "65+", _ins(6)),
    ("F5a", 5, "No USC", 30.7, "dexa", "50+", _eq("HAVEUS42", 2)),
    ("F5b", 5, "Yes USC", 45.3, "dexa", "50+", _eq("HAVEUS42", 1)),
    ("F6a", 6, "Hispanic", 25.4, "dexa", "50+", _eq("RACETHX", 1)),
    ("F6b", 6, "NH White", 47.7, "dexa", "50+", _eq("RACETHX", 2)),
    ("F6c", 6, "NH Black", 37.1, "dexa", "50+", _eq("RACETHX", 3)),
    ("F6d", 6, "NH Asian", 30.4, "dexa", "50+", _eq("RACETHX", 4)),
    ("F7a", 7, "Northeast", 44.1, "dexa", "50+", _reg(1)),
    ("F7b", 7, "Midwest", 43.9, "dexa", "50+", _reg(2)),
    ("F7c", 7, "South", 42.1, "dexa", "50+", _reg(3)),
    ("F7d", 7, "West", 41.7, "dexa", "50+", _reg(4)),
    ("F8a", 8, "Low income (<200% FPL)", 37.5, "dexa", "50+", _eq("POVCAT22", 1, 2, 3)),
    ("F8b", 8, "Middle income (200-<400% FPL)", 38.9, "dexa", "50+", _eq("POVCAT22", 4)),
    ("F8c", 8, "High income (>=400% FPL)", 47.6, "dexa", "50+", _eq("POVCAT22", 5)),
]
MSA_CELLS = [("F7e", 7, "Non-MSA", 43.3), ("F7f", 7, "MSA", 42.7)]


def in_band(a, band):
    if a is None:
        return False
    if band == "50+":
        return a >= 50
    if band == "50-64":
        return 50 <= a <= 64
    return a >= 65


def estimate(persons, member, outcome):
    """Weighted share (%) of outcome among members with SAQWT22F > 0, unweighted n, and a Taylor-series SE
    (with-replacement, strata VARSTR, PSUs VARPSU; domain estimation over the whole file)."""
    sw = 0.0
    swy = 0.0
    n = 0
    for p in persons:
        w = p.get("SAQWT22F")
        if w is None or not w > 0 or not member(p):
            continue
        n += 1
        sw += w
        if outcome(p):
            swy += w
    if sw <= 0:
        return {"n": n, "pct": None, "se": None}
    r = swy / sw
    tot = {}
    for p in persons:
        w = p.get("SAQWT22F")
        if w is None or not w > 0:
            continue
        h, j = p.get("VARSTR"), p.get("VARPSU")
        z = 0.0
        if member(p):
            z = w * ((1.0 if outcome(p) else 0.0) - r) / sw
        tot.setdefault(h, {}).setdefault(j, 0.0)
        tot[h][j] += z
    var = 0.0
    for h, psus in tot.items():
        k = len(psus)
        if k < 2:
            continue
        vals = list(psus.values())
        m = sum(vals) / k
        var += k / (k - 1) * sum((v - m) ** 2 for v in vals)
    return {"n": n, "pct": 100.0 * r, "se": 100.0 * math.sqrt(var)}


def evaluate(persons, variant=VARIANTS[0], dexa_u=dexa_universe):
    _, female, agef = variant
    out = []
    for cid, fig, label, pub, outcome, band, sub in CELLS:
        if outcome == "osteo":
            uni, yes = osteo_universe, osteo_yes
        else:
            uni, yes = dexa_u, dexa_yes

        def member(p, uni=uni, band=band, sub=sub):
            return female(p) and in_band(agef(p), band) and uni(p) and sub(p)
        e = estimate(persons, member, yes)
        pct = e["pct"]
        diff = None if pct is None else pct - pub
        out.append({"cid": cid, "figure": fig, "label": label, "published": pub, "pct": pct, "se": e["se"],
                    "n": e["n"], "diff": diff,
                    "exact": diff is not None and abs(diff) <= 0.05 + 1e-9,
                    "close": diff is not None and abs(diff) <= 0.5 + 1e-9})
    return out


def grade(primary, msa_present, missing):
    k = len(primary)
    close = sum(1 for r in primary if r["close"])
    exact = sum(1 for r in primary if r["exact"])
    g = {"cells": k, "close": close, "exact": exact}
    g["P1"] = {"grade": "held" if close >= 20 else "failed", "close": close, "of": k}
    f2a = [r for r in primary if r["cid"] == "F2a"]
    g["P2"] = {"grade": "held" if f2a and f2a[0]["exact"] else "failed",
               "pct": f2a[0]["pct"] if f2a else None}
    g["P3"] = {"grade": "held" if not msa_present else "failed", "msa_variables_in_file": msa_present}
    g["P4"] = {"grade": "held" if exact >= 18 else "failed", "exact": exact, "of": k}
    if missing:
        g["missing_columns"] = missing
    return g


def load(zip_path):
    """(persons, missing columns, MSA-like variables present, all variable names)."""
    import pandas as pd  # only needed for the real run
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".dta")]
        if not names:
            raise RuntimeError("no .dta file in %s" % zip_path)
        path = z.extract(names[0], tmp)
    with pd.read_stata(path, iterator=True) as rd:
        labels = rd.variable_labels()
    available = list(labels.keys())
    msa = sorted(v for v in available if v.upper().startswith("MSA") or "METRO" in v.upper()
                 or "MSA" in str(labels.get(v, "")).upper().split())
    cols = [c for c in COLUMNS if c in available]
    missing = [c for c in COLUMNS if c not in available]
    df = pd.read_stata(path, columns=cols, convert_categoricals=False)
    df = df.astype(object).where(df.notna(), None)
    persons = df.to_dict("records")
    for p in persons:
        for k, v in list(p.items()):
            if k != "DUPERSID" and v is not None:
                p[k] = float(v)
    return persons, missing, msa, available


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data/h243dta.zip")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["h243"] = {"file": os.path.basename(a.data), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        persons, missing, msa, available = load(a.data)
        out["persons"] = len(persons)
        out["n_variables"] = len(available)
        out["missing_columns"] = missing
        out["msa_like_variables"] = msa
        out["msa_named_variables_present"] = [v for v in MSA_NAMES if v in available]
        out["saq_positive_weight"] = sum(1 for p in persons if p.get("SAQWT22F") and p["SAQWT22F"] > 0)
        primary = evaluate(persons)
        out["cells"] = primary
        out["msa_cells"] = [{"cid": c[0], "label": c[2], "published": c[3],
                             "status": "not computable from HC-243" if not msa else "MSA-like variable present"}
                            for c in MSA_CELLS]
        sens = {}
        for v in VARIANTS[1:]:
            sens[v[0]] = [{"cid": r["cid"], "pct": r["pct"], "n": r["n"], "exact": r["exact"]}
                          for r in evaluate(persons, v)]
        sens["A_dexa_universe_B"] = [{"cid": r["cid"], "pct": r["pct"], "n": r["n"], "exact": r["exact"]}
                                     for r in evaluate(persons, VARIANTS[0], dexa_universe_b)]
        out["sensitivity"] = sens
        out["grades"] = grade(primary, out["msa_named_variables_present"] + msa, missing)
        with open(os.path.join(a.out_dir, "cells.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cid", "figure", "label", "published", "pct", "se", "n", "diff", "exact", "close"])
            for r in primary:
                w.writerow([r["cid"], r["figure"], r["label"], r["published"],
                            None if r["pct"] is None else round(r["pct"], 3),
                            None if r["se"] is None else round(r["se"], 3), r["n"],
                            None if r["diff"] is None else round(r["diff"], 3), r["exact"], r["close"]])
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r569.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"grades": out.get("grades"), "error": out["error"],
                      "missing_columns": out.get("missing_columns")}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
