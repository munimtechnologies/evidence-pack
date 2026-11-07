# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R2b addendum r558x: MEPS Statistical Brief #558 (lack of reliable transportation, 2021, HC-233).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r558x-prereg-v1-2026-11-07.md (evidence-pack). Two questions:
  1. Internal consistency: with the file's own weighted age shares among the brief's base, what overall rate
     do the brief's four printed age rates (11.1, 9.2, 6.1, 4.3) imply, next to its printed total (6.2)?
  2. Readings: does one simple alternative choice (another weight, the item's -15 code counted as yes or as
     no, no weights, or AGELAST for age) bring #558's 40 graded cells close?
Each reading is a transformation of the records fed to meps.r2b.est558 unchanged, so the "spec" reading is
exactly check R2b. Only aggregate estimates leave the job. Research information about published
statistics, not medical advice.
"""
import argparse
import hashlib
import json
import os

from meps import r2b, r2conc

VERSION = "0.1.0"

FIELDS = r2b.FIELDS["H233"] + ["PERWT21F", "AGELAST"]
Y = "SDNOTRANS"
W = "SDOHWT21F"
PRINTED_TOTAL = 6.2
PRINTED_AGE = (("18-34", 11.1), ("35-49", 9.2), ("50-64", 6.1), ("65+", 4.3))
VARIANTS = ("spec", "perwt", "m15_yes", "m15_no", "unweighted", "agelast")
FIG1 = ("total", "age|18-34", "age|35-49", "age|50-64", "age|65+", "race|2", "race|3", "race|1", "race|other")


def age_shares(recs, wv=W):
    """Weighted share (%) of each of #558's age bands among its base (r2b._base: positive SDOH weight,
    item answered 1 or 2, AGE31X >= 18), weighting by wv. None if the base has no weight."""
    base = r2b._base(recs, Y)
    tot = sum(r[wv] for r in base)
    if tot <= 0:
        return None
    return {lab: 100.0 * sum(r[wv] for r in base if lo <= r["AGE31X"] <= hi) / tot for lab, lo, hi in r2b.AGE_558}


def implied_total(shares, rates=PRINTED_AGE):
    """Overall rate (%) implied by age-band rates and age shares (%)."""
    return sum(shares[lab] * rate for lab, rate in rates) / 100.0


def variant(recs, name):
    """New records for one reading; the input records are not changed."""
    if name not in VARIANTS:
        raise ValueError(name)
    out = []
    for r in recs:
        s = dict(r)
        if name == "perwt":
            s[W] = r["PERWT21F"] if r[W] > 0 else 0.0
        elif name == "m15_yes" and r[Y] == -15:
            s[Y] = 1.0
        elif name == "m15_no" and r[Y] == -15:
            s[Y] = 2.0
        elif name == "unweighted":
            s[W] = 1.0 if r[W] > 0 else 0.0
        elif name == "agelast":
            s["AGE31X"] = r["AGELAST"]
        out.append(s)
    return out


def run(recs, cells):
    res = {}
    for name in VARIANTS:
        est = r2b.est558(variant(recs, name))
        ev = r2b.evaluate(558, cells, est, False)
        flat = {r2b.keystr(k): v for k, v in est.items()}
        res[name] = {"tally": r2conc.tally(ev), "fig1": {k: flat.get(k) for k in FIG1},
                     "cells": [[c["seq"], None if c["value"] is None else round(c["value"], 4), c["exact"],
                                c["close"]] for c in ev]}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "brief": 558, "file": "H233", "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["data"] = {"file": os.path.basename(a.data), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        del raw
        inv = r2conc.read_inventory(a.inventory)
        pos = r2conc.positions(inv, FIELDS)
        out["positions"] = pos
        rows = r2conc.load_ascii(a.data, pos)
        g = r2b.gate(rows, r2b.GATES["H233"])
        out["gate"] = g
        if g["passed"]:
            recs = [r2b.to_rec(r) for r in rows]
            del rows
            base = r2b._base(recs, Y)
            out["diagnostics"] = {
                "n_base": len(base),
                "n_perwt_positive": sum(1 for r in recs if r["PERWT21F"] > 0),
                "n_sdoh_positive_perwt_zero": sum(1 for r in recs if r[W] > 0 and r["PERWT21F"] <= 0),
                "n_item_m15_with_sdoh_weight": sum(1 for r in recs if r[W] > 0 and r[Y] == -15),
                "n_age31x_ne_agelast_in_base": sum(1 for r in base if r["AGE31X"] != r["AGELAST"]),
            }
            consistency = {}
            for wv in (W, "PERWT21F"):
                sh = age_shares(recs, wv)
                consistency[wv] = {"age_shares": sh, "implied_total": None if sh is None else implied_total(sh)}
            consistency["printed_total"] = PRINTED_TOTAL
            consistency["printed_age_rates"] = dict(PRINTED_AGE)
            out["consistency"] = consistency
            res = run(recs, r2b.load_cells(a.cells, 558))
            out["variants"] = res
            sp = res["spec"]["tally"]
            out["spec_matches_r2b"] = (sp["close"], sp["exact"], sp["computable"]) == (18, 2, 40)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r558x.json"), "w") as f:
        json.dump(out, f, indent=1)
    brief = {"error": out["error"], "gate_passed": (out.get("gate") or {}).get("passed"),
             "spec_matches_r2b": out.get("spec_matches_r2b"),
             "implied_total_sdoh": ((out.get("consistency") or {}).get(W) or {}).get("implied_total"),
             "tallies": {k: v["tally"] for k, v in (out.get("variants") or {}).items()}}
    print(json.dumps(brief, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
