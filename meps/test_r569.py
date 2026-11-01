# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r569 (synthetic records only; no MEPS data)."""
import math
import unittest

from meps import r569 as r


def person(**kw):
    p = {"SAQWT22F": 1.0, "VARSTR": 1.0, "VARPSU": 1.0, "SEX": 2.0, "AGELAST": 55.0, "ADOSTP42": 2.0,
         "ADBNDN42": 1.0, "INSURC22": 1.0, "HAVEUS42": 1.0, "RACETHX": 2.0, "REGION22": 1.0, "POVCAT22": 5.0}
    p.update(kw)
    return p


class TestParts(unittest.TestCase):
    def test_cells(self):
        self.assertEqual(len(r.CELLS), 24)
        self.assertEqual(len(set(c[0] for c in r.CELLS)), 24)
        self.assertEqual(len(r.MSA_CELLS), 2)

    def test_age(self):
        self.assertEqual(r.age_primary({"AGELAST": None, "AGE22X": -1, "AGE42X": 52}), 52)
        self.assertEqual(r.age_primary({"AGELAST": -1.0, "AGE22X": 60.0}), 60.0)
        self.assertEqual(r.age_primary({"AGELAST": 70.0, "AGE22X": 60.0}), 70.0)
        self.assertIsNone(r.age_saq({"ADAGE42": -1}))
        self.assertTrue(r.in_band(50, "50-64") and r.in_band(64, "50-64") and not r.in_band(65, "50-64"))
        self.assertTrue(r.in_band(65, "65+") and r.in_band(50, "50+") and not r.in_band(49, "50+"))
        self.assertFalse(r.in_band(None, "50+"))

    def test_estimate_se(self):
        ps = [person(VARSTR=1.0, VARPSU=1.0, ADBNDN42=1.0), person(VARSTR=1.0, VARPSU=2.0, ADBNDN42=2.0),
              person(VARSTR=2.0, VARPSU=1.0, ADBNDN42=1.0), person(VARSTR=2.0, VARPSU=2.0, ADBNDN42=2.0),
              person(SAQWT22F=0.0)]
        e = r.estimate(ps, r.dexa_universe, r.dexa_yes)
        self.assertEqual(e["n"], 4)
        self.assertAlmostEqual(e["pct"], 50.0)
        self.assertAlmostEqual(e["se"], 100 * math.sqrt(0.125))

    def test_estimate_empty(self):
        e = r.estimate([person(ADOSTP42=1.0)], r.dexa_universe, r.dexa_yes)
        self.assertEqual(e, {"n": 0, "pct": None, "se": None})


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        self.ps = [
            person(),
            person(AGELAST=70.0, ADOSTP42=1.0, ADBNDN42=-1.0, VARPSU=2.0, INSURC22=4.0),
            person(SEX=1.0, AGELAST=60.0, ADOSTP42=1.0),
            person(AGELAST=45.0),
            person(AGELAST=66.0, ADBNDN42=2.0, SAQWT22F=3.0, INSURC22=5.0, VARSTR=2.0),
        ]
        self.res = {x["cid"]: x for x in r.evaluate(self.ps)}

    def test_values(self):
        self.assertAlmostEqual(self.res["F1a"]["pct"], 20.0)
        self.assertEqual(self.res["F1a"]["n"], 3)
        self.assertAlmostEqual(self.res["F2a"]["pct"], 25.0)
        self.assertEqual(self.res["F2a"]["n"], 2)
        self.assertAlmostEqual(self.res["F2b"]["pct"], 100.0)
        self.assertAlmostEqual(self.res["F2c"]["pct"], 0.0)
        self.assertIsNone(self.res["F4a"]["pct"])
        self.assertEqual(self.res["F4a"]["n"], 0)
        self.assertAlmostEqual(self.res["F4b"]["pct"], 0.0)
        self.assertFalse(self.res["F1a"]["exact"])
        self.assertFalse(self.res["F1a"]["close"])
        self.assertFalse(self.res["F4a"]["exact"])

    def test_variant_b_uses_saq_sex(self):
        res = {x["cid"]: x for x in r.evaluate(self.ps, r.VARIANTS[1])}
        self.assertEqual(res["F1a"]["n"], 0)

    def test_dexa_universe_b(self):
        ps = self.ps + [person(ADOSTP42=-15.0, ADBNDN42=1.0, SAQWT22F=4.0)]
        res = {x["cid"]: x for x in r.evaluate(ps, r.VARIANTS[0], r.dexa_universe_b)}
        self.assertEqual(res["F2a"]["n"], 3)
        self.assertAlmostEqual(res["F2a"]["pct"], 62.5)


class TestGrade(unittest.TestCase):
    def rows(self, exact_n, close_n):
        out = []
        for i, c in enumerate(r.CELLS):
            out.append({"cid": c[0], "pct": c[3], "exact": i < exact_n, "close": i < close_n})
        return out

    def test_all_held(self):
        g = r.grade(self.rows(24, 24), [], [])
        self.assertEqual([g[k]["grade"] for k in ("P1", "P2", "P3", "P4")], ["held"] * 4)

    def test_failures(self):
        g = r.grade(self.rows(3, 19), ["MSA22"], ["AGELAST"])
        self.assertEqual(g["P1"]["grade"], "failed")
        self.assertEqual(g["P2"]["grade"], "failed")
        self.assertEqual(g["P3"]["grade"], "failed")
        self.assertEqual(g["P4"]["grade"], "failed")
        self.assertEqual(g["missing_columns"], ["AGELAST"])
        g = r.grade(self.rows(18, 20), [], [])
        self.assertEqual(g["P1"]["grade"], "held")
        self.assertEqual(g["P2"]["grade"], "held")
        self.assertEqual(g["P4"]["grade"], "held")


if __name__ == "__main__":
    unittest.main()
