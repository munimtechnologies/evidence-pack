# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/gsdet.py (stage 5). Invented rows, arrays and random weights only: no KPMP value, id or
image appears here. The standard-library tests always run; the numpy/OpenCV and torch smoke tests run only where
those packages are installed (the compute job runs them before any slide is read)."""
import importlib.util
import math
import os
import tempfile
import unittest

from kidney import gsdet


def _have(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


HAVE_CV = _have("numpy", "cv2")
HAVE_TORCH = _have("numpy", "cv2", "torch", "segmentation_models_pytorch")


def row(pkg, part, size="100 MB", v2=True, access="open"):
    name = "file-%s_Seg_Masks_Features%s.zip" % (pkg, "_v2" if v2 else "")
    return {"Access": access, "Size": size, "File Name": name, "Internal Package ID": pkg, "Participant ID": part}


ROWS = [
    row("0001", "p1"),
    row("0002", "p2", size="400 MB"),
    row("0003", "p3", v2=False),
    row("0004", "p1"),
    row("0005", "p5"),
    row("0006", "p5"),
    row("0007", "p7", size="1.06 GB"),
    row("0000", "p8", size="300 MB"),
    row("0009", "p9", size="57.6 MB"),
    row("0008", "p2", size="50 MB"),
    row("000a", "p10", access="controlled"),
]


class TestSelect(unittest.TestCase):
    def test_size(self):
        self.assertAlmostEqual(gsdet.size_mb("57.6 MB"), 57.6)
        self.assertAlmostEqual(gsdet.size_mb("1.06 GB"), 1060.0)
        self.assertAlmostEqual(gsdet.size_mb("980 KB"), 0.98)
        self.assertIsNone(gsdet.size_mb("big"))
        self.assertIsNone(gsdet.size_mb("12 XB"))
        self.assertIsNone(gsdet.size_mb(""))

    def test_rule(self):
        got = [r["Internal Package ID"] for r in gsdet.select_packages(ROWS, ["0005"])]
        self.assertEqual(got, ["0000", "0001", "0008", "0009"])

    def test_rule_without_exclusions(self):
        got = [r["Internal Package ID"] for r in gsdet.select_packages(ROWS)]
        self.assertEqual(got, ["0000", "0001", "0005", "0008", "0009"])

    def test_split_ok(self):
        sel = gsdet.select_packages(ROWS, ["0005"])
        train, problems = gsdet.split(ROWS, sel, ["0000", "0001"], n_train=2)
        self.assertEqual([r["Internal Package ID"] for r in train], ["0008", "0009"])
        self.assertEqual(problems, [])
        self.assertEqual(gsdet.fetch_list(train)[0]["slide"], "train01")
        self.assertEqual(gsdet.fetch_list(train)[1]["package"], "0009")

    def test_split_wrong_order(self):
        sel = gsdet.select_packages(ROWS, ["0005"])
        _, problems = gsdet.split(ROWS, sel, ["0001", "0000"], n_train=2)
        self.assertEqual(problems, ["the rule does not reproduce the frozen test list"])

    def test_split_short(self):
        sel = gsdet.select_packages(ROWS, ["0005"])
        _, problems = gsdet.split(ROWS, sel, ["0000", "0001"], n_train=3)
        self.assertEqual(problems, ["only 2 training packages"])

    def test_split_leak(self):
        sel = gsdet.select_packages(ROWS, ["0005"])
        train, problems = gsdet.split(ROWS, sel, ["0000", "0008"], n_train=2)
        self.assertEqual([r["Internal Package ID"] for r in train], ["0008", "0009"])
        self.assertEqual(problems, ["the rule does not reproduce the frozen test list",
                                    "a training package comes from a test participant"])


class TestHelpers(unittest.TestCase):
    def test_pick_kind(self):
        allk = {"gs", "ns", "rand"}
        self.assertEqual(gsdet.pick_kind(0.1, allk), "gs")
        self.assertEqual(gsdet.pick_kind(0.5, allk), "ns")
        self.assertEqual(gsdet.pick_kind(0.9, allk), "rand")
        self.assertEqual(gsdet.pick_kind(0.2, {"ns", "rand"}), "ns")
        self.assertEqual(gsdet.pick_kind(0.7, {"ns", "rand"}), "rand")
        self.assertEqual(gsdet.pick_kind(0.99, {"gs"}), "gs")
        self.assertIsNone(gsdet.pick_kind(0.5, set()))

    def test_crop_origin(self):
        self.assertEqual(gsdet.crop_origin(100.4, 50.6), (-44, -93))
        self.assertEqual(gsdet.crop_origin(100.4, 50.6, 288, 3, -2), (-41, -95))
        self.assertEqual(gsdet.crop_origin(10, 10, 4), (8, 8))

    def test_class_of(self):
        self.assertEqual(gsdet.class_of(0.7), "gs")
        self.assertEqual(gsdet.class_of(0.0), "ns")
        self.assertEqual(gsdet.class_of(-1.0), "ns")

    def test_settings(self):
        self.assertEqual((gsdet.CROP, gsdet.PATCH, gsdet.BATCH, gsdet.STEPS, gsdet.SEED), (288, 256, 8, 1500, 5))
        self.assertEqual(gsdet.MINUTES, 240.0)
        self.assertEqual(gsdet.CLASS_WEIGHTS, (1.0, 1.0, 2.0))
        self.assertEqual(gsdet.N_TRAIN, 24)
        self.assertEqual(gsdet.KIND_CODE, {"rand": 0, "ns": 1, "gs": 2})

    def test_slide_pairs(self):
        with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as m:
            for n in ("a.svs", "b.svs", "c.svs"):
                open(os.path.join(w, n), "w").close()
            for n in ("a.ome.tif", "c.ome.tif", "d.ome.tif"):
                open(os.path.join(m, n), "w").close()
            self.assertEqual(gsdet.slide_pairs(w, m), ["a", "c"])

    def test_crops_aggregate(self):
        diag = {"x": {"ok": True, "crops": {"rand": 2, "ns": 3, "gs": 1}},
                "y": {"ok": True, "crops": {"rand": 1, "ns": 0, "gs": 4}}, "z": {"ok": False}}
        agg = gsdet.crops_aggregate(diag)
        self.assertEqual((agg["slides"], agg["ok"], agg["crops"]), (3, 2, {"rand": 3, "ns": 3, "gs": 5}))
        self.assertNotIn("x", [k for k in agg])


@unittest.skipUnless(HAVE_CV, "numpy and OpenCV not installed")
class TestArrays(unittest.TestCase):
    def test_crop(self):
        import numpy as np
        a = np.arange(25).reshape(5, 5).astype(np.uint8)
        self.assertEqual(gsdet.crop(a, -1, -1, 3, 255).tolist(), [[255, 255, 255], [255, 0, 1], [255, 5, 6]])
        self.assertEqual(gsdet.crop(a, 3, 3, 3, 0).tolist(), [[18, 19, 0], [23, 24, 0], [0, 0, 0]])
        self.assertEqual(gsdet.crop(a, 10, 10, 2, 7).tolist(), [[7, 7], [7, 7]])
        rgb = np.zeros((4, 4, 3), np.uint8)
        self.assertEqual(gsdet.crop(rgb, 0, 0, 6, 255).shape, (6, 6, 3))

    def test_centers(self):
        import numpy as np
        cmap = np.zeros((400, 400), np.uint8)
        cmap[50:100, 50:100] = 2
        cmap[200:210, 200:210] = 1
        cmap[300:350, 300:350] = 1
        img = np.full((400, 400, 3), 255, np.uint8)
        img[0:160, 0:160] = (200, 50, 50)
        got = gsdet.centers(cmap, img, 1.5, np.random.RandomState(0))
        kinds = [k for k, _, _ in got]
        self.assertEqual((kinds.count("gs"), kinds.count("ns"), kinds.count("rand")), (1, 1, 25))
        self.assertEqual(got[0], ("gs", 74.5, 74.5))
        self.assertEqual(got[1], ("ns", 324.5, 324.5))
        for k, x, y in got[2:]:
            self.assertTrue(0 <= x < 160 and 0 <= y < 160 and x % 16 == 0 and y % 16 == 0)

    def test_slide_crops(self):
        import numpy as np
        cmap = np.zeros((400, 400), np.uint8)
        cmap[50:100, 50:100] = 2
        img = np.full((400, 400, 3), 255, np.uint8)
        img[0:160, 0:160] = (200, 50, 50)
        xs, ys, kinds = gsdet.slide_crops(img, cmap, 1.5, np.random.RandomState(1))
        self.assertEqual(len(xs), 26)
        self.assertEqual(kinds[0], 2)
        self.assertEqual(xs[0].shape, (288, 288, 3))
        self.assertEqual(ys[0].shape, (288, 288))
        self.assertEqual(int((ys[0] == 2).sum()), 2500)

    def test_draw_and_batch(self):
        import numpy as np
        rng = np.random.RandomState(0)
        xs = rng.randint(0, 256, size=(6, 96, 96, 3)).astype(np.uint8)
        ys = rng.randint(0, 3, size=(6, 96, 96)).astype(np.uint8)
        kinds = np.array([0, 1, 2, 0, 1, 2], np.uint8)
        idx = gsdet.draw_indices(kinds, 50, rng)
        self.assertEqual(len(idx), 50)
        self.assertTrue(all(0 <= i < 6 for i in idx))
        only_ns = gsdet.draw_indices(np.array([1, 1, 0], np.uint8), 20, rng, probs=(("ns", 1.0),))
        self.assertTrue(all(i in (0, 1) for i in only_ns))
        mean = np.array([0.5, 0.5, 0.5], np.float32)
        std = np.array([0.25, 0.25, 0.25], np.float32)
        xb, yb = gsdet.make_batch(xs, ys, idx[:2], rng, mean, std, patch=64)
        self.assertEqual((xb.shape, str(xb.dtype)), ((2, 3, 64, 64), "float32"))
        self.assertEqual((yb.shape, str(yb.dtype)), ((2, 64, 64), "int64"))
        self.assertTrue(xb.flags["C_CONTIGUOUS"])
        self.assertTrue(set(np.unique(yb).tolist()) <= {0, 1, 2})

    def test_batch_keeps_pixels_with_labels(self):
        import numpy as np
        xs = np.zeros((1, 8, 8, 3), np.uint8)
        ys = np.zeros((1, 8, 8), np.uint8)
        xs[0, 2, 5] = 255
        ys[0, 2, 5] = 2
        mean = np.zeros(3, np.float32)
        std = np.ones(3, np.float32)
        for seed in range(8):
            xb, yb = gsdet.make_batch(xs, ys, [0], np.random.RandomState(seed), mean, std, patch=8)
            self.assertEqual(np.argwhere(xb[0, 0] == 1.0).tolist(), np.argwhere(yb[0] == 2).tolist())

    def test_decode(self):
        import numpy as np
        pbg = np.ones((300, 300), np.float32)
        pgs = np.zeros((300, 300), np.float32)
        pbg[10:60, 10:60] = 0.1
        pgs[10:60, 10:60] = 0.8
        pbg[100:150, 100:150] = 0.1
        pgs[100:150, 100:150] = 0.1
        pbg[200:210, 200:210] = 0.1
        objs, classes = gsdet.decode(pbg, pgs, 1.5, 1.5, strip_rows=37)
        self.assertEqual(classes, ["gs", "ns"])
        self.assertEqual(objs[0], [52.5, 52.5, 15.0, 15.0, 90.0, 90.0, 5625.0])
        self.assertEqual(len(objs), 2)


@unittest.skipUnless(HAVE_TORCH, "torch / segmentation_models_pytorch not installed")
class TestTorch(unittest.TestCase):
    def test_expand_head(self):
        import torch
        sd = gsdet.new_model(2).state_dict()
        sd3 = gsdet.expand_head(sd)
        m3 = gsdet.new_model(3)
        m3.load_state_dict(sd3, strict=True)
        w = sd3["segmentation_head.0.weight"]
        self.assertEqual(int(w.shape[0]), 3)
        self.assertTrue(torch.equal(w[2], w[1]))
        self.assertTrue(torch.equal(sd3["segmentation_head.0.bias"][2], sd["segmentation_head.0.bias"][1]))

    def test_train_and_detect_end_to_end(self):
        import numpy as np
        import torch
        torch.set_num_threads(2)
        rng = np.random.RandomState(0)
        with tempfile.TemporaryDirectory() as d:
            init = os.path.join(d, "unet_model-1.pth")
            m2 = gsdet.new_model(2)
            torch.save({"model": {"module." + k: v for k, v in m2.state_dict().items()},
                        "stats": [np.array([0.6, 0.5, 0.7], np.float32), np.array([0.2, 0.2, 0.2], np.float32)]},
                       init)
            crops = os.path.join(d, "crops")
            os.makedirs(crops)
            np.savez(os.path.join(crops, "a.npz"),
                     x=rng.randint(0, 256, size=(3, gsdet.CROP, gsdet.CROP, 3)).astype(np.uint8),
                     y=rng.randint(0, 3, size=(3, gsdet.CROP, gsdet.CROP)).astype(np.uint8),
                     k=np.array([0, 1, 2], np.uint8))
            np.savez(os.path.join(crops, "b.npz"), x=np.zeros((0, gsdet.CROP, gsdet.CROP, 3), np.uint8),
                     y=np.zeros((0, gsdet.CROP, gsdet.CROP), np.uint8), k=np.zeros((0,), np.uint8))
            out = os.path.join(d, "gs5.pth")
            s = gsdet.train(crops, init, out, steps=2, minutes=30.0, batch=2)
            self.assertEqual((s["steps"], s["crops"]), (2, 3))
            self.assertGreater(s["bn_frozen"], 0)
            self.assertTrue(math.isfinite(s["first_loss"]))
            model, mean, std, steps = gsdet.load_model3(out)
            self.assertEqual(steps, 2)
            self.assertAlmostEqual(float(mean[0]), 0.6, places=5)
            img = rng.randint(0, 256, size=(300, 520, 3)).astype(np.uint8)
            pbg, pgs, used, skipped = gsdet.predict3(img, model, mean, std, tta=True)
            self.assertEqual((pbg.shape, pgs.shape), ((300, 520), (300, 520)))
            self.assertEqual((used, skipped), (2, 0))   # padded to 512 x 520: tiles at x = 0 and x = 8
            self.assertTrue(float(pbg.min()) >= 0.0 and float(pbg.max()) <= 1.0 + 1e-5)
            self.assertTrue(float((pbg + pgs).max()) <= 1.0 + 1e-5)
            objs, classes = gsdet.decode(pbg, pgs, 1.5, 1.5)
            self.assertEqual(len(objs), len(classes))
            self.assertTrue(set(classes) <= {"gs", "ns"})


if __name__ == "__main__":
    unittest.main()
