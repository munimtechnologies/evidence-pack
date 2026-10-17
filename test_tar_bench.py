# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for tar_bench.py (no network)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tar_bench as tb  # noqa: E402

TOPIC = """Topic: CD000001

Title: Rapid tests for malaria

Query:
exp Malaria/
plasmod*.ti,ab.
1 or 2
(sensitiv: or diagnos:).mp. or di.fs.
exp Pancreatic Neoplasms/di [Diagnosis]
(RDT adj3 test$).ti,ab.
limit 6 to ed=19400101-20100114

Pids:
    111
    222
"""

XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
<PubmedArticle><MedlineCitation><PMID>111</PMID><Article>
<ArticleTitle>Rapid <i>malaria</i> test</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">First part.</AbstractText>
<AbstractText Label="RESULTS">Second part.</AbstractText></Abstract>
<PublicationTypeList><PublicationType>Journal Article</PublicationType>
<PublicationType>Retracted Publication</PublicationType></PublicationTypeList>
</Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>222</PMID><Article>
<ArticleTitle>Fever study</ArticleTitle>
<PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
</Article>
<CommentsCorrectionsList><CommentsCorrections RefType="RetractionIn"><RefSource>X</RefSource>
</CommentsCorrections></CommentsCorrectionsList>
</MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>333</PMID><Article>
<ArticleTitle>Plain</ArticleTitle>
<PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
</Article></MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""


class TestParsing(unittest.TestCase):
    def test_parse_topic(self):
        t = tb.parse_topic(TOPIC)
        self.assertEqual(t["topic"], "CD000001")
        self.assertEqual(t["title"], "Rapid tests for malaria")
        self.assertEqual(len(t["query_lines"]), 7)
        self.assertEqual(t["query_lines"][0], "exp Malaria/")
        self.assertEqual(t["pids"], ["111", "222"])

    def test_query_terms_plain(self):
        terms, prefixes = tb.query_terms(tb.parse_topic(TOPIC)["query_lines"])
        self.assertEqual(terms, ["malaria", "plasmod", "sensitiv", "diagnos", "pancreatic", "neoplasms",
                                 "rdt", "test"])
        self.assertEqual(prefixes, [])

    def test_query_terms_prefix(self):
        terms, prefixes = tb.query_terms(tb.parse_topic(TOPIC)["query_lines"], prefix=True)
        self.assertEqual(terms, ["malaria", "pancreatic", "neoplasms", "rdt"])
        self.assertEqual(prefixes, ["plasmod", "sensitiv", "diagnos", "test"])

    def test_tokenize(self):
        self.assertEqual(tb.tokenize("The RDT-test of 2010 and Malaria"), ["rdt", "test", "malaria"])

    def test_parse_qrels(self):
        q, dups = tb.parse_qrels("T1 0 1 0\nT1 0 2 1\nT1 0 2 0\nT1 0 3 -1\nbad line\nT2 0 9 1\n")
        self.assertEqual(q, {"T1": {"1": 0, "2": 1, "3": -1}, "T2": {"9": 1}})
        self.assertEqual(dups, 1)
        self.assertEqual(tb.judged(q["T1"]), {"1": 0, "2": 1})

    def test_parse_efetch(self):
        d = tb.parse_efetch(XML)
        self.assertEqual(d["111"]["title"], "Rapid malaria test")
        self.assertEqual(d["111"]["abstract"], "First part. Second part.")
        self.assertTrue(d["111"]["retracted"])
        self.assertTrue(d["222"]["retracted"])
        self.assertEqual(d["222"]["abstract"], "")
        self.assertFalse(d["333"]["retracted"])


class TestRanking(unittest.TestCase):
    def test_bm25_score_by_hand(self):
        docs = {"1": ["malaria", "test"], "2": ["fever"]}
        r = tb.bm25_rank("T", docs, ["malaria"])
        self.assertEqual(r[0][0], "1")
        # idf = ln(1 + 1.5/1.5) = ln 2; avgdl 1.5; tf 1, dl 2:
        # 2.2 / (1 + 1.2 * (0.25 + 0.75 * 2 / 1.5)) = 2.2 / 2.5 = 0.88
        self.assertAlmostEqual(r[0][1], math.log(2) * 0.88, places=9)
        self.assertEqual(r[1], ("2", 0.0))

    def test_prefix_matches(self):
        docs = {"1": ["sensitivity", "sensitive"], "2": ["specificity"], "3": ["other"]}
        r = tb.bm25_rank("T", docs, [], ["sensitiv"])
        self.assertEqual(r[0][0], "1")
        self.assertGreater(r[0][1], 0)
        self.assertEqual(r[1][1], 0.0)
        exact = tb.bm25_rank("T", docs, ["sensitiv"])
        self.assertEqual(exact[0][1], 0.0)

    def test_ties_are_fixed(self):
        docs = {str(i): ["x"] for i in range(20)}
        a = [p for p, _ in tb.bm25_rank("T", docs, ["y"])]
        b = [p for p, _ in tb.bm25_rank("T", dict(reversed(list(docs.items()))), ["y"])]
        self.assertEqual(a, b)
        self.assertEqual(sorted(a), sorted(docs))
        rnd = [p for p, _ in tb.random_rank("T", list(docs))]
        self.assertEqual(sorted(rnd), sorted(docs))
        self.assertNotEqual(rnd, a)


class TestMeasures(unittest.TestCase):
    def test_by_hand(self):
        q = {"a": 1, "b": 0, "c": 0, "d": 1, "e": 0}
        m = tb.measures(["a", "b", "c", "d", "e"], q)
        self.assertEqual((m["n"], m["r"], m["last_rel"]), (5, 2, 4))
        self.assertAlmostEqual(m["ap"], 0.75)
        self.assertAlmostEqual(m["wss_100"], 0.2)
        self.assertAlmostEqual(m["wss_95"], 0.15)
        self.assertEqual(m["norm_area"], 0.75)
        self.assertEqual((m["r1"], m["r5"], m["r10"], m["r20"]), (0.5, 0.5, 0.5, 0.5))

    def test_no_relevant_is_none(self):
        self.assertIsNone(tb.measures(["a"], {"a": 0}))

    def test_missing_relevant_zeroes_wss(self):
        m = tb.measures(["a", "b"], {"a": 1, "b": 0, "c": 1})
        self.assertEqual(m["n"], 3)
        self.assertEqual(m["wss_100"], 0)
        self.assertEqual(m["wss_95"], 0)
        self.assertAlmostEqual(m["ap"], 0.5)

    def test_verdicts(self):
        good = {"ap": 0.17, "wss_95": 0.33}
        a = {"mean": good, "topics": {f"T{i}": {"ap": 0.1} for i in range(30)}}
        c = {"topics": {f"T{i}": {"ap": 0.2 if i < 20 else 0.05} for i in range(30)}}
        v = tb.verdicts({"bool": a, "bool_title_prefix": c})
        self.assertEqual((v["H1"], v["H2"], v["H2_wins"]), ("supported", "supported", 20))
        c["topics"]["T0"]["ap"] = 0.1
        a["mean"] = {"ap": 0.25, "wss_95": 0.36}
        v = tb.verdicts({"bool": a, "bool_title_prefix": c})
        self.assertEqual((v["H1"], v["H2"], v["H2_wins"]), ("not supported", "not supported", 19))
        self.assertEqual(tb.verdicts({"bool": {"mean": good, "topics": {}}})["H1"], "untestable")


class TestEfetch(unittest.TestCase):
    def test_split_and_log(self):
        def fetch(body):
            ids = dict(x.split("=", 1) for x in body.decode().split("&"))["id"].split("%2C")
            if len(ids) > 2 or "333" in ids:
                raise RuntimeError("HTTP 400: Failed to connect")
            return XML
        errors = []
        out = tb.efetch_docs(["111", "222", "333", "444"], errors, fetch=fetch, batch=4, split=2)
        self.assertEqual(sorted(out), ["111", "222", "333"])
        self.assertEqual(tb.failed_count(errors), 2)
        self.assertEqual(errors[0]["efetch_failed"], ["333", "444"])

    def test_stop_after_max_failed(self):
        def fetch(body):
            raise RuntimeError("HTTP 400")
        errors = []
        out = tb.efetch_docs([str(i) for i in range(6)], errors, fetch=fetch, batch=2, split=2, max_failed=1)
        self.assertEqual(out, {})
        self.assertEqual(tb.failed_count(errors), 6)
        self.assertEqual(errors[1]["error"], "skipped after repeated failures")


if __name__ == "__main__":
    unittest.main()
