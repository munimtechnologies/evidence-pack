# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_spread (standard library only, synthetic participants, no network)."""
import math
import unittest

from kidney import kpmp_spread as ks


def exp_areas(scale, n=10):
    """n areas whose logs are 0, scale, 2*scale, ..."""
    return [math.exp(j * scale) for j in range(n)]


class TestSpread(unittest.TestCase):
    def test_quantile(self):
        v = [1, 2, 3, 4]
        self.assertAlmostEqual(ks.quantile(v, 0.25), 1.75)
        self.assertAlmostEqual(ks.quantile(v, 0.5), 2.5)
        self.assertAlmostEqual(ks.quantile(v, 0.75), 3.25)
        self.assertAlmostEqual(ks.quantile(v, 1.0), 4)

    def test_spread_stats_log(self):
        s = ks.spread_stats(exp_areas(1.0) + [0, -1, None])
        self.assertEqual(s["n"], 10)
        self.assertAlmostEqual(s["median"], 4.5)
        self.assertAlmostEqual(s["iqr"], 4.5)
        self.assertAlmostEqual(s["sd"], math.sqrt(82.5 / 9))
        self.assertIsNone(ks.spread_stats([1.0] * 9))

    def test_spread_stats_unitless(self):
        s = ks.spread_stats([0.1] * 5 + [0.3] * 5, log=False)
        self.assertAlmostEqual(s["iqr"], 0.2)
        self.assertAlmostEqual(s["median"], 0.2)

    def test_ranks(self):
        self.assertEqual(ks.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
        self.assertEqual(ks.ranks([3, 1, 2]), [3.0, 1.0, 2.0])

    def test_pearson(self):
        self.assertAlmostEqual(ks.pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(ks.pearson([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertIsNone(ks.pearson([1, 2, 3], [5, 5, 5]))
        self.assertIsNone(ks.pearson([1, 2], [1, 2]))

    def test_residual(self):
        for e in ks.residual([1, 2, 3], [1, 2, 3]):
            self.assertAlmostEqual(e, 0.0)
        for e, want in zip(ks.residual([1, 2, 4], [7, 7, 7]), [1 - 7 / 3, 2 - 7 / 3, 4 - 7 / 3]):
            self.assertAlmostEqual(e, want)

    def test_strat_test_perfect_and_small_stratum(self):
        rows = [("v1", i, i, 0) for i in range(12)] + [("v2", i, -i, 0) for i in range(5)]
        t = ks.strat_test(rows, 1, 200, 1)
        self.assertAlmostEqual(t["rho"], 1.0)
        self.assertEqual(t["n"], 12)
        self.assertEqual(t["strata"], [12])
        self.assertLess(t["p"], 0.05)

    def test_strat_test_strata_combined(self):
        rows = [("v1", i, i, 0) for i in range(12)] + [("v2", i, -i, 0) for i in range(12)]
        t = ks.strat_test(rows, 1, 0, 0)
        self.assertAlmostEqual(t["rho"], 0.0)
        self.assertEqual(t["n"], 24)
        self.assertNotIn("p", t)

    def test_strat_test_adjusted(self):
        flat = ks.strat_test([("v1", i, i, 5) for i in range(10)], 1, 0, 0, adjusted=True)
        self.assertAlmostEqual(flat["rho"], 1.0)
        same = ks.strat_test([("v1", i, (i * 7) % 10, i) for i in range(10)], 1, 100, 0, adjusted=True)
        self.assertIsNone(same["rho"])
        self.assertNotIn("p", same)

    def test_holm(self):
        for a, want in zip(ks.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(a, want)
        self.assertEqual(ks.holm([0.5, 0.9]), [1.0, 1.0])

    def test_grade(self):
        self.assertEqual(ks.grade({"n": 59, "rho": 0.3, "p": 0.01}, 1), "untestable")
        self.assertEqual(ks.grade({"n": 60, "rho": 0.3, "p": 0.01}, 1), "pass")
        self.assertEqual(ks.grade({"n": 60, "rho": -0.3, "p": 0.01}, 1), "fail")
        self.assertEqual(ks.grade({"n": 60, "rho": 0.3, "p": 0.2}, 1), "fail")
        self.assertEqual(ks.grade({"n": 60, "rho": 0.3}, 1), "untestable")

    def test_add_package_and_rows(self):
        pt = {}
        ks.add_package(pt, "P2", "v2", {"glom_area": exp_areas(1.0), "mesangial_fraction": [0.2] * 10})
        ks.add_package(pt, "P1", "v1", {"glom_area": exp_areas(1.0)[:5]})
        ks.add_package(pt, "P1", "v1", {"glom_area": exp_areas(1.0)[5:]})
        ks.add_package(pt, "P3", "v1", {"glom_area": exp_areas(1.0, 9)})
        self.assertEqual(pt["P1"]["versions"], {"v1"})
        clin = {"P1": {"albuminuria": 2}, "P2": {"albuminuria": None}, "P3": {"albuminuria": 5}}
        rows = ks.rows_for(pt, clin, "glom_area", "iqr", "albuminuria")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "v1")
        self.assertEqual(rows[0][2], 2)
        self.assertAlmostEqual(rows[0][1], 4.5)
        self.assertAlmostEqual(rows[0][3], 4.5)
        n_rows = ks.rows_for(pt, clin, "glom_area", "iqr", "n_gloms")
        self.assertEqual([(r[0], r[2]) for r in n_rows], [("v1", 10), ("v2", 10)])
        mes = ks.rows_for(pt, clin, "mesangial_fraction", "iqr", "n_gloms")
        self.assertEqual(len(mes), 1)
        self.assertEqual(mes[0][0], "v2")
        self.assertAlmostEqual(mes[0][1], 0.0)
        self.assertAlmostEqual(mes[0][3], 0.2)

    def test_level_counts(self):
        self.assertEqual(ks.level_counts([("v1", 0, 2, 0), ("v1", 0, 2, 0), ("v2", 0, 5, 0)]), {"2": 2, "5": 1})

    def test_run_test(self):
        pt, clin = {}, {}
        for k in range(12):
            pid = "P%02d" % k
            ks.add_package(pt, pid, "v1", {"glom_area": exp_areas((k + 1) / 10)})
            clin[pid] = {"albuminuria": 1 + k // 3}
        spec = ("T", "glom_area", "iqr", "albuminuria", 1, False)
        out = ks.run_test(pt, clin, spec, 0, 0)
        self.assertEqual(out["rows"], 12)
        self.assertAlmostEqual(out["test"]["rho"], math.sqrt(135 / 143))
        self.assertAlmostEqual(out["v1_only"]["rho"], math.sqrt(135 / 143))
        self.assertIsNone(out["v2_only"]["rho"])
        self.assertEqual(out["levels"], {"1": 3, "2": 3, "3": 3, "4": 3})
        adj = ks.run_test(pt, clin, ("T", "glom_area", "iqr", "albuminuria", 1, True), 0, 0)
        self.assertIsNone(adj["test"]["rho"])


if __name__ == "__main__":
    unittest.main()
