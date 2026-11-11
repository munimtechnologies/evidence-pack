# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/anom.py on synthetic numbers only (no KPMP data). numpy parts are skipped without numpy."""
import importlib.util
import json
import os
import tempfile
import unittest

from kidney import anom

HAS_NUMPY = importlib.util.find_spec("numpy") is not None


class TestStandardize(unittest.TestCase):
    def test_zscores_and_constant_column(self):
        self.assertEqual(anom.standardize([[1, 5], [3, 5]]), [[-1.0, 0.0], [1.0, 0.0]])

    def test_empty_and_ragged(self):
        self.assertEqual(anom.standardize([]), [])
        with self.assertRaises(ValueError):
            anom.standardize([[1, 2], [3]])


class TestKnn(unittest.TestCase):
    X = [[0], [1], [10]]
    G = ["a", "a", "b"]

    def test_k1_other_groups_only(self):
        self.assertEqual(anom.knn_scores(self.X, self.G, 1), [10.0, 9.0, 9.0])

    def test_k2_uses_what_exists(self):
        self.assertEqual(anom.knn_scores(self.X, self.G, 2), [10.0, 9.0, 9.5])

    def test_single_group_gives_none(self):
        self.assertEqual(anom.knn_scores([[0], [1]], ["a", "a"], 1), [None, None])

    def test_bad_args(self):
        with self.assertRaises(ValueError):
            anom.knn_scores([[0]], ["a", "b"], 1)
        with self.assertRaises(ValueError):
            anom.knn_scores([[0]], ["a"], 0)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_matches(self):
        for k in (1, 2):
            want = anom.knn_scores(self.X, self.G, k)
            got = anom.knn_scores_np(self.X, self.G, k, chunk=2)
            for w, g in zip(want, got):
                self.assertAlmostEqual(w, g, places=9)
        self.assertEqual(anom.knn_scores_np([[0], [1]], ["a", "a"], 1), [None, None])


class TestAuroc(unittest.TestCase):
    def test_values(self):
        self.assertEqual(anom.auroc([0.9, 0.8, 0.3, 0.1], [1, 0, 1, 0]), 0.75)
        self.assertEqual(anom.auroc([1, 1], [1, 0]), 0.5)
        self.assertEqual(anom.auroc([3, None, 1], [1, 1, 0]), 1.0)
        self.assertIsNone(anom.auroc([1, 2], [1, 1]))
        with self.assertRaises(ValueError):
            anom.auroc([1, 2], [1, 2])


@unittest.skipUnless(HAS_NUMPY, "numpy not installed")
class TestMahalanobis(unittest.TestCase):
    REF = [[1, 0], [-1, 0], [0, 1], [0, -1]]

    def test_isotropic_reference(self):
        for shrink in (0.0, 0.5):
            got = anom.mahalanobis_np(self.REF, [[0, 0], [2, 2]], shrink=shrink)
            self.assertAlmostEqual(got[0], 0.0, places=9)
            self.assertAlmostEqual(got[1], 4.0, places=9)

    def test_bad_args(self):
        with self.assertRaises(ValueError):
            anom.mahalanobis_np(self.REF, [[0, 0]], shrink=2)
        with self.assertRaises(ValueError):
            anom.mahalanobis_np([[1, 0]], [[0, 0]])


class TestTopAndBurden(unittest.TestCase):
    S = [5, 4, 3, 2, 1, None]
    G = ["a", "a", "b", "b", "c", "c"]

    def test_top_count_is_integer_ceiling(self):
        self.assertEqual(anom.top_indices(self.S, 400), [0, 1])
        self.assertEqual(anom.top_indices(list(range(20)), 50), [19])
        self.assertEqual(anom.top_indices([1, 1, 1], 334), [0, 1])
        self.assertEqual(anom.top_indices([None], 50), [])
        with self.assertRaises(ValueError):
            anom.top_indices(self.S, 0)

    def test_burden_and_concentration(self):
        self.assertEqual(anom.burden(self.S, self.G, 400), {"a": 1.0, "b": 0.0, "c": 0.0})
        self.assertEqual(anom.concentration(self.S, self.G, 400), 1.0)
        self.assertEqual(anom.concentration([1, 2], ["a", "b"], 1000), 0.5)
        self.assertIsNone(anom.concentration([None], ["a"], 50))


class TestRankStats(unittest.TestCase):
    def test_ranks_with_ties(self):
        self.assertEqual(anom.ranks([5, 1, 5]), [2.5, 1.0, 2.5])
        self.assertEqual(anom.ranks([3, 1, 2]), [3.0, 1.0, 2.0])

    def test_spearman(self):
        self.assertEqual(anom.spearman([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertEqual(anom.spearman([1, 2, 3], [30, 20, 10]), -1.0)
        self.assertIsNone(anom.spearman([1, 2, 3], [7, 7, 7]))
        self.assertIsNone(anom.spearman([1, 2], [1, 2]))

    def test_partial(self):
        # ranks: x 1..4, y (1,3,2,4), z (1.5,1.5,3.5,3.5): rxy 0.8, rxz 2/sqrt(5), ryz 1/sqrt(5) -> 0.4/0.4
        self.assertAlmostEqual(anom.partial_spearman([1, 2, 3, 4], [1, 3, 2, 4], [1, 1, 2, 2]), 1.0, places=9)
        self.assertIsNone(anom.partial_spearman([1, 2, 3, 4], [1, 3, 2, 4], [0, 0, 0, 0]))
        self.assertIsNone(anom.partial_spearman([1, 2, 3, 4], [1, 3, 2, 4], [2, 4, 6, 8]))

    def test_perm_p(self):
        x = list(range(12))
        z = [0, 1] * 6
        r, p = anom.perm_p(x, list(x), z, 200, seed=7)
        self.assertAlmostEqual(r, 1.0, places=9)
        self.assertLessEqual(p, 0.01)
        self.assertEqual(anom.perm_p(x, list(x), z, 200, seed=7), (r, p))
        self.assertEqual(anom.perm_p(x, list(x), z, 0, seed=7)[1], 1.0)
        self.assertEqual(anom.perm_p(x, list(x), [0] * 12, 10, seed=7), (None, None))

    def test_holm(self):
        got = anom.holm([0.01, 0.04, 0.03])
        for g, w in zip(got, [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(g, w, places=12)
        self.assertEqual(anom.holm([0.5, 0.9]), [1.0, 1.0])
        self.assertEqual(anom.holm([]), [])


@unittest.skipUnless(HAS_NUMPY, "numpy not installed")
class TestNumpyFeatures(unittest.TestCase):
    def test_masked_mean_area_weighted(self):
        import numpy as np
        fmap = np.array([[[1, 9], [4, 9]], [[0, 7], [3, 7]]], dtype=np.float64)
        mask = np.zeros((4, 4), dtype=bool)
        mask[0:3, 0:2] = True
        self.assertEqual(anom.masked_mean(fmap, mask), [2.0, 1.0])
        self.assertIsNone(anom.masked_mean(fmap, np.zeros((4, 4), dtype=bool)))

    def test_baseline_features(self):
        import numpy as np
        rgb = np.full((4, 4, 3), 100, dtype=np.uint8)
        rgb[0, 0] = 250
        mask = np.zeros((4, 4), dtype=bool)
        mask[0:2, 0:3] = True
        f = anom.baseline_features(rgb, mask)
        self.assertEqual(len(f), len(anom.BASELINE_NAMES))
        self.assertEqual(f[0], 6.0)
        self.assertEqual(f[1], 1.0)
        self.assertAlmostEqual(f[2], 2 / 3, places=12)
        self.assertEqual(f[3:6], [125.0, 125.0, 125.0])
        for v in f[6:9]:
            self.assertAlmostEqual(v, 3125 ** 0.5, places=9)
        self.assertAlmostEqual(f[9], 1 / 6, places=12)
        self.assertIsNone(anom.baseline_features(rgb, np.zeros((4, 4), dtype=bool)))


class TestCli(unittest.TestCase):
    def test_score_file(self):
        objs = {"objects": [{"group": "a", "x": [0.0]}, {"group": "a", "x": [1.0]}, {"group": "b", "x": [10.0]}]}
        with tempfile.TemporaryDirectory() as d:
            inp, out = os.path.join(d, "o.json"), os.path.join(d, "s.json")
            with open(inp, "w", encoding="utf-8") as f:
                json.dump(objs, f)
            self.assertEqual(anom.main(["score", "--in", inp, "--k", "1", "--top-permille", "1", "--out", out]), 0)
            with open(out, encoding="utf-8") as f:
                doc = json.load(f)
        self.assertTrue(doc["private"])
        self.assertEqual(doc["n_objects"], 3)
        self.assertEqual(doc["n_groups"], 2)
        self.assertEqual(len(doc["scores"]), 3)
        self.assertEqual(doc["top"], [0])
        self.assertEqual(doc["code_version"], anom.CODE_VERSION)


if __name__ == "__main__":
    unittest.main()
