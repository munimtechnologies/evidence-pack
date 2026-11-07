# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M7: a printed Total that lies outside the range of its own subgroup values (MEPS Statistical Briefs).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m7-totals-prereg-v1-2026-11-07.md (evidence-pack). Input: census M3's published
dataset of the accessible data tables of every brief (findings/meps-brief-tables-v1/tables.csv and cells/*.csv).

A percentage, mean or median for all persons is a mixture of the same statistic over any partition of those persons
(age groups, sexes, insurance groups), so it cannot lie below the smallest or above the largest subgroup value
(beyond rounding). For every column of every table, each row labelled as a total ("Total", "All persons", ...) is
paired with the subgroup rows of its own section, or, when its own section has fewer than two other rows, with every
other section of two or more rows. Each pair gets one verdict:
  excluded_label     a label or the title names a quantity the bound does not hold for (standard errors, changes,
                     differences, ratios, counts in numbers/millions/thousands)
  excluded_negative  the total or a subgroup value is negative
  below              total < smallest subgroup value - rounding tolerance          (flag)
  ok                 total within [smallest, largest] +/- rounding tolerance
  sum_like           total > largest and total >= 98% of the subgroups' sum - tolerance (a sum or a share table)
  above              largest < total < 98% of the subgroups' sum                     (flag)
Flags are only candidates: a subgroup list may not be a true partition (selected conditions, "any of" totals), and
each flagged figure is checked by hand against the brief's page. Research information about published statistics,
not medical advice.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re

VERSION = "0.1.0"
SUM_SHARE = 0.98
SAMPLE = 40
EPS = 1e-9
TOTAL_RE = re.compile(
    r"^\s*(?:total|overall)\b"
    r"|^\s*all\s+(?:persons|people|adults|children|ages|individuals|families|races|women|men|workers|employees"
    r"|groups|u\.?s\.?)\b"
    r"|^\s*(?:all|united\s+states|u\.?s\.?|us)\s*\W*$", re.I)
SKIP_RE = re.compile(r"standard\s+error|\bs\.\s?e\.|\bse\b|\bchanges?\b|difference|\bratios?\b|\bnumber\s+of\b"
                     r"|\bmillions?\b|\bthousands?\b|\bcount\b", re.I)
PAIR_FIELDS = ["number", "year", "table", "label", "col", "col_label", "total_label", "total_row", "total", "section",
               "n_parts", "lo", "lo_label", "hi", "hi_label", "sum", "verdict"]


def is_total(label):
    return bool(TOTAL_RE.search(label or ""))


def tol(d1, d2):
    """Largest gap two printed numbers with d1 and d2 decimals can show by rounding alone."""
    return 0.5 * 10 ** -d1 + 0.5 * 10 ** -d2


def verdict(total, dt, parts, texts):
    """Verdict for one (total, subgroup list) pair. parts: [(value, decimals)]; texts: labels and title to screen."""
    if any(SKIP_RE.search(t or "") for t in texts):
        return "excluded_label"
    if total < 0 or any(v < 0 for v, _ in parts):
        return "excluded_negative"
    lo_v, lo_d = min(parts, key=lambda p: p[0])
    hi_v, hi_d = max(parts, key=lambda p: p[0])
    if total < lo_v - tol(dt, lo_d) - EPS:
        return "below"
    if total <= hi_v + tol(dt, hi_d) + EPS:
        return "ok"
    s = sum(v for v, _ in parts)
    tol_s = 0.5 * 10 ** -dt + sum(0.5 * 10 ** -d for _, d in parts)
    if total >= SUM_SHARE * s - tol_s - EPS:
        return "sum_like"
    return "above"


def read_tables(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_cells(paths):
    out = {}
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.setdefault((r["number"], r["table"]), []).append(r)
    return out


def check_key(number, label):
    return hashlib.sha256(("m7|%s|%s" % (number, label)).encode("utf-8")).hexdigest()


def _fmt(v):
    return ("%.6f" % v).rstrip("0").rstrip(".")


def table_pairs(t, cells):
    """All (total, subgroup list) pairs of one table, one dict per pair (PAIR_FIELDS)."""
    label = t["label"] or ("#" + t["index"])
    by_col = {}
    for c in cells:
        by_col.setdefault(int(c["col"]), []).append(c)
    out = []
    for col in sorted(by_col):
        entries = sorted(by_col[col], key=lambda c: int(c["row"]))
        totals = [e for e in entries if is_total(e["row_label"])]
        groups, order = {}, []
        for e in entries:
            if is_total(e["row_label"]):
                continue
            if e["section"] not in groups:
                groups[e["section"]] = []
                order.append(e["section"])
            groups[e["section"]].append(e)
        for tot in totals:
            own = groups.get(tot["section"], [])
            if len(own) >= 2:
                pick = [tot["section"]]
            else:
                pick = [s for s in order if s != tot["section"] and len(groups[s]) >= 2]
            tv, td = float(tot["value"]), int(tot["decimals"] or 0)
            for s in pick:
                ps = groups[s]
                parts = [(float(p["value"]), int(p["decimals"] or 0)) for p in ps]
                v = verdict(tv, td, parts, [t["title"], tot["col_label"], tot["row_label"], s])
                lo = min(range(len(ps)), key=lambda i: parts[i][0])
                hi = max(range(len(ps)), key=lambda i: parts[i][0])
                out.append({"number": t["number"], "year": t["year"], "table": t["index"], "label": label,
                            "col": col, "col_label": tot["col_label"][:150], "total_label": tot["row_label"],
                            "total_row": int(tot["row"]), "total": _fmt(tv), "section": s, "n_parts": len(ps),
                            "lo": _fmt(parts[lo][0]), "lo_label": ps[lo]["row_label"],
                            "hi": _fmt(parts[hi][0]), "hi_label": ps[hi]["row_label"],
                            "sum": _fmt(sum(p[0] for p in parts)), "verdict": v})
    return out


def census(tables, cells):
    pairs = []
    for t in sorted(tables, key=lambda t: (int(t["number"]), int(t["index"]))):
        pairs.extend(table_pairs(t, cells.get((t["number"], t["index"]), [])))
    by_verdict = {}
    for p in pairs:
        by_verdict[p["verdict"]] = by_verdict.get(p["verdict"], 0) + 1
    flags = [dict(p) for p in pairs if p["verdict"] in ("below", "above")]
    figs = sorted({(f["number"], f["label"]) for f in flags}, key=lambda k: check_key(*k))
    rank = {k: i + 1 for i, k in enumerate(figs)}
    for f in flags:
        f["check_rank"] = rank[(f["number"], f["label"])]
        f["in_sample"] = f["check_rank"] <= SAMPLE
    flags.sort(key=lambda f: (f["check_rank"], int(f["table"]), f["col"], f["total_row"], f["section"]))
    c558 = [p for p in pairs if p["number"] == "558" and p["label"] == "Figure 1" and p["total_label"] == "Total"]
    control = {"pairs": [(p["section"], p["verdict"]) for p in c558],
               "all_ok": bool(c558) and all(p["verdict"] == "ok" for p in c558)}
    summary = {"version": VERSION, "tables": len(tables),
               "tables_with_total_pairs": len({(p["number"], p["table"]) for p in pairs}),
               "pairs": len(pairs), "by_verdict": by_verdict,
               "pairs_bound_applied": sum(by_verdict.get(k, 0) for k in ("ok", "below", "above")),
               "flags": len(flags), "figures_flagged": len(figs),
               "figures_flagged_by_kind": {k: len({(f["number"], f["label"]) for f in flags if f["verdict"] == k})
                                           for k in ("below", "above")},
               "sample_size": min(SAMPLE, len(figs)), "control_558_f1": control}
    return summary, pairs, flags


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    tables = read_tables(a.tables)
    cells = read_cells(sorted(glob.glob(os.path.join(a.cells_dir, "*.csv"))))
    summary, pairs, flags = census(tables, cells)
    with open(os.path.join(a.out_dir, "m7-pairs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PAIR_FIELDS)
        w.writeheader()
        w.writerows(pairs)
    with open(os.path.join(a.out_dir, "m7-flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["check_rank", "in_sample"] + PAIR_FIELDS)
        w.writeheader()
        w.writerows(flags)
    with open(os.path.join(a.out_dir, "m7-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
