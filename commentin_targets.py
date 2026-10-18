#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""commentin_targets: what are the same-issue targets of JAMA Network's bare-DOI "Comment in" links?

Pre-registration: findings/commentin-targets-prereg-v1-2026-10-18.md.

Census v1 (findings/pubmed-commentin-census-v1-results-2026-10-17.md) found two kinds of bare-DOI
"Comment in" link at JAMA Network: earlier related articles (38%), which cannot be comments, and
targets dated in the same month as the record, which "may well comment on the record". This script
reads every link of the second kind in live PubMed and sorts its target into one class:
  reciprocal        the target lists the record under "Comment on"
  comment_on_other  the target lists other records under "Comment on", not this one
  comment_typed     the target is typed Comment or Editorial but lists nothing under "Comment on"
  research_typed    the target carries a study-design publication type (trial, review, ...)
  untyped           the target was read and is none of the above
  not_in_pubmed     the target's DOI is not in PubMed
  unread            a PubMed lookup failed
  link_gone         the record no longer carries this link
Population: census rows with cls bare_doi, a target DOI and "earlier": false (target not dated
before the record in Crossref), from pubmed_commentin_v1_nopmid_links.jsonl on main.

Standard library only. Usage: python commentin_targets.py --links pubmed_commentin_v1_nopmid_links.jsonl --out-dir /out
"""
import argparse
import collections
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commentin_check as cc  # noqa: E402

PREREG = "findings/commentin-targets-prereg-v1-2026-10-18.md"
CLASSES = ("reciprocal", "comment_on_other", "comment_typed", "research_typed", "untyped",
           "not_in_pubmed", "unread", "link_gone")
READ = CLASSES[:5]
COMMENT_TYPES = {"Comment", "Editorial"}
DESIGN_TYPES = {"Review", "Systematic Review", "Meta-Analysis", "Observational Study", "Multicenter Study",
                "Comparative Study", "Validation Study", "Evaluation Study", "Case Reports", "Twin Study"}
VOID_SHARE = 0.02
MIN_N = 100


def population(rows):
    """Census rows in scope: bare-DOI links whose target is not dated before the record."""
    return [r for r in rows if r.get("cls") == "bare_doi" and r.get("earlier") is False and r.get("tgt_doi")]


def era(year):
    year = int(year or 0)
    return "2016-2023" if year <= 2023 else ("2024" if year == 2024 else "2025-2026")


def classify_target(link):
    """Class of one census link, given the live link commentin_check found for it (None if none)."""
    if link is None:
        return "link_gone"
    if not link.get("tgt_found"):
        return "unread" if "target_unread" in (link.get("flags") or []) else "not_in_pubmed"
    if link.get("reciprocal"):
        return "reciprocal"
    if link.get("tgt_comment_on"):
        return "comment_on_other"
    types = set(link.get("tgt_pubtypes") or [])
    if types & COMMENT_TYPES:
        return "comment_typed"
    if types & DESIGN_TYPES or any("Trial" in t for t in types):
        return "research_typed"
    return "untyped"


def match(rows, records):
    """[(census row, live link or None)]: a census link matches the live link of the same record
    with the same target DOI."""
    live = {}
    for rec in records:
        for link in rec.get("links") or []:
            if link.get("tgt_doi"):
                live.setdefault((str(rec.get("pmid")), link["tgt_doi"]), link)
    return [(r, live.get((str(r["src_pmid"]), cc.ic.dh.clean_doi(r["tgt_doi"])))) for r in rows]


def tally(pairs):
    c = collections.Counter(classify_target(link) for _, link in pairs)
    return {k: c.get(k, 0) for k in CLASSES}


def share_test(n, k, op, threshold):
    if n < MIN_N:
        return "untestable"
    s = k / n
    return "supported" if (s <= threshold if op == "<=" else s >= threshold) else "not supported"


def verdicts(t):
    """Pre-registered: shares of read targets (the first five classes) at JAMA Network."""
    n = sum(t[k] for k in READ)
    return {"H1": share_test(n, t["reciprocal"], "<=", 0.05),
            "H2": share_test(n, t["comment_on_other"], ">=", 0.10),
            "H3": share_test(n, t["research_typed"], ">=", 0.10)}


def run(rows, check=None):
    """(results, per-link rows) for census rows; check is commentin_check.check."""
    check = check or cc.check
    groups = {}
    for r in population(rows):
        groups.setdefault(r["group"], []).append(r)
    sources = sorted({str(r["src_pmid"]) for rs in groups.values() for r in rs}, key=int)
    records, errors = check(sources) if sources else ([], [])
    pairs = {g: match(rs, records) for g, rs in groups.items()}
    empty = {k: 0 for k in CLASSES}
    jn = pairs.get("jama_network", [])
    by_era, by_journal = {}, {}
    for r, link in jn:
        by_era.setdefault(era(r.get("year")), []).append((r, link))
        by_journal.setdefault(r.get("ta") or "", []).append((r, link))
    by_group = {g: tally(p) for g, p in sorted(pairs.items())}
    jt = by_group.get("jama_network", empty)
    results = {
        "prereg": PREREG, "population": {g: len(rs) for g, rs in sorted(groups.items())},
        "sources": len(sources), "sources_found": sum(1 for rec in records if rec.get("found")),
        "by_group": by_group, "by_era": {k: tally(v) for k, v in sorted(by_era.items())},
        "by_journal": {k: tally(v) for k, v in sorted(by_journal.items())},
        "void": jt["unread"] > VOID_SHARE * max(len(jn), 1),
        "hypotheses": verdicts(jt), "errors": errors[:200], "n_errors": len(errors),
    }
    out_rows = []
    for g, ps in sorted(pairs.items()):
        for r, link in ps:
            link = link or {}
            out_rows.append({"group": g, "ta": r.get("ta"), "year": r.get("year"), "src_pmid": str(r["src_pmid"]),
                             "tgt_doi": r["tgt_doi"], "class": classify_target(link or None),
                             "tgt_pmid": link.get("tgt_pmid"), "tgt_title": link.get("tgt_title", ""),
                             "tgt_date": link.get("tgt_date"), "tgt_pubtypes": link.get("tgt_pubtypes", []),
                             "tgt_comment_on": link.get("tgt_comment_on", [])})
    return results, out_rows


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--links", default="pubmed_commentin_v1_nopmid_links.jsonl")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()
    results, rows = run(read_jsonl(args.links))
    results["minutes"] = round((time.time() - t0) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    with open(os.path.join(args.out_dir, "targets.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({k: results[k] for k in ("population", "sources", "sources_found", "by_group", "void",
                                               "hypotheses", "n_errors", "minutes")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
