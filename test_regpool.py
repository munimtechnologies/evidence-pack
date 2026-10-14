# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import math
import os
import unittest

import regpool

HERE = os.path.dirname(os.path.abspath(__file__))
GABA = regpool.load(os.path.join(HERE, "studies", "gabapentin_aud.json"))
TOPI = regpool.load(os.path.join(HERE, "studies", "topiramate_aud.json"))


def study(spec, nct):
    return next(s for s in spec["studies"] if s["nct"] == nct)


class EffectTests(unittest.TestCase):
    def test_binary_good_event(self):
        # OR = (12*42)/(32*4) = 3.9375; d = -ln(OR) * sqrt(3)/pi
        g, v = regpool.effect(study(GABA, "NCT02349477"))
        self.assertAlmostEqual(g, -0.7556, places=3)
        self.assertAlmostEqual(v, 0.11806, places=4)

    def test_binary_bad_event(self):
        # relapse 14/25 vs 13/24 is slightly worse on gabapentin
        g, _ = regpool.effect(study(GABA, "NCT01014533"))
        self.assertAlmostEqual(g, 0.0409, places=3)

    def test_binary_two_doses_combined(self):
        g, _ = regpool.effect(study(GABA, "NCT00391716"))
        self.assertAlmostEqual(g, -0.7333, places=3)

    def test_zero_cell_correction(self):
        g, v = regpool.effect({"kind": "binary", "t": [0, 10], "c": [0, 10]})
        self.assertAlmostEqual(g, 0.0)
        self.assertAlmostEqual(v, (2 / 0.5 + 2 / 10.5) * 3 / math.pi ** 2)

    def test_higher_better_flips(self):
        # 69.9 vs 59.6 days to relapse, SEs to SDs: longer is better, so g < 0
        g, _ = regpool.effect(study(GABA, "NCT00183196"))
        self.assertAlmostEqual(g, -0.2072, places=3)

    def test_hedges_arms(self):
        g, v = regpool.effect(study(GABA, "NCT01141049"))
        self.assertAlmostEqual(g, -0.7776, places=3)
        self.assertAlmostEqual(v, 0.10781, places=4)
        g, v = regpool.effect(study(TOPI, "NCT02371889"))
        self.assertAlmostEqual(g, -0.4852, places=3)
        self.assertAlmostEqual(v, 0.02422, places=4)

    def test_combine_arms(self):
        m, sd, n = regpool.combine_arms((65.1, 44.0, 75), (59.3, 47.3, 77))
        self.assertEqual(n, 152)
        self.assertAlmostEqual(m, 62.1618, places=3)
        self.assertAlmostEqual(sd, 45.643, places=2)

    def test_p_derived(self):
        g, _ = regpool.effect(study(TOPI, "NCT00626925"))
        self.assertAlmostEqual(g, -0.5573, places=3)


class PoolTests(unittest.TestCase):
    def test_identical_studies(self):
        r = regpool.pool([(-0.3, 0.04), (-0.3, 0.04), (-0.3, 0.04)])
        self.assertAlmostEqual(r["g"], -0.3)
        self.assertEqual(r["tau2"], 0.0)
        self.assertAlmostEqual(r["se"], math.sqrt(0.04 / 3))

    def test_chi2_sf(self):
        self.assertAlmostEqual(regpool.chi2_sf(20.09, 8), 0.01, places=3)
        self.assertAlmostEqual(regpool.chi2_sf(3.841, 1), 0.05, places=3)

    def test_gabapentin_by_hand(self):
        _, sets, res, loo = regpool.analyses(GABA)
        main = res["main"]
        self.assertEqual(main["k"], 6)
        self.assertAlmostEqual(main["g"], -0.360, delta=0.01)
        self.assertAlmostEqual(main["I2"], 0.28, delta=0.03)
        self.assertLess(main["ci"][1], 0)
        self.assertLess(main["hksj_ci"][0], main["ci"][0])
        self.assertEqual(len(loo), 6)
        mono = res["gabapentin alone vs placebo (drop the add-on-to-naltrexone trial)"]
        self.assertEqual(mono["k"], 5)
        self.assertAlmostEqual(mono["g"], -0.425, delta=0.01)
        heavy = res["heavy-drinking outcomes only"]
        self.assertEqual(heavy["k"], 3)
        self.assertAlmostEqual(heavy["g"], -0.519, delta=0.01)
        both = res["main plus sensitivity-only trials"]
        self.assertEqual(both["k"], 7)
        self.assertAlmostEqual(both["g"], -0.311, delta=0.01)
        self.assertNotIn("NCT02252536", sets["main"])

    def test_topiramate_shape(self):
        _, sets, res, loo = regpool.analyses(TOPI)
        self.assertEqual(res["main"]["k"], 9)
        self.assertTrue(-0.45 < res["main"]["g"] < -0.15)
        self.assertEqual(len(sets["posted arm data only (drop p-derived and rescaled-SD trials)"]), 7)
        self.assertNotIn("main plus sensitivity-only trials", res)
        self.assertEqual(len(loo), 9)

    def test_report(self):
        eff, _, res, loo = regpool.analyses(GABA)
        text = regpool.report(GABA, eff, res, loo)
        self.assertIn("| NCT02252536 |", text)
        self.assertIn("sensitivity only.", text)
        self.assertIn("101/49", text)
        self.assertIn("without NCT00183196", text)


if __name__ == "__main__":
    unittest.main()
