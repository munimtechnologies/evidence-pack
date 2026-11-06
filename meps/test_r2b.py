# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r2b (no network, no MEPS file). Every expected value is worked by hand."""
import csv
import json
import os
import tempfile
import unittest
import zipfile

from meps import r2b


def _r554(i, w, y, age, race=2, smk=3):
    return {"id": "%03d" % i, "SDOHWT21F": w, "SDENICPROD": y, "AGE31X": age, "RACETHX": race, "SEX": 1,
            "REGION31": 1, "RTHLTH31": 1, "MNHLTH31": 1, "OFTSMK53": smk, "ASTHDX": 2}


def _r558(i, w, y, **kw):
    r = {"id": "%03d" % i, "SDOHWT21F": w, "SDNOTRANS": y, "AGE31X": 40, "RACETHX": 2, "INSCOV21": 1,
         "MCREV21": 2, "MCDEV21": 2, "RTHLTH31": 1, "MNHLTH31": 1, "OFTSMK53": 3}
    for v in ("DIABDX_M18", "EMPHDX", "CANCERDX", "CHDDX", "ANGIDX", "MIDX", "OHRTDX", "ASTHDX", "BPMLDX",
              "STRKDX", "CHOLDX"):
        r[v] = 2
    r.update(kw)
    return r


def _r171(i, w, age, tot, ip=0, obv=0, rx=0, ins=1):
    return {"id": "%03d" % i, "PERWT14F": w, "AGE14X": age, "AGELAST": age, "INSCOV14": ins,
            "TOTEXP14": tot, "IPTEXP14": ip, "OBVEXP14": obv, "OPTEXP14": 0, "ERTEXP14": 0, "RXEXP14": rx,
            "DVTEXP14": 0, "HHAEXP14": 0, "HHNEXP14": 0, "VISEXP14": 0, "OTHEXP14": 0}


class TestKeys(unittest.TestCase):
    def test_lengths(self):
        self.assertEqual(len(r2b.KEYS[554]), 30)
        for b in (558, 493, 496, 497, 533):
            self.assertEqual(len(r2b.KEYS[b]), 40)

    def test_page_order(self):
        self.assertEqual(r2b.KEYS[554][15], ("msa", "Yes"))
        self.assertEqual(r2b.KEYS[554][29], ("all_adults",))
        self.assertEqual(r2b.KEYS[558][39], ("ncond_ge", 3))
        self.assertEqual(r2b.KEYS[497][31], ("expshare", "45-64"))
        self.assertEqual(r2b.KEYS[497][32], ("popshare", "18-44"))
        self.assertEqual(r2b.KEYS[533][22], ("total", 100))


class TestHelpers(unittest.TestCase):
    def test_wmedian(self):
        self.assertEqual(r2b.wmedian([(3, 1.0), (1, 1.0), (2, 1.0)]), 2)
        self.assertEqual(r2b.wmedian([(10, 3.0), (20, 1.0)]), 10)
        self.assertEqual(r2b.wmedian([(150, 1.0), (1000, 1.0)]), 150)
        self.assertIsNone(r2b.wmedian([]))

    def test_gate(self):
        rows = [{"W": "1.0", "X": "0", "C": "1"}, {"W": "0.000000", "X": "5", "C": "-1"}]
        g = r2b.gate(rows, {"rows": 2, "positive": ("W", 1), "zeros": ("X", 1), "counts": {"C": {1: 1, -1: 1}}})
        self.assertTrue(g["passed"])
        g = r2b.gate(rows, {"rows": 2, "positive": ("W", 2)})
        self.assertFalse(g["passed"])

    def test_ins558(self):
        self.assertEqual(r2b.ins558({"INSCOV21": 1, "MCREV21": 1, "MCDEV21": 1}), "private")
        self.assertEqual(r2b.ins558({"INSCOV21": 2, "MCREV21": 1, "MCDEV21": 1}), "medicare")
        self.assertEqual(r2b.ins558({"INSCOV21": 2, "MCREV21": 2, "MCDEV21": 1}), "medicaid")
        self.assertEqual(r2b.ins558({"INSCOV21": 2, "MCREV21": 2, "MCDEV21": 2}), "other_public")
        self.assertEqual(r2b.ins558({"INSCOV21": 3, "MCREV21": 2, "MCDEV21": 2}), "uninsured")

    def test_msa_check(self):
        inv = [{"name": "REGION31", "description": "CENSUS REGION - R3/1"}]
        self.assertTrue(r2b.msa_check(inv)["not_computable"])
        inv.append({"name": "MSA21", "description": "MSA - 12/31/21"})
        self.assertFalse(r2b.msa_check(inv)["not_computable"])


class TestEstimators(unittest.TestCase):
    def test_554(self):
        recs = [_r554(1, 1.0, 1, 20), _r554(2, 3.0, 2, 22), _r554(3, 2.0, 1, 30, race=4),
                _r554(4, 5.0, -1, 40), _r554(5, 0.0, 1, 50), _r554(6, 4.0, 2, 17)]
        e = r2b.est554(recs)
        self.assertEqual(e[("n", "base")], 3)
        self.assertAlmostEqual(e[("all_adults",)], 50.0)
        self.assertAlmostEqual(e[("age", "18-24")], 25.0)
        self.assertAlmostEqual(e[("age", "25-34")], 100.0)
        self.assertIsNone(e[("age", "35-44")])
        self.assertAlmostEqual(e[("race", 2)], 25.0)
        self.assertIsNone(e[("race", "other")])
        self.assertAlmostEqual(e[("smoke", "no")], 25.0)
        self.assertIsNone(e[("smoke", "yes")])

    def test_558(self):
        recs = [_r558(1, 1.0, 1, OFTSMK53=1, CHDDX=1), _r558(2, 1.0, 2), _r558(3, 2.0, 1, DIABDX_M18=1),
                _r558(4, 9.0, -15)]
        e = r2b.est558(recs)
        self.assertAlmostEqual(e[("total",)], 75.0)
        self.assertAlmostEqual(e[("ins", "private")], 75.0)
        self.assertIsNone(e[("ins", "medicare")])
        self.assertAlmostEqual(e[("cond", "none")], 0.0)
        self.assertAlmostEqual(e[("cond", "smoker")], 100.0)
        self.assertAlmostEqual(e[("ncond_ge", 1)], 100.0)
        self.assertAlmostEqual(e[("ncond_ge", 2)], 100.0)
        self.assertIsNone(e[("ncond_ge", 3)])
        self.assertAlmostEqual(e[("ncond8_ge", 1)], 100.0)
        self.assertIsNone(e[("ncond8_ge", 2)])

    def test_493(self):
        recs = [_r171(1, 1.0, 30, 150, obv=100, rx=50), _r171(2, 1.0, 70, 1000, ip=1000), _r171(3, 2.0, 40, 0)]
        e = r2b.est493(recs)
        self.assertAlmostEqual(e[("pct", "any", "all")], 50.0)
        self.assertAlmostEqual(e[("mean", "any", "all")], 575.0)
        self.assertEqual(e[("median", "any", "all")], 150)
        self.assertAlmostEqual(e[("pct", "ip", "all")], 25.0)
        self.assertAlmostEqual(e[("mean", "amb", "all")], 100.0)
        self.assertAlmostEqual(e[("pct", "any", "ge65")], 100.0)
        self.assertEqual(e[("n", "sum_mismatch")], 0)
        self.assertEqual(e[("n", "age14_fallback")], 0)

    def test_496(self):
        xs = [0, 0, 10, 20, 30, 40, 50, 60, 70, 80]
        recs = [_r171(i + 1, 1.0, 70 if x == 80 else 30, x) for i, x in enumerate(xs)]
        e = r2b.est496(recs)
        self.assertAlmostEqual(e[("tier_share", "none")], 20.0)
        self.assertAlmostEqual(e[("tier_share", "low")], 30.0)
        self.assertAlmostEqual(e[("tier_share", "middle")], 40.0)
        self.assertAlmostEqual(e[("tier_share", "high")], 10.0)
        self.assertAlmostEqual(e[("agedist", "65+", "high")], 100.0)
        self.assertAlmostEqual(e[("agedist", "18-44", "middle")], 100.0)
        self.assertAlmostEqual(e[("insdist", "18-64", 1, "low")], 100.0)
        self.assertIsNone(e[("insdist", "0-17", 1, "low")])

    def test_497(self):
        recs = [_r171(1, 1.0, 10, 100), _r171(2, 1.0, 50, 300)]
        e = r2b.est497(recs)
        self.assertAlmostEqual(e[("popshare", "0-17")], 50.0)
        self.assertAlmostEqual(e[("expshare", "0-17")], 25.0)
        self.assertAlmostEqual(e[("expshare", "45-64")], 75.0)
        self.assertAlmostEqual(e[("popshare", "65+")], 0.0)
        self.assertAlmostEqual(e[("agemean", "0-17", "Bottom 50%")], 100.0)
        self.assertIsNone(e[("agemean", "0-17", "Top 50%")])


class TestEvaluate(unittest.TestCase):
    def _cells(self, d):
        path = os.path.join(d, "cells.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["brief", "named_file", "seq", "source", "group", "row", "column", "published", "value",
                        "unit", "graded", "expected", "reads"])
            for s in range(30, 0, -1):
                w.writerow([554, "HC-233", s, "Figure", "", "r%d" % s, "c", "50.0%", "50.0", "pct", 1, "", ""])
            w.writerow([554, "HC-233", "", "Figure", "", "x", "c", "-", "", "pct", 0, "", ""])
            w.writerow([558, "HC-233", 1, "Figure", "", "t", "c", "6.2", "6.2", "pct", 1, "", ""])
        return path

    def test_evaluate_554(self):
        with tempfile.TemporaryDirectory() as d:
            cells = r2b.load_cells(self._cells(d), 554)
        self.assertEqual([int(c["seq"]) for c in cells], list(range(1, 31)))
        est = {k: 50.04 for k in r2b.KEYS[554]}
        res = r2b.evaluate(554, cells, est, True)
        t = r2b.r2conc.tally(res)
        self.assertEqual(t["cells"], 30)
        self.assertEqual(t["computable"], 28)
        self.assertEqual(t["exact"], 28)
        self.assertEqual(t["not_computable"], 2)
        self.assertEqual(res[15]["status"], "not computable")
        self.assertAlmostEqual(res[0]["gap"], 0.04)
        self.assertTrue(res[0]["underspecified"])

    def test_wrong_count(self):
        with tempfile.TemporaryDirectory() as d:
            cells = r2b.load_cells(self._cells(d), 558)
        with self.assertRaises(ValueError):
            r2b.evaluate(558, cells, {}, False)


class TestMain(unittest.TestCase):
    def test_gate_stops_533(self):
        inv = [["H209", "2018", "DUPERSID", "1", "3", "PERSON ID"],
               ["H209", "2018", "PERWT18F", "4", "8", "FINAL PERSON WEIGHT, 2018"],
               ["H209", "2018", "TOTEXP18", "9", "12", "TOTAL HEALTH CARE EXP 18"],
               ["H209", "2018", "AGELAST", "13", "14", "PERSON'S AGE LAST TIME ELIGIBLE"]]
        with tempfile.TemporaryDirectory() as d:
            ip = os.path.join(d, "H209.csv")
            with open(ip, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["file", "data_year", "name", "start", "end", "description"])
                w.writerows(inv)
            zp = os.path.join(d, "h209dat.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("h209.dat", "001100.5  5030\r\n002000.0   0 5\r\n")
            out = os.path.join(d, "out")
            rc = r2b.main(["--brief", "533", "--data", zp, "--inventory", ip, "--cells", "unused.csv",
                           "--out-dir", out])
            with open(os.path.join(out, "r2b-533.json")) as f:
                res = json.load(f)
        self.assertEqual(rc, 0)
        self.assertIsNone(res["error"])
        self.assertFalse(res["gate"]["passed"])
        self.assertEqual(res["gate"]["checks"][0], ["rows", "count", 2, 30461])
        self.assertEqual(res["gate"]["checks"][1], ["PERWT18F", ">0", 1, 29415])
        self.assertEqual(res["gate"]["checks"][2], ["TOTEXP18", "==0", 1, 4620])


if __name__ == "__main__":
    unittest.main()
