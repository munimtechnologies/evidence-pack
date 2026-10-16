# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Indirect alpha-1 blocker vs finasteride HRs from Fung et al., PLoS One 2024 (Table 2).

Every published HR uses tamsulosin as the reference, so HR(A vs finasteride) =
HR(A vs tam) / HR(fin vs tam). The two log-HRs are treated as independent. They
share the tamsulosin group, so the true covariance is positive and these CIs are
slightly wide (conservative). Standard library only.
"""
import json
import math

Z = 1.959964

# (HR, lo, hi) vs tamsulosin, copied from Fung 2024 Table 2 (PMC11340942).
FUNG = {
    ("terazosin", "AD", "overall"): (0.73, 0.65, 0.82),
    ("terazosin", "PD", "overall"): (0.74, 0.66, 0.83),
    ("terazosin", "AD", ">1yr"): (0.69, 0.60, 0.80),
    ("terazosin", "PD", ">1yr"): (0.68, 0.59, 0.78),
    ("terazosin", "death", "overall"): (0.97, 0.94, 1.01),
    ("doxazosin", "AD", "overall"): (0.84, 0.76, 0.92),
    ("doxazosin", "PD", "overall"): (0.79, 0.72, 0.88),
    ("finasteride", "AD", "overall"): (0.98, 0.90, 1.06),
    ("finasteride", "PD", "overall"): (0.90, 0.83, 0.98),
    ("finasteride", "AD", ">1yr"): (0.90, 0.81, 0.99),
    ("finasteride", "PD", ">1yr"): (0.91, 0.82, 1.00),
    ("finasteride", "death", "overall"): (0.93, 0.90, 0.96),
}


def log_se(hr, lo, hi):
    return math.log(hr), (math.log(hi) - math.log(lo)) / (2 * Z)


def vs_finasteride(drug, outcome, window):
    a, sa = log_se(*FUNG[(drug, outcome, window)])
    b, sb = log_se(*FUNG[("finasteride", outcome, window)])
    d, s = a - b, math.sqrt(sa ** 2 + sb ** 2)
    return {"drug": drug, "outcome": outcome, "window": window,
            "hr": round(math.exp(d), 3), "lo": round(math.exp(d - Z * s), 3),
            "hi": round(math.exp(d + Z * s), 3)}


def run():
    keys = [("terazosin", "AD", "overall"), ("terazosin", "PD", "overall"),
            ("terazosin", "AD", ">1yr"), ("terazosin", "PD", ">1yr"),
            ("terazosin", "death", "overall"),
            ("doxazosin", "AD", "overall"), ("doxazosin", "PD", "overall")]
    return [vs_finasteride(*k) for k in keys]


if __name__ == "__main__":
    import sys
    res = run()
    text = json.dumps(res, indent=1)
    print(text)
    if len(sys.argv) > 2 and sys.argv[1] == "--out":
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
