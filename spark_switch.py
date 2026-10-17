#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""spark_switch: score the pre-registered cue switch on the SPARK Task 1 sample bench.

Pre-registration: spark/prereg-ce-switch-v1.md. Reads the per_question.jsonl
that spark_ce.py writes and adds one ranking that needs no new model run:

- switch: chosen (the v3 ranking) when the question has a priority cue, the
  MedCPT cross-encoder (ce) otherwise.

No question in devset_ordinary_v2.jsonl has a cue, so there switch is ce and
the test is ce against chosen. Any other dev set in the input is summarized
too; on the v1 sets the switch was found after looking at the results, so
those rows are labelled post hoc. Standard library only.

Usage: python spark_switch.py --per-question /out/ce/per_question.jsonl --out /out
       [--devset devset_ordinary_v2.jsonl]
"""
import argparse
import json
import os
import re
import sys

NEW = "devset_ordinary_v2.jsonl"
V1_ORDINARY_CHOSEN = 0.809  # chosen on devset_ordinary_v1.jsonl in v3 and in ce-rerank-v1
H1_GAIN = 0.05
H2_MAX_HURT = 3
H3_BAND = 0.10
S_MIN_IN_POOL = 26
METHODS = ("chosen", "ce", "switch")
# copied unchanged from spark_eval.py (v3)
CUE = re.compile(r"\b(first|original|landmark|seminal|introduc\w*|discover\w*|pioneer\w*|earliest|initial)\b")
YEAR_Q = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def cue_questions(devset):
    """ids of dev-set questions that match the bench's priority cue (the prereg allows none in v2)."""
    return [q["info_need_id"] for q in devset if CUE.search(q["info_need"].lower())]


def with_switch(row):
    """The row plus a 'switch' entry: chosen's ranking if the question has a cue, ce's otherwise."""
    return dict(row, switch=row["chosen"] if row["cue"] else row["ce"])


def mrr(rows, key):
    return round(sum(r[key]["rr"] for r in rows) / len(rows), 4) if rows else 0.0


def compare(rows, base, alt):
    """Questions where alt ranks the answer higher (helped) or lower (hurt) than base."""
    helped = [r["id"] for r in rows if r[alt]["rr"] > r[base]["rr"] + 1e-9]
    hurt = [r["id"] for r in rows if r[alt]["rr"] < r[base]["rr"] - 1e-9]
    return {"base": base, "alt": alt, "delta_mrr5": round(mrr(rows, alt) - mrr(rows, base), 4),
            "helped": helped, "hurt": hurt}


def summarize(rows):
    return {"n": len(rows), "in_pool": sum(1 for r in rows if r["in_pool"]),
            "cue": sum(1 for r in rows if r["cue"]),
            "mrr5": {m: mrr(rows, m) for m in METHODS},
            "ce_vs_chosen": compare(rows, "chosen", "ce")}


def hypotheses(s):
    """The tests of prereg-ce-switch-v1.md, applied to the new set's summary."""
    gain = round(s["mrr5"]["ce"] - s["mrr5"]["chosen"], 4)
    hurt = len(s["ce_vs_chosen"]["hurt"])
    out = {"H1": {"ce_minus_chosen": gain, "supported": gain >= H1_GAIN - 1e-9},
           "H2": {"hurt": hurt, "supported": hurt <= H2_MAX_HURT},
           "H3": {"chosen": s["mrr5"]["chosen"], "v1": V1_ORDINARY_CHOSEN,
                  "supported": abs(s["mrr5"]["chosen"] - V1_ORDINARY_CHOSEN) <= H3_BAND + 1e-9},
           "S": {"in_pool": s["in_pool"], "n": s["n"], "ok": s["in_pool"] >= S_MIN_IN_POOL}}
    out["decision"] = "switch is the provisional pick" if out["H1"]["supported"] else "keep chosen"
    return out


def word(ok):
    return "supported" if ok else "not supported"


def report(result):
    lines = ["# Cue switch on the SPARK Task 1 sample bench (spark/prereg-ce-switch-v1.md)", "",
             "| dev set | role | n | answer in pool | chosen | ce | switch | ce helped / hurt |",
             "|---|---|---|---|---|---|---|---|"]
    for name, s in result["sets"].items():
        c = s["ce_vs_chosen"]
        lines.append(f"| {name} | {s['role']} | {s['n']} | {s['in_pool']} | " +
                     " | ".join(f"{s['mrr5'][m]:.3f}" for m in METHODS) +
                     f" | {len(c['helped'])} / {len(c['hurt'])} |")
    h = result.get("hypotheses")
    if h:
        lines += ["", f"- H1 (ce - chosen >= {H1_GAIN} on {NEW}): {h['H1']['ce_minus_chosen']:+.4f}, "
                  f"{word(h['H1']['supported'])}",
                  f"- H2 (ce hurts at most {H2_MAX_HURT} questions): {h['H2']['hurt']} hurt, {word(h['H2']['supported'])}",
                  f"- H3 (chosen within {H3_BAND} of v1's {V1_ORDINARY_CHOSEN}): {h['H3']['chosen']:.3f}, "
                  f"{word(h['H3']['supported'])}",
                  f"- S (answer in pool for at least {S_MIN_IN_POOL}): {h['S']['in_pool']} of {h['S']['n']}, "
                  f"{'ok' if h['S']['ok'] else 'FAILED'}",
                  f"- **Decision: {h['decision']}**"]
        hurt = result["sets"][NEW]["ce_vs_chosen"]["hurt"]
        if hurt:
            lines.append(f"- Questions ce hurt: {', '.join(hurt)}")
    if result.get("cue_questions"):
        lines += ["", f"- Questions matching the cue (the prereg allows none): {', '.join(result['cue_questions'])}"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-question", nargs="+", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--devset", default="", help="the new dev set, to check that no question has a cue")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    sets = {}
    for path in args.per_question:
        for row in load(path):
            sets.setdefault(row.get("devset", os.path.basename(path)), []).append(with_switch(row))
    result = {"sets": {}}
    for name in sorted(sets):
        s = summarize(sets[name])
        s["role"] = "pre-registered test" if name == NEW else "post hoc"
        result["sets"][name] = s
    if NEW in result["sets"]:
        result["hypotheses"] = hypotheses(result["sets"][NEW])
    if args.devset:
        result["cue_questions"] = cue_questions(load(args.devset))
    with open(os.path.join(args.out, "switch_results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    text = report(result)
    with open(os.path.join(args.out, "switch_results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
