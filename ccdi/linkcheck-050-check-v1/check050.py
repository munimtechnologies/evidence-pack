"""PRE-REGISTERED real-data check of LinkCheck 0.5.0's OMB race/ethnicity reading
(ccdi/linkcheck-050-check-v1; predictions S1-S6 in README.md, published at evidence-pack tag
v0.9.1 before this job ran).

On every snapshot of NCI's CCDI Data Federation this machine keeps (the kept second snapshot,
if it is here, and the newest complete fresh snapshot), this job runs:
  - LinkCheck 0.4.0 (tag v0.8.9), in a separate process, as the reference;
  - LinkCheck 0.5.0 with no declared convention;
  - LinkCheck 0.5.0 with CCDI-DCC declared as following OMB's 2024 combined question.
and grades:
  S1  0.5.0 gives exactly 0.4.0's result (every key but "tool" and the new "standards"
      section) and 0.4.0's cohort columns, row for row;
  S2  the only served records carrying a 2024-only race value (Hispanic or Latino, or Middle
      Eastern or North African, in the race list) are CCDI-DCC's 24 "White, Hispanic or
      Latino" records; at least 20 of them also state Hispanic or Latino as ethnicity;
  S3  (an identity of the code) per source, the records read as 1997, both or contradictory
      are exactly the records with an informative ethnicity;
  S4  with nothing declared, no record's "not Hispanic" is implied, and CCDI-DCC serves no
      "Not Hispanic or Latino" record;
  S5  with CCDI-DCC declared 2024, between 46,650 and 47,101 CCDI-DCC records are read as
      not Hispanic or Latino by implication;
  S6  with CCDI-DCC declared 2024, in linked pairs where one record's "not Hispanic" is only
      implied and the other record states its ethnicity, at least 5% of the stated values
      are "Hispanic or Latino" (at least 100 such pairs needed to grade); below 2% would
      support the 2024 reading, 2% to under 5% is inconclusive.
No request goes to the federation: a machine that keeps no snapshot grades nothing.

Aggregates only: counts and source names, never participant IDs. The cohort tables, which
hold record ids, are written to a temporary folder, compared and deleted.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

import ensure_snapshot2
from linkcheck import ccdi, core

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "old")
DECLARED = {"CCDI-DCC": "2024"}
# S2: the 24 CCDI-DCC records served with race "White, Hispanic or Latino" as one string
# (post-hoc demographics note, parts 3-4, tag v0.5.8); at least 20 of them are served with
# ethnicity Hispanic or Latino.
S2_DCC_RECORDS, S2_DCC_BOTH_MIN = 24, 20
S2_DCC_VALUES = {"Hispanic or Latino": 24}
S5_RANGE = (46650, 47101)
S6_MIN_PAIRS, S6_THRESHOLD, S6_SUPPORTS_BELOW = 100, 0.05, 0.02
CHECKS = ("S1", "S2", "S3", "S4", "S5", "S6")
LABEL = ("PRE-REGISTERED: predictions S1-S6 in README.md, published at evidence-pack tag "
         "v0.9.1 before this job ran")


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def snapshots(kept, fresh_root):
    """[(folder, name)] of the snapshots this machine keeps."""
    out = []
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        out.append((kept, "kept second snapshot"))
    found = ensure_snapshot2.complete(fresh_root) if fresh_root else []
    if found:
        out.append((found[-1], "fresh snapshot " + os.path.basename(found[-1])))
    return out


def as_json(obj):
    """The object as it would be written and read back (string keys, lists for tuples)."""
    return json.loads(json.dumps(obj, sort_keys=True))


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def compare_old(raw, new_result, new_rows, tmp):
    """S1: 0.4.0 (in its own process) against 0.5.0 on one snapshot."""
    old_json, old_csv = os.path.join(tmp, "old.json"), os.path.join(tmp, "old.csv")
    new_csv = os.path.join(tmp, "new.csv")
    subprocess.run([sys.executable, "-m", "linkcheck.ccdi", "--raw", raw, "--out", old_json,
                    "--cohort", old_csv], cwd=OLD, check=True, stdout=subprocess.DEVNULL)
    with open(old_json, encoding="utf-8") as fh:
        old = json.load(fh)
    new = as_json(new_result)
    differing = sorted(k for k in set(old) | set(new)
                       if k not in ("tool", "linkcheck") and old.get(k) != new.get(k))
    old_lc, new_lc = old["linkcheck"], new["linkcheck"]
    differing += sorted("linkcheck." + k for k in set(old_lc) | set(new_lc)
                        if k not in ("tool", "standards") and old_lc.get(k) != new_lc.get(k))
    core.write_cohort(new_rows, new_csv)
    old_fields, old_rows = read_csv(old_csv)
    new_fields, new_rows_read = read_csv(new_csv)
    same_rows = len(old_rows) == len(new_rows_read) and all(
        a == {f: b[f] for f in old_fields} for a, b in zip(old_rows, new_rows_read))
    added = [f for f in new_fields if f not in old_fields]
    for p in (old_json, old_csv, new_csv):
        os.remove(p)
    return verdict(not differing and same_rows and new_fields[:len(old_fields)] == old_fields,
                   old_tool=old.get("tool"), new_tool=new.get("tool"),
                   differing_keys=differing, cohort_rows=[len(old_rows), len(new_rows_read)],
                   cohort_old_columns_identical=same_rows, cohort_columns_added=added)


def grade_one(raw, tmp):
    plain, rows = ccdi.check(raw, core.RULES)
    g = {"S1": compare_old(raw, plain, rows, tmp)}
    del rows
    rep = plain["linkcheck"]
    by_src = rep["standards"]["by_source"]
    only24 = {s: {k: v["convention"].get(k, 0) for k in ("2024", "both", "contradictory")}
              for s, v in by_src.items()}
    others_clean = all(not any(only24[s].values()) and not v["values_2024_only"]
                       and v["hispanic_in_race_list"] == 0
                       for s, v in by_src.items() if s != "CCDI-DCC")
    d24 = only24.get("CCDI-DCC", {})
    dv = by_src.get("CCDI-DCC", {})
    dcc_as_predicted = (dv.get("values_2024_only") == S2_DCC_VALUES
                        and dv.get("hispanic_in_race_list") == S2_DCC_RECORDS
                        and d24.get("both", 0) >= S2_DCC_BOTH_MIN
                        and d24.get("both", 0) + d24.get("2024", 0) == S2_DCC_RECORDS
                        and d24.get("contradictory", 0) == 0)
    g["S2"] = verdict(others_clean and dcc_as_predicted,
                      conventions_2024=only24,
                      values_2024_only={s: v["values_2024_only"] for s, v in by_src.items()},
                      hispanic_in_race_list={s: v["hispanic_in_race_list"]
                                             for s, v in by_src.items()})
    s3 = {s: [sum(v["convention"].get(k, 0) for k in ("1997", "both", "contradictory")),
              rep["completeness"][s]["informative"]["ethnicity"]] for s, v in by_src.items()}
    g["S3"] = verdict(all(a == b for a, b in s3.values()),
                      read_with_ethnicity_vs_completeness=s3)
    implied = {s: v["hispanic"].get("NH_implied", 0) for s, v in by_src.items()}
    dcc = by_src.get("CCDI-DCC", {}).get("hispanic", {})
    g["S4"] = verdict("CCDI-DCC" in by_src and not any(implied.values())
                      and dcc.get("NH", 0) == 0,
                      nh_implied=implied, ccdi_dcc_hispanic=dcc)

    declared, _ = ccdi.check(raw, core.RULES, (), DECLARED)
    st = declared["linkcheck"]["standards"]
    dcc_d = st["by_source"].get("CCDI-DCC", {})
    n5 = dcc_d.get("hispanic", {}).get("NH_implied", 0)
    g["S5"] = verdict(S5_RANGE[0] <= n5 <= S5_RANGE[1], ccdi_dcc_nh_implied=n5,
                      ccdi_dcc_hispanic=dcc_d.get("hispanic"),
                      ccdi_dcc_convention=dcc_d.get("convention"), range=list(S5_RANGE))
    vs = st["pairs"]["exact"]["all"]["implied_nh_vs_stated"]
    n6 = vs.get("H", 0) + vs.get("NH", 0)
    share = round(vs.get("H", 0) / n6, 4) if n6 else None
    by_pair = {k: v["implied_nh_vs_stated"] for k, v in
               st["pairs"]["exact"]["by_source_pair"].items() if v["implied_nh_vs_stated"]}
    if share is None:
        reading = None
    elif share < S6_SUPPORTS_BELOW:
        reading = "supports the 2024 reading"
    elif share < S6_THRESHOLD:
        reading = "inconclusive"
    else:
        reading = "contradicts the 2024 reading"
    eth = rep["conflicts"]["exact"]["all"]["ethnicity"]
    stated_both = eth.get("agree", 0) + eth.get("disagree", 0)
    obs = dict(implied_nh_vs_stated=vs, pairs=n6, share_stated_hispanic=share,
               reading=reading, by_source_pair=by_pair, threshold=S6_THRESHOLD,
               supports_below=S6_SUPPORTS_BELOW, min_pairs=S6_MIN_PAIRS,
               baseline_1997_ethnicity_disagreement=[eth.get("disagree", 0), stated_both])
    if n6 < S6_MIN_PAIRS:
        g["S6"] = {"grade": "not gradable", "observed": obs}
    else:
        g["S6"] = verdict(share >= S6_THRESHOLD, **obs)
    descriptive = {
        "plain": {"by_source": by_src,
                  "pairs_exact_all": rep["standards"]["pairs"]["exact"]["all"],
                  "persons_hispanic_conflict": rep["standards"]["persons_hispanic_conflict"],
                  "ethnicity_conflicts_exact_all": rep["conflicts"]["exact"]["all"]["ethnicity"]},
        "declared": {"declared": st["declared"], "by_source": st["by_source"],
                     "pairs_exact_all": st["pairs"]["exact"]["all"],
                     "pairs_exact_by_source_pair": st["pairs"]["exact"]["by_source_pair"],
                     "persons_hispanic_conflict": st["persons_hispanic_conflict"]},
        "records": plain["input"]["records"],
        "pairs_exact": rep["links"]["pairs_exact"]}
    return g, descriptive


def overall(per_snapshot):
    """A prediction holds if it passes on every snapshot where it could be graded."""
    out = {}
    for c in CHECKS:
        grades = [s["grades"][c]["grade"] for s in per_snapshot
                  if s["grades"][c]["grade"] != "not gradable"]
        if not grades:
            out[c] = "not graded"
        else:
            out[c] = "pass" if all(x == "pass" for x in grades) else "fail"
    return out


def has_ids(obj):
    """True if any key or string in obj looks like a COG USI (a participant id)."""
    if isinstance(obj, dict):
        return any(has_ids(k) or has_ids(v) for k, v in obj.items())
    if isinstance(obj, list):
        return any(has_ids(v) for v in obj)
    return isinstance(obj, str) and bool(ccdi.USI.match(obj))


def run(kept, fresh_root):
    per_snapshot = []
    tmp = tempfile.mkdtemp()
    try:
        for raw, name in snapshots(kept, fresh_root):
            grades, descriptive = grade_one(raw, tmp)
            per_snapshot.append({"snapshot": name, "grades": grades,
                                 "descriptive": descriptive})
    finally:
        shutil.rmtree(tmp)
    out = {"label": LABEL, "linkcheck": "linkcheck " + core.__version__,
           "snapshots": [s["snapshot"] for s in per_snapshot],
           "grades": overall(per_snapshot), "per_snapshot": per_snapshot}
    if has_ids(out):
        raise SystemExit("refusing to write: the result holds something shaped like a USI")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True, help="kept second snapshot")
    ap.add_argument("--fresh-root", required=True,
                    help="folder holding fresh snapshots (ccdi-raw-fresh-<UTC time>)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = run(args.kept, args.fresh_root)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "check050.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshots": out["snapshots"], "grades": out["grades"],
                      "per_snapshot": {s["snapshot"]: {c: g["grade"] for c, g in
                                                      s["grades"].items()}
                                       for s in out["per_snapshot"]}},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
