# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.m5ages (no network, no MEPS file). Every expected value is worked by hand."""
import csv
import json
import os
import tempfile
import unittest

from meps import m5ages

T = m5ages.TOP
T170 = ("Figure 5. Percentage of women age 40 and over with breast cancer screening in the past two years, "
        "by age and insurance status, 2005")


def cell(num, table, row_label, col_label):
    return {"number": num, "table": table, "label": "", "row": "0", "col": "1", "section": "",
            "row_label": row_label, "col_label": col_label, "text": "1.0", "value": "1.0", "decimals": "1"}


def data():
    tables = [{"number": "170", "year": "2007", "index": "5", "label": "Figure 5", "title": T170},
              {"number": "170", "year": "2007", "index": "6", "label": "Figure 5", "title": T170},
              {"number": "900", "year": "2010", "index": "1", "label": "Figure 1", "title": "Figure 1. Spending by age, 2010"},
              {"number": "901", "year": "2010", "index": "1", "label": "Figure 1", "title": "Figure 1. Coverage by age, 2010"},
              {"number": "902", "year": "2010", "index": "1", "label": "Figure 1",
               "title": "Figure 1. Coverage by weekly hours, 2000"},
              {"number": "903", "year": "2010", "index": "1", "label": "Table 1",
               "title": "Table 1. Coverage by age and income, 2010"},
              {"number": "906", "year": "2010", "index": "1", "label": "Figure 2",
               "title": "Figure 2. Visits by age group, 2010"}]
    cells = {("170", "5"): [cell("170", "5", "Private insurance", "Age 40-65 / Breast exams")],
             ("170", "6"): [cell("170", "6", "Medicare only", "Age 65+ / Breast exams")],
             ("900", "1"): [cell("900", "1", "Dollars", "18-44"), cell("900", "1", "Dollars", "45-64"),
                            cell("900", "1", "Dollars", "65+")],
             ("901", "1"): [cell("901", "1", "Percent", "Ages 0-17"), cell("901", "1", "Percent", "Ages 19-64")],
             ("902", "1"): [cell("902", "1", "Percent", "1-20"), cell("902", "1", "Percent", "20-34")],
             ("903", "1"): [cell("903", "1", "Income 100-199 percent", "Age 18-64"),
                            cell("903", "1", "Income 200-399 percent", "Age 65+")],
             ("906", "1"): [cell("906", "1", "Children 0-18", "Percent"), cell("906", "1", "Adults 18-64", "Percent")]}
    return tables, cells


class TestBands(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(m5ages.bands("Age 40-65"), [(40, 65)])
        self.assertEqual(m5ages.bands("Age 65+"), [(65, T)])
        self.assertEqual(m5ages.bands("65 +"), [(65, T)])
        self.assertEqual(m5ages.bands("All women age 40 and over"), [(40, T)])
        self.assertEqual(m5ages.bands("Persons 65 years and older"), [(65, T)])
        self.assertEqual(m5ages.bands("Under age 18"), [(0, 17)])
        self.assertEqual(m5ages.bands("All persons <65 years"), [(0, 64)])
        self.assertEqual(m5ages.bands("Ages 18 to 44"), [(18, 44)])
        self.assertEqual(m5ages.bands("Age 18" + chr(0x2013) + "44"), [(18, 44)])
        self.assertEqual(m5ages.bands("1996-2001"), [])
        self.assertEqual(m5ages.bands("Private"), [])

    def test_age_part(self):
        self.assertTrue(m5ages.is_age_part("Age 18-64", "Figure 1. Coverage, 2010"))
        self.assertTrue(m5ages.is_age_part("18-64", "Figure 1. Coverage by age, 2010"))
        self.assertFalse(m5ages.is_age_part("1-20", "Figure 1. Coverage by weekly hours, 2000"))
        self.assertFalse(m5ages.is_age_part("Income 100-199 percent", "Table 1. Coverage by age and income"))


class TestCheck(unittest.TestCase):
    def test_check(self):
        self.assertEqual(m5ages.check({(40, 65), (65, T)}), [("overlap", (40, 65), (65, T))])
        self.assertEqual(m5ages.check({(18, 44), (45, 64), (65, T)}), [])
        self.assertEqual(m5ages.check({(0, 17), (19, 64)}), [("gap1", (0, 17), (19, 64))])
        self.assertEqual(m5ages.check({(0, 17), (19, 23), (18, 64)}), [])
        self.assertEqual(m5ages.check({(40, T), (40, 49), (50, 64), (65, T)}), [])
        self.assertEqual(m5ages.fmt((65, T)), "65+")
        self.assertEqual(m5ages.fmt((40, 65)), "40-65")


class TestCensus(unittest.TestCase):
    def test_census(self):
        tables, cells = data()
        s, flags, band_rows = m5ages.census(tables, cells)
        self.assertEqual(s["tables"], 7)
        self.assertEqual(s["figures"], 6)
        self.assertEqual(s["figures_with_age_bands"], 5)
        self.assertEqual(s["flags"], 3)
        self.assertEqual(s["figures_flagged"], 3)
        self.assertEqual(s["by_kind"], {"overlap": 2, "gap1": 1})
        self.assertTrue(s["positive_control_170_f5"])
        self.assertEqual([(f["number"], f["kind"], f["band_a"], f["band_b"]) for f in flags],
                         [("170", "overlap", "40-65", "65+"), ("901", "gap1", "0-17", "19-64"),
                          ("906", "overlap", "0-18", "18-64")])
        self.assertEqual(flags[0]["label_a"], "Age 40-65")
        self.assertEqual(band_rows[0], ["170", "2007", "Figure 5", "40-65;65+"])
        self.assertEqual(len(band_rows), 5)

    def test_main(self):
        tables, cells = data()
        with tempfile.TemporaryDirectory() as d:
            tp = os.path.join(d, "tables.csv")
            with open(tp, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["number", "year", "index", "label", "title", "n_rows", "n_cols",
                                                  "n_numeric", "sum_check_passed"])
                w.writeheader()
                for t in tables:
                    w.writerow(dict(t, n_rows="1", n_cols="2", n_numeric="1", sum_check_passed=""))
            cd = os.path.join(d, "cells")
            os.makedirs(cd)
            with open(os.path.join(cd, "st100-199.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(cell("1", "1", "a", "b").keys()))
                w.writeheader()
                for cs in cells.values():
                    w.writerows(cs)
            out = os.path.join(d, "out")
            rc = m5ages.main(["--tables", tp, "--cells-dir", cd, "--out-dir", out])
            with open(os.path.join(out, "m5-summary.json")) as f:
                s = json.load(f)
            with open(os.path.join(out, "m5-flags.csv"), newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(rc, 0)
        self.assertEqual(s["flags"], 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual((rows[0]["number"], rows[0]["kind"], rows[0]["band_a"], rows[0]["band_b"]),
                         ("170", "overlap", "40-65", "65+"))


if __name__ == "__main__":
    unittest.main()
