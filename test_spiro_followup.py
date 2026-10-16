# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import random
import unittest

import nhanes_spiro as ns
import spiro_followup as sf

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


class TestGroups(unittest.TestCase):
    def test_groups_are_comparator_ingredients(self):
        for k, g in sf.GROUPS.items():
            self.assertTrue(g <= ns.ANTIHYPERTENSIVES, k)
            self.assertNotIn(ns.SPIRO, g)
        self.assertTrue(set(sf.NEGATIVE_CONTROLS) <= set(sf.GROUPS))
        self.assertNotIn("A1_alpha1_blockers", sf.NEGATIVE_CONTROLS)

    def test_sets(self):
        got = sf.antihypertensive_sets([(1, "Hydrochlorothiazide; Spironolactone"), (1, "CLONIDINE"),
                                        (2, "METFORMIN")])
        self.assertEqual(got, {1: {"HYDROCHLOROTHIAZIDE", "CLONIDINE"}, 2: set()})


class TestRows(unittest.TestCase):
    def test_strata(self):
        rows = [{"cycle": "A", "n_other": 1}, {"cycle": "A", "n_other": 2},
                {"cycle": "A", "n_other": 1}, {"cycle": "B", "n_other": 1}]
        self.assertEqual(sf.strata(rows), [[0, 2], [1], [3]])

    def test_permute_keeps_strata(self):
        labels = [1, 0, 0, 1, 0, 0]
        new = sf.permute_labels(labels, [[0, 1, 2], [3, 4, 5]], random.Random(1))
        self.assertEqual(sorted(new[0:3]), [0, 0, 1])
        self.assertEqual(sorted(new[3:6]), [0, 0, 1])
        self.assertEqual(labels, [1, 0, 0, 1, 0, 0])

    def test_regimen_rows(self):
        rows = [{"n_other": 2, "spiro": 1}, {"n_other": 2, "spiro": 0},
                {"n_other": 3, "spiro": 0}, {"n_other": 1, "spiro": 1}]
        self.assertEqual(sf.regimen_rows(rows), [rows[0], rows[2]])

    def test_group_rows(self):
        rows = [{"spiro": 1, "ings": ["CLONIDINE"], "n_other": 1},
                {"spiro": 0, "ings": ["CLONIDINE", "LISINOPRIL"], "n_other": 2},
                {"spiro": 0, "ings": ["AMLODIPINE"], "n_other": 1}]
        got = sf.group_rows(rows, sf.GROUPS["NC1_central_vasodilator"])
        self.assertEqual([(r["spiro"], r["n_other"]) for r in got], [(1, 1), (0, 1)])
        self.assertEqual((rows[1]["spiro"], rows[1]["n_other"]), (0, 2))


class TestRules(unittest.TestCase):
    def test_specificity(self):
        res = {k: {"n_spiro": 50, "beta": 0.1, "ci_high": 0.3} for k in sf.NEGATIVE_CONTROLS}
        self.assertEqual(sf.specificity(res), ("no evidence against specificity", []))
        res["NC3_loop"] = {"n_spiro": 50, "beta": -0.5, "ci_high": -0.1}
        self.assertEqual(sf.specificity(res), ("not specific to spironolactone", ["NC3_loop"]))
        res["NC3_loop"] = {"n_spiro": 10, "beta": -0.5, "ci_high": -0.1}
        self.assertEqual(sf.specificity(res)[1], [])
        res["NC3_loop"] = {"n_spiro": 50, "beta": -0.2, "ci_high": -0.05}
        self.assertEqual(sf.specificity(res)[1], [])
        res["NC3_loop"] = {"n": 5, "error": "no spironolactone contrast"}
        self.assertEqual(sf.specificity(res)[1], [])

    def test_fragile_and_overall(self):
        self.assertFalse(sf.fragile([{"decision": "supported"}]))
        self.assertTrue(sf.fragile([{"decision": "supported"}, {"decision": "inconclusive"}]))
        self.assertTrue(sf.fragile([{"n": 1, "error": "x"}]))
        self.assertEqual(sf.overall(0.01, "supported", [], False), "robust")
        self.assertEqual(sf.overall(0.2, "supported", [], False), "not robust")
        self.assertEqual(sf.overall(0.01, "supported", ["NC3_loop"], False), "not robust")
        self.assertEqual(sf.overall(0.01, "inconclusive", [], False), "mixed")
        self.assertEqual(sf.overall(0.01, "supported", [], True), "mixed")


@unittest.skipUnless(HAVE_NP, "numpy not installed")
class TestNumeric(unittest.TestCase):
    def test_wls_beta(self):
        X = np.array([[1, 0], [1, 0], [1, 1], [1, 1]], dtype=float)
        y = np.array([1.0, 1.0, 3.0, 3.0])
        w = np.array([1.0, 2.0, 1.0, 2.0])
        self.assertAlmostEqual(sf.wls_beta(X, y, w, 1), 2.0, places=9)

    def test_randomization(self):
        rows = [{"spiro": i % 2, "y": 2.0 - (i % 2) + ((i % 5) - 2) * 0.1, "w": 1.0, "age": 50,
                 "female": 0, "race": 3, "educ": 5, "cycle": "A", "n_other": 1} for i in range(40)]
        r = sf.randomization_test(rows, ["A"], n_perm=200, seed=1)
        self.assertAlmostEqual(r["beta"], -1.0, places=9)
        self.assertEqual(r["n_perm"], 200)
        self.assertLess(r["p"], 0.01)


if __name__ == "__main__":
    unittest.main()
