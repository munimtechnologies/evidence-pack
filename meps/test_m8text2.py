# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for census M8 v0.2 (meps/m8text2.py). No network; census M3's parser is replaced by fixed cells."""
import csv
import json
import os
import tempfile
import unittest
from unittest import mock

from meps import m8text2 as m8

# An older-template page: the body sits in a layout table, the figure's data table is nested inside it.
OLD = """<html><body>
<table width="100%"><tr><td class="nav">Menu</td><td>
<h1>Statistical Brief #9</h1>
<p><b>Findings</b></p>
<p>In 2020, 89.2 percent of employees were offered a deductible (figure 1). Rates fell by 16.1 percent.</p>
<p>Coverage was 4.0 percent<br><br>Nonmetropolitan fair or poor health was 17.7 percent (figure 1).</p>
<table><caption>Figure 1. Shares</caption>
<tr><th></th><th>Fair</th><th>Poor</th></tr>
<tr><td>All</td><td>13.0</td><td>4.7</td></tr>
<tr><td>Change</td><td>-16.1</td><td>86.2</td></tr>
</table>
<p>Definitions</p>
<p>A sensitivity result was 43.2 percent (figure 1).</p>
</td></tr></table>
</body></html>"""

RESUME = ("<p>Definitions</p><p>Note 1.5 here (figure 1).</p><h3>Findings (figure 1)</h3>"
          "<p>Rate was 4.7 percent.</p>")
BOUNDPAGE = "<p>Spending was less than $0.1 billion and 4.7 percent (figure 1).</p>"


def cell(v, d, row, col, tindex=1, section=""):
    return {"value": v, "decimals": d, "row": row, "col": col, "tindex": tindex, "section": section}


CELLS = [cell(13.0, 1, 1, 1), cell(4.7, 1, 1, 2), cell(-16.1, 1, 2, 1), cell(86.2, 1, 2, 2)]
FIGS = {("f", 1): CELLS}


def num(s):
    return m8.numbers(s)[0]


class TestPure(unittest.TestCase):
    def test_parse_refs(self):
        self.assertEqual(m8.parse_refs("listed in figure 5, 7.7 percent"), [("f", 5)])
        self.assertEqual(m8.parse_refs("rose (figures 11 and 12)."), [("f", 11), ("f", 12)])
        self.assertEqual(m8.parse_refs("Age (figures 6" + chr(0x2013) + "9)"), [("f", 6), ("f", 7), ("f", 8),
                                                                                   ("f", 9)])
        self.assertEqual(m8.parse_refs("shown in figure 1."), [("f", 1)])
        self.assertEqual(m8.parse_refs("no reference here"), [])

    def test_numbers_bound(self):
        got = m8.numbers("less than $0.1 billion and 0.2")
        self.assertEqual([(n["text"], n["bound"]) for n in got], [("0.1", True), ("0.2", False)])
        self.assertFalse(num("more than 4 groups had 3.5")["bound"])

    def test_stop_heading(self):
        self.assertTrue(m8.stop_heading("Definitions"))
        self.assertTrue(m8.stop_heading("Data Source:"))
        self.assertTrue(m8.stop_heading("About MEPS-HC"))
        self.assertTrue(m8.stop_heading("Suggested Citation"))
        self.assertFalse(m8.stop_heading("Findings"))

    def test_classify(self):
        self.assertEqual(m8.classify(num("16.1"), CELLS, set()), ("match", []))
        self.assertEqual(m8.classify(num("17.7"), CELLS, set()), ("derived", []))
        self.assertEqual(m8.classify(num("8.3"), CELLS, set()), ("derived", []))
        self.assertEqual(m8.classify(num("29.1"), CELLS, set()), ("derived", []))
        self.assertEqual(m8.classify(num("70.1"), CELLS, set()), ("derived", []))
        self.assertEqual(m8.classify(num("90.9"), CELLS, set()), ("unmatched", []))
        self.assertEqual(m8.classify(num("89.2"), CELLS, set()), ("unmatched", ["86.2"]))
        self.assertEqual(m8.classify(num("89.2"), CELLS, {"86.2"}), ("unmatched", []))
        self.assertEqual(m8.classify(num("16.9"), CELLS, set()), ("unmatched", ["16.1"]))

    def test_text_blocks_layout(self):
        b = m8.text_blocks(OLD)
        self.assertEqual(len(b), 8)
        self.assertEqual(b[0], ("text", "Menu"))
        self.assertEqual(b[1], ("h1", "Statistical Brief #9"))
        self.assertEqual(b[4], ("p", "Coverage was 4.0 percent"))
        self.assertEqual(b[5][1], "Nonmetropolitan fair or poor health was 17.7 percent (figure 1).")
        self.assertEqual(b[6], ("p", "Definitions"))
        joined = " ".join(t for _, t in b)
        self.assertNotIn("Figure 1. Shares", joined)
        self.assertNotIn("13.0", joined)

    def test_check_page_layout(self):
        rows, st = m8.check_page(OLD, figs=FIGS)
        self.assertEqual(st, {"blocks": 8, "numbers": 4, "checked": 3, "bounds": 0, "stopped": 1})
        got = [(r["text"], r["verdict"], r["near"], r["refs"]) for r in rows]
        self.assertEqual(got, [("89.2", "unmatched", "86.2", "f1"), ("16.1", "match", "", "f1"),
                               ("17.7", "derived", "", "f1")])

    def test_check_page_resume_and_bound(self):
        rows, st = m8.check_page(RESUME, figs=FIGS)
        self.assertEqual(st, {"blocks": 4, "numbers": 1, "checked": 1, "bounds": 0, "stopped": 1})
        self.assertEqual([(r["text"], r["verdict"]) for r in rows], [("4.7", "match")])
        rows, st = m8.check_page(BOUNDPAGE, figs=FIGS)
        self.assertEqual((st["numbers"], st["checked"], st["bounds"]), (2, 1, 1))
        self.assertEqual([(r["text"], r["verdict"]) for r in rows], [("4.7", "match")])

    def test_gate(self):
        res = {n: ([{"x": 1}], {}) for n in m8.DEV_OLD[:9]}
        res.update({n: ([], {}) for n in m8.DEV_OLD[9:]})
        g = m8.gate_check(res)
        self.assertEqual((g["with_checked_numbers"], g["passed"]), (9, True))
        self.assertEqual(g["without"], m8.DEV_OLD[9:])
        del res[m8.DEV_OLD[0]]
        self.assertFalse(m8.gate_check(res)["passed"])


class TestMain(unittest.TestCase):
    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            tp = os.path.join(d, "tables.csv")
            with open(tp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["number", "year", "index", "label", "title", "n_rows", "n_cols", "n_numeric",
                            "sum_check_passed"])
                w.writerow([536, 2021, 1, "Figure 1", "x", 3, 3, 4, ""])
                w.writerow([567, 2025, 1, "Figure 1", "y", 3, 3, 4, ""])
            out = os.path.join(d, "out")
            with mock.patch.object(m8, "figure_cells", lambda h: FIGS):
                rc = m8.main(["--tables", tp, "--out-dir", out], get=lambda u: OLD.encode("utf-8"),
                             pause=lambda s: None, allowed=lambda u: True)
            self.assertEqual(rc, 0)
            with open(os.path.join(out, "m8v2-summary.json")) as f:
                s = json.load(f)
            self.assertEqual((s["briefs"], s["fetched"], s["numbers_checked"], s["flags"]), (2, 2, 6, 2))
            self.assertEqual(s["by_verdict"], {"match": 2, "derived": 2, "unmatched": 2})
            self.assertEqual(s["controls"], {"567": False, "536": True})
            self.assertEqual((s["matched_share"], s["matched_share_old"], s["matched_share_new"]),
                             (0.6667, 0.6667, 0.6667))
            self.assertEqual((s["coverage"], s["sample_size"]), (1.0, 1))
            self.assertEqual((s["gate"]["with_checked_numbers"], s["gate"]["passed"]), (1, False))
            with open(os.path.join(out, "m8v2-flags.csv"), newline="", encoding="utf-8") as f:
                fl = {r["number"]: r for r in csv.DictReader(f)}
            self.assertEqual((fl["536"]["control"], fl["536"]["check_rank"]), ("True", ""))
            self.assertEqual((fl["567"]["control"], fl["567"]["check_rank"], fl["567"]["in_sample"]),
                             ("False", "1", "True"))


if __name__ == "__main__":
    unittest.main()
