# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for commentin_targets.py (no network). The live links stand in for what
commentin_check returns; their targets are shaped on PubMed records read on 2026-10-18
(28208180, a comment on 28208174, and 28208174, a multicentre trial, both linked from 28208186)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import commentin_targets as ct  # noqa: E402

ROWS = [
    {"group": "jama_network", "ta": "JAMA Oncol", "year": 2017, "src_pmid": "28208186", "cls": "bare_doi",
     "tgt_doi": "10.1001/jamaoncol.2016.6722", "earlier": False},
    {"group": "jama_network", "ta": "JAMA Oncol", "year": 2017, "src_pmid": "28208186", "cls": "bare_doi",
     "tgt_doi": "10.1001/jamaoncol.2016.6749", "earlier": False},
    {"group": "jama_network", "ta": "JAMA", "year": 2025, "src_pmid": "40274279", "cls": "bare_doi",
     "tgt_doi": "10.1001/jama.2024.17482", "earlier": True},
    {"group": "jama_network", "ta": "JAMA Netw Open", "year": 2025, "src_pmid": "39808433", "cls": "bare_doi",
     "tgt_doi": "10.1001/jamanetworkopen.2024.53972", "earlier": False},
    {"group": "control", "ta": "Ann Intern Med", "year": 2021, "src_pmid": "1", "cls": "bare_doi",
     "tgt_doi": "10.7326/x", "earlier": False},
    {"group": "jama_network", "ta": "JAMA", "year": 2020, "src_pmid": "2", "cls": "other_nopmid",
     "tgt_doi": "10.1001/y", "earlier": False},
    {"group": "jama_network", "ta": "JAMA", "year": 2020, "src_pmid": "3", "cls": "bare_doi",
     "tgt_doi": "10.1001/z", "earlier": None},
]
COMMENT = {"tgt_doi": "10.1001/jamaoncol.2016.6722", "tgt_pmid": "28208180", "tgt_found": True,
           "reciprocal": False, "tgt_comment_on": ["28208174"], "tgt_pubtypes": ["Journal Article", "Comment"],
           "tgt_title": "Improving the Evidence Base for Delivery of High-Quality Cancer Care.",
           "tgt_date": "2017-08-01", "flags": ["bare_doi", "not_reciprocal", "comment_on_other"]}
TRIAL = {"tgt_doi": "10.1001/jamaoncol.2016.6749", "tgt_pmid": "28208174", "tgt_found": True,
         "reciprocal": False, "tgt_comment_on": [], "tgt_pubtypes": ["Clinical Trial", "Journal Article",
                                                                     "Multicenter Study"],
         "tgt_title": "Feasibility Assessment", "tgt_date": "2017-08-01", "flags": ["bare_doi", "not_reciprocal"]}
UNREAD = {"tgt_doi": "10.7326/x", "tgt_pmid": None, "tgt_found": False, "reciprocal": None, "tgt_comment_on": [],
          "tgt_pubtypes": [], "flags": ["bare_doi", "target_unread"]}
RECORDS = [{"pmid": "1", "found": True, "links": [UNREAD]},
           {"pmid": "28208186", "found": True, "links": [COMMENT, TRIAL]},
           {"pmid": "39808433", "found": True, "links": []}]


class FakeCheck:
    def __init__(self):
        self.calls = []

    def __call__(self, tokens):
        self.calls.append(list(tokens))
        return RECORDS, []


class TestClassify(unittest.TestCase):
    def test_population(self):
        pop = ct.population(ROWS)
        self.assertEqual([r["src_pmid"] for r in pop], ["28208186", "28208186", "39808433", "1"])

    def test_classes(self):
        self.assertEqual(ct.classify_target(None), "link_gone")
        self.assertEqual(ct.classify_target(UNREAD), "unread")
        self.assertEqual(ct.classify_target(dict(UNREAD, flags=["bare_doi", "target_not_in_pubmed"])),
                         "not_in_pubmed")
        self.assertEqual(ct.classify_target(dict(COMMENT, reciprocal=True)), "reciprocal")
        self.assertEqual(ct.classify_target(COMMENT), "comment_on_other")
        self.assertEqual(ct.classify_target(dict(COMMENT, tgt_comment_on=[], tgt_pubtypes=["Editorial"])),
                         "comment_typed")
        self.assertEqual(ct.classify_target(TRIAL), "research_typed")
        self.assertEqual(ct.classify_target(dict(TRIAL, tgt_pubtypes=["Randomized Controlled Trial"])),
                         "research_typed")
        self.assertEqual(ct.classify_target(dict(TRIAL, tgt_pubtypes=["Journal Article"])), "untyped")

    def test_era(self):
        self.assertEqual([ct.era(y) for y in (2017, 2023, 2024, 2025, 2026)],
                         ["2016-2023", "2016-2023", "2024", "2025-2026", "2025-2026"])

    def test_share_test(self):
        self.assertEqual(ct.share_test(99, 0, "<=", 0.05), "untestable")
        self.assertEqual(ct.share_test(100, 5, "<=", 0.05), "supported")
        self.assertEqual(ct.share_test(100, 6, "<=", 0.05), "not supported")
        self.assertEqual(ct.share_test(200, 20, ">=", 0.10), "supported")
        self.assertEqual(ct.share_test(200, 19, ">=", 0.10), "not supported")


class TestRun(unittest.TestCase):
    def test_run(self):
        check = FakeCheck()
        results, rows = ct.run(ROWS, check=check)
        self.assertEqual(check.calls, [["1", "28208186", "39808433"]])
        self.assertEqual(results["population"], {"control": 1, "jama_network": 3})
        jn = results["by_group"]["jama_network"]
        self.assertEqual((jn["comment_on_other"], jn["research_typed"], jn["link_gone"]), (1, 1, 1))
        self.assertEqual(sum(jn.values()), 3)
        self.assertEqual(results["by_group"]["control"]["unread"], 1)
        self.assertFalse(results["void"])
        self.assertEqual(results["hypotheses"], {"H1": "untestable", "H2": "untestable", "H3": "untestable"})
        self.assertEqual(results["by_era"]["2016-2023"]["comment_on_other"], 1)
        self.assertEqual(results["by_era"]["2025-2026"]["link_gone"], 1)
        self.assertEqual(results["by_journal"]["JAMA Oncol"]["research_typed"], 1)
        self.assertEqual((results["sources"], results["sources_found"]), (3, 3))
        self.assertEqual([r["class"] for r in rows], ["unread", "comment_on_other", "research_typed", "link_gone"])
        self.assertEqual(rows[1]["tgt_comment_on"], ["28208174"])
        self.assertIsNone(rows[3]["tgt_pmid"])

    def test_void_when_lookups_fail(self):
        records = [{"pmid": "28208186", "found": True,
                    "links": [dict(UNREAD, tgt_doi="10.1001/jamaoncol.2016.6722"), TRIAL]},
                   {"pmid": "39808433", "found": True, "links": []}]
        results, _ = ct.run(ROWS[:4], check=lambda tokens: (records, ["esummary from 1: HTTP 400"]))
        self.assertTrue(results["void"])
        self.assertEqual(results["n_errors"], 1)

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            links = os.path.join(d, "links.jsonl")
            with open(links, "w", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r) + "\n" for r in ROWS[2:3]))
            code = ct.main(["--links", links, "--out-dir", d])
            with open(os.path.join(d, "results.json"), encoding="utf-8") as fh:
                results = json.load(fh)
            with open(os.path.join(d, "targets.jsonl"), encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(results["population"], {})
        self.assertEqual(results["sources"], 0)
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
