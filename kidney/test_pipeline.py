# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/pipeline.py. Invented records, synthetic images and random weights only: no KPMP value,
id or image appears here. The standard-library tests always run; the end-to-end test needs numpy, OpenCV, tifffile,
torch and segmentation-models-pytorch and runs in the compute job."""
import contextlib
import csv
import importlib.util
import io
import json
import os
import tempfile
import unittest

from kidney import pipeline as pl


def _have(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


HAVE_ALL = _have("numpy", "cv2", "tifffile", "torch", "segmentation_models_pytorch")

DET = [
    {"slide": "s1", "ok": True, "objects": [[10.0, 20.0, 5.0, 15.0, 15.0, 25.0, 2500.0],
                                            [100.0, 200.0, 90.0, 190.0, 110.0, 210.0, 3000.0]],
     "classes": ["ns", "gs"], "errors": [], "seconds": 3.0},
    {"slide": "s2", "ok": False, "errors": ["ValueError('no MPP in the slide header')"], "seconds": 0.5},
    {"slide": "s3", "ok": True, "objects": [], "classes": [], "errors": [], "seconds": 1.0},
]
QC = [
    {"slide": "s1", "ok": True, "mpp": 0.252, "tissue_fraction": 0.4, "pieces": 2, "green_ink_fraction": 0.0,
     "blur_median": 12.5, "seconds": 2.0, "errors": []},
    {"slide": "s2", "ok": True, "mpp": None, "tissue_fraction": 0.3, "pieces": 1, "green_ink_fraction": 0.001,
     "blur_median": 8.0, "seconds": 1.0, "errors": []},
]
NAMES = ["s1", "s2", "s3", "s4"]


class TestStdlib(unittest.TestCase):
    def test_list_slides(self):
        with tempfile.TemporaryDirectory() as d:
            for f in ("b.svs", "A.SVS", "notes.txt"):
                with open(os.path.join(d, f), "w") as h:
                    h.write("x")
            os.makedirs(os.path.join(d, "c.svs"))
            self.assertEqual(pl.list_slides(d), ["A.SVS", "b.svs"])

    def test_median(self):
        self.assertIsNone(pl.median([]))
        self.assertEqual(pl.median([3, 1, 2]), 2)
        self.assertEqual(pl.median([4, 1, 3, 2]), 2.5)

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.bin")
            with open(p, "wb") as h:
                h.write(b"abc")
            want = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            self.assertEqual(pl.sha256_file(p), want)
            self.assertEqual(pl.sha256_file(p, chunk=2), want)

    def test_object_rows(self):
        rows = pl.object_rows(DET)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"slide": "s1", "glomerulus": 1, "class": "non_globally_sclerotic", "cx_um": 10.0,
                                   "cy_um": 20.0, "x0_um": 5.0, "y0_um": 15.0, "x1_um": 15.0, "y1_um": 25.0,
                                   "area_um2": 2500.0})
        self.assertEqual((rows[1]["glomerulus"], rows[1]["class"], rows[1]["area_um2"]),
                         (2, "globally_sclerotic", 3000.0))

    def test_slide_rows(self):
        rows = pl.slide_rows(NAMES, QC, DET)
        self.assertEqual([r["slide"] for r in rows], NAMES)
        s1, s2, s3, s4 = rows
        self.assertEqual((s1["qc_ok"], s1["detect_ok"], s1["scan_mpp"], s1["pieces"]), (True, True, 0.252, 2))
        self.assertEqual((s1["glomeruli"], s1["globally_sclerotic"], s1["non_globally_sclerotic"]), (2, 1, 1))
        self.assertEqual((s1["gs_share"], s1["median_area_um2"], s1["seconds"], s1["errors"]), (0.5, 2750.0, 5.0, ""))
        self.assertEqual((s2["qc_ok"], s2["detect_ok"], s2["glomeruli"], s2["gs_share"]), (True, False, None, None))
        self.assertEqual((s2["median_area_um2"], s2["seconds"]), (None, 1.5))
        self.assertEqual(s2["errors"], "detect: ValueError('no MPP in the slide header')")
        self.assertEqual((s3["qc_ok"], s3["detect_ok"], s3["glomeruli"], s3["globally_sclerotic"]), (False, True, 0, 0))
        self.assertEqual((s3["gs_share"], s3["median_area_um2"], s3["seconds"]), (None, None, 1.0))
        self.assertEqual(s3["errors"], "qc: not run")
        self.assertEqual((s4["detect_ok"], s4["glomeruli"], s4["seconds"]), (False, None, 0.0))
        self.assertEqual(s4["errors"], "qc: not run; detect: not run")
        no_qc = pl.slide_rows(NAMES, [], DET, qc_ran=False)
        self.assertEqual([r["errors"] for r in no_qc],
                         ["", "detect: ValueError('no MPP in the slide header')", "", "detect: not run"])
        self.assertEqual([r["qc_ok"] for r in no_qc], [False, False, False, False])

    def test_totals(self):
        t = pl.totals(pl.slide_rows(NAMES, QC, DET))
        self.assertEqual(t, {"slides": 4, "qc_ok": 2, "detect_ok": 2, "glomeruli": 2, "globally_sclerotic": 1,
                             "non_globally_sclerotic": 1, "gs_share": 0.5})
        self.assertEqual(pl.totals([]), {"slides": 0, "qc_ok": 0, "detect_ok": 0, "glomeruli": 0,
                                         "globally_sclerotic": 0, "non_globally_sclerotic": 0, "gs_share": None})

    def test_write_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "slides.csv")
            pl.write_csv(p, pl.SLIDE_FIELDS, pl.slide_rows(NAMES, QC, DET))
            with open(p, encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4)
        self.assertEqual(list(rows[0].keys()), pl.SLIDE_FIELDS)
        self.assertEqual((rows[0]["qc_ok"], rows[0]["gs_share"], rows[0]["median_area_um2"]), ("True", "0.5", "2750.0"))
        self.assertEqual((rows[1]["glomeruli"], rows[1]["scan_mpp"]), ("", ""))

    def test_annotations(self):
        objs, rows = pl.object_rows(DET), pl.slide_rows(NAMES, QC, DET)
        with tempfile.TemporaryDirectory() as d:
            summary = pl.annotations(objs, rows, d)
            adir = os.path.join(d, pl.ANNOT_DIR)
            names = sorted(os.listdir(adir))
            with open(os.path.join(adir, "s1.geojson"), encoding="utf-8") as f:
                doc = json.load(f)
            with open(os.path.join(adir, "annot-report.json"), encoding="utf-8") as f:
                report = json.load(f)
            det_summary = pl.annotations(objs, rows, os.path.join(d, "det"), "detection")
            with open(os.path.join(d, "det", pl.ANNOT_DIR, "s1.geojson"), encoding="utf-8") as f:
                det_doc = json.load(f)
        self.assertEqual(names, ["annot-report.json", "s1.geojson"])
        self.assertEqual((summary["dir"], summary["object_type"], summary["files"], summary["features"]),
                         ("annotations", "annotation", 1, 2))
        self.assertEqual((summary["dropped_rows"], summary["skipped_slides"]), (0, 3))
        self.assertEqual(summary["annot"], report["annot"])
        self.assertEqual([(s["slide"], s["reason"]) for s in report["skipped"]],
                         [("s2", "detection failed"), ("s3", "no scan_mpp (QC skipped or no MPP in the header)"),
                          ("s4", "detection failed")])
        self.assertEqual(doc["type"], "FeatureCollection")
        f1, f2 = doc["features"]
        self.assertEqual(f1["geometry"]["coordinates"],
                         [[[19.8, 59.5], [59.5, 59.5], [59.5, 99.2], [19.8, 99.2], [19.8, 59.5]]])
        self.assertEqual(f1["properties"], {"objectType": "annotation", "name": "glomerulus 1",
                                            "classification": {"name": "non_globally_sclerotic",
                                                               "color": [44, 160, 44]}})
        self.assertEqual(f2["geometry"]["coordinates"][0][0], [357.1, 754.0])
        self.assertEqual(f2["geometry"]["coordinates"][0][2], [436.5, 833.3])
        self.assertEqual((f2["properties"]["name"], f2["properties"]["classification"]["name"]),
                         ("glomerulus 2", "globally_sclerotic"))
        self.assertEqual((det_summary["object_type"], det_summary["files"]), ("detection", 1))
        self.assertEqual(det_doc["features"][0]["properties"]["objectType"], "detection")

    def test_main_errors_and_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            model = os.path.join(d, "m.pth")
            with open(model, "wb") as h:
                h.write(b"not a model")
            src, out = os.path.join(d, "in"), os.path.join(d, "out")
            os.makedirs(src)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(pl.main(["--in-dir", os.path.join(d, "missing"), "--out-dir", out,
                                          "--model", model]), 2)
                self.assertEqual(pl.main(["--in-dir", src, "--out-dir", out,
                                          "--model", os.path.join(d, "missing.pth")]), 2)
                self.assertFalse(os.path.exists(out))
                self.assertEqual(pl.main(["--in-dir", src, "--out-dir", out, "--model", model]), 2)
            with open(os.path.join(out, "manifest.json"), encoding="utf-8") as f:
                man = json.load(f)
            with open(os.path.join(out, "inputs.csv"), encoding="utf-8", newline="") as f:
                lines = f.read().splitlines()
            annot_dir_made = os.path.exists(os.path.join(out, pl.ANNOT_DIR))
        self.assertEqual(man["slides"], 0)
        self.assertEqual(man["error"], "no .svs file in the input folder")
        self.assertEqual(lines, ["file,bytes,sha256"])
        self.assertFalse(annot_dir_made)


@unittest.skipUnless(HAVE_ALL, "numpy, cv2, tifffile, torch and segmentation_models_pytorch needed")
class TestEndToEnd(unittest.TestCase):
    def test_synthetic_folder(self):
        import numpy as np
        import tifffile
        import torch
        from kidney import annot, gsdet
        torch.manual_seed(0)
        img = np.full((1024, 1024, 3), 240, dtype=np.uint8)
        img[100:900, 100:900] = (200, 120, 180)
        stats = [np.array([0.6, 0.5, 0.6], dtype="float32"), np.array([0.2, 0.2, 0.2], dtype="float32")]
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "in"), os.path.join(d, "out")
            os.makedirs(src)
            tifffile.imwrite(os.path.join(src, "a_slide.svs"), img, tile=(256, 256), photometric="rgb",
                             description="Synthetic test slide|MPP = 0.5", metadata=None)
            tifffile.imwrite(os.path.join(src, "b_nompp.svs"), img, tile=(256, 256), photometric="rgb",
                             metadata=None)
            with open(os.path.join(src, "readme.txt"), "w") as h:
                h.write("not a slide")
            ckpt = os.path.join(d, "gs.pth")
            torch.save({"model": gsdet.new_model(3).state_dict(), "stats": stats, "classes": 3, "steps": 0}, ckpt)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = pl.main(["--in-dir", src, "--out-dir", out, "--model", ckpt, "--threads", "2"])
            with open(os.path.join(out, "slides.csv"), encoding="utf-8", newline="") as f:
                slides = list(csv.DictReader(f))
            with open(os.path.join(out, "glomeruli.csv"), encoding="utf-8", newline="") as f:
                gloms = list(csv.DictReader(f))
            with open(os.path.join(out, "inputs.csv"), encoding="utf-8", newline="") as f:
                inputs = list(csv.DictReader(f))
            with open(os.path.join(out, "manifest.json"), encoding="utf-8") as f:
                man = json.load(f)
            with open(os.path.join(out, "detections.json"), encoding="utf-8") as f:
                det = json.load(f)
            with open(os.path.join(out, pl.ANNOT_DIR, "a_slide.geojson"), encoding="utf-8") as f:
                ann = json.load(f)
            ann_files = sorted(os.listdir(os.path.join(out, pl.ANNOT_DIR)))
            want_sha = pl.sha256_file(ckpt)
            self.assertTrue(os.path.isfile(os.path.join(out, "qc.json")))
        self.assertEqual(code, 1)  # b_nompp has no MPP in its header, so its detection fails
        self.assertEqual([s["slide"] for s in slides], ["a_slide", "b_nompp"])
        a, b = slides
        self.assertEqual((a["qc_ok"], a["detect_ok"], a["scan_mpp"]), ("True", "True", "0.5"))
        self.assertEqual(a["errors"], "")
        self.assertEqual(int(a["glomeruli"]), len(gloms))
        self.assertEqual(int(a["globally_sclerotic"]) + int(a["non_globally_sclerotic"]), len(gloms))
        self.assertTrue(all(g["slide"] == "a_slide" for g in gloms))
        self.assertTrue(all(float(g["area_um2"]) >= 2000.0 for g in gloms))
        self.assertEqual((b["qc_ok"], b["detect_ok"], b["glomeruli"]), ("True", "False", ""))
        self.assertIn("no MPP", b["errors"])
        self.assertEqual([i["file"] for i in inputs], ["a_slide.svs", "b_nompp.svs"])
        self.assertTrue(all(len(i["sha256"]) == 64 for i in inputs))
        self.assertEqual(man["model"], {"file": "gs.pth", "sha256": want_sha, "train_steps": 0})
        self.assertEqual((man["totals"]["slides"], man["totals"]["detect_ok"]), (2, 1))
        self.assertEqual(man["code_versions"]["pipeline"], pl.CODE_VERSION)
        self.assertEqual(man["code_versions"]["annot"], annot.CODE_VERSION)
        self.assertEqual(det["code_version"], gsdet.CODE_VERSION)
        self.assertEqual(det["rows"][0]["tiles_used"], 1)
        self.assertEqual(ann_files, ["a_slide.geojson", "annot-report.json"])
        self.assertEqual(len(ann["features"]) + man["annotations"]["dropped_rows"], len(gloms))
        self.assertEqual((man["annotations"]["files"], man["annotations"]["skipped_slides"]), (1, 1))
        self.assertEqual(man["settings"]["annotations"], "annotation")


if __name__ == "__main__":
    unittest.main()
