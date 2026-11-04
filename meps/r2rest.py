# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R2, the last two drawn briefs: recompute the first 40 published cells of MEPS Statistical Briefs
#507 (family out-of-pocket expenses, 2015, HC-181) and #491 (spending by type of service, 2013, HC-163)
from the one Full Year Consolidated public-use file each brief names, read from its fixed-width ASCII zip
(never downloaded by this code).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r2-prereg-v1-2026-11-02.md; specification (fixed before any job reads
these briefs' variables): findings/meps-r2-spec-507-491-v1-2026-11-04.md (evidence-pack). Column positions
come from the published codebook inventory (findings/meps-inventory-v1/inventory/H<nnn>.csv). Only
aggregate estimates leave the job. Research information about published statistics, not medical advice.
"""
import argparse
import csv
import hashlib
import json
import os

from meps import r2conc

VERSION = "0.1.0"

# ---------------------------------------------------------------- #507 (HC-181, CPS families on 12/31/15)
INC = ("All", "Poor", "Low", "Middle", "High")
STR = ("All", "1A0C", "2A0C", "1A1C", "2A1C")  # Figure 3/4 order: 1 adult w/o, 2+ w/o, 1 w/, 2+ w/ children
BANDS = ("lt100", "100-2500", "gt2500")
POV_GROUP = {1: "Poor", 2: "Poor", 3: "Low", 4: "Middle", 5: "High"}


def fam_cells():
    """#507 Figures 1-4 in page order (row by row, left to right): exactly 40 cells."""
    out = []
    for g, t in zip(INC, ["451", "86", "252", "504", "868"]):
        out.append(("F1-%s" % g, 1, "median", ("inc", g), t))
    f2 = [["25%", "52%", "33%", "20%", "11%"], ["61%", "44%", "57%", "67%", "68%"],
          ["14%", "4%", "10%", "13%", "22%"]]
    for b, row in zip(BANDS, f2):
        for g, t in zip(INC, row):
            out.append(("F2-%s-%s" % (b, g), 2, "dist", ("inc", g, b), t))
    for s, t in zip(STR, ["451", "242", "869", "116", "721"]):
        out.append(("F3-%s" % s, 3, "median", ("str", s), t))
    f4 = [["25%", "61%", "14%"], ["33%", "60%", "8%"], ["13%", "66%", "21%"], ["48%", "47%", "6%"],
          ["17%", "65%", "19%"]]
    for s, row in zip(STR, f4):
        for b, t in zip(BANDS, row):
            out.append(("F4-%s-%s" % (s, b), 4, "dist", ("str", s, b), t))
    return out


# ---------------------------------------------------------------- #491 (HC-163, persons)
TYPES = ("IP", "AMB", "RX", "DENT", "HHOTH")
AGEG = ("Total", "lt65", "65plus")
INSG = ("AnyPriv", "PubOnly", "Unins", "McrOnly", "McrPriv", "McrOthPub")  # INSURC13 = 1..6
PAYERS = ("PRIV", "MCR", "OOP", "MCD", "OTH")
SVC = {"IP": ("IPTEXP",), "AMB": ("OBVEXP", "OPTEXP", "ERTEXP"), "RX": ("RXEXP",), "DENT": ("DVTEXP",),
       "HHOTH": ("HHAEXP", "HHNEXP", "VISEXP", "OTHEXP")}
PAY = {"PRIV": ("TOTPRV", "TOTTRI"), "MCR": ("TOTMCR",), "OOP": ("TOTSLF",), "MCD": ("TOTMCD",),
       "OTH": ("TOTVA", "TOTOFD", "TOTSTL", "TOTWCP", "TOTOPR", "TOTOPU", "TOTOSR")}
F1_491 = [["27.9", "25.8", "32.4"], ["37.9", "40.5", "32.4"], ["22.0", "21.5", "22.9"], ["6.6", "7.8", "3.8"],
          ["5.7", "4.4", "8.5"]]
F2_491 = [["24.1", "31.3", "26.6", "38.6", "29.0", "31.7"], ["43.1", "31.0", "43.2", "28.1", "37.1", "23.0"],
          ["19.9", "26.9", "21.8", "22.5", "22.3", "26.3"], ["9.4", "3.3", "6.2", "3.2", "4.8", "1.1"],
          ["3.6", "7.5", "2.2", "7.5", "6.7", "17.9"]]
F3_491 = [["40.6", "53.6", "13.2"], ["25.3", "7.2", "63.6"], ["13.8", "14.5", "12.2"], ["12.4", "16.5", "3.8"],
          ["7.9", "8.2", "7.3"]]


def svc_all_cells():
    """#491 Figures 1-3 in page order: 15 + 30 + 15 cells. The first 40 are graded; the rest are exploratory."""
    out = []
    for t, row in zip(TYPES, F1_491):
        for g, txt in zip(AGEG, row):
            out.append(("F1-%s-%s" % (t, g), 1, "share", ("type", t, g), txt))
    for t, row in zip(TYPES, F2_491):
        for g, txt in zip(INSG, row):
            out.append(("F2-%s-%s" % (t, g), 2, "share", ("type", t, g), txt))
    for p, row in zip(PAYERS, F3_491):
        for g, txt in zip(AGEG, row):
            out.append(("F3-%s-%s" % (p, g), 3, "share", ("payer", p, g), txt))
    return out


ALL_491 = svc_all_cells()

# Codebook value tables (HC-181 / HC-163 online codebooks, read 2026-11-04) and HC-181 documentation
# Table 3.3/3.4 (14,522 CPS families on 12/31/15 with a positive family weight).
GATE_507 = {"rows": 35427, "pos": {"FAMWT15C": 33850}, "zero": {"TOTSLF15": 13409, "TOTEXP15": 6936},
            "counts": {"FCRP1231": {-1: 411, 0: 20135, 1: 14881},
                       "POVCAT15": {1: 7924, 2: 2260, 3: 5921, 4: 10111, 5: 9211}},
            "families": 14522}
GATE_491 = {"rows": 36940, "pos": {"PERWT13F": 35068}, "zero": {"TOTEXP13": 7831},
            "counts": {"INSURC13": {1: 16238, 2: 10000, 3: 6585, 4: 1449, 5: 1798, 6: 769, 7: 52, 8: 49}}}

BRIEFS = {
    507: {"file": "H181", "yy": "15", "zip": "h181dat.zip", "cells": fam_cells(), "extra": [], "gate": GATE_507},
    491: {"file": "H163", "yy": "13", "zip": "h163dat.zip", "cells": ALL_491[:40], "extra": ALL_491[40:],
          "gate": GATE_491},
}


def fields_507():
    return ["DUID", "CPSFAMID", "FCRP1231", "FAMWT15C", "POVCAT15", "AGELAST", "TOTSLF15", "TOTEXP15"]


def comp_names(yy):
    svc = [v + yy for t in TYPES for v in SVC[t]]
    pay = [v + yy for p in PAYERS for v in PAY[p]]
    return svc, pay


def fields_491(yy="13"):
    svc, pay = comp_names(yy)
    return ["DUPERSID", "PERWT%sF" % yy, "AGELAST", "INSURC%s" % yy, "TOTEXP%s" % yy] + svc + pay


def gate(rows, g, money, age="AGELAST"):
    res = {"rows": len(rows), "rows_expected": g["rows"]}
    ok = len(rows) == g["rows"]
    for v, n in g["pos"].items():
        c = sum(1 for r in rows if float(r[v]) > 0)
        res["positive_" + v] = [c, n]
        ok = ok and c == n
    for v, n in g["zero"].items():
        c = sum(1 for r in rows if float(r[v]) == 0)
        res["zero_" + v] = [c, n]
        ok = ok and c == n
    for v, table in g["counts"].items():
        got = {}
        for r in rows:
            k = int(r[v])
            got[k] = got.get(k, 0) + 1
        res["counts_" + v] = {str(k): [got.get(k, 0), n] for k, n in sorted(table.items())}
        unexpected = sorted(set(got) - set(table))
        if unexpected:
            res["unexpected_" + v] = unexpected
        ok = ok and got == table
    res["negative_money"] = sum(1 for r in rows for m in money if float(r[m]) < 0)
    res["age_out_of_range"] = sum(1 for r in rows if not 0 <= int(r[age]) <= 85)
    ok = ok and res["negative_money"] == 0 and res["age_out_of_range"] == 0
    res["passed"] = ok
    return res


# ---------------------------------------------------------------- weighted quantiles
def wquantile_sas(pairs, p):
    """SAS PROC SURVEYMEANS quantile: on the weighted CDF F over distinct values y(1) < ... < y(n),
    y(1) if p < F(y(1)); y(k) + (p - F(y(k))) / (F(y(k+1)) - F(y(k))) * (y(k+1) - y(k)) where
    F(y(k)) <= p < F(y(k+1)); y(n) otherwise."""
    agg = {}
    for x, w in pairs:
        agg[x] = agg.get(x, 0.0) + w
    xs = sorted(agg)
    total = float(sum(agg.values()))
    cdf, c = [], 0.0
    for x in xs:
        c += agg[x]
        cdf.append(c / total)
    if p < cdf[0]:
        return xs[0]
    for k in range(len(xs) - 1):
        if cdf[k] <= p < cdf[k + 1]:
            return xs[k] + (p - cdf[k]) / (cdf[k + 1] - cdf[k]) * (xs[k + 1] - xs[k])
    return xs[-1]


def wquantile_lower(pairs, p):
    """Smallest value whose weighted CDF reaches p (exploratory alternative, not graded)."""
    total = sum(w for _, w in pairs)
    c = 0.0
    for x, w in sorted(pairs):
        c += w
        if c >= p * total - 1e-9:
            return x
    return max(x for x, _ in pairs)


# ---------------------------------------------------------------- #507 families
def build_families(rows):
    """CPS families on 12/31/15 (HC-181 documentation section 3.5): key DUID + CPSFAMID; members are persons
    with FCRP1231 >= 0 (in the 12/31 CPS family) and FAMWT15C > 0; the family weight and poverty category
    are the reference person's (FCRP1231 = 1). Family out-of-pocket and total expense are member sums."""
    fams = {}
    diag = {"members_zero_famwt": 0, "keys_ref_not_1": 0, "pov_mixed": 0, "weight_mixed": 0}
    for r in rows:
        rp = int(r["FCRP1231"])
        if rp < 0:
            continue
        w = float(r["FAMWT15C"])
        if w <= 0:
            diag["members_zero_famwt"] += 1
            continue
        key = r["DUID"] + r["CPSFAMID"]
        f = fams.setdefault(key, {"refs": [], "members": []})
        m = (int(r["AGELAST"]), float(r["TOTSLF15"]), float(r["TOTEXP15"]), int(r["POVCAT15"]), w)
        f["members"].append(m)
        if rp == 1:
            f["refs"].append(m)
    out = []
    for key in sorted(fams):
        f = fams[key]
        if len(f["refs"]) != 1:
            diag["keys_ref_not_1"] += 1
            continue
        ref, ms = f["refs"][0], f["members"]
        if len({m[3] for m in ms}) > 1:
            diag["pov_mixed"] += 1
        if len({m[4] for m in ms}) > 1:
            diag["weight_mixed"] += 1
        adults = sum(1 for m in ms if m[0] >= 18)
        out.append({"key": key, "w": ref[4], "pov": POV_GROUP.get(ref[3]), "size": len(ms), "adults": adults,
                    "children": len(ms) - adults, "elderly": any(m[0] >= 65 for m in ms),
                    "oop": sum(m[1] for m in ms), "exp": sum(m[2] for m in ms)})
    diag["families"] = len(out)
    diag["families_weighted"] = sum(f["w"] for f in out)
    return out, diag


def structure(f):
    if f["adults"] == 0:
        return None
    if f["adults"] == 1:
        return "1A0C" if f["children"] == 0 else "1A1C"
    return "2A0C" if f["children"] == 0 else "2A1C"


def band(oop):
    if oop < 100:
        return "lt100"
    if oop <= 2500:
        return "100-2500"
    return "gt2500"


def fam_estimates(fams):
    """Population: families with no member aged 65+ and positive family total expense."""
    nonelderly = [f for f in fams if not f["elderly"]]
    pop = [f for f in nonelderly if f["exp"] > 0]
    groups = {("inc", "All"): pop, ("str", "All"): pop}
    for g in INC[1:]:
        groups[("inc", g)] = [f for f in pop if f["pov"] == g]
    for s in STR[1:]:
        groups[("str", s)] = [f for f in pop if structure(f) == s]
    est, n = {}, {}
    for (dim, g), fs in groups.items():
        n["%s:%s" % (dim, g)] = len(fs)
        pairs = [(f["oop"], f["w"]) for f in fs]
        if not pairs:
            continue
        est[("median", (dim, g))] = wquantile_sas(pairs, 0.5)
        est[("median_lower", (dim, g))] = wquantile_lower(pairs, 0.5)
        tw = sum(w for _, w in pairs)
        for b in BANDS:
            est[("dist", (dim, g, b))] = 100.0 * sum(w for x, w in pairs if band(x) == b) / tw
    tw_pop = sum(f["w"] for f in pop)
    tw_ne = sum(f["w"] for f in nonelderly)
    cross = {}
    for g in INC[1:]:
        for s in STR[1:]:
            wsum = sum(f["w"] for f in pop if f["pov"] == g and structure(f) == s)
            cross["%s|%s" % (g, s)] = {"weighted": wsum, "pct": 100.0 * wsum / tw_pop if tw_pop else None}
    diag = {"n": n, "nonelderly_families_weighted": tw_ne, "population_weighted": tw_pop,
            "share_with_expense": 100.0 * tw_pop / tw_ne if tw_ne else None,
            "no_adult_families": sum(1 for f in pop if structure(f) is None),
            "table1_crosstab_exploratory": cross}
    return est, diag


# ---------------------------------------------------------------- #491 persons
def svc_groups(p):
    g = ["Total", "lt65" if p["age"] < 65 else "65plus"]
    if 1 <= p["ins"] <= 6:
        g.append(INSG[p["ins"] - 1])
    return g


def svc_estimates(persons, yy="13"):
    """Shares (%) of total expense TOTEXPyy by type of service and by source of payment, per group."""
    sums = {}
    for p in persons:
        for g in svc_groups(p):
            s = sums.setdefault(g, {"T": 0.0})
            s["T"] += p["w"] * p["x"]
            for t in TYPES:
                k = ("type", t)
                s[k] = s.get(k, 0.0) + p["w"] * sum(p["v"][v + yy] for v in SVC[t])
            for q in PAYERS:
                k = ("payer", q)
                s[k] = s.get(k, 0.0) + p["w"] * sum(p["v"][v + yy] for v in PAY[q])
    est = {}
    for g, s in sums.items():
        if s["T"] <= 0:
            continue
        for t in TYPES:
            est[("share", ("type", t, g))] = 100.0 * s[("type", t)] / s["T"]
        for q in PAYERS:
            est[("share", ("payer", q, g))] = 100.0 * s[("payer", q)] / s["T"]
    svc, pay = comp_names(yy)
    diag = {"persons": len(persons),
            "svc_mismatch": sum(1 for p in persons if abs(sum(p["v"][v] for v in svc) - p["x"]) > 0.5),
            "pay_mismatch": sum(1 for p in persons if abs(sum(p["v"][v] for v in pay) - p["x"]) > 0.5),
            "ins_age_conflict": sum(1 for p in persons
                                    if (1 <= p["ins"] <= 3 and p["age"] >= 65) or (p["ins"] >= 4 and p["age"] < 65)),
            "group_n": {g: sum(1 for p in persons if g in svc_groups(p)) for g in AGEG + INSG}}
    return est, diag


# ---------------------------------------------------------------- grading
def evaluate(cells, est):
    out = []
    for cid, fig, kind, arg, text in cells:
        r = {"cid": cid, "figure": fig, "kind": kind, "published": text, "underspecified": kind == "median"}
        v = est.get((kind, arg))
        if v is None:
            r.update(status="no estimate", value=None, gap=None, exact=False, close=False)
        else:
            gap, exact, close = r2conc.match("agepct" if kind in ("dist", "share") else "mean", v, text)
            r.update(status="computed", value=v, gap=gap, exact=exact, close=close)
        if kind == "median":
            r["alt_lower_median"] = est.get(("median_lower", arg))
        out.append(r)
    return out


def write_cells(path, res):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cid", "figure", "kind", "published", "value", "gap", "exact", "close", "status",
                    "underspecified", "alt_lower_median"])
        for r in res:
            alt = r.get("alt_lower_median")
            w.writerow([r["cid"], r["figure"], r["kind"], r["published"],
                        None if r["value"] is None else round(r["value"], 4),
                        None if r["gap"] is None else round(r["gap"], 4), r["exact"], r["close"], r["status"],
                        r["underspecified"], None if alt is None else round(alt, 4)])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", type=int, required=True, choices=sorted(BRIEFS))
    ap.add_argument("--data", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    spec = BRIEFS[a.brief]
    yy = spec["yy"]
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "brief": a.brief, "file": spec["file"], "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["data"] = {"file": os.path.basename(a.data), "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
        del raw
        inv = r2conc.read_inventory(a.inventory)
        names = fields_507() if a.brief == 507 else fields_491(yy)
        pos = r2conc.positions(inv, names)
        out["positions"] = pos
        rows = r2conc.load_ascii(a.data, pos)
        if a.brief == 507:
            g = gate(rows, spec["gate"], ["TOTSLF15", "TOTEXP15"])
            fams, fdiag = build_families(rows)
            g["families"] = [fdiag["families"], spec["gate"]["families"]]
            g["keys_ref_not_1"] = fdiag["keys_ref_not_1"]
            g["passed"] = (g["passed"] and fdiag["families"] == spec["gate"]["families"]
                           and fdiag["keys_ref_not_1"] == 0)
            out["gate"] = g
            out["family_diagnostics"] = fdiag
            if g["passed"]:
                est, diag = fam_estimates(fams)
                out["diagnostics"] = diag
        else:
            svc, pay = comp_names(yy)
            g = gate(rows, spec["gate"], ["TOTEXP" + yy] + svc + pay)
            out["gate"] = g
            if g["passed"]:
                w = "PERWT%sF" % yy
                persons = [{"w": float(r[w]), "age": int(r["AGELAST"]), "ins": int(r["INSURC" + yy]),
                            "x": float(r["TOTEXP" + yy]), "v": {k: float(r[k]) for k in svc + pay}}
                           for r in rows if float(r[w]) > 0]
                est, diag = svc_estimates(persons, yy)
                out["diagnostics"] = diag
        if g["passed"]:
            res = evaluate(spec["cells"], est)
            out["cells"] = res
            out["tally"] = r2conc.tally(res)
            write_cells(os.path.join(a.out_dir, "cells-%d.csv" % a.brief), res)
            if spec["extra"]:
                ext = evaluate(spec["extra"], est)
                out["extra_exploratory"] = ext
                out["extra_tally"] = r2conc.tally(ext)
                write_cells(os.path.join(a.out_dir, "extra-%d.csv" % a.brief), ext)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r2rest-%d.json" % a.brief), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"brief": a.brief, "gate": out.get("gate"), "tally": out.get("tally"),
                      "extra_tally": out.get("extra_tally"), "error": out["error"]}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
