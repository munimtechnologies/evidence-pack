"""Tests for LinkCheck's paging audit, on made-up page counts only (no network).

Every expected number below was worked out by hand from the pages in this file before the
tests were first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

from linkcheck import paging

# A: total 25, error on page 2. B: total 12, error past its end. C: no total.
# D: total 5, the server answers every page after its end with an error.
MIXED = {1: {"A": 10, "B": 10, "C": 10, "D": 5},
         2: {"A": None, "B": 2, "C": 10, "D": None},
         3: {"A": 5, "B": None, "C": 4, "D": None},
         4: {"D": None}}
MIXED_TOTALS = {"A": 25, "B": 12, "D": 5}
# P loses its whole page 2 with no error; Q is one entry short on page 3.
SILENT = {1: {"P": 10, "Q": 10}, 2: {"P": 0, "Q": 10}, 3: {"P": 10, "Q": 9}}
SILENT_TOTALS = {"P": 30, "Q": 30}


def flag(page, source, kind, entries, want):
    return {"page": page, "source": source, "kind": kind, "entries": entries, "expected": want}


class Expected(unittest.TestCase):
    def test_expected(self):
        self.assertEqual([paging.expected(p, 10, 25) for p in (1, 2, 3, 4)], [10, 10, 5, 0])
        self.assertEqual(paging.expected(1, 10, 0), 0)


class Mixed(unittest.TestCase):
    def setUp(self):
        self.report = paging.audit(MIXED, 10, MIXED_TOTALS)
        self.src = self.report["sources"]

    def test_flags(self):
        self.assertEqual(self.report["flags"], [flag(2, "A", "error", None, 10)])
        self.assertEqual(self.report["flag_counts"], {"error": 1})
        self.assertEqual((self.report["pages"], self.report["last_page"],
                          self.report["missing_pages"], self.report["whole_page_failures"]),
                         (4, 4, [], []))

    def test_error_page_is_explained(self):
        a = self.src["A"]
        self.assertEqual((a["total"], a["served"], a["error_pages"], a["unexplained"]),
                         (25, 15, [2], 0))
        self.assertEqual(a["lost"], {"error_pages": 10, "short_pages": 0, "missing_pages": 0,
                                     "pages_not_walked": 0})

    def test_errors_past_end_lose_nothing(self):
        self.assertEqual((self.src["B"]["errors_past_end"], self.src["B"]["served"],
                          self.src["B"]["unexplained"]), (1, 12, 0))
        self.assertEqual((self.src["D"]["errors_past_end"], self.src["D"]["error_pages"],
                          self.src["D"]["unexplained"]), (3, [], 0))

    def test_no_total(self):
        c = self.src["C"]
        self.assertEqual((c["total"], c["served"], c["not_judged"], c["errors_not_judged"],
                          c["unexplained"]), (None, 24, 2, 0, None))
        self.assertEqual(sorted(self.src), ["A", "B", "C", "D"])


class Silent(unittest.TestCase):
    def test_short_pages_with_totals(self):
        report = paging.audit(SILENT, 10, SILENT_TOTALS)
        self.assertEqual(report["flags"], [flag(2, "P", "short", 0, 10),
                                           flag(3, "Q", "short", 9, 10)])
        p, q = report["sources"]["P"], report["sources"]["Q"]
        self.assertEqual((p["served"], p["short_pages"], p["lost"]["short_pages"],
                          p["unexplained"]), (20, [[2, 10]], 10, 0))
        self.assertEqual((q["served"], q["short_pages"], q["unexplained"]), (29, [[3, 1]], 0))

    def test_short_page_found_without_totals(self):
        report = paging.audit(SILENT, 10)
        self.assertEqual(report["flags"], [flag(2, "P", "short", 0, 10)])
        self.assertEqual(report["sources"]["P"]["not_judged"], 1)
        self.assertIsNone(report["sources"]["Q"]["unexplained"])


class Gaps(unittest.TestCase):
    def test_over_whole_failure_missing_and_unwalked(self):
        report = paging.audit({1: {"E": 12}, 2: None, 4: {"E": 10}}, 10, {"E": 50})
        self.assertEqual(report["flags"], [flag(1, "E", "over", 12, 10),
                                           flag(2, "E", "error", None, 10)])
        self.assertEqual((report["pages"], report["last_page"], report["missing_pages"],
                          report["whole_page_failures"]), (3, 4, [3], [2]))
        e = report["sources"]["E"]
        self.assertEqual((e["served"], e["excess"], e["over_pages"], e["unexplained"]),
                         (22, 2, [[1, 2]], 0))
        self.assertEqual(e["lost"], {"error_pages": 10, "short_pages": 0, "missing_pages": 10,
                                     "pages_not_walked": 10})

    def test_bad_input(self):
        for args in (({1: {"A": 1}}, 0), ({0: {"A": 1}}, 10), ({1: {"A": -1}}, 10),
                     ({1: {"A": True}}, 10), ({1: ["A"]}, 10), ({1: {"A": 1}}, 10, {"A": -5})):
            with self.assertRaises(ValueError):
                paging.audit(*args)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_main(self):
        pages = self.write("pages.jsonl", "".join(json.dumps({"page": n, "counts": c}) + "\n"
                                                  for n, c in sorted(SILENT.items())))
        totals = self.write("totals.json", json.dumps(SILENT_TOTALS))
        out = os.path.join(self.tmp, "report.json")
        self.assertEqual(paging.main(["--pages", pages, "--per-page", "10", "--totals", totals,
                                      "--out", out]), 0)
        with open(out, encoding="utf-8") as fh:
            report = json.load(fh)
        self.assertEqual(report["flag_counts"], {"short": 2})
        self.assertEqual(report["sources"]["P"]["unexplained"], 0)

    def test_duplicate_page(self):
        pages = self.write("dup.jsonl", '{"page": 1, "counts": {}}\n{"page": 1, "counts": {}}\n')
        with self.assertRaises(ValueError):
            paging.read_pages(pages)


if __name__ == "__main__":
    unittest.main()
