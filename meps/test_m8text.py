# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for census M8 (meps/m8text.py). No network."""
import csv
import json
import os
import tempfile
import unittest

from meps import m8text as m8

try:
    from meps import brief_tables  # noqa: F401
    HAVE_BT = True
except ImportError:
    HAVE_BT = False

PAGE = """<html><body>
<h2>Highlights</h2>
<ul><li>In 2020, 4.0 percent of adults did X.</li></ul>
<h3>Overall and sex (Figure 1)</h3>
<p>In 2020, 4.0 percent used A, and 1.5 percent used both. Use was higher among women (2.0%) than men (0.9%).</p>
<p>Among men, the difference was 0.8 points. About 98.5 percent did not use both.</p>
<table><caption>Figure 1. Use, overall and by sex</caption>
<tr><th></th><th>A only (%)</th><th>Both (%)</th></tr>
<tr><td>Overall</td><td>4.0</td><td>1.5</td></tr>
<tr><td>Men</td><td>2.7</td><td>1.9</td></tr>
<tr><td>Women</td><td>5.1</td><td>2.0</td></tr>
</table>
<p>Source: survey 2021-22.</p>
<p>Spending rose to 12.3 percent in 2020, from 11.1 percent (figure 2) and 7.7 in a group not shown.</p>
<table><caption>Figure 2. Spending</caption>
<tr><th></th><th>2019</th><th>2020</th></tr>
<tr><td>All</td><td>11.1</td><td>12.8</td></tr>
</table>
</body></html>"""


def cell(v, d, row, col, tindex=1, section=""):
    return {"value": v, "decimals": d, "row": row, "col": col, "tindex": tindex, "section": section}


class TestPure(unittest.TestCase):
    def test_parse_refs(self):
        self.assertEqual(m8.parse_refs("rose (figures 11 and 12)."), [("f", 11), ("f", 12)])
        self.assertEqual(m8.parse_refs("Age (figures 6" + chr(0x2013) + "9)"), [("f", 6), ("f", 7), ("f", 8),
                                                                                   ("f", 9)])
        self.assertEqual(m8.parse_refs("Figures 1, 3, and 5 show"), [("f", 1), ("f", 3), ("f", 5)])
        self.assertEqual(m8.parse_refs("from 11.1 percent (figure 2) and 7.7"), [("f", 2)])
        self.assertEqual(m8.parse_refs("see Table 2 and figure 4"), [("f", 4), ("t", 2)])
        self.assertEqual(m8.parse_refs("Overall and sex (Figure 1)"), [("f", 1)])
        self.assertEqual(m8.parse_refs("no reference here"), [])

    def test_numbers(self):
        got = m8.numbers("rose 1,234.5 from 0.9% in 2020, v1.2 and 3.4.5 end 89.2.")
        self.assertEqual([n["text"] for n in got], ["1,234.5", "0.9", "89.2"])
        self.assertEqual((got[0]["value"], got[0]["decimals"], got[0]["digits"]), (1234.5, 1, "12345"))
        self.assertEqual(got[1]["digits"], "09")

    def test_near_miss(self):
        self.assertTrue(m8.near_miss("09", "19"))
        self.assertTrue(m8.near_miss("123", "132"))
        self.assertFalse(m8.near_miss("123", "321"))
        self.assertFalse(m8.near_miss("12", "123"))
        self.assertFalse(m8.near_miss("12", "12"))
        self.assertFalse(m8.near_miss("123", "145"))

    def test_heading_like(self):
        self.assertTrue(m8.heading_like("h3", "Results 4.5", m8.numbers("Results 4.5")))
        self.assertTrue(m8.heading_like("p", "Overall and sex (Figure 1)", []))
        self.assertFalse(m8.heading_like("p", "In 2020, 4.0 percent", m8.numbers("In 2020, 4.0 percent")))

    def test_classify(self):
        cells = [cell(4.0, 1, 0, 1), cell(1.5, 1, 0, 2), cell(2.7, 1, 1, 1), cell(1.9, 1, 1, 2),
                 cell(5.1, 1, 2, 1), cell(2.0, 1, 2, 2)]

        def num(s):
            return m8.numbers(s)[0]

        self.assertEqual(m8.classify(num("4.0"), cells, set()), ("match", []))
        self.assertEqual(m8.classify(num("98.5"), cells, set()), ("derived", []))
        self.assertEqual(m8.classify(num("0.8"), cells, set()), ("derived", []))
        self.assertEqual(m8.classify(num("0.9"), cells, {"0.9"}), ("unmatched", ["1.9"]))
        self.assertEqual(m8.classify(num("0.9"), cells, {"0.9", "1.9"}), ("unmatched", []))
        self.assertEqual(m8.classify(num("7.7"), cells, set()), ("unmatched", ["2.7"]))
        self.assertEqual(m8.classify(num("17.7"), cells, set()), ("unmatched", []))
        # one-decimal text against a two-decimal cell: rounding match
        self.assertEqual(m8.classify(num("35.5"), [cell(35.47, 2, 0, 1)], set()), ("match", []))

    def test_text_blocks(self):
        b = m8.text_blocks(PAGE)
        self.assertEqual([t for t, _ in b], ["h2", "li", "h3", "p", "p", "p", "p"])
        self.assertEqual(b[5][1], "Source: survey 2021-22.")
        self.assertNotIn("Figure 1. Use", " ".join(t for _, t in b))


@unittest.skipUnless(HAVE_BT, "meps/brief_tables.py not present")
class TestPage(unittest.TestCase):
    def test_check_page(self):
        rows, st = m8.check_page(PAGE)
        self.assertEqual(st, {"blocks": 7, "numbers": 10, "checked": 9})
        got = [(r["text"], r["verdict"], r["near"], r["refs"]) for r in rows]
        self.assertEqual(got, [("4.0", "match", "", "f1"), ("1.5", "match", "", "f1"), ("2.0", "match", "", "f1"),
                               ("0.9", "unmatched", "1.9", "f1"), ("0.8", "derived", "", "f1"),
                               ("98.5", "derived", "", "f1"), ("12.3", "unmatched", "12.8", "f2"),
                               ("11.1", "match", "", "f2"), ("7.7", "unmatched", "", "f2")])

    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            tp = os.path.join(d, "tables.csv")
            with open(tp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["number", "year", "index", "label", "title", "n_rows", "n_cols", "n_numeric",
                            "sum_check_passed"])
                w.writerow([567, 2025, 1, "Figure 1", "x", 4, 3, 6, ""])
                w.writerow([567, 2025, 2, "Figure 2", "y", 2, 3, 2, ""])
            out = os.path.join(d, "out")
            rc = m8.main(["--tables", tp, "--out-dir", out], get=lambda u: PAGE.encode("utf-8"),
                         pause=lambda s: None, allowed=lambda u: True)
            self.assertEqual(rc, 0)
            with open(os.path.join(out, "m8-summary.json")) as f:
                s = json.load(f)
            self.assertEqual((s["briefs"], s["fetched"], s["numbers_checked"], s["flags"]), (1, 1, 9, 2))
            self.assertEqual(s["by_verdict"], {"match": 4, "derived": 2, "unmatched": 3})
            self.assertEqual(s["controls"], {"567": True, "536": False})
            self.assertEqual(s["sample_size"], 1)
            with open(os.path.join(out, "m8-flags.csv"), newline="", encoding="utf-8") as f:
                fl = {r["text"]: r for r in csv.DictReader(f)}
            self.assertEqual((fl["0.9"]["control"], fl["0.9"]["check_rank"]), ("True", ""))
            self.assertEqual((fl["12.3"]["control"], fl["12.3"]["check_rank"], fl["12.3"]["in_sample"]),
                             ("False", "1", "True"))


if __name__ == "__main__":
    unittest.main()
