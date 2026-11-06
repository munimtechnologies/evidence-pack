# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R2b: recompute the graded published cells of the six single-file MEPS Statistical Briefs that the
R2 draw did not pick (#493, #496, #497 on HC-171, 2014; #533 on HC-209, 2018; #554, #558 on HC-233, 2021)
from the fixed-width ASCII zip of the one Full Year Consolidated file each brief names (never downloaded
by this code).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r2b-prereg-v1-2026-11-06.md. Transcription (the published cells, two reads):
findings/meps-r2b-transcription-v1/cells.csv. Specification: findings/meps-r2b-spec-v1-*.md (evidence-pack).
Column positions come from the published codebook inventory (findings/meps-inventory-v1/inventory/H<nnn>.csv).
Ranking, ASCII reading and matching are reused from meps.r2conc (check R2). Only aggregate estimates leave
the job. Research information about published statistics, not medical advice.
"""
import argparse
import csv
import hashlib
import json
import os

from meps import r2conc

VERSION = "0.1.0"

BRIEF_FILE = {554: "H233", 558: "H233", 493: "H171", 496: "H171", 497: "H171", 533: "H209"}

FIELDS = {
    "H233": ["DUPERSID", "SDOHWT21F", "SDENICPROD", "SDNOTRANS", "AGE31X", "RACETHX", "SEX", "REGION31",
             "RTHLTH31", "MNHLTH31", "OFTSMK53", "ASTHDX", "INSCOV21", "MCREV21", "MCDEV21", "DIABDX_M18",
             "EMPHDX", "CANCERDX", "CHDDX", "ANGIDX", "MIDX", "OHRTDX", "BPMLDX", "STRKDX", "CHOLDX"],
    "H171": ["DUPERSID", "PERWT14F", "TOTEXP14", "AGE14X", "AGELAST", "INSCOV14", "IPTEXP14", "OBVEXP14",
             "OPTEXP14", "ERTEXP14", "RXEXP14", "DVTEXP14", "HHAEXP14", "HHNEXP14", "VISEXP14", "OTHEXP14"],
    "H209": ["DUPERSID", "PERWT18F", "TOTEXP18", "AGELAST"],
}

# Codebook value-table counts (meps.ahrq.gov codebook pages, read 2026-11-06; every table sums to the file's
# record count). Nothing is computed unless every listed count matches.
GATES = {
    "H233": {"rows": 28336, "positive": ("SDOHWT21F", 18400),
             "counts": {"SDENICPROD": {-15: 216, -1: 9936, 1: 2419, 2: 15765},
                        "SDNOTRANS": {-15: 204, -1: 9936, 1: 1187, 2: 17009},
                        "RACETHX": {1: 6798, 2: 15023, 3: 4071, 4: 1385, 5: 1059},
                        "AGE31X": {-1: 511}, "INSCOV21": {1: 16128, 2: 10136, 3: 2072},
                        "OFTSMK53": {1: 1913, 2: 939, 3: 19379}}},
    "H171": {"rows": 34875, "positive": ("PERWT14F", 33162), "zeros": ("TOTEXP14", 7225),
             "counts": {"INSCOV14": {1: 17829, 2: 12078, 3: 4968}, "AGE14X": {-1: 209}}},
    "H209": {"rows": 30461, "positive": ("PERWT18F", 29415), "zeros": ("TOTEXP18", 4620)},
}


def _num(text):
    return float(text)


def gate(rows, g):
    """Record count, positive weights, zero expenditures and the listed value counts against the codebook."""
    checks = [["rows", "count", len(rows), g["rows"]]]
    var, exp = g["positive"]
    checks.append([var, ">0", sum(1 for r in rows if _num(r[var]) > 0), exp])
    if "zeros" in g:
        var, exp = g["zeros"]
        checks.append([var, "==0", sum(1 for r in rows if _num(r[var]) == 0), exp])
    for var, table in g.get("counts", {}).items():
        for value, exp in table.items():
            checks.append([var, "==%d" % value, sum(1 for r in rows if _num(r[var]) == value), exp])
    return {"checks": checks, "passed": all(c[2] == c[3] for c in checks)}


def to_rec(row):
    rec = {k: (v if k == "DUPERSID" else _num(v)) for k, v in row.items()}
    rec["id"] = row.get("DUPERSID", "")
    return rec


def wpct(recs, wv, num):
    """Weighted percentage of recs for which num(r) is true; None if recs carry no weight."""
    den = sum(r[wv] for r in recs)
    if den <= 0:
        return None
    return 100.0 * sum(r[wv] for r in recs if num(r)) / den


def wmedian(pairs):
    """Weighted median of (value, weight > 0) pairs: the smallest value whose cumulative weight reaches half
    of the total (our reading; the brief does not state its quantile rule)."""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    if total <= 0:
        return None
    c = 0.0
    for x, w in pairs:
        c += w
        if c >= total / 2.0 - 1e-9:
            return x
    return pairs[-1][0]


# ---- #554 and #558 (HC-233; Social and Health Experiences SAQ items) ----

AGE_554 = (("18-24", 18, 24), ("25-34", 25, 34), ("35-44", 35, 44), ("45-64", 45, 64), ("65+", 65, 200))
AGE_558 = (("18-34", 18, 34), ("35-49", 35, 49), ("50-64", 50, 64), ("65+", 65, 200))
SDOH_W = "SDOHWT21F"


def _base(recs, outcome):
    """Adults (AGE31X >= 18) with a positive SDOH weight who answered the item yes (1) or no (2)."""
    return [r for r in recs if r[SDOH_W] > 0 and r[outcome] in (1, 2) and r["AGE31X"] >= 18]


def _health(e, sub, p):
    for var, key in (("RTHLTH31", "gh"), ("MNHLTH31", "mh")):
        for code in (1, 2, 3):
            e[(key, code)] = p([r for r in sub if r[var] == code])
        e[(key, "fp")] = p([r for r in sub if r[var] in (4, 5)])


def est554(recs):
    y = "SDENICPROD"
    base = _base(recs, y)

    def p(sub):
        return wpct(sub, SDOH_W, lambda r: r[y] == 1)

    young = [r for r in base if 18 <= r["AGE31X"] <= 24]
    e = {("all_adults",): p(base), ("n", "base"): len(base), ("n", "young"): len(young),
         ("n", "wpos_item_inapplicable"): sum(1 for r in recs if r[SDOH_W] > 0 and r[y] == -1),
         ("n", "wzero_item_present"): sum(1 for r in recs if r[SDOH_W] <= 0 and r[y] != -1)}
    for lab, lo, hi in AGE_554:
        e[("age", lab)] = p([r for r in base if lo <= r["AGE31X"] <= hi])
    for code in (1, 2, 3):
        e[("race", code)] = p([r for r in young if r["RACETHX"] == code])
    e[("race", "other")] = p([r for r in young if r["RACETHX"] in (4, 5)])
    for code in (1, 2):
        e[("sex", code)] = p([r for r in young if r["SEX"] == code])
    for code in (1, 2, 3, 4):
        e[("region", code)] = p([r for r in young if r["REGION31"] == code])
    _health(e, young, p)
    e[("smoke", "yes")] = p([r for r in young if r["OFTSMK53"] in (1, 2)])
    e[("smoke", "no")] = p([r for r in young if r["OFTSMK53"] == 3])
    for code in (1, 2):
        e[("asthma", code)] = p([r for r in young if r["ASTHDX"] == code])
    return e


COND9 = ("diab", "emph", "cancer", "heart", "smoker", "asthma", "hyper", "stroke", "chol")


def conds(r):
    return {"diab": r["DIABDX_M18"] == 1, "emph": r["EMPHDX"] == 1, "cancer": r["CANCERDX"] == 1,
            "heart": any(r[v] == 1 for v in ("CHDDX", "ANGIDX", "MIDX", "OHRTDX")),
            "smoker": r["OFTSMK53"] in (1, 2), "asthma": r["ASTHDX"] == 1, "hyper": r["BPMLDX"] == 1,
            "stroke": r["STRKDX"] == 1, "chol": r["CHOLDX"] == 1}


def ins558(r):
    """Private first (any private in 2021), then Medicare, then Medicaid/CHIP, as the brief's definitions
    assign people with more than one coverage; uninsured all year."""
    if r["INSCOV21"] == 1:
        return "private"
    if r["INSCOV21"] == 3:
        return "uninsured"
    if r["MCREV21"] == 1:
        return "medicare"
    if r["MCDEV21"] == 1:
        return "medicaid"
    return "other_public"


def est558(recs):
    y = "SDNOTRANS"
    base = _base(recs, y)

    def p(sub):
        return wpct(sub, SDOH_W, lambda r: r[y] == 1)

    e = {("total",): p(base), ("n", "base"): len(base)}
    for lab, lo, hi in AGE_558:
        e[("age", lab)] = p([r for r in base if lo <= r["AGE31X"] <= hi])
    for code in (1, 2, 3):
        e[("race", code)] = p([r for r in base if r["RACETHX"] == code])
    e[("race", "other")] = p([r for r in base if r["RACETHX"] == 5])
    e[("race", "asian")] = p([r for r in base if r["RACETHX"] == 4])
    e[("race", "other_incl_asian")] = p([r for r in base if r["RACETHX"] in (4, 5)])
    for k in ("private", "medicare", "medicaid", "uninsured", "other_public"):
        e[("ins", k)] = p([r for r in base if ins558(r) == k])
    _health(e, base, p)
    for k in ("private", "medicare", "medicaid", "uninsured"):
        sub = [r for r in base if ins558(r) == k]
        e[("insgh", k, "good")] = p([r for r in sub if r["RTHLTH31"] in (1, 2, 3)])
        e[("insgh", k, "fp")] = p([r for r in sub if r["RTHLTH31"] in (4, 5)])
    flags = [(r, conds(r)) for r in base]
    for c in COND9:
        e[("cond", c)] = p([r for r, f in flags if f[c]])
    n9 = [(r, sum(f.values())) for r, f in flags]
    n8 = [(r, sum(v for k, v in f.items() if k != "smoker")) for r, f in flags]
    e[("cond", "none")] = p([r for r, n in n9 if n == 0])
    e[("ncond", "none")] = e[("cond", "none")]
    e[("ncond8", "none")] = p([r for r, n in n8 if n == 0])
    for k in (1, 2, 3, 4):
        e[("ncond_ge", k)] = p([r for r, n in n9 if n >= k])
        e[("ncond8_ge", k)] = p([r for r, n in n8 if n >= k])
    return e


# ---- #493, #496, #497 (HC-171, 2014) ----

CATS493 = ("any", "ip", "amb", "rx", "dent", "hho")
COMPONENTS = ("ip", "amb", "rx", "dent", "hho")


def age14(r):
    """Age at the end of 2014 (AGE14X); AGELAST for persons out of scope by then (AGE14X = -1)."""
    return r["AGE14X"] if r["AGE14X"] >= 0 else r["AGELAST"]


def cat_values(r, yy="14"):
    return {"any": r["TOTEXP" + yy], "ip": r["IPTEXP" + yy],
            "amb": r["OBVEXP" + yy] + r["OPTEXP" + yy] + r["ERTEXP" + yy],
            "rx": r["RXEXP" + yy], "dent": r["DVTEXP" + yy],
            "hho": r["HHAEXP" + yy] + r["HHNEXP" + yy] + r["VISEXP" + yy] + r["OTHEXP" + yy]}


def est493(recs):
    w = "PERWT14F"
    base = [r for r in recs if r[w] > 0]
    cols = {"all": base, "lt65": [r for r in base if age14(r) < 65],
            "ge65": [r for r in base if age14(r) >= 65]}
    e = {}
    for col, sub in cols.items():
        vals = [(cat_values(r), r[w]) for r in sub]
        total_w = sum(x for _, x in vals)
        for c in CATS493:
            pos = [(v[c], x) for v, x in vals if v[c] > 0]
            sw = sum(x for _, x in pos)
            e[("pct", c, col)] = 100.0 * sw / total_w if total_w > 0 else None
            e[("mean", c, col)] = sum(v * x for v, x in pos) / sw if sw > 0 else None
            e[("median", c, col)] = wmedian(pos)
    e[("n", "sum_mismatch")] = sum(
        1 for r in base if abs(sum(cat_values(r)[c] for c in COMPONENTS) - r["TOTEXP14"]) > 1.0)
    e[("n", "age14_fallback")] = sum(1 for r in base if r["AGE14X"] < 0)
    return e


TIERS = ("none", "low", "middle", "high")
BANDS496 = (("0-17", 0, 17), ("18-44", 18, 44), ("45-64", 45, 64), ("65+", 65, 200))


def tiers(persons):
    """persons: (id, weight > 0, expenditure, record). R2's ranking rule: high = top 10%, middle = the rest
    of the top 50%, then low (positive spending) and none (zero spending) in the bottom 50%."""
    order = sorted(persons, key=lambda p: (-p[2], p[1], p[0]))
    cw = [0.0]
    for p in order:
        cw.append(cw[-1] + p[1])
    k10 = r2conc.top_k(cw, cw[-1], 10)
    k50 = r2conc.top_k(cw, cw[-1], 50)
    out = []
    for i, p in enumerate(order):
        t = "high" if i < k10 else "middle" if i < k50 else ("none" if p[2] == 0 else "low")
        out.append((t, p))
    return out


def est496(recs):
    w, x = "PERWT14F", "TOTEXP14"
    persons = [(r["id"], r[w], r[x], r) for r in recs if r[w] > 0]
    tagged = tiers(persons)
    all_w = sum(p[1] for p in persons)
    e = {}
    for t in TIERS:
        in_t = [p for tt, p in tagged if tt == t]
        tw = sum(p[1] for p in in_t)
        e[("tier_share", t)] = 100.0 * tw / all_w if all_w > 0 else None
        for lab, lo, hi in BANDS496:
            e[("agedist", lab, t)] = (100.0 * sum(p[1] for p in in_t if lo <= age14(p[3]) <= hi) / tw
                                      if tw > 0 else None)
        for band, lo, hi in (("0-17", 0, 17), ("18-64", 18, 64)):
            sub = [p for p in in_t if lo <= age14(p[3]) <= hi]
            sw = sum(p[1] for p in sub)
            for ins in (1, 2, 3):
                e[("insdist", band, ins, t)] = (100.0 * sum(p[1] for p in sub if p[3]["INSCOV14"] == ins) / sw
                                                if sw > 0 else None)
    return e


BANDS497 = (("65+", 65, 200), ("45-64", 45, 64), ("18-44", 18, 44), ("0-17", 0, 17))
F2_497 = ("Bottom 50%", "Top 50%", "Top 30%", "Top 10%", "Top 5%", "Top 1%")
F4_497 = ("Bottom 50%", "Top 50%", "Top 10%", "Top 5%")


def est497(recs):
    w, x = "PERWT14F", "TOTEXP14"
    persons = [(r["id"], r[w], r[x], age14(r)) for r in recs if r[w] > 0]
    e = dict(r2conc.summarize(persons))
    all_w = sum(p[1] for p in persons)
    total = sum(p[1] * p[2] for p in persons)
    for lab, lo, hi in BANDS497:
        sub = [p for p in persons if lo <= p[3] <= hi]
        e[("popshare", lab)] = 100.0 * sum(p[1] for p in sub) / all_w if all_w > 0 else None
        e[("expshare", lab)] = 100.0 * sum(p[1] * p[2] for p in sub) / total if total > 0 else None
        se = r2conc.summarize(sub)
        for g in F4_497:
            e[("agemean", lab, g)] = se[("mean", g)]
    return e


# ---- #533 (HC-209, 2018): R2's concentration layout ----

def est533(recs):
    persons = [(r["id"], r["PERWT18F"], r["TOTEXP18"], int(r["AGELAST"])) for r in recs if r["PERWT18F"] > 0]
    return dict(r2conc.summarize(persons))


ESTIMATORS = {554: est554, 558: est558, 493: est493, 496: est496, 497: est497, 533: est533}


# ---- graded cells, in page order (seq 1..N of the transcription) ----

def _keys():
    k = {}
    a = [("age", b) for b, _, _ in AGE_554]
    a += [("race", 2), ("race", 3), ("race", 1), ("race", "other"), ("sex", 1), ("sex", 2)]
    a += [("region", c) for c in (1, 2, 3, 4)] + [("msa", "Yes"), ("msa", "No")]
    for key in ("gh", "mh"):
        a += [(key, 1), (key, 2), (key, 3), (key, "fp")]
    a += [("smoke", "yes"), ("smoke", "no"), ("asthma", 1), ("asthma", 2), ("all_adults",)]
    k[554] = a
    b = [("total",)] + [("age", lab) for lab, _, _ in AGE_558]
    b += [("race", 2), ("race", 3), ("race", 1), ("race", "other")]
    b += [("ins", i) for i in ("private", "medicare", "medicaid", "uninsured")]
    for key in ("gh", "mh"):
        b += [(key, 1), (key, 2), (key, 3), (key, "fp")]
    for i in ("private", "medicare", "medicaid"):
        b += [("insgh", i, "good"), ("insgh", i, "fp")]
    b += [("cond", "none")] + [("cond", c) for c in COND9]
    b += [("ncond", "none"), ("ncond_ge", 2), ("ncond_ge", 3)]
    k[558] = b
    c = [(kind, cat, col) for kind in ("pct", "mean") for cat in CATS493 for col in ("all", "lt65", "ge65")]
    c += [("median", "any", "all"), ("median", "any", "lt65"), ("median", "any", "ge65"), ("median", "ip", "all")]
    k[493] = c
    d = [("agedist", lab, t) for lab, _, _ in BANDS496 for t in TIERS]
    d += [("insdist", "0-17", i, t) for i in (1, 2, 3) for t in TIERS]
    d += [("insdist", "18-64", i, t) for i in (1, 2, 3) for t in TIERS]
    k[496] = d
    f = []
    for p in r2conc.CURVE_P:
        f += [("cumpct", p), ("total", p)]
    f += [("mean", g) for g in F2_497]
    for lab, _, _ in BANDS497:
        f += [("popshare", lab), ("expshare", lab)]
    f += [("agemean", "0-17", g) for g in F4_497]
    k[497] = f
    h = []
    for p in r2conc.CURVE_P:
        h += [("cumpct", p), ("total", p)]
    h += [("total", 100)] + [("mean", g) for g in r2conc.GROUPS] + [("nc", i) for i in range(1, 11)]
    k[533] = h
    return k


KEYS = _keys()


def underspecified(brief, key):
    """Cells whose value depends on a choice the brief does not state (see the specification)."""
    if brief in (554, 558):
        return True  # no weight is named; SDOHWT21F is our reading
    if brief == 493:
        return not (key[0] in ("pct", "mean") and key[1] == "any" and key[2] == "all")
    if brief in (497, 533):
        return key[0] in ("cumpct", "total", "agemean")
    return False


def msa_check(inv_rows):
    """#554 Figure 3 MSA cells: not computable if no variable name or description mentions MSA or METRO and
    the positive control REGION31 is listed."""
    names = {r["name"] for r in inv_rows}
    hits = [r["name"] for r in inv_rows
            if "MSA" in r["name"].upper() or "MSA" in r.get("description", "").upper()
            or "METRO" in r.get("description", "").upper()]
    res = {"msa_variables": hits, "positive_control": "REGION31", "positive_found": "REGION31" in names}
    res["not_computable"] = not hits and res["positive_found"]
    return res


def load_cells(path, brief):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if int(r["brief"]) == brief and r["graded"] == "1"]
    rows.sort(key=lambda r: int(r["seq"]))
    return rows


def keystr(key):
    return "|".join(str(p) for p in key)


def evaluate(brief, cells, est, not_computable):
    keys = KEYS[brief]
    if len(cells) != len(keys):
        raise ValueError("brief %d: %d graded cells, %d keys" % (brief, len(cells), len(keys)))
    out = []
    for cell, key in zip(cells, keys):
        r = {"seq": int(cell["seq"]), "source": cell["source"], "group": cell["group"], "row": cell["row"],
             "column": cell["column"], "published": cell["value"], "unit": cell["unit"], "key": keystr(key),
             "underspecified": underspecified(brief, key)}
        if key[0] in ("msa", "nc"):
            r.update(status="not computable" if not_computable else "unresolved", value=None, gap=None,
                     exact=None, close=None)
        else:
            v = est.get(key)
            if v is None:
                r.update(status="no estimate", value=None, gap=None, exact=False, close=False)
            else:
                kind = "cumpct" if cell["unit"] == "pct" else "mean"
                gap, exact, close = r2conc.match(kind, v, cell["value"])
                r.update(status="computed", value=v, gap=gap, exact=exact, close=close)
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", type=int, required=True, choices=sorted(BRIEF_FILE))
    ap.add_argument("--data", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    fname = BRIEF_FILE[a.brief]
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "brief": a.brief, "file": fname, "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["data"] = {"file": os.path.basename(a.data), "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
        del raw
        inv = r2conc.read_inventory(a.inventory)
        pos = r2conc.positions(inv, FIELDS[fname])
        out["positions"] = pos
        rows = r2conc.load_ascii(a.data, pos)
        g = gate(rows, GATES[fname])
        out["gate"] = g
        if g["passed"]:
            recs = [to_rec(r) for r in rows]
            del rows
            est = ESTIMATORS[a.brief](recs)
            nc = False
            if a.brief == 554:
                out["msa_check"] = msa_check(inv)
                nc = out["msa_check"]["not_computable"]
            elif a.brief == 533:
                out["condition_check"] = r2conc.condition_check(inv, "18")
                nc = out["condition_check"]["not_computable"]
            res = evaluate(a.brief, load_cells(a.cells, a.brief), est, nc)
            out["cells"] = res
            out["tally"] = r2conc.tally(res)
            out["estimates"] = {keystr(k): v for k, v in est.items()}
            with open(os.path.join(a.out_dir, "cells-%d.csv" % a.brief), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["seq", "source", "row", "column", "published", "value", "gap", "exact", "close",
                            "status", "underspecified"])
                for r in res:
                    w.writerow([r["seq"], r["source"], r["row"], r["column"], r["published"],
                                None if r["value"] is None else round(r["value"], 4),
                                None if r["gap"] is None else round(r["gap"], 4), r["exact"], r["close"],
                                r["status"], r["underspecified"]])
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r2b-%d.json" % a.brief), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"brief": a.brief, "gate_passed": (out.get("gate") or {}).get("passed"),
                      "tally": out.get("tally"), "error": out["error"]}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
