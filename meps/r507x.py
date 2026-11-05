# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Exploratory addendum to check R2, Brief #507: which rule for counting a family's children reproduces the
brief's Table 1 (16 published family counts by poverty status and family structure)?

The graded R2 run reproduced every poverty-row total of Table 1 to within one weighted family, but within each
row some families that the graded specification counts as having children appear in AHRQ's no-children
columns, with the adult count unchanged. This module holds the universe, family, weight and poverty definitions
of the graded specification fixed and changes only who counts as an adult or a child, under nine rules fixed in
findings/meps-r507x-prereg-v1-2026-11-05.md before any job reads the extra variables. It never changes a grade.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name. Reads the HC-181 fixed-width ASCII zip
(never downloads it). Only aggregate estimates leave the job. Research information about published statistics,
not medical advice.
"""
import argparse
import csv
import hashlib
import json
import math
import os

from meps import r2conc, r2rest

VERSION = "0.1.0"

# Brief #507 Table 1, weighted families (two reads of stat507.shtml on 2026-11-05 agree; each column and the
# poverty rows were checked by hand to add up to the printed totals, the grand total to within 1).
TABLE1 = {
    "Poor|1A0C": 9999307, "Poor|1A1C": 4125194, "Poor|2A0C": 1643690, "Poor|2A1C": 3625857,
    "Low|1A0C": 4966606, "Low|1A1C": 1542376, "Low|2A0C": 2099368, "Low|2A1C": 3550845,
    "Middle|1A0C": 10376047, "Middle|1A1C": 1756263, "Middle|2A0C": 6221641, "Middle|2A1C": 9028253,
    "High|1A0C": 11690284, "High|1A1C": 932514, "High|2A0C": 15399069, "High|2A1C": 10239641,
}
TABLE1_COLS = {"1A0C": 37032244, "1A1C": 8356347, "2A0C": 25363768, "2A1C": 26444596}
TABLE1_ALL = 97196954

AGE_VARS = ("AGE15X", "AGE31X", "AGE42X", "AGE53X")
EXTRA = ["PID", "PERWT15F", "INSC1231", "REFRL15X", "MOPID53X", "DAPID53X"] + list(AGE_VARS)

# HC-181 online codebook value tables, read 2026-11-05; each checked by hand to add up to 35,427.
# Age bins: (-1 inapplicable, 0-17, 18-64, 65-85).
GATE_X = {
    "pos": {"PERWT15F": 33893},
    "counts": {"INSC1231": {1: 35067, 2: 360},
               "REFRL15X": {1: 14177, 2: 5578, 3: 977, 4: 11736, 5: 154, 6: 752, 7: 897, 8: 621, 9: 37, 10: 51,
                            11: 193, 91: 254}},
    "neg1": {"MOPID53X": 22791, "DAPID53X": 26919},
    "age_bins": {"AGE15X": [235, 9615, 21210, 4367], "AGE31X": [997, 9541, 20735, 4154],
                 "AGE42X": [504, 9608, 21009, 4306], "AGE53X": [235, 9563, 21232, 4397]},
}


def age_bin(a):
    if a == -1:
        return 0
    if 0 <= a <= 17:
        return 1
    if 18 <= a <= 64:
        return 2
    if 65 <= a <= 85:
        return 3
    return None


def gate_x(rows, g=GATE_X):
    res, ok = {}, True
    for v, n in g["pos"].items():
        c = sum(1 for r in rows if float(r[v]) > 0)
        res["positive_" + v] = [c, n]
        ok = ok and c == n
    for v, table in g["counts"].items():
        got = {}
        for r in rows:
            k = int(r[v])
            got[k] = got.get(k, 0) + 1
        res["counts_" + v] = {str(k): [got.get(k, 0), n] for k, n in sorted(table.items())}
        ok = ok and got == table
    for v, n in g["neg1"].items():
        c = sum(1 for r in rows if int(r[v]) == -1)
        bad = sum(1 for r in rows if int(r[v]) != -1 and not 101 <= int(r[v]) <= 402)
        res["neg1_" + v] = [c, n, bad]
        ok = ok and c == n and bad == 0
    for v, want in g["age_bins"].items():
        got = [0, 0, 0, 0]
        bad = 0
        for r in rows:
            b = age_bin(int(r[v]))
            if b is None:
                bad += 1
            else:
                got[b] += 1
        res["bins_" + v] = [got, want, bad]
        ok = ok and got == want and bad == 0
    res["passed"] = ok
    return res


# ---------------------------------------------------------------- rules (fixed in the addendum)
def _agelast(m):
    return m["AGELAST"] >= 18, m["AGELAST"] <= 17


def _age_rule(var):
    def rule(m, pids):
        a = m[var]
        return a >= 18, 0 <= a <= 17
    return rule


def _child_if(cond):
    def rule(m, pids):
        adult, child = _agelast(m)
        return adult, child and cond(m, pids)
    return rule


RULES = [
    ("R0", "graded spec: AGELAST (adult 18+, child 0-17)", lambda m, pids: _agelast(m)),
    ("R1", "age as of 12/31/15, AGE15X (-1 = neither)", _age_rule("AGE15X")),
    ("R2", "age at round 3/1, AGE31X (-1 = neither)", _age_rule("AGE31X")),
    ("R3", "age at round 4/2, AGE42X (-1 = neither)", _age_rule("AGE42X")),
    ("R4", "age at round 5/3, AGE53X (-1 = neither)", _age_rule("AGE53X")),
    ("R5", "AGELAST; a child also needs PERWT15F > 0", _child_if(lambda m, p: m["PERWT15F"] > 0)),
    ("R6", "AGELAST; a child also needs INSC1231 = 1", _child_if(lambda m, p: m["INSC1231"] == 1)),
    ("R7", "AGELAST; a child also needs REFRL15X = 4", _child_if(lambda m, p: m["REFRL15X"] == 4)),
    ("R8", "AGELAST; a child also needs a parent (MOPID53X/DAPID53X) in the family",
     _child_if(lambda m, p: m["MOPID53X"] in p or m["DAPID53X"] in p)),
]
ROUND_AGE = ("R2", "R3", "R4")


def build(rows):
    """CPS families on 12/31/15 exactly as in r2rest.build_families (members FCRP1231 >= 0 and FAMWT15C > 0;
    weight and poverty from the one reference person), keeping each member's extra variables."""
    fams = {}
    for r in rows:
        rp = int(r["FCRP1231"])
        w = float(r["FAMWT15C"])
        if rp < 0 or w <= 0:
            continue
        m = {"AGELAST": int(r["AGELAST"]), "oop": float(r["TOTSLF15"]), "exp": float(r["TOTEXP15"]),
             "pov": int(r["POVCAT15"]), "w": w, "PID": int(r["PID"]), "PERWT15F": float(r["PERWT15F"]),
             "INSC1231": int(r["INSC1231"]), "REFRL15X": int(r["REFRL15X"]), "MOPID53X": int(r["MOPID53X"]),
             "DAPID53X": int(r["DAPID53X"])}
        for v in AGE_VARS:
            m[v] = int(r[v])
        f = fams.setdefault(r["DUID"] + r["CPSFAMID"], {"refs": [], "members": []})
        f["members"].append(m)
        if rp == 1:
            f["refs"].append(m)
    out, bad = [], 0
    for key in sorted(fams):
        f = fams[key]
        if len(f["refs"]) != 1:
            bad += 1
            continue
        ref, ms = f["refs"][0], f["members"]
        out.append({"key": key, "w": ref["w"], "pov": r2rest.POV_GROUP.get(ref["pov"]), "members": ms,
                    "pids": {m["PID"] for m in ms}, "elderly": any(m["AGELAST"] >= 65 for m in ms),
                    "oop": sum(m["oop"] for m in ms), "exp": sum(m["exp"] for m in ms)})
    return out, bad


def classify(fam, rule):
    adults = children = 0
    for m in fam["members"]:
        a, c = rule(m, fam["pids"])
        adults += 1 if a else 0
        children += 1 if c else 0
    if adults == 0:
        return None
    if adults == 1:
        return "1A0C" if children == 0 else "1A1C"
    return "2A0C" if children == 0 else "2A1C"


def round_half_up(x):
    return int(math.floor(x + 0.5))


def compare(cross, table):
    """Per cell: ours, published, gap, exact (ours rounded half-up to an integer equals the published count)."""
    out = {}
    for k, pub in table.items():
        v = cross.get(k, 0.0)
        out[k] = {"ours": v, "published": pub, "gap": v - pub, "exact": round_half_up(v) == pub}
    return out


STR_CELLS = [c for c in r2rest.fam_cells() if c[3][0] == "str" and c[3][1] != "All"]


def struct_estimates(pop, labels):
    est = {}
    for s in r2rest.STR[1:]:
        pairs = [(f["oop"], f["w"]) for f, lab in zip(pop, labels) if lab == s]
        if not pairs:
            continue
        est[("median", ("str", s))] = r2rest.wquantile_sas(pairs, 0.5)
        tw = sum(w for _, w in pairs)
        for b in r2rest.BANDS:
            est[("dist", ("str", s, b))] = 100.0 * sum(w for x, w in pairs if r2rest.band(x) == b) / tw
    return est


def analyze(fams):
    pop = [f for f in fams if not f["elderly"] and f["exp"] > 0]
    res = []
    for rid, desc, rule in RULES:
        labels = [classify(f, rule) for f in pop]
        cross, cols = {}, {}
        for f, lab in zip(pop, labels):
            if lab is None:
                continue
            k = "%s|%s" % (f["pov"], lab)
            cross[k] = cross.get(k, 0.0) + f["w"]
            cols[lab] = cols.get(lab, 0.0) + f["w"]
        cells = compare(cross, TABLE1)
        colcmp = compare(cols, TABLE1_COLS)
        gaps = [abs(c["gap"]) for c in cells.values()]
        st = r2rest.evaluate(STR_CELLS, struct_estimates(pop, labels))
        res.append({"rule": rid, "description": desc,
                    "table1_exact": sum(1 for c in cells.values() if c["exact"]),
                    "table1_max_abs_gap": max(gaps), "table1_sum_abs_gap": sum(gaps),
                    "columns_exact": sum(1 for c in colcmp.values() if c["exact"]),
                    "families_with_adult_weighted": sum(cols.values()),
                    "all_gap": sum(cols.values()) - TABLE1_ALL,
                    "no_adult_families": sum(1 for lab in labels if lab is None),
                    "no_adult_weighted": sum(f["w"] for f, lab in zip(pop, labels) if lab is None),
                    "struct_cells_exact": sum(1 for r in st if r["exact"]),
                    "struct_cells_close": sum(1 for r in st if r["close"]),
                    "struct_cells_n": len(st),
                    "table1": cells, "columns": colcmp, "struct_cells": st})
    best = sorted(res, key=lambda r: (-r["table1_exact"], r["table1_sum_abs_gap"]))[0]["rule"]
    repro = [r["rule"] for r in res if r["table1_exact"] == len(TABLE1)]
    summary = {"population_families": len(pop), "reproducing_rules": repro, "best_rule": best,
               "E1_some_rule_reproduces_all_16": bool(repro),
               "E2_best_rule_is_round_age": best in ROUND_AGE}
    return res, summary


def write_csv(path, res):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rule", "cell", "published", "ours", "gap", "exact"])
        for r in res:
            for k in TABLE1:
                c = r["table1"][k]
                w.writerow([r["rule"], k, c["published"], round(c["ours"], 2), round(c["gap"], 2), c["exact"]])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "brief": 507, "file": "H181", "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["data"] = {"file": os.path.basename(a.data), "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
        del raw
        pos = r2conc.positions(r2conc.read_inventory(a.inventory), r2rest.fields_507() + EXTRA)
        out["positions"] = pos
        rows = r2conc.load_ascii(a.data, pos)
        g = r2rest.gate(rows, r2rest.GATE_507, ["TOTSLF15", "TOTEXP15"])
        gx = gate_x(rows)
        fams, bad = build(rows)
        g["families"] = [len(fams), r2rest.GATE_507["families"]]
        g["keys_ref_not_1"] = bad
        g["passed"] = g["passed"] and gx["passed"] and len(fams) == r2rest.GATE_507["families"] and bad == 0
        out["gate"] = g
        out["gate_extra"] = gx
        if g["passed"]:
            res, summary = analyze(fams)
            out["summary"] = summary
            out["rules"] = res
            write_csv(os.path.join(a.out_dir, "table1-rules.csv"), res)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r507x.json"), "w") as f:
        json.dump(out, f, indent=1)
    brief = [{k: r[k] for k in ("rule", "table1_exact", "table1_max_abs_gap", "table1_sum_abs_gap",
                                 "columns_exact", "all_gap", "no_adult_families", "struct_cells_exact",
                                 "struct_cells_close")} for r in out.get("rules", [])]
    print(json.dumps({"gate_passed": out.get("gate", {}).get("passed"), "summary": out.get("summary"),
                      "rules": brief, "error": out["error"]}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
