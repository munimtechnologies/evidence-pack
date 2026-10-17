#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""spark_eval: a small bench for NLM SPARK PubMed/PMC Task 1 (known-item retrieval).

The real task needs an index of all ~38M PubMed records. This bench fits in
2 GB of memory instead:

1. A sample corpus: --files evenly spaced files of the challenge's own PubMed
   baseline (about 30,000 records each), plus hard negatives (the top 20 of
   PubMed's own Best Match search for each dev question, in three query
   forms) and every dev answer, fetched with E-utilities. Preprints and
   records outside 1959-2026 are left out, as in the Challenge Corpus.
   Indexed with SQLite FTS5 (contentless, Porter stemming).
2. Ranking variants, all fixed before the first run: plain BM25, field-weighted
   BM25, then demoting non-primary publication types (reviews, letters,
   comments...), a citation-count prior (NIH iCite), an "earliest paper"
   prior when the question asks for a first or original paper, and a boost
   for a publication year named in the question. A grid around the last
   variant is reported too, and is labelled as tuned on the dev set.
3. A reference that needs no sample: PubMed's own Best Match ranking over all
   of PubMed, for the raw question, its keywords ANDed and its keywords ORed.

Scores are MRR@5 (the task's metric), hit@1, hit@5 and recall@100. The sample
has about 1/30 of the real distractors, so the sample-index scores are only
for comparing variants with each other, never a claim about the full task.

v2: each dev set gets its own hard negatives (so a second set can reuse the
v1 index), the citation prior's effect is reported per question, and the
answers' citation counts are summarized (prereg-devset-ordinary-v1.md).

v3: gated citation priors (prereg-cite-gate-v1.md): a smaller weight, the
prior only when the question has a priority cue, and the prior only for
near-ties in BM25 score. Each question records whether it has the cue.

Usage: python spark_eval.py --db /data/sample.db --out /out [--files 40]
"""
import argparse
import gzip
import io
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pm_extract as pm

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL = {"tool": "mv2-munim-spark-eval", "email": "mv2@munimtech.com"}
ICITE = "https://icite.od.nih.gov/api/pubs?pmids=%s&fl=pmid,citation_count"
LANDMARK_SET = "devset_landmark_v1.jsonl"

STOP = set("""
a an the of in on for to and or with without by from at as is are was were be been being that this these
those which what who whom whose when where why how it its into than then there their them they he she his
her we our you your i me my do does did done can could would should may might must will shall not no nor
only just also very more most less least such so any each other both either neither one two about after
before between during over under up down out off again later still far
paper papers study studies report reports reported article articles publication published work find
retrieve need want looking look show showed shown shows demonstrate demonstrated describe described
describing description introduce introduced introducing propose proposed proposing first original
landmark seminal classic standard citation famous key initial earliest which what use used using
""".split())
CUE = re.compile(r"\b(first|original|landmark|seminal|introduc\w*|discover\w*|pioneer\w*|earliest|initial)\b")
REVIEW_Q = re.compile(r"\b(review\w*|meta-analys\w*|systematic|commentary|editorial|letter|guideline\w*|statement)\b")
YEAR_Q = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
NONPRIMARY = {"Review", "Systematic Review", "Meta-Analysis", "Comment", "Letter", "Editorial",
              "Published Erratum", "Retraction of Publication", "News", "Newspaper Article", "Biography",
              "Historical Article", "Interview", "Portrait", "Lecture", "Introductory Journal Article"}
FIELDS = ("title", "abstract", "mesh", "authors", "journal")
POOL = 50

# fixed before the first run; the grid below is the only tuning
FW = (3, 1, 1, 1, 0.5)
METHODS = [
    ("bm25_flat", {"w": (1, 1, 1, 1, 1)}),
    ("bm25_fields", {"w": FW}),
    ("fields+ptype", {"w": FW, "demote": 0.6}),
    ("fields+ptype+cite", {"w": FW, "demote": 0.6, "beta": 0.3}),
    ("fields+ptype+cite+early", {"w": FW, "demote": 0.6, "beta": 0.3, "gamma": 0.2}),
    ("fields+ptype+cite+early+year", {"w": FW, "demote": 0.6, "beta": 0.3, "gamma": 0.2, "delta": 0.3}),
    # v3, fixed in prereg-cite-gate-v1.md before the landmark questions were re-read
    ("fields+ptype+cite0.1", {"w": FW, "demote": 0.6, "beta": 0.1}),
    ("fields+ptype+cite|cue", {"w": FW, "demote": 0.6, "beta": 0.3, "gate": "cue"}),
    ("fields+ptype+cite|band0.8", {"w": FW, "demote": 0.6, "beta": 0.3, "band": 0.8}),
    ("fields+ptype+cite|cue+early+year", {"w": FW, "demote": 0.6, "beta": 0.3, "gate": "cue", "gamma": 0.2,
                                          "delta": 0.3}),
]
GRID = [{"w": FW, "demote": 0.6, "beta": b, "gamma": g, "delta": d}
        for b in (0.0, 0.15, 0.3, 0.5) for g in (0.0, 0.1, 0.2, 0.4) for d in (0.0, 0.3)]
# the pre-registered primary comparison: the citation prior on top of fields+ptype
PRIMARY = ("fields+ptype", "fields+ptype+cite")
MISSES = "fields+ptype+cite|cue+early+year"


def terms(question):
    """Content words of a question, lower case, in order, without duplicates."""
    out = []
    for tok in re.findall(r"[a-z0-9]+", question.lower()):
        if tok in STOP or (len(tok) < 2 and not tok.isdigit()) or tok in out:
            continue
        out.append(tok)
    return out


def fts_query(words):
    return " OR ".join('"%s"' % w for w in words)


def rr(ranked, answer, k=5):
    """Reciprocal rank of answer within the first k items (0 if absent)."""
    for i, p in enumerate(ranked[:k]):
        if str(p) == str(answer):
            return 1.0 / (i + 1)
    return 0.0


def hard_negative_part(devset_path):
    """Build-table key for a dev set's hard negatives; v1's landmark set kept its original key."""
    name = os.path.basename(devset_path)
    return "hard-negatives" if name == LANDMARK_SET else "hard-negatives:" + name


def quartiles(values):
    """(q1, median, q3) of the non-None values by linear interpolation, or None if there are none."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None

    def at(f):
        x = f * (len(vals) - 1)
        lo = int(math.floor(x))
        hi = min(lo + 1, len(vals) - 1)
        return vals[lo] + (vals[hi] - vals[lo]) * (x - lo)
    return (at(0.25), at(0.5), at(0.75))


def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(title, abstract, mesh, authors, journal, "
               "content='', tokenize='porter unicode61 remove_diacritics 2')")
    db.execute("CREATE TABLE IF NOT EXISTS meta(pmid INTEGER PRIMARY KEY, year INTEGER, ptypes TEXT, "
               "title TEXT, source TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS built(part TEXT PRIMARY KEY, n INTEGER)")
    return db


def add(db, doc, source):
    """Index one record unless it is already in, a preprint, or outside 1959-2026."""
    pmid = int(doc["pmid"])
    year = doc.get("year")
    if "Preprint" in doc.get("ptypes", []) or (year and not 1959 <= year <= 2026):
        return False
    if db.execute("SELECT 1 FROM meta WHERE pmid=?", (pmid,)).fetchone():
        return False
    db.execute("INSERT INTO meta VALUES (?,?,?,?,?)",
               (pmid, year, "|".join(doc.get("ptypes", [])), doc.get("title", "")[:300], source))
    db.execute("INSERT INTO docs(rowid, title, abstract, mesh, authors, journal) VALUES (?,?,?,?,?,?)",
               (pmid, doc.get("title", ""), doc.get("abstract", ""),
                " ; ".join(doc.get("mesh", []) + doc.get("keywords", [])),
                " ; ".join(doc.get("authors", [])), doc.get("journal", "")))
    return True


def add_xml(db, stream, source):
    n = 0
    for _, el in ET.iterparse(stream, events=("end",)):
        if el.tag != "PubmedArticle":
            continue
        doc = pm.doc_of(el)
        el.clear()
        if doc and add(db, doc, source):
            n += 1
    return n


def sample_files(k, last):
    if k <= 1:
        return [1]
    return sorted({1 + round(i * (last - 1) / (k - 1)) for i in range(k)})


def eutil(name, params):
    time.sleep(0.4)  # NCBI asks for at most 3 requests a second without a key
    url = EUTILS + name + ".fcgi?" + urllib.parse.urlencode(dict(params, **TOOL))
    return pm.fetch(url, timeout=120, tries=3)


def esearch(term, retmax=20):
    data = json.loads(eutil("esearch", {"db": "pubmed", "term": term, "retmax": retmax, "sort": "relevance",
                                        "retmode": "json"}))
    return (data.get("esearchresult") or {}).get("idlist") or []


def efetch_into(db, pmids, source, log):
    n = 0
    ids = sorted({str(p) for p in pmids})
    for i in range(0, len(ids), 200):
        batch = ids[i:i + 200]
        try:
            raw = eutil("efetch", {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"})
            n += add_xml(db, io.BytesIO(raw), source)
        except Exception as err:  # report and go on
            log.append(f"efetch {source} batch {i}: {err!r}")
    db.commit()
    return n


def citations(pmids, log):
    out = {}
    ids = sorted({int(p) for p in pmids})
    for i in range(0, len(ids), 200):
        batch = ids[i:i + 200]
        try:
            data = json.loads(pm.fetch(ICITE % ",".join(map(str, batch)), timeout=120, tries=3))
            for row in data.get("data", []):
                out[int(row["pmid"])] = row.get("citation_count") or 0
        except Exception as err:
            log.append(f"icite batch {i}: {err!r}")
        time.sleep(0.2)
    return out


def search(db, question, weights, limit=100):
    words = terms(question)
    if not words:
        return []
    w = ", ".join("%g" % x for x in weights)
    rows = db.execute(f"SELECT rowid, bm25(docs, {w}) AS s FROM docs WHERE docs MATCH ? ORDER BY s LIMIT ?",
                      (fts_query(words), limit)).fetchall()
    return [(int(p), -s) for p, s in rows]  # FTS5 bm25 is negative; flip so bigger is better


def rerank(cands, meta, cites, question, demote=1.0, beta=0.0, gamma=0.0, delta=0.0, gate=None, band=None):
    """Re-order the first POOL candidates; meta maps pmid -> (year, ptypes).

    gate="cue" applies the citation prior only to questions with a priority cue;
    band=b applies it only to candidates scoring at least b times the top BM25 score.
    """
    pool = cands[:POOL]
    if not pool:
        return []
    top = pool[0][1] or 1.0
    q = question.lower()
    cmax = max(math.log1p(cites.get(p, 0)) for p, _ in pool) or 1.0
    years = [meta[p][0] for p, _ in pool[:20] if meta.get(p, (None,))[0]]
    ymin, ymax = (min(years), max(years)) if years else (0, 0)
    cue = bool(CUE.search(q))
    qyears = [int(y) for y in YEAR_Q.findall(q)]
    review_ok = bool(REVIEW_Q.search(q))
    if gate == "cue" and not cue:
        beta = 0.0
    scored = []
    for p, s in pool:
        year, ptypes = meta.get(p, (None, ""))
        x = s / top
        near = band is None or x >= band
        if demote < 1 and not review_ok and NONPRIMARY & set(ptypes.split("|")):
            x *= demote
        if beta and near:
            x += beta * math.log1p(cites.get(p, 0)) / cmax
        if gamma and cue and year and ymax > ymin:
            x += gamma * min(1.0, max(0.0, (ymax - year) / (ymax - ymin)))
        if delta and qyears and year and any(abs(year - y) <= 1 for y in qyears):
            x += delta
        scored.append((-x, p))
    scored.sort()
    return [p for _, p in scored]


def summarize(rows, key):
    """MRR@5, hit@1, hit@5 (and recall@100 if present) over rows[i][key]."""
    vals = [r[key] for r in rows]
    n = len(vals) or 1
    out = {"n": len(vals), "mrr5": round(sum(v["rr"] for v in vals) / n, 4),
           "hit1": round(sum(1 for v in vals if v["rr"] == 1.0) / n, 4),
           "hit5": round(sum(1 for v in vals if v["rr"] > 0) / n, 4)}
    if vals and "in100" in vals[0]:
        out["recall100"] = round(sum(1 for v in vals if v["in100"]) / n, 4)
    return out


def by_kind(rows, key):
    kinds = sorted({r["kind"] for r in rows})
    return {k: summarize([r for r in rows if r["kind"] == k], key) for k in kinds}


def compare(rows, base, alt):
    """Per-question effect of switching from method base to method alt."""
    diffs = [r[alt]["rr"] - r[base]["rr"] for r in rows]
    n = len(diffs) or 1
    return {"base": base, "alt": alt, "delta_mrr5": round(sum(diffs) / n, 4),
            "helped": sum(1 for d in diffs if d > 1e-9), "hurt": sum(1 for d in diffs if d < -1e-9),
            "same": sum(1 for d in diffs if abs(d) <= 1e-9),
            "hurt_ids": [r["id"] for r, d in zip(rows, diffs) if d < -1e-9]}


def build(db, args, devset, log):
    t0 = time.time()
    files = sample_files(args.files, args.last)
    for n in files:
        part = "baseline:%d" % n
        if db.execute("SELECT 1 FROM built WHERE part=?", (part,)).fetchone():
            continue
        try:
            raw = pm.fetch(pm.FTP % n)
            cnt = add_xml(db, gzip.GzipFile(fileobj=io.BytesIO(raw)), part)
        except Exception as err:
            log.append(f"{part}: {err!r}")
            db.rollback()
            continue
        db.execute("INSERT INTO built VALUES (?,?)", (part, cnt))
        db.commit()
        print(f"{part}: {cnt} records, {round((time.time() - t0) / 60, 1)} min", file=sys.stderr, flush=True)
    pubmed = {}
    for q in devset:
        forms = {"raw": q["info_need"], "kw_and": " ".join(terms(q["info_need"])),
                 "kw_or": " OR ".join(terms(q["info_need"]))}
        pubmed[q["info_need_id"]] = {}
        for form, term in forms.items():
            try:
                pubmed[q["info_need_id"]][form] = esearch(term)
            except Exception as err:
                log.append(f"esearch {q['info_need_id']} {form}: {err!r}")
                pubmed[q["info_need_id"]][form] = None
    part = hard_negative_part(args.devset)
    if not db.execute("SELECT 1 FROM built WHERE part=?", (part,)).fetchone():
        hard = {p for forms in pubmed.values() for ids in forms.values() if ids for p in ids}
        n_hard = efetch_into(db, hard, "pubmed-top20", log)
        n_ans = efetch_into(db, [q["pmid"] for q in devset], "answer", log)
        db.execute("INSERT INTO built VALUES (?, ?)", (part, n_hard + n_ans))
        db.commit()
    return files, pubmed, round((time.time() - t0) / 60, 1)


def evaluate(db, devset, pubmed, log):
    cands = {}
    for name, cfg in METHODS[:2]:
        cands[name] = {q["info_need_id"]: search(db, q["info_need"], cfg["w"]) for q in devset}
    pool_ids = {p for name in cands for lst in cands[name].values() for p, _ in lst[:POOL]}
    pool_ids |= {int(q["pmid"]) for q in devset}
    meta = {}
    for p in pool_ids:
        row = db.execute("SELECT year, ptypes FROM meta WHERE pmid=?", (p,)).fetchone()
        if row:
            meta[p] = (row[0], row[1] or "")
    cites = citations(pool_ids, log)
    rows = []
    for q in devset:
        qid, ans = q["info_need_id"], int(q["pmid"])
        row = {"id": qid, "kind": q["kind"], "answer": ans, "answer_indexed": ans in meta,
               "answer_citations": cites.get(ans), "terms": terms(q["info_need"]),
               "cue": bool(CUE.search(q["info_need"].lower()))}
        for name, cfg in METHODS:
            base = cands["bm25_flat" if cfg["w"] == METHODS[0][1]["w"] else "bm25_fields"][qid]
            extra = {k: v for k, v in cfg.items() if k != "w"}
            ranked = rerank(base, meta, cites, q["info_need"], **extra) if extra else [p for p, _ in base]
            row[name] = {"rr": rr(ranked, ans), "in100": ans in {p for p, _ in base},
                         "rank": ranked.index(ans) + 1 if ans in ranked else None, "top3": ranked[:3],
                         "top1_citations": cites.get(ranked[0]) if ranked else None}
        for i, cfg in enumerate(GRID):
            extra = {k: v for k, v in cfg.items() if k != "w"}
            row["grid%d" % i] = {"rr": rr(rerank(cands["bm25_fields"][qid], meta, cites, q["info_need"], **extra), ans)}
        for form, ids in (pubmed.get(qid) or {}).items():
            row["pubmed_" + form] = {"rr": rr(ids or [], ans), "returned": len(ids or []),
                                     "failed": ids is None}
        rows.append(row)
    return rows, meta, cites


def titles(db, pmids):
    out = {}
    for p in pmids:
        row = db.execute("SELECT title, year FROM meta WHERE pmid=?", (p,)).fetchone()
        out[p] = f"{row[1]} {row[0][:90]}" if row else "?"
    return out


def report(db, rows, files, minutes, log, out_dir, devset_name):
    n_docs = db.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
    sources = dict(db.execute("SELECT CASE WHEN source LIKE 'baseline:%' THEN 'baseline' ELSE source END AS s, "
                              "COUNT(*) FROM meta GROUP BY s").fetchall())
    methods = {name: dict(summarize(rows, name), by_kind=by_kind(rows, name)) for name, _ in METHODS}
    pubmed = {}
    for form in ("raw", "kw_and", "kw_or"):
        key = "pubmed_" + form
        if rows and key in rows[0]:
            pubmed[form] = dict(summarize(rows, key),
                                zero_results=sum(1 for r in rows if r[key]["returned"] == 0),
                                failed=sum(1 for r in rows if r[key]["failed"]), by_kind=by_kind(rows, key))
    grid = sorted(({"params": {k: v for k, v in cfg.items() if k != "w"}, **summarize(rows, "grid%d" % i)}
                   for i, cfg in enumerate(GRID)), key=lambda g: -g["mrr5"])
    primary = compare(rows, *PRIMARY)
    vs_ptype = {name: compare(rows, "fields+ptype", name) for name, _ in METHODS[3:]}
    cite_q = quartiles([r["answer_citations"] for r in rows])
    top1_q = quartiles([r[PRIMARY[1]]["top1_citations"] for r in rows if r[PRIMARY[1]]["rr"] < 1])
    result = {"devset": devset_name, "corpus": {"documents": n_docs, "by_source": sources, "baseline_files": files,
                                                "build_minutes": minutes},
              "answers_indexed": sum(1 for r in rows if r["answer_indexed"]),
              "cue_questions": sum(1 for r in rows if r["cue"]),
              "methods": methods, "primary": primary, "vs_fields_ptype": vs_ptype,
              "answer_citations_q1_median_q3": cite_q, "wrong_top1_citations_q1_median_q3": top1_q,
              "pubmed_best_match_full_corpus": pubmed, "grid_tuned_on_dev": grid, "log": log}
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    with open(os.path.join(out_dir, "per_question.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("grid")}) + "\n")
    lines = [f"# SPARK Task 1 sample bench (dev set: {devset_name}, {len(rows)} known-item questions)", "",
             f"Sample index: {n_docs} records ({sources}); {len(files)} baseline files. "
             f"Answers indexed: {result['answers_indexed']}/{len(rows)}. "
             f"Questions with a priority cue: {result['cue_questions']}.", "",
             "The sample holds about 1/30 of the real distractors, so its scores compare variants with each "
             "other only. PubMed Best Match rows rank all of PubMed.", "",
             "| system | MRR@5 | hit@1 | hit@5 | recall@100 |", "|---|---|---|---|---|"]
    for name, m in methods.items():
        lines.append(f"| sample: {name} | {m['mrr5']:.3f} | {m['hit1']:.3f} | {m['hit5']:.3f} | "
                     f"{m.get('recall100', 0):.3f} |")
    for form, m in pubmed.items():
        lines.append(f"| PubMed Best Match, {form} (all of PubMed; {m['zero_results']} queries returned nothing) | "
                     f"{m['mrr5']:.3f} | {m['hit1']:.3f} | {m['hit5']:.3f} | |")
    lines += ["", "## Against fields+ptype", ""]
    for name, c in vs_ptype.items():
        lines.append(f"- {name}: MRR@5 {c['delta_mrr5']:+.4f}; helped {c['helped']}, hurt {c['hurt']}"
                     f" ({', '.join(c['hurt_ids']) or 'none'})")
    lines += ["", f"Answer citation counts (q1, median, q3): {cite_q}. Citation counts of the wrong top-1 "
              f"under {primary['alt']} (q1, median, q3): {top1_q}."]
    lines += ["", "Best grid settings (tuned on this dev set, so optimistic):", ""]
    for g in grid[:5]:
        lines.append(f"- {g['params']}: MRR@5 {g['mrr5']:.3f}, hit@1 {g['hit1']:.3f}")
    lines += ["", f"## Misses of {MISSES}", ""]
    for r in rows:
        if r[MISSES]["rr"] < 1:
            t = titles(db, [r["answer"]] + r[MISSES]["top3"])
            lines.append(f"- {r['id']} ({r['kind']}): answer {r['answer']} ({t[r['answer']]}) at rank "
                         f"{r[MISSES]['rank']}; top: " + " | ".join(f"{p} {t[p]}" for p in r[MISSES]["top3"]))
    if log:
        lines += ["", "## Problems", ""] + [f"- {x}" for x in log[:50]]
    with open(os.path.join(out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="sample.db")
    ap.add_argument("--out", default="out")
    ap.add_argument("--files", type=int, default=40)
    ap.add_argument("--last", type=int, default=1306)
    ap.add_argument("--devset", default="devset_ordinary_v1.jsonl")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    devset = pm.load_devset(args.devset)
    log = []
    db = connect(args.db)
    files, pubmed, minutes = build(db, args, devset, log)
    rows, _, _ = evaluate(db, devset, pubmed, log)
    result = report(db, rows, files, minutes, log, args.out, os.path.basename(args.devset))
    brief = {"devset": result["devset"], "documents": result["corpus"]["documents"],
             "answers_indexed": result["answers_indexed"], "cue_questions": result["cue_questions"],
             "mrr5": {k: v["mrr5"] for k, v in result["methods"].items()},
             "primary": {k: v for k, v in result["primary"].items() if k != "hurt_ids"},
             "answer_citations_q1_median_q3": result["answer_citations_q1_median_q3"],
             "pubmed_mrr5": {k: v["mrr5"] for k, v in result["pubmed_best_match_full_corpus"].items()}}
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
