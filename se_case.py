# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# MV2 of Munim, Inc.; AI agents (Claude) drafted this code in his name.
"""Check whether ClinicalTrials.gov 'Standard Error' cells on a 0-100 percentage scale
are possible as SEs, and whether they are possible as SDs (Bhatia-Davis bound).

Also shows what a meta-analyst would get from one cell pair under each reading.
Standard library only. Research information, not medical advice.
"""
import argparse
import json
import math
import urllib.request

NCT = "NCT02037126"
LO, HI = 0.0, 100.0

# Transcribed by hand from the live API record on 2026-10-16 (outcomes 14-17; n = 20 per arm).
# (measure, period, arm, mean, posted_se, n)
ROWS = [
    ("alcohol_abstinent_days", 1, "psilocybin", 5.7, 11.34, 20),
    ("alcohol_abstinent_days", 1, "placebo", 27.68, 32.10, 20),
    ("alcohol_abstinent_days", 2, "psilocybin", 5.85, 7.86, 20),
    ("alcohol_abstinent_days", 2, "placebo", 34.32, 37.3, 20),
    ("alcohol_abstinent_days", 3, "psilocybin", 7.19, 14.06, 20),
    ("alcohol_abstinent_days", 3, "placebo", 27.39, 34.32, 20),
    ("heavy_alcohol_abstinent_days", 1, "psilocybin", 1.8, 4.88, 20),
    ("heavy_alcohol_abstinent_days", 1, "placebo", 13.29, 24.53, 20),
    ("heavy_alcohol_abstinent_days", 2, "psilocybin", 2.40, 6.67, 20),
    ("heavy_alcohol_abstinent_days", 2, "placebo", 19.44, 31.11, 20),
    ("heavy_alcohol_abstinent_days", 3, "psilocybin", 4.09, 13.55, 20),
    ("heavy_alcohol_abstinent_days", 3, "placebo", 16.01, 28.21, 20),
    ("tobacco_abstinent_days", 1, "psilocybin", 55.07, 46.01, 20),
    ("tobacco_abstinent_days", 1, "placebo", 63.52, 40.91, 20),
    ("tobacco_abstinent_days", 2, "psilocybin", 53.80, 48.90, 20),
    ("tobacco_abstinent_days", 2, "placebo", 75.25, 38.96, 20),
    ("tobacco_abstinent_days", 3, "psilocybin", 49.36, 48.50, 20),
    ("tobacco_abstinent_days", 3, "placebo", 74.05, 38.46, 20),
    ("cannabis_abstinent_days", 1, "psilocybin", 14.31, 26.76, 20),
    ("cannabis_abstinent_days", 1, "placebo", 28.57, 39.09, 20),
    ("cannabis_abstinent_days", 2, "psilocybin", 21.99, 34.28, 20),
    ("cannabis_abstinent_days", 2, "placebo", 36.85, 43.99, 20),
    ("cannabis_abstinent_days", 3, "psilocybin", 18.19, 33.49, 20),
    ("cannabis_abstinent_days", 3, "placebo", 31.24, 43.57, 20),
]

# Primary outcome 1 (cocaine-abstinent days), period 1, for contrast: labelled SE and plausible as SE.
PRIMARY = [
    ("cocaine_abstinent_days", 1, "psilocybin", 97.43, 1.01, 20),
    ("cocaine_abstinent_days", 1, "placebo", 71.63, 5.25, 20),
]


def max_sd(mean, n, lo=LO, hi=HI):
    """Largest possible sample SD (n-1 denominator) for n values in [lo, hi] with this mean."""
    if not lo <= mean <= hi or n < 2:
        return float("nan")
    return math.sqrt((mean - lo) * (hi - mean) * n / (n - 1))


def classify(mean, spread, n):
    cap = max_sd(mean, n)
    implied = spread * math.sqrt(n)
    return {
        "max_sd": round(cap, 2),
        "sd_if_se": round(implied, 2),
        "possible_as_se": implied <= cap,
        "possible_as_sd": spread <= cap,
    }


def hedges_g(m1, sd1, n1, m2, sd2, n2):
    sp = math.sqrt(((n1 - 1) * sd1 ** 2 + (n2 - 1) * sd2 ** 2) / (n1 + n2 - 2))
    j = 1 - 3 / (4 * (n1 + n2) - 9)
    return j * (m1 - m2) / sp


def two_readings(rows):
    """g (placebo minus psilocybin, so positive favours psilocybin if the values are use days)
    with the spread read as an SD, and read literally as an SE converted by sqrt(n)."""
    (_, _, _, m1, s1, n1), (_, _, _, m2, s2, n2) = rows
    as_sd = hedges_g(m2, s2, n2, m1, s1, n1)
    as_se = hedges_g(m2, s2 * math.sqrt(n2), n2, m1, s1 * math.sqrt(n1), n1)
    return round(as_sd, 3), round(as_se, 3)


def fetch_live():
    url = ("https://clinicaltrials.gov/api/v2/studies/%s"
           "?fields=resultsSection.outcomeMeasuresModule.outcomeMeasures" % NCT)
    with urllib.request.urlopen(url, timeout=60) as r:
        doc = json.load(r)
    oms = doc["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    cells = []
    for om in oms:
        if om.get("dispersionType") != "STANDARD_ERROR" and "Error" not in str(om.get("dispersionType")):
            continue
        denoms = {c["groupId"]: int(c["value"]) for d in om.get("denoms", []) for c in d.get("counts", [])}
        for k, cl in enumerate(om.get("classes", []), 1):
            for cat in cl.get("categories", []):
                for m in cat.get("measurements", []):
                    try:
                        cells.append((om["title"], k, m["groupId"], float(m["value"]),
                                      float(m["spread"]), denoms[m["groupId"]]))
                    except (KeyError, ValueError):
                        pass
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="se_case.json")
    ap.add_argument("--live", action="store_true", help="also re-read the live record and compare")
    a = ap.parse_args()
    res = {"nct": NCT, "cells": [], "primary": [], "g_alcohol_p1": {}, "live": None}
    for r in ROWS:
        res["cells"].append(dict(zip(("measure", "period", "arm", "mean", "spread", "n"), r), **classify(*r[3:])))
    for r in PRIMARY:
        res["primary"].append(dict(zip(("measure", "period", "arm", "mean", "spread", "n"), r), **classify(*r[3:])))
    g_sd, g_se = two_readings(ROWS[0:2])
    res["g_alcohol_p1"] = {"as_sd": g_sd, "as_se": g_se}
    res["counts"] = {
        "cells": len(ROWS),
        "impossible_as_se": sum(not c["possible_as_se"] for c in res["cells"]),
        "possible_as_sd": sum(c["possible_as_sd"] for c in res["cells"]),
    }
    if a.live:
        live = fetch_live()
        hand = {(round(m, 2), round(s, 2)) for (_, _, _, m, s, _) in ROWS + PRIMARY}
        got = {(round(m, 2), round(s, 2)) for (_, _, _, m, s, _) in live}
        res["live"] = {"se_cells_live": len(live), "hand_cells_missing_from_live": sorted(hand - got)}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("counts", "g_alcohol_p1", "live")}, indent=1))
    for c in res["cells"] + res["primary"]:
        print("%-30s p%d %-10s mean %6.2f spread %6.2f  sd_if_se %7.2f  max_sd %6.2f  as_se %-5s as_sd %s" % (
            c["measure"], c["period"], c["arm"], c["mean"], c["spread"], c["sd_if_se"], c["max_sd"],
            c["possible_as_se"], c["possible_as_sd"]))


if __name__ == "__main__":
    main()
