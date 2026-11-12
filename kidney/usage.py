#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""usage: the "every KPMP image used and how it was used" CSV that the NIDDK Kidney AI Discovery Challenge asks each
submission to include, built from the same download lists the compute jobs used, plus a train/test leakage check.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical device,
not for diagnosis or patient care. Standard library only. It reads no image and changes no pre-registered number.

Inputs:
  --csv   KPMP's open file list (columns "File Name", "Internal Package ID", "Participant ID").
  --use   stage:kind=path, repeated. path is a list the jobs really used: a download list
          [{"slide", "package", "name"}, ...] (fetch.py, gsdet select, prep plan) or a plain [package id, ...]
          (an exclusion list). kind is one of KINDS; stage is a free label such as stage6 or d-pass.
Output (--out): one CSV row per KPMP package (one whole-slide image each), in order of first use, with the columns
in COLUMNS. The CSV names KPMP files and participants, so it is a PRIVATE file for the submission only and is never
published in the repo; the command line prints totals only.

Leakage check: within one stage, no package and no participant may be both "train" and "dev"/"test", and no
"excluded" package may be used in any other way. Any of these makes the exit code 1. Overlaps ACROSS stages are
counted and reported (any_package, any_participant) but do not fail, because each stage's model is trained afresh
from the released weights; the report must still state them.

Usage:
  python -m kidney.usage --csv files.csv --use stage6:train=stage5-train.json --use stage6:test=test-list.json
      --use stage6:dev=slides.json --use stage6:excluded=excluded.json --use d-pass:pass=batch-01.json
      --out usage.csv --report usage-report.json        (one command line)
Exit codes: 0 clean; 1 a reported problem or a within-stage leak; 2 bad arguments or an unreadable list.
"""
import argparse
import csv
import json

from kidney import prep

CODE_VERSION = "0.1.0"
KINDS = ("train", "dev", "test", "pass", "qc", "excluded")
EVAL_KINDS = ("dev", "test")
KIND_TEXT = {
    "train": "training: model weights were fitted on it",
    "dev": "development: scored to check or choose settings, never trained on in this stage",
    "test": "held-out test: scored once as pre-registered, never trained on in this stage",
    "pass": "inference only: the detector was run on it for the analyses",
    "qc": "quality control: slide metadata and thumbnail read only",
    "excluded": "excluded: listed but left out on purpose",
}
COLUMNS = ("kpmp_file_name", "internal_package_id", "participant_id", "kinds", "how_used")


def parse_use(text):
    """'stage:kind=path' -> (stage, kind, path). Raises ValueError for anything else (no '=', no ':', an empty part,
    an unknown kind, or ';' in the stage, which the CSV uses as its separator)."""
    label, sep, path = text.partition("=")
    stage, sep2, kind = label.rpartition(":")
    if not sep or not sep2 or not stage or not path or kind not in KINDS or ";" in stage:
        raise ValueError("bad --use %r: want stage:kind=path with kind one of %s" % (text, ", ".join(KINDS)))
    return stage, kind, path


def items(doc):
    """[(package, name or None)] of one list: a download list of dicts with a "package" (and usually a "name"), or a
    plain list of package ids. Raises ValueError for anything else."""
    if not isinstance(doc, list):
        raise ValueError("a JSON list is expected")
    out = []
    for x in doc:
        if isinstance(x, str) and x:
            out.append((x, None))
        elif isinstance(x, dict) and isinstance(x.get("package"), str) and x["package"]:
            n = x.get("name")
            out.append((x["package"], n if isinstance(n, str) and n else None))
        else:
            raise ValueError("a list item has no package id")
    return out


def file_names(rows):
    """{package: [file names in the file list's order]}."""
    out = {}
    for r in rows:
        p, n = r.get("Internal Package ID"), r.get("File Name")
        if p and n:
            out.setdefault(p, []).append(n)
    return out


def default_name(names):
    """The package's first version 2 segmentation file name, else its first file name."""
    for n in names:
        if n.endswith(prep.V2_SUFFIX):
            return n
    return names[0]


def _kind_order(k):
    return KINDS.index(k)


def build(rows, uses):
    """rows: KPMP file-list rows. uses: [(stage, kind, [(package, name or None), ...]), ...].
    -> (table, report). table: one dict per package (keys COLUMNS) in order of first use. report: totals only."""
    pmap, ambiguous = prep.part_map(rows)
    names = file_names(rows)
    order, info = [], {}
    by_stage = {}
    for stage, kind, lst in uses:
        sets = by_stage.setdefault(stage, {k: set() for k in KINDS})
        for p, n in lst:
            if p not in info:
                order.append(p)
                info[p] = {"name": None, "uses": set(), "clash": False}
            d = info[p]
            if n is not None:
                if d["name"] is None:
                    d["name"] = n
                elif d["name"] != n:
                    d["clash"] = True
            d["uses"].add((stage, kind))
            sets[kind].add(p)
    prob = {"not_in_file_list": 0, "no_participant": 0, "name_mismatch": 0}
    table = []
    for p in order:
        d = info[p]
        known = names.get(p)
        if known is None:
            prob["not_in_file_list"] += 1
            name, part = d["name"] or "", ""
        else:
            if d["clash"] or (d["name"] is not None and d["name"] not in known):
                prob["name_mismatch"] += 1
            name = d["name"] or default_name(known)
            part = pmap.get(p, "")
            if not part:
                prob["no_participant"] += 1
        u = sorted(d["uses"], key=lambda x: (x[0], _kind_order(x[1])))
        kinds = sorted({k for _, k in u}, key=_kind_order)
        table.append({"kpmp_file_name": name, "internal_package_id": p, "participant_id": part,
                      "kinds": "; ".join(kinds),
                      "how_used": "; ".join("%s: %s" % (s, KIND_TEXT[k]) for s, k in u)})
    leaks = {"stage_package": 0, "stage_participant": 0, "excluded_used": 0, "any_package": 0, "any_participant": 0}
    all_train, all_eval = set(), set()

    def parts(ps):
        return {pmap[p] for p in ps if p in pmap}

    for stage in sorted(by_stage):
        s = by_stage[stage]
        ev = set().union(*(s[k] for k in EVAL_KINDS))
        leaks["stage_package"] += len(s["train"] & ev)
        leaks["stage_participant"] += len(parts(s["train"]) & parts(ev))
        used = set().union(*(s[k] for k in KINDS if k != "excluded"))
        leaks["excluded_used"] += len(s["excluded"] & used)
        all_train |= s["train"]
        all_eval |= ev
    leaks["any_package"] = len(all_train & all_eval)
    leaks["any_participant"] = len(parts(all_train) & parts(all_eval))
    by_kind = {k: sum(1 for p in order if any(kk == k for _, kk in info[p]["uses"])) for k in KINDS}
    by_use = {}
    for stage in sorted(by_stage):
        for k in KINDS:
            if by_stage[stage][k]:
                by_use["%s:%s" % (stage, k)] = len(by_stage[stage][k])
    report = {"code_version": CODE_VERSION, "packages": len(order),
              "participants": len({t["participant_id"] for t in table if t["participant_id"]}),
              "by_kind": by_kind, "by_use": by_use, "problems": prob, "leaks": leaks,
              "ambiguous_packages_in_file_list": ambiguous}
    report["ok"] = (not any(prob.values()) and leaks["stage_package"] == 0 and leaks["stage_participant"] == 0
                    and leaks["excluded_used"] == 0 and len(order) > 0)
    return table, report


def write_csv(path, table):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(COLUMNS))
        w.writeheader()
        for t in table:
            w.writerow(t)


def main(argv=None):
    ap = argparse.ArgumentParser(description="KPMP image usage CSV + leakage check (local, private output).")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--use", action="append", required=True, help="stage:kind=path (repeat)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    a = ap.parse_args(argv)
    uses = []
    for spec in a.use:
        try:
            stage, kind, path = parse_use(spec)
        except ValueError as e:
            ap.error(str(e))
        try:
            with open(path, encoding="utf-8") as f:
                lst = items(json.load(f))
        except (OSError, ValueError) as e:
            ap.error("%s: %s" % (path, str(e)[:200]))
        uses.append((stage, kind, lst))
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    table, report = build(rows, uses)
    write_csv(a.out, table)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
