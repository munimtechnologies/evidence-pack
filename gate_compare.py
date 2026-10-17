#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""gate_compare: apply the pre-registered decision rule of prereg-cite-gate-v1.md.

Reads the results.json of the landmark and the ordinary dev set and picks the
citation-prior variant to keep:

1. eligible: ordinary-set MRR@5 >= fields+ptype's minus 0.02;
2. choose: highest equal-weight mean of the two sets' MRR@5;
3. ties go to the simpler rule, in the order of CANDIDATES.

Usage: python gate_compare.py /out/landmark/results.json /out/ordinary/results.json --out /out
"""
import argparse
import json
import os
import sys

REFERENCE = "fields+ptype"
# simplest first: this order breaks ties
CANDIDATES = [REFERENCE, "fields+ptype+cite0.1", "fields+ptype+cite|band0.8", "fields+ptype+cite|cue",
              "fields+ptype+cite|cue+early+year"]
REPORTED = ["fields+ptype+cite"]  # the ungated v1/v2 variant: shown, never chosen
SLACK = 0.02


def decide(landmark, ordinary, slack=SLACK):
    """landmark, ordinary: {method: mrr5}. Returns (chosen, table) where table has one row per method."""
    floor = ordinary[REFERENCE] - slack
    table = []
    for name in CANDIDATES + REPORTED:
        mean = (landmark[name] + ordinary[name]) / 2
        table.append({"method": name, "landmark": landmark[name], "ordinary": ordinary[name],
                      "mean": round(mean, 4), "d_landmark": round(landmark[name] - landmark[REFERENCE], 4),
                      "d_ordinary": round(ordinary[name] - ordinary[REFERENCE], 4),
                      "eligible": name in CANDIDATES and ordinary[name] >= floor - 1e-9})
    best = None
    for row in table:  # CANDIDATES come first and in tie-break order, so a strict > keeps the simpler one
        if row["eligible"] and (best is None or row["mean"] > best["mean"] + 1e-9):
            best = row
    return best["method"], table


def mrr(path):
    with open(path, encoding="utf-8") as f:
        res = json.load(f)
    return {k: v["mrr5"] for k, v in res["methods"].items()}, res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("landmark")
    ap.add_argument("ordinary")
    ap.add_argument("--out", default="out")
    args = ap.parse_args(argv)
    lm, lm_res = mrr(args.landmark)
    od, od_res = mrr(args.ordinary)
    chosen, table = decide(lm, od)
    out = {"chosen": chosen, "slack": SLACK, "table": table,
           "cue_questions": {"landmark": lm_res.get("cue_questions"), "ordinary": od_res.get("cue_questions")},
           "n": {"landmark": lm_res["methods"][REFERENCE]["n"], "ordinary": od_res["methods"][REFERENCE]["n"]}}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "decision.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    lines = ["# Citation-prior gate: pre-registered decision (prereg-cite-gate-v1.md)", "",
             f"Questions: landmark {out['n']['landmark']} ({out['cue_questions']['landmark']} with a priority cue), "
             f"ordinary {out['n']['ordinary']} ({out['cue_questions']['ordinary']} with a cue).", "",
             "| method | landmark | ordinary | mean | vs fields+ptype (landmark / ordinary) | eligible |",
             "|---|---|---|---|---|---|"]
    for r in table:
        lines.append(f"| {r['method']} | {r['landmark']:.3f} | {r['ordinary']:.3f} | {r['mean']:.3f} | "
                     f"{r['d_landmark']:+.3f} / {r['d_ordinary']:+.3f} | {'yes' if r['eligible'] else 'no'} |")
    lines += ["", f"**Chosen: {chosen}.**"]
    with open(os.path.join(args.out, "decision.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"chosen": chosen, "table": table}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
