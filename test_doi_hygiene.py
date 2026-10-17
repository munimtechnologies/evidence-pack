# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for doi_hygiene.py. python -m unittest -v test_doi_hygiene"""
import contextlib
import io
import json
import os
import re
import tempfile
import unittest

import doi_hygiene as dh

CSV_HEAD = "doi,openalex_id,kind,openalex_citations_2026_10_16,crossref_registered,class\n"
CSV_ROWS = ("10.1016/s0140,W3120106258,dash,22520,false,unregistered\n"
            "10.1007/978,W2930673238,dash,423,false,unregistered\n"
            "10.1007/978,W2780154223,dash,0,,unchecked\n")


def kinds(result):
    return [f["kind"] for f in result["flags"]]


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class CleanAndExtract(unittest.TestCase):
    def test_clean_maps_dashes_prefix_case_and_trailing_dot(self):
        self.assertEqual(dh.clean_doi("https://doi.org/10.1111/J.1365‐2141.2010.08000.X."),
                         "10.1111/j.1365-2141.2010.08000.x")

    def test_soft_hyphen_is_dropped(self):
        self.assertEqual(dh.clean_doi("10.1000/ab­c"), "10.1000/abc")

    def test_only_unbalanced_closing_paren_is_stripped(self):
        self.assertEqual(dh.clean_doi("10.1016/s0140-6736(19)30456-5)"), "10.1016/s0140-6736(19)30456-5")
        self.assertEqual(dh.clean_doi("10.1000/x(1)"), "10.1000/x(1)")

    def test_extract_keeps_full_doi_through_unicode_dashes(self):
        text = ("Smith J. Blood. 2010. doi:10.1111/j.1365‐2141.2010.08000.x; "
                "Lancet Oncol (10.1016/S1470‐2045(19)30456‑5).")
        self.assertEqual(dh.extract_dois(text),
                         ["10.1111/j.1365-2141.2010.08000.x", "10.1016/s1470-2045(19)30456-5"])

    def test_naive_pattern_leaves_the_stub(self):
        # The mechanism the stub records feed on: an ASCII-only DOI pattern stops at U+2010.
        naive = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
        self.assertEqual(naive.search("10.1111/j.1365‐2141.2010.08000.x").group(0), "10.1111/j.1365")


class CheckDoi(unittest.TestCase):
    def test_known_stub_shapes_are_flagged(self):
        for doi in ["10.1016/s0140", "10.1016/S0140-6736", "10.1111/j.1365", "10.1088/0957",
                    "10.1641/0006-3568", "10.1186/s13054", "10.1007/978", "10.1016/b978"]:
            with self.subTest(doi=doi):
                self.assertEqual(kinds(dh.check_doi(doi, {})), ["stub"])

    def test_alphabetic_suffix_is_journal_level(self):
        for doi in ["10.1136/bmjopen", "10.1108/ejim", "10.25171/instgeoph_pas_publs"]:
            with self.subTest(doi=doi):
                self.assertEqual(kinds(dh.check_doi(doi, {})), ["journal_level"])

    def test_real_article_dois_are_not_flagged(self):
        for doi in ["10.1016/S0140-6736(19)30456-5", "10.1111/j.1365-2141.2010.08000.x",
                    "10.1038/s41598-018-37186-2", "10.1136/bmjopen-2019-030000",
                    "10.1016/j.physbeh.2017.03.040", "https://doi.org/10.1002/asi.24896"]:
            with self.subTest(doi=doi):
                result = dh.check_doi(doi, {})
                self.assertTrue(result["valid"])
                self.assertEqual(result["flags"], [])

    def test_unicode_dash_is_flagged_and_fixed(self):
        result = dh.check_doi("10.1111/j.1365‐2141.2010.08000.x", {})
        self.assertEqual(result["doi"], "10.1111/j.1365-2141.2010.08000.x")
        self.assertEqual(kinds(result), ["dash"])

    def test_truncated_at_separator(self):
        self.assertEqual(kinds(dh.check_doi("10.1016/s0140-6736(", {})), ["truncated"])
        self.assertEqual(kinds(dh.check_doi("10.1111/j.1365-", {})), ["truncated"])

    def test_invalid(self):
        result = dh.check_doi("not a doi", {})
        self.assertFalse(result["valid"])
        self.assertEqual(kinds(result), ["invalid"])
        self.assertFalse(dh.check_doi("", None)["valid"])


class Blocklist(TempDir):
    def test_missing_file_or_empty_path_gives_empty(self):
        self.assertEqual(dh.load_blocklist(os.path.join(self.tmp.name, "none.csv")), {})
        self.assertEqual(dh.load_blocklist(""), {})

    def test_load_groups_duplicate_dois(self):
        bl = dh.load_blocklist(self.write("bl.csv", CSV_HEAD + CSV_ROWS))
        self.assertEqual(sorted(bl), ["10.1007/978", "10.1016/s0140"])
        self.assertEqual([r["openalex_id"] for r in bl["10.1007/978"]], ["W2930673238", "W2780154223"])

    def test_blocklist_hit_on_doi(self):
        bl = dh.load_blocklist(self.write("bl.csv", CSV_HEAD + CSV_ROWS))
        result = dh.check_doi("10.1016/S0140", bl)
        self.assertEqual(kinds(result), ["stub", "blocklist"])
        self.assertIn("W3120106258", result["flags"][1]["why"])

    def test_blocklist_hit_on_openalex_id_alone(self):
        bl = dh.load_blocklist(self.write("bl.csv", CSV_HEAD + CSV_ROWS))
        work = {"id": "https://openalex.org/W2780154223", "doi": None, "type": "book", "cited_by_count": 0}
        self.assertEqual(kinds(dh.check_record(work, bl)), ["blocklist"])

    @unittest.skipUnless(os.path.exists(dh.BLOCKLIST), "stub_blocklist_v1.csv not next to the module")
    def test_shipped_blocklist(self):
        bl = dh.load_blocklist()
        rows = [r for group in bl.values() for r in group]
        self.assertEqual(len(rows), 74)
        self.assertEqual(len(bl), 73)
        unregistered = [r for r in rows if r["class"] == "unregistered"]
        self.assertEqual(len(unregistered), 33)
        self.assertEqual(sum(int(r["openalex_citations_2026_10_16"]) for r in unregistered), 56438)
        self.assertEqual(sum(1 for r in rows if r["class"] == "registered"), 27)


class Records(unittest.TestCase):
    def test_large_paratext_record(self):
        work = {"id": "W4383956374", "doi": "https://doi.org/10.1108/ejim", "type": "paratext",
                "cited_by_count": 434}
        self.assertEqual(kinds(dh.check_record(work, {})), ["journal_level", "paratext"])
        work["cited_by_count"] = 10
        self.assertEqual(kinds(dh.check_record(work, {})), ["journal_level"])

    def test_article_number_one(self):
        work = {"id": "https://openalex.org/W2909240409", "doi": "https://doi.org/10.1038/s41598-018-37186-2",
                "type": "article", "cited_by_count": 8494, "biblio": {"first_page": "1", "last_page": None}}
        result = dh.check_record(work, {})
        self.assertEqual(result["id"], "W2909240409")
        self.assertEqual(result["doi"], "10.1038/s41598-018-37186-2")
        self.assertEqual(kinds(result), ["article_one"])

    def test_journal_swap_sink_is_not_visible_here(self):
        # Bunney 2017 is a sink, but nothing in its own record shows it (see sink_check_v2.py).
        work = {"id": "W2599766179", "doi": "https://doi.org/10.1016/j.physbeh.2017.03.040",
                "type": "article", "cited_by_count": 2067, "biblio": {"first_page": "139", "last_page": "148"}}
        self.assertEqual(dh.check_record(work, {})["flags"], [])

    def test_crossref_article_one_risk(self):
        self.assertTrue(dh.article_one_risk({"article-number": "1"}))
        self.assertTrue(dh.article_one_risk({"page": "1"}))
        self.assertFalse(dh.article_one_risk({"page": "1-17"}))
        self.assertFalse(dh.article_one_risk({"page": "139-148"}))
        self.assertFalse(dh.article_one_risk({}))


class Cli(TempDir):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(dh.main(argv), 0)
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_check(self):
        rows = self.run_main(["check", "10.1136/bmjopen", "10.1002/asi.24896", "--blocklist", ""])
        self.assertEqual([kinds(r) for r in rows], [["journal_level"], []])

    def test_scan(self):
        path = self.write("refs.txt", "a 10.1111/j.1365‐2141.2010.08000.x.\nb doi:10.1016/s0140\n")
        rows = self.run_main(["scan", path, "--blocklist", self.write("bl.csv", CSV_HEAD + CSV_ROWS)])
        self.assertEqual([r["doi"] for r in rows], ["10.1111/j.1365-2141.2010.08000.x", "10.1016/s0140"])
        self.assertEqual([kinds(r) for r in rows], [["dash"], ["stub", "blocklist"]])

    def test_records(self):
        line = json.dumps({"id": "W1", "doi": "https://doi.org/10.1136/bmjopen", "type": "article",
                           "cited_by_count": 2230})
        rows = self.run_main(["records", self.write("works.jsonl", line + "\n\n"), "--blocklist", ""])
        self.assertEqual(len(rows), 1)
        self.assertEqual(kinds(rows[0]), ["journal_level"])


if __name__ == "__main__":
    unittest.main()
