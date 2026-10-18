#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""validate_v11: live check of the v1.1 PubMed lookup on the 26 links that commentin-targets v1
(commentin_targets_v1_targets.jsonl, run 2026-10-18) labelled not_in_pubmed.

Expected, written before the run (findings/lookup-v11-2026-10-18.md): the 20 JAMA Otolaryngol
links (18 DOIs, all from one esearch batch that came back empty without an error) resolve to PMIDs;
the 6 others are named absent by PubMed's esearch (flag target_not_in_pubmed); 0 are target_unread.

Usage: python validate_v11.py --out-dir /out
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commentin_check as cc  # noqa: E402

# (source PMID, target DOI), in the order of commentin_targets_v1_targets.jsonl
ROWS = [
    ("29181510", "10.1001/jamaneurol.2017.4634"), ("29255902", "10.1001/jamainternmed.2018.0098"),
    ("29799927", "10.1001/jamasurg.2018.2792"), ("29926083", "10.1001/jamacardio.2018.2412"),
    ("29987336", "10.1001/jamapediatrics.2018.3179"), ("31393537", "10.1001/jamaoto.2019.3430"),
    ("31393537", "10.1001/jamaoto.2019.3432"), ("31536099", "10.1001/jamaoto.2019.2499"),
    ("31580395", "10.1001/jamaoto.2019.2778"), ("31600390", "10.1001/jamaoto.2019.2823"),
    ("31600390", "10.1001/jamaoto.2019.2855"), ("31621810", "10.1001/jamaoto.2019.3078"),
    ("31621812", "10.1001/jamaoto.2019.3021"), ("31774492", "10.1001/jamaoto.2019.3613"),
    ("31855260", "10.1001/jamaoto.2019.3950"), ("31895461", "10.1001/jamaoto.2019.3731"),
    ("32215610", "10.1001/jamaoto.2020.0274"), ("32320008", "10.1001/jamaoto.2020.0832"),
    ("32324231", "10.1001/jamaoto.2020.0415"), ("32352482", "10.1001/jamaoto.2020.0524"),
    ("32352483", "10.1001/jamaoto.2020.0559"), ("32407461", "10.1001/jamaoto.2020.0678"),
    ("32857106", "10.1001/jamaoto.2020.0998"), ("32857113", "10.1001/jamaoto.2020.0998"),
    ("32857114", "10.1001/jamaoto.2020.0998"), ("38900427", "10.1001/jamanetworkopen.2024.15614"),
]


def outcome(link):
    if link is None:
        return "link_gone"
    if link.get("tgt_found"):
        return "found"
    for f in ("target_not_in_pubmed", "target_unread"):
        if f in link.get("flags") or []:
            return f
    return "other"


def summarise(rows):
    oto = [r for r in rows if r["tgt_doi"].startswith("10.1001/jamaoto.")]
    rest = [r for r in rows if not r["tgt_doi"].startswith("10.1001/jamaoto.")]
    c = collections.Counter(r["outcome"] for r in rows)
    expected = {"oto_found": sum(1 for r in oto if r["outcome"] == "found") == len(oto),
                "rest_absent": sum(1 for r in rest if r["outcome"] == "target_not_in_pubmed") == len(rest),
                "no_unread": c.get("target_unread", 0) == 0}
    return {"links": len(rows), "oto_links": len(oto), "other_links": len(rest),
            "outcomes": dict(sorted(c.items())),
            "oto_outcomes": dict(sorted(collections.Counter(r["outcome"] for r in oto).items())),
            "other_outcomes": dict(sorted(collections.Counter(r["outcome"] for r in rest).items())),
            "expected": expected, "all_as_expected": all(expected.values())}


def run(check=None):
    check = check or cc.check
    sources = sorted({s for s, _ in ROWS}, key=int)
    records, errors = check(sources)
    live = {}
    for rec in records:
        for link in rec.get("links") or []:
            if link.get("tgt_doi"):
                live.setdefault((str(rec.get("pmid")), link["tgt_doi"]), link)
    rows = []
    for s, d in ROWS:
        link = live.get((s, d))
        rows.append({"src_pmid": s, "tgt_doi": d, "outcome": outcome(link),
                     "tgt_pmid": (link or {}).get("tgt_pmid"), "flags": (link or {}).get("flags"),
                     "tgt_title": (link or {}).get("tgt_title"), "tgt_date": (link or {}).get("tgt_date"),
                     "tgt_pubtypes": (link or {}).get("tgt_pubtypes")})
    summary = summarise(rows)
    summary.update({"sources": len(sources), "sources_found": sum(1 for r in records if r.get("found")),
                    "errors": errors, "n_errors": len(errors)})
    return summary, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    summary, rows = run()
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    with open(os.path.join(args.out_dir, "links.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
