# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r569x (synthetic records only; no MEPS data)."""
import unittest

from meps import r569
from meps import r569x as x


def person(**kw):
    p = {"SAQWT22F": 1.0, "PERWT22F": 1.0, "SEX": 2.0, "AGELAST": 55.0, "ADOSTP42": 2.0, "ADBNDN42": 1.0,
         "REGION22": 1.0, "REGION53": 2.0, "ADAGE42": 4.0}
    p.update(kw)
    return p


class TestParts(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(sorted(x.VARIANTS), sorted(x.ORDER))
        self.assertEqual(x.ORDER[0], "A")
        self.assertEqual(len(x.V1), 24)
        self.assertEqual(sorted(x.V1), sorted(c[0] for c in r569.CELLS))
        self.assertIn("REGION53", x.COLUMNS)
        self.assertIn("PERWT22F", x.COLUMNS)

    def test_in_age(self):
        p = {"ADAGE42": 4.0, "AGELAST": 40.0}
        self.assertTrue(x.in_age(p, "50+", x.VARIANTS["C2"]))
        self.assertFalse(x.in_age(p, "50+", x.VARIANTS["A"]))
        q = {"AGELAST": 49.0, "AGE22X": 50.0}
        self.assertFalse(x.in_age(q, "50+", x.VARIANTS["A"]))
        self.assertTrue(x.in_age(q, "50+", x.VARIANTS["AGE22"]))
        self.assertTrue(x.in_age(q, "50-64", x.VARIANTS["AGE22"]))
        self.assertFalse(x.in_age(q, "50-64", x.VARIANTS["C2"]))

    def test_region_sub(self):
        p = {"REGION53": 1.0, "REGION22": 2.0}
        self.assertTrue(x.cell_sub("F7a", None, x.VARIANTS["REG53"])(p))
        self.assertFalse(x.cell_sub("F7a", None, x.VARIANTS["A"])(p))
        self.assertTrue(x.cell_sub("F7b", None, x.VARIANTS["A"])(p))
        sub = lambda p: True  # noqa: E731
        self.assertIs(x.cell_sub("F2a", sub, x.VARIANTS["REG53"]), sub)

    def test_estimate_w_needs_saq(self):
        ps = [person(SAQWT22F=0.0, PERWT22F=5.0)]
        e = x.estimate_w(ps, lambda p: True, lambda p: True, "PERWT22F")
        self.assertEqual(e, {"n": 0, "pct": None})

    def test_rounds_to(self):
        self.assertFalse(x._rounds_to(42.7498, 42.8))
        self.assertTrue(x._rounds_to(42.75, 42.8))
        self.assertTrue(x._rounds_to(24.799, 24.8))
        self.assertTrue(x._rounds_to(47.6, 47.6))


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        self.ps = [
            person(PERWT22F=2.0),
            person(AGELAST=70.0, ADOSTP42=-15.0, ADBNDN42=2.0, REGION53=1.0),
            person(AGELAST=60.0, ADBNDN42=2.0, SAQWT22F=0.0, PERWT22F=5.0),
        ]

    def res(self, k):
        return {r["cid"]: r for r in x.evaluate_v(self.ps, x.VARIANTS[k])}

    def test_a(self):
        a = self.res("A")
        self.assertEqual(a["F2a"]["n"], 1)
        self.assertAlmostEqual(a["F2a"]["pct"], 100.0)
        self.assertEqual(a["F1a"]["n"], 1)
        self.assertAlmostEqual(a["F1a"]["pct"], 0.0)
        self.assertEqual(a["F7a"]["n"], 1)
        self.assertEqual(a["F7b"]["n"], 0)
        self.assertIsNone(a["F7b"]["pct"])
        self.assertEqual(len(a), 24)

    def test_u3(self):
        u = self.res("U3")
        self.assertEqual(u["F2a"]["n"], 2)
        self.assertAlmostEqual(u["F2a"]["pct"], 50.0)
        self.assertEqual(u["F1a"]["n"], 1)

    def test_reg53(self):
        g = self.res("REG53")
        self.assertEqual(g["F7a"]["n"], 0)
        self.assertEqual(g["F7b"]["n"], 1)

    def test_pw(self):
        w = self.res("PW")
        self.assertEqual(w["F2a"]["n"], 1)
        self.assertAlmostEqual(w["F2a"]["pct"], 100.0)

    def test_c2(self):
        c = self.res("C2")
        self.assertEqual(c["F2a"]["n"], 1)


class TestGateReadings(unittest.TestCase):
    def rows(self):
        return [{"cid": c, "pct": v, "exact": c not in x.MISSES} for c, v in x.V1.items()]

    def test_gate(self):
        g = x.gate(self.rows())
        self.assertTrue(g["passed"])
        self.assertEqual(g["exact"], 19)
        rows = self.rows()
        rows[0]["pct"] += 0.001
        g = x.gate(rows)
        self.assertFalse(g["passed"])
        self.assertEqual(g["cells_off"], [rows[0]["cid"]])

    def test_summarize_and_readings(self):
        rows = [{"cid": c, "exact": c not in x.MISSES, "rounds": True, "close": True} for c in x.V1]
        s = x.summarize(rows)
        self.assertEqual(s["exact"], 19)
        self.assertEqual(s["fig7_exact"], 1)
        self.assertEqual(s["misses_now_exact"], [])
        self.assertEqual(s["v1_exact_now_not"], [])
        summ = {k: dict(s) for k in x.ORDER}
        summ["REG42"] = dict(s, fig7_exact=4, exact=22)
        summ["PW"] = dict(s, exact=12)
        r = x.readings(summ)
        self.assertEqual(r["region"], ["REG42"])
        self.assertEqual(r["X1_pw_control"]["grade"], "held")
        self.assertEqual(r["candidates"], ["REG42"])


if __name__ == "__main__":
    unittest.main()
