"""PRE-REGISTERED real-data check of LinkCheck 0.3.1's page-body reader and refetch rule
(ccdi/linkcheck-031-check-v1; predictions R1-R4 in README.md, published at evidence-pack tag
v0.8.5 before this job ran).

On the kept second CCDI snapshot it:
  - reads every saved /subject page with linkcheck.paging.body_counts and compares the
    counts with those of the paging audit's own reader (ccdi/paging-audit-v1/ccdi_pages.py,
    tag v0.7.0, which held Q1-Q6);
  - audits both endpoints with LinkCheck 0.3.1, including the new last page the totals
    require and the pages a walker should have fetched again;
  - finds the first page a walk-until-empty client would stop at;
  - counts the error objects on /subject pages by source and kind (the kind only; error
    messages never leave the job);
  - replays the third snapshot's cut (a walk stopped at /subject-mapping page 345) through
    the refetch rule (descriptive).

Aggregates only: counts, page numbers, source names and error kinds, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os

import ccdi_pages
from linkcheck import paging

# Second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC): 599 pages walked per endpoint;
# CCDI-DCC's 59,795 subjects end on page 598; PCDC fails on /subject pages 12 and 35
# (ccdi/paging-audit-v1, Q1).
SNAPSHOT2 = {"pages": 599, "last": 598,
             "subject_flags": [[12, "PCDC", "error", None, 100],
                               [35, "PCDC", "error", None, 100]]}
CUT = 345
LABEL = ("PRE-REGISTERED: predictions R1-R4 in README.md, published at evidence-pack tag "
         "v0.8.5 before this job ran")


def subject_files(raw):
    """{page number: path} of the saved /subject pages, read as the census reads them."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = ccdi_pages.numbered(os.path.join(raw, "subject"))
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    return files


def kind_of(message):
    return message.split(": ", 1)[0] if ": " in message else "(not an object)"


def body_walk(raw):
    """(pages, rejected, error_kinds) from paging.body_counts on every saved /subject page.
    error_kinds counts "source | kind" over the error objects; messages are never kept."""
    pages, rejected, kinds = {}, [], collections.Counter()
    for n, path in sorted(subject_files(raw).items()):
        parsed = ccdi_pages.load(path)
        try:
            pages[n] = paging.body_counts(parsed)
        except ValueError:
            rejected.append(n)
            continue
        for item in parsed if isinstance(parsed, list) else [parsed]:
            src = str(item.get("source", "(whole page)"))
            for m in paging.error_messages(item):
                kinds[src + " | " + kind_of(m)] += 1
    return pages, rejected, dict(sorted(kinds.items()))


def first_empty(pages):
    """The first page a walk-until-empty client stops at: failed, or no entries at all."""
    for n in sorted(pages):
        if pages[n] is None or not any(pages[n].values()):
            return n
    return None


def replay(mpages, per_page, totals, cut):
    """What the refetch rule says about a walk that stopped at page `cut` because that page
    came back with no entries."""
    walked = {n: c for n, c in mpages.items() if n < cut}
    walked[cut] = {}
    pages = paging.refetch_pages(walked, per_page, totals)
    return {"cut_at": cut, "refetch_count": len(pages),
            "refetch_first": pages[0] if pages else None,
            "refetch_last": pages[-1] if pages else None}


def grade(census, body, rejected, subj, mapp, mpages, expected):
    e, verdict = expected, ccdi_pages.verdict
    diff = sorted(n for n in set(census) | set(body)
                  if census.get(n, "absent") != body.get(n, "absent"))
    flags = ccdi_pages.flag_rows(subj)
    fs, fm = first_empty(body), first_empty(mpages)
    return {
        "R1": verdict(not rejected and not diff and len(body) == e["pages"],
                      pages=len(body), rejected=rejected, differing_pages=diff),
        "R2": verdict(subj["required_last_page"] == e["last"] and subj["refetch_pages"] == []
                      and flags == e["subject_flags"],
                      required_last_page=subj["required_last_page"],
                      refetch_pages=subj["refetch_pages"], flags=flags),
        "R3": verdict(mapp["required_last_page"] == e["last"] and mapp["refetch_pages"] == [],
                      required_last_page=mapp["required_last_page"],
                      refetch_pages=mapp["refetch_pages"]),
        "R4": verdict(fs == e["last"] + 1 and fm == e["last"] + 1,
                      subject_first_empty=fs, mapping_first_empty=fm)}


def run(raw, expected=SNAPSHOT2, cut=CUT):
    per_page, census, domains, names = ccdi_pages.subject_walk(raw)
    body, rejected, kinds = body_walk(raw)
    mpages, unmapped = ccdi_pages.mapping_walk(raw, domains, names)
    totals = ccdi_pages.summary_totals(raw)
    subj = paging.audit(body, per_page, totals)
    mapp = paging.audit(mpages, per_page, totals)
    return {"label": LABEL, "tool": subj["tool"],
            "input": {"per_page": per_page, "subject_pages": len(census),
                      "mapping_pages": len(mpages), "unmapped_mapping_entries": unmapped,
                      "summary_totals": totals},
            "grades": grade(census, body, rejected, subj, mapp, mpages, expected),
            "subject_error_kinds": kinds,
            "replay_cut": replay(mpages, per_page, totals, cut),
            "subject": subj, "mapping": mapp}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="kept second snapshot (raw/ of ccdi-diag-v1)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if os.path.exists(os.path.join(args.raw, "subject", "chosen.json")):
        result = run(args.raw)
        result["input"]["snapshot"] = "kept second snapshot"
    else:
        why = "no kept second snapshot on this machine"
        result = {"label": LABEL, "input": {"snapshot": None},
                  "grades": {r: {"grade": "not graded", "why": why}
                             for r in ("R1", "R2", "R3", "R4")}}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "check031.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot": result["input"]["snapshot"], "grades": result["grades"]},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
