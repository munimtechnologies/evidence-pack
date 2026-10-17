#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""integrity_check: one command over PMIDs and DOIs that says, as of today, whether each record is
retracted, under an expression of concern or corrected according to PubMed and to Crossref (which
now carries Retraction Watch notices), and whether its DOI is one that open citation counts get wrong.

  python integrity_check.py 9500320 10.1001/jama.2025.3471 "10.1016/S0140-6736(97)11096-0"
  python integrity_check.py --file references.txt --out checked.jsonl
  python integrity_check.py --file references.txt --fail-on retracted      # exit 2 if any is retracted

Sources (read only, no keys, standard library only):
  PubMed esummary: pubtype "Retracted Publication"; references with reftype "Retraction in",
    "Retracted and republished in" (retracted), "Expression of concern in" (concern), "Erratum in",
    "Update in", "Corrected and republished in" (corrected). "Comment in" links are not notices.
    DOIs are mapped to PMIDs with one esearch per 18 DOIs ("<doi>"[doi] OR ...).
  Crossref /works?filter=doi:...: "updated-by" entries (type retraction, partial_retraction, removal
    or withdrawal -> retracted; expression_of_concern -> concern; any other Crossmark type ->
    corrected), "update-to" (the record is itself a notice) and a title that starts with
    "RETRACTED:" or "WITHDRAWN:". Since 2023 Crossref's "updated-by" includes Retraction Watch
    entries (source "retraction-watch"), so publishers that never deposited a notice are covered.
  doi_hygiene.check_doi: dash, truncated, stub, journal_level and blocklist flags
    (findings/open-citation-count-errors-2026-10-17.md).

Status per record: retracted > concern > corrected > clear; "unknown" when neither source answered;
"invalid" for a token that is neither a PMID nor a DOI. "said_by" names the sources behind the status,
so a retraction known to one source only is visible. NCBI reports temporary failures as HTTP 400, so
HTTP 400 and 5xx are retried; a batch that still fails is listed under errors and its records stay
"unknown" rather than "clear". A "clear" record means neither source had a notice on the day in
"checked_at", not that the paper is sound.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doi_hygiene as dh  # noqa: E402

UA = "evidence-pack integrity_check/0.1 (MV2, Munim, Inc.; mailto:mv2@munimtech.com)"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works"
MAILTO = "mv2@munimtech.com"
PUBMED_BATCH = 18          # esummary ids per call (findings: larger batches fail more often)
CROSSREF_BATCH = 40        # doi: filters per call
NCBI_PAUSE = 0.34          # seconds between NCBI calls (3 per second without a key)
RETRACTED_TYPES = {"retraction", "partial_retraction", "removal", "withdrawal"}
CONCERN_TYPES = {"expression_of_concern"}
PUBMED_RETRACTED = ("retraction in", "retracted and republished in")
PUBMED_CONCERN = ("expression of concern in",)
PUBMED_CORRECTED = ("erratum in", "update in", "corrected and republished in")
PUBMED_NOTICE_OF = ("retraction of", "expression of concern for", "erratum for", "update of",
                    "retracted and republished from", "corrected and republished from")
NOTICE_PUBTYPES = ("Retraction Notice", "Expression of Concern", "Published Erratum")
STATUS_ORDER = ["retracted", "concern", "corrected", "clear", "unknown", "invalid"]
PMID_RE = re.compile(r"\bPMID:?\s*(\d{4,9})\b", re.I)
# separators after the word: colon, hyphen, en dash (U+2013), em dash (U+2014); built with chr() to keep this file ASCII
TITLE_PREFIX = re.compile("^(retracted|withdrawn)(\\s+article)?\\s*[:\\-" + chr(0x2013) + chr(0x2014) + "]", re.I)


def chunks(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def parse_token(tok):
    """{"input", "pmid", "doi", "raw"}: digits are a PMID, anything that cleans to a DOI is a DOI."""
    t = (tok or "").strip()
    if t.lower().startswith("pmid:"):
        t = t[5:].strip()
    if t.isdigit():
        return {"input": tok, "pmid": t, "doi": None, "raw": None}
    doi = dh.clean_doi(t)
    if dh.DOI_RE.match(doi):
        return {"input": tok, "pmid": None, "doi": doi, "raw": t}
    return {"input": tok, "pmid": None, "doi": None, "raw": None}


def read_file(path):
    """Tokens from a text file: a line that is only digits is a PMID; otherwise every DOI in the
    line and every 'PMID: n' in it. Blank lines and lines starting with # are skipped."""
    tokens = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.isdigit():
                tokens.append(s)
                continue
            tokens.extend(dh.find_dois(s))
            tokens.extend(m.group(1) for m in PMID_RE.finditer(s))
    return tokens


def http_json(url, tries=4, sleep=time.sleep):
    """(parsed JSON, None) or (None, error text). HTTP 404 is final; 400, 5xx and network errors
    are retried with a growing pause."""
    last = ""
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "HTTP 404"
            last = "HTTP %d" % e.code
        except Exception as e:  # network hiccups, bad JSON
            last = "%s: %s" % (type(e).__name__, e)
        if k + 1 < tries:
            sleep(1.5 * (k + 1))
    return None, last


# ---- PubMed ----

def pubmed_lookup(pmids, dois, get=None, pause=None):
    """{"by_pmid": {pmid: esummary record}, "doi_to_pmid": {doi: pmid}, "errors": [text]}."""
    get = get or http_json
    pause = pause or time.sleep
    out = {"by_pmid": {}, "doi_to_pmid": {}, "errors": []}
    ids = [str(p) for p in pmids]
    for batch in chunks(list(dois), PUBMED_BATCH):
        term = " OR ".join('"%s"[doi]' % d for d in batch)
        url = EUTILS + "esearch.fcgi?db=pubmed&retmode=json&retmax=%d&term=%s" % (
            len(batch) * 2, urllib.parse.quote(term, safe=""))
        data, err = get(url)
        pause(NCBI_PAUSE)
        if err or not isinstance(data, dict):
            out["errors"].append("esearch from %s: %s" % (batch[0], err or "bad response"))
            continue
        ids.extend(str(i) for i in (data.get("esearchresult") or {}).get("idlist") or [])
    seen = set()
    ids = [i for i in ids if not (i in seen or seen.add(i))]
    for batch in chunks(ids, PUBMED_BATCH):
        url = EUTILS + "esummary.fcgi?db=pubmed&retmode=json&id=%s" % ",".join(batch)
        data, err = get(url)
        pause(NCBI_PAUSE)
        result = data.get("result") if isinstance(data, dict) else None
        if err or not isinstance(result, dict):
            out["errors"].append("esummary from %s: %s" % (batch[0], err or "bad response"))
            continue
        for uid in result.get("uids") or []:
            rec = result.get(str(uid))
            if not isinstance(rec, dict) or rec.get("error"):
                continue
            out["by_pmid"][str(uid)] = rec
            for a in rec.get("articleids") or []:
                if a.get("idtype") == "doi" and a.get("value"):
                    out["doi_to_pmid"][dh.clean_doi(a["value"])] = str(uid)
    return out


def pubmed_status(rec):
    """What one esummary record says: retracted, concern, corrected, the notices behind that,
    and whether the record is itself a notice."""
    pubtypes = [str(p) for p in rec.get("pubtype") or []]
    status = {"retracted": "Retracted Publication" in pubtypes, "concern": False, "corrected": False,
              "notices": [], "is_notice": any(p in NOTICE_PUBTYPES for p in pubtypes), "notice_of": [],
              "pubtypes": pubtypes, "title": " ".join(str(rec.get("title") or "").split()),
              "pubdate": rec.get("pubdate"), "year": None}
    m = re.match(r"\d{4}", str(rec.get("pubdate") or ""))
    if m:
        status["year"] = int(m.group(0))
    for ref in rec.get("references") or []:
        kind = str(ref.get("reftype") or "").strip().lower()
        n = {"reftype": ref.get("reftype"), "refsource": ref.get("refsource"), "pmid": ref.get("pmid")}
        if kind in PUBMED_RETRACTED:
            status["retracted"] = True
            status["notices"].append(n)
        elif kind in PUBMED_CONCERN:
            status["concern"] = True
            status["notices"].append(n)
        elif kind in PUBMED_CORRECTED:
            status["corrected"] = True
            status["notices"].append(n)
        elif kind in PUBMED_NOTICE_OF:
            status["is_notice"] = True
            status["notice_of"].append(n)
    return status


# ---- Crossref ----

def crossref_lookup(dois, get=None):
    """{"by_doi": {doi: work item}, "errors": [text]} with only the fields the check needs."""
    get = get or http_json
    out = {"by_doi": {}, "errors": []}
    for batch in chunks(list(dois), CROSSREF_BATCH):
        flt = ",".join("doi:" + d for d in batch)
        url = "%s?filter=%s&select=DOI,title,type,issued,updated-by,update-to&rows=%d&mailto=%s" % (
            CROSSREF, urllib.parse.quote(flt, safe=":,/()"), len(batch), MAILTO)
        data, err = get(url)
        items = (data.get("message") or {}).get("items") if isinstance(data, dict) else None
        if err or not isinstance(items, list):
            out["errors"].append("crossref from %s: %s" % (batch[0], err or "bad response"))
            continue
        for it in items:
            if isinstance(it, dict) and it.get("DOI"):
                out["by_doi"][dh.clean_doi(it["DOI"])] = it
    return out


def _date(parts):
    parts = [x for x in ((parts or [[]])[0] or []) if isinstance(x, int)]
    return "-".join(("%02d" % x) if i else str(x) for i, x in enumerate(parts)) or None


def crossref_status(item):
    """What one Crossref work says: Crossmark/Retraction Watch updates to it, whether it is itself
    a notice, and whether its title carries a RETRACTED/WITHDRAWN prefix."""
    updates, retracted, concern, corrected = [], False, False, False
    for u in item.get("updated-by") or []:
        kind = str(u.get("type") or "").strip().lower().replace(" ", "_").replace("-", "_")
        updates.append({"type": kind, "label": u.get("label"), "doi": dh.clean_doi(u.get("DOI")),
                        "date": _date((u.get("updated") or {}).get("date-parts")),
                        "source": u.get("source")})
        if kind in RETRACTED_TYPES:
            retracted = True
        elif kind in CONCERN_TYPES:
            concern = True
        else:
            corrected = True
    title = " ".join(str((item.get("title") or [""])[0]).split())
    prefix = bool(TITLE_PREFIX.match(title))
    notice_of = [{"type": u.get("type"), "doi": dh.clean_doi(u.get("DOI"))}
                 for u in item.get("update-to") or []]
    issued = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
    year = issued[0] if issued and isinstance(issued[0], int) else None
    return {"retracted": retracted or prefix, "concern": concern, "corrected": corrected,
            "updates": updates, "title_prefix": prefix, "is_notice": bool(notice_of),
            "notice_of": notice_of, "title": title, "year": year, "type": item.get("type")}


# ---- combine ----

def overall(pubmed, crossref):
    """(status, sources that say so). Worst level wins; clear needs at least one answering source."""
    sources = [("pubmed", pubmed), ("crossref", crossref)]
    for level in ("retracted", "concern", "corrected"):
        said = [name for name, s in sources if s and s.get(level)]
        if said:
            return level, said
    if any(s for _, s in sources):
        return "clear", []
    return "unknown", []


def combine(entry, pub_rec, cr_item, blocklist=None, today=None):
    rec = {"input": entry["input"], "pmid": entry.get("pmid"), "doi": entry.get("doi"), "title": "",
           "year": None, "status": "invalid", "said_by": [], "pubmed": None, "crossref": None,
           "hygiene": [], "checked_at": today or datetime.date.today().isoformat()}
    if not rec["pmid"] and not rec["doi"]:
        return rec
    if rec["doi"]:
        rec["hygiene"] = dh.check_doi(entry.get("raw") or rec["doi"], blocklist)["flags"]
    if pub_rec is not None:
        rec["pubmed"] = pubmed_status(pub_rec)
    if cr_item is not None:
        rec["crossref"] = crossref_status(cr_item)
    rec["title"] = (rec["pubmed"] or {}).get("title") or (rec["crossref"] or {}).get("title") or ""
    rec["year"] = (rec["crossref"] or {}).get("year") or (rec["pubmed"] or {}).get("year")
    rec["status"], rec["said_by"] = overall(rec["pubmed"], rec["crossref"])
    return rec


def run(tokens, get=None, pause=None, use_pubmed=True, use_crossref=True, blocklist=None, today=None):
    """(records, errors) for a list of PMID/DOI tokens. Duplicates are dropped; order is kept."""
    entries, seen = [], set()
    for t in tokens:
        e = parse_token(t)
        key = (e["pmid"], e["doi"])
        if key != (None, None) and key in seen:
            continue
        seen.add(key)
        entries.append(e)
    pmids = [e["pmid"] for e in entries if e["pmid"]]
    dois = [e["doi"] for e in entries if e["doi"]]
    empty_pub = {"by_pmid": {}, "doi_to_pmid": {}, "errors": []}
    pub = pubmed_lookup(pmids, dois, get, pause) if use_pubmed and (pmids or dois) else empty_pub
    for e in entries:
        if e["pmid"] and not e["doi"]:
            for a in (pub["by_pmid"].get(e["pmid"]) or {}).get("articleids") or []:
                if a.get("idtype") == "doi" and a.get("value"):
                    e["doi"] = dh.clean_doi(a["value"])
                    break
        elif e["doi"] and not e["pmid"]:
            e["pmid"] = pub["doi_to_pmid"].get(e["doi"])
    all_dois = sorted({e["doi"] for e in entries if e["doi"]})
    cr = crossref_lookup(all_dois, get) if use_crossref and all_dois else {"by_doi": {}, "errors": []}
    records = []
    for e in entries:
        p = pub["by_pmid"].get(e["pmid"]) if e["pmid"] else None
        c = cr["by_doi"].get(e["doi"]) if e["doi"] else None
        records.append(combine(e, p, c, blocklist, today))
    return records, pub["errors"] + cr["errors"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", help="PMIDs and DOIs")
    ap.add_argument("--file", help="text file: one PMID or DOI per line, or free text with DOIs and 'PMID: n'")
    ap.add_argument("--out", help="write JSON lines here instead of stdout")
    ap.add_argument("--fail-on", choices=["retracted", "concern", "corrected"],
                    help="exit 2 if any record is at this level or worse")
    ap.add_argument("--no-pubmed", action="store_true", help="skip PubMed")
    ap.add_argument("--no-crossref", action="store_true", help="skip Crossref")
    ap.add_argument("--blocklist", default=dh.BLOCKLIST, help="doi_hygiene blocklist CSV ('' for none)")
    args = ap.parse_args(argv)
    tokens = list(args.ids) + (read_file(args.file) if args.file else [])
    if not tokens:
        ap.error("give PMIDs/DOIs or --file")
    records, errors = run(tokens, use_pubmed=not args.no_pubmed, use_crossref=not args.no_crossref,
                          blocklist=dh.load_blocklist(args.blocklist))
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    counts = {s: sum(1 for r in records if r["status"] == s) for s in STATUS_ORDER}
    print("%d checked: %s; %d with doi_hygiene flags; %d lookup errors" % (
        len(records), ", ".join("%d %s" % (counts[s], s) for s in STATUS_ORDER if counts[s]),
        sum(1 for r in records if r["hygiene"]), len(errors)), file=sys.stderr)
    for e in errors:
        print("error: " + e, file=sys.stderr)
    if args.fail_on:
        bad = STATUS_ORDER[:STATUS_ORDER.index(args.fail_on) + 1]
        if any(r["status"] in bad for r in records):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
