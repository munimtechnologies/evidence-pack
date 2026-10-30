# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_tbmsz on synthetic tubules (no KPMP data, no network)."""
import math
import unittest

from kidney import kpmp_tbmsz as ts


def tub(tbm, size):
    """A kpmp_tbm0 tubule row: (tbm, cell, lumen, size, medulla)."""
    return (tbm, None, None, size, None)


def participant_rows():
    """10 small tubules (size 1) and 20 large ones (size e^2), all with TBM e^1, plus a zero-TBM row and
    a row without a TBM number."""
    return ([tub(math.e, 1.0)] * 10 + [tub(math.e, math.exp(2))] * 20
            + [tub(0.0, 1.0), tub(None, 1.0)])


class FitTests(unittest.TestCase):
    def test_exact_line(self):
        a, b = ts.fit_line([0.0, 1.0, 2.0], [1.0, 3.0, 5.0])
        self.assertAlmostEqual(a, 1.0)
        self.assertAlmostEqual(b, 2.0)

    def test_no_fit(self):
        self.assertIsNone(ts.fit_line([1.0, 1.0], [2.0, 3.0]))
        self.assertIsNone(ts.fit_line([5.0], [1.0]))

    def test_usable(self):
        x, y = ts.usable(tub(2.0, 4.0))
        self.assertAlmostEqual(x, math.log(4.0))
        self.assertAlmostEqual(y, math.log(2.0))
        self.assertIsNone(ts.usable(tub(0.0, 4.0)))
        self.assertIsNone(ts.usable(tub(-1.0, 4.0)))
        self.assertIsNone(ts.usable(tub(2.0, None)))
        self.assertIsNone(ts.usable(tub(None, 4.0)))

    def test_version_fits(self):
        # ln TBM = 0.5 + 0.25 ln size exactly; the zero row is left out
        rows = [tub(math.exp(0.5 + 0.25 * s), math.exp(s)) for s in (0.0, 2.0, 4.0)] + [tub(0.0, 3.0)]
        fits = ts.version_fits([("a", "v1", rows)])
        self.assertEqual(sorted(fits), ["v1"])
        self.assertAlmostEqual(fits["v1"]["intercept"], 0.5)
        self.assertAlmostEqual(fits["v1"]["slope"], 0.25)
        self.assertEqual(fits["v1"]["n"], 3)


class SizeTests(unittest.TestCase):
    def test_size_cuts(self):
        rows = [tub(1.0, s) for s in (5.0, 1.0, 4.0, 2.0, 3.0)] + [tub(None, 0.5), tub(1.0, 0.0)]
        cuts = ts.size_cuts([("a", "v1", rows)])
        self.assertEqual(cuts, {"v1": 2.0, "v2": None})

    def test_quartile_medians(self):
        rows = [tub(float(s), float(s)) for s in range(1, 9)]
        self.assertEqual(ts.quartile_medians([("a", "v1", rows)]), {"v1": [1.5, 3.5, 5.5, 7.5]})


class ParticipantTests(unittest.TestCase):
    def setUp(self):
        fits = {"v1": {"intercept": 0.0, "slope": 1.0, "n": 30}}
        packages = [("a", "v1", participant_rows()), ("b", "v1", [tub(math.e, 1.0)] * 30),
                    ("c", "v1", [tub(math.e, 1.0)] * 5)]
        self.ptable = ts.participant_table(packages, {"a": "P", "c": "Q"}, fits, {"v1": 2.0, "v2": None})

    def test_table(self):
        self.assertEqual(sorted(self.ptable), ["P", "Q"])
        p = self.ptable["P"]
        self.assertEqual(p["versions"], {"v1"})
        self.assertEqual(p["n"], 31)
        self.assertEqual(p["small"], 11)
        self.assertEqual(len(p["resid"]), 30)
        self.assertEqual(len(p["resid_floor"]), 20)

    def test_features(self):
        p = self.ptable["P"]
        # residual = ln TBM - ln size: +1 for the 10 small, -1 for the 20 large
        self.assertAlmostEqual(ts.feature(p, "tbm_adj"), -1.0)
        self.assertAlmostEqual(ts.feature(p, "tbm_pos"), 1.0)
        self.assertAlmostEqual(ts.feature(p, "tbm_adj_floor"), -1.0)
        self.assertAlmostEqual(ts.feature(p, "tbm_pos_floor"), 1.0)
        self.assertAlmostEqual(ts.feature(p, "small_share"), 11 / 31)
        q = self.ptable["Q"]
        self.assertIsNone(ts.feature(q, "tbm_adj"))
        self.assertIsNone(ts.feature(q, "small_share"))
        with self.assertRaises(KeyError):
            ts.feature(p, "nope")

    def test_rows(self):
        scores = {"P": {"atr": 10.0}, "Q": {"atr": 5.0}}
        clin = {"P": {"egfr": 50.0}}
        rows = ts.test_rows(self.ptable, "tbm_adj", "tiv", "atr", None, scores, clin)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "v1")
        self.assertAlmostEqual(rows[0][1], -1.0)
        self.assertEqual(rows[0][2], 10.0)
        self.assertIsNone(rows[0][3])
        rows = ts.test_rows(self.ptable, "tbm_adj", "clinical", "egfr", "small_share", scores, clin)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], 50.0)
        self.assertAlmostEqual(rows[0][3], 11 / 31)
        rows = ts.test_rows(self.ptable, "tbm_adj", "feature", "tbm_pos", None, scores, clin)
        self.assertAlmostEqual(rows[0][2], 1.0)

    def test_no_fit_no_residuals(self):
        t = ts.participant_table([("a", "v2", participant_rows())], {"a": "P"}, {}, {"v1": None, "v2": None})
        self.assertEqual(t["P"]["resid"], [])
        self.assertEqual(t["P"]["n"], 31)
        self.assertEqual(t["P"]["small"], 0)


class GradeTests(unittest.TestCase):
    def test_grade_one(self):
        self.assertEqual(ts.grade_one({"n": 60, "rho": 0.2, "p": 0.01}, 1), "pass")
        self.assertEqual(ts.grade_one({"n": 60, "rho": 0.2, "p": 0.01}, -1), "fail")
        self.assertEqual(ts.grade_one({"n": 60, "rho": 0.2, "p": 0.05}, 1), "fail")
        self.assertEqual(ts.grade_one({"n": 59, "rho": 0.2, "p": 0.01}, 1), "untestable")
        self.assertEqual(ts.grade_one({"n": 60, "rho": 0.2}, 1), "untestable")
        self.assertEqual(ts.grade_one({"n": 60, "rho": None, "p": 0.01}, 1), "untestable")

    def test_keys(self):
        self.assertEqual(ts.GRADE_KEYS, ("A1_tbm_adj_vs_atrophy", "A2_tbm_adj_vs_egfr",
                                         "A3_tbm_adj_vs_atrophy_given_small"))
        self.assertEqual(len(ts.DESCRIBE), 16)
        self.assertEqual(len({d[0] for d in ts.DESCRIBE}), 16)


if __name__ == "__main__":
    unittest.main()
