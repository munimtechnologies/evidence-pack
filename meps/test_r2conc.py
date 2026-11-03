# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r2conc (no network, no MEPS file)."""
import csv
import json
import os
import tempfile
import unittest
import zipfile

from meps import r2conc


def _synthetic():
    xs = [0, 0, 0, 0, 100, 200, 300, 400, 500, 1000]
    ages = [5, 10, 20, 30, 40, 50, 60, 70, 15, 80]
    return [("%02d" % (i + 1), 1.0, float(x), a) for i, (x, a) in enumerate(zip(xs, ages))]


def _inventory(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "data_year", "name", "start", "end", "description"])
        for r in rows:
            w.writerow(r)


INV = [["H181", "2015", "DUPERSID", "1", "3", "PERSON ID"],
       ["H181", "2015", "PERWT15F", "4", "8", "FINAL PERSON WEIGHT, 2015"],
       ["H181", "2015", "TOTEXP15", "9", "12", "TOTAL HEALTH CARE EXP 15"],
       ["H181", "2015", "AGELAST", "13", "14", "PERSON'S AGE LAST TIME ELIGIBLE"]]
LINES = ["001100.5  5030", "002000.0   0 5"]


def _zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("h181.dat", "\r\n".join(LINES) + "\r\n\r\n")


class TestCells(unittest.TestCase):
    def test_forty_cells_each(self):
        for b, spec in r2conc.BRIEFS.items():
            self.assertEqual(len(spec["cells"]), 40, b)
            self.assertEqual(len({c[0] for c in spec["cells"]}), 40, b)
        self.assertEqual(sum(1 for c in r2conc.BRIEFS[540]["cells"] if c[2] == "nc"), 10)
        self.assertEqual(sum(1 for c in r2conc.BRIEFS[506]["cells"] if c[2] == "nc"), 0)

    def test_page_order(self):
        c = r2conc.BRIEFS[521]["cells"]
        self.assertEqual(c[0][0], "F1-p10-cum")
        self.assertEqual(c[1][0], "F1-p10-total")
        self.assertEqual(c[22][0], "F1-p100-total")
        self.assertEqual(c[22][4], "1,617.5")
        self.assertEqual(c[23][0], "F2-Overall")
        self.assertEqual(c[30][0], "F3-0-17-Overall")
        self.assertEqual(c[39][0], "F3-18-44-Top5")
        self.assertEqual(c[39][4], "17.9")


class TestMatch(unittest.TestCase):
    def test_rounding(self):
        self.assertTrue(r2conc.rounds_to(2.85, "2.9"))
        self.assertTrue(r2conc.rounds_to(4978.4, "4,978"))
        self.assertFalse(r2conc.rounds_to(4978.5, "4,978"))
        self.assertEqual(r2conc.dec_places("1,263.2"), 1)
        self.assertEqual(r2conc.dec_places("0"), 0)
        self.assertEqual(r2conc.dec_places("4.0"), 1)

    def test_close_rules(self):
        self.assertEqual(r2conc.match("mean", 5020.0, "4,978")[1:], (False, True))
        self.assertEqual(r2conc.match("mean", 5030.0, "4,978")[1:], (False, False))
        self.assertEqual(r2conc.match("total", 0.04, "0")[1:], (True, True))
        self.assertEqual(r2conc.match("total", 0.6, "0")[1:], (False, False))
        self.assertTrue(r2conc.match("cumpct", 3.3, "2.9")[2])
        self.assertFalse(r2conc.match("cumpct", 3.5, "2.9")[2])


class TestIO(unittest.TestCase):
    def test_positions_and_load(self):
        d = tempfile.mkdtemp()
        inv_path = os.path.join(d, "H181.csv")
        _inventory(inv_path, INV)
        inv = r2conc.read_inventory(inv_path)
        pos = r2conc.positions(inv, ["DUPERSID", "PERWT15F", "TOTEXP15", "AGELAST"])
        self.assertEqual(pos["PERWT15F"], (4, 8))
        with self.assertRaises(KeyError):
            r2conc.positions(inv, ["NOPE"])
        zp = os.path.join(d, "h181dat.zip")
        _zip(zp)
        rows = r2conc.load_ascii(zp, pos)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"DUPERSID": "001", "PERWT15F": "100.5", "TOTEXP15": "50", "AGELAST": "30"})
        self.assertEqual(rows[1]["AGELAST"], "5")
        names = {"w": "PERWT15F", "x": "TOTEXP15", "age": "AGELAST"}
        g = r2conc.gate(rows, {"rows": 2, "pos_wt": 1, "zero_exp": 1}, names)
        self.assertTrue(g["passed"])
        self.assertFalse(r2conc.gate(rows, {"rows": 3, "pos_wt": 1, "zero_exp": 1}, names)["passed"])

    def test_main_gate_fails_cleanly(self):
        d = tempfile.mkdtemp()
        inv_path = os.path.join(d, "H181.csv")
        _inventory(inv_path, INV)
        zp = os.path.join(d, "h181dat.zip")
        _zip(zp)
        out = os.path.join(d, "out")
        rc = r2conc.main(["--brief", "506", "--data", zp, "--inventory", inv_path, "--out-dir", out])
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "r2conc-506.json")) as f:
            res = json.load(f)
        self.assertIsNone(res["error"])
        self.assertFalse(res["gate"]["passed"])
        self.assertEqual(res["gate"]["rows"], 2)
        self.assertNotIn("cells", res)
        self.assertEqual(len(res["data"]["sha256"]), 64)


class TestSummarize(unittest.TestCase):
    def test_synthetic(self):
        e = r2conc.summarize(_synthetic())
        self.assertAlmostEqual(e[("cumpct", 50)], 4.0)
        self.assertAlmostEqual(e[("cumpct", 90)], 60.0)
        self.assertAlmostEqual(e[("cumpct", 10)], 0.0)
        self.assertAlmostEqual(e[("total", 100)], 2.5e-6)
        self.assertAlmostEqual(e[("mean", "Overall")], 250.0)
        self.assertAlmostEqual(e[("mean", "Top 50%")], 480.0)
        self.assertAlmostEqual(e[("mean", "Bottom 50%")], 20.0)
        self.assertAlmostEqual(e[("mean", "Top 10%")], 1000.0)
        self.assertAlmostEqual(e[("mean", "Top 30%")], 1900.0 / 3)
        self.assertIsNone(e[("mean", "Top 5%")])
        self.assertAlmostEqual(e[("agepct", ("0-17", "Top 50%"))], 20.0)
        self.assertAlmostEqual(e[("agepct", ("18-44", "Top 50%"))], 0.0)
        self.assertAlmostEqual(e[("agepct", ("0-17", "Bottom 50%"))], 40.0)
        self.assertAlmostEqual(e[("agepct", ("18-44", "Bottom 50%"))], 60.0)
        self.assertAlmostEqual(e[("agepct", ("0-17", "Overall"))], 30.0)
        self.assertEqual(e[("n", "Top 50%")], 5)
        self.assertEqual(e[("n", "Bottom 50%")], 5)

    def test_ties_lower_weight_goes_up(self):
        e = r2conc.summarize([("a", 3.0, 10.0, 30), ("b", 1.0, 10.0, 10), ("c", 6.0, 0.0, 30)])
        self.assertEqual(e[("n", "Top 30%")], 1)
        self.assertAlmostEqual(e[("agepct", ("0-17", "Top 30%"))], 100.0)
        self.assertEqual(e[("n", "Top 50%")], 2)


class TestConditionsAndTally(unittest.TestCase):
    def test_condition_check(self):
        inv = [{"name": "TOTEXP19", "description": "TOTAL HEALTH CARE EXP 19"},
               {"name": "VADERM31", "description": "VSAQ: DIAGNOSED WITH DERMATOL CONDITIONS"}]
        self.assertTrue(r2conc.condition_check(inv, "19")["not_computable"])
        inv2 = inv + [{"name": "ICD10CDX", "description": "ICD-10 CODE"}]
        cc = r2conc.condition_check(inv2, "19")
        self.assertEqual(cc["condition_variables"], ["ICD10CDX"])
        self.assertFalse(cc["not_computable"])

    def test_evaluate_and_tally(self):
        e = r2conc.summarize(_synthetic())
        cells = [("x1", 1, "cumpct", 50, "4.0"), ("x2", 2, "mean", "Top 5%", "100"),
                 ("x3", 3, "nc", "lab", "7.6")]
        res = r2conc.evaluate(cells, e, {"not_computable": True})
        self.assertEqual([r["status"] for r in res], ["computed", "no estimate", "not computable"])
        self.assertTrue(res[0]["exact"])
        t = r2conc.tally(res)
        self.assertEqual((t["cells"], t["computable"], t["close"], t["exact"], t["not_computable"]),
                         (3, 2, 1, 1, 1))
        self.assertEqual(t["share_close"], 0.5)


if __name__ == "__main__":
    unittest.main()
