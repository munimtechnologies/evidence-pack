#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""pubmed_commentin: census of PubMed "Comment in" links that carry no PMID.

Pre-registration: findings/pubmed-commentin-census-prereg-v1-2026-10-17.md.
Operational amendment (retries only, no change to the analysis):
findings/pubmed-commentin-census-prereg-v1-amendment-2026-10-17.md.

A PubMed "Comment in" link (CommentsCorrections RefType="CommentIn") should
point to a later item that comments on the record. A pilot on JAMA's 2025
randomized trials found a second kind: links whose RefSource is a bare
"doi: 10.1001/..." with no PMID, pointing to related, mostly older JAMA Network
articles. This script counts both kinds at 13 JAMA Network journals and 4
control journals (2016-2026), dates both ends of each link in Crossref, and
checks whether the target names the record back in its own "Comment on" list.

Classes of "Comment in" entries:
  pmid          the entry has a PMID child
  bare_doi      no PMID, and RefSource is only "doi: 10.x/..."
  other_nopmid  no PMID, anything else

Standard library only. Usage: python pubmed_commentin.py --out-dir /out
"""
import argparse
import collections
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

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works"
UA = "mv2-pubmed-commentin/1.1 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
SEED = 20261017
GROUPS = ("jama_network", "control")
JAMA_NETWORK = ("JAMA", "JAMA Netw Open", "JAMA Intern Med", "JAMA Pediatr", "JAMA Cardiol",
                "JAMA Neurol", "JAMA Surg", "JAMA Oncol", "JAMA Psychiatry", "JAMA Dermatol",
                "JAMA Ophthalmol", "JAMA Otolaryngol Head Neck Surg", "JAMA Health Forum")
CONTROL = ("N Engl J Med", "Lancet", "BMJ", "Ann Intern Med")
YEARS = tuple(range(2016, 2027))
PER_GROUP_PMID_DATED = 3000
MAX_BARE_DATED = 20000
PER_GROUP_RECIPROCITY = 300
# Operational settings (amendment 2026-10-17). NCBI returns some backend
# failures as HTTP 400, so E-utilities calls retry them; a batch that still
# fails is re-tried in pieces of EFETCH_SPLIT, and pieces that still fail are
# recorded, not fatal. More than VOID_SHARE of records lost voids the run.
EFETCH_BATCH = 200
EFETCH_SPLIT = 20
EFETCH_MAX_FAILED_BATCHES = 10
VOID_SHARE = 0.01
# The 76 JAMA 2025 randomized-trial records read by hand in the pilot. They are
# held out so the census tests the pattern on records nobody looked at.
PILOT_PMIDS = frozenset("""
41205227 41191364 41159835 41159812 41144242 41134589 41123939 41114973 41076588 41076587
41026481 40982270 40960806 40928788 40920401 40906494 40886310 40886309 40887995 40884493
40878848 40853561 40839372 40773205 40758331 40720610 40632510 40616323 40587141 40501321
40495743 40489090 40471557 40455621 40434761 40388916 40366680 40354045 40332892 40323617
40294395 40274279 40266580 40159390 40156829 40121537 40098564 40079944 40079940 40063041
40042839 39992668 39928308 39908052 39878993 39878968 39869330 39847361 39813042 39804681
39804674 39761054 39671272 39665585 39657224 39658862 39657981 39652885 39621340 39616603
39602290 39602173 39556768 39556379 39540799 39466640
""".split())

DOI_ONLY = re.compile(r"^\s*doi:\s*(10\.\d{4,9}/\S+?)\.?\s*$", re.I)
ANY_DOI = re.compile(r"doi:\s*(10\.\d{4,9}/\S+)", re.I)


def classify(ref_source, pmid):
    if pmid:
        return "pmid"
    if DOI_ONLY.match(ref_source or ""):
        return "bare_doi"
    return "other_nopmid"


def ref_doi(ref_source):
    m = ANY_DOI.search(ref_source or "")
    return m.group(1).rstrip(".,;").lower() if m else ""


def parse_articles(data):
    """Records from PubMed efetch XML: pmid, doi, ta, year, pubtypes, comment_in, comment_on."""
    out = []
    for art in ET.fromstring(data).iter("PubmedArticle"):
        mc = art.find("MedlineCitation")
        a = mc.find("Article")
        doi = ""
        for e in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if e.get("IdType") == "doi" and (e.text or "").strip():
                doi = e.text.strip().lower()
                break
        if not doi and a is not None:
            for e in a.findall("ELocationID"):
                if e.get("EIdType") == "doi" and (e.text or "").strip():
                    doi = e.text.strip().lower()
                    break
        year = 0
        if a is not None:
            pd = a.find("Journal/JournalIssue/PubDate")
            if pd is not None:
                y = pd.findtext("Year") or (pd.findtext("MedlineDate") or "")[:4]
                year = int(y) if y.isdigit() else 0
        comment_in, comment_on = [], []
        for c in mc.findall("CommentsCorrectionsList/CommentsCorrections"):
            src = (c.findtext("RefSource") or "").strip()
            pmid = (c.findtext("PMID") or "").strip()
            if c.get("RefType") == "CommentIn":
                comment_in.append({"source": src, "pmid": pmid, "cls": classify(src, pmid),
                                   "doi": ref_doi(src)})
            elif c.get("RefType") == "CommentOn" and pmid:
                comment_on.append(pmid)
        out.append({"pmid": (mc.findtext("PMID") or "").strip(), "doi": doi,
                    "ta": (mc.findtext("MedlineJournalInfo/MedlineTA") or "").strip(), "year": year,
                    "pubtypes": [p.text or "" for p in a.findall("PublicationTypeList/PublicationType")]
                    if a is not None else [],
                    "comment_in": comment_in, "comment_on": comment_on})
    return out


def earlier(t, s):
    """True if date t is strictly before date s, compared at the coarser of the two precisions."""
    if not t or not s:
        return None
    k = min(len(t), len(s))
    return tuple(t[:k]) < tuple(s[:k])


def sample(items, k, rng):
    return list(items) if len(items) <= k else rng.sample(list(items), k)


def judge(parts):
    """parts: (n, k, op, threshold, min_n). Supported only if every share k/n passes."""
    ok = []
    for n, k, op, thr, min_n in parts:
        if n < min_n:
            return "untestable"
        s = k / n
        ok.append(s >= thr if op == ">=" else s <= thr)
    return "supported" if all(ok) else "not supported"


def build_links(arts, recs):
    links = []
    for pmid in sorted(arts, key=int):
        a = arts[pmid]
        group, ta, year = recs.get(pmid, ("", "", 0))
        for c in a["comment_in"]:
            links.append({"group": group, "ta": ta, "year": year, "src_pmid": pmid,
                          "src_doi": a["doi"], "cls": c["cls"], "tgt_pmid": c["pmid"],
                          "tgt_doi": c["doi"], "ref_source": c["source"]})
    return links


def tally(links):
    t = {}
    for l in links:
        g = t.setdefault(l["group"], {"pmid": 0, "bare_doi": 0, "other_nopmid": 0})
        g[l["cls"]] += 1
    return t


def breakdown(arts, recs, by):
    out = {}
    for pmid, a in arts.items():
        group, ta, year = recs[pmid]
        d = out.setdefault(f"{group}|{ta if by == 'ta' else year}",
                           {"records": 0, "with_bare_doi": 0, "links": 0, "bare_doi_links": 0})
        nb = sum(1 for c in a["comment_in"] if c["cls"] == "bare_doi")
        d["records"] += 1
        d["with_bare_doi"] += 1 if nb else 0
        d["links"] += len(a["comment_in"])
        d["bare_doi_links"] += nb
    return dict(sorted(out.items()))


def dating_tally(links):
    out = {}
    for l in links:
        if l.get("earlier") is None:
            continue
        d = out.setdefault(l["group"], {}).setdefault(l["cls"], [0, 0])
        d[0] += 1
        d[1] += 1 if l["earlier"] else 0
    return out


def reciprocity_tally(checks):
    out = {}
    for r in checks:
        if r.get("reciprocal") is None:
            continue
        d = out.setdefault(r["group"], {}).setdefault(r["cls"], [0, 0])
        d[0] += 1
        d[1] += 1 if r["reciprocal"] else 0
    return out


def prefix_tally(links):
    out = {}
    for l in links:
        if l["cls"] == "bare_doi":
            d = out.setdefault(l["group"], [0, 0])
            d[0] += 1
            d[1] += 1 if l["tgt_doi"].startswith("10.1001/") else 0
    return out


def verdicts(t, dating, recip, prefix):
    j, c = t.get("jama_network", {}), t.get("control", {})
    jd, jr = dating.get("jama_network", {}), recip.get("jama_network", {})
    pj = prefix.get("jama_network", [0, 0])
    return {
        "H1": judge([(sum(j.values()), j.get("bare_doi", 0), ">=", 0.02, 100),
                     (sum(c.values()), c.get("bare_doi", 0), "<=", 0.005, 100)]),
        "H2": judge([tuple(jd.get("bare_doi", [0, 0])) + (">=", 0.80, 30),
                     tuple(jd.get("pmid", [0, 0])) + ("<=", 0.05, 30)]),
        "H3": judge([tuple(jr.get("bare_doi", [0, 0])) + ("<=", 0.10, 30),
                     tuple(jr.get("pmid", [0, 0])) + (">=", 0.90, 30)]),
        "H4": judge([(pj[0], pj[1], ">=", 0.90, 30)]),
    }


def http(url, data=None, tries=4, retry_400=False):
    """GET (or POST if data) with retries. 404 is final; 400 is final unless retry_400."""
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or (e.code == 400 and not retry_400):
                raise
            try:
                body = e.read()[:300].decode("utf-8", "replace")
            except Exception:
                body = ""
            last = RuntimeError(f"HTTP {e.code}: {body}")
        except Exception as e:  # network hiccups: retry
            last = e
        time.sleep(3 * (k + 1))
    raise last


def ncbi(url, data=None):
    try:
        return http(url, data, tries=5, retry_400=True)
    finally:
        time.sleep(0.4)  # stay under 3 requests per second without an API key


def get_json(url):
    try:
        return json.loads(http(url))
    finally:
        time.sleep(0.1)


def esearch_ids(term):
    q = urllib.parse.urlencode({"db": "pubmed", "term": term, "retmax": "9999", "retmode": "json"})
    r = json.loads(ncbi(EUTILS + "esearch.fcgi?" + q))["esearchresult"]
    return int(r["count"]), r.get("idlist", [])


def collect(journals, group, log):
    recs = {}
    for ta in journals:
        for y in YEARS:
            term = f'hascommentin AND "{ta}"[ta] AND {y}[dp]'
            n, ids = esearch_ids(term)
            parts = [(term, n, ids)]
            if n > len(ids):
                parts = []
                for m in range(1, 13):
                    t2 = f'hascommentin AND "{ta}"[ta] AND {y}/{m:02d}[dp]'
                    parts.append((t2,) + esearch_ids(t2))
            for t2, n2, ids2 in parts:
                log.append({"term": t2, "count": n2, "got": len(ids2)})
                for i in ids2:
                    recs.setdefault(i, (group, ta, y))
    return recs


def _efetch_post(body):
    return ncbi(EUTILS + "efetch.fcgi", body)


def efetch(pmids, errors=None, fetch=None):
    """{pmid: record}. A failing batch is re-tried in pieces; pieces that still fail are logged
    in errors as {"efetch_failed": [pmids], "error": ...} and left out. After
    EFETCH_MAX_FAILED_BATCHES failed pieces, the rest is logged as skipped without fetching."""
    fetch = fetch or _efetch_post
    errors = [] if errors is None else errors
    out, state = {}, {"failed": 0}

    def one(chunk, may_split):
        if state["failed"] >= EFETCH_MAX_FAILED_BATCHES:
            errors.append({"efetch_failed": list(chunk), "error": "skipped after repeated failures"})
            return
        body = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"}).encode()
        try:
            arts = parse_articles(fetch(body))
        except Exception as e:
            if may_split and len(chunk) > EFETCH_SPLIT:
                for j in range(0, len(chunk), EFETCH_SPLIT):
                    one(chunk[j:j + EFETCH_SPLIT], False)
            else:
                state["failed"] += 1
                errors.append({"efetch_failed": list(chunk), "error": repr(e)[:300]})
            return
        for a in arts:
            out[a["pmid"]] = a

    for i in range(0, len(pmids), EFETCH_BATCH):
        one(pmids[i:i + EFETCH_BATCH], True)
    return out


def efetch_failed_count(errors):
    return sum(len(e["efetch_failed"]) for e in errors if "efetch_failed" in e)


def _item_date(it):
    dp = ((it.get("published") or {}).get("date-parts") or [[]])[0]
    return [int(x) for x in dp if x is not None]


def crossref_dates(dois, fetch_json, errors=None):
    """{doi: {"date": [y, m, d], "type": ..., "title": ...}} from Crossref, 20 DOIs per call."""
    out = {}
    clean = sorted({d for d in dois if d and "," not in d})
    for i in range(0, len(clean), 20):
        chunk = clean[i:i + 20]
        q = urllib.parse.urlencode({"filter": ",".join("doi:" + d for d in chunk),
                                    "select": "DOI,published,type,title", "rows": "40"})
        try:
            items = fetch_json(CROSSREF + "?" + q).get("message", {}).get("items", [])
        except Exception as e:
            if errors is not None:
                errors.append({"crossref_batch": i, "error": repr(e)[:200]})
            items = []
            for d in chunk:
                try:
                    items.append(fetch_json(CROSSREF + "/" + urllib.parse.quote(d)).get("message", {}))
                except Exception as e2:
                    if errors is not None:
                        errors.append({"crossref_doi": d, "error": repr(e2)[:200]})
        for it in items:
            if it.get("DOI"):
                out[it["DOI"].lower()] = {"date": _item_date(it), "type": it.get("type", ""),
                                          "title": ((it.get("title") or [""])[0] or "")[:200]}
    return out


def doi_to_pmid(doi):
    try:
        n, ids = esearch_ids(f"{doi}[doi]")
    except Exception:
        return ""
    return ids[0] if n == 1 and ids else ""


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--max-records", type=int, default=0, help="for smoke tests only")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    t0, log, errors = time.time(), [], []
    rng = random.Random(SEED)

    recs = {}
    for group, journals in (("jama_network", JAMA_NETWORK), ("control", CONTROL)):
        for pmid, meta in collect(journals, group, log).items():
            recs.setdefault(pmid, meta)
    held_out = sorted(p for p in recs if p in PILOT_PMIDS)
    for p in held_out:
        del recs[p]
    pmids = sorted(recs, key=int)
    if args.max_records:
        pmids = pmids[:args.max_records]
    fetch_errors = []
    arts = {p: a for p, a in efetch(pmids, fetch_errors).items() if p in recs}
    records_failed = efetch_failed_count(fetch_errors)
    errors += fetch_errors
    links = build_links(arts, recs)
    t = tally(links)

    # Dating: every bare_doi link (up to MAX_BARE_DATED) and a seeded sample of pmid links with DOIs.
    bare = [l for l in links if l["cls"] == "bare_doi" and l["src_doi"] and l["tgt_doi"]]
    dated = sample(bare, MAX_BARE_DATED, rng)
    for g in GROUPS:
        pool = [l for l in links if l["cls"] == "pmid" and l["group"] == g and l["src_doi"] and l["tgt_doi"]]
        dated += sample(pool, PER_GROUP_PMID_DATED, rng)
    dates = crossref_dates({l["src_doi"] for l in dated} | {l["tgt_doi"] for l in dated}, get_json, errors)
    for l in dated:
        s, tg = dates.get(l["src_doi"], {}), dates.get(l["tgt_doi"], {})
        l["src_date"], l["tgt_date"] = s.get("date", []), tg.get("date", [])
        l["tgt_type"], l["tgt_title"] = tg.get("type", ""), tg.get("title", "")
        l["earlier"] = earlier(l["tgt_date"], l["src_date"])

    # Reciprocity: does the target list the record in its own "Comment on"?
    checks, cache = [], {}
    for g in GROUPS:
        for l in sample([x for x in links if x["cls"] == "bare_doi" and x["group"] == g and x["tgt_doi"]],
                        PER_GROUP_RECIPROCITY, rng):
            if l["tgt_doi"] not in cache:
                cache[l["tgt_doi"]] = doi_to_pmid(l["tgt_doi"])
            checks.append({"group": g, "cls": "bare_doi", "src_pmid": l["src_pmid"],
                           "tgt_doi": l["tgt_doi"], "tgt_pmid": cache[l["tgt_doi"]]})
        for l in sample([x for x in links if x["cls"] == "pmid" and x["group"] == g],
                        PER_GROUP_RECIPROCITY, rng):
            checks.append({"group": g, "cls": "pmid", "src_pmid": l["src_pmid"],
                           "tgt_doi": l["tgt_doi"], "tgt_pmid": l["tgt_pmid"]})
    target_errors = []
    targets = efetch(sorted({c["tgt_pmid"] for c in checks if c["tgt_pmid"]}, key=int), target_errors)
    errors += target_errors
    for c in checks:
        tg = targets.get(c["tgt_pmid"])
        c["reciprocal"] = (c["src_pmid"] in tg["comment_on"]) if tg else None
        c["tgt_pubtypes"] = tg["pubtypes"] if tg else []

    dating, recip, prefix = dating_tally(dated), reciprocity_tally(checks), prefix_tally(links)
    prefixes = collections.Counter(l["tgt_doi"].split("/")[0] for l in links if l["cls"] == "bare_doi")
    results = {
        "prereg": "findings/pubmed-commentin-census-prereg-v1-2026-10-17.md",
        "amendment": "findings/pubmed-commentin-census-prereg-v1-amendment-2026-10-17.md",
        "seed": SEED, "years": [YEARS[0], YEARS[-1]], "journals": {"jama_network": JAMA_NETWORK,
                                                                   "control": CONTROL},
        "records_found": len(recs) + len(held_out), "held_out_pilot_records": len(held_out),
        "records_fetched": len(arts), "records_failed": records_failed,
        "reciprocity_targets_failed": efetch_failed_count(target_errors),
        "void": records_failed > VOID_SHARE * max(len(pmids), 1),
        "records_without_comment_in": sum(1 for a in arts.values() if not a["comment_in"]),
        "links_by_class": t, "dating": dating, "reciprocity": recip, "prefix_10_1001": prefix,
        "bare_doi_target_prefixes": dict(prefixes.most_common(20)),
        "by_year": breakdown(arts, recs, "year"), "by_journal": breakdown(arts, recs, "ta"),
        "hypotheses": verdicts(t, dating, recip, prefix),
        "search_log": log, "errors": errors[:200], "n_errors": len(errors),
        "minutes": round((time.time() - t0) / 60, 1),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    write_jsonl(os.path.join(args.out_dir, "nopmid_links.jsonl"),
                [l for l in links if l["cls"] != "pmid"])
    write_jsonl(os.path.join(args.out_dir, "pmid_dated_sample.jsonl"),
                [l for l in dated if l["cls"] == "pmid"])
    write_jsonl(os.path.join(args.out_dir, "reciprocity.jsonl"), checks)
    print(json.dumps({k: results[k] for k in ("records_fetched", "records_failed", "void", "links_by_class",
                                               "dating", "reciprocity", "prefix_10_1001", "hypotheses",
                                               "n_errors", "minutes")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
