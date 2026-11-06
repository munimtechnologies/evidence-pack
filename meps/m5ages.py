# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M5: age bands that overlap or leave a one-year gap inside one MEPS Statistical Brief figure.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m5-agebands-prereg-v1-2026-11-06.md (evidence-pack). Input: census M3's published
dataset of the accessible data tables of every brief (findings/meps-brief-tables-v1/tables.csv and cells/*.csv).
All panels that share one label in one brief ("Figure 5" printed twice) form one figure. Every row or column label
part (col labels are split on " / ") that looks like an age band is parsed: "40-65", "18 to 44", "65+",
"65 and older", "under 18", "<65". Two bands of one figure are flagged when neither contains the other and they
share an age (overlap, e.g. 40-65 next to 65+), or when exactly one age between them is in no band of the figure
(gap1, e.g. 0-17 next to 19-64). Flags are only candidates: each is checked by hand against the brief's page.
Research information about published statistics, not medical advice.
"""
import argparse
import csv
import glob
import json
import os
import re

VERSION = "0.1.0"
TOP = 999  # open upper end of "65+" / "65 and older"
MAX_AGE = 110
DASHES = "-" + chr(0x2013) + chr(0x2014)
AGE_WORD = re.compile(r"\bage[sd]?\b", re.I)
EXCLUDE = re.compile(r"%|\$|percent|poverty|fpl|income|hour|visit|day|week|month|dollar|condition", re.I)
RANGE_RE = re.compile(r"(?<![\d.$])(\d{1,3})\s*(?:[" + DASHES + r"]|\bto\b|\bthrough\b)\s*(\d{1,3})(?![\d.%])",
                      re.I)
PLUS_RE = re.compile(r"(?<![\d.$])(\d{1,3})\s*(?:\+|(?:years?\s+)?(?:and|or)\s+(?:over|older|above|up))", re.I)
UNDER_RE = re.compile(r"(?:\bunder|\bless\s+than|\byounger\s+than|\bbelow|<)\s*(?:age\s*)?(\d{1,3})(?![\d.%])", re.I)


def bands(part):
    """Age bands (lo, hi) written in one label part; hi = TOP for an open upper end."""
    out = []
    for m in RANGE_RE.finditer(part):
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= lo < hi <= MAX_AGE:
            out.append((lo, hi))
    for m in PLUS_RE.finditer(part):
        lo = int(m.group(1))
        if lo <= MAX_AGE:
            out.append((lo, TOP))
    for m in UNDER_RE.finditer(part):
        a = int(m.group(1))
        if 1 <= a <= MAX_AGE:
            out.append((0, a - 1))
    return out


def is_age_part(part, title):
    """A label part is read for age bands unless it names another unit; it, or the figure title, must say age."""
    if EXCLUDE.search(part):
        return False
    return bool(AGE_WORD.search(part) or AGE_WORD.search(title))


def check(band_set):
    """Flags for one figure: ("overlap" | "gap1", band_a, band_b), band_a sorted before band_b."""
    bs = sorted(band_set)
    flags = []
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            if (a[0] <= b[0] and b[1] <= a[1]) or (b[0] <= a[0] and a[1] <= b[1]):
                continue  # nested: a total band and its parts
            if max(a[0], b[0]) <= min(a[1], b[1]):
                flags.append(("overlap", a, b))
            elif a[1] != TOP and a[1] + 2 == b[0]:
                gap = a[1] + 1
                if not any(c[0] <= gap <= c[1] for c in bs):
                    flags.append(("gap1", a, b))
    return flags


def fmt(b):
    return "%d+" % b[0] if b[1] == TOP else "%d-%d" % b


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


def figures(tables, cells):
    """{(number, label): {...,"bands": {band: first label part}}}; all panels with one label form one figure."""
    groups = {}
    for t in tables:
        label = t["label"] or ("#" + t["index"])
        g = groups.setdefault((t["number"], label), {"number": t["number"], "year": t["year"], "label": label,
                                                     "title": t["title"], "bands": {}})
        for c in cells.get((t["number"], t["index"]), []):
            for lab in (c["row_label"], c["col_label"]):
                for part in lab.split(" / "):
                    part = part.strip()
                    if part and is_age_part(part, g["title"]):
                        for b in bands(part):
                            g["bands"].setdefault(b, part)
    return groups


def census(tables, cells):
    groups = figures(tables, cells)
    flags = []
    for key in sorted(groups, key=lambda k: (int(k[0]), k[1])):
        g = groups[key]
        for kind, a, b in check(g["bands"]):
            flags.append({"number": g["number"], "year": g["year"], "label": g["label"], "kind": kind,
                          "band_a": fmt(a), "band_b": fmt(b), "label_a": g["bands"][a], "label_b": g["bands"][b],
                          "title": g["title"][:200]})
    kinds = {}
    for f in flags:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    ctrl = any(f["number"] == "170" and f["label"] == "Figure 5" and f["kind"] == "overlap"
               and (f["band_a"], f["band_b"]) == ("40-65", "65+") for f in flags)
    summary = {"version": VERSION, "tables": len(tables), "figures": len(groups),
               "figures_with_age_bands": sum(1 for g in groups.values() if g["bands"]),
               "flags": len(flags), "figures_flagged": len({(f["number"], f["label"]) for f in flags}),
               "by_kind": kinds, "positive_control_170_f5": ctrl}
    band_rows = [[g["number"], g["year"], g["label"], ";".join(fmt(b) for b in sorted(g["bands"]))]
                 for k, g in sorted(groups.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])) if g["bands"]]
    return summary, flags, band_rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    tables = read_tables(a.tables)
    cells = read_cells(sorted(glob.glob(os.path.join(a.cells_dir, "*.csv"))))
    summary, flags, band_rows = census(tables, cells)
    fields = ["number", "year", "label", "kind", "band_a", "band_b", "label_a", "label_b", "title"]
    with open(os.path.join(a.out_dir, "m5-flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(flags)
    with open(os.path.join(a.out_dir, "m5-bands.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "year", "label", "bands"])
        w.writerows(band_rows)
    with open(os.path.join(a.out_dir, "m5-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
