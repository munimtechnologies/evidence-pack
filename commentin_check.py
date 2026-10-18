#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""commentin_check: list the PubMed "Comment in" links of each PMID or DOI and flag the ones to
read before citing them as commentary on the record.

  python commentin_check.py 40274279 10.1056/NEJMc2401126
  python commentin_check.py --file references.txt --out comment_links.jsonl
  python commentin_check.py --file references.txt --fail-on-flag      # exit 2 if any link is flagged

A "Comment in" link should point to a later item that comments on the record, and that item should
name the record back in its own "Comment on" list. MV2's census of 13 JAMA Network and 4 control
journals, 2016-2026 (findings/pubmed-commentin-census-v1-results-2026-10-17.md), found that 12.1%
of JAMA Network "Comment in" entries are a bare "doi: 10.1001/..." with no PMID (0.37% at the
controls), that none of 300 sampled bare-DOI targets names the record back, and that 38% of them
are older than the record.

Facts per link (PubMed esummary only; read only, no keys, standard library only):
  cls          pmid | bare_doi | other_nopmid (the classifier of pubmed_commentin.py)
  tgt_pmid     the target's PMID, from the link or by looking up the DOI in it
  earlier      the target's PubMed sort date is before the record's (None if either is unknown)
  reciprocal   the target lists the record under "Comment on" (None if the target was not read)
  tgt_comment_on  the PMIDs the target itself lists under "Comment on"
Link flags: bare_doi, other_nopmid, no_target_id, target_not_in_pubmed, target_unread (a lookup
failed), earlier, not_reciprocal, comment_on_other (the target is a comment on other records but
does not name this one; e.g. 28208186 links 28208180, a comment on 28208174). A flag is a reason to open the target and read it, not a verdict:
PubMed also links real comments to newer records (NEJM letter 38507769 lists an older Nat Rev
Nephrol comment, 38012264, that names it back), and a real comment may not link back.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import integrity_check as ic  # noqa: E402
from pubmed_commentin import classify, earlier, ref_doi  # noqa: E402

FLAGS = ("bare_doi", "other_nopmid", "no_target_id", "target_not_in_pubmed", "target_unread",
         "earlier", "not_reciprocal", "comment_on_other")
SORT_DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")


def sort_date(rec):
    """(y, m, d) from PubMed's sortpubdate "2025/05/27 00:00", else (y,) from pubdate, else ()."""
    m = SORT_DATE.match(str((rec or {}).get("sortpubdate") or ""))
    if m:
        return tuple(int(x) for x in m.groups())
    m = re.match(r"\d{4}", str((rec or {}).get("pubdate") or ""))
    return (int(m.group(0)),) if m else ()


def iso(d):
    return "-".join(("%02d" % x) if i else str(x) for i, x in enumerate(d)) or None


def comment_links(rec):
    """The "Comment in" entries of one esummary record, in PubMed's order."""
    out = []
    for ref in rec.get("references") or []:
        if str(ref.get("reftype") or "").strip().lower() != "comment in":
            continue
        source = " ".join(str(ref.get("refsource") or "").split())
        pmid = str(ref.get("pmid") or "").strip()
        out.append({"refsource": source, "cls": classify(source, pmid), "tgt_pmid": pmid or None,
                    "tgt_doi": ic.dh.clean_doi(ref_doi(source)) or None})
    return out


def comment_on_pmids(rec):
    return {str(ref.get("pmid") or "").strip() for ref in (rec or {}).get("references") or []
            if str(ref.get("reftype") or "").strip().lower() == "comment on"}


def describe(entry, rec, by_pmid, doi_to_pmid, lookup_failed, today=None):
    """One output record: the source's "Comment in" links with their targets read and flagged."""
    out = {"input": entry["input"], "pmid": entry.get("pmid"), "doi": entry.get("doi"), "title": "",
           "date": None, "found": rec is not None, "links": [], "counts": {},
           "checked_at": today or datetime.date.today().isoformat()}
    links = []
    if rec is not None:
        src_date = sort_date(rec)
        out["title"] = " ".join(str(rec.get("title") or "").split())
        out["date"] = iso(src_date)
        if not out["doi"]:
            for a in rec.get("articleids") or []:
                if a.get("idtype") == "doi" and a.get("value"):
                    out["doi"] = ic.dh.clean_doi(a["value"])
                    break
        for link in comment_links(rec):
            tp = link["tgt_pmid"] or (doi_to_pmid.get(link["tgt_doi"]) if link["tgt_doi"] else None)
            t = by_pmid.get(tp) if tp else None
            t_date = sort_date(t) if t is not None else ()
            link.update({"tgt_pmid": tp, "tgt_found": t is not None,
                         "tgt_title": " ".join(str((t or {}).get("title") or "").split()),
                         "tgt_date": iso(t_date),
                         "tgt_pubtypes": [str(p) for p in (t or {}).get("pubtype") or []],
                         "tgt_comment_on": sorted(p for p in comment_on_pmids(t) if p) if t is not None else [],
                         "earlier": earlier(t_date, src_date),
                         "reciprocal": (str(out["pmid"]) in comment_on_pmids(t)) if t is not None else None})
            flags = [link["cls"]] if link["cls"] != "pmid" else []
            if t is None:
                if not tp and not link["tgt_doi"]:
                    flags.append("no_target_id")
                else:
                    flags.append("target_unread" if lookup_failed else "target_not_in_pubmed")
            if link["earlier"]:
                flags.append("earlier")
            if link["reciprocal"] is False:
                flags.append("not_reciprocal")
                if link["tgt_comment_on"]:
                    flags.append("comment_on_other")
            link["flags"] = flags
            links.append(link)
    out["links"] = links
    counts = {"links": len(links), "pmid": sum(1 for l in links if l["cls"] == "pmid")}
    for f in FLAGS:
        counts[f] = sum(1 for l in links if f in l["flags"])
    counts["to_read"] = sum(1 for l in links if l["flags"])
    out["counts"] = counts
    return out


def check(tokens, get=None, pause=None, today=None):
    """(records, errors) for a list of PMID/DOI tokens. Duplicates are dropped; order is kept.
    Two rounds of PubMed calls: the records themselves, then the targets of their links."""
    entries, seen = [], set()
    for t in tokens:
        e = ic.parse_token(t)
        key = (e["pmid"], e["doi"])
        if key != (None, None) and key in seen:
            continue
        seen.add(key)
        entries.append(e)
    src = ic.pubmed_lookup([e["pmid"] for e in entries if e["pmid"]],
                           [e["doi"] for e in entries if e["doi"]], get, pause)
    for e in entries:
        if e["doi"] and not e["pmid"]:
            e["pmid"] = src["doi_to_pmid"].get(e["doi"])
    tpmids, tdois = set(), set()
    for e in entries:
        for link in comment_links(src["by_pmid"].get(e["pmid"]) or {}):
            if link["tgt_pmid"]:
                if link["tgt_pmid"] not in src["by_pmid"]:
                    tpmids.add(link["tgt_pmid"])
            elif link["tgt_doi"] and link["tgt_doi"] not in src["doi_to_pmid"]:
                tdois.add(link["tgt_doi"])
    tgt = ic.pubmed_lookup(sorted(tpmids, key=int), sorted(tdois), get, pause)
    by_pmid, doi_to_pmid = dict(src["by_pmid"]), dict(src["doi_to_pmid"])
    by_pmid.update(tgt["by_pmid"])
    doi_to_pmid.update(tgt["doi_to_pmid"])
    errors = src["errors"] + tgt["errors"]
    records = [describe(e, src["by_pmid"].get(e["pmid"]) if e["pmid"] else None, by_pmid, doi_to_pmid,
                        bool(errors), today) for e in entries]
    return records, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", help="PMIDs and DOIs")
    ap.add_argument("--file", help="text file: one PMID or DOI per line, or free text with DOIs and 'PMID: n'")
    ap.add_argument("--out", help="write JSON lines here instead of stdout")
    ap.add_argument("--fail-on-flag", action="store_true", help="exit 2 if any link is flagged")
    args = ap.parse_args(argv)
    tokens = list(args.ids) + (ic.read_file(args.file) if args.file else [])
    if not tokens:
        ap.error("give PMIDs/DOIs or --file")
    records, errors = check(tokens)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    total = {k: sum(r["counts"][k] for r in records) for k in ("links", "pmid", "bare_doi",
                                                               "other_nopmid", "to_read")}
    print("%d records (%d found in PubMed): %d Comment in links (%d pmid, %d bare_doi, %d other_nopmid); "
          "%d flagged to read; %d lookup errors" % (
              len(records), sum(1 for r in records if r["found"]), total["links"], total["pmid"],
              total["bare_doi"], total["other_nopmid"], total["to_read"], len(errors)), file=sys.stderr)
    for e in errors:
        print("error: " + e, file=sys.stderr)
    if args.fail_on_flag and total["to_read"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
