"""claimcheck command line (plan v5 section 3):

    python -m claimcheck <package.md> [--jobs <manifest.json>] [--plans <dir>]
        [--deadline 2027-03-26] --json out.json

Reads the package as UTF-8 bytes, applies the v4 cut, runs every module (R6-b only with
--plans, R7-b only with --jobs) and writes one JSON report. Unscored info flags are in the
same list with "scored": false. Deterministic apart from runtime_seconds; no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import json
import os
import sys
import time
from datetime import date

from . import __version__
from . import grammar as g
from . import modules2, modules3


def run(text, deadline=modules2.DEADLINE, plans=None, tools=None):
    """(doc, flags) for one package text."""
    doc = g.Doc(text)
    flags = modules2.check(doc, deadline) + modules3.check(doc, plans, tools)
    return doc, sorted(flags, key=lambda f: (f.line, f.module, f.rule, f.span))


def report(name, doc, flags, seconds):
    counts, info = {}, 0
    for f in flags:
        if f.scored:
            counts[f.module] = counts.get(f.module, 0) + 1
        else:
            info += 1
    return {"package": name, "checker": "claimcheck " + __version__,
            "lines_total": doc.total_lines, "lines_cut": doc.cut,
            "flags": [f.as_dict() for f in flags], "counts": counts,
            "scored": sum(counts.values()), "info": info,
            "runtime_seconds": round(seconds, 3)}


def main(argv=None):
    p = argparse.ArgumentParser(prog="claimcheck")
    p.add_argument("package")
    p.add_argument("--jobs", help="manifest mapping tool names to job files (R7-b)")
    p.add_argument("--plans", help="folder of plan files (R6-b)")
    p.add_argument("--deadline", default=modules2.DEADLINE.isoformat())
    p.add_argument("--json", required=True)
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    with open(a.package, "rb") as fh:
        text = fh.read().decode("utf-8")
    plans = modules3.load_plans(a.plans) if a.plans else None
    tools = modules3.load_manifest(a.jobs) if a.jobs else None
    doc, flags = run(text, date.fromisoformat(a.deadline), plans, tools)
    out = report(os.path.basename(a.package), doc, flags, time.perf_counter() - t0)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print("%s: %d scored flags, %d info" % (out["package"], out["scored"], out["info"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
