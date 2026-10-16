# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Oral, placebo-controlled RCTs of metformin for knee OA: a pain-SMD pool.

Standard library only. Effects are signed so that positive = less pain on
metformin. Inputs are transcribed from the published papers (see TRIALS).
Run: python meta_oral.py [--out pool.json]
"""
import argparse
import json
import math

Z975 = 1.959964
T975 = {1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764}

# Pan 2025 reports the SMD itself (VAS pain, 0.43, 95% CI 0.02-0.83).
# The other two report end-of-treatment mean +/- SD per arm only.
TRIALS = [
    {"id": "pan2025", "pmid": "40274279", "smd": 0.43, "lo": 0.02, "hi": 0.83,
     "note": "VAS pain SMD as published; ITT n 54/53"},
    {"id": "alimoradi2023", "pmid": "36879307", "scale": "KOOS pain 0-100, higher better",
     "met": (70.8, 19.1, 44), "pla": (50.5, 19.0, 44), "higher_better": True,
     "note": "post-treatment; header n 44/44 but 27/44 completed; imputation not described"},
    {"id": "aiad2024", "pmid": "38869746", "scale": "WOMAC pain 0-20, lower better",
     "met": (7.68, 1.406, 25), "pla": (10.24, 1.877, 25), "higher_better": False,
     "note": "week 12; completers 25/25 of 60 randomized (Results) or 50 (Methods)"},
]


def hedges_g(met, pla, higher_better):
    m1, s1, n1 = met
    m2, s2, n2 = pla
    sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    d = (m1 - m2) / sp if higher_better else (m2 - m1) / sp
    g = d * (1 - 3 / (4 * (n1 + n2 - 2) - 1))
    se = math.sqrt((n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2)))
    return g, se


def effect(trial):
    if "smd" in trial:
        return trial["smd"], (trial["hi"] - trial["lo"]) / (2 * Z975)
    return hedges_g(trial["met"], trial["pla"], trial["higher_better"])


def dl_pool(ys, ses):
    """DerSimonian-Laird random effects, with a Hartung-Knapp-Sidik-Jonkman CI."""
    k = len(ys)
    w = [1 / s ** 2 for s in ses]
    fe = sum(wi * y for wi, y in zip(w, ys)) / sum(w)
    q = sum(wi * (y - fe) ** 2 for wi, y in zip(w, ys))
    c = sum(w) - sum(wi ** 2 for wi in w) / sum(w)
    tau2 = max(0.0, (q - (k - 1)) / c)
    i2 = max(0.0, (q - (k - 1)) / q) * 100 if q > 0 else 0.0
    ws = [1 / (s ** 2 + tau2) for s in ses]
    mu = sum(wi * y for wi, y in zip(ws, ys)) / sum(ws)
    se = 1 / math.sqrt(sum(ws))
    qstar = sum(wi * (y - mu) ** 2 for wi, y in zip(ws, ys)) / (k - 1)
    se_hk = math.sqrt(qstar / sum(ws))
    t = T975[k - 1]
    return {"k": k, "mu": mu, "se": se, "lo": mu - Z975 * se, "hi": mu + Z975 * se,
            "hksj_lo": mu - t * se_hk, "hksj_hi": mu + t * se_hk,
            "tau2": tau2, "i2": i2, "q": q}


def run():
    rows = []
    for t in TRIALS:
        g, se = effect(t)
        rows.append({"id": t["id"], "pmid": t["pmid"], "g": round(g, 4), "se": round(se, 4),
                     "note": t["note"]})
    by = {r["id"]: r for r in rows}
    out = {"trials": rows, "pools": {}}
    for name, ids in [("all_three", ["pan2025", "alimoradi2023", "aiad2024"]),
                      ("without_aiad", ["pan2025", "alimoradi2023"]),
                      ("without_alimoradi", ["pan2025", "aiad2024"])]:
        p = dl_pool([by[i]["g"] for i in ids], [by[i]["se"] for i in ids])
        out["pools"][name] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    res = run()
    text = json.dumps(res, indent=1)
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
