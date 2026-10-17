#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""tar_bench: screening-prioritisation benchmark on CLEF TAR 2018 Task 2 (30 DTA reviews).

Pre-registration: findings/clef-tar-2018-bm25-prereg-v1-2026-10-17.md.

For each of the 30 Cochrane diagnostic-test-accuracy review topics, the
candidate records found by the review's Boolean search are ranked by BM25 over
PubMed title + abstract, and the ranking is scored with the formulas of CLEF's
own evaluator (scripts/tar_eval.py and measures/eval_measures.py in
github.com/CLEF-TAR/tar): AP, last_rel, WSS@95, WSS@100, norm_area, plus
recall at 1/5/10/20% of the list. Abstract-level qrels are primary,
content-level qrels secondary.

Variants:
  bool               terms of the Boolean query, field tags stripped, wildcards removed
  bool_title         bool plus the review title's terms
  bool_title_prefix  bool_title, but truncated query words match as prefixes
  title              title terms only (reference)
  random             a fixed pseudo-random order (reference)

Exploratory: how many records in the qrels PubMed now marks as retracted.

Standard library only. Usage: python tar_bench.py --out-dir /out --cache-dir /data
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CLEF = "https://raw.githubusercontent.com/CLEF-TAR/tar/{sha}/2018-TAR/Task2/Testing/"
CLEF_API = "https://api.github.com/repos/CLEF-TAR/tar/commits/master"
CLEF_PINNED = "dbc13d0"
UA = "mv2-tar-bench/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
TOPICS = ("CD008122 CD008587 CD008759 CD008892 CD009175 CD009263 CD009694 CD010213 CD010296 CD010502 "
          "CD010657 CD010680 CD010864 CD011053 CD011126 CD011420 CD011431 CD011515 CD011602 CD011686 "
          "CD011912 CD011926 CD012009 CD012010 CD012083 CD012165 CD012179 CD012216 CD012281 CD012599").split()
QRELS = {"abs": "qrels/full.test.abs.2018.qrels", "content": "qrels/full.test.content.2018.qrels"}
VARIANTS = ("bool", "bool_title", "bool_title_prefix", "title", "random")
K1, B = 1.2, 0.75
SEED = "20261017"
RECALL_AT = (1, 5, 10, 20)
# Published target (Wang et al., SIGIR-AP 2023, arXiv 2309.05238, Table 2, CLEF-2018, Boolean + BM25).
WANG_BM25 = {"ap": 0.154, "last_rel": 6033.067, "r1": 0.082, "r5": 0.242, "r10": 0.391, "r20": 0.563,
             "wss_95": 0.361, "wss_100": 0.264}
EFETCH_BATCH = 200
EFETCH_SPLIT = 20
EFETCH_MAX_FAILED_BATCHES = 10
VOID_SHARE = 0.01

STOP = frozenset("""a an and are as at be by for from in into is it its not of on or the to with without
adj exp limit near next same ed""".split())
WILDCARD = "*$:?#"
FIELD_SUFFIX = re.compile(r"\.[a-z]{2,3}(?:,[a-z]{2,3})*\.?(?=[\s)]|$)")
FLOATING_SUB = re.compile(r"\b[a-z]{2}\.fs\.?")
SUBHEADING = re.compile(r"/[a-z]{2}\b")
BRACKETS = re.compile(r"\[[^\]]*\]")
QTOKEN = re.compile(r"([a-z0-9]+)([*$:?#]\d*)?")
TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return [t for t in TOKEN.findall((text or "").lower()) if t not in STOP and not t.isdigit()]


def parse_topic(text):
    """{"topic", "title", "query_lines", "pids"} from a CLEF TAR topic file."""
    out = {"topic": "", "title": "", "query_lines": [], "pids": []}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Topic:"):
            out["topic"], section = line[6:].strip(), None
        elif line.startswith("Title:"):
            out["title"], section = line[6:].strip(), None
        elif line.startswith("Query:"):
            section = "query"
            if line[6:].strip():
                out["query_lines"].append(line[6:].strip())
        elif line.startswith("Pids:"):
            section = "pids"
        elif line and section == "query":
            out["query_lines"].append(line)
        elif line and section == "pids":
            out["pids"].extend(p for p in line.split() if p.isdigit())
    return out


def query_terms(lines, prefix=False):
    """(terms, prefixes) from Ovid-style query lines, in order of first appearance.

    Lines that only combine earlier lines ("1 or 2", "or/1-41") or start with "limit"
    give nothing. Field tags (.ti,ab. .mp.), floating subheadings (di.fs.), subheadings
    (/di), bracketed notes and the operators are dropped, as are pure numbers. With
    prefix=False a truncated word (sensitiv:, zeugmatogra*) is kept as the literal stem;
    with prefix=True it becomes a prefix, and exact terms a prefix already covers are dropped.
    """
    terms, prefixes = [], []
    for raw in lines:
        line = raw.lower().strip()
        if line.startswith("limit"):
            continue
        line = BRACKETS.sub(" ", line)
        line = FLOATING_SUB.sub(" ", line)
        line = FIELD_SUFFIX.sub(" ", line)
        line = SUBHEADING.sub(" ", line)
        for word, wild in QTOKEN.findall(line):
            if word in STOP or word.isdigit() or re.fullmatch(r"adj\d*", word):
                continue
            target = prefixes if (prefix and wild) else terms
            if word not in target:
                target.append(word)
    if prefix:
        terms = [t for t in terms if not any(t.startswith(p) for p in prefixes)]
    return terms, prefixes


def tie_key(topic, pmid, salt=""):
    return hashlib.md5(f"{salt}{topic}:{pmid}".encode()).hexdigest()


def bm25_rank(topic, docs, terms, prefixes=(), k1=K1, b=B):
    """[(pmid, score)] best first. docs: {pmid: [tokens]}. Ties are broken by a fixed hash.

    Each prefix acts as one term: its tf is the summed tf of the document's words that
    start with it, its df the number of documents with any such word.
    idf = ln(1 + (N - df + 0.5) / (df + 0.5)) (Lucene form).
    """
    pmids = sorted(docs)
    n = len(pmids)
    if not n:
        return []
    keys = list(dict.fromkeys(list(terms) + ["\x00" + p for p in prefixes]))
    vocab_map = {}
    if prefixes:
        vocab = {t for p in pmids for t in docs[p]}
        for t in vocab:
            for p in prefixes:
                if t.startswith(p):
                    vocab_map.setdefault(t, []).append("\x00" + p)
    wanted = set(terms)
    tfs, lens, df = {}, {}, {}
    for p in pmids:
        c = {}
        for t in docs[p]:
            if t in wanted:
                c[t] = c.get(t, 0) + 1
            for k in vocab_map.get(t, ()):
                c[k] = c.get(k, 0) + 1
        tfs[p], lens[p] = c, len(docs[p])
        for k in c:
            df[k] = df.get(k, 0) + 1
    avgdl = sum(lens.values()) / n or 1.0
    idf = {k: math.log(1 + (n - df.get(k, 0) + 0.5) / (df.get(k, 0) + 0.5)) for k in keys}
    scored = []
    for p in pmids:
        s, norm = 0.0, k1 * (1 - b + b * lens[p] / avgdl)
        for k, tf in tfs[p].items():
            s += idf[k] * tf * (k1 + 1) / (tf + norm)
        scored.append((p, s))
    scored.sort(key=lambda x: (-x[1], tie_key(topic, x[0])))
    return scored


def random_rank(topic, pmids):
    return [(p, 0.0) for p in sorted(pmids, key=lambda p: tie_key(topic, p, SEED))]


def parse_qrels(text):
    """({topic: {pmid: value}}, duplicates). The first line for a (topic, pmid) is kept."""
    out, dups = {}, 0
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        topic, _, pmid, val = parts
        d = out.setdefault(topic, {})
        if pmid in d:
            dups += 1
            continue
        d[pmid] = int(val)
    return out, dups


def judged(qrels_topic):
    """The documents tar_eval counts in N: values 0, 1 and 2 (-1 and >2 are left out)."""
    return {p: v for p, v in qrels_topic.items() if 0 <= v <= 2}


def measures(ranking, qrels_topic):
    """tar_eval's measures for a full ranking of the judged documents.

    ranking: pmids best first. Relevant means value 1 or 2. N is the number of
    judged documents (or the number ranked, if larger, as in tar_eval).
    """
    rel = {p for p, v in qrels_topic.items() if v in (1, 2)}
    r = len(rel)
    n = max(len(judged(qrels_topic)), len(ranking))
    if not r or not n:
        return None
    target95 = round(float(r) * 0.95)
    found, last_rel, last_rel_95, ap, area, cg = 0, 0, 0, 0.0, 0.0, 0
    hits_at = []
    for rank, p in enumerate(ranking, 1):
        v = 1 if p in rel else 0
        if v:
            if found < target95:
                last_rel_95 = rank
            found += 1
            last_rel = rank
            ap += found / rank
        area += cg + 0.5 * v
        cg += v
        hits_at.append(found)
    area += (n - len(ranking)) * cg
    max_area = r * n - (r * r) / 2.0
    out = {"n": n, "r": r, "ap": ap / r, "last_rel": last_rel,
           "wss_100": (n - last_rel) / n if found >= r else 0,
           "wss_95": (n - last_rel_95) / n - 0.05 if found >= target95 else 0,
           "norm_area": round(area / max_area, 3) if max_area > 0 else 0.0}
    for x in RECALL_AT:
        k = min(max(1, math.ceil(x * n / 100)), len(hits_at))
        out[f"r{x}"] = hits_at[k - 1] / r if hits_at else 0.0
    return out


def mean_of(per_topic, keys=("ap", "last_rel", "wss_95", "wss_100", "norm_area", "r1", "r5", "r10", "r20")):
    rows = [m for m in per_topic.values() if m]
    return {k: round(sum(m[k] for m in rows) / len(rows), 4) for k in keys} if rows else {}


def verdicts(abs_results):
    """H1: bool reproduces Wang's BM25 row (AP within 0.04 and WSS@95 within 0.06).
    H2: bool_title_prefix beats bool on AP in at least 20 of the 30 topics."""
    a = abs_results.get("bool", {})
    ma = a.get("mean", {})
    if len(a.get("topics", {})) < 30:
        h1 = "untestable"
    else:
        h1 = ("supported" if abs(ma["ap"] - WANG_BM25["ap"]) <= 0.04
              and abs(ma["wss_95"] - WANG_BM25["wss_95"]) <= 0.06 else "not supported")
    c = abs_results.get("bool_title_prefix", {}).get("topics", {})
    pairs = [(c[t]["ap"], a["topics"][t]["ap"]) for t in c if c[t] and a.get("topics", {}).get(t)]
    wins = sum(1 for x, y in pairs if x > y)
    h2 = "untestable" if len(pairs) < 30 else ("supported" if wins >= 20 else "not supported")
    return {"H1": h1, "H2": h2, "H2_wins": wins, "H2_pairs": len(pairs)}


# ---- PubMed ----

def _text(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def parse_efetch(data):
    """{pmid: {"title", "abstract", "pubtypes", "retracted"}} from PubMed efetch XML."""
    out = {}
    for art in ET.fromstring(data).iter("PubmedArticle"):
        mc = art.find("MedlineCitation")
        a = mc.find("Article")
        pmid = (mc.findtext("PMID") or "").strip()
        title = _text(a.find("ArticleTitle")) if a is not None else ""
        abstract = " ".join(_text(x) for x in a.findall("Abstract/AbstractText")) if a is not None else ""
        pubtypes = [p.text or "" for p in a.findall("PublicationTypeList/PublicationType")] if a is not None else []
        retraction_in = any(c.get("RefType") == "RetractionIn"
                            for c in mc.findall("CommentsCorrectionsList/CommentsCorrections"))
        out[pmid] = {"title": title, "abstract": abstract, "pubtypes": pubtypes,
                     "retracted": "Retracted Publication" in pubtypes or retraction_in}
    return out


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


def _efetch_post(body):
    try:
        return http(EUTILS + "efetch.fcgi", body, tries=5, retry_400=True)
    finally:
        time.sleep(0.4)  # stay under 3 requests per second without an API key


def efetch_docs(pmids, errors=None, fetch=None, batch=EFETCH_BATCH, split=EFETCH_SPLIT,
                max_failed=EFETCH_MAX_FAILED_BATCHES):
    """{pmid: doc}. A failing batch is re-tried in pieces of `split`; pieces that still fail
    are logged in errors as {"efetch_failed": [...], "error": ...}. After max_failed failed
    pieces the rest is logged as skipped without fetching."""
    fetch = fetch or _efetch_post
    errors = [] if errors is None else errors
    out, state = {}, {"failed": 0}

    def one(chunk, may_split):
        if state["failed"] >= max_failed:
            errors.append({"efetch_failed": list(chunk), "error": "skipped after repeated failures"})
            return
        body = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk), "retmode": "xml",
                                       "tool": "mv2-tar-bench", "email": "mv2@munimtech.com"}).encode()
        try:
            got = parse_efetch(fetch(body))
        except Exception as e:
            if may_split and len(chunk) > split:
                for j in range(0, len(chunk), split):
                    one(chunk[j:j + split], False)
            else:
                state["failed"] += 1
                errors.append({"efetch_failed": list(chunk), "error": repr(e)[:300]})
            return
        out.update(got)

    for i in range(0, len(pmids), batch):
        one(pmids[i:i + batch], True)
    return out


def failed_count(errors):
    return sum(len(e["efetch_failed"]) for e in errors if "efetch_failed" in e)


def load_cache(path):
    out = {}
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                out[d.pop("pmid")] = d
    return out


def save_cache(path, docs):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for p in sorted(docs, key=int):
            f.write(json.dumps(dict(pmid=p, **docs[p]), ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def write_run(path, topic_rankings, tag):
    """TREC run lines for tar_eval: topic NF pmid rank score tag."""
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for topic, ranked in topic_rankings:
            for i, (p, s) in enumerate(ranked, 1):
                f.write(f"{topic} NF {p} {i} {s:.6f} {tag}\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--cache-dir", default="/data")
    ap.add_argument("--max-topics", type=int, default=0, help="for smoke tests only")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, "runs"), exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    t0, errors = time.time(), []

    # The shared sandbox often exhausts GitHub's unauthenticated API allowance, so the
    # commit is resolved for the record only; files come from master either way.
    try:
        sha = json.loads(http(CLEF_API, tries=2))["sha"]
    except Exception as e:
        sha, errors = "", errors + [{"clef_sha": repr(e)[:200]}]
    base = CLEF.format(sha=sha or "master")
    topics = TOPICS[:args.max_topics] if args.max_topics else TOPICS
    tdata = {t: parse_topic(http(base + "topics/" + t).decode("utf-8", "replace")) for t in topics}
    qrels, dups = {}, {}
    for level, path in QRELS.items():
        qrels[level], dups[level] = parse_qrels(http(base + path).decode("utf-8", "replace"))

    needed = sorted({p for t in topics for p in qrels["abs"].get(t, {})}, key=int)
    cache_path = os.path.join(args.cache_dir, "clef2018_pubmed.jsonl.gz")
    docs = load_cache(cache_path)
    cached = len([p for p in needed if p in docs])
    missing = [p for p in needed if p not in docs]
    fetch_errors = []
    docs.update(efetch_docs(missing, fetch_errors))
    save_cache(cache_path, docs)
    errors += fetch_errors
    records_failed = failed_count(fetch_errors)
    failed_set = {p for e in fetch_errors for p in e.get("efetch_failed", [])}
    absent = [p for p in needed if p not in docs and p not in failed_set]

    results = {level: {v: {"topics": {}} for v in VARIANTS} for level in QRELS}
    topic_stats, retracted = {}, []
    for t in topics:
        cand = sorted(judged(qrels["abs"].get(t, {})), key=int)
        tokens = {}  # per topic, to keep memory down
        for p in cand:
            d = docs.get(p, {})
            tokens[p] = [sys.intern(x) for x in tokenize(d.get("title", "") + " " + d.get("abstract", ""))]
        tdocs = tokens
        title_terms = list(dict.fromkeys(tokenize(tdata[t]["title"])))
        b_terms, _ = query_terms(tdata[t]["query_lines"])
        p_terms, p_prefixes = query_terms(tdata[t]["query_lines"], prefix=True)
        bt = list(dict.fromkeys(b_terms + title_terms))
        btp = list(dict.fromkeys(p_terms + [x for x in title_terms
                                            if not any(x.startswith(p) for p in p_prefixes)]))
        ranked = {"bool": bm25_rank(t, tdocs, b_terms), "bool_title": bm25_rank(t, tdocs, bt),
                  "bool_title_prefix": bm25_rank(t, tdocs, btp, p_prefixes),
                  "title": bm25_rank(t, tdocs, title_terms), "random": random_rank(t, cand)}
        for v, rk in ranked.items():
            order = [p for p, _ in rk]
            for level in QRELS:
                results[level][v]["topics"][t] = measures(order, judged(qrels[level].get(t, {})))
            results["abs"][v].setdefault("_rankings", []).append((t, rk))
        rel_abs = [p for p, x in qrels["abs"].get(t, {}).items() if x in (1, 2)]
        topic_stats[t] = {"title": tdata[t]["title"], "n": len(cand), "topic_file_pids": len(tdata[t]["pids"]),
                          "rel_abs": len(rel_abs),
                          "rel_content": sum(1 for x in qrels["content"].get(t, {}).values() if x in (1, 2)),
                          "no_text": sum(1 for p in cand if not tokens[p]),
                          "no_abstract": sum(1 for p in cand if p in docs and not docs[p].get("abstract")),
                          "n_terms": {"bool": len(b_terms), "bool_title": len(bt),
                                      "bool_title_prefix": [len(p_terms), len(p_prefixes)]}}
        for p in cand:
            if docs.get(p, {}).get("retracted"):
                retracted.append({"topic": t, "pmid": p, "rel_abs": qrels["abs"][t].get(p),
                                  "rel_content": qrels["content"].get(t, {}).get(p),
                                  "title": docs[p]["title"][:200], "pubtypes": docs[p]["pubtypes"]})
    for v in VARIANTS:
        write_run(os.path.join(args.out_dir, "runs", f"{v}.res.gz"), results["abs"][v].pop("_rankings"), f"mv2-{v}")
    for level in QRELS:
        for v in VARIANTS:
            results[level][v]["mean"] = mean_of(results[level][v]["topics"])
            results[level][v]["topics_scored"] = sum(1 for m in results[level][v]["topics"].values() if m)

    out = {
        "prereg": "findings/clef-tar-2018-bm25-prereg-v1-2026-10-17.md",
        "clef_sha": sha, "clef_sha_matches_pinned": sha.startswith(CLEF_PINNED),
        "bm25": {"k1": K1, "b": B}, "topics": len(topics), "qrels_duplicates": dups,
        "pmids_needed": len(needed), "pmids_from_cache": cached, "records_failed": records_failed,
        "pmids_absent_from_pubmed": len(absent), "absent_sample": absent[:50],
        "void": records_failed > VOID_SHARE * max(len(needed), 1),
        "wang_2023_bm25": WANG_BM25,
        "mean_abs": {v: results["abs"][v]["mean"] for v in VARIANTS},
        "mean_content": {v: results["content"][v]["mean"] for v in VARIANTS},
        "hypotheses": verdicts(results["abs"]),
        "retracted_records": len(retracted),
        "retracted_relevant_abs": sum(1 for r in retracted if r["rel_abs"] in (1, 2)),
        "retracted_relevant_content": sum(1 for r in retracted if r["rel_content"] in (1, 2)),
        "topic_stats": topic_stats, "per_topic": results,
        "errors": errors[:200], "n_errors": len(errors), "minutes": round((time.time() - t0) / 60, 1),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(args.out_dir, "retracted.jsonl"), "w", encoding="utf-8") as f:
        for r in retracted:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("clef_sha", "pmids_needed", "records_failed", "pmids_absent_from_pubmed",
                                           "void", "mean_abs", "hypotheses", "retracted_records",
                                           "retracted_relevant_abs", "n_errors", "minutes")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
