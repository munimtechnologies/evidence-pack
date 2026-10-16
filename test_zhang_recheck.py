# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Checks zhang_recheck.py against the hand-computed values in the run-25 note."""
import unittest

import zhang_recheck


class TestRecheck(unittest.TestCase):
    def setUp(self):
        self.r = zhang_recheck.run()

    def test_crude_rates(self):
        c = self.r["crude_rates_per_1000"]
        self.assertAlmostEqual(c["tz"], 11.86, delta=0.01)
        self.assertAlmostEqual(c["tam"], 16.99, delta=0.01)
        self.assertAlmostEqual(c["ari"], 13.01, delta=0.01)

    def test_crude_ratios(self):
        c = self.r["crude"]
        self.assertAlmostEqual(c["tz vs tam"]["rr"], 0.698, delta=0.002)
        self.assertAlmostEqual(c["tz vs tam"]["t"], -28.17, delta=0.05)
        self.assertAlmostEqual(c["tz vs ari"]["rr"], 0.911, delta=0.002)
        self.assertAlmostEqual(c["tz vs ari"]["se"], 0.01897, delta=0.0001)
        self.assertAlmostEqual(c["tz vs ari"]["t"], -4.90, delta=0.05)
        self.assertAlmostEqual(c["ari vs tam"]["rr"], 0.766, delta=0.002)
        self.assertAlmostEqual(c["ari vs tam"]["se"], 0.01547, delta=0.0001)
        self.assertAlmostEqual(c["ari vs tam"]["t"], -17.24, delta=0.05)

    def test_printed_tz_vs_ari_matches_ari_vs_tam(self):
        c, se = self.r["crude"], self.r["printed_implied_se"]["crude tz vs ari"]
        self.assertAlmostEqual(se, 0.01436, delta=0.0001)
        self.assertLess(abs(se - c["ari vs tam"]["se"]), abs(se - c["tz vs ari"]["se"]))
        self.assertLess(abs(0.77 - c["ari vs tam"]["rr"]), abs(0.77 - c["tz vs ari"]["rr"]))
        self.assertAlmostEqual(self.r["printed_ci_midpoint"]["crude tz vs ari"], 0.807, delta=0.002)

    def test_crude_tz_vs_tam_se_agrees(self):
        self.assertAlmostEqual(self.r["printed_implied_se"]["crude tz vs tam"], 0.01262, delta=0.0001)
        self.assertAlmostEqual(self.r["crude"]["tz vs tam"]["se"], 0.01277, delta=0.0001)

    def test_weighted(self):
        w = self.r["weighted"]
        self.assertAlmostEqual(w["tz vs tam"]["rr"], 0.820, delta=0.002)
        self.assertAlmostEqual(w["ari vs tam"]["rr"], 0.921, delta=0.002)
        self.assertAlmostEqual(w["tz vs ari"]["rr"], 0.890, delta=0.002)
        x = self.r["weighted_tz_vs_ari_from_printed"]
        self.assertAlmostEqual(x["hr"], 0.903, delta=0.002)
        self.assertAlmostEqual(x["lo"], 0.871, delta=0.002)
        self.assertAlmostEqual(x["hi"], 0.937, delta=0.002)
        ci = self.r["weighted_tz_vs_tam_count_ci"]
        self.assertAlmostEqual(ci["lo"], 0.819, delta=0.002)
        self.assertAlmostEqual(ci["hi"], 0.861, delta=0.002)

    def test_weighted_se_shrink(self):
        s = self.r["weighted_se_shrink"]
        self.assertAlmostEqual(s["tz vs tam"], 63.0, delta=1.0)
        self.assertAlmostEqual(s["ari vs tam"], 79.8, delta=1.0)

    def test_tae(self):
        t = self.r["tae_2019"]
        self.assertAlmostEqual(t["midpoint"], 1.122, delta=0.002)
        self.assertAlmostEqual(t["hi_if_lo_right"], 1.175, delta=0.002)
        self.assertAlmostEqual(t["lo_if_hi_right"], 1.034, delta=0.002)


if __name__ == "__main__":
    unittest.main()
