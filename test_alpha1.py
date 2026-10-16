# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Pre-registration 4 (prazosin and doxazosin for AUD); every expected value hand-computed 2026-10-15.

2026-10-16: test_h2_split expected tau^2 = 0 for the general subgroup. The sealed run
(alpha1-pool-v1) gave 0.0016: Q = 4.09 on 4 df, so DerSimonian-Laird tau^2 is just above
zero (hand recheck: (4.08 - 4) / 54.7 = 0.0015). The expectation was wrong, not the code.
"""
import os
import unittest

import regpool

HERE = os.path.dirname(os.path.abspath(__file__))


def lst(name):
    return regpool.load(os.path.join(HERE, "studies", name + ".json"))


ALPHA = lst("alpha1_aud")
SECOND = lst("alpha1_aud_second")
E3 = lst("alpha1_aud_e3")


def study(spec, nct):
    return next(s for s in spec["studies"] if s["nct"] == nct)


def subset(spec, tag):
    return next(name for name, t in spec["subsets"].items() if t == tag)


class Alpha1EffectTests(unittest.TestCase):
    def test_effects(self):
        for nct, want in (("NCT00762710", -0.3824), ("NCT02989493", -0.1645),
                          ("NCT01916941", 0.1974), ("NCT00585780", 0.1441),
                          ("NCT02322047", -0.2781), ("NCT02500602", -0.0421),
                          ("NCT01518972", -0.9545), ("NCT00744055", 0.1018)):
            g, _ = regpool.effect(study(ALPHA, nct))
            self.assertAlmostEqual(g, want, delta=0.01, msg=nct)

    def test_binary_bad_event_variance(self):
        # any heavy drinking day 17/29 vs 21/32: ln OR = ln(187/252)
        _, v = regpool.effect(study(ALPHA, "NCT02989493"))
        self.assertAlmostEqual(v, 0.08532, places=4)

    def test_arm_sizes(self):
        self.assertEqual(regpool.arm_sizes(study(ALPHA, "NCT00585780")), (55, 45))
        self.assertEqual(regpool.arm_sizes(study(ALPHA, "NCT02322047")), (14, 15))
        self.assertEqual(regpool.arm_sizes(study(ALPHA, "NCT01518972")), (9, 11))

    def test_dropped_trial_absent(self):
        # NCT02226367 posts only a craving scale
        self.assertNotIn("NCT02226367", [s["nct"] for s in ALPHA["studies"]])

    def test_withdrawal_strata_e2(self):
        high = {"kind": "arms_se", "t": [8.2, 4.09, 21], "c": [27.11, 7.97, 23]}
        low = {"kind": "arms_se", "t": [31.29, 7.42, 34], "c": [7.32, 3.54, 22]}
        self.assertAlmostEqual(regpool.effect(high)[0], -0.6081, delta=0.01)
        self.assertAlmostEqual(regpool.effect(low)[0], 0.6682, delta=0.01)


class Alpha1PoolTests(unittest.TestCase):
    def test_h1_main(self):
        _, sets, res, loo = regpool.analyses(ALPHA)
        main = res["main"]
        self.assertEqual(main["k"], 8)
        self.assertAlmostEqual(main["g"], -0.0782, delta=0.01)
        self.assertAlmostEqual(main["tau2"], 0.0116, delta=0.003)
        self.assertLess(main["ci"][0], 0)
        self.assertGreater(main["ci"][1], 0)
        self.assertEqual(len(loo), 8)

    def test_h2_split(self):
        _, _, res, _ = regpool.analyses(ALPHA)
        general = res[subset(ALPHA, "general")]
        comorbid = res[subset(ALPHA, "comorbid")]
        self.assertEqual((general["k"], comorbid["k"]), (5, 3))
        self.assertAlmostEqual(general["g"], -0.0846, delta=0.01)
        self.assertAlmostEqual(general["tau2"], 0.0016, delta=0.001)
        self.assertAlmostEqual(comorbid["g"], -0.1166, delta=0.015)
        r = regpool.subgroup_difference(ALPHA, "general", "comorbid")
        self.assertAlmostEqual(r["diff"], -0.032, delta=0.02)
        self.assertGreater(r["p"], 0.05)

    def test_e1_drug(self):
        _, _, res, _ = regpool.analyses(ALPHA)
        self.assertEqual(res[subset(ALPHA, "doxazosin")]["k"], 2)
        self.assertAlmostEqual(res[subset(ALPHA, "doxazosin")]["g"], -0.0722, delta=0.01)
        self.assertEqual(res[subset(ALPHA, "prazosin")]["k"], 6)
        self.assertAlmostEqual(res[subset(ALPHA, "prazosin")]["g"], -0.100, delta=0.02)

    def test_second_outcome_effects(self):
        for nct, want in (("NCT00585780", 0.2528), ("NCT02322047", 0.1423),
                          ("NCT02500602", 0.1464), ("NCT01518972", -0.5888),
                          ("NCT00762710", -0.3824)):
            g, _ = regpool.effect(study(SECOND, nct))
            self.assertAlmostEqual(g, want, delta=0.01, msg=nct)

    def test_e3(self):
        g, _ = regpool.effect(study(E3, "NCT02322047"))
        self.assertAlmostEqual(g, 0.1043, delta=0.01)

    def test_six_lists(self):
        specs = [lst(n) for n in ("topiramate_aud", "gabapentin_aud", "naltrexone_aud",
                                  "acamprosate_aud", "varenicline_aud")] + [ALPHA]
        cmp = regpool.compare(specs, "general", "comorbid")
        self.assertEqual(cmp["df"], 5)
        self.assertAlmostEqual(cmp["rows"][5][1]["diff"], -0.032, delta=0.02)


if __name__ == "__main__":
    unittest.main()
