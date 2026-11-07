# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.m7totals (no network, no MEPS file). Every expected value is worked by hand."""
import csv
import json
import os
import tempfile
import unittest

from meps import m7totals as m

T558 = ("Figure 1. Percentage of adults (aged 18 and older) who lacked reliable transportation for daily living in "
        "the past 12 months, by age and race/ethnicity, 2021")


def cell(num, table, row, col, section, row_label, value, decimals="1", col_label="Percent"):
    return {"number": num, "table": table, "label": "", "row": str(row), "col": str(col), "section": section,
            "row_label": row_label, "col_label": col_label, "text": value, "value": value, "decimals": decimals}


def data():
    tables = [{"number": "558", "year": "2021", "index": "1", "label": "Figure 1", "title": T558},
              {"number": "900", "year": "2010", "index": "1", "label": "Figure 1",
               "title": "Figure 1. Mean expenses by sex, 2010"},
              {"number": "901", "year": "2012", "index": "1", "label": "Table 1",
               "title": "Table 1. Percent with a visit, 2012"},
              {"number": "902", "year": "2012", "index": "1", "label": "Figure 2",
               "title": "Figure 2. Number of people (millions), 2012"},
              {"number": "903", "year": "2012", "index": "1", "label": "Figure 3",
               "title": "Figure 3. Percent distribution of expenses by type, 2012"},
              {"number": "904", "year": "2012", "index": "1", "label": "Figure 1", "title": "Figure 1. Net gain, 2012"},
              {"number": "905", "year": "2012", "index": "1", "label": "Figure 1", "title": "Figure 1. Rate, 2012"}]
    cells = {
        ("558", "1"): [cell("558", "1", 0, 1, "", "Total", "6.2"),
                       cell("558", "1", 2, 1, "Age", "18-34", "11.1"), cell("558", "1", 3, 1, "Age", "35-49", "9.2"),
                       cell("558", "1", 4, 1, "Age", "50-64", "6.1"), cell("558", "1", 5, 1, "Age", "65+", "4.3"),
                       cell("558", "1", 7, 1, "Race/ethnicity", "Non-Hispanic White", "4.6"),
                       cell("558", "1", 8, 1, "Race/ethnicity", "Non-Hispanic Black", "8.8"),
                       cell("558", "1", 9, 1, "Race/ethnicity", "Hispanic", "9.3"),
                       cell("558", "1", 10, 1, "Race/ethnicity", "Non-Hispanic other", "10.0")],
        ("900", "1"): [cell("900", "1", 0, 1, "", "Total", "50.0", col_label="Group A"),
                       cell("900", "1", 1, 1, "", "Male", "40.0", col_label="Group A"),
                       cell("900", "1", 2, 1, "", "Female", "70.0", col_label="Group A"),
                       cell("900", "1", 0, 2, "", "Total", "80.0", col_label="Group B"),
                       cell("900", "1", 1, 2, "", "Male", "40.0", col_label="Group B"),
                       cell("900", "1", 2, 2, "", "Female", "70.0", col_label="Group B")],
        ("901", "1"): [cell("901", "1", 0, 1, "", "Total", "5.0"),
                       cell("901", "1", 2, 1, "Age", "0-17", "10.0"), cell("901", "1", 3, 1, "Age", "18+", "20.0"),
                       cell("901", "1", 5, 1, "Sex", "Male", "4.0"), cell("901", "1", 6, 1, "Sex", "Female", "6.0")],
        ("902", "1"): [cell("902", "1", 0, 1, "", "Total", "300", "0"), cell("902", "1", 1, 1, "", "A", "100", "0"),
                       cell("902", "1", 2, 1, "", "B", "200", "0")],
        ("903", "1"): [cell("903", "1", 0, 1, "", "Total", "100.0"), cell("903", "1", 1, 1, "", "Inpatient", "30.0"),
                       cell("903", "1", 2, 1, "", "Outpatient", "70.0")],
        ("904", "1"): [cell("904", "1", 0, 1, "", "Total", "-1.0"), cell("904", "1", 1, 1, "", "A", "2.0"),
                       cell("904", "1", 2, 1, "", "B", "3.0")],
        ("905", "1"): [cell("905", "1", 0, 1, "", "Total", "5.0"), cell("905", "1", 1, 1, "", "A", "4.0")],
    }
    return tables, cells


class TestParts(unittest.TestCase):
    def test_is_total(self):
        for s in ("Total", "Total*", "Total population", "All persons", "All", "U.S.", "Overall", "United States"):
            self.assertTrue(m.is_total(s), s)
        for s in ("All other", "Subtotal", "Any private", "Totally", "18-34", ""):
            self.assertFalse(m.is_total(s), s)

    def test_verdict(self):
        p = [(10.0, 1), (20.0, 1)]
        self.assertEqual(m.verdict(5.0, 1, p, ["x"]), "below")
        self.assertEqual(m.verdict(9.9, 1, p, [""]), "ok")      # 10.0 - (0.05 + 0.05)
        self.assertEqual(m.verdict(9.8, 1, p, [""]), "below")
        self.assertEqual(m.verdict(20.1, 1, p, [""]), "ok")
        self.assertEqual(m.verdict(25.0, 1, p, [""]), "above")   # 98% of 30 = 29.4, minus 0.15
        self.assertEqual(m.verdict(29.3, 1, p, [""]), "sum_like")  # >= 29.25
        self.assertEqual(m.verdict(9.0, 0, [(10.0, 0), (20.0, 0)], [""]), "ok")
        self.assertEqual(m.verdict(1.0, 1, [(2.0, 1), (3.0, 1)], ["Standard error of the mean"]), "excluded_label")
        self.assertEqual(m.verdict(1.0, 1, [(2.0, 1), (3.0, 1)], ["Percent change"]), "excluded_label")
        self.assertEqual(m.verdict(1.0, 1, [(2.0, 1), (3.0, 1)], ["Northeast"]), "below")
        self.assertEqual(m.verdict(1.0, 1, [(-2.0, 1), (3.0, 1)], [""]), "excluded_negative")


class TestCensus(unittest.TestCase):
    def test_census(self):
        tables, cells = data()
        s, pairs, flags = m.census(tables, cells)
        self.assertEqual(len(pairs), 9)
        self.assertEqual(s["by_verdict"], {"ok": 4, "above": 1, "below": 1, "excluded_label": 1, "sum_like": 1,
                                           "excluded_negative": 1})
        self.assertEqual(s["pairs_bound_applied"], 6)
        self.assertEqual(s["tables_with_total_pairs"], 6)
        self.assertEqual((s["flags"], s["figures_flagged"], s["sample_size"]), (2, 2, 2))
        self.assertEqual(s["figures_flagged_by_kind"], {"below": 1, "above": 1})
        self.assertTrue(s["control_558_f1"]["all_ok"])
        self.assertEqual(s["control_558_f1"]["pairs"], [("Age", "ok"), ("Race/ethnicity", "ok")])
        self.assertEqual(sorted((f["number"], f["verdict"]) for f in flags), [("900", "above"), ("901", "below")])
        self.assertEqual(sorted(f["check_rank"] for f in flags), [1, 2])
        below = [f for f in flags if f["verdict"] == "below"][0]
        self.assertEqual((below["section"], below["total"], below["lo"], below["lo_label"], below["hi"],
                          below["hi_label"], below["sum"], below["n_parts"]),
                         ("Age", "5", "10", "0-17", "20", "18+", "30", 2))
        above = [f for f in flags if f["verdict"] == "above"][0]
        self.assertEqual((above["col"], above["col_label"], above["total"]), (2, "Group B", "80"))
        self.assertEqual([p["verdict"] for p in pairs if p["number"] == "901"], ["below", "ok"])

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
            with open(os.path.join(cd, "st500-599.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(cell("1", "1", 0, 1, "", "a", "1").keys()))
                w.writeheader()
                for cs in cells.values():
                    w.writerows(cs)
            out = os.path.join(d, "out")
            rc = m.main(["--tables", tp, "--cells-dir", cd, "--out-dir", out])
            with open(os.path.join(out, "m7-summary.json")) as f:
                s = json.load(f)
            with open(os.path.join(out, "m7-flags.csv"), newline="", encoding="utf-8") as f:
                flags = list(csv.DictReader(f))
            with open(os.path.join(out, "m7-pairs.csv"), newline="", encoding="utf-8") as f:
                pairs = list(csv.DictReader(f))
        self.assertEqual(rc, 0)
        self.assertEqual((s["pairs"], s["flags"]), (9, 2))
        self.assertEqual(len(flags), 2)
        self.assertEqual(len(pairs), 9)
        self.assertEqual(s["control_558_f1"]["pairs"], [["Age", "ok"], ["Race/ethnicity", "ok"]])


if __name__ == "__main__":
    unittest.main()
