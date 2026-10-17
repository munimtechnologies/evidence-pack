#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""doi_hygiene: flag DOIs and records that open citation counts are known to get wrong.

Built from the evidence-pack findings of 2026-10-16
(findings/open-citation-count-errors-2026-10-17.md):
  1. Unicode dashes. Publisher-deposited reference DOIs with U+2010 in place of "-" do not resolve,
     and a DOI pattern that stops at the dash leaves a bare journal stem (10.1111/j.1365).
  2. DOI stubs. OpenAlex records whose own DOI is such a stem (10.1016/s0140, 10.1136/bmjopen)
     collect every reference truncated the same way. stub_blocklist_v1.csv lists the 74 known ones.
  3. Article number 1. In article-numbered journals a reference written "Sci Rep 9:1-17" can land
     on the volume's article 1 (Krivachy, arXiv:2511.01675). In OpenAlex, an MDPI or Frontiers
     citer up to 2021 whose reference to another paper of the volume has first page "1" can also
     be linked to article 1 (findings/article-number-1-forward-v2-results-2026-10-17.md); the
     "link" command checks one such link against the citer's Crossref deposit.
  4. Journal-title ("paratext") records with many citations, which are mostly misdirected.
These are heuristics: a flag means "check this before counting it", not proof of an error.
Journal swaps of the Bunney kind (findings/citation-sink-bunney-v2-results-2026-10-16.md) need
sink_check_v2.py; nothing in a single DOI or record shows them. Standard library only.

  python doi_hygiene.py check 10.1136/bmjopen "10.1016/S0140-6736(19)30456-5"
  python doi_hygiene.py scan references.txt
  python doi_hygiene.py records openalex_works.jsonl
  python doi_hygiene.py link 10.3390/su8010001 citer_crossref_work.json
"""
import argparse
import csv
import json
import os
import re
import sys

# hyphen, non-breaking hyphen, figure dash, en dash, em dash, horizontal bar, minus sign,
# small hyphen-minus, fullwidth hyphen-minus; the soft hyphen is dropped
DASHES = "‐‑‒–—―−﹣－"
SOFT_HYPHEN = "­"
NORMALISE = {ord(c): "-" for c in DASHES}
NORMALISE[ord(SOFT_HYPHEN)] = None
PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/",
            "doi.org/", "doi:")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
FIND_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")
# Suffixes that only ever begin a DOI: the part before the first "-" or "(" of a journal's DOIs.
STUB_SUFFIX = [
    (re.compile(r"^j\.\d{4}$"), "Blackwell ISSN stem (j.NNNN)"),
    (re.compile(r"^s\d{4}(-\d{3}[\dx])?$"), "Elsevier PII stem (sNNNN or sNNNN-NNNN)"),
    (re.compile(r"^s\d{5}$"), "journal-code stem (sNNNNN)"),
    (re.compile(r"^\d{4}(-\d{3}[\dx])?$"), "ISSN stem (NNNN or NNNN-NNNN)"),
    (re.compile(r"^b?97[89]$"), "ISBN stem (978 or 979)"),
]
ALPHA_SUFFIX = re.compile(r"^[a-z][a-z_]*$")
PARATEXT_MIN = 50
# MDPI: 10.3390/<journal><volume><issue, 2 digits><article, 4 digits>; Frontiers: 10.3389/<journal>.<year>.<article>
MDPI_RX = re.compile(r"^10\.3390/([a-z]+)(\d+)(\d{2})(\d{4})$")
FRONTIERS_RX = re.compile(r"^10\.3389/(f[a-z]+)\.(\d{4})\.(\d{5})$")
LINK_LAST_YEAR = 2021  # forward test v2: 13 of 40 page-1 pairs linked for 2019-2021 citers, 0 of 41 for 2023-2025
HERE = os.path.dirname(os.path.abspath(__file__))
BLOCKLIST = os.path.join(HERE, "stub_blocklist_v1.csv")


def clean_doi(text):
    """Lower-case DOI with dashes mapped to "-", resolver prefixes and trailing punctuation removed."""
    doi = (text or "").translate(NORMALISE).strip().lower()
    for prefix in PREFIXES:
        if doi.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    while doi and doi[-1] in ".,;:":
        doi = doi[:-1]
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1]
    return doi


def find_dois(text):
    """DOIs in free text, as written. The pattern runs to whitespace, so a U+2010 cannot cut one short."""
    return [m.group(0) for m in FIND_RE.finditer(text or "")]


def extract_dois(text):
    """Cleaned DOIs in free text."""
    return [clean_doi(d) for d in find_dois(text)]


def load_blocklist(path=BLOCKLIST):
    """{doi: [rows]} from a blocklist CSV with a doi column; empty if there is no file."""
    if not path or not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("doi"):
                out.setdefault(clean_doi(row["doi"]), []).append(row)
    return out


def blocklist_flag(rows):
    ids = ", ".join(r.get("openalex_id") or "?" for r in rows)
    return {"kind": "blocklist", "why": "known DOI-stub record (%s); drop it from citation counts" % ids}


def check_doi(text, blocklist=None):
    """{"input", "doi", "valid", "flags"}; each flag is {"kind", "why"}."""
    raw = text or ""
    doi = clean_doi(raw)
    if not DOI_RE.match(doi):
        return {"input": raw, "doi": doi, "valid": False,
                "flags": [{"kind": "invalid", "why": "not of the form 10.NNNN/suffix"}]}
    flags = []
    if any(c in raw for c in DASHES + SOFT_HYPHEN):
        flags.append({"kind": "dash", "why": "non-ASCII dash or soft hyphen mapped to '-'; "
                                             "the DOI as written does not resolve"})
    suffix = doi.split("/", 1)[1]
    if doi.endswith(("-", "(", "/")):
        flags.append({"kind": "truncated", "why": "ends at a separator; the DOI was cut short"})
    else:
        for pattern, why in STUB_SUFFIX:
            if pattern.match(suffix):
                flags.append({"kind": "stub", "why": why + "; a journal's DOIs start with it, "
                                                           "no article has it"})
                break
        else:
            if ALPHA_SUFFIX.match(suffix):
                flags.append({"kind": "journal_level", "why": "journal-level DOI or alphabetic stem; "
                                                              "citations to it are mostly misdirected"})
    rows = (blocklist or {}).get(doi)
    if rows:
        flags.append(blocklist_flag(rows))
    return {"input": raw, "doi": doi, "valid": True, "flags": flags}


def article_one_risk(work):
    """True when a Crossref-style work is article (or page) 1 with no page range."""
    page = str(work.get("page") or "").translate(NORMALISE).strip()
    number = str(work.get("article-number") or "").strip()
    return number == "1" or page == "1"


def check_record(work, blocklist=None):
    """Flags for one OpenAlex work (id, doi, type, cited_by_count, biblio)."""
    wid = str(work.get("id") or "").rsplit("/", 1)[-1]
    doi = work.get("doi") or ""
    flags = check_doi(doi, blocklist)["flags"] if doi else []
    if wid and not any(f["kind"] == "blocklist" for f in flags):
        hits = [r for rows in (blocklist or {}).values() for r in rows if r.get("openalex_id") == wid]
        if hits:
            flags.append(blocklist_flag(hits))
    cites = work.get("cited_by_count") or 0
    if work.get("type") == "paratext" and cites >= PARATEXT_MIN:
        flags.append({"kind": "paratext", "why": "journal-title record with %d citations; "
                                                 "most are meant for one of its articles" % cites})
    biblio = work.get("biblio") or {}
    if str(biblio.get("first_page") or "") == "1" and str(biblio.get("last_page") or "") in ("", "1"):
        flags.append({"kind": "article_one", "why": "article 1 with no page range; references written "
                                                    "'vol:1-N' can land here (Krivachy 2025)"})
    return {"id": wid, "doi": clean_doi(doi), "cited_by_count": work.get("cited_by_count"),
            "flags": flags}


def volume_of(doi):
    """(publisher, journal, volume, is article 1) for an MDPI or Frontiers article DOI, else None.
    A Frontiers volume is its year; MDPI article 1 is issue 1, article 1."""
    d = clean_doi(doi)
    x = MDPI_RX.match(d)
    if x:
        return "MDPI", x.group(1), x.group(2).lstrip("0"), x.group(3) == "01" and x.group(4) == "0001"
    x = FRONTIERS_RX.match(d)
    if x:
        return "Frontiers", x.group(1), x.group(2), x.group(3) == "00001"
    return None


def year_of(work):
    for key in ("issued", "published-print", "published-online", "published"):
        parts = ((work.get(key) or {}).get("date-parts") or [[None]])[0]
        if parts and isinstance(parts[0], int):
            return parts[0]
    return None


def article_one_link(article1, citer):
    """Why OpenAlex may link a citing work (a Crossref work with its deposited references) to an
    MDPI or Frontiers article 1.

    verdict "cited": the citer deposits a reference to article 1 itself. "page1_sibling": it does not,
    but deposits a reference to another paper of the same volume with first page "1", the pattern of
    findings/article-number-1-forward-v2-results-2026-10-17.md, so the link is likely an addition on top
    of the correct one. "unexplained": neither. "not_covered": article1 is not an MDPI or Frontiers
    article 1. Only references with DOIs are read."""
    target = volume_of(article1)
    a1 = clean_doi(article1)
    refs = (citer or {}).get("reference") or []
    out = {"article1": a1, "citer": clean_doi((citer or {}).get("DOI")), "year": year_of(citer or {}),
           "verdict": "not_covered", "page1_refs": [], "flags": []}
    if not target or not target[3]:
        return out
    if any(clean_doi(r.get("DOI")) == a1 for r in refs):
        out["verdict"] = "cited"
        return out
    for r in refs:
        v = volume_of(r.get("DOI"))
        if v and v[:3] == target[:3] and str(r.get("first-page") or "").strip() == "1":
            out["page1_refs"].append(clean_doi(r.get("DOI")))
    if not out["page1_refs"]:
        out["verdict"] = "unexplained"
        return out
    out["verdict"] = "page1_sibling"
    why = ("the citer cites %s of the same volume with first page '1', not article 1; OpenAlex links "
           "about a third of citers up to %d that do this to article 1 as well"
           % (", ".join(out["page1_refs"]), LINK_LAST_YEAR))
    if out["year"] is not None and out["year"] > LINK_LAST_YEAR:
        why += " (this citer is from %d; none of 41 such cases from 2023-2025 were linked)" % out["year"]
    out["flags"].append({"kind": "article_one_link", "why": why})
    return out


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--blocklist", default=BLOCKLIST, help="blocklist CSV ('' for none)")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", parents=[common], help="check DOIs").add_argument("dois", nargs="+")
    sub.add_parser("scan", parents=[common], help="find and check DOIs in a text file").add_argument("path")
    sub.add_parser("records", parents=[common], help="check OpenAlex works, one JSON per line").add_argument("path")
    link = sub.add_parser("link", help="check an OpenAlex link from a citing work to an MDPI/Frontiers article 1")
    link.add_argument("article1")
    link.add_argument("path", help="the citing work's Crossref JSON (/works/<doi> response or its message)")
    args = ap.parse_args(argv)
    if args.cmd == "link":
        with open(args.path, encoding="utf-8") as fh:
            work = json.load(fh)
        results = [article_one_link(args.article1, work.get("message", work))]
    else:
        blocklist = load_blocklist(args.blocklist)
        if args.cmd == "check":
            results = [check_doi(d, blocklist) for d in args.dois]
        elif args.cmd == "scan":
            with open(args.path, encoding="utf-8") as fh:
                results = [check_doi(d, blocklist) for d in find_dois(fh.read())]
        else:
            with open(args.path, encoding="utf-8") as fh:
                results = [check_record(json.loads(line), blocklist) for line in fh if line.strip()]
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    flagged = sum(1 for r in results if r["flags"])
    print("%d checked, %d flagged" % (len(results), flagged), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
