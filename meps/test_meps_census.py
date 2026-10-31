# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.meps_census (no network)."""
import json
import os
import tempfile
import unittest

from meps import meps_census as mc


class TextTests(unittest.TestCase):
    def test_html_lines(self):
        page = ("<html><head><style>x{}</style></head><body><h2>Data Source</h2>"
                "<p>Uses HC-209 and H206A.</p></body></html>")
        self.assertEqual(mc.html_lines(page), ["Data Source", "Uses HC-209 and H206A."])

    def test_section_heading(self):
        lines = ["Highlights", "x", "Data Source", "This brief uses H209.", "More text.", "Definitions", "Age: y"]
        self.assertEqual(mc.data_source_section(lines), "This brief uses H209. More text.")

    def test_section_inline(self):
        lines = ["Data Source: This Statistical Brief summarizes data from the 2013 MEPS-IC.", "Definitions"]
        self.assertEqual(mc.data_source_section(lines),
                         "This Statistical Brief summarizes data from the 2013 MEPS-IC.")

    def test_section_missing(self):
        self.assertIsNone(mc.data_source_section(["Highlights", "Findings", "Definitions"]))

    def test_year(self):
        lines = ["STATISTICAL BRIEF #100: Trends 1996-2002", "Julie Hudson", "September 2005",
                 "Highlights", "June 2010"]
        self.assertEqual(mc.brief_year(lines), 2005)
        self.assertIsNone(mc.brief_year(["Title", "Highlights", "June 2010"]))


class ClassifyTests(unittest.TestCase):
    def test_norm_id(self):
        self.assertEqual(mc.norm_id("HC-01"), "H1")
        self.assertEqual(mc.norm_id("HC 13"), "H13")
        self.assertEqual(mc.norm_id("H213IF1"), "H213IF1")

    def test_nonpublic_internal(self):
        s = "uses (f) internal versions of the Prescribed Medicines Files (H206A, H213A) and HC-209"
        self.assertEqual(mc.classify(s), ("NONPUBLIC", ["H206A", "H209", "H213A"], ["internal"]))

    def test_ic(self):
        s = ("This Statistical Brief summarizes data from the 2013 MEPS-IC. "
             "special computation runs on the confidential MEPS-IC data")
        self.assertEqual(mc.classify(s), ("IC", [], ["confidential", "special_computation"]))

    def test_puf(self):
        s = "data from HC-01, HC13 and HC-036BRR"
        self.assertEqual(mc.classify(s), ("PUF", ["H1", "H13", "H36BRR"], []))

    def test_model(self):
        s = "The estimates come from the KIDSIM model, built on HC-01"
        self.assertEqual(mc.classify(s), ("NONPUBLIC", ["H1"], ["model"]))

    def test_noid_and_none(self):
        self.assertEqual(mc.classify("Data from the 2019 MEPS household component."), ("NOID", [], []))
        self.assertEqual(mc.classify(None), ("NOSECTION", [], []))


LISTING = ('Results: 1 to 2 of 2 <tr><td><a href="Pub_ProdResults_Details.jsp?pt=Statistical+Brief&opt=1&id=1322">'
           'Recent Changes</a></td><td>2025</td><td><a href="../data_files/publications/st566/stat566.pdf">PDF</a> '
           '<a href="../data_files/publications/st566/stat566.shtml">HTML</a></td></tr>'
           '<tr><td><a href="Pub_ProdResults_Details.jsp?pt=Statistical+Brief&opt=1&id=1100">Old</a></td>'
           '<td>2005</td><td><a href="../data_files/publications/st100/stat100.pdf">PDF</a></td></tr>')

BRIEF = ("<html><body><h1>STATISTICAL BRIEF #566</h1><p>September 2025</p><h2>Highlights</h2><p>x</p>"
         "<h2>Data Source</h2><p>(f) internal versions of the Prescribed Medicines Files (H206A)</p>"
         "<h2>Definitions</h2><p>Adults</p></body></html>")


class ListingTests(unittest.TestCase):
    def test_parse_listing(self):
        self.assertEqual(mc.parse_listing(LISTING), {566: 2025, 100: 2005})
        self.assertEqual(mc.parse_total(LISTING), 2)


class GradeTests(unittest.TestCase):
    def test_grade(self):
        rows = ([{"cls": "IC", "year": 2010, "n_ids": 0}] * 2 + [{"cls": "NOSECTION", "year": None, "n_ids": 0}]
                + [{"cls": "PUF", "year": 2010, "n_ids": 1}] * 6 + [{"cls": "NONPUBLIC", "year": 2020, "n_ids": 1}])
        g = mc.grade(rows, 10)
        self.assertEqual(g["P1"], {"value": 0.9, "grade": "held"})
        self.assertEqual(g["P2"], {"value": 1.0, "grade": "held"})
        self.assertEqual(g["P3"], {"value": 0.1429, "grade": "held"})
        self.assertEqual(g["P4"], {"n_2016_on": 1, "n_to_2015": 6, "grade": "untestable"})
        self.assertEqual(g["P5"], {"value": 0.2222, "grade": "held"})


class RunTests(unittest.TestCase):
    def test_run_offline(self):
        pages = {mc.LIST_URL.format(start=1): (200, LISTING), mc.LIST_URL.format(start=101): (200, LISTING),
                 mc.BRIEF_URL.format(n=566): (200, BRIEF)}
        with tempfile.TemporaryDirectory() as d:
            c = mc.run(d, get=lambda url: pages.get(url, (404, "")), pause=lambda s: None, delay=0, min_listing=1)
            self.assertEqual(c["frame"], "listing")
            self.assertEqual(c["total_listed"], 2)
            self.assertEqual(c["counts"]["NONPUBLIC"], 1)
            self.assertEqual(c["counts"]["NOPAGE"], 1)
            self.assertEqual(c["validation_sample"], [566])
            self.assertEqual(c["year_disagreements"], 0)
            with open(os.path.join(d, "validation-sample.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["numbers"], [566])
            self.assertTrue(os.path.exists(os.path.join(d, "briefs.csv")))


if __name__ == "__main__":
    unittest.main()
