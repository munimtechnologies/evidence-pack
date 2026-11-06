# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.m4titles (no network, no MEPS file). Every expected value is worked by hand."""
import csv
import json
import os
import tempfile
import unittest

from meps import m4titles

T5 = "Figure 5: Percentage of persons by race/ethnicity and percentile of spending, 2018"
T6 = "Figure 6: Percentage of persons by race/ethnicity and percentile of spending, 2018"
T7 = "Figure 7: Percentage of persons by source of payment and percentile of spending, 2018"


def cell(r, c, t, num="533", table="5", col="1"):
    return {"number": num, "table": table, "label": "", "row": "0", "col": col, "section": "",
            "row_label": r, "col_label": c, "text": t, "value": t, "decimals": "1"}


class TestKey(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(m4titles.title_key(T5, ["Overall percentage"]),
                         "percentage of persons by race/ethnicity and percentile of spending, 2018")
        self.assertEqual(m4titles.title_key(T5, []), m4titles.title_key(T6, ["Overall percentage"]))

    def test_appended_headers(self):
        a = m4titles.title_key("Figure 1a. Payments for hospital inpatient stays, 2010 Prescribed medicines "
                               "Hospital inpatient Ambulatory care Other", ["Prescribed medicines",
                                                                             "Hospital inpatient"])
        b = m4titles.title_key("Figure 1b. Payments for hospital inpatient stays, 2010 Private insurance Medicare",
                               ["Private insurance"])
        self.assertEqual(a, "payments for hospital inpatient stays, 2010")
        self.assertEqual(a, b)

    def test_min_cut(self):
        self.assertEqual(m4titles.title_key("Table 2: Total expenses by total", ["Total"]), "total expenses by")


class TestClassify(unittest.TestCase):
    def test_classes(self):
        ca = [cell("A", "X", "1.0"), cell("B", "X", "2.0")]
        self.assertEqual(m4titles.classify(ca, [dict(c) for c in ca]), "identical_data")
        self.assertEqual(m4titles.classify(ca, [cell("A", "X", "1.5"), cell("B", "X", "2.0")]),
                         "same_labels_different_values")
        self.assertEqual(m4titles.classify(ca, [cell("C", "X", "1.0"), cell("B", "X", "2.0")]),
                         "different_labels")
        self.assertEqual(m4titles.classify(ca, [cell("A*", "X", "1.0"), cell("B", "X ", "2.0")]),
                         "identical_data")


class TestCensus(unittest.TestCase):
    def _data(self):
        tables = [{"number": "533", "year": "2021", "index": "5", "label": "Figure 5", "title": T5},
                  {"number": "533", "year": "2021", "index": "6", "label": "Figure 6", "title": T6},
                  {"number": "533", "year": "2021", "index": "7", "label": "Figure 7", "title": T7},
                  {"number": "10", "year": "2003", "index": "1", "label": "Figure 1", "title": "Figure 1: Short"}]
        cells = {("533", "5"): [cell("Hispanic", "Overall percentage", "18.5")],
                 ("533", "6"): [cell("Prescribed medicines", "Overall percentage", "22.9", table="6")],
                 ("533", "7"): [cell("Private", "Overall percentage", "40.0", table="7")]}
        return tables, cells

    def test_census(self):
        tables, cells = self._data()
        s, pairs, short = m4titles.census(tables, cells)
        self.assertEqual(s["tables"], 4)
        self.assertEqual(s["briefs"], 2)
        self.assertEqual(s["short_keys"], 1)
        self.assertEqual(s["pairs"], 1)
        self.assertEqual(s["briefs_with_pairs"], 1)
        self.assertEqual(s["by_class"], {"different_labels": 1})
        self.assertEqual(s["positive_control_533_f5_f6"], "different_labels")
        self.assertEqual((pairs[0]["label_a"], pairs[0]["label_b"]), ("Figure 5", "Figure 6"))
        self.assertEqual(short[0], ["10", "Figure 1", "short"])

    def test_main(self):
        tables, cells = self._data()
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
            with open(os.path.join(cd, "st500-599.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(cell("a", "b", "c").keys()))
                w.writeheader()
                for cs in cells.values():
                    w.writerows(cs)
            out = os.path.join(d, "out")
            rc = m4titles.main(["--tables", tp, "--cells-dir", cd, "--out-dir", out])
            with open(os.path.join(out, "m4-summary.json")) as f:
                s = json.load(f)
            with open(os.path.join(out, "m4-candidates.csv"), newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(rc, 0)
        self.assertEqual(s["pairs"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label_a"], "Figure 5")
        self.assertEqual(rows[0]["class"], "different_labels")


if __name__ == "__main__":
    unittest.main()
