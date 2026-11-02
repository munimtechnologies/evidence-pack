# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.brief_tables (synthetic HTML; no network)."""
import json
import os
import tempfile
import unittest

from meps import brief_tables as b

PAGE = (
    '<html><body><table class="layout"><tr><td><img src="logo.gif"> Font size S M L</td></tr>'
    '<tr><td><h2>Findings</h2><p>As shown in Figure 2, 42.8 percent of women.</p>'
    '<p><b>Figure 1. Percentage of women with diagnosed osteoporosis, 2022</b></p>'
    '<img alt="Figure data for accessible table follows the image" src="f1.gif">'
    '<table><tr><th>Age Group</th><th>Percentage (%)</th></tr>'
    '<tr><td>Age 50 and older</td><td>21.5</td></tr>'
    '<tr><td>Age 50-64</td><td>9.2</td></tr></table>'
    '<p>Figure 2: Percentage distribution of spending by type, 2013</p>'
    '<table>'
    '<tr><td></td><td colspan="2">Less than 65</td><td>65+</td></tr>'
    '<tr><td></td><td>Any private</td><td>Public only</td><td>Medicare only</td></tr>'
    '<tr><td>Inpatient</td><td>60.0</td><td>50.1</td><td>40.0</td></tr>'
    '<tr><td>Other<br>services</td><td>40.0</td><td>{X}</td><td>60.0</td></tr>'
    '<tr><td colspan="4">Source: AHRQ, MEPS, 2013.</td></tr>'
    '</table>'
    '<table><tr><td>Contact</td><td>FAQ</td></tr></table>'
    '</td></tr></table>'
    '<table><tr><td>Page last reviewed</td><td>2024</td></tr></table>'
    '</body></html>')


def page(x="49.9"):
    return PAGE.replace("{X}", x)


def rec(label, vals):
    return {"label": label, "n_numeric": len(vals), "cells": [{"value": v} for v in vals]}


class TestNumber(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(b.number("42.8"), (42.8, 1))
        self.assertEqual(b.number(" $1,234 "), (1234.0, 0))
        self.assertEqual(b.number("12 %"), (12.0, 0))
        self.assertEqual(b.number("45.3*"), (45.3, 1))
        self.assertEqual(b.number("-0.5"), (-0.5, 1))
        self.assertEqual(b.number("2,010"), (2010.0, 0))
        for t in ("--", "", None, "Age 50", "1,23", "65+"):
            self.assertIsNone(b.number(t))


class TestParse(unittest.TestCase):
    def test_page(self):
        recs = b.parse_page(page())
        self.assertEqual([r["label"] for r in recs], ["Figure 1", "Figure 2"])
        self.assertEqual([r["index"] for r in recs], [1, 2])
        t1, t2 = recs
        self.assertEqual(t1["title"], "Figure 1. Percentage of women with diagnosed osteoporosis, 2022")
        self.assertEqual([c["value"] for c in t1["cells"]], [21.5, 9.2])
        self.assertEqual(t1["cells"][0]["col_label"], "Percentage (%)")
        self.assertEqual(t1["cells"][1]["row_label"], "Age 50-64")
        self.assertEqual(t1["cells"][0]["decimals"], 1)
        self.assertIsNone(t1["sum_check"])
        self.assertEqual(t2["title"], "Figure 2: Percentage distribution of spending by type, 2013")
        self.assertEqual(t2["n_numeric"], 6)
        self.assertEqual(t2["n_rows"], 5)
        self.assertEqual(t2["n_cols"], 4)
        self.assertEqual([c["col_label"] for c in t2["cells"][:3]],
                         ["Less than 65 / Any private", "Less than 65 / Public only", "65+ / Medicare only"])
        self.assertEqual(t2["cells"][3]["row_label"], "Other services")
        self.assertEqual([c["value"] for c in t2["cells"]], [60.0, 50.1, 40.0, 40.0, 49.9, 60.0])
        self.assertEqual(t2["sum_check"], {"cols_ok": 3, "cols": 3, "rows_ok": 0, "rows": 2, "passed": True})

    def test_sum_flag(self):
        t2 = b.parse_page(page("48.9"))[1]
        self.assertFalse(t2["sum_check"]["passed"])
        self.assertEqual(t2["sum_check"]["cols_ok"], 2)

    def test_caption_and_money(self):
        recs = b.parse_page('<p>See Table 9.</p><table><caption>Table 3. Mean expense</caption>'
                            '<tr><td>All</td><td>$1,234</td></tr></table>')
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["label"], "Table 3")
        self.assertEqual(recs[0]["cells"][0]["value"], 1234.0)
        self.assertEqual(recs[0]["cells"][0]["decimals"], 0)
        self.assertEqual(recs[0]["cells"][0]["col_label"], "")

    def test_title_inside_table(self):
        recs = b.parse_page('<p>Figure 9. Old</p><table><tr><td colspan="2">Figure 4. Mean expense, 2019</td></tr>'
                            '<tr><td>Group</td><td>Mean ($)</td></tr><tr><td>All</td><td>5,000</td></tr></table>')
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["label"], "Figure 4")
        self.assertTrue(recs[0]["title"].startswith("Figure 4. Mean expense, 2019"))
        self.assertEqual(recs[0]["cells"][0]["col_label"], "Mean ($)")
        self.assertEqual(recs[0]["cells"][0]["value"], 5000.0)

    def test_unclosed_cells(self):
        recs = b.parse_page('<table><tr><td>A<td>1.5<tr><td>B<td>2.5</table>')
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["label"], "")
        self.assertEqual([c["value"] for c in recs[0]["cells"]], [1.5, 2.5])
        self.assertEqual([c["row_label"] for c in recs[0]["cells"]], ["A", "B"])

    def test_decode(self):
        text, raw = b._decode(b"caf\xe9")
        self.assertEqual(text[:3], "caf")
        self.assertEqual(ord(text[3]), 0xE9)
        self.assertEqual(raw, b"caf\xe9")


class TestGateGrade(unittest.TestCase):
    def pages(self):
        sizes = [3, 3, 2, 3, 2, 4, 6, 3]
        recs, k = [], 0
        for i, s in enumerate(sizes):
            recs.append(rec("Figure %d" % (i + 1), b.G569[k:k + s]))
            k += s
        p491 = [rec("Figure 1", [1.0] * 15), rec("Figure 2", [1.0] * 30), rec("Figure 3", [1.0] * 15)]
        return {569: recs + [rec("", [5.0])], 491: p491}

    def test_gate(self):
        p = self.pages()
        g = b.gate(p)
        self.assertTrue(g["passed"])
        self.assertEqual(g["G1_values_read"], 26)
        p[569][0]["cells"][0]["value"] = 21.4
        self.assertFalse(b.gate(p)["passed"])
        p = self.pages()
        p[491] = p[491][:2]
        g = b.gate(p)
        self.assertFalse(g["passed"])
        self.assertEqual(g["G2_counts"], [15, 30])
        self.assertFalse(b.gate({})["passed"])

    def test_grade(self):
        years = dict((n, 2017) for n in b.R2_ELIGIBLE)
        years[10] = 2003
        pages = dict((n, [rec("Figure 1", [1.0])]) for n in b.R2_ELIGIBLE)
        pages[10] = []
        g = b.grade(pages, years)
        self.assertEqual(g["P1"]["grade"], "held")
        self.assertEqual(g["P1"]["n_2016_on"], 11)
        self.assertEqual(g["P2"]["grade"], "held")
        pages[491] = []
        pages[493] = None
        g = b.grade(pages, years)
        self.assertEqual(g["P1"]["n_2016_on"], 10)
        self.assertEqual(g["P1"]["with_table"], 9)
        self.assertEqual(g["P1"]["grade"], "held")
        self.assertEqual(g["P2"]["r2_without_table"], [491, 493])
        self.assertEqual(g["P2"]["grade"], "failed")
        pages[496] = []
        g = b.grade(pages, years)
        self.assertEqual(g["P1"]["grade"], "failed")


class TestBuild(unittest.TestCase):
    def fake(self, robots, fail_once=False):
        state = {"n": 0}

        def get(url):
            if url == b.ROBOTS:
                return robots.encode("utf-8")
            state["n"] += 1
            if fail_once and state["n"] == 1:
                raise OSError("boom")
            return page().encode("utf-8")
        return get

    def test_robots_allow(self):
        waits = []
        pages, err, sha = b.build([569, 491], get=self.fake("User-agent: *\nDisallow: /mepsweb/data_files/pufs/\n"),
                                  pause=waits.append)
        self.assertEqual(err, {})
        self.assertEqual(waits, [3])
        self.assertEqual(len(pages[569]), 2)
        self.assertEqual(len(sha[491]), 64)

    def test_robots_block(self):
        pages, err, sha = b.build([569, 491], get=self.fake("User-agent: *\nDisallow: /data_files/\n"),
                                  pause=lambda s: None)
        self.assertEqual(len(err), 2)
        self.assertIsNone(pages[569])
        self.assertEqual(sha, {})

    def test_retry(self):
        waits = []
        pages, err, sha = b.build([569], get=self.fake("", fail_once=True), pause=waits.append,
                                  allowed=lambda u: True)
        self.assertEqual(err, {})
        self.assertEqual(waits, [30])
        self.assertEqual(len(pages[569]), 2)

    def test_main(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "briefs.csv")
        with open(p, "w", encoding="utf-8") as f:
            f.write("number,year,status\n569,2022,ok\n491,2016,ok\n10,2003,NOPAGE\n")
        out_dir = os.path.join(tmp, "out")
        rc = b.main(["--briefs", p, "--out-dir", out_dir], get=self.fake(""), pause=lambda s: None,
                    allowed=lambda u: True)
        self.assertEqual(rc, 0)
        with open(os.path.join(out_dir, "brief-tables.json")) as f:
            out = json.load(f)
        self.assertIsNone(out["error"])
        self.assertEqual(out["n_briefs"], 2)
        self.assertEqual(out["n_fetched"], 2)
        self.assertFalse(out["gate"]["passed"])
        self.assertEqual(out["totals"], {"tables": 4, "cells": 16, "briefs_with_table": 2})
        self.assertEqual(out["cell_files"], ["st400-499.csv", "st500-599.csv"])
        self.assertEqual(out["sum_check"]["distribution_tables"], 2)
        self.assertEqual(out["sum_check"]["flagged"], [])
        self.assertEqual(out["per_brief"]["569"]["cells"], 8)
        with open(os.path.join(out_dir, "tables.csv")) as f:
            self.assertTrue(f.readline().startswith("number,year,index,label,title"))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "cells", "st500-599.csv")))


if __name__ == "__main__":
    unittest.main()
