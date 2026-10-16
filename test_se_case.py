# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
import math
import unittest

import se_case


class TestSeCase(unittest.TestCase):
    def test_max_sd_hand(self):
        # 5.7 * 94.3 = 537.51; sqrt = 23.184; * sqrt(20/19) = 23.79 (by hand)
        self.assertAlmostEqual(se_case.max_sd(5.7, 20), 23.79, places=2)

    def test_alcohol_p1_psilocybin(self):
        c = se_case.classify(5.7, 11.34, 20)
        self.assertFalse(c["possible_as_se"])  # 11.34 * 4.472 = 50.71 > 23.79
        self.assertTrue(c["possible_as_sd"])
        self.assertAlmostEqual(c["sd_if_se"], 50.71, places=2)

    def test_all_secondary_cells(self):
        # Hand check on 2026-10-16: all 24 impossible as SE, all 24 possible as SD.
        for r in se_case.ROWS:
            c = se_case.classify(*r[3:])
            self.assertFalse(c["possible_as_se"], r)
            self.assertTrue(c["possible_as_sd"], r)

    def test_primary_is_plausible_as_se(self):
        for r in se_case.PRIMARY:
            self.assertTrue(se_case.classify(*r[3:])["possible_as_se"], r)

    def test_two_readings_hand(self):
        # sp = sqrt((11.34^2 + 32.10^2) / 2) = 24.073; d = 21.98 / 24.073 = 0.9131; J = 1 - 3/151
        g_sd, g_se = se_case.two_readings(se_case.ROWS[0:2])
        self.assertAlmostEqual(g_sd, 0.895, places=3)
        self.assertAlmostEqual(g_se, 0.200, places=3)
        self.assertAlmostEqual(g_sd / g_se, math.sqrt(20), places=2)

    def test_n_below_two(self):
        self.assertTrue(math.isnan(se_case.max_sd(50, 1)))


if __name__ == "__main__":
    unittest.main()
