# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Pre-registration 6: consistency of ratio estimates in a sample of TriNetX abstracts.

Runs rwe_recheck's pre-registered checks (centre, width, crude/table) over the
sampled rows, then the outcomes the pre-registration names: the share of
estimates with a centre flag (Wilson 95% CI) against Georgescu & Wren's
5.6-7.5% for MEDLINE, the share of papers with any flag, and the share of
count-bearing rows flagged.

Also runs one exploratory check that was NOT pre-registered: a printed P value
against the P implied by the CI (normal approximation on the log scale),
flagged only when the two z values differ by more than rwe_recheck's
STAT_FACTOR after allowing for rounding.

Usage: python trinetx_audit.py trinetx_rows.json [--out result.json]
"""
import json
import math
import sys
from statistics import NormalDist

import rwe_recheck as rr

BENCH_LO, BENCH_HI = 0.056, 0.075   # Georgescu & Wren 2018, MEDLINE
Z95 = 1.959964
COUNT_CHECKS = ("width", "crude", "table")


def wilson(k, n, z=Z95):
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def z_of_p(p):
    """Two-sided z for a P value; P at or below zero gives infinity."""
    if p <= 0:
        return float("inf")
    return NormalDist().inv_cdf(1 - min(p, 1.0) / 2)


def printed_z_range(s):
    s = str(s).replace(" ", "")
    if s.startswith("<"):
        return z_of_p(float(s[1:])), float("inf")
    p0, p1 = rr.bounds(s)
    return z_of_p(p1), z_of_p(p0)


def check_p(row):
    if "p" not in row:
        return None
    e0, e1 = rr._bounds(row, "est")
    est_min = 0.0 if e0 <= 0 <= e1 else min(abs(e0), abs(e1))
    est_max = max(abs(e0), abs(e1))
    c0, c1 = rr.ci_se_range(row)
    z_lo = est_min / c1
    z_hi = est_max / c0 if c0 > 0 else float("inf")
    pz_lo, pz_hi = printed_z_range(row["p"])
    ok = not (pz_lo > rr.STAT_FACTOR * z_hi or z_lo > rr.STAT_FACTOR * pz_hi)
    z_mid = abs(rr._point(row, "est")) / ((rr._point(row, "hi") - rr._point(row, "lo")) / (2 * rr.Z))
    return {"z_from_ci": z_mid, "p_from_ci": 2 * (1 - NormalDist().cdf(z_mid)),
            "z_printed": [pz_lo, pz_hi], "ok": ok}


def verdict(lo, hi):
    if lo > BENCH_HI:
        return "higher than MEDLINE"
    if hi < BENCH_LO:
        return "lower than MEDLINE"
    return "consistent with the benchmark"


def audit(rows):
    res = rr.run(rows)
    for row, out in zip(rows, res["rows"]):
        out["paper"] = row["paper"]
        out["k"] = row["k"]
        out["has_counts"] = "a" in row
        pc = check_p(row)
        if pc is not None:
            out["p_check"] = pc
    n = len(rows)
    centre = [o["label"] for o in res["rows"] if "centre" in o["flags"]]
    papers = sorted({o["paper"] for o in res["rows"]})
    flagged_papers = sorted({o["paper"] for o in res["rows"] if o["flags"]})
    count_rows = [o for o in res["rows"] if o["has_counts"]]
    count_flagged = [o["label"] for o in count_rows
                     if any(f in COUNT_CHECKS for f in o["flags"])]
    p_rows = [o for o in res["rows"] if "p_check" in o]
    p_flagged = [o["label"] for o in p_rows if not o["p_check"]["ok"]]
    lo, hi = wilson(len(centre), n)
    plo, phi = wilson(len(flagged_papers), len(papers))
    return {
        "n_rows": n,
        "n_papers": len(papers),
        "primary": {"centre_flagged": centre, "rate": len(centre) / n,
                    "wilson95": [lo, hi], "benchmark": [BENCH_LO, BENCH_HI],
                    "verdict": verdict(lo, hi)},
        "secondary": {"papers_flagged": flagged_papers,
                      "paper_rate": len(flagged_papers) / len(papers),
                      "paper_wilson95": [plo, phi],
                      "count_rows": len(count_rows), "count_rows_flagged": count_flagged},
        "exploratory_p": {"rows_with_p": len(p_rows), "flagged": p_flagged},
        "rows": res["rows"],
    }


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        out = audit(json.load(f)["rows"])
    text = json.dumps(out, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    if len(sys.argv) > 3 and sys.argv[2] == "--out":
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write(text)
