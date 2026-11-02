# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R1 addendum (exploratory, dated 2026-11-02): which definition choices move the five #569 cells that
check R1 v1 did not reproduce to the published decimal (F2a, F4b, F7a, F7b, F7c)?

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r569-addendum-prereg-v1-2026-11-02.md (evidence-pack). The addendum never
regrades R1 v1; it reports variants side by side. Reads the HC-243 public-use file from a local zip (never
downloads it) and writes aggregate estimates for the brief's published cells only. Research information about
published statistics, not medical advice.
"""
import argparse
import csv
import hashlib
import json
import os
import tempfile
import zipfile

from meps import r569

VERSION = "0.1.0"

EXTRA = ["REGION53", "PERWT22F"]
COLUMNS = list(r569.COLUMNS) + [c for c in EXTRA if c not in r569.COLUMNS]

# R1 v1 results (cells.csv of job meps-r569-v1, 3 decimals): the gate for variant A.
V1 = {"F1a": 21.455, "F1b": 9.167, "F1c": 33.771, "F2a": 42.75, "F2b": 24.799, "F2c": 67.57,
      "F3a": 27.879, "F3b": 17.423, "F4a": 69.447, "F4b": 72.469, "F4c": 45.849, "F5a": 30.655,
      "F5b": 45.331, "F6a": 25.392, "F6b": 47.686, "F6c": 37.14, "F6d": 30.417, "F7a": 44.034,
      "F7b": 44.129, "F7c": 41.978, "F7d": 41.744, "F8a": 37.461, "F8b": 38.868, "F8c": 47.6}
V1_EXACT = 19
MISSES = ("F2a", "F4b", "F7a", "F7b", "F7c")


def age_age22(p):
    """End-of-year age first: AGE22X, then AGE42X, AGE31X (ignores AGELAST)."""
    return r569.first_nonneg(p, ("AGE22X", "AGE42X", "AGE31X"))


def dexa_universe_u3(p):
    """Scan denominator that also keeps women whose osteoporosis answer is 'cannot be computed' (-15)."""
    return p.get("ADOSTP42") in (2, -15) and p.get("ADBNDN42") in (1, 2)


# Variant: name -> settings. "age50" is how the 50+ cells select age; bands always use "ageband".
BASE = {"age50": "primary", "ageband": r569.age_primary, "region": "REGION22",
        "dexa_u": r569.dexa_universe, "weight": "SAQWT22F"}


def _v(**kw):
    d = dict(BASE)
    d.update(kw)
    return d


VARIANTS = {
    "A": _v(),
    "REG42": _v(region="REGION42"),
    "REG31": _v(region="REGION31"),
    "REG53": _v(region="REGION53"),
    "C2": _v(age50="adage4"),
    "AGE22": _v(ageband=age_age22, age50="age22"),
    "U3": _v(dexa_u=dexa_universe_u3),
    "PW": _v(weight="PERWT22F"),
}
ORDER = ["A", "REG42", "REG31", "REG53", "C2", "AGE22", "U3", "PW"]


def in_age(p, band, v):
    if band == "50+":
        if v["age50"] == "adage4":
            return p.get("ADAGE42") == 4
        if v["age50"] == "age22":
            return r569.in_band(age_age22(p), band)
        return r569.in_band(r569.age_primary(p), band)
    return r569.in_band(v["ageband"](p), band)


def estimate_w(persons, member, outcome, wvar):
    """Weighted share (%) among members who completed the SAQ (SAQWT22F > 0), weighted by `wvar`."""
    sw = 0.0
    swy = 0.0
    n = 0
    for p in persons:
        s = p.get("SAQWT22F")
        w = p.get(wvar)
        if s is None or not s > 0 or w is None or not w > 0 or not member(p):
            continue
        n += 1
        sw += w
        if outcome(p):
            swy += w
    if sw <= 0:
        return {"n": n, "pct": None}
    return {"n": n, "pct": 100.0 * swy / sw}


def cell_sub(cid, sub, v):
    """Subgroup predicate; Figure 7 region cells use the variant's region variable."""
    if cid in ("F7a", "F7b", "F7c", "F7d"):
        code = {"F7a": 1, "F7b": 2, "F7c": 3, "F7d": 4}[cid]
        var = v["region"]
        return lambda p: p.get(var) == code
    return sub


def evaluate_v(persons, v):
    out = []
    female = lambda p: p.get("SEX") == 2  # noqa: E731
    for cid, fig, label, pub, outcome, band, sub in r569.CELLS:
        if outcome == "osteo":
            uni, yes = r569.osteo_universe, r569.osteo_yes
        else:
            uni, yes = v["dexa_u"], r569.dexa_yes
        s = cell_sub(cid, sub, v)

        def member(p, uni=uni, band=band, s=s):
            return female(p) and in_age(p, band, v) and uni(p) and s(p)
        e = estimate_w(persons, member, yes, v["weight"])
        pct = e["pct"]
        diff = None if pct is None else pct - pub
        out.append({"cid": cid, "published": pub, "pct": pct, "n": e["n"], "diff": diff,
                    "exact": diff is not None and abs(diff) <= 0.05 + 1e-9,
                    "rounds": pct is not None and _rounds_to(pct, pub),
                    "close": diff is not None and abs(diff) <= 0.5 + 1e-9})
    return out


def _rounds_to(x, pub):
    """True if x rounds half-up to the published one-decimal value (reported alongside +-0.05)."""
    import math
    return abs(math.floor(x * 10 + 0.5) / 10.0 - pub) < 1e-9


def summarize(rows):
    d = {r["cid"]: r for r in rows}
    return {"exact": sum(1 for r in rows if r["exact"]),
            "rounds": sum(1 for r in rows if r["rounds"]),
            "close": sum(1 for r in rows if r["close"]),
            "fig7_exact": sum(1 for c in ("F7a", "F7b", "F7c", "F7d") if d[c]["exact"]),
            "misses_now_exact": [c for c in MISSES if d[c]["exact"]],
            "v1_exact_now_not": [r["cid"] for r in rows if r["cid"] not in MISSES and not r["exact"]]}


def gate(rows_a):
    """Variant A must reproduce R1 v1: every cell within 0.0005 of the v1 value and 19 exact."""
    bad = [r["cid"] for r in rows_a if r["pct"] is None or abs(r["pct"] - V1[r["cid"]]) > 0.0005 + 1e-9]
    ex = sum(1 for r in rows_a if r["exact"])
    return {"passed": not bad and ex == V1_EXACT, "cells_off": bad, "exact": ex}


def readings(summ):
    """Fixed readings from the pre-registration (descriptive, not a regrade)."""
    out = {}
    out["region"] = [k for k in ("REG42", "REG31", "REG53") if summ[k]["fig7_exact"] == 4]
    out["X1_pw_control"] = {"exact": summ["PW"]["exact"],
                            "grade": "held" if summ["PW"]["exact"] < V1_EXACT else "failed"}
    out["candidates"] = [k for k in ORDER[1:] if k != "PW" and summ[k]["exact"] > V1_EXACT]
    return out


def load(zip_path, columns=None):
    import pandas as pd  # only needed for the real run
    columns = columns or COLUMNS
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".dta")]
        if not names:
            raise RuntimeError("no .dta file in %s" % zip_path)
        path = z.extract(names[0], tmp)
    with pd.read_stata(path, iterator=True) as rd:
        available = list(rd.variable_labels().keys())
    cols = [c for c in columns if c in available]
    missing = [c for c in columns if c not in available]
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
    out = {"version": VERSION, "error": None}
    try:
        with open(a.data, "rb") as f:
            raw = f.read()
        out["h243"] = {"file": os.path.basename(a.data), "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
        persons, missing = load(a.data)
        out["persons"] = len(persons)
        out["missing_columns"] = missing
        res = {k: evaluate_v(persons, VARIANTS[k]) for k in ORDER}
        out["gate"] = gate(res["A"])
        summ = {k: summarize(res[k]) for k in ORDER}
        out["summary"] = summ
        out["readings"] = readings(summ)
        out["variants"] = {k: [{"cid": r["cid"], "pct": r["pct"], "n": r["n"], "exact": r["exact"],
                                "rounds": r["rounds"]} for r in res[k]] for k in ORDER}
        with open(os.path.join(a.out_dir, "variants.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["variant", "cid", "published", "pct", "n", "diff", "exact", "rounds"])
            for k in ORDER:
                for r in res[k]:
                    w.writerow([k, r["cid"], r["published"], None if r["pct"] is None else round(r["pct"], 4),
                                r["n"], None if r["diff"] is None else round(r["diff"], 4), r["exact"],
                                r["rounds"]])
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r569x.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"gate": out.get("gate"), "readings": out.get("readings"), "error": out["error"]},
                     indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
