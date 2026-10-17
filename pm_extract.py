#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""pm_extract: turn the NLM SPARK PubMed baseline into compact JSONL, one file per baseline file.

Streams pubmed27nNNNN.xml.gz from the challenge's own copy
(ftp.ncbi.nlm.nih.gov/pubmed/.pubmed-spark/), checks each against its .md5,
and writes <data>/docs/pubmed27nNNNN.jsonl.gz with one record per citation:
pmid, pmcid, doi, title, abstract, year, journal, authors, mesh, keywords,
publication types. A per-file manifest (<data>/docs/manifest/NNNN.json) holds
the counts, so the job can stop at a time budget and the next version resumes
where it left off. The search index is built from these files in a later job.

Usage: python pm_extract.py --data /data --out /out [--first 1 --last 1306]
       [--workers 4] [--budget-minutes 160] [--devset devset_landmark_v1.jsonl]
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from multiprocessing import Pool

FTP = "https://ftp.ncbi.nlm.nih.gov/pubmed/.pubmed-spark/pubmed27n%04d.xml.gz"
UA = "Mozilla/5.0 (MV2 of Munim, Inc.; spark-pm-corpus; mv2@munimtech.com)"
MD5_RE = re.compile(r"\b([0-9a-fA-F]{32})\b")
YEAR_RE = re.compile(r"\b(1[89]\d\d|20\d\d)\b")
MAX_AUTHORS = 25
MIN_FREE_BYTES = 5 * 1024 ** 3


def fetch(url, timeout=300, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as err:  # network hiccups: back off and retry
            last = err
            time.sleep(5 * (attempt + 1))
    raise last


def md5_of(text):
    """The checksum in an NCBI .md5 file ('MD5(name)= <hex>')."""
    match = MD5_RE.search(text)
    return match.group(1).lower() if match else ""


def text_of(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def year_of(article):
    for path in ("Journal/JournalIssue/PubDate/Year", "Journal/JournalIssue/PubDate/MedlineDate",
                 "ArticleDate/Year"):
        match = YEAR_RE.search(article.findtext(path) or "")
        if match:
            return int(match.group(1))
    return None


def author_of(el):
    if el.findtext("CollectiveName"):
        return " ".join(el.findtext("CollectiveName").split())
    last = (el.findtext("LastName") or "").strip()
    initials = (el.findtext("Initials") or "").strip()
    return (last + " " + initials).strip()


def doc_of(pa):
    """One <PubmedArticle> as a compact dict, or None if it has no PMID."""
    mc = pa.find("MedlineCitation")
    if mc is None:
        return None
    pmid = (mc.findtext("PMID") or "").strip()
    if not pmid:
        return None
    art = mc.find("Article")
    doc = {"pmid": pmid, "pmcid": "", "doi": "", "title": "", "abstract": "", "year": None,
           "journal": "", "authors": [], "n_authors": 0, "mesh": [], "keywords": [], "ptypes": []}
    if art is not None:
        doc["title"] = text_of(art.find("ArticleTitle")) or text_of(art.find("VernacularTitle"))
        parts = []
        for ab in art.findall("Abstract/AbstractText"):
            body = text_of(ab)
            label = ab.get("Label")
            if body:
                parts.append(f"{label}: {body}" if label else body)
        doc["abstract"] = " ".join(parts)
        doc["year"] = year_of(art)
        doc["journal"] = (art.findtext("Journal/ISOAbbreviation") or mc.findtext("MedlineJournalInfo/MedlineTA")
                          or art.findtext("Journal/Title") or "").strip()
        authors = [a for a in (author_of(el) for el in art.findall("AuthorList/Author")) if a]
        doc["n_authors"] = len(authors)
        # keep the first authors and always the last (senior) author
        doc["authors"] = authors if len(authors) <= MAX_AUTHORS else authors[:MAX_AUTHORS - 1] + authors[-1:]
        doc["ptypes"] = [t for t in (text_of(p) for p in art.findall("PublicationTypeList/PublicationType")) if t]
    doc["mesh"] = [t for t in (text_of(d) for d in mc.findall("MeshHeadingList/MeshHeading/DescriptorName")) if t]
    doc["keywords"] = [t for t in (text_of(k) for k in mc.findall("KeywordList/Keyword")) if t]
    for aid in pa.findall("PubmedData/ArticleIdList/ArticleId"):
        kind = aid.get("IdType")
        if kind == "pmc" and not doc["pmcid"]:
            doc["pmcid"] = (aid.text or "").strip()
        elif kind == "doi" and not doc["doi"]:
            doc["doi"] = (aid.text or "").strip()
    return doc


def convert(stream, sink, watch=()):
    """Stream baseline XML into JSONL lines on ``sink``; return counts and hits on ``watch`` PMIDs."""
    counts = {"records": 0, "with_abstract": 0, "with_pmcid": 0, "with_mesh": 0, "deleted": 0, "text_chars": 0}
    hits = {}
    for _, el in ET.iterparse(stream, events=("end",)):
        if el.tag == "DeleteCitation":
            counts["deleted"] += len(el.findall("PMID"))
            el.clear()
            continue
        if el.tag != "PubmedArticle":
            continue
        doc = doc_of(el)
        el.clear()
        if doc is None:
            continue
        sink.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
        counts["records"] += 1
        counts["with_abstract"] += 1 if doc["abstract"] else 0
        counts["with_pmcid"] += 1 if doc["pmcid"] else 0
        counts["with_mesh"] += 1 if doc["mesh"] else 0
        counts["text_chars"] += len(doc["title"]) + len(doc["abstract"])
        if doc["pmid"] in watch:
            hits[doc["pmid"]] = {"title": doc["title"][:200], "year": doc["year"], "has_abstract": bool(doc["abstract"])}
    return counts, hits


def paths(data, n):
    docs = os.path.join(data, "docs")
    return (os.path.join(docs, "pubmed27n%04d.jsonl.gz" % n),
            os.path.join(docs, "manifest", "%04d.json" % n))


def work(task):
    """Download, check and convert one baseline file. Returns its manifest (or a skip/error note)."""
    n, data, deadline, watch = task
    out_path, man_path = paths(data, n)
    if os.path.exists(man_path):
        with open(man_path, encoding="utf-8") as f:
            return json.load(f)
    if time.time() > deadline:
        return {"file": n, "status": "not_started"}
    os.makedirs(os.path.dirname(man_path), exist_ok=True)
    if shutil.disk_usage(data).free < MIN_FREE_BYTES:
        return {"file": n, "status": "not_started", "note": "disk below 5 GB free"}
    t0 = time.time()
    url = FTP % n
    try:
        raw = fetch(url)
    except Exception as err:
        return {"file": n, "status": "download_error", "error": repr(err)}
    try:  # the checksum is optional: a missing .md5 must not cost the file
        want = md5_of(fetch(url + ".md5", timeout=60, tries=2).decode("ascii", "replace"))
    except Exception:
        want = ""
    got = hashlib.md5(raw).hexdigest()
    if want and want != got:
        return {"file": n, "status": "md5_mismatch", "want": want, "got": got}
    try:
        with gzip.open(out_path + ".part", "wt", encoding="utf-8", compresslevel=6) as sink:
            counts, hits = convert(gzip.GzipFile(fileobj=io.BytesIO(raw)), sink, set(watch))
    except Exception as err:
        return {"file": n, "status": "parse_error", "error": repr(err)}
    os.replace(out_path + ".part", out_path)
    manifest = {"file": n, "status": "done", "url": url, "md5": got, "md5_checked": bool(want),
                "gz_bytes": len(raw), "out_bytes": os.path.getsize(out_path),
                "seconds": round(time.time() - t0, 1), "counts": counts, "devset_hits": hits}
    with open(man_path + ".part", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    os.replace(man_path + ".part", man_path)
    return manifest


def load_devset(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def summarize(manifests, devset):
    done = [m for m in manifests if m.get("status") == "done"]
    totals = {}
    for m in done:
        for key, value in m["counts"].items():
            totals[key] = totals.get(key, 0) + value
    hits = {}
    for m in done:
        for pmid, info in m.get("devset_hits", {}).items():
            hits[pmid] = dict(info, file=m["file"])
    found = [q["info_need_id"] for q in devset if q["pmid"] in hits]
    statuses = {}
    for m in manifests:
        statuses[m.get("status", "?")] = statuses.get(m.get("status", "?"), 0) + 1
    return {"files_done": len(done), "statuses": statuses, "totals": totals,
            "gz_bytes_in": sum(m["gz_bytes"] for m in done), "jsonl_gz_bytes_out": sum(m["out_bytes"] for m in done),
            "devset": {"questions": len(devset), "answer_found": len(found),
                       "missing": [q["info_need_id"] + " " + q["pmid"] for q in devset if q["pmid"] not in hits],
                       "hits": hits},
            "problems": [m for m in manifests if m.get("status") not in ("done", "not_started")]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="out")
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=1306)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget-minutes", type=float, default=160)
    ap.add_argument("--devset", default="devset_landmark_v1.jsonl")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.data, exist_ok=True)
    devset = load_devset(args.devset)
    watch = sorted({q["pmid"] for q in devset})
    started = time.time()
    deadline = started + args.budget_minutes * 60
    tasks = [(n, args.data, deadline, watch) for n in range(args.first, args.last + 1)]
    manifests = []
    with Pool(args.workers) as pool:
        for m in pool.imap_unordered(work, tasks):
            manifests.append(m)
            if m.get("status") == "done" and len(manifests) % 25 == 0:
                print(f"{len(manifests)}/{len(tasks)} files handled, {round((time.time() - started) / 60, 1)} min",
                      file=sys.stderr, flush=True)
    manifests.sort(key=lambda m: m["file"])
    report = summarize(manifests, devset)
    report["minutes_this_run"] = round((time.time() - started) / 60, 1)
    report["range"] = [args.first, args.last]
    report["data_free_gb"] = round(shutil.disk_usage(args.data).free / 1024 ** 3, 1)
    with open(os.path.join(args.out, "extract.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    brief = {k: report[k] for k in ("files_done", "statuses", "totals", "gz_bytes_in", "jsonl_gz_bytes_out",
                                    "minutes_this_run", "data_free_gb")}
    brief["devset_answer_found"] = report["devset"]["answer_found"]
    brief["devset_missing"] = report["devset"]["missing"]
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
