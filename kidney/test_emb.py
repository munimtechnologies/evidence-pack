# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/emb.py. Invented records, synthetic images and random weights only: no KPMP value, id or
image appears here. Standard-library tests always run; the numpy/OpenCV test uses a fake encoder; the torch tests
need torch, tifffile and segmentation-models-pytorch and run in the compute job."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

from kidney import emb
from kidney import glom


def _have(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


HAVE_NP = _have("numpy", "cv2")
HAVE_ALL = _have("numpy", "cv2", "tifffile", "torch", "segmentation_models_pytorch")

Z = [0.0] * 7
DOC = {"emb_dim": 2, "rows": [
    {"slide": "s1", "ok": True, "objects": [Z, Z], "classes": ["ns", "gs"], "emb": [[1.0, 2.0], [3.0, 4.0]],
     "base": [[5.0], [6.0]], "clipped": [False, True], "seconds": 30.0},
    {"slide": "s2", "ok": False, "errors": ["x"], "seconds": 6.0},
    {"slide": "s3", "ok": True, "objects": [Z], "classes": ["ns"], "emb": [None], "base": [[7.0]],
     "clipped": [False], "seconds": 24.0},
    {"slide": "s4", "ok": True, "objects": [Z], "classes": ["gs"], "emb": [[9.0, 9.0]], "base": [[8.0]],
     "clipped": [False], "seconds": 0.0},
]}
GROUPS = {"s1": "p1", "s2": "p1", "s3": "p2"}


class TestStdlib(unittest.TestCase):
    def test_check_window(self):
        self.assertEqual(emb.check_window(288), 288)
        self.assertEqual(emb.check_window(32), 32)
        for bad in (0, -32, 300, 288.5):
            with self.assertRaises(ValueError):
                emb.check_window(bad)
        self.assertEqual(emb.WINDOW % emb.STRIDE, 0)

    def test_kept_labels_matches_region_records(self):
        rows = [(0, 0, 1, 1, 888, 0.0, 0.0), (0, 0, 1, 1, 889, 0.0, 0.0), (0, 0, 1, 1, 5000, 0.0, 0.0)]
        self.assertEqual(emb.kept_labels(rows, 1.5), [1, 2])
        self.assertEqual(len(glom.region_records(rows, 1.5, 1.5)), 2)
        self.assertEqual(emb.kept_labels(rows, 1.5, min_area_um2=1998.0), [0, 1, 2])
        self.assertEqual(emb.kept_labels([], 1.5), [])

    def test_clipped_inclusive_bounds(self):
        self.assertFalse(emb.clipped(10, 10, 100, 100, 0, 0))
        self.assertFalse(emb.clipped(188, 188, 100, 100, 0, 0))
        self.assertTrue(emb.clipped(189, 188, 100, 100, 0, 0))
        self.assertTrue(emb.clipped(188, 189, 100, 100, 0, 0))
        self.assertTrue(emb.clipped(-1, 10, 5, 5, 0, 0))
        self.assertFalse(emb.clipped(10, 10, 5, 5, 10, 10, 32))
        self.assertTrue(emb.clipped(9, 10, 5, 5, 10, 10, 32))

    def test_rounded(self):
        self.assertEqual(emb.rounded([1.234567, 2]), [1.23457, 2.0])
        self.assertEqual(emb.rounded([0.14], 1), [0.1])

    def test_table_emb(self):
        objs, skipped = emb.table(DOC, GROUPS, "emb")
        self.assertEqual(objs, [{"group": "p1", "slide": "s1", "index": 1, "class": "ns", "x": [1.0, 2.0]},
                                {"group": "p1", "slide": "s1", "index": 2, "class": "gs", "x": [3.0, 4.0]}])
        self.assertEqual(skipped, {"no_group": 1, "no_vector": 1})

    def test_table_base(self):
        objs, skipped = emb.table(DOC, GROUPS, "base")
        self.assertEqual([(o["group"], o["slide"], o["index"], o["class"], o["x"]) for o in objs],
                         [("p1", "s1", 1, "ns", [5.0]), ("p1", "s1", 2, "gs", [6.0]), ("p2", "s3", 1, "ns", [7.0])])
        self.assertEqual(skipped, {"no_group": 1, "no_vector": 0})

    def test_table_bad_kind(self):
        with self.assertRaises(ValueError):
            emb.table(DOC, GROUPS, "pixels")

    def test_aggregate(self):
        self.assertEqual(emb.aggregate(DOC), {"code_version": emb.CODE_VERSION, "slides": 4, "ok": 3, "objects": 4,
                                              "with_emb": 3, "clipped": 1, "emb_dim": 2, "minutes": 1.0})
        self.assertEqual(emb.aggregate({"rows": []})["slides"], 0)

    def test_table_cli_feeds_anom(self):
        from kidney import anom
        with tempfile.TemporaryDirectory() as d:
            pe, pg, po = (os.path.join(d, n) for n in ("emb.json", "groups.json", "objects.json"))
            with open(pe, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            with open(pg, "w", encoding="utf-8") as f:
                json.dump(GROUPS, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = emb.main(["table", "--emb", pe, "--groups", pg, "--kind", "emb", "--out", po])
            with open(po, encoding="utf-8") as f:
                out = json.load(f)
            with open(pg, "w", encoding="utf-8") as f:
                json.dump({}, f)
            with contextlib.redirect_stdout(io.StringIO()):
                code_empty = emb.main(["table", "--emb", pe, "--groups", pg, "--out", po])
        self.assertEqual(code, 0)
        self.assertEqual(code_empty, 1)
        self.assertEqual((out["kind"], out["private"], len(out["objects"])), ("emb", True, 2))
        self.assertEqual(json.loads(buf.getvalue())["skipped"], {"no_group": 1, "no_vector": 1})
        doc = anom.score_objects(out["objects"], k=1, use_numpy=False)
        self.assertEqual((doc["n_objects"], doc["n_groups"], doc["scores"]), (2, 1, [None, None]))


@unittest.skipUnless(HAVE_NP, "numpy and cv2 needed")
class TestEmbedSlide(unittest.TestCase):
    """Three foreground regions on a 600 x 600 map at 1.5 um/px: B (10 x 10 px, 225 um^2, dropped) lies inside A's
    window, A (40 x 40 px, non-sclerotic), C (60 x 60 px, P(GS) = 1, globally sclerotic)."""

    def _maps(self):
        import numpy as np
        pbg = np.ones((600, 600), dtype="float32")
        pgs = np.zeros((600, 600), dtype="float32")
        pbg[50:60, 200:210] = 0.0
        pbg[100:140, 100:140] = 0.0
        pbg[400:460, 300:360] = 0.0
        pgs[400:460, 300:360] = 1.0
        img = np.full((600, 600, 3), 200, dtype=np.uint8)
        return img, pbg, pgs

    @staticmethod
    def _enc(wins):
        import numpy as np
        return np.stack([np.stack([np.ones((9, 9)), np.full((9, 9), 2.0)]) for _ in wins])

    def test_objects_vectors_and_masks(self):
        from kidney import gsdet
        img, pbg, pgs = self._maps()
        objs, classes, e, base, clip = emb.embed_slide(img, pbg, pgs, 1.5, 1.5, self._enc, batch=1)
        want_objs, want_classes = gsdet.decode(pbg, pgs, 1.5, 1.5)
        self.assertEqual((objs, classes), (want_objs, want_classes))
        self.assertEqual(len(objs), 2)
        self.assertEqual(sorted(zip([o[6] for o in objs], classes)), [(3600.0, "ns"), (8100.0, "gs")])
        self.assertEqual(clip, [False, False])
        for o, b in zip(objs, base):
            self.assertEqual(b[0] * 2.25, o[6])  # the window mask is the object's own region, B left out
            self.assertEqual(b[1:], [1.0, 1.0, 200.0, 200.0, 200.0, 0.0, 0.0, 0.0, 1.0])
        for v in e:
            self.assertEqual(len(v), 2)
            self.assertAlmostEqual(v[0], 1.0, places=9)
            self.assertAlmostEqual(v[1], 2.0, places=9)
        again = emb.embed_slide(img, pbg, pgs, 1.5, 1.5, self._enc, batch=16)
        self.assertEqual(again, (objs, classes, e, base, clip))

    def test_errors(self):
        import numpy as np
        img, pbg, pgs = self._maps()
        with self.assertRaises(ValueError):
            emb.embed_slide(img, pbg, pgs, 1.5, 1.5, lambda w: np.zeros((len(w) + 1, 2, 9, 9)))
        with self.assertRaises(ValueError):
            emb.embed_slide(img, pbg, pgs, 1.5, 1.5, self._enc, size=300)

    def test_no_objects(self):
        import numpy as np
        img, _, _ = self._maps()
        pbg = np.ones((600, 600), dtype="float32")
        pgs = np.zeros((600, 600), dtype="float32")
        self.assertEqual(emb.embed_slide(img, pbg, pgs, 1.5, 1.5, self._enc), ([], [], [], [], []))


@unittest.skipUnless(HAVE_ALL, "numpy, cv2, tifffile, torch and segmentation_models_pytorch needed")
class TestTorch(unittest.TestCase):
    STATS = None

    def _stats(self):
        import numpy as np
        return [np.array([0.6, 0.5, 0.6], dtype="float32"), np.array([0.2, 0.2, 0.2], dtype="float32")]

    def test_encoder_shape(self):
        import numpy as np
        import torch
        from kidney import gsdet
        torch.manual_seed(0)
        model = gsdet.new_model(3)
        model.eval()
        mean, std = self._stats()
        enc = emb.make_encoder(model, mean, std)
        out = enc([np.full((288, 288, 3), 200, dtype=np.uint8)] * 2)
        self.assertEqual(model.encoder.out_channels[-1], 352)
        self.assertEqual(out.shape, (2, 352, 9, 9))

    def test_run_matches_detect(self):
        import numpy as np
        import tifffile
        import torch
        from kidney import gsdet
        torch.manual_seed(0)
        img = np.full((1024, 1024, 3), 240, dtype=np.uint8)
        img[100:900, 100:900] = (200, 120, 180)
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in")
            os.makedirs(src)
            tifffile.imwrite(os.path.join(src, "a_slide.svs"), img, tile=(256, 256), photometric="rgb",
                             description="Synthetic test slide|MPP = 0.5", metadata=None)
            tifffile.imwrite(os.path.join(src, "b_nompp.svs"), img, tile=(256, 256), photometric="rgb",
                             metadata=None)
            ckpt = os.path.join(d, "gs.pth")
            torch.save({"model": gsdet.new_model(3).state_dict(), "stats": self._stats(), "classes": 3,
                        "steps": 0}, ckpt)
            out = os.path.join(d, "emb.json")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = emb.main(["run", "--in-dir", src, "--model", ckpt, "--out", out, "--threads", "2"])
            with open(out, encoding="utf-8") as f:
                doc = json.load(f)
            det = gsdet.run_detect(src, ckpt)
        self.assertEqual(code, 1)  # b_nompp has no MPP in its header
        self.assertEqual([r["slide"] for r in doc["rows"]], ["a_slide", "b_nompp"])
        a, b = doc["rows"]
        self.assertTrue(a["ok"])
        self.assertFalse(b["ok"])
        self.assertIn("no MPP", b["errors"][0])
        self.assertEqual((a["objects"], a["classes"]), (det["rows"][0]["objects"], det["rows"][0]["classes"]))
        n = len(a["objects"])
        self.assertEqual((len(a["emb"]), len(a["base"]), len(a["clipped"])), (n, n, n))
        self.assertTrue(all(v is None or len(v) == 352 for v in a["emb"]))
        self.assertEqual((doc["emb_dim"], doc["window"], doc["stage"], doc["private"]), (352, 288, -1, True))
        self.assertEqual(json.loads(buf.getvalue())["slides"], 2)


if __name__ == "__main__":
    unittest.main()
