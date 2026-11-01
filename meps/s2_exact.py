# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check S2: exact counts of persons with an expense behind 18 published 2022 MEPS-HC summary-table cells.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-sumtab-s2-prereg-v1-2026-11-01.md (evidence-pack).
Reads the MEPS HC-243 public-use file from a local zip (never downloads it) and AHRQ's published DY2022.csv
from GitHub. Writes aggregate counts for published cells only. Research information, not medical advice.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
import time
import urllib.request
import zipfile

VERSION = "0.1.0"
SHA = "4fbd9b1617a8d73d29a6e016b803b865208a1366"
DY_URL = ("https://raw.githubusercontent.com/HHS-AHRQ/MEPS-summary-tables/%s/"
          "formatted_tables/hc_use/DY2022.csv" % SHA)
UA = "MV2-of-Munim-Inc evidence-pack s2_exact/0.1.0 (mv2@munimtech.com)"

COLUMNS = ["DUPERSID", "PERWT22F", "TOTEXP22", "AGE22X", "AGE42X", "AGE31X", "SEX", "INSCOV22",
           "INSURC22", "POVCAT22", "REGION22", "REGION42", "REGION31", "MARRY22X", "MARRY42X",
           "MARRY31X", "RACETHX", "RACEV1X", "EDUCYR", "EMPST53", "EMPST42", "EMPST31"]

AGES = ("AGE22X", "AGE42X", "AGE31X")
REGS = ("REGION22", "REGION42", "REGION31")
MARS = ("MARRY22X", "MARRY42X", "MARRY31X")
EMPS = ("EMPST53", "EMPST42", "EMPST31")

UNINS = "Uninsured, all ages"
UNINS65 = "<65, Uninsured"
RACE4 = "Amer. Indian, AK Native, or mult. races"
INAPP16 = "Inapplicable (age < 16)"
INAPP18 = "Inapplicable (age < 18)"


def first_nonneg(p, names):
    """First value among names that is not None and >= 0 (AHRQ's coalesce after negatives -> NA)."""
    for k in names:
        v = p.get(k)
        if v is not None and v >= 0:
            return v
    return None


def age(p):
    return first_nonneg(p, AGES)


def _age_lt(p, hi):
    a = age(p)
    return a is not None and a < hi


def _age_between(p, lo, hi):
    a = age(p)
    return a is not None and lo <= a <= hi


def _less_than_hs(p):
    a = age(p)
    e = p.get("EDUCYR")
    return a is not None and a >= 18 and e is not None and 0 <= e < 12


def _race4(p):
    r = p.get("RACETHX")
    return r is not None and r > 3 and p.get("RACEV1X") in (3, 6)


# (variable, level) -> list of (variant name, predicate), tried in order.
LEVELS = {
    ("sex", "Male"): [("A", lambda p: p.get("SEX") == 1)],
    ("insurance", UNINS): [("A", lambda p: p.get("INSCOV22") == 3)],
    ("insurance", UNINS65): [("A", lambda p: p.get("INSURC22") == 3)],
    ("insurance", "65+, No medicare"): [("A", lambda p: p.get("INSURC22") in (7, 8))],
    ("race", RACE4): [("A", _race4)],
    ("education", "Less than high school"): [("A", _less_than_hs)],
    ("education", INAPP18): [("A", lambda p: _age_lt(p, 18))],
    ("poverty", "Near-poor"): [("A", lambda p: p.get("POVCAT22") == 2)],
    ("agegrps", "Under 18"): [("A", lambda p: _age_lt(p, 18))],
    ("agegrps", "5-17"): [("A", lambda p: _age_between(p, 5, 17))],
    ("region", "Northeast"): [("A", lambda p: p.get("REGION22") == 1),
                              ("B", lambda p: first_nonneg(p, REGS) == 1)],
    ("married", "Separated"): [("A", lambda p: p.get("MARRY22X") == 4),
                               ("B", lambda p: first_nonneg(p, MARS) == 4)],
    ("married", INAPP16): [("A", lambda p: p.get("MARRY22X") == 6),
                           ("B", lambda p: first_nonneg(p, MARS) == 6)],
    ("employed", INAPP16): [("A", lambda p: first_nonneg(p, EMPS) is None and _age_lt(p, 16))],
}

# (cell id, row_var, rowLevels, col_var, colLevels, n expected from S1)
CELLS = [
    ("C01", "sex", "Male", "insurance", "65+, No medicare", 60),
    ("C02", "race", RACE4, "education", "Less than high school", 63),
    ("C03", "insurance", UNINS, "poverty", "Near-poor", 100),
    ("C04", "insurance", UNINS65, "poverty", "Near-poor", 97),
    ("C05", "agegrps", "Under 18", "insurance", UNINS, 105),
    ("C06", "agegrps", "Under 18", "insurance", UNINS65, 105),
    ("C07", "agegrps", "5-17", "insurance", UNINS, 90),
    ("C08", "agegrps", "5-17", "insurance", UNINS65, 90),
    ("C09", "region", "Northeast", "insurance", UNINS, 91),
    ("C10", "region", "Northeast", "insurance", UNINS65, 91),
    ("C11", "married", "Separated", "insurance", UNINS, 69),
    ("C12", "married", "Separated", "insurance", UNINS65, 68),
    ("C13", "married", INAPP16, "insurance", UNINS, 79),
    ("C14", "married", INAPP16, "insurance", UNINS65, 79),
    ("C15", "employed", INAPP16, "insurance", UNINS, 80),
    ("C16", "employed", INAPP16, "insurance", UNINS65, 80),
    ("C17", "education", INAPP18, "insurance", UNINS, 105),
    ("C18", "education", INAPP18, "insurance", UNINS65, 105),
]


def stats(persons, pred):
    """n (PERWT22F > 0), n_exp (also TOTEXP22 > 0), weighted mean of TOTEXP22 over the n_exp persons."""
    n = 0
    n_exp = 0
    sw = 0.0
    swx = 0.0
    for p in persons:
        w = p.get("PERWT22F")
        if w is None or not w > 0 or not pred(p):
            continue
        n += 1
        x = p.get("TOTEXP22")
        if x is not None and x > 0:
            n_exp += 1
            sw += float(w)
            swx += float(w) * float(x)
    mean = swx / sw if sw > 0 else None
    return {"n": n, "n_exp": n_exp, "mean": mean}


def _num(s):
    if s is None:
        return None
    s = str(s).strip()
    if s == "" or s.upper() == "NA":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_published(text):
    """DY csv text -> {(stat_var, row_var, rowLevels, col_var, colLevels): {"value", "sample_size"}} (first wins)."""
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        key = (r.get("stat_var"), r.get("row_var"), r.get("rowLevels"), r.get("col_var"), r.get("colLevels"))
        if key in out:
            continue
        ss = _num(r.get("sample_size"))
        out[key] = {"value": _num(r.get("value")), "sample_size": int(ss) if ss is not None else None}
    return out


def evaluate_cell(persons, cell, published, tol=0.005):
    cid, rv, rl, cv, cl, expected = cell
    pub_mean = published.get(("meanEXP", rv, rl, cv, cl))
    pub_med = published.get(("medEXP", rv, rl, cv, cl))
    pub_pct = published.get(("pctEXP", rv, rl, cv, cl))
    target = pub_mean["sample_size"] if pub_mean else None
    tried = []
    chosen = None
    for rn, rf in LEVELS[(rv, rl)]:
        for cn, cf in LEVELS[(cv, cl)]:
            s = stats(persons, lambda p, rf=rf, cf=cf: rf(p) and cf(p))
            tried.append({"variant": rn + cn, "n": s["n"]})
            if target is not None and s["n"] == target:
                chosen = (rn + cn, s)
                break
        if chosen:
            break
    pct = pub_pct["value"] if pub_pct else None
    if pct is not None and pct > 1.0:
        pct = pct / 100.0
    r = {"cid": cid, "row_var": rv, "rowLevels": rl, "col_var": cv, "colLevels": cl,
         "expected_n": expected, "published_n": target,
         "published_mean": pub_mean["value"] if pub_mean else None,
         "published_median": pub_med["value"] if pub_med else None,
         "pct_share": pct, "tried": tried, "variant": None, "n": None, "n_exp": None,
         "mean": None, "mean_ok": False, "passed": False}
    if chosen:
        name, s = chosen
        r.update({"variant": name, "n": s["n"], "n_exp": s["n_exp"], "mean": s["mean"]})
        pm = r["published_mean"]
        if pm is not None and s["mean"] is not None and pm != 0:
            r["mean_ok"] = abs(s["mean"] - pm) / abs(pm) <= tol
        r["passed"] = bool(r["mean_ok"])
    return r


def grade(results):
    passed = [r for r in results if r["passed"]]
    k = len(passed)
    g = {"passed_cells": k}
    if k < 5:
        g["P1"] = {"grade": "untestable", "passed": k}
    else:
        below = sum(1 for r in passed if r["n_exp"] < 60)
        g["P1"] = {"grade": "held" if below == k else "failed", "below_60": below, "passed": k,
                   "value": round(below / k, 4)}
    g["P2"] = {"grade": "held" if k >= 12 else "failed", "passed": k}
    c01 = [r for r in results if r["cid"] == "C01"]
    ok3 = bool(c01) and c01[0]["passed"] and c01[0]["n_exp"] <= 59
    g["P3"] = {"grade": "held" if ok3 else "failed",
               "n_exp": c01[0]["n_exp"] if c01 else None}
    if k < 5:
        g["P4"] = {"grade": "untestable", "passed": k}
    else:
        close = sum(1 for r in passed
                    if r["pct_share"] is not None and r["n"] and abs(r["n_exp"] / r["n"] - r["pct_share"]) <= 0.10)
        g["P4"] = {"grade": "held" if close / k >= 0.8 else "failed", "close": close, "value": round(close / k, 4)}
    est = 0
    for r in passed:
        if r["n_exp"] < 60:
            est += (1 if r["published_mean"] is not None else 0) + (1 if r["published_median"] is not None else 0)
    g["estimates_below_60"] = est
    return g


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError("fetch failed: %s (%s)" % (url, last))


def load_persons(zip_path):
    """Read only COLUMNS from the .dta inside the zip; NaN -> None. Returns (persons, missing columns)."""
    import pandas as pd  # only needed for the real run
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".dta")]
        if not names:
            raise RuntimeError("no .dta file in %s" % zip_path)
        path = z.extract(names[0], tmp)
    with pd.read_stata(path, iterator=True) as rd:
        available = list(rd.variable_labels().keys())
    cols = [c for c in COLUMNS if c in available]
    missing = [c for c in COLUMNS if c not in available]
    df = pd.read_stata(path, columns=cols, convert_categoricals=False)
    df = df.astype(object).where(df.notna(), None)
    persons = df.to_dict("records")
    for p in persons:
        for k, v in list(p.items()):
            if k != "DUPERSID" and v is not None:
                p[k] = float(v)
    return persons, missing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data/h243dta.zip")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "sha": SHA, "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["h243"] = {"file": os.path.basename(a.data), "bytes": len(raw), "sha256": sha256_bytes(raw)}
        dy = fetch(DY_URL)
        out["dy2022"] = {"bytes": len(dy), "sha256": sha256_bytes(dy)}
        published = parse_published(dy.decode("utf-8"))
        persons, missing = load_persons(a.data)
        out["persons"] = len(persons)
        out["persons_positive_weight"] = sum(1 for p in persons if p.get("PERWT22F") and p["PERWT22F"] > 0)
        out["missing_columns"] = missing
        results = [evaluate_cell(persons, c, published) for c in CELLS]
        out["cells"] = results
        out["grades"] = grade(results)
        with open(os.path.join(a.out_dir, "cells.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cid", "row_var", "rowLevels", "col_var", "colLevels", "published_n", "variant", "n",
                        "n_exp", "pct_share", "mean", "published_mean", "published_median", "mean_ok", "passed"])
            for r in results:
                w.writerow([r["cid"], r["row_var"], r["rowLevels"], r["col_var"], r["colLevels"],
                            r["published_n"], r["variant"], r["n"], r["n_exp"], r["pct_share"], r["mean"],
                            r["published_mean"], r["published_median"], r["mean_ok"], r["passed"]])
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "s2.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"grades": out.get("grades"), "error": out["error"],
                      "missing_columns": out.get("missing_columns")}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
