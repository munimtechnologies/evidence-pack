# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Checks meta_oral.py against the hand-computed values in the write-up."""
import unittest

import meta_oral


class TestOralPool(unittest.TestCase):
    def setUp(self):
        self.res = meta_oral.run()
        self.g = {r["id"]: r for r in self.res["trials"]}

    def test_trial_effects(self):
        self.assertAlmostEqual(self.g["pan2025"]["se"], 0.2066, delta=0.001)
        self.assertAlmostEqual(self.g["alimoradi2023"]["g"], 1.056, delta=0.002)
        self.assertAlmostEqual(self.g["alimoradi2023"]["se"], 0.2276, delta=0.001)
        self.assertAlmostEqual(self.g["aiad2024"]["g"], 1.519, delta=0.002)
        self.assertAlmostEqual(self.g["aiad2024"]["se"], 0.3210, delta=0.001)

    def test_pool_all_three(self):
        p = self.res["pools"]["all_three"]
        self.assertAlmostEqual(p["mu"], 0.967, delta=0.01)
        self.assertAlmostEqual(p["lo"], 0.363, delta=0.01)
        self.assertAlmostEqual(p["hi"], 1.570, delta=0.01)
        self.assertAlmostEqual(p["tau2"], 0.221, delta=0.01)
        self.assertAlmostEqual(p["i2"], 78.5, delta=1.0)
        self.assertAlmostEqual(p["hksj_lo"], -0.38, delta=0.03)
        self.assertAlmostEqual(p["hksj_hi"], 2.31, delta=0.03)

    def test_pool_without_aiad(self):
        p = self.res["pools"]["without_aiad"]
        self.assertAlmostEqual(p["mu"], 0.736, delta=0.01)
        self.assertAlmostEqual(p["tau2"], 0.149, delta=0.01)


if __name__ == "__main__":
    unittest.main()
