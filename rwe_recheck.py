# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""rwe_recheck: internal-consistency checks for published estimates.

Each row is one printed estimate with its 95% CI, plus whatever else the paper
prints (event counts, denominators, a 2x2 table, a t or z statistic). Numbers
are given as strings exactly as printed, so the rounding of each one is known.
A check flags a row only if no unrounded values consistent with the printed
ones pass it.

Checks:
  centre  the estimate lies at the CI midpoint (log scale for ratios).
  width   the CI is not much narrower than the Poisson SE sqrt(1/a + 1/b)
          from the event counts allows (ratio scale only).
  stat    a printed t or z matches the SE implied by the CI.
  crude   an estimate printed as crude matches the ratio of the printed
          counts within 3 count SEs.
  table   an odds ratio printed as crude, with its CI, matches the 2x2 table
          it came from (Woolf logit interval).

The width and stat factors are heuristics, not tests: a flag says a number
needs a second look, not which number is wrong. Standard library only.

Usage: python rwe_recheck.py rows.json [--out result.json]
"""
import json
import math
import sys

Z = 1.959964
WIDTH_FACTOR = 0.67   # widest CI-implied SE below this share of the count SE is flagged
STAT_FACTOR = 1.25    # t-implied and CI-implied SEs further apart than this are flagged
CRUDE_SES = 3.0       # crude estimate further than this many count SEs from the counts
TABLE_SLACK = 0.05    # log-scale slack for continuity corrections and method choices
EPS = 1e-9


def half_unit(s):
    """Half a unit in the last printed decimal place of a number string."""
    s = str(s).strip()
    d = len(s.split(".")[1]) if "." in s else 0
    return 0.5 * 10 ** (-d)


def bounds(s):
    v, h = float(s), half_unit(s)
    return v - h, v + h


def _bounds(row, key):
    lo, hi = bounds(row[key])
    if row["scale"] == "ratio":
        return math.log(max(lo, 1e-12)), math.log(hi)
    return lo, hi


def _point(row, key):
    v = float(row[key])
    return math.log(v) if row["scale"] == "ratio" else v


def ci_se_range(row):
    """Smallest and largest SE the printed 95% CI allows, given its rounding."""
    l0, l1 = _bounds(row, "lo")
    h0, h1 = _bounds(row, "hi")
    return max(0.0, h0 - l1) / (2 * Z), (h1 - l0) / (2 * Z)


def check_centre(row):
    e0, e1 = _bounds(row, "est")
    l0, l1 = _bounds(row, "lo")
    h0, h1 = _bounds(row, "hi")
    m0, m1 = (l0 + h0) / 2, (l1 + h1) / 2
    mid = (_point(row, "lo") + _point(row, "hi")) / 2
    if row["scale"] == "ratio":
        mid = math.exp(mid)
    # EPS: rows whose rounding ranges just touch (Palzes 2021) must not flip on float error.
    return {"midpoint": mid, "ok": m0 <= e1 + EPS and e0 <= m1 + EPS}


def check_width(row):
    if row["scale"] != "ratio" or "a" not in row:
        return None
    count_se = math.sqrt(1.0 / row["a"] + 1.0 / row["b"])
    se_max = ci_se_range(row)[1]
    return {"count_se": count_se, "ci_se_max": se_max, "ratio": se_max / count_se,
            "ok": se_max >= WIDTH_FACTOR * count_se}


def check_stat(row):
    if "t" not in row:
        return None
    e0, e1 = _bounds(row, "est")
    est_min = 0.0 if e0 <= 0 <= e1 else min(abs(e0), abs(e1))
    est_max = max(abs(e0), abs(e1))
    t0, t1 = bounds(row["t"])
    t_min = 0.0 if t0 <= 0 <= t1 else min(abs(t0), abs(t1))
    t_max = max(abs(t0), abs(t1))
    se_t_min = est_min / t_max
    se_t_max = est_max / t_min if t_min > 0 else float("inf")
    c0, c1 = ci_se_range(row)
    ok = not (se_t_min > STAT_FACTOR * c1 or c0 > STAT_FACTOR * se_t_max)
    return {"se_from_t": abs(_point(row, "est") / float(row["t"])),
            "se_from_ci": (_point(row, "hi") - _point(row, "lo")) / (2 * Z), "ok": ok}


def check_crude(row):
    if row["scale"] != "ratio" or "na" not in row:
        return None
    rr = (row["a"] / row["na"]) / (row["b"] / row["nb"])
    x = math.log(rr)
    e0, e1 = _bounds(row, "est")
    gap = 0.0 if e0 <= x <= e1 else min(abs(x - e0), abs(x - e1))
    se = math.sqrt(1.0 / row["a"] + 1.0 / row["b"])
    # Adjusted estimates may move away from the crude ratio; only report them.
    ok = gap <= CRUDE_SES * se if row.get("crude") else True
    return {"crude_ratio": rr, "gap_in_se": gap / se, "ok": ok}


def check_table(row):
    if "cells" not in row:
        return None
    a, b, c, d = row["cells"]
    x = math.log(a * d / (b * c))
    se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    woolf = {"est": math.exp(x), "lo": math.exp(x - Z * se), "hi": math.exp(x + Z * se)}
    off = []
    for k in ("est", "lo", "hi"):
        p = float(row[k])
        if abs(math.log(woolf[k]) - math.log(p)) > half_unit(row[k]) / p + TABLE_SLACK:
            off.append(k)
    return {"woolf": woolf, "off": off, "ok": not off}


CHECKS = (("centre", check_centre), ("width", check_width), ("stat", check_stat),
          ("crude", check_crude), ("table", check_table))


def recheck(row):
    out = {"label": row["label"], "source": row.get("source", ""), "checks": {}, "flags": []}
    for name, fn in CHECKS:
        res = fn(row)
        if res is None:
            continue
        out["checks"][name] = res
        if not res["ok"]:
            out["flags"].append(name)
    return out


def run(rows):
    results = [recheck(r) for r in rows]
    return {"n_rows": len(results),
            "n_flagged": sum(1 for r in results if r["flags"]),
            "flagged": [r["label"] for r in results if r["flags"]],
            "rows": results}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        res = run(json.load(f)["rows"])
    text = json.dumps(res, indent=1)
    print(text)
    if len(sys.argv) > 3 and sys.argv[2] == "--out":
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write(text)
