# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r558x (synthetic records only; standard library)."""
import unittest

from meps import r558x


def rec(age, w, y, perwt, agelast):
    return {"AGE31X": float(age), "SDOHWT21F": float(w), "SDNOTRANS": float(y), "PERWT21F": float(perwt),
            "AGELAST": float(agelast)}


def sample():
    return [rec(20, 1, 1, 2, 20),     # A: in base, 18-34
            rec(40, 1, 2, 2, 41),     # B: in base, 35-49
            rec(55, 2, 2, 1, 55),     # C: in base, 50-64
            rec(70, 0, -1, 3, 70),    # D: no SDOH weight
            rec(70, 4, -15, 1, 70),   # E: item code -15
            rec(17, 1, 1, 1, 18)]     # F: under 18 by AGE31X, 18 by AGELAST


class TestShares(unittest.TestCase):
    def test_sdoh_shares(self):
        sh = r558x.age_shares(sample())
        self.assertEqual(sh, {"18-34": 25.0, "35-49": 25.0, "50-64": 50.0, "65+": 0.0})
        self.assertAlmostEqual(r558x.implied_total(sh), 8.125)

    def test_perwt_shares(self):
        sh = r558x.age_shares(sample(), "PERWT21F")
        self.assertEqual(sh, {"18-34": 40.0, "35-49": 40.0, "50-64": 20.0, "65+": 0.0})
        self.assertAlmostEqual(r558x.implied_total(sh), 9.34)

    def test_empty_base(self):
        self.assertIsNone(r558x.age_shares([rec(30, 0, 1, 1, 30)]))

    def test_implied_total_uniform(self):
        sh = {"18-34": 100.0, "35-49": 0.0, "50-64": 0.0, "65+": 0.0}
        self.assertAlmostEqual(r558x.implied_total(sh), 11.1)


class TestVariants(unittest.TestCase):
    def test_m15_yes(self):
        recs = sample()
        sh = r558x.age_shares(r558x.variant(recs, "m15_yes"))
        self.assertEqual(sh, {"18-34": 12.5, "35-49": 12.5, "50-64": 25.0, "65+": 50.0})
        self.assertEqual(recs[4]["SDNOTRANS"], -15.0)  # input unchanged

    def test_m15_no(self):
        v = r558x.variant(sample(), "m15_no")
        self.assertEqual(v[4]["SDNOTRANS"], 2.0)
        self.assertEqual(v[0]["SDNOTRANS"], 1.0)

    def test_agelast(self):
        sh = r558x.age_shares(r558x.variant(sample(), "agelast"))
        self.assertEqual(sh, {"18-34": 40.0, "35-49": 20.0, "50-64": 40.0, "65+": 0.0})

    def test_perwt_and_unweighted(self):
        p = r558x.variant(sample(), "perwt")
        self.assertEqual([r["SDOHWT21F"] for r in p], [2.0, 2.0, 1.0, 0.0, 1.0, 1.0])
        u = r558x.variant(sample(), "unweighted")
        self.assertEqual([r["SDOHWT21F"] for r in u], [1.0, 1.0, 1.0, 0.0, 1.0, 1.0])

    def test_spec_is_identity(self):
        self.assertEqual(r558x.variant(sample(), "spec"), sample())

    def test_unknown(self):
        with self.assertRaises(ValueError):
            r558x.variant(sample(), "other")


if __name__ == "__main__":
    unittest.main()
