#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""nhanes_spiro: pre-registered NHANES check of spironolactone use and drinking
among adults with hypertension (findings/spironolactone-nhanes-prereg-2026-10-15.md).
Research information, not medical advice.

Downloads the public CDC files (DEMO, ALQ, BPQ, MCQ, RXQ_RX) for NHANES
2005-2006 to 2015-2016 and 2017-March 2020, builds one row per eligible adult,
and fits weighted least squares of ALQ130 (average drinks per drinking day,
capped at 15) on spironolactone use plus the pre-registered covariates, with
cluster-robust standard errors over (cycle, stratum, PSU).

The row-building functions are plain Python and tested in test_nhanes_spiro.py;
pandas (to read SAS transport files) and statsmodels are imported only when used.
"""
import argparse
import json
import math
import os
import time
import urllib.request

# (label, folder year, legacy folder, file name pattern, interview weight, years covered)
CYCLES = [
    ("2005-2006", "2005", "2005-2006", "{}_D", "WTINT2YR", 2.0),
    ("2007-2008", "2007", "2007-2008", "{}_E", "WTINT2YR", 2.0),
    ("2009-2010", "2009", "2009-2010", "{}_F", "WTINT2YR", 2.0),
    ("2011-2012", "2011", "2011-2012", "{}_G", "WTINT2YR", 2.0),
    ("2013-2014", "2013", "2013-2014", "{}_H", "WTINT2YR", 2.0),
    ("2015-2016", "2015", "2015-2016", "{}_I", "WTINT2YR", 2.0),
    ("2017-2020", "2017", "2017-2018", "P_{}", "WTINTPRP", 3.2),
]
TOTAL_YEARS = sum(c[5] for c in CYCLES)  # 15.2
FILES = ["DEMO", "ALQ", "BPQ", "MCQ", "RXQ_RX"]

SPIRO = "SPIRONOLACTONE"
OTHER_MRA = {"EPLERENONE", "FINERENONE"}
# Comparator antihypertensive ingredients (generic names as NHANES writes them).
# Eye-drop beta blockers (timolol, betaxolol) and guanfacine (mostly ADHD) are left out.
ANTIHYPERTENSIVES = {
    # ACE inhibitors
    "BENAZEPRIL", "CAPTOPRIL", "ENALAPRIL", "FOSINOPRIL", "LISINOPRIL", "MOEXIPRIL",
    "PERINDOPRIL", "QUINAPRIL", "RAMIPRIL", "TRANDOLAPRIL",
    # angiotensin receptor blockers and renin inhibitor
    "AZILSARTAN", "CANDESARTAN", "EPROSARTAN", "IRBESARTAN", "LOSARTAN", "OLMESARTAN",
    "TELMISARTAN", "VALSARTAN", "ALISKIREN",
    # calcium channel blockers
    "AMLODIPINE", "DILTIAZEM", "FELODIPINE", "ISRADIPINE", "NICARDIPINE", "NIFEDIPINE",
    "NISOLDIPINE", "VERAPAMIL",
    # thiazide and thiazide-like diuretics
    "CHLOROTHIAZIDE", "CHLORTHALIDONE", "HYDROCHLOROTHIAZIDE", "INDAPAMIDE", "METOLAZONE",
    # loop diuretics
    "BUMETANIDE", "FUROSEMIDE", "TORSEMIDE",
    # other potassium-sparing diuretics
    "AMILORIDE", "TRIAMTERENE",
    # beta blockers
    "ACEBUTOLOL", "ATENOLOL", "BISOPROLOL", "CARVEDILOL", "LABETALOL", "METOPROLOL",
    "NADOLOL", "NEBIVOLOL", "PINDOLOL", "PROPRANOLOL",
    # alpha blockers, central agents, vasodilators
    "DOXAZOSIN", "PRAZOSIN", "TERAZOSIN", "CLONIDINE", "METHYLDOPA", "HYDRALAZINE",
    "MINOXIDIL",
}
RACES = [1, 2, 4, 5]          # RIDRETH1; 3 (non-Hispanic White) is the reference
EDUCATION = [0, 1, 2, 3, 4]   # DMDEDUC2; 5 (college graduate) is the reference, 0 = unknown


def code(v):
    """NHANES numeric value -> int, or None if missing. SAS transport zeros
    come back as about 5e-79, so values are rounded."""
    if v is None or isinstance(v, (str, bytes)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return int(round(f))


def ingredients(name):
    """'Hydrochlorothiazide; Spironolactone' -> ['HYDROCHLOROTHIAZIDE', 'SPIRONOLACTONE']."""
    if isinstance(name, bytes):
        name = name.decode("latin-1")
    if not isinstance(name, str):
        return []
    return [p.strip().upper() for p in name.split(";") if p.strip()]


def summarize_rx(records):
    """records: (seqn, drug name, days taken) for prescriptions taken in the past
    month. Returns {seqn: {"spiro", "excluded", "n_other", "spiro_days"}}."""
    people = {}
    for seqn, drug, days in records:
        p = people.setdefault(seqn, {"ings": set(), "spiro_days": None})
        ings = ingredients(drug)
        p["ings"].update(ings)
        d = code(days)
        if SPIRO in ings and d is not None and 1 <= d <= 31025:
            p["spiro_days"] = d if p["spiro_days"] is None else max(p["spiro_days"], d)
    out = {}
    for seqn, p in people.items():
        out[seqn] = {
            "spiro": SPIRO in p["ings"],
            "excluded": bool(p["ings"] & OTHER_MRA),
            "n_other": len(p["ings"] & ANTIHYPERTENSIVES),
            "spiro_days": p["spiro_days"],
        }
    return out


def drinks(v):
    """ALQ130 -> drinks per drinking day capped at 15, or None (777/999, missing)."""
    c = code(v)
    if c is None or c < 1 or c > 95:
        return None
    return min(c, 15)


def heavy(y, female):
    return 1 if y >= (4 if female else 5) else 0


def analysis_row(raw, rx):
    """One participant's merged values -> analysis row, or None if not eligible
    under the pre-registered population rules."""
    age = code(raw.get("RIDAGEYR"))
    if age is None or age < 20:
        return None
    if code(raw.get("BPQ020")) != 1:
        return None
    if rx is None or rx["excluded"] or (not rx["spiro"] and rx["n_other"] == 0):
        return None
    if code(raw.get("MCQ160B")) != 2 or code(raw.get("MCQ160L")) != 2:
        return None
    y = drinks(raw.get("ALQ130"))
    if y is None:
        return None
    female = code(raw.get("RIAGENDR")) == 2
    race = code(raw.get("RIDRETH1"))
    educ = code(raw.get("DMDEDUC2"))
    return {
        "age": age,
        "female": int(female),
        "race": race if race in (1, 2, 3, 4, 5) else 5,
        "educ": educ if educ in (1, 2, 3, 4, 5) else 0,
        "y": y,
        "heavy": heavy(y, female),
        "spiro": int(rx["spiro"]),
        "spiro_days": rx["spiro_days"],
        "n_other": min(rx["n_other"], 4),
    }


def design(rows, cycles, adjusted=True):
    """Design matrix (list of lists) and column names; constant columns other
    than the intercept are dropped."""
    names = ["const", "spiro"]
    if adjusted:
        names += ["age", "age2", "female"] + ["race%d" % r for r in RACES] + \
                 ["educ%d" % e for e in EDUCATION] + ["cycle:" + c for c in cycles[1:]] + ["n_other"]
    X = []
    for r in rows:
        x = [1.0, float(r["spiro"])]
        if adjusted:
            x += [r["age"] / 10.0, (r["age"] / 10.0) ** 2, float(r["female"])]
            x += [1.0 if r["race"] == k else 0.0 for k in RACES]
            x += [1.0 if r["educ"] == k else 0.0 for k in EDUCATION]
            x += [1.0 if r["cycle"] == c else 0.0 for c in cycles[1:]]
            x += [float(r["n_other"])]
        X.append(x)
    keep = [0] + [j for j in range(1, len(names)) if len({x[j] for x in X}) > 1]
    return [[x[j] for j in keep] for x in X], [names[j] for j in keep]


def decide(lo, hi):
    if hi < 0:
        return "supported"
    if lo > 0:
        return "contradicted"
    return "inconclusive"


def fit(rows, outcome, cycles, weighted=True, adjusted=True):
    import numpy as np
    import statsmodels.api as sm
    X, names = design(rows, cycles, adjusted)
    if "spiro" not in names:
        return {"n": len(rows), "error": "no spironolactone contrast"}
    y = np.array([float(r[outcome]) for r in rows])
    groups = {}
    g = np.array([groups.setdefault(r["cluster"], len(groups)) for r in rows])
    X = np.array(X)
    if weighted:
        model = sm.WLS(y, X, weights=np.array([r["w"] for r in rows]))
    else:
        model = sm.OLS(y, X)
    res = model.fit(cov_type="cluster", cov_kwds={"groups": g})
    j = names.index("spiro")
    lo, hi = res.conf_int()[j]
    return {
        "n": len(rows), "n_spiro": sum(r["spiro"] for r in rows), "clusters": len(groups),
        "beta": float(res.params[j]), "se": float(res.bse[j]), "ci_low": float(lo),
        "ci_high": float(hi), "p": float(res.pvalues[j]), "decision": decide(lo, hi),
        "rules_out_half_drink_reduction": bool(lo > -0.5), "covariates": names,
    }


def fetch(urls, dest, log):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    last = None
    for url in urls:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; MV2 of Munim, Inc.)"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                if not data.startswith(b"HEADER RECORD"):
                    raise ValueError("not a SAS transport file (%d bytes, starts %r)" % (len(data), data[:40]))
                with open(dest + ".part", "wb") as f:
                    f.write(data)
                os.replace(dest + ".part", dest)
                log.append("downloaded %s (%d bytes)" % (url, len(data)))
                return dest
            except Exception as e:  # noqa: BLE001 - try the next attempt or URL
                last = "%s: %s" % (url, e)
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("could not download %s; last error %s" % (dest, last))


def read_records(path):
    import pandas as pd
    df = pd.read_sas(path, format="xport", encoding="latin-1")
    df.columns = [c.upper() for c in df.columns]
    return df.to_dict("records")


def build(data_dir, log):
    rows, counts = [], {}
    for label, year, legacy, pattern, wvar, years in CYCLES:
        recs = {}
        for base in FILES:
            name = pattern.format(base)
            urls = ["https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/%s/DataFiles/%s.xpt" % (year, name),
                    "https://wwwn.cdc.gov/Nchs/Nhanes/%s/%s.XPT" % (legacy, name)]
            recs[base] = read_records(fetch(urls, os.path.join(data_dir, name + ".xpt"), log))
        merged = {}
        for base in ["DEMO", "ALQ", "BPQ", "MCQ"]:
            for rec in recs[base]:
                s = code(rec.get("SEQN"))
                if s is not None and (base == "DEMO" or s in merged):
                    merged.setdefault(s, {}).update(rec)
        rx = summarize_rx((code(r.get("SEQN")), r.get("RXDDRUG"), r.get("RXDDAYS"))
                          for r in recs["RXQ_RX"] if code(r.get("RXDUSE")) == 1)
        c = {"participants": len(merged), "spiro_any_age": sum(1 for v in rx.values() if v["spiro"]),
             "eligible": 0, "eligible_spiro": 0, "no_weight": 0}
        for s, raw in merged.items():
            row = analysis_row(raw, rx.get(s))
            if row is None:
                continue
            w = raw.get(wvar)
            if code(w) is None or float(w) <= 0:
                c["no_weight"] += 1
                continue
            row.update({"seqn": s, "cycle": label, "w": float(w) * years / TOTAL_YEARS,
                        "cluster": "%s|%s|%s" % (label, code(raw.get("SDMVSTRA")), code(raw.get("SDMVPSU")))})
            rows.append(row)
            c["eligible"] += 1
            c["eligible_spiro"] += row["spiro"]
        counts[label] = c
        log.append("%s: %s" % (label, json.dumps(c)))
    return rows, counts


def describe(rows):
    out = {}
    for grp, sel in (("spironolactone", 1), ("comparator", 0)):
        rs = [r for r in rows if r["spiro"] == sel]
        sw = sum(r["w"] for r in rs)
        out[grp] = {
            "n": len(rs),
            "mean_drinks_unweighted": round(sum(r["y"] for r in rs) / len(rs), 3) if rs else None,
            "mean_drinks_weighted": round(sum(r["w"] * r["y"] for r in rs) / sw, 3) if sw else None,
            "heavy_share_weighted": round(sum(r["w"] * r["heavy"] for r in rs) / sw, 4) if sw else None,
            "female_share": round(sum(r["female"] for r in rs) / len(rs), 3) if rs else None,
            "mean_age": round(sum(r["age"] for r in rs) / len(rs), 1) if rs else None,
            "mean_n_other": round(sum(r["n_other"] for r in rs) / len(rs), 2) if rs else None,
        }
    return out


def fmt(r):
    if "error" in r:
        return "n %d: %s" % (r["n"], r["error"])
    return "n %d (%d spironolactone, %d clusters): beta %+.3f, 95%% CI %+.3f to %+.3f, p %.3f -> %s" % (
        r["n"], r["n_spiro"], r["clusters"], r["beta"], r["ci_low"], r["ci_high"], r["p"], r["decision"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)
    log = []
    rows, counts = build(a.data_dir, log)
    cycles = [c[0] for c in CYCLES]
    long_rows = [r for r in rows if r["spiro"] == 0 or (r["spiro_days"] or 0) >= 90]
    res = {
        "counts_by_cycle": counts,
        "describe": describe(rows),
        "primary_H1": fit(rows, "y", cycles),
        "S1_heavy_day": fit(rows, "heavy", cycles),
        "S2_spiro_90_days": fit(long_rows, "y", cycles),
        "S3_unweighted": fit(rows, "y", cycles, weighted=False),
        "S4_unadjusted": fit(rows, "y", cycles, adjusted=False),
    }
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    lines = ["# NHANES spironolactone check: results", "",
             "Pre-registration: findings/spironolactone-nhanes-prereg-2026-10-15.md", "",
             "## Counts by cycle", ""]
    lines += ["- %s: %s" % (k, json.dumps(v)) for k, v in counts.items()]
    lines += ["", "## Groups", ""] + ["- %s: %s" % (k, json.dumps(v)) for k, v in res["describe"].items()]
    lines += ["", "## Models (beta = spironolactone minus comparator)", ""]
    for k in ("primary_H1", "S1_heavy_day", "S2_spiro_90_days", "S3_unweighted", "S4_unadjusted"):
        lines.append("- %s: %s" % (k, fmt(res[k])))
    p = res["primary_H1"]
    if "error" not in p:
        lines += ["", "H1 decision: **%s**; CI rules out a reduction of 0.5 drinks per drinking day: %s"
                  % (p["decision"], p["rules_out_half_drink_reduction"])]
    lines += ["", "## Log", ""] + ["- " + s for s in log]
    with open(os.path.join(a.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
