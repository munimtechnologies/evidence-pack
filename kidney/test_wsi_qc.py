# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney.wsi_qc. Standard-library parts always run; pixel parts need numpy (and tifffile)."""
import csv
import json
import os
import tempfile
import unittest

from kidney import wsi_qc as q

try:
    import numpy as np
except ImportError:  # the stdlib-only test run skips the pixel tests
    np = None
try:
    import tifffile
except ImportError:
    tifffile = None

DESC = ("Aperio Image Library v11.2.1 \r\n46000x32914 [0,100 46000x32814] (240x240) JPEG/RGB Q=30"
        "|AppMag = 40|StripeWidth = 2040|ScanScope ID = SS1234|MPP = 0.2520|Date = 01/02/19")

PINK, WHITE, GREEN, BLACK = (200, 120, 180), (240, 240, 240), (60, 140, 90), (10, 10, 10)


class TestStdlib(unittest.TestCase):
    def test_parse_aperio(self):
        self.assertEqual(q.parse_aperio(DESC), {"mpp": 0.252, "appmag": 40.0, "scanner": "SS1234"})
        self.assertEqual(q.parse_aperio(""), {"mpp": None, "appmag": None, "scanner": None})
        self.assertEqual(q.parse_aperio(None)["mpp"], None)

    def test_pick_thumb_level(self):
        sizes = [(40000, 30000), (10000, 7500), (2500, 1875)]
        self.assertEqual(q.pick_thumb_level(sizes), 2)
        self.assertEqual(q.pick_thumb_level(sizes, side=3000), 2)  # level 1 is over 40M pixels
        self.assertEqual(q.pick_thumb_level([(1000, 800)]), 0)
        self.assertIsNone(q.pick_thumb_level([(10000, 9000)]))
        self.assertEqual(q.pick_thumb_level([(8000, 4000), (4000, 2000), (1000, 500)]), 1)

    def test_pick_spread(self):
        self.assertEqual(q.pick_spread(10, 4), [0, 3, 6, 9])
        self.assertEqual(q.pick_spread(3, 16), [0, 1, 2])
        self.assertEqual(q.pick_spread(0, 16), [])
        self.assertEqual(q.pick_spread(5, 1), [0])
        self.assertEqual(len(q.pick_spread(13952, 16)), 16)

    def test_components_and_pieces(self):
        grid = [[1, 1, 0, 0],
                [1, 0, 0, 1],
                [0, 0, 0, 1],
                [1, 0, 0, 0]]
        sizes = q.count_components(grid)
        self.assertEqual(sizes, [3, 2, 1])
        self.assertEqual(q.piece_count(sizes, min_share=0.2), 2)
        self.assertEqual(q.piece_count(sizes, min_share=0.5), 1)  # threshold 3 cells
        self.assertEqual(q.piece_count(sizes, min_share=0.6), 0)  # threshold 3.6 cells
        self.assertEqual(q.piece_count([]), 0)

    def test_tile_origins(self):
        grid = [[False, True], [False, False]]
        self.assertEqual(q.tile_origins(grid, cell=2, ds=10, w0=100, h0=100, k=4, tile=8), [(26, 6)])
        # clipped at the far edge and at zero
        self.assertEqual(q.tile_origins([[True]], cell=10, ds=1, w0=10, h0=10, k=1, tile=8), [(1, 1)])
        self.assertEqual(q.tile_origins([[True]], cell=10, ds=1, w0=6, h0=6, k=1, tile=8), [(0, 0)])

    def test_median_or_none(self):
        self.assertIsNone(q.median_or_none([None, None]))
        self.assertEqual(q.median_or_none([3, None, 1, 2]), 2)


@unittest.skipUnless(np is not None, "numpy not installed")
class TestPixels(unittest.TestCase):
    def test_masks(self):
        a = np.array([[WHITE, PINK, BLACK, GREEN]], dtype=np.uint8)
        self.assertEqual(q.tissue_mask(a).tolist(), [[False, True, False, False]])
        self.assertEqual(q.green_ink_mask(a).tolist(), [[False, False, False, True]])
        self.assertEqual(q.black_mask(a).tolist(), [[False, False, True, False]])

    def test_od_means(self):
        a = np.array([[[255, 255, 255], [0, 0, 0]]], dtype=np.uint8)
        self.assertEqual(q.od_means(a, [[True, False]]), [0.0, 0.0, 0.0])
        self.assertEqual(q.od_means(a, [[False, False]]), [None, None, None])
        od = q.od_means(np.array([[PINK]], dtype=np.uint8), [[True]])
        self.assertTrue(0 < od[0] < od[2] < od[1])  # red 200 > blue 180 > green 120 in intensity

    def test_laplacian_var(self):
        self.assertEqual(q.laplacian_var(np.full((5, 5), 7.0)), 0.0)
        board = np.indices((4, 4)).sum(axis=0) % 2
        self.assertAlmostEqual(q.laplacian_var(board), 16.0)
        self.assertIsNone(q.laplacian_var(np.zeros((2, 5))))

    def test_coarse_grid(self):
        m = np.zeros((4, 4), dtype=bool)
        m[:2, :2] = True
        self.assertEqual(q.coarse_grid(m, grid=2), ([[True, False], [False, False]], 2))


@unittest.skipUnless(np is not None and tifffile is not None, "numpy and tifffile needed")
class TestEndToEnd(unittest.TestCase):
    def test_synthetic_slide(self):
        img = np.empty((1024, 1024, 3), dtype=np.uint8)
        img[:, :] = WHITE
        img[0:450, :] = PINK      # piece A: 450 rows
        img[600:1024, :] = PINK   # piece B: 424 rows
        img[500:510, 0:100] = GREEN  # 1,000 pixels of green ink in the gap
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "in"), os.path.join(d, "out")
            os.makedirs(src)
            tifffile.imwrite(os.path.join(src, "synthetic.svs"), img, tile=(256, 256), photometric="rgb")
            with open(os.path.join(src, "notes.txt"), "w") as f:
                f.write("not a slide")
            self.assertEqual(q.main(["--in-dir", src, "--out-dir", out]), 0)
            with open(os.path.join(out, "qc.json"), encoding="utf-8") as f:
                doc = json.load(f)
            with open(os.path.join(out, "qc.csv"), encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        r = doc["rows"][0]
        self.assertTrue(r["ok"], r["errors"])
        self.assertEqual((r["width"], r["height"], r["n_levels"], r["thumb_level"]), (1024, 1024, 1, 0))
        self.assertEqual(r["tissue_fraction"], 0.8535)          # 874 * 1024 / 1024**2
        self.assertEqual(r["green_ink_fraction"], 0.00095)      # 1,000 / 1,048,576
        self.assertEqual(r["pieces"], 2)
        self.assertEqual(r["piece_cells_top3"], "7168 6784")    # 56 and 53 grid rows of 128 cells
        self.assertEqual(r["blur_tiles"], 16)
        self.assertGreater(r["blur_median"], 0.0)               # every tile holds a tissue/background edge
        self.assertIsNone(r["mpp"])
        self.assertEqual(doc["summary"]["multi_piece"], 1)
        self.assertEqual(doc["summary"]["with_green_ink"], 0)    # 0.00095 is under the 0.001 flag
        self.assertEqual(rows[0]["slide"], "synthetic")

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(q.main(["--in-dir", d, "--out-dir", os.path.join(d, "o")]), 2)


if __name__ == "__main__":
    unittest.main()
