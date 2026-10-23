"""Paging audit of a CCDI Data Federation snapshot (PRE-REGISTERED: predictions Q1-Q6 are in
README.md in this folder, published at evidence-pack tag v0.7.0 before this job ran).

Reads a raw/ snapshot saved by the census's fetch_ccdi.py (tag v0.5.5) and turns every saved
page of /subject and /subject-mapping into per-source entry counts for LinkCheck's paging
audit (linkcheck/paging.py, tag v0.7.0):
  - /subject: a source's entries on a page are the records in its `data` list. A source
    whose `data` is not a list has an error on that page. A response that is not a JSON
    list failed as a whole.
  - /subject-mapping: each Participant Index entry is given to the source of the served
    subject it names, matched as the census matches it (domain name, case-insensitively,
    as a source or namespace name, plus the participant id). An entry whose subject was not
    served is given by its domain name alone; one whose domain name matches no source is
    counted as unmapped. A response that is not a JSON object failed as a whole.
  - totals: each source's counts.total in /subject/summary.
Then it audits both endpoints and grades Q1-Q6.

Aggregates only: counts, page numbers and source names, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import glob
import gzip
import json
import os
import re

from linkcheck import paging

PAGE = re.compile(r"^page-(\d+)\.json\.gz$")
# Second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC), from the census re-run
# (ccdi/diagnostics-v1) and diagnostics stages 2-3 (ccdi/diagnostics-v2, -v3).
SNAPSHOT2 = {
    "per_page": 100, "pages": 599,
    "totals": {"CCDI-DCC": 59795, "KidsFirst": 38440, "PCDC": 24432, "StJude": 14681,
               "Treehouse": 12723, "ccdi-ecDNA": 3205, "ccdi-iusccc-pst": 504},
    "subject_past_end": {"CCDI-DCC": 0, "KidsFirst": 0, "PCDC": 354, "StJude": 452,
                         "Treehouse": 471, "ccdi-ecDNA": 566, "ccdi-iusccc-pst": 0},
    "subject_flags": [[12, "PCDC", "error", None, 100], [35, "PCDC", "error", None, 100]],
    "mapping_flags": [[35, "PCDC", "short", 0, 100]],
    "lost": {"subject": {"PCDC": 200}, "mapping": {"PCDC": 100}},
    "unmapped": 0}
LABEL = ("PRE-REGISTERED: predictions Q1-Q6 in README.md, published at evidence-pack tag "
         "v0.7.0 before this job ran")


def load(path):
    with gzip.open(path, "rb") as fh:
        body = fh.read()
    try:
        return json.loads(body)
    except ValueError:
        return None


def numbered(folder):
    """{page number: path} for the page-NNNN.json.gz files in a folder."""
    out = {}
    for path in glob.glob(os.path.join(folder, "page-*.json.gz")):
        m = PAGE.match(os.path.basename(path))
        if m:
            out[int(m.group(1))] = path
    return out


def subject_walk(raw):
    """(per_page, pages, domains, names): per-source record counts on every /subject page,
    and the lookups the mapping side needs, built in the census's order (first copy kept)."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = numbered(os.path.join(raw, "subject"))
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    pages, domains, names = {}, {}, {}
    for n, path in sorted(files.items()):
        parsed = load(path)
        if not isinstance(parsed, list):
            pages[n] = None
            continue
        counts = {}
        for item in parsed:
            if not isinstance(item, dict) or "source" not in item:
                continue
            src = str(item["source"])
            data = item.get("data")
            if not isinstance(data, list):
                counts[src] = None
                continue
            counts[src] = len(data)
            domains.setdefault(src.lower(), src)
            for rec in data:
                ident = (rec.get("id") or {}) if isinstance(rec, dict) else {}
                ns = str((ident.get("namespace") or {}).get("name")).lower()
                name = str(ident.get("name"))
                domains.setdefault(ns, src)
                names.setdefault((src.lower(), name), src)
                names.setdefault((ns, name), src)
        pages[n] = counts
    return chosen["per_page"], pages, domains, names


def mapping_walk(raw, domains, names):
    """(pages, unmapped): per-source Participant Index entries on every /subject-mapping page."""
    pages, unmapped = {}, 0
    for n, path in sorted(numbered(os.path.join(raw, "mapping")).items()):
        parsed = load(path)
        if not isinstance(parsed, dict):
            pages[n] = None
            continue
        counts = {}
        for e in parsed.get("participant_ids") or []:
            if not isinstance(e, dict):
                continue
            dom = str(e.get("domain_name")).lower()
            src = names.get((dom, str(e.get("participant_id")))) or domains.get(dom)
            if src is None:
                unmapped += 1
                continue
            counts[src] = counts.get(src, 0) + 1
        pages[n] = counts
    return pages, unmapped


def summary_totals(raw):
    path = os.path.join(raw, "fed", "subject-summary.json.gz")
    summary = load(path) if os.path.exists(path) else None
    out = {}
    for item in summary if isinstance(summary, list) else []:
        if isinstance(item, dict) and item.get("source") is not None:
            total = (item.get("counts") or {}).get("total")
            if paging.is_count(total):
                out[str(item["source"])] = total
    return out


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def flag_rows(report):
    return [[f["page"], f["source"], f["kind"], f["entries"], f["expected"]]
            for f in report["flags"]]


def shape(report):
    return {"per_page": report["per_page"], "pages": report["pages"],
            "last_page": report["last_page"], "missing_pages": report["missing_pages"],
            "whole_page_failures": report["whole_page_failures"], "flags": flag_rows(report)}


def by_source(report, lost_kind):
    return {s: {"total": r["total"], "served": r["served"],
                "errors_past_end": r["errors_past_end"], "not_judged": r["not_judged"],
                "unexplained": r["unexplained"], "lost": r["lost"][lost_kind]}
            for s, r in report["sources"].items()}


def wanted(e, endpoint, past_end):
    lost = e["lost"][endpoint]
    return {s: {"total": t, "served": t - lost.get(s, 0), "errors_past_end": past_end.get(s, 0),
                "not_judged": 0, "unexplained": 0, "lost": lost.get(s, 0)}
            for s, t in e["totals"].items()}


def grade(subj, mapp, unmapped, expected=None):
    """Q5-Q6 hold for any snapshot. Q1-Q4 use the second snapshot's numbers and are graded
    only when `expected` is given."""
    out = {}
    on_subject = {(f["page"], f["source"]) for f in subj["flags"]}
    alone = [[f["page"], f["source"]] for f in mapp["flags"]
             if (f["page"], f["source"]) not in on_subject]
    out["Q5"] = verdict(not alone, mapping_flags=len(mapp["flags"]),
                        not_flagged_on_subject=alone, vacuous=not mapp["flags"])
    left = {name: {s: r["unexplained"] for s, r in sorted(rep["sources"].items())
                   if r["total"] is not None and r["unexplained"] != 0}
            for name, rep in (("subject", subj), ("mapping", mapp))}
    out["Q6"] = verdict(not left["subject"] and not left["mapping"], unexplained_not_zero=left)
    if expected is None:
        for q in ("Q1", "Q2", "Q3", "Q4"):
            out[q] = {"grade": "not graded",
                      "why": "fresh snapshot: the predicted numbers belong to snapshot 2"}
        return dict(sorted(out.items()))
    e = expected
    frame = {"per_page": e["per_page"], "pages": e["pages"], "last_page": e["pages"],
             "missing_pages": [], "whole_page_failures": []}
    got = shape(subj)
    out["Q1"] = verdict(got == dict(frame, flags=e["subject_flags"]), **got)
    got = by_source(subj, "error_pages")
    out["Q2"] = verdict(got == wanted(e, "subject", e["subject_past_end"]), sources=got)
    got = shape(mapp)
    out["Q3"] = verdict(got == dict(frame, flags=e["mapping_flags"]), **got)
    got = by_source(mapp, "short_pages")
    out["Q4"] = verdict(got == wanted(e, "mapping", {}) and unmapped == e["unmapped"],
                        sources=got, unmapped=unmapped)
    return dict(sorted(out.items()))


def run(raw, expected=None):
    per_page, spages, domains, names = subject_walk(raw)
    mpages, unmapped = mapping_walk(raw, domains, names)
    totals = summary_totals(raw)
    subj = paging.audit(spages, per_page, totals)
    mapp = paging.audit(mpages, per_page, totals)
    return {"label": LABEL, "tool": subj["tool"],
            "input": {"per_page": per_page, "subject_pages": len(spages),
                      "mapping_pages": len(mpages), "unmapped_mapping_entries": unmapped,
                      "summary_totals": totals},
            "grades": grade(subj, mapp, unmapped, expected),
            "subject": subj, "mapping": mapp}


def pick(kept, fallback):
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        return kept, "kept second snapshot"
    if fallback and os.path.exists(os.path.join(fallback, "subject", "chosen.json")):
        return fallback, "fresh snapshot taken by this job"
    raise SystemExit("no snapshot under " + kept + (" or " + fallback if fallback else ""))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="kept snapshot (raw/ folder of ccdi-diag-v1)")
    ap.add_argument("--fallback-raw", help="fresh snapshot, used only if --raw has none")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw, which = pick(args.raw, args.fallback_raw)
    result = run(raw, SNAPSHOT2 if raw == args.raw else None)
    result["input"]["snapshot"] = which
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "paging-audit.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot": which, "grades": result["grades"]}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
