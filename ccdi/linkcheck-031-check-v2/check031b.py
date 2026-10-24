"""PRE-REGISTERED real-data check of LinkCheck 0.3.1's page-body reader and refetch rule, second
try (ccdi/linkcheck-031-check-v2; predictions R1-R4 from tag v0.8.5 and T1-T4 in README.md,
published at evidence-pack tag v0.8.7 before this job ran).

The first try (linkcheck-031-v1) ran on a machine without the kept second snapshot, so R1-R4
were not graded. A job cannot choose its machine, so this one grades whichever snapshot the
machine holds:
  - the kept second snapshot (/data/ccdi-raw-snapshot2): R1-R4 exactly as written at v0.8.5,
    by check031.py from that tag, unchanged;
  - else the newest complete fresh snapshot under the fresh root (one an earlier job kept, or
    the one ensure_snapshot2.py has just taken with fetch_robust.py): T1-T4, the same four
    checks with the fresh snapshot's expected values.

Aggregates only: counts, page numbers, source names and error kinds, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import json
import os

import check031
import ensure_snapshot2

# A fresh snapshot (ccdi-fresh-v1, 2026-10-23 21:47 to 2026-10-24 01:22 UTC): the same seven
# source totals as the second snapshot, so CCDI-DCC still ends on page 598 and the walk keeps
# page 599; PCDC fails on /subject page 35 only (page 12 was served again).
FRESH = {"pages": 599, "last": 598,
         "subject_flags": [[35, "PCDC", "error", None, 100]]}
R, T = ("R1", "R2", "R3", "R4"), ("T1", "T2", "T3", "T4")
LABEL = ("PRE-REGISTERED: predictions R1-R4 (tag v0.8.5) and T1-T4 in README.md, published "
         "at evidence-pack tag v0.8.7 before this job ran")


def not_graded(names, why):
    return {n: {"grade": "not graded", "why": why} for n in names}


def pick(kept, fresh_root):
    """(folder, description) of the snapshot to grade, or (None, None)."""
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        return kept, "kept second snapshot"
    found = ensure_snapshot2.complete(fresh_root)
    if found:
        return found[-1], "fresh snapshot " + os.path.basename(found[-1])
    return None, None


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(kept, fresh_root, fresh_expected=FRESH, cut=check031.CUT):
    raw, name = pick(kept, fresh_root)
    if raw is None:
        result = {"input": {"snapshot": None},
                  "grades": not_graded(R + T, "no complete snapshot on this machine")}
    elif raw == kept:
        result = check031.run(raw, cut=cut)
        result["grades"].update(not_graded(T, "the kept second snapshot was used"))
    else:
        result = check031.run(raw, fresh_expected, cut)
        grades = {"T" + r[1:]: g for r, g in result["grades"].items()}
        grades.update(not_graded(R, "no kept second snapshot on this machine"))
        result["grades"] = grades
        result["fresh_complete"] = read_json(os.path.join(raw, "complete.json"))
        result["fresh_retries"] = read_json(os.path.join(raw, "retries.json"))
    result["label"] = LABEL
    result["input"]["snapshot"] = name
    result["grades"] = dict(sorted(result["grades"].items()))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True, help="kept second snapshot")
    ap.add_argument("--fresh-root", required=True,
                    help="folder holding fresh snapshots (ccdi-raw-fresh-<UTC time>)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    result = run(args.kept, args.fresh_root)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "check031b.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot": result["input"]["snapshot"], "grades": result["grades"]},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
