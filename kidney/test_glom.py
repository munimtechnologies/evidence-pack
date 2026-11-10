# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/glom.py. The standard-library parts always run; nothing here needs numpy, torch,
OpenCV, a slide or the model weights. Invented numbers only."""
import os
import tempfile
import unittest

from kidney import glom


class TestTiles(unittest.TestCase):
    def test_starts(self):
        self.assertEqual(glom.tile_starts(1000), [0, 409, 488])
        self.assertEqual(glom.tile_starts(921), [0, 409])
        self.assertEqual(glom.tile_starts(512), [0])
        self.assertEqual(glom.tile_starts(300), [0])

    def test_settings(self):
        self.assertEqual(glom.TARGET_MPP, 1.5)
        self.assertEqual(glom.P_TH, 4000)
        self.assertEqual(glom.MIN_AREA_UM2, 2000.0)


class TestLevel(unittest.TestCase):
    def test_pick(self):
        li, zoom = glom.pick_level([(40000, 20000), (10000, 5000), (2500, 1250)], 0.25)
        self.assertEqual(li, 1)
        self.assertAlmostEqual(zoom, 1.5)

    def test_level0_only(self):
        li, zoom = glom.pick_level([(4000, 2000)], 0.5)
        self.assertEqual(li, 0)
        self.assertAlmostEqual(zoom, 3.0)


class TestHelpers(unittest.TestCase):
    def test_strip_prefix(self):
        self.assertEqual(glom.strip_prefix({"module.a": 1, "module.b": 2}), {"a": 1, "b": 2})
        self.assertEqual(glom.strip_prefix({"a": 1, "module.b": 2}), {"a": 1, "module.b": 2})

    def test_summarize(self):
        s = glom.summarize_regions([1000, 2000, 10], 1.5)
        self.assertEqual(s, {"regions": 3, "glomeruli": 2, "median_area_um2": 3375.0, "total_area_um2": 6750.0,
                             "small_regions": 1})
        self.assertIsNone(glom.summarize_regions([], 1.5)["median_area_um2"])

    def test_kept_areas(self):
        self.assertEqual(glom.kept_areas([2000, 10, 1000], 1.5), [2250.0, 4500.0])
        self.assertEqual(glom.kept_areas([], 1.5), [])

    def test_model_paths(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("unet_model-2.pth", "unet_model-1.pth", "other.pth"):
                open(os.path.join(d, n), "w").close()
            got = [os.path.basename(p) for p in glom.model_paths(d)]
        self.assertEqual(got, ["unet_model-1.pth", "unet_model-2.pth"])


class TestObjects(unittest.TestCase):
    ROWS = [(10, 20, 4, 2, 1000, 11.5, 20.5), (0, 0, 1, 1, 800, 0.0, 0.0)]

    def test_y_scale(self):
        self.assertAlmostEqual(glom.y_scale(1.5, (3000, 2000), (1000, 500)), 2.0)
        self.assertAlmostEqual(glom.y_scale(1.5, [3000, 2000], (1000, 667)), 3000000 / 2001000.0)
        self.assertAlmostEqual(glom.y_scale(1.5, (3000, 1500), (1000, 500)), 1.5)

    def test_region_records(self):
        self.assertEqual(glom.region_records(self.ROWS, 1.5, 1.5), [[18.0, 31.5, 15.0, 30.0, 21.0, 33.0, 2250.0]])
        self.assertEqual(glom.region_records(self.ROWS, 1.5, 2.0), [[18.0, 42.0, 15.0, 40.0, 21.0, 44.0, 2250.0]])
        self.assertEqual(glom.region_records([], 1.5, 1.5), [])

    def test_records_match_the_count(self):
        areas = [r[4] for r in self.ROWS]
        self.assertEqual(len(glom.region_records(self.ROWS, 1.5, 1.5)),
                         glom.summarize_regions(areas, 1.5)["glomeruli"])
        self.assertEqual([r[6] for r in glom.region_records(self.ROWS, 1.5, 1.5)], glom.kept_areas(areas, 1.5))


if __name__ == "__main__":
    unittest.main()
