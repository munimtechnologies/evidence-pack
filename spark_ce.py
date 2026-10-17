#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""spark_ce: does an open biomedical cross-encoder help the SPARK Task 1 sample bench?

Pre-registration: prereg-ce-rerank-v1.md. Reuses the sample index that
spark-sample-eval-v3 built (/data/sample40.db, opened read-only) and takes the
same 50-candidate pool per question (field-weighted BM25). Four rankings of
that pool are scored with MRR@5:

- chosen: the v3 winner, fields+ptype+cite|cue+early+year (copied from spark_eval.py);
- ce: NCBI's MedCPT cross-encoder (public domain) on question vs title + abstract;
- rrf: reciprocal-rank fusion (k = 60) of chosen and ce;
- ce|cue->rrf: rrf for questions with a priority cue, ce for the rest.

Titles and abstracts come from PubMed efetch (the v3 index is contentless);
citation counts from NIH iCite, as in v3. The torch/transformers imports
happen only when the model is loaded, so the tests need the standard library
only.

Usage: python spark_ce.py --db /data/sample40.db --out /out --hf-home /data/hf
"""
import argparse
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL = {"tool": "mv2-munim-spark-ce", "email": "mv2@munimtech.com"}
ICITE = "https://icite.od.nih.gov/api/pubs?pmids=%s&fl=pmid,citation_count"
UA = "mv2-spark-ce/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
MODEL = "ncbi/MedCPT-Cross-Encoder"
LANDMARK, ORDINARY = "devset_landmark_v1.jsonl", "devset_ordinary_v1.jsonl"
V3 = {LANDMARK: 0.838, ORDINARY: 0.809}  # chosen method's MRR@5 in spark-sample-eval-v3
SANITY = 0.01
MARGIN = 0.02
RRF_K = 60
NCBI_PAUSE = 0.4  # NCBI asks for at most 3 requests a second without a key

# copied unchanged from spark_eval.py (v3)
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
FW = (3, 1, 1, 1, 0.5)
POOL = 50
CHOSEN = {"demote": 0.6, "beta": 0.3, "gate": "cue", "gamma": 0.2, "delta": 0.3}
# fixed in prereg-ce-rerank-v1.md; this order breaks ties (simplest first)
CANDIDATES = ("ce", "rrf", "ce|cue->rrf")
METHODS = ("chosen",) + CANDIDATES


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


def search(db, question, weights, limit=100):
    words = terms(question)
    if not words:
        return []
    w = ", ".join("%g" % x for x in weights)
    rows = db.execute(f"SELECT rowid, bm25(docs, {w}) AS s FROM docs WHERE docs MATCH ? ORDER BY s LIMIT ?",
                      (fts_query(words), limit)).fetchall()
    return [(int(p), -s) for p, s in rows]  # FTS5 bm25 is negative; flip so bigger is better


def rerank(cands, meta, cites, question, demote=1.0, beta=0.0, gamma=0.0, delta=0.0, gate=None, band=None):
    """Re-order the first POOL candidates; meta maps pmid -> (year, ptypes). Unchanged from spark_eval.py."""
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


# new in this bench
def fetch(url, data=None, timeout=120, tries=3):
    """GET (POST when data is given) with retries; raises after the last try."""
    last = None
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as err:  # network hiccups: back off and retry
            last = err
            time.sleep(5 * (attempt + 1))
    raise last


def load_devset(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def text_of(el):
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def parse_texts(raw):
    """{pmid: 'title abstract'} for each PubmedArticle in an efetch XML reply."""
    out = {}
    for pa in ET.fromstring(raw).iter("PubmedArticle"):
        mc = pa.find("MedlineCitation")
        art = mc.find("Article") if mc is not None else None
        pmid = (mc.findtext("PMID") or "").strip() if mc is not None else ""
        if art is None or not pmid.isdigit():
            continue
        title = text_of(art.find("ArticleTitle")) or text_of(art.find("VernacularTitle"))
        parts = []
        for ab in art.findall("Abstract/AbstractText"):
            body = text_of(ab)
            label = ab.get("Label")
            if body:
                parts.append(f"{label}: {body}" if label else body)
        out[int(pmid)] = (title + " " + " ".join(parts)).strip()
    return out


def texts(pmids, log, get=fetch, pause=NCBI_PAUSE):
    out = {}
    ids = sorted({int(p) for p in pmids})
    for i in range(0, len(ids), 200):
        if pause:
            time.sleep(pause)
        try:
            raw = get(EUTILS + "efetch.fcgi",
                      dict(TOOL, db="pubmed", id=",".join(map(str, ids[i:i + 200])), retmode="xml"))
            out.update(parse_texts(raw))
        except Exception as err:  # report and go on
            log.append(f"efetch batch {i}: {err!r}")
    return out


def citations(pmids, log, get=fetch, pause=0.2):
    out = {}
    ids = sorted({int(p) for p in pmids})
    for i in range(0, len(ids), 200):
        try:
            data = json.loads(get(ICITE % ",".join(map(str, ids[i:i + 200]))))
            for row in data.get("data", []):
                out[int(row["pmid"])] = row.get("citation_count") or 0
        except Exception as err:
            log.append(f"icite batch {i}: {err!r}")
        if pause:
            time.sleep(pause)
    return out


def meta_of(db, pmids):
    out = {}
    for p in pmids:
        row = db.execute("SELECT year, ptypes FROM meta WHERE pmid=?", (p,)).fetchone()
        if row:
            out[p] = (row[0], row[1] or "")
    return out


def ce_scorer(model_name=MODEL, batch=16, max_length=512):
    """score(question, docs) -> one MedCPT cross-encoder logit per doc."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()

    def score(question, docs):
        out = []
        for i in range(0, len(docs), batch):
            pairs = [[question, d] for d in docs[i:i + batch]]
            with torch.no_grad():
                enc = tok(pairs, truncation=True, padding=True, return_tensors="pt", max_length=max_length)
                out += [float(x) for x in model(**enc).logits.squeeze(dim=1).tolist()]
        return out
    return score


def order_by(pool, scores):
    """pool (in BM25 order) sorted by score, highest first; ties keep the BM25 order."""
    return [p for _, _, p in sorted((-s, i, p) for i, (p, s) in enumerate(zip(pool, scores)))]


def rrf(rankings, k=RRF_K):
    """Reciprocal-rank fusion; ties go to the better position in the first ranking."""
    score = {}
    for ranking in rankings:
        for i, p in enumerate(ranking):
            score[p] = score.get(p, 0.0) + 1.0 / (k + i + 1)
    pos = {p: i for i, p in enumerate(rankings[0])} if rankings else {}
    return sorted(score, key=lambda p: (-score[p], pos.get(p, len(pos))))


def evaluate(db, devset, score, log, get=fetch, pause=NCBI_PAUSE):
    cands = {q["info_need_id"]: search(db, q["info_need"], FW) for q in devset}
    pool_ids = {p for lst in cands.values() for p, _ in lst[:POOL]} | {int(q["pmid"]) for q in devset}
    meta = meta_of(db, pool_ids)
    cites = citations(pool_ids, log, get, pause and 0.2)
    txt = texts(pool_ids, log, get, pause)
    rows = []
    for q in devset:
        qid, ans, question = q["info_need_id"], int(q["pmid"]), q["info_need"]
        base = cands[qid]
        pool = [p for p, _ in base[:POOL]]
        chosen = rerank(base, meta, cites, question, **CHOSEN)
        ce = order_by(pool, score(question, [txt.get(p, "") for p in pool])) if pool else []
        fused = rrf([chosen, ce])
        cue = bool(CUE.search(question.lower()))
        ranked = {"chosen": chosen, "ce": ce, "rrf": fused, "ce|cue->rrf": fused if cue else ce}
        row = {"id": qid, "kind": q["kind"], "answer": ans, "cue": cue, "in_pool": ans in pool,
               "answer_has_text": bool(txt.get(ans)), "pool": len(pool)}
        for name in METHODS:
            lst = ranked[name]
            row[name] = {"rr": rr(lst, ans), "rank": lst.index(ans) + 1 if ans in lst else None, "top3": lst[:3]}
        rows.append(row)
    return rows


def summarize(rows, key):
    n = len(rows) or 1
    return {"n": len(rows), "mrr5": round(sum(r[key]["rr"] for r in rows) / n, 4),
            "hit1": round(sum(1 for r in rows if r[key]["rr"] == 1.0) / n, 4),
            "hit5": round(sum(1 for r in rows if r[key]["rr"] > 0) / n, 4)}


def decide(mrr, margin=MARGIN):
    """mrr: {devset: {method: MRR@5}}. The rule of prereg-ce-rerank-v1.md."""
    sets = sorted(mrr)
    mean = {m: round(sum(mrr[s][m] for s in sets) / len(sets), 4) for m in METHODS}
    eligible = [m for m in CANDIDATES
                if mean[m] - mean["chosen"] >= margin - 1e-9
                and all(mrr[s][m] >= mrr[s]["chosen"] - margin - 1e-9 for s in sets)]
    pick = "chosen"
    for m in eligible:  # CANDIDATES are in tie-break order, so a strict > keeps the simpler one
        if pick == "chosen" or mean[m] > mean[pick] + 1e-9:
            pick = m
    return {"mean": mean, "eligible": eligible, "pick": pick}


def hypotheses(mrr):
    d = decide(mrr)
    lm, od = mrr[LANDMARK], mrr[ORDINARY]
    return {"H1": "supported" if od["ce"] > od["chosen"] else "not supported",
            "H2": "supported" if lm["ce"] < lm["chosen"] else "not supported",
            "H3": "supported" if d["pick"] != "chosen" else "not supported",
            "decision": d,
            "sanity": {s: {"v3": V3[s], "now": mrr[s]["chosen"], "ok": abs(mrr[s]["chosen"] - V3[s]) <= SANITY}
                       for s in (LANDMARK, ORDINARY)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="/data/sample40.db")
    ap.add_argument("--out", default="out")
    ap.add_argument("--devsets", nargs="+", default=[LANDMARK, ORDINARY])
    ap.add_argument("--hf-home", default="", help="model cache folder (set before transformers is imported)")
    args = ap.parse_args(argv)
    if args.hf_home:
        os.environ["HF_HOME"] = args.hf_home
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    db = sqlite3.connect("file:%s?mode=ro" % args.db, uri=True)
    score = ce_scorer()
    log, summary, allrows = [], {}, {}
    for path in args.devsets:
        name = os.path.basename(path)
        rows = evaluate(db, load_devset(path), score, log)
        allrows[name] = rows
        summary[name] = {m: summarize(rows, m) for m in METHODS}
        summary[name]["in_pool"] = round(sum(1 for r in rows if r["in_pool"]) / (len(rows) or 1), 4)
        print(f"{name}: {json.dumps({m: summary[name][m]['mrr5'] for m in METHODS})}", file=sys.stderr, flush=True)
    mrr = {s: {m: summary[s][m]["mrr5"] for m in METHODS} for s in summary}
    result = {"model": MODEL, "pool": POOL, "rrf_k": RRF_K, "summary": summary,
              "minutes": round((time.time() - t0) / 60, 1), "log": log}
    if LANDMARK in mrr and ORDINARY in mrr:
        result["hypotheses"] = hypotheses(mrr)
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    with open(os.path.join(args.out, "per_question.jsonl"), "w", encoding="utf-8") as f:
        for name, rows in allrows.items():
            for r in rows:
                f.write(json.dumps(dict(r, devset=name)) + "\n")
    lines = ["# MedCPT cross-encoder rerank on the SPARK Task 1 sample bench (prereg-ce-rerank-v1.md)", "",
             "| dev set | answer in pool | " + " | ".join(METHODS) + " |", "|---|---|" + "---|" * len(METHODS)]
    for s, v in summary.items():
        lines.append(f"| {s} | {v['in_pool']:.3f} | " + " | ".join(f"{v[m]['mrr5']:.3f}" for m in METHODS) + " |")
    if "hypotheses" in result:
        h = result["hypotheses"]
        lines += ["", f"- H1 (ce beats chosen on ordinary): {h['H1']}",
                  f"- H2 (ce below chosen on landmark): {h['H2']}",
                  f"- H3 (a candidate passes the rule): {h['H3']}; eligible {h['decision']['eligible'] or 'none'}",
                  f"- **Pick: {h['decision']['pick']}** (means {h['decision']['mean']})",
                  f"- Sanity (chosen within {SANITY} of v3): " +
                  ", ".join(f"{s} {x['now']:.3f} vs {x['v3']:.3f} {'ok' if x['ok'] else 'MOVED'}"
                            for s, x in h["sanity"].items())]
    if log:
        lines += ["", "## Problems", ""] + [f"- {x}" for x in log[:50]]
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "log"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
