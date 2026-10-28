# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_zs. Tubule rows are (tbm, cell, lumen, size, medulla) tuples, the shape
kidney.kpmp_tbm0.tubules returns."""
import unittest

from kidney import kpmp_census as kc
from kidney import kpmp_zs as zs

W = [3, 11, 7, 1, 9, 5, 12, 2, 8, 4, 10, 6]


def p1_rows():
    """20 tubules with a TBM number (5 zero, small, collapsed) and one without."""
    rows = [(0.0, 28.0, 0.01, 10, None)] * 5 + [(2.0, 30.0, 0.2, 100, None)] * 15
    return rows + [(None, 30.0, 0.2, 100, None)]


def p2_rows():
    """25 v1 tubules: 5 zero rows in the medulla, 20 positive cortex rows, no luminal fraction."""
    return [(0.0, 28.0, None, 80, 1)] * 5 + [(3.0, 30.0, None, 80, 0)] * 20


def table():
    packages = [("pkA", "v2", p1_rows()), ("pkB", "v1", p2_rows()), ("pkC", "v2", p1_rows())]
    return zs.participant_table(packages, {"pkA": "P1", "pkB": "P2"}, {"v1": 50, "v2": 50})


class TestHelpers(unittest.TestCase):
    def test_quantile(self):
        self.assertEqual(zs.quantile([5, 1, 3, 2, 4], 0.25), 2)
        self.assertEqual(zs.quantile([7], 0.25), 7)
        self.assertIsNone(zs.quantile([], 0.25))

    def test_size_cuts(self):
        rows = [(1.0, 1.0, 0.1, s, None) for s in range(1, 9)] + [(None, 1.0, 0.1, 0.5, None), (1.0, 1.0, 0.1, 0, None)]
        self.assertEqual(zs.size_cuts([("a", "v2", rows)]), {"v1": None, "v2": 2})

    def test_residuals(self):
        for a, b in zip(zs.residuals([1, 2, 3, 4], [1, 2, 3, 4]), [0, 0, 0, 0]):
            self.assertAlmostEqual(a, b)
        self.assertEqual(zs.residuals([1, 2, 3], [5, 5, 5]), [-1, 0, 1])


class TestParticipants(unittest.TestCase):
    def test_counts(self):
        pt = table()
        self.assertEqual(sorted(pt), ["P1", "P2"])
        p1, p2 = pt["P1"], pt["P2"]
        self.assertEqual((p1["n"], p1["zero"], p1["n_cortex"], p1["zero_cortex"]), (20, 5, 20, 5))
        self.assertEqual((p1["small"], p1["lumen_n"], p1["collapsed"]), (5, 20, 5))
        self.assertEqual((p2["n"], p2["zero"], p2["n_cortex"], p2["zero_cortex"]), (25, 5, 20, 0))
        self.assertEqual((p2["small"], p2["lumen_n"]), (0, 0))

    def test_features(self):
        pt = table()
        self.assertEqual([zs.feature(pt["P1"], f) for f in
                          ("zero_share", "zero_share_cortex", "size_med", "small_share", "collapsed_share")],
                         [0.25, 0.25, 100, 0.25, 0.25])
        self.assertEqual([zs.feature(pt["P2"], f) for f in
                          ("zero_share", "zero_share_cortex", "size_med", "small_share", "collapsed_share")],
                         [0.2, 0.0, 80, 0.0, None])

    def test_floor(self):
        pt = zs.participant_table([("pk", "v2", p1_rows()[1:])], {"pk": "P"}, {"v2": 50})
        self.assertEqual(pt["P"]["n"], 19)
        self.assertIsNone(zs.feature(pt["P"], "zero_share"))
        self.assertIsNone(zs.feature(pt["P"], "size_med"))

    def test_rows(self):
        pt = table()
        scores = {"P1": {kc.ATROPHY_SCORE: 10.0}}
        clin = {"P1": {"egfr": 90.0, "age_bin": 50}, "P2": {"egfr": 60.0, "age_bin": None}}
        self.assertEqual(zs.test_rows(pt, "zero_share", "clinical", "egfr", "age_bin", scores, clin),
                         [("v2", 0.25, 90.0, 50)])
        self.assertEqual(zs.test_rows(pt, "zero_share", "clinical", "egfr", None, scores, clin),
                         [("v2", 0.25, 90.0, None), ("v1", 0.2, 60.0, None)])
        self.assertEqual(zs.test_rows(pt, "zero_share", "clinical", "egfr", "collapsed_share", scores, clin),
                         [("v2", 0.25, 90.0, 0.25)])
        self.assertEqual(zs.test_rows(pt, "zero_share", "tiv", kc.ATROPHY_SCORE, "size_med", scores, clin),
                         [("v2", 0.25, 10.0, 100)])


class TestPartial(unittest.TestCase):
    def test_identical_and_reversed(self):
        same = [("v2", w, w, z) for z, w in enumerate(W)]
        t = zs.partial_test(same, 1, 200, 7)
        self.assertAlmostEqual(t["rho"], 1.0)
        self.assertEqual(t["strata"], [12])
        self.assertLess(t["p"], 0.05)
        rev = [("v2", w, -w, z) for z, w in enumerate(W)]
        self.assertAlmostEqual(zs.partial_test(rev, 1, 0, 0)["rho"], -1.0)

    def test_covariate_explains_both(self):
        rows = [("v2", z, 2 * z, z) for z in range(12)]
        self.assertIsNone(zs.partial_test(rows, 1, 0, 0)["rho"])

    def test_small_stratum_dropped(self):
        rows = [("v2", w, w, z) for z, w in enumerate(W)] + [("v1", w, -w, z) for z, w in enumerate(W[:9])]
        t = zs.partial_test(rows, 1, 0, 0)
        self.assertEqual((t["n"], t["strata"]), (12, [12]))
        self.assertAlmostEqual(t["rho"], 1.0)


class TestGrade(unittest.TestCase):
    def test_grade(self):
        tests = {k: {"floor_ok": True, "partial": {"rho": 0.3 * d, "p": 0.01}} for k, _, _, _, d in zs.TESTS}
        tests["S1_zero_share_vs_atrophy_given_size"]["floor_ok"] = False
        tests["S2_zero_share_vs_egfr_given_size"]["partial"] = {"rho": 0.3, "p": 0.01}
        tests["S3_zero_share_vs_atrophy_given_age"]["partial"] = {"rho": 0.3, "p": 0.2}
        g = zs.grade({"tests": tests})
        self.assertEqual([g[k] for k in zs.GRADE_KEYS], ["untestable", "fail", "fail", "pass", "pass", "pass"])


if __name__ == "__main__":
    unittest.main()
