#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# The bundled table (../data/meps-statbrief-errata.csv) is CC BY 4.0; the published numbers in it are AHRQ's.
"""meps_errata: look up known slips, reproduction results and documentation gaps in AHRQ's MEPS Statistical Briefs.

Made with AI agents (Claude) working in MV2's name at Munim, Inc. Read-only and offline: it reads one bundled CSV
and never touches the network. Every row is a lead found by an open, pre-registered check in
github.com/munimtechnologies/evidence-pack and links the note behind it. No row has been confirmed by a person or
by AHRQ. Research information about published statistics, not medical advice.

Examples:
  python meps_errata.py --brief 558
  python meps_errata.py --brief 558 --value 6.2
  python meps_errata.py --kind reproduction
  python meps_errata.py --summary
  python meps_errata.py --grep deductible --json
Exit codes: 0 at least one row matched, 1 no row matched, 2 the table could not be read.
"""
import argparse
import csv
import json
import os
import re
import sys

VERSION = "0.1.0"
TABLE_VERSION = "0.2.0"
REPO = "https://github.com/munimtechnologies/evidence-pack/blob/main/"
COLUMNS = ("id", "brief", "data_year", "file", "place", "kind", "evidence", "printed", "alternative", "cells",
           "computable", "exact", "close", "what", "note")
COUNT_FIELDS = ("cells", "computable", "exact", "close")
REPRODUCES_SHARE = 0.80   # the pre-registered R2/R2b threshold: at least 80% of computable cells close
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def default_csv():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", "meps-statbrief-errata.csv"))


def load(path):
    """Rows of the table as dicts (count fields as int or None). ValueError if a column is missing."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("missing columns: " + ", ".join(missing))
        rows = []
        for r in reader:
            row = {c: (r.get(c) or "").strip() for c in COLUMNS}
            for c in COUNT_FIELDS:
                row[c] = int(row[c]) if row[c] else None
            rows.append(row)
    return rows


def numbers(text):
    """Numbers written in a field, as floats (signs and % are ignored: '-0.9%' gives 0.9)."""
    return [float(x) for x in NUMBER.findall(text or "")]


def brief_number(text):
    """'558', '#558' or 'stat558' -> '558'; anything else -> the stripped text."""
    m = re.search(r"\d+", text or "")
    return str(int(m.group(0))) if m else (text or "").strip()


def reproduces(row):
    """True/False for a reproduction row (close share of computable cells >= 80%), None otherwise."""
    if row.get("kind") != "reproduction" or not row.get("computable"):
        return None
    return row["close"] / float(row["computable"]) >= REPRODUCES_SHARE


def select(rows, brief=None, kind=None, grep=None, value=None, ids=None):
    """Rows matching every filter given. value matches a number in the printed or alternative field."""
    out = []
    for r in rows:
        if brief is not None and r["brief"] != brief_number(str(brief)):
            continue
        if kind and r["kind"].lower() != kind.lower():
            continue
        if ids and r["id"] not in ids:
            continue
        if grep:
            hay = " ".join(str(r[c]) for c in ("place", "kind", "printed", "alternative", "what")).lower()
            if grep.lower() not in hay:
                continue
        if value is not None:
            want = numbers(str(value))
            have = numbers(r["printed"]) + numbers(r["alternative"])
            if not want or not any(abs(w - h) < 1e-9 for w in want for h in have):
                continue
        out.append(r)
    return out


def summary(rows):
    """Lines: '<n> items', then one line per kind, then the reproduction tally."""
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    lines = ["%d items" % len(rows)]
    lines += ["  %s: %d" % (k, kinds[k]) for k in sorted(kinds)]
    rep = [r for r in rows if r["kind"] == "reproduction"]
    if rep:
        comp = sum(r["computable"] or 0 for r in rep)
        lines.append("reproduction: %d briefs, %d of %d computable cells exact, %d close; not reproducing: %s" % (
            len(rep), sum(r["exact"] or 0 for r in rep), comp, sum(r["close"] or 0 for r in rep),
            ", ".join("#" + r["brief"] for r in rep if reproduces(r) is False) or "none"))
    return lines


def render(r):
    head = "%s  #%s %s  [%s; %s]" % (r["id"], r["brief"], r["place"], r["kind"], r["evidence"])
    lines = [head]
    if r["data_year"] or r["file"]:
        lines.append("  data: %s" % " ".join(x for x in (r["data_year"], r["file"]) if x))
    if r["printed"]:
        lines.append("  printed: %s" % r["printed"])
    if r["alternative"]:
        lines.append("  other: %s" % r["alternative"])
    lines.append("  " + r["what"])
    lines.append("  note: " + REPO + r["note"])
    lines.append("  brief: https://meps.ahrq.gov/data_files/publications/st%s/stat%s.shtml" % (r["brief"], r["brief"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Known slips, reproduction results and documentation gaps in MEPS "
                                             "Statistical Briefs (offline lookup).")
    ap.add_argument("--csv", default=None, help="table path (default: the bundled copy)")
    ap.add_argument("--brief", help="brief number, e.g. 558")
    ap.add_argument("--kind", help="e.g. 'figure vs text', reproduction, 'documentation gap', label, title")
    ap.add_argument("--grep", help="case-insensitive text in place/kind/printed/alternative/what")
    ap.add_argument("--value", help="a number you are about to quote, e.g. 6.2")
    ap.add_argument("--id", action="append", dest="ids", help="row id, e.g. MEPS-E009 (repeatable)")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    if a.version:
        print("meps_errata %s, table %s" % (VERSION, TABLE_VERSION))
        return 0
    try:
        rows = load(a.csv or default_csv())
    except (OSError, ValueError, csv.Error) as e:
        print("cannot read the table: %s" % e, file=sys.stderr)
        return 2
    if a.summary:
        print("\n".join(summary(rows)))
        return 0 if rows else 1
    got = select(rows, brief=a.brief, kind=a.kind, grep=a.grep, value=a.value, ids=a.ids)
    if a.json:
        print(json.dumps(got, indent=1))
    elif got:
        print("\n\n".join(render(r) for r in got))
    else:
        print("no known item matches (this is not proof the number is right; see SKILL.md)")
    return 0 if got else 1


if __name__ == "__main__":
    raise SystemExit(main())
