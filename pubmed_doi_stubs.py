# pubmed_doi_stubs.py - PubMed records whose DOI is a bare Elsevier stem (e.g. "10.1016/S0197"), and what that does downstream.
# Pre-registration: findings/pubmed-doi-stub-census-prereg-v1-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads NCBI E-utilities, Crossref and OpenAlex.
import argparse
import csv
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAILTO = "mv2@munimtech.com"
TOOL = "mv2-pubmed-doi-stubs"
UA = "mv2-pubmed-doi-stubs/1.0 (MV2 of Munim, Inc.; mailto:%s)" % MAILTO
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CR = "https://api.crossref.org/works/"
OA = "https://api.openalex.org/works"
SEED = 20261022
WAITS = (5, 30, 120)
GROUP = 50  # stems per OR search
EFETCH_BATCH = 200
NCBI_PAUSE = 0.4  # NCBI asks for at most 3 requests a second without a key
CR_PAUSE = 0.05
OA_PAUSE = 0.15
MAX_OA_CALLS = 400
H3_SAMPLE = 200

# Pre-registered thresholds
H1_MIN = 300  # PubMed records whose DOI is exactly a bare Elsevier stem
H2_YEARS, H2_SHARE, H2_MIN_N = (2003, 2005), 0.80, 30
H3_SHARE, H3_MIN_N = 0.90, 20  # PII-rebuilt DOIs registered in Crossref with a matching title
H4_SHARE, H4_MIN_N = 0.30, 50  # PMIDs that no OpenAlex work carries as its PMID

STOP = {"with", "from", "that", "this", "have", "been", "were", "into", "over", "than", "their", "these", "those",
        "which", "after", "among", "between", "during", "under", "using", "within", "without", "about", "study"}
PII = re.compile(r"^S(\d{4})(\d{3}[\dX])(\d{2})(\d{5})([\dX])$", re.I)


def http(url, data=None, waits=WAITS, sleep=time.sleep):
    """GET (POST when data is given) with back-off on 429/5xx. Returns bytes, or None (400/404 or after the last wait)."""
    last = None
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    for w in (0,) + tuple(waits):
        if w:
            sleep(w)
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            last = e
        except Exception as e:  # network hiccup: wait and retry
            last = e
    sys.stderr.write("HTTP gave up %s: %s\n" % (url, last))
    return None


class Eutils:
    """esearch/efetch over POST, paced and counted. fetch(url, data) defaults to http()."""

    def __init__(self, fetch=None, pause=NCBI_PAUSE, sleep=time.sleep):
        self.fetch, self.pause, self.sleep, self.calls, self.failed = fetch, pause, sleep, 0, 0

    def post(self, cgi, params):
        self.calls += 1
        if self.pause:
            self.sleep(self.pause)
        raw = (self.fetch or http)(EU + cgi, dict(params, tool=TOOL, email=MAILTO))
        if raw is None:
            self.failed += 1
        return raw

    def search(self, term, retmax=0):
        """The esearchresult dict, or None if the call failed."""
        raw = self.post("esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "json", "retmax": str(retmax)})
        if not raw:
            return None
        try:
            return json.loads(raw).get("esearchresult") or {}
        except ValueError:
            self.failed += 1
            return None


def elsevier_stems():
    """Every bare Elsevier stem a DOI cut at its first hyphen can leave: 10.1016/S#### (PII era) and 10.1016/####."""
    return ["10.1016/S%04d" % i for i in range(10000)] + ["10.1016/%04d" % i for i in range(10000)]


def phrase(stem):
    return '"%s"[aid]' % stem


def norm(s):
    s = re.sub(r"\[[^\]]*\]\s*$", "", (s or "").strip().lower()).strip()
    return s.strip('"').strip()


def matched_in(res, group):
    """Stems of a group that an OR search matched: from the query translation, else the group minus phrases not found."""
    want = {norm(s): s for s in group}
    hits = sorted({want[norm(m)] for m in re.findall(r'"([^"]+)"\[', res.get("querytranslation") or "")
                   if norm(m) in want})
    if hits:
        return hits
    missing = set()
    for key in ("warninglist", "errorlist"):
        missing |= {norm(x) for x in (res.get(key) or {}).get("phrasesnotfound") or []}
    return [s for s in group if norm(s) not in missing] or list(group)


def screen(eu, stems, group=GROUP):
    """Group-test stems as PubMed article identifiers. Returns (candidate stems, number of groups whose search failed)."""
    cands, failed = [], 0
    for i in range(0, len(stems), group):
        g = stems[i:i + group]
        res = eu.search(" OR ".join(phrase(s) for s in g))
        if res is None:
            failed += 1
            continue
        if int(res.get("count") or 0):
            cands += matched_in(res, g)
    return cands, failed


def text_of(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def year_of(pd):
    if pd is None:
        return None
    m = re.search(r"\d{4}", text_of(pd.find("Year")) or text_of(pd.find("MedlineDate")))
    return int(m.group(0)) if m else None


def parse_pubmed_xml(raw):
    """One dict per PubmedArticle. Only the article's own ArticleIdList is read, never its reference list."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    recs = []
    for art in root.iter("PubmedArticle"):
        mc = art.find("MedlineCitation")
        a = mc.find("Article") if mc is not None else None
        if a is None:
            continue
        ids = {}
        for el in art.findall("PubmedData/ArticleIdList/ArticleId"):
            ids.setdefault(el.get("IdType") or "", (el.text or "").strip())
        eloc = [(e.text or "").strip() for e in a.findall("ELocationID") if e.get("EIdType") == "doi"]
        j = a.find("Journal")
        recs.append({"pmid": text_of(mc.find("PMID")), "title": text_of(a.find("ArticleTitle"))[:300],
                     "journal": text_of(j.find("ISOAbbreviation")) if j is not None else "",
                     "issn": text_of(j.find("ISSN")) if j is not None else "",
                     "year": year_of(a.find("Journal/JournalIssue/PubDate")), "doi": ids.get("doi", ""),
                     "pii": ids.get("pii", ""), "eloc_doi": eloc[0] if eloc else ""})
    return recs


def fetch_records(eu, pmids, batch=EFETCH_BATCH):
    out, failed = [], 0
    for i in range(0, len(pmids), batch):
        raw = eu.post("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids[i:i + batch]), "retmode": "xml"})
        if raw is None:
            failed += 1
            continue
        out += parse_pubmed_xml(raw)
    return out, failed


def pii_to_doi(pii):
    """Elsevier's DOI from an S-type PII, e.g. S0091674903020116 -> 10.1016/S0091-6749(03)02011-6; '' otherwise."""
    m = PII.match(re.sub(r"[-()\s]", "", pii or ""))
    if not m:
        return ""
    return "10.1016/S%s-%s(%s)%s-%s" % tuple(g.upper() for g in m.groups())


def title_words(t):
    ws = []
    for w in re.findall(r"[a-z0-9]+", (t or "").lower()):
        if len(w) >= 4 and w not in STOP and w not in ws:
            ws.append(w)
    return ws[:10]


def title_match(pubmed_title, titles):
    """True if at least half (rounded up, min 1) of the PubMed title's content words appear as words in titles."""
    ws = title_words(pubmed_title)
    if not ws:
        return None
    text = " %s " % " ".join(re.findall(r"[a-z0-9]+", " ".join(titles).lower()))
    hits = sum(1 for w in ws if " %s " % w in text)
    return hits >= max(1, (len(ws) + 1) // 2)


def check_repair(fetch, rec):
    """Look the PII-rebuilt DOI up in Crossref and compare titles."""
    doi = rec["repaired_doi"]
    out = {"pmid": rec["pmid"], "stem": rec["stem"], "repaired_doi": doi}
    msg = None
    raw = fetch(CR + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
    if raw:
        try:
            msg = json.loads(raw).get("message") or None
        except ValueError:
            msg = None
    if msg is None:
        return dict(out, status="unregistered")
    titles = (msg.get("title") or []) + (msg.get("subtitle") or [])
    out["crossref_title"] = (titles[0] if titles else "")[:300]
    out["crossref_cites"] = msg.get("is-referenced-by-count")
    m = title_match(rec["title"], titles)
    if m is None:
        return dict(out, status="no_title_words")
    return dict(out, status="registered_match" if m else "registered_mismatch")


def openalex_by_pmid(fetch, pmids, cap=MAX_OA_CALLS):
    """OpenAlex works whose ids.pmid is in pmids. Returns (found {pmid: work}, pmids actually looked up, calls)."""
    found, looked, calls = {}, [], 0
    for i in range(0, len(pmids), 50):
        if calls >= cap:
            break
        calls += 1
        batch = pmids[i:i + 50]
        if OA_PAUSE:
            time.sleep(OA_PAUSE)
        raw = fetch(OA + "?" + urllib.parse.urlencode({"filter": "ids.pmid:" + "|".join(batch), "per-page": "200",
                                                       "select": "id,doi,display_name,ids,cited_by_count,locations_count",
                                                       "mailto": MAILTO}))
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        if data is None:
            continue
        looked += batch
        for w in data.get("results") or []:
            p = str((w.get("ids") or {}).get("pmid") or "").rstrip("/").rsplit("/", 1)[-1]
            if p:
                found[p] = {"id": str(w.get("id") or "").rsplit("/", 1)[-1],
                            "doi": re.sub(r"^https?://(dx\.)?doi\.org/", "", w.get("doi") or "", flags=re.I).lower(),
                            "title": (w.get("display_name") or "")[:300], "cites": w.get("cited_by_count") or 0,
                            "locations": w.get("locations_count")}
    return found, looked, calls


def score_h1(verified):
    n = sum(1 for r in verified if r["elsevier"])
    return ("supported" if n >= H1_MIN else "not supported"), {"n": n}


def score_h2(verified):
    ys = [r["year"] for r in verified if r["elsevier"] and r["year"]]
    if len(ys) < H2_MIN_N:
        return "untestable", {"n": len(ys)}
    k = sum(1 for y in ys if H2_YEARS[0] <= y <= H2_YEARS[1])
    return ("supported" if k / len(ys) >= H2_SHARE else "not supported"), {"n": len(ys), "in_window": k,
                                                                           "share": k / len(ys)}


def score_h3(checks):
    t = [c for c in checks if c["status"] != "no_title_words"]
    k = sum(1 for c in t if c["status"] == "registered_match")
    d = {"checked": len(checks), "testable": len(t), "registered_match": k,
         "registered_mismatch": sum(1 for c in t if c["status"] == "registered_mismatch"),
         "unregistered": sum(1 for c in t if c["status"] == "unregistered")}
    if len(t) < H3_MIN_N:
        return "untestable", d
    d["share"] = k / len(t)
    return ("supported" if d["share"] >= H3_SHARE else "not supported"), d


def score_h4(looked, found):
    nf = sum(1 for p in looked if p not in found)
    d = {"looked_up": len(looked), "not_found": nf}
    if len(looked) < H4_MIN_N:
        return "untestable", d
    d["share"] = nf / len(looked)
    return ("supported" if d["share"] >= H4_SHARE else "not supported"), d


def read_extra(path):
    if not path:
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return sorted({(r.get("stub") or "").strip() for r in csv.DictReader(f)} - {""})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--extra", default="", help="CSV with a 'stub' column: non-Elsevier stems, exploratory only")
    ap.add_argument("--limit", type=int, default=0, help="debug only: screen the first N Elsevier stems")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    eu = Eutils(pause=NCBI_PAUSE)
    stems = elsevier_stems()
    if a.limit:
        stems = stems[:a.limit]
    els = {s.lower() for s in stems}
    extra = [s for s in read_extra(a.extra) if s.lower() not in els]
    res = {"seed": SEED, "limit": a.limit, "screen": {"elsevier_stems": len(stems), "extra_stems": len(extra)}}

    cands, failed_groups = screen(eu, stems + extra)
    per_stem, failed_counts = {}, 0
    for s in cands:
        r = eu.search(phrase(s), retmax=10000)
        if r is None:
            failed_counts += 1
            continue
        if int(r.get("count") or 0):
            per_stem[s] = {"count": int(r.get("count") or 0), "pmids": r.get("idlist") or []}
    res["screen"].update({"candidates": len(cands), "stems_with_records": len(per_stem),
                          "failed_groups": failed_groups, "failed_counts": failed_counts})
    sys.stderr.write("screen done: %d stems with records, %d E-utilities calls\n" % (len(per_stem), eu.calls))

    pmids = sorted({p for v in per_stem.values() for p in v["pmids"]}, key=int)
    recs, failed_fetch = fetch_records(eu, pmids)
    stem_of = {s.lower(): s for s in per_stem}
    verified = []
    for r in recs:
        hit = [d for d in (r["doi"], r["eloc_doi"]) if d and d.lower() in stem_of]
        if hit:
            r["stem"] = stem_of[hit[0].lower()]
            r["elsevier"] = r["stem"].lower() in els
            r["repaired_doi"] = pii_to_doi(r["pii"])
            r["pii_matches_stem"] = bool(r["repaired_doi"]) and r["repaired_doi"][9:13] == r["stem"][9:13]
            verified.append(r)
    verified.sort(key=lambda r: int(r["pmid"]))
    res["verified"] = {"pmids_fetched": len(pmids), "records_parsed": len(recs), "failed_fetch_batches": failed_fetch,
                       "all": len(verified), "elsevier": sum(1 for r in verified if r["elsevier"]),
                       "with_s_pii": sum(1 for r in verified if r["repaired_doi"]),
                       "stems": len({r["stem"] for r in verified})}

    pool = [r for r in verified if r["elsevier"] and r["repaired_doi"]]
    pick = random.Random(SEED).sample(pool, min(H3_SAMPLE, len(pool)))
    checks = []
    for r in pick:
        checks.append(check_repair(http, r))
        if CR_PAUSE:
            time.sleep(CR_PAUSE)

    el_pmids = [r["pmid"] for r in verified if r["elsevier"]]
    found, looked, oa_calls = openalex_by_pmid(http, el_pmids)
    by_pmid = {r["pmid"]: r for r in verified}
    stub_works = {}
    for p, w in found.items():
        r = by_pmid.get(p)
        if r and w["doi"] == r["stem"].lower():
            sw = stub_works.setdefault(w["id"], dict(w, pmid=p, stem=r["stem"], pubmed_title=r["title"]))
            sw["title_matches_pmid"] = title_match(r["title"], [w["title"]])
    for r in verified:
        w = found.get(r["pmid"])
        r["openalex"] = w["id"] if w else ""
        r["openalex_doi"] = w["doi"] if w else ""

    res["H1"], res["H1_detail"] = score_h1(verified)
    res["H2"], res["H2_detail"] = score_h2(verified)
    res["H3"], res["H3_detail"] = score_h3(checks)
    res["H4"], res["H4_detail"] = score_h4(looked, found)
    res["openalex_stub_works"] = {"n": len(stub_works), "citations": sum(w["cites"] for w in stub_works.values()),
                                  "locations": sum(w["locations"] or 0 for w in stub_works.values()),
                                  "title_mismatch": sum(1 for w in stub_works.values()
                                                        if w["title_matches_pmid"] is False)}
    years, journals = {}, {}
    for r in verified:
        years[str(r["year"])] = years.get(str(r["year"]), 0) + 1
        journals[r["journal"]] = journals.get(r["journal"], 0) + 1
    res["years"] = dict(sorted(years.items()))
    res["top_journals"] = dict(sorted(journals.items(), key=lambda x: (-x[1], x[0]))[:30])
    res["calls"] = {"eutils": eu.calls, "eutils_failed": eu.failed, "crossref": len(checks), "openalex": oa_calls}

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for name, rows in (("records.jsonl", verified), ("repair_checks.jsonl", checks),
                       ("openalex_stub_works.jsonl", sorted(stub_works.values(), key=lambda w: (-w["cites"], w["id"])))):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(a.out_dir, "stems.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stem", "pubmed_count", "verified", "journals", "years"])
        for s in sorted(per_stem):
            rs = [r for r in verified if r["stem"] == s]
            ys = sorted(r["year"] for r in rs if r["year"])
            js = sorted({r["journal"] for r in rs})
            w.writerow([s, per_stem[s]["count"], len(rs), "; ".join(js[:5]), "%s-%s" % (ys[0], ys[-1]) if ys else ""])
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
