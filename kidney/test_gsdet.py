# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/gsdet.py (stages 5 and 6). Invented rows, arrays and random weights only: no KPMP value,
id or image appears here. The standard-library tests always run; the numpy/OpenCV and torch smoke tests run only
where those packages are installed (the compute job runs them before any slide is read)."""
import contextlib
import csv
import importlib.util
import io
import json
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


class TestFreshSplit(unittest.TestCase):
    def setUp(self):
        self.sel = gsdet.select_packages(ROWS, ["0005"])

    def test_ok(self):
        test, problems = gsdet.fresh_split(ROWS, self.sel, ["0000"], ["0001"], n_test=2, min_test=1)
        self.assertEqual([r["Internal Package ID"] for r in test], ["0008", "0009"])
        self.assertEqual(problems, [])
        fl = gsdet.fetch_list(test, gsdet.TEST_PREFIX)
        self.assertEqual([s["slide"] for s in fl], ["test601", "test602"])
        self.assertEqual(fl[1]["package"], "0009")

    def test_wrong_training_list_and_leak(self):
        test, problems = gsdet.fresh_split(ROWS, self.sel, ["0000"], ["0008"], n_test=2, min_test=1)
        self.assertEqual([r["Internal Package ID"] for r in test], ["0008", "0009"])
        self.assertEqual(problems, ["the rule does not reproduce the stage 5 training list",
                                    "a test package comes from a frozen or training participant"])

    def test_wrong_frozen_list(self):
        _, problems = gsdet.fresh_split(ROWS, self.sel, ["0001"], ["0000"], n_test=2, min_test=1)
        self.assertEqual(problems, ["the rule does not reproduce the frozen test list",
                                    "the rule does not reproduce the stage 5 training list"])

    def test_short(self):
        test, problems = gsdet.fresh_split(ROWS, self.sel, ["0000"], ["0001"], n_test=3, min_test=3)
        self.assertEqual(len(test), 2)
        self.assertEqual(problems, ["only 2 test packages"])

    def test_cli_select_test(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {k: os.path.join(d, k) for k in ("files.csv", "excl.json", "frozen.json", "train.json",
                                                      "test.json")}
            with open(paths["files.csv"], "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(ROWS[0]))
                w.writeheader()
                w.writerows(ROWS)
            for key, doc in (("excl.json", ["0005"]), ("frozen.json", [{"package": "0000"}]),
                             ("train.json", [{"package": "0001"}])):
                with open(paths[key], "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = gsdet.main(["select-test", "--csv", paths["files.csv"], "--exclude", paths["excl.json"],
                                   "--frozen", paths["frozen.json"], "--train", paths["train.json"],
                                   "--out", paths["test.json"], "--n-test", "2"])
            with open(paths["test.json"], encoding="utf-8") as f:
                fl = json.load(f)
        self.assertEqual(code, 3)   # 2 test packages is below MIN_TEST
        self.assertEqual([s["slide"] for s in fl], ["test601", "test602"])
        out = json.loads(buf.getvalue())
        self.assertEqual((out["selected"], out["test"], out["problems"]), (4, 2, ["only 2 test packages"]))
        self.assertNotIn("0008", buf.getvalue())


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

    def test_pick_kind_arm_b(self):
        b = gsdet.KIND_PROBS_B
        allk = {"gs", "ns", "rand", "hard"}
        self.assertEqual([gsdet.pick_kind(u, allk, b) for u in (0.1, 0.5, 0.7, 0.95)], ["gs", "ns", "rand", "hard"])
        # without hard crops the other three are renormalised: 0.4375 / 0.3125 / 0.25
        self.assertEqual([gsdet.pick_kind(u, {"gs", "ns", "rand"}, b) for u in (0.43, 0.5, 0.8)],
                         ["gs", "ns", "rand"])

    def test_parse_probs(self):
        self.assertEqual(gsdet.parse_probs("gs=0.35,ns=0.25,rand=0.2,hard=0.2"), gsdet.KIND_PROBS_B)
        self.assertEqual(gsdet.parse_probs(" gs = 1 , "), (("gs", 1.0),))
        for bad in ("xx=1", "gs=1,gs=2", "gs=-1", "gs=0", "", "gs", "gs=abc"):
            with self.assertRaises(ValueError, msg=bad):
                gsdet.parse_probs(bad)

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
        self.assertEqual((gsdet.N_TRAIN, gsdet.N_TEST, gsdet.MIN_TEST), (24, 12, 10))
        self.assertEqual(gsdet.KIND_CODE, {"rand": 0, "ns": 1, "gs": 2, "hard": 3})
        self.assertEqual(gsdet.CAPS, (("gs", 50), ("ns", 25), ("rand", 25)))
        self.assertEqual(gsdet.KIND_PROBS, (("gs", 0.4), ("ns", 0.3), ("rand", 0.3)))
        self.assertEqual(gsdet.KIND_PROBS_B, (("gs", 0.35), ("ns", 0.25), ("rand", 0.2), ("hard", 0.2)))
        self.assertEqual((gsdet.HARD_CAP, gsdet.HARD_MAX_OVERLAP), (25, 0.10))

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
        self.assertEqual((agg["slides"], agg["ok"], agg["crops"]),
                         (3, 2, {"rand": 3, "ns": 3, "gs": 5, "hard": 0}))
        self.assertNotIn("x", [k for k in agg])
        self.assertNotIn("hard_found", agg)

    def test_crops_aggregate_hard(self):
        diag = {"a": {"ok": True, "hard_found": 7, "crops": {"hard": 5}},
                "b": {"ok": True, "hard_found": 2, "crops": {"hard": 2}}, "c": {"ok": False, "hard_found": 50}}
        agg = gsdet.crops_aggregate(diag)
        self.assertEqual((agg["crops"]["hard"], agg["hard_found"], agg["crops"]["gs"]), (7, 9, 0))


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

    def test_centers_rand_cap(self):
        import numpy as np
        cmap = np.zeros((400, 400), np.uint8)
        img = np.full((400, 400, 3), 255, np.uint8)
        img[0:160, 0:160] = (200, 50, 50)
        caps = (("gs", 50), ("ns", 25), ("rand", 75))
        got = gsdet.centers(cmap, img, 1.5, np.random.RandomState(0), caps)
        self.assertEqual(len(got), 75)   # 10 x 10 tissue grid points, 75 drawn without replacement
        self.assertEqual(len(set((x, y) for _, x, y in got)), 75)

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

    def test_crops_at_hard(self):
        import numpy as np
        cmap = np.zeros((400, 400), np.uint8)
        cmap[50:100, 50:100] = 2
        img = np.full((400, 400, 3), 255, np.uint8)
        xs, ys, kinds = gsdet.crops_at(img, cmap, [("hard", 74.5, 74.5)], np.random.RandomState(1))
        self.assertEqual(kinds, [3])
        self.assertEqual((xs[0].shape, ys[0].shape), ((288, 288, 3), (288, 288)))
        self.assertEqual(int((ys[0] == 2).sum()), 2500)

    def test_hard_centers(self):
        import numpy as np
        pbg = np.ones((300, 300), np.float32)
        for y0, x0, n in ((10, 10, 50), (100, 100, 50), (200, 200, 50), (270, 10, 10)):
            pbg[y0:y0 + n, x0:x0 + n] = 0.1
        cmap = np.zeros((300, 300), np.uint8)
        cmap[100:150, 100:150] = 1      # fully on a KPMP glomerulus: not a hard negative
        cmap[200:202, 200:250] = 2      # 100 of 2,500 pixels (4%) on a KPMP glomerulus: a hard negative
        got, found = gsdet.hard_centers(pbg, cmap, 1.5, np.random.RandomState(0), strip_rows=37)
        self.assertEqual(found, 2)      # the 100-pixel region is below 2,000 um^2 at 1.5 um
        self.assertEqual(sorted((x, y) for _, x, y in got), [(34.5, 34.5), (224.5, 224.5)])
        self.assertEqual(set(k for k, _, _ in got), {"hard"})
        got, found = gsdet.hard_centers(pbg, cmap, 1.5, np.random.RandomState(0), cap=1)
        self.assertEqual((len(got), found), (1, 2))
        self.assertEqual(gsdet.hard_centers(pbg, cmap, 1.5, np.random.RandomState(0), max_overlap=0.0), ([], 0))
        self.assertEqual(gsdet.hard_centers(pbg, cmap, 1.5, np.random.RandomState(0), max_overlap=1.01)[1], 3)

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
        only_hard = gsdet.draw_indices(np.array([0, 3, 1, 3], np.uint8), 20, rng, probs=(("hard", 1.0),))
        self.assertTrue(all(i in (1, 3) for i in only_hard))
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
            # stage 6 arm B: a second crop folder with one hard crop and the arm B kind mix
            hard = os.path.join(d, "hard")
            os.makedirs(hard)
            np.savez(os.path.join(hard, "a.npz"),
                     x=rng.randint(0, 256, size=(1, gsdet.CROP, gsdet.CROP, 3)).astype(np.uint8),
                     y=np.zeros((1, gsdet.CROP, gsdet.CROP), np.uint8), k=np.array([3], np.uint8))
            out_b = os.path.join(d, "gsB.pth")
            s2 = gsdet.train([crops, hard], init, out_b, steps=2, minutes=30.0, batch=2, probs=gsdet.KIND_PROBS_B)
            self.assertEqual((s2["steps"], s2["crops"], s2["crops_by_kind"]["hard"]), (2, 4, 1))
            self.assertEqual(s2["kind_probs"][3], ["hard", 0.2])
            cmap = np.zeros((300, 520), np.uint8)
            got, found = gsdet.hard_centers(pbg, cmap, 1.5, np.random.RandomState(0))
            self.assertEqual(len(got), min(found, gsdet.HARD_CAP))


if __name__ == "__main__":
    unittest.main()
