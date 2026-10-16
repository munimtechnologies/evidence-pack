# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Checks rwe_recheck.py against values computed by hand in the run-26 note."""
import json
import os
import unittest

import rwe_recheck

HERE = os.path.dirname(os.path.abspath(__file__))

EXPECTED_FLAGS = {
    "Tae terazosin vs tamsulosin dementia HR": ["centre"],
    "Zhang crude TZ/DZ/AZ vs 5-ARI": ["centre", "stat", "crude"],
    "Zhang weighted TZ/DZ/AZ vs tamsulosin": ["width"],
    "Zhang weighted 5-ARI vs tamsulosin": ["width"],
    "Alimoradi adjusted GG+GA vs AA": ["centre"],
    "Alimoradi adjusted C allele": ["centre"],
    "Alimoradi crude CC vs CA+AA": ["centre", "table"],
}


class TestHelpers(unittest.TestCase):
    def test_half_unit(self):
        self.assertAlmostEqual(rwe_recheck.half_unit("0.79"), 0.005)
        self.assertAlmostEqual(rwe_recheck.half_unit("1.112"), 0.0005)
        self.assertAlmostEqual(rwe_recheck.half_unit("-1"), 0.5)
        self.assertAlmostEqual(rwe_recheck.half_unit("-313.0"), 0.05)


class TestRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "recheck_rows.json"), encoding="utf-8") as f:
            cls.res = rwe_recheck.run(json.load(f)["rows"])
        cls.by = {r["label"]: r for r in cls.res["rows"]}

    def test_counts(self):
        self.assertEqual(self.res["n_rows"], 68)
        self.assertEqual(len(self.by), 68)
        self.assertEqual(self.res["n_flagged"], 7)

    def test_flags(self):
        got = {r["label"]: r["flags"] for r in self.res["rows"] if r["flags"]}
        self.assertEqual(got, EXPECTED_FLAGS)

    def test_tae_midpoint(self):
        c = self.by["Tae terazosin vs tamsulosin dementia HR"]["checks"]["centre"]
        self.assertAlmostEqual(c["midpoint"], 1.1217, delta=0.001)

    def test_loften_borderline_centre_passes(self):
        self.assertEqual(self.by["Loften intoxication vs CCBs"]["flags"], [])
        self.assertEqual(self.by["Loften intoxication vs alpha-blockers"]["flags"], [])

    def test_loften_width(self):
        w = self.by["Loften remission vs other K-sparing"]["checks"]["width"]
        self.assertAlmostEqual(w["count_se"], 0.15964, delta=0.0005)
        self.assertAlmostEqual(w["ratio"], 1.011, delta=0.02)

    def test_loften_crude_is_info_only(self):
        c = self.by["Loften remission vs loop diuretics"]["checks"]["crude"]
        self.assertAlmostEqual(c["crude_ratio"], 1.387, delta=0.002)
        self.assertTrue(c["ok"])

    def test_zhang_crude(self):
        c = self.by["Zhang crude TZ/DZ/AZ vs 5-ARI"]["checks"]["crude"]
        self.assertAlmostEqual(c["crude_ratio"], 0.911, delta=0.002)
        self.assertAlmostEqual(c["gap_in_se"], 8.53, delta=0.1)
        ok = self.by["Zhang crude TZ/DZ/AZ vs tamsulosin"]["checks"]["crude"]
        self.assertAlmostEqual(ok["crude_ratio"], 0.698, delta=0.002)

    def test_zhang_weighted_width(self):
        w = self.by["Zhang weighted TZ/DZ/AZ vs tamsulosin"]["checks"]["width"]
        self.assertAlmostEqual(w["count_se"], 0.012652, delta=0.0001)
        self.assertAlmostEqual(w["ratio"], 0.240, delta=0.01)

    def test_alimoradi_table(self):
        t = self.by["Alimoradi crude CC vs CA+AA"]["checks"]["table"]
        self.assertAlmostEqual(t["woolf"]["est"], 2.872, delta=0.003)
        self.assertAlmostEqual(t["woolf"]["lo"], 1.558, delta=0.003)
        self.assertAlmostEqual(t["woolf"]["hi"], 5.294, delta=0.01)
        self.assertEqual(t["off"], ["lo"])
        g = self.by["Alimoradi crude G allele"]["checks"]["table"]
        self.assertAlmostEqual(g["woolf"]["est"], 1.889, delta=0.003)
        self.assertEqual(g["off"], [])


if __name__ == "__main__":
    unittest.main()
