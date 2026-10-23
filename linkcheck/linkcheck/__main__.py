"""Command line: python -m linkcheck --records R.jsonl --links L.jsonl --out report.json

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import json
import sys

from . import core


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="linkcheck",
        description="Completeness, conflict and over-count report for linked records.")
    ap.add_argument("--records", required=True,
                    help="JSON Lines: source, id, alt_ids, sex, race, ethnicity, "
                         "vital_status, age_at_vital_status")
    ap.add_argument("--links", required=True,
                    help="JSON Lines: a_source, a_id, b_source, b_id")
    ap.add_argument("--out", required=True, help="aggregate report (JSON)")
    ap.add_argument("--rules", default=",".join(core.RULES),
                    help="link rules to use, from: " + ", ".join(core.RULES))
    ap.add_argument("--priority", default="",
                    help="source order for the vital_priority column, e.g. B,A")
    ap.add_argument("--cohort",
                    help="also write the person-level cohort table (CSV). It lists record "
                         "ids, so keep it as private as the input")
    ap.add_argument("--min-cell", type=int, default=0,
                    help="show report counts below this as '<N' (default 0: off)")
    args = ap.parse_args(argv)
    rules = [r for r in args.rules.split(",") if r]
    priority = [p for p in args.priority.split(",") if p]
    report, rows = core.check(core.read_jsonl(args.records), core.read_jsonl(args.links),
                              rules, priority)
    report = core.suppress(report, args.min_cell)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    if args.cohort:
        core.write_cohort(rows, args.cohort)
    print(json.dumps(report["overcount"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
