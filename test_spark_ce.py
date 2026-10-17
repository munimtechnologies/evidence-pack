# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for spark_ce.py (standard library only; no model is loaded)."""
import json
import sqlite3
import unittest

import spark_ce as sc

XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
<PubmedArticle><MedlineCitation><PMID>11</PMID><Article>
<ArticleTitle>Basic local alignment search tool.</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">A new approach to rapid sequence comparison.</AbstractText>
<AbstractText>It is called <i>BLAST</i>.</AbstractText></Abstract>
</Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>12</PMID><Article>
<ArticleTitle>The BLAST algorithm: a review.</ArticleTitle>
</Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>13</PMID><Article>
<ArticleTitle>Gapped BLAST and PSI-BLAST.</ArticleTitle>
<Abstract><AbstractText>Algorithm improvements for blast searches.</AbstractText></Abstract>
</Article></MedlineCitation></PubmedArticle>
</PubmedArticleSet>
"""


def fake_get(url, data=None):
    if "icite" in url:
        return json.dumps({"data": [{"pmid": 11, "citation_count": 50000}, {"pmid": 12, "citation_count": 3},
                                    {"pmid": 13, "citation_count": 40000}]}).encode()
    if url.endswith("efetch.fcgi"):
        return XML
    raise AssertionError(url)


def fts5_db():
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(title, abstract, mesh, authors, journal, "
                   "content='', tokenize='porter unicode61 remove_diacritics 2')")
    except sqlite3.OperationalError:
        return None
    db.execute("CREATE TABLE meta(pmid INTEGER PRIMARY KEY, year INTEGER, ptypes TEXT, title TEXT, source TEXT)")
    docs = [(11, 1990, "Journal Article", "Basic local alignment search tool",
             "A new approach to rapid sequence comparison, basic local alignment search tool BLAST"),
            (12, 2005, "Journal Article|Review", "The BLAST algorithm: a review", "A review of the BLAST algorithm"),
            (13, 1997, "Journal Article", "Gapped BLAST and PSI-BLAST", "Algorithm improvements for blast")]
    for pmid, year, ptypes, title, abstract in docs:
        db.execute("INSERT INTO meta VALUES (?,?,?,?,?)", (pmid, year, ptypes, title, "test"))
        db.execute("INSERT INTO docs(rowid, title, abstract, mesh, authors, journal) VALUES (?,?,?,?,?,?)",
                   (pmid, title, abstract, "", "", ""))
    return db


class TextTests(unittest.TestCase):
    def test_terms_and_rr(self):
        self.assertEqual(sc.terms("Which paper introduced the BLAST algorithm?"), ["blast", "algorithm"])
        self.assertEqual(sc.rr([3, 1, 2], 1), 0.5)
        self.assertEqual(sc.rr([1, 2, 3, 4, 5, 6], 6), 0.0)
        self.assertEqual(sc.fts_query(["a1", "b"]), '"a1" OR "b"')

    def test_parse_texts(self):
        t = sc.parse_texts(XML)
        self.assertEqual(sorted(t), [11, 12, 13])
        self.assertEqual(t[11], "Basic local alignment search tool. BACKGROUND: A new approach to rapid sequence "
                                "comparison. It is called BLAST.")
        self.assertEqual(t[12], "The BLAST algorithm: a review.")

    def test_texts_reports_failures(self):
        log = []

        def broken(url, data=None):
            raise OSError("down")
        self.assertEqual(sc.texts([1, 2], log, get=broken, pause=0), {})
        self.assertEqual(len(log), 1)


class RankTests(unittest.TestCase):
    def test_order_by(self):
        self.assertEqual(sc.order_by([5, 6, 7], [0.1, 0.9, 0.1]), [6, 5, 7])
        self.assertEqual(sc.order_by([], []), [])

    def test_rrf(self):
        # 1 and 3 tie (1/61 + 1/63); 2 has 2/62, just below; the tie goes to the first ranking's order
        self.assertEqual(sc.rrf([[1, 2, 3], [3, 2, 1]]), [1, 3, 2])
        self.assertEqual(sc.rrf([[4, 5], [4, 5]]), [4, 5])

    def test_rerank_is_v3(self):
        # the chosen settings, as fixed in prereg-cite-gate-v1.md
        self.assertEqual(sc.CHOSEN, {"demote": 0.6, "beta": 0.3, "gate": "cue", "gamma": 0.2, "delta": 0.3})
        self.assertEqual(sc.FW, (3, 1, 1, 1, 0.5))
        self.assertEqual(sc.POOL, 50)
        meta = {1: (2000, "Journal Article"), 2: (2000, "Review")}
        # no cue, no review words: the review is demoted below an equal-scoring article
        self.assertEqual(sc.rerank([(2, 1.0), (1, 1.0)], meta, {}, "rapid local sequence search", demote=0.6), [1, 2])
        # the citation prior is off without a cue
        cites = {1: 0, 2: 10 ** 6}
        self.assertEqual(sc.rerank([(1, 1.0), (2, 0.99)], {1: (2000, ""), 2: (2000, "")}, cites,
                                   "rapid local sequence search", **sc.CHOSEN), [1, 2])
        self.assertEqual(sc.rerank([(1, 1.0), (2, 0.99)], {1: (2000, ""), 2: (2000, "")}, cites,
                                   "the original rapid local sequence search", **sc.CHOSEN), [2, 1])


class DecideTests(unittest.TestCase):
    def mrr(self, lm, od):
        return {sc.LANDMARK: dict(zip(sc.METHODS, lm)), sc.ORDINARY: dict(zip(sc.METHODS, od))}

    def test_tie_goes_to_simpler(self):
        d = sc.decide(self.mrr((0.8, 0.85, 0.83, 0.84), (0.8, 0.75, 0.83, 0.82)))
        self.assertEqual(d["eligible"], ["rrf", "ce|cue->rrf"])
        self.assertEqual(d["pick"], "rrf")

    def test_drop_on_one_set_blocks(self):
        d = sc.decide(self.mrr((0.80, 0.70, 0.80, 0.80), (0.80, 0.99, 0.80, 0.80)))
        self.assertEqual(d["eligible"], [])
        self.assertEqual(d["pick"], "chosen")

    def test_hypotheses(self):
        h = sc.hypotheses(self.mrr((0.838, 0.70, 0.86, 0.85), (0.809, 0.90, 0.85, 0.90)))
        self.assertEqual((h["H1"], h["H2"], h["H3"]), ("supported", "supported", "supported"))
        self.assertEqual(h["decision"]["pick"], "ce|cue->rrf")
        self.assertTrue(all(x["ok"] for x in h["sanity"].values()))


class EvaluateTests(unittest.TestCase):
    def test_evaluate_with_fake_model(self):
        db = fts5_db()
        if db is None:
            self.skipTest("this sqlite3 has no FTS5")
        devset = [{"info_need_id": "t-1", "pmid": "11", "kind": "method",
                   "info_need": "Which paper introduced the BLAST algorithm for rapid local sequence similarity "
                                "searching?"}]

        def score(question, docs):
            return [10.0 if d.startswith("Basic local") else 0.0 for d in docs]
        log = []
        rows = sc.evaluate(db, devset, score, log, get=fake_get, pause=0)
        self.assertEqual(log, [])
        r = rows[0]
        self.assertTrue(r["in_pool"] and r["answer_has_text"] and r["cue"])
        self.assertEqual(r["pool"], 3)
        self.assertEqual(r["ce"]["rr"], 1.0)
        self.assertEqual(r["ce|cue->rrf"]["top3"], r["rrf"]["top3"])
        self.assertEqual(sorted(r["chosen"]["top3"]), [11, 12, 13])
        self.assertEqual(sc.summarize(rows, "ce"), {"n": 1, "mrr5": 1.0, "hit1": 1.0, "hit5": 1.0})


if __name__ == "__main__":
    unittest.main()
