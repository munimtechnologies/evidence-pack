#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""dash_dois: do publisher-asserted reference DOIs with Unicode dashes fail only because of the dash?

Follow-up to phantom-refs-v1. In 11 of its 232 audited meta-analyses, publisher-asserted reference
DOIs came back "not found" in Crossref and at doi.org, and nearly all of them carry U+2010 (or
another non-ASCII dash) where the DOI has an ASCII hyphen. For each of those meta-analyses this
re-reads the Crossref reference list and, for every publisher-asserted DOI, records whether the raw
DOI resolves and whether the dash-normalised DOI resolves. Standard library only.

  python dash_dois.py --out /out
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "mv2@munimtech.com"
UA = "mv2-munim-dash-dois/1.0 (mailto:%s)" % MAILTO
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
CROSSREF = "https://api.crossref.org/works/"
HANDLES = "https://doi.org/api/handles/"
# The meta-analyses in phantom-refs-v1 flags.jsonl with not-found, no-text references.
PMIDS = ["42811387", "42287032", "41645402", "41641734", "41891174", "42332835",
         "41804840", "42030436", "42509016", "41656984", "42572491"]
# hyphen, non-breaking hyphen, figure dash, en dash, em dash, minus sign, soft hyphen
DASHES = "‐‑‒–—−­"
NORMALISE = {ord(c): "-" for c in DASHES[:-1]}
NORMALISE[ord("­")] = None


def get(url, timeout=60, tries=4):
    """(status, body). 400/404 come back at once; other errors back off and retry."""
    last = ""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as err:
            if err.code in (400, 404):
                return err.code, b""
            last = "HTTP %d" % err.code
        except Exception as err:  # network hiccups: back off and retry
            last = repr(err)
        time.sleep(5 * (attempt + 1))
    return None, last.encode()


def has_dash(doi):
    return any(c in DASHES for c in doi or "")


def normalise(doi):
    return (doi or "").translate(NORMALISE)


class Lookup:
    """Crossref, then doi.org; cached by lower-case DOI."""

    def __init__(self, fetch=get):
        self.fetch, self.cache, self.calls = fetch, {}, 0

    def resolve(self, doi):
        """'crossref' | 'other-ra' | 'not-found' | 'error'."""
        key = doi.lower()
        if key not in self.cache:
            self.calls += 1
            time.sleep(0.1 if self.fetch is get else 0)
            status, _ = self.fetch(CROSSREF + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
            if status == 200:
                self.cache[key] = "crossref"
            elif status in (400, 404):
                status, _ = self.fetch(HANDLES + urllib.parse.quote(doi, safe="/"))
                self.cache[key] = {200: "other-ra", 404: "not-found", 400: "not-found"}.get(status, "error")
            else:
                self.cache[key] = "error"
        return self.cache[key]


def classify(raw, look):
    """One publisher-asserted DOI -> {'dash', 'raw', 'normalised'}; 'normalised' is '' without a dash."""
    rec = {"doi": raw, "dash": has_dash(raw), "raw": look.resolve(raw), "normalised": ""}
    if rec["dash"]:
        rec["normalised"] = look.resolve(normalise(raw))
    return rec


def tally(recs):
    t = {"publisher_dois": len(recs), "dash": 0, "raw_resolves": 0, "dash_raw_fails": 0,
         "dash_fixed": 0, "dash_still_fails": 0, "plain_fails": 0, "errors": 0}
    for r in recs:
        if "error" in (r["raw"], r["normalised"]):
            t["errors"] += 1
            continue
        ok = r["raw"] in ("crossref", "other-ra")
        t["raw_resolves"] += ok
        if r["dash"]:
            t["dash"] += 1
            if not ok:
                t["dash_raw_fails"] += 1
                if r["normalised"] in ("crossref", "other-ra"):
                    t["dash_fixed"] += 1
                else:
                    t["dash_still_fails"] += 1
        elif not ok:
            t["plain_fails"] += 1
    return t


def pubmed_dois(pmids, fetch=get):
    q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "json",
                                "tool": "mv2-munim-dash-dois", "email": MAILTO})
    status, body = fetch(EUTILS + "?" + q, timeout=120)
    if status != 200:
        raise RuntimeError("esummary failed: %s" % status)
    res = json.loads(body).get("result") or {}
    out = {}
    for p in pmids:
        ids = (res.get(p) or {}).get("articleids") or []
        out[p] = next((a.get("value", "").strip() for a in ids if a.get("idtype") == "doi"), "")
    return out


def audit(pmid, doi, look, fetch=get):
    row = {"pmid": pmid, "doi": doi}
    status, body = fetch(CROSSREF + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
    if status != 200:
        row["status"] = "not-in-crossref"
        return row, []
    msg = json.loads(body).get("message") or {}
    row.update(status="audited", publisher=msg.get("publisher", ""), member=msg.get("member", ""),
               container=" ".join(msg.get("container-title") or [])[:120])
    recs = [classify(r["DOI"].strip(), look) for r in msg.get("reference") or []
            if r.get("DOI") and r.get("doi-asserted-by") == "publisher"]
    row["tally"] = tally(recs)
    return row, [dict(r, pmid=pmid) for r in recs]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    look = Lookup()
    dois = pubmed_dois(PMIDS)
    rows, recs = [], []
    for p in PMIDS:
        if not dois[p]:
            rows.append({"pmid": p, "status": "no-doi"})
            continue
        row, rr = audit(p, dois[p], look)
        rows.append(row)
        recs.extend(rr)
        print(json.dumps(row), flush=True)
    total = tally(recs)
    with open(os.path.join(args.out, "rows.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "total": total, "lookups": look.calls}, f, indent=1)
    with open(os.path.join(args.out, "dois.jsonl"), "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    lines = ["# Dash-normalised reference DOIs (follow-up to phantom-refs-v1)", "",
             "- Meta-analyses: %d; audited: %d" % (len(rows), sum(r.get("status") == "audited" for r in rows)),
             "- Totals: %s" % json.dumps(total, sort_keys=True), "", "## Per meta-analysis", ""]
    for r in rows:
        lines.append("- PMID %s (%s; %s): %s" % (r["pmid"], r.get("doi", ""), r.get("publisher", r.get("status")),
                                                  json.dumps(r.get("tally", {}), sort_keys=True)))
    still = [r for r in recs if r["dash"] and r["raw"] == "not-found" and r["normalised"] != "crossref"
             and r["normalised"] != "other-ra"]
    plain = [r for r in recs if not r["dash"] and r["raw"] == "not-found"]
    lines += ["", "## Dash DOIs that still fail after normalising (%d)" % len(still), ""]
    lines += ["- %s (PMID %s)" % (normalise(r["doi"]), r["pmid"]) for r in still]
    lines += ["", "## Plain-ASCII DOIs that fail (%d)" % len(plain), ""]
    lines += ["- %s (PMID %s)" % (r["doi"], r["pmid"]) for r in plain]
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
