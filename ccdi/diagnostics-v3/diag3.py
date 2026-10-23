"""POST-HOC diagnostics, stage 3, for the CCDI concordance census (ccdi-concord-v1).

Written on 2026-10-23 AFTER the ccdi-diag2-v1 results were seen. Nothing here was
pre-registered. Stage 2 found that the PCDC part of /subject fails at every page size tried
(100, 50, 25, 10) and narrowed the failure to records 3,461-3,470 of PCDC's paging order,
while the other 90 records of the old page 35 came back at smaller page sizes. This job asks:

  1  /subject at per_page 1, records 3,456-3,475: which single positions fail? Plus page
     347 at per_page 10 again, to see whether the failure persists.
  2  /subject-mapping over the same range (pages 34-35 at 100, 69-70 at 50, 341-350 at 10,
     records 3,456-3,475 at 1): how many entries come back per source, how many are not in
     the kept snapshot's mapping, and does any page carry an error?

v2 (2026-10-23): ccdi-diag3-v1 ran on a machine whose data volume did not hold the kept
snapshot and stopped before any request. With --allow-missing-snapshot the probes run
anyway: the snapshot comparisons are then reported as null, and source names are taken
from the live /subject responses instead of the snapshot. The questions are unchanged.

Aggregates only: positions and counts, never participant IDs. Error text is scrubbed of
anything identifier-like.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os
import time

import analyze
import diag
import fetch_ccdi

POSITIONS = tuple(range(3456, 3476))
SUBJECT_PROBES = ((347, 10),) + tuple((p, 1) for p in POSITIONS)
MAPPING_PROBES = (((34, 100), (35, 100), (69, 50), (70, 50))
                  + tuple((p, 10) for p in range(341, 351)) + tuple((p, 1) for p in POSITIONS))


def fetch(path, page, per_page, get, pause):
    time.sleep(pause)
    status, body = get(fetch_ccdi.fed_url(path, page=page, per_page=per_page))[:2]
    try:
        return status, json.loads(body)
    except (TypeError, ValueError):
        return status, None


def subject_probe(subjects, get=None, pause=fetch_ccdi.PAUSE, seen=None):
    """subjects=None means no kept snapshot: not_in_snapshot is reported as null.
    Source names in every response are added to the set `seen`, if given."""
    get = get or fetch_ccdi.get
    names = None if subjects is None else {s["name"] for s in subjects.values()
                                           if s["source"] == "PCDC"}
    rows = []
    for page, per_page in SUBJECT_PROBES:
        status, parsed = fetch("/subject", page, per_page, get, pause)
        row = {"page": page, "per_page": per_page, "status": status, "records": None}
        if not isinstance(parsed, list):
            row["error"] = "response is not a JSON list"
            rows.append(row)
            continue
        if seen is not None:
            seen.update(str(x["source"]) for x in parsed if isinstance(x, dict) and x.get("source"))
        item = next((x for x in parsed if isinstance(x, dict) and x.get("source") == "PCDC"),
                    None)
        data = item.get("data") if item else None
        if isinstance(data, list):
            got = [analyze.fed_subject(r, "PCDC")["name"] for r in data if isinstance(r, dict)]
            row["records"] = len(got)
            row["not_in_snapshot"] = (None if names is None
                                      else sum(1 for n in got if n not in names))
        else:
            row["error"] = diag.scrub(json.dumps({k: v for k, v in (item or {}).items()
                                                  if k not in ("data", "summary")}))
        rows.append(row)
    return rows


def mapping_probe(entries, sources, get=None, pause=fetch_ccdi.PAUSE):
    """entries=None means no kept snapshot: not_in_snapshot is reported as null."""
    get = get or fetch_ccdi.get
    known = None if entries is None else {(str(e.get("domain_name")).lower(),
                                           str(e.get("participant_id"))) for e in entries}
    rows = []
    for page, per_page in MAPPING_PROBES:
        status, parsed = fetch("/subject-mapping", page, per_page, get, pause)
        row = {"page": page, "per_page": per_page, "status": status}
        if not isinstance(parsed, dict):
            row["error"] = "response is not a JSON object"
            rows.append(row)
            continue
        by_dom, new = collections.Counter(), collections.Counter()
        for e in parsed.get("participant_ids") or []:
            if not isinstance(e, dict):
                continue
            dom = str(e.get("domain_name"))
            label = dom if dom in sources else "other"
            by_dom[label] += 1
            if known is not None and (dom.lower(), str(e.get("participant_id"))) not in known:
                new[label] += 1
        row["entries"] = dict(sorted(by_dom.items()))
        row["not_in_snapshot"] = None if known is None else dict(sorted(new.items()))
        other = {k: v for k, v in parsed.items() if k != "participant_ids"}
        if other:
            row["other_keys"] = diag.scrub(json.dumps(other, sort_keys=True), 300)
        rows.append(row)
    return rows


def main(argv=None, get=None, pause=fetch_ccdi.PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="raw/ folder kept by ccdi-diag-v1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-missing-snapshot", action="store_true",
                    help="run the probes without the kept snapshot (comparisons become null)")
    args = ap.parse_args(argv)
    found = os.path.exists(os.path.join(args.raw, "subject", "chosen.json"))
    if not found and not args.allow_missing_snapshot:
        raise SystemExit("kept snapshot not found under " + args.raw)
    subjects = entries = None
    snapshot_check = {"found": found}
    if found:
        _, _, subjects, _ = analyze.read_subjects(args.raw)
        entries = analyze.read_mappings(args.raw)
        snapshot_check.update({"subjects": len(subjects), "mapping_entries": len(entries)})
    else:
        print("kept snapshot not found under " + args.raw + "; probing without it", flush=True)
    seen = set()
    subject_rows = subject_probe(subjects, get=get, pause=pause, seen=seen)
    sources = {s["source"] for s in subjects.values()} if found else seen
    result = {"label": "POST HOC: written after ccdi-diag2-v1 results were seen",
              "snapshot_check": snapshot_check,
              "sources": sorted(sources),
              "subject_probe": subject_rows,
              "failing_positions_at_per_page_1": [r["page"] for r in subject_rows
                                                  if r["per_page"] == 1 and r["records"] is None],
              "mapping_probe": mapping_probe(entries, sources, get=get, pause=pause)}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "diagnostics3.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps(result, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
