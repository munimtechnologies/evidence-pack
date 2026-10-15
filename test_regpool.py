# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import math
import os
import unittest

import regpool

HERE = os.path.dirname(os.path.abspath(__file__))
GABA = regpool.load(os.path.join(HERE, "studies", "gabapentin_aud.json"))
TOPI = regpool.load(os.path.join(HERE, "studies", "topiramate_aud.json"))
NALT = regpool.load(os.path.join(HERE, "studies", "naltrexone_aud.json"))


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


class GroupTests(unittest.TestCase):
    def test_t975(self):
        self.assertEqual(regpool.t975(10), 2.228)
        self.assertAlmostEqual(regpool.t975(41), 2.0195, delta=0.001)
        self.assertAlmostEqual(regpool.t975(120), 1.9799, delta=0.001)

    def test_spread_conversions(self):
        self.assertEqual(regpool.to_msn([5.0, 2.0, 30], "sd"), (5.0, 2.0, 30))
        m, sd, n = regpool.to_msn([1.0, 2.0, 25], "se")
        self.assertAlmostEqual(sd, 10.0)
        m, sd, n = regpool.to_msn([3.5, 0.1, 6.8, 42], "ci95")
        self.assertAlmostEqual(sd, 10.75, delta=0.02)
        m, sd, n = regpool.to_msn([19.77, 6.01, 50.15, 204], "median_iqr")
        self.assertAlmostEqual(m, 25.31, places=2)
        self.assertAlmostEqual(sd, 32.696, places=2)

    def test_groups_by_hand(self):
        # hand-computed 2026-10-15 (Cochrane 6.5.2.10 merging, then Hedges' g)
        for nct, want in (("NCT01218958", -0.2511), ("NCT00831272", -0.1876),
                          ("NCT00920829", -0.2930), ("NCT00006489", -0.4302),
                          ("NCT00142818", 0.0430), ("NCT01077310", 0.0984)):
            g, _ = regpool.effect(study(NALT, nct))
            self.assertAlmostEqual(g, want, delta=0.01, msg=nct)
        self.assertEqual(regpool.arm_sizes(study(NALT, "NCT00920829")), (73, 73))
        self.assertEqual(regpool.arm_sizes(study(NALT, "NCT01218958")), (407, 204))

    def test_naltrexone_split(self):
        _, sets, res, _ = regpool.analyses(NALT)
        self.assertEqual(res["main"]["k"], 17)
        general = res["general AUD samples"]
        comorbid = res["samples selected for something else as well (another disorder, HIV, a second substance, housing, age group)"]
        self.assertEqual((general["k"], comorbid["k"]), (6, 11))
        self.assertAlmostEqual(general["g"], -0.0965, delta=0.02)
        self.assertAlmostEqual(comorbid["g"], -0.222, delta=0.02)
        self.assertEqual(len(sets["sensitivity: young-adult and homeless trials counted as general (general side)"]), 8)
        self.assertEqual(len(sets["sensitivity: young-adult and homeless trials counted as general (comorbid side)"]), 9)

    def test_compare(self):
        cmp = regpool.compare([TOPI, GABA, NALT], "general", "comorbid")
        diffs = [r["diff"] for _, r in cmp["rows"]]
        self.assertAlmostEqual(diffs[0], 0.471, delta=0.02)
        self.assertAlmostEqual(diffs[1], 0.547, delta=0.02)
        self.assertAlmostEqual(diffs[2], -0.125, delta=0.03)
        self.assertEqual(cmp["df"], 2)
        self.assertGreater(cmp["Q"], 6)
        text = regpool.compare_report(cmp, "general", "comorbid")
        self.assertIn("Fixed-effect average difference", text)


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

    def test_topiramate_matches_pool_py(self):
        # pool.py (topiramate-pool-v1) and regpool.py v0.2 both gave these
        _, sets, res, loo = regpool.analyses(TOPI)
        self.assertEqual(res["main"]["k"], 9)
        self.assertAlmostEqual(res["main"]["g"], -0.301, delta=0.001)
        self.assertAlmostEqual(res["general AUD samples"]["g"], -0.574, delta=0.001)
        self.assertAlmostEqual(res["comorbid samples (PTSD, smoking, cocaine, adolescents)"]["g"], -0.103, delta=0.001)
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
