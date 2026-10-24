"""PRE-REGISTERED real-data check of LinkCheck 0.4.0's CCDI snapshot reader
(ccdi/linkcheck-040-check-v1; predictions C1-C5 in README.md, published at evidence-pack tag
v0.8.9 before this job ran).

LinkCheck 0.4.0 moves the reading of a saved CCDI Data Federation snapshot into the package
(linkcheck/ccdi.py). Every earlier check read snapshots with job code: adapt() in
ccdi/linkcheck-repro-v2/repro2.py (tag v0.8.0) on the census's reader analyze.py (tag v0.5.5),
and ccdi_pages.py (tag v0.7.0). This job downloads that code unchanged and, on every snapshot
this machine keeps (the kept second snapshot, if it is here, and the newest complete fresh
snapshot), compares the package with it:
  C1  records: the same records, in the same order;
  C2  links: the same link rows, in the same order, and the same association counts;
  C3  pages: the same page size, per-page per-source counts on both endpoints, unmapped
      Participant Index entries and source totals;
  C4  the census: the exact pairs LinkCheck finds from the package's reading (ccdi.check) are
      exactly the census code's pairs, and its exact over-count equals the census's section D;
  C5  the snapshot's absolute numbers from the package alone: records, exact pairs, persons,
      naive over-count and shared ids.
No request goes to the federation: a machine that keeps no snapshot grades nothing.

Aggregates only: counts, page numbers and source names, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import json
import os

import analyze
import ccdi_pages
import ensure_snapshot2
import repro2
from linkcheck import ccdi, core

SHARED = {"CCDI-DCC": {"ids": 87, "records": 174}}
# The second snapshot (2026-10-22/23): linkcheck-repro-v2 (tag v0.8.1). A fresh snapshot
# (2026-10-23/24): fresh-snapshot-v1 (tag v0.8.6). The Dell's fresh snapshot (2026-10-24
# 02:01-05:53 UTC) has had only its pages audited (tag v0.8.8), with the same source totals.
EXPECTED = {
    "kept second snapshot": {"records": 153580, "pairs_exact": 20496, "persons": 135849,
                             "naive_overcount": 17731, "shared_ids": SHARED},
    "fresh": {"records": 153680, "pairs_exact": 20496, "persons": 135949,
              "naive_overcount": 17731, "shared_ids": SHARED}}
CHECKS = ("C1", "C2", "C3", "C4", "C5")
LABEL = ("PRE-REGISTERED: predictions C1-C5 in README.md, published at evidence-pack tag "
         "v0.8.9 before this job ran")


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def first_difference(a, b):
    """The first position at which two lists differ (a length difference counts), or None."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def differing_pages(a, b):
    return sorted(n for n in set(a) | set(b) if a.get(n, "absent") != b.get(n, "absent"))


def snapshots(kept, fresh_root):
    """[(folder, name)] of the snapshots this machine keeps."""
    out = []
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        out.append((kept, "kept second snapshot"))
    found = ensure_snapshot2.complete(fresh_root) if fresh_root else []
    if found:
        out.append((found[-1], "fresh"))
    return out


def grade_one(raw, expected):
    """Grades C1-C5 on one snapshot, and the package's aggregate result."""
    _, _, subjects, _ = analyze.read_subjects(raw)
    entries = analyze.read_mappings(raw)
    j_records, j_links, j_counts = repro2.adapt(subjects, entries)
    ref = repro2.census(subjects, entries)
    j_per_page, j_spages, domains, names = ccdi_pages.subject_walk(raw)
    j_mpages, j_unmapped = ccdi_pages.mapping_walk(raw, domains, names)
    j_totals = ccdi_pages.summary_totals(raw)
    del subjects, entries, domains, names

    snap = ccdi.read_snapshot(raw)
    g = {}
    g["C1"] = verdict(snap["records"] == j_records, records=len(snap["records"]),
                      job_records=len(j_records),
                      first_difference=first_difference(snap["records"], j_records))
    g["C2"] = verdict(snap["links"] == j_links and snap["link_counts"] == j_counts,
                      link_rows=len(snap["links"]), job_link_rows=len(j_links),
                      first_difference=first_difference(snap["links"], j_links),
                      counts=snap["link_counts"], job_counts=j_counts)
    ds = differing_pages(snap["subject_pages"], j_spages)
    dm = differing_pages(snap["mapping_pages"], j_mpages)
    g["C3"] = verdict(snap["per_page"] == j_per_page and not ds and not dm
                      and snap["unmapped_mapping_entries"] == j_unmapped
                      and snap["totals"] == j_totals,
                      per_page=snap["per_page"], subject_pages=len(snap["subject_pages"]),
                      mapping_pages=len(snap["mapping_pages"]),
                      differing_subject_pages=ds, differing_mapping_pages=dm,
                      unmapped=snap["unmapped_mapping_entries"], job_unmapped=j_unmapped,
                      totals_equal=snap["totals"] == j_totals)
    index = core.Index(snap["records"])
    pairs, _ = core.resolve_links(index, snap["links"], core.RULES)
    exact = {p for p, rule in pairs.items() if rule == "exact"}
    del snap, index, pairs, j_records, j_links

    result, _ = ccdi.check(raw, core.RULES, repro2.PRIORITY)
    report = result["linkcheck"]
    oc = report["overcount"]["exact"]
    mine = {"persons": oc["persons"], "naive_overcount": oc["naive_overcount"],
            "linked_persons": oc["linked_persons"], "records_in_links": oc["records_in_links"]}
    d = ref["d"]
    theirs = {"persons": d["deduplicated_total"], "naive_overcount": d["naive_overcount"],
              "linked_persons": d["linked_persons"],
              "records_in_links": d["subjects_in_cross_source_links"]}
    only_census, only_lc = len(ref["pair_keys"] - exact), len(exact - ref["pair_keys"])
    g["C4"] = verdict(only_census == 0 and only_lc == 0
                      and report["links"]["pairs_exact"] == ref["pairs"] and mine == theirs,
                      linkcheck_pairs=report["links"]["pairs_exact"], census_pairs=ref["pairs"],
                      census_only=only_census, linkcheck_only=only_lc,
                      linkcheck=mine, census=theirs)
    got = {"records": oc["records"], "pairs_exact": report["links"]["pairs_exact"],
           "persons": oc["persons"], "naive_overcount": oc["naive_overcount"],
           "shared_ids": report["shared_ids"]}
    g["C5"] = verdict(got == expected, **got)
    return g, result


def overall(per_snapshot):
    """A prediction holds if it passes on every snapshot graded."""
    out = {}
    for c in CHECKS:
        grades = [s["grades"][c]["grade"] for s in per_snapshot]
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
    return isinstance(obj, str) and bool(analyze.USI.match(obj))


def run(kept, fresh_root, expected=EXPECTED):
    per_snapshot = []
    for raw, name in snapshots(kept, fresh_root):
        grades, result = grade_one(raw, expected[name])
        per_snapshot.append({"snapshot": name if name != "fresh" else
                             "fresh snapshot " + os.path.basename(raw),
                             "grades": grades, "result": result})
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
    with open(os.path.join(args.out, "check040.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshots": out["snapshots"], "grades": out["grades"],
                      "per_snapshot": {s["snapshot"]: {c: g["grade"] for c, g in
                                                      s["grades"].items()}
                                       for s in out["per_snapshot"]}},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
