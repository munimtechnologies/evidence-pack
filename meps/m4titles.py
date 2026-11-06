# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M4: repeated figure and table titles inside one MEPS Statistical Brief.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m4-titles-prereg-v1-2026-11-06.md (evidence-pack). Input: census M3's published
dataset of the accessible data tables of every brief (findings/meps-brief-tables-v1/tables.csv and cells/*.csv).
A candidate is a pair of tables in one brief whose title keys are equal. The key is the title without its
"Figure N." label, lower-cased, cut where the table's own column headers start (older pages append them to the
caption), with spaces collapsed and end punctuation removed. Each candidate pair is then classed by its data.
Candidates are only candidates: each is checked by hand against the brief's page before anything is counted as
a title error. Research information about published statistics, not medical advice.
"""
import argparse
import csv
import glob
import json
import os
import re

VERSION = "0.1.0"
LABEL_RE = re.compile(r"^\s*(figure|table|exhibit)\s*[0-9]+[a-z]?\s*[.:\-]?\s*", re.I)
MIN_CUT = 15
MIN_KEY = 10


def _norm(text):
    return " ".join(text.lower().split())


def title_key(title, col_labels=()):
    """Key of one table's title. col_labels: the table's column headers in column order."""
    t = _norm(LABEL_RE.sub("", title, count=1))
    cut = len(t)
    for lab in col_labels[:1]:
        lab = _norm(lab)
        for probe in (lab, lab.split(": ")[-1], lab.split(": ")[0]):
            if len(probe) < 4:
                continue
            i = t.find(probe, MIN_CUT)
            if i != -1 and i < cut:
                cut = i
    return t[:cut].strip(" .:;,-")


def read_tables(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_cells(paths):
    """{(number, table index): [cell dicts]} from the M3 cells files."""
    out = {}
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.setdefault((r["number"], r["table"]), []).append(r)
    return out


def col_labels(cells):
    by_col = {}
    for c in cells:
        if c["col_label"].strip() and c["col"].strip().isdigit():
            by_col.setdefault(int(c["col"]), c["col_label"].strip())
    return [by_col[k] for k in sorted(by_col)]


def _lab(text):
    return _norm(text).rstrip("*").strip()


def classify(ca, cb):
    """identical data / same labels, different values / different labels (row or column headers differ)."""
    rows_a, rows_b = {_lab(c["row_label"]) for c in ca}, {_lab(c["row_label"]) for c in cb}
    cols_a, cols_b = {_lab(c["col_label"]) for c in ca}, {_lab(c["col_label"]) for c in cb}
    if rows_a != rows_b or cols_a != cols_b:
        return "different_labels"
    va = sorted((_lab(c["row_label"]), _lab(c["col_label"]), c["text"].strip()) for c in ca)
    vb = sorted((_lab(c["row_label"]), _lab(c["col_label"]), c["text"].strip()) for c in cb)
    return "identical_data" if va == vb else "same_labels_different_values"


def census(tables, cells):
    keyed, short = {}, []
    for t in tables:
        cs = cells.get((t["number"], t["index"]), [])
        k = title_key(t["title"], col_labels(cs))
        if len(k) < MIN_KEY:
            short.append([t["number"], t["label"], k])
            continue
        keyed.setdefault((t["number"], k), []).append(t)
    pairs = []
    for (num, k), ts in sorted(keyed.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = ts[i], ts[j]
                ca, cb = cells.get((num, a["index"]), []), cells.get((num, b["index"]), [])
                pairs.append({"number": int(num), "year": a["year"], "label_a": a["label"], "label_b": b["label"],
                              "key": k, "title_a": a["title"], "title_b": b["title"],
                              "class": classify(ca, cb), "cells_a": len(ca), "cells_b": len(cb),
                              "rows_a": " | ".join(sorted({c["row_label"] for c in ca}))[:300],
                              "rows_b": " | ".join(sorted({c["row_label"] for c in cb}))[:300]})
    classes = {}
    for p in pairs:
        classes[p["class"]] = classes.get(p["class"], 0) + 1
    ctrl = [p for p in pairs if p["number"] == 533 and {p["label_a"], p["label_b"]} == {"Figure 5", "Figure 6"}]
    summary = {"version": VERSION, "tables": len(tables), "briefs": len({t["number"] for t in tables}),
               "short_keys": len(short), "pairs": len(pairs),
               "briefs_with_pairs": len({p["number"] for p in pairs}), "by_class": classes,
               "positive_control_533_f5_f6": ctrl[0]["class"] if ctrl else None}
    return summary, pairs, short


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    tables = read_tables(a.tables)
    cells = read_cells(sorted(glob.glob(os.path.join(a.cells_dir, "*.csv"))))
    summary, pairs, short = census(tables, cells)
    fields = ["number", "year", "label_a", "label_b", "class", "cells_a", "cells_b", "key", "title_a", "title_b",
              "rows_a", "rows_b"]
    with open(os.path.join(a.out_dir, "m4-candidates.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in pairs:
            w.writerow(p)
    with open(os.path.join(a.out_dir, "m4-short-keys.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "label", "key"])
        w.writerows(short)
    with open(os.path.join(a.out_dir, "m4-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
