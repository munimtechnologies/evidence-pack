# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R2, concentration briefs: recompute the in-scope published cells of MEPS Statistical Briefs
#506 (2015, HC-181), #521 (2016, HC-192) and #540 (2019, HC-216) from the one Full Year Consolidated
public-use file each brief names, read from its fixed-width ASCII zip (never downloaded by this code).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r2-prereg-v1-2026-11-02.md; specification (fixed before any job reads a
file): findings/meps-r2-spec-conc-v1-2026-11-03.md (evidence-pack). Column positions come from the
published codebook inventory (findings/meps-inventory-v1/inventory/H<nnn>.csv). Only aggregate estimates
for published cells leave the job. Research information about published statistics, not medical advice.
"""
import argparse
import bisect
import csv
import hashlib
import io
import json
import os
import zipfile
from decimal import ROUND_HALF_UP, Decimal

VERSION = "0.1.0"

CURVE_P = (10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99)
GROUPS = ("Overall", "Bottom 50%", "Top 50%", "Top 30%", "Top 10%", "Top 5%", "Top 1%")
F3_GROUPS = ("Overall", "Bottom 50%", "Top 50%", "Top 10%", "Top 5%")
TOP_Q = (50, 30, 10, 5, 1)


def _gid(g):
    return g.replace(" ", "").replace("%", "")


def curve_cells(cum, tot):
    """Figure 1 cells in page order (row-major): rows 10..99 give cumulative % then total ($ billions);
    row 100 gives the total only. The anchors (row 0 both columns, row 100 cumulative %) are not estimates."""
    if len(cum) != len(CURVE_P) or len(tot) != len(CURVE_P) + 1:
        raise ValueError("curve lengths")
    out = []
    for p, c, t in zip(CURVE_P, cum, tot[:-1]):
        out.append(("F1-p%d-cum" % p, 1, "cumpct", p, c))
        out.append(("F1-p%d-total" % p, 1, "total", p, t))
    out.append(("F1-p100-total", 1, "total", 100, tot[-1]))
    return out


def mean_cells(texts):
    if len(texts) != len(GROUPS):
        raise ValueError("means length")
    return [("F2-%s" % _gid(g), 2, "mean", g, t) for g, t in zip(GROUPS, texts)]


def age_cells(r017, r1844):
    out = []
    for band, texts in (("0-17", r017), ("18-44", r1844)):
        if len(texts) != len(F3_GROUPS):
            raise ValueError("age row length")
        for g, t in zip(F3_GROUPS, texts):
            out.append(("F3-%s-%s" % (band, _gid(g)), 3, "agepct", (band, g), t))
    return out


def nc_cells(rows):
    out = []
    for i, (label, overall, top5) in enumerate(rows, 1):
        out.append(("F3-c%d-Overall" % i, 3, "nc", label + " / Overall", overall))
        out.append(("F3-c%d-Top5" % i, 3, "nc", label + " / Top 5%", top5))
    return out


# Published text of every in-scope cell, typed from two reads of each brief page (census M3 rows and a
# WebFetch "copy every cell exactly" read, 2026-11-03); both reads agreed on every cell.
BRIEFS = {
    506: {"file": "H181", "yy": "15", "zip": "h181dat.zip", "rows": 35427, "pos_wt": 33893, "zero_exp": 6936,
          "cells": curve_cells(
              ["0", "0.1", "0.5", "1.3", "2.8", "5.3", "9.7", "17.5", "33.2", "49.2", "77.5"],
              ["0", "1.1", "7.4", "20.7", "44.6", "85.2", "154.6", "279.8", "530.7", "787.6", "1239.2",
               "1599.9"])
          + mean_cells(["4,978", "278", "9,678", "14,990", "33,269", "50,572", "112,395"])
          + age_cells(["23.1", "31.5", "14.6", "5.1", "4.0"], ["35.3", "43.6", "27.0", "19.7", "16.3"])},
    521: {"file": "H192", "yy": "16", "zip": "h192dat.zip", "rows": 34655, "pos_wt": 33259, "zero_exp": 6933,
          "cells": curve_cells(
              ["0", "0.1", "0.4", "1.3", "2.8", "5.3", "9.8", "17.8", "34.0", "50.0", "78.1"],
              ["0", "0.9", "7.1", "20.4", "44.6", "86.0", "157.9", "288.2", "549.5", "809.1", "1,263.2",
               "1,617.5"])
          + mean_cells(["5,006", "276", "9,735", "15,057", "33,053", "50,077", "110,003"])
          + age_cells(["22.9", "30.9", "14.9", "6.5", "5.1"], ["35.2", "43.4", "26.9", "20.4", "17.9"])},
    540: {"file": "H216", "yy": "19", "zip": "h216dat.zip", "rows": 28512, "pos_wt": 27648, "zero_exp": 4292,
          "cells": curve_cells(
              ["0.0", "0.1", "0.5", "1.4", "3.0", "5.7", "10.4", "18.6", "35.0", "51.2", "79.3"],
              ["0", "1.7", "10.2", "28.4", "61.2", "117.5", "213.1", "380.7", "716.5", "1,048.6", "1,622.3",
               "2,046.8"])
          + mean_cells(["6,252", "374", "12,130", "18,669", "40,638", "61,007", "130,087"])
          + nc_cells([("Diabetes mellitus", "7.6", "26.2"),
                      ("COPD, asthma, and other respiratory conditions", "11.7", "28.4"),
                      ("Heart disease", "6.7", "28.8"), ("Hyperlipidemia", "13.5", "35.1"),
                      ("Mental disorders", "15.7", "36.3")])},
}


def _clean(text):
    return text.replace(",", "").replace("$", "").replace("%", "").strip()


def dec_places(text):
    t = _clean(text)
    return len(t.split(".")[1]) if "." in t else 0


def pub_value(text):
    return Decimal(_clean(text))


def rounds_to(value, text):
    """True if value, rounded half-up to the printed precision, equals the printed number."""
    q = Decimal(1).scaleb(-dec_places(text))
    return Decimal(repr(float(value))).quantize(q, rounding=ROUND_HALF_UP) == pub_value(text)


def match(kind, value, text):
    """(gap, exact, close). Percentages: close within 0.5 points. Means and totals: within 1% of the
    published value; a published 0 is close only if the value rounds to 0 at the printed precision."""
    pub = float(pub_value(text))
    gap = value - pub
    exact = rounds_to(value, text)
    if kind in ("cumpct", "agepct"):
        close = abs(gap) <= 0.5 + 1e-9
    elif pub == 0:
        close = exact
    else:
        close = abs(gap) <= 0.01 * abs(pub) + 1e-9
    return gap, exact, close


def read_inventory(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def positions(inv_rows, names):
    """{name: (start, end)} (1-based, inclusive) for each name, from the codebook inventory."""
    found = {}
    for r in inv_rows:
        if r["name"] in names:
            found[r["name"]] = (int(r["start"]), int(r["end"]))
    missing = [n for n in names if n not in found]
    if missing:
        raise KeyError("not in inventory: %s" % ", ".join(missing))
    return found


def load_ascii(zip_path, fields):
    """Rows of the fixed-width .dat member as {name: stripped text}."""
    with zipfile.ZipFile(zip_path) as z:
        members = [n for n in z.namelist() if not n.endswith("/")]
        dat = [n for n in members if n.lower().endswith(".dat")] or members
        if not dat:
            raise RuntimeError("empty zip %s" % zip_path)
        rows = []
        with z.open(dat[0]) as f:
            for raw in io.TextIOWrapper(f, encoding="latin-1", newline=""):
                line = raw.rstrip("\r\n")
                if not line.strip():
                    continue
                rows.append({k: line[s - 1:e].strip() for k, (s, e) in fields.items()})
    return rows


def gate(rows, spec, names):
    w, x, age = names["w"], names["x"], names["age"]
    ws = [float(r[w]) for r in rows]
    xs = [float(r[x]) for r in rows]
    ages = [int(r[age]) for r in rows]
    g = {"rows": len(rows), "rows_expected": spec["rows"],
         "positive_weight": sum(1 for v in ws if v > 0), "positive_weight_expected": spec["pos_wt"],
         "zero_expense": sum(1 for v in xs if v == 0), "zero_expense_expected": spec["zero_exp"],
         "age_out_of_range": sum(1 for a in ages if not 0 <= a <= 85),
         "negative_expense": sum(1 for v in xs if v < 0)}
    g["passed"] = (g["rows"] == g["rows_expected"] and g["positive_weight"] == g["positive_weight_expected"]
                   and g["zero_expense"] == g["zero_expense_expected"] and g["age_out_of_range"] == 0
                   and g["negative_expense"] == 0)
    return g


def top_k(cw, total_w, q):
    """Length of the top-q% prefix: the most persons, in order, whose cumulative weight <= q% of all weight."""
    return bisect.bisect_right(cw, q * total_w / 100.0) - 1


def summarize(persons):
    """persons: (id, weight > 0, total expenditure, age). Order: expenditure high to low, then lower weight
    first (ties go to the higher group), then id. Returns {(kind, arg): estimate}."""
    order = sorted(persons, key=lambda r: (-r[2], r[1], r[0]))
    cw, cwx, c17, c44 = [0.0], [0.0], [0.0], [0.0]
    for _, w, x, a in order:
        cw.append(cw[-1] + w)
        cwx.append(cwx[-1] + w * x)
        c17.append(c17[-1] + (w if 0 <= a <= 17 else 0.0))
        c44.append(c44[-1] + (w if 18 <= a <= 44 else 0.0))
    n, W, T = len(order), cw[-1], cwx[-1]
    est = {}
    for p in CURVE_P:
        k = top_k(cw, W, 100 - p)
        bx = T - cwx[k]
        est[("cumpct", p)] = 100.0 * bx / T if T > 0 else None
        est[("total", p)] = bx / 1e9
    est[("total", 100)] = T / 1e9
    kb = top_k(cw, W, 50)
    groups = {"Overall": (n, W, T, c17[-1], c44[-1]),
              "Bottom 50%": (n - kb, W - cw[kb], T - cwx[kb], c17[-1] - c17[kb], c44[-1] - c44[kb])}
    for q in TOP_Q:
        k = top_k(cw, W, q)
        groups["Top %d%%" % q] = (k, cw[k], cwx[k], c17[k], c44[k])
    for g, (cnt, sw, swx, s17, s44) in groups.items():
        est[("n", g)] = cnt
        est[("mean", g)] = swx / sw if sw > 0 else None
        est[("agepct", ("0-17", g))] = 100.0 * s17 / sw if sw > 0 else None
        est[("agepct", ("18-44", g))] = 100.0 * s44 / sw if sw > 0 else None
    return est


def condition_check(inv_rows, yy):
    """Treated-condition cells need event-level condition codes (CCSR / ICD-10), which an FYC file does not
    carry. Not computable if no such variable is listed, the positive control TOTEXPyy is listed and the
    negative control ICD10CDX (a Medical Conditions file variable) is not."""
    names = {r["name"] for r in inv_rows}
    hits = []
    for r in inv_rows:
        nm = r["name"].upper()
        desc = r.get("description", "").upper()
        if nm.startswith(("CCS", "ICD")) or "CCSR" in desc or "ICD-10" in desc or "ICD10" in desc \
                or "CLINICAL CLASSIFICATION" in desc:
            hits.append(r["name"])
    pos = "TOTEXP%s" % yy
    res = {"condition_variables": hits, "positive_control": pos, "positive_found": pos in names,
           "negative_control": "ICD10CDX", "negative_found": "ICD10CDX" in names}
    res["not_computable"] = not hits and res["positive_found"] and not res["negative_found"]
    return res


def evaluate(cells, est, cc=None):
    out = []
    for cid, fig, kind, arg, text in cells:
        # The concentration-curve construction is not stated in the briefs (spec: our reading).
        r = {"cid": cid, "figure": fig, "kind": kind, "published": text,
             "underspecified": kind in ("cumpct", "total")}
        if kind == "nc":
            nc = cc is not None and cc["not_computable"]
            r.update(status="not computable" if nc else "unresolved", value=None, gap=None, exact=None,
                     close=None)
        else:
            v = est.get((kind, arg))
            if v is None:
                r.update(status="no estimate", value=None, gap=None, exact=False, close=False)
            else:
                gap, exact, close = match(kind, v, text)
                r.update(status="computed", value=v, gap=gap, exact=exact, close=close)
        out.append(r)
    return out


def tally(results):
    comp = [r for r in results if r["status"] in ("computed", "no estimate")]
    t = {"cells": len(results), "computable": len(comp),
         "close": sum(1 for r in comp if r["close"]), "exact": sum(1 for r in comp if r["exact"]),
         "not_computable": sum(1 for r in results if r["status"] == "not computable"),
         "unresolved": sum(1 for r in results if r["status"] == "unresolved")}
    t["share_close"] = round(t["close"] / t["computable"], 4) if t["computable"] else None
    return t


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", type=int, required=True, choices=sorted(BRIEFS))
    ap.add_argument("--data", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    spec = BRIEFS[a.brief]
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "brief": a.brief, "file": spec["file"], "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["data"] = {"file": os.path.basename(a.data), "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
        del raw
        inv = read_inventory(a.inventory)
        yy = spec["yy"]
        names = {"id": "DUPERSID", "w": "PERWT%sF" % yy, "x": "TOTEXP%s" % yy, "age": "AGELAST"}
        pos = positions(inv, list(names.values()))
        out["positions"] = pos
        rows = load_ascii(a.data, pos)
        g = gate(rows, spec, names)
        out["gate"] = g
        if g["passed"]:
            persons = [(r[names["id"]], float(r[names["w"]]), float(r[names["x"]]), int(r[names["age"]]))
                       for r in rows if float(r[names["w"]]) > 0]
            est = summarize(persons)
            out["group_n"] = {grp: est[("n", grp)] for grp in GROUPS}
            cc = condition_check(inv, yy)
            out["condition_check"] = cc
            res = evaluate(spec["cells"], est, cc)
            out["cells"] = res
            out["tally"] = tally(res)
            with open(os.path.join(a.out_dir, "cells-%d.csv" % a.brief), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["cid", "figure", "kind", "published", "value", "gap", "exact", "close", "status",
                            "underspecified"])
                for r in res:
                    w.writerow([r["cid"], r["figure"], r["kind"], r["published"],
                                None if r["value"] is None else round(r["value"], 4),
                                None if r["gap"] is None else round(r["gap"], 4), r["exact"], r["close"],
                                r["status"], r["underspecified"]])
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r2conc-%d.json" % a.brief), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"brief": a.brief, "gate": out.get("gate"), "tally": out.get("tally"),
                      "error": out["error"]}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
