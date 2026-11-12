# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/annot.py (standard library only; invented slide names, no KPMP data)."""
import contextlib
import csv
import io
import json
import os
import shutil
import tempfile
import unittest

from kidney import annot

GLOM_FIELDS = ["slide", "glomerulus", "class", "cx_um", "cy_um", "x0_um", "y0_um", "x1_um", "y1_um", "area_um2"]
SLIDE_FIELDS = ["slide", "detect_ok", "scan_mpp"]


def grow(slide, n, cls, x0, y0, x1, y1):
    return {"slide": slide, "glomerulus": str(n), "class": cls, "cx_um": "", "cy_um": "", "x0_um": x0,
            "y0_um": y0, "x1_um": x1, "y1_um": y1, "area_um2": "500.0"}


class TestParts(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(annot.to_float("1.5"), 1.5)
        self.assertEqual(annot.to_float(2), 2.0)
        for bad in (None, "", "abc", "nan", "inf", "-inf"):
            self.assertIsNone(annot.to_float(bad), bad)

    def test_is_true(self):
        for v in ("True", "true", " TRUE ", "1", "yes", True):
            self.assertTrue(annot.is_true(v), v)
        for v in ("False", "", "0", None, False):
            self.assertFalse(annot.is_true(v), v)

    def test_safe_name(self):
        self.assertEqual(annot.safe_name("SLIDE-1_a.b"), "SLIDE-1_a.b")
        self.assertEqual(annot.safe_name("SL A/B"), "SL_A_B")
        self.assertEqual(annot.safe_name(""), "_")

    def test_box_ring_closed(self):
        ring = annot.box_ring(1, 2, 3, 4)
        self.assertEqual(ring, [[1, 2], [3, 2], [3, 4], [1, 4], [1, 2]])
        self.assertEqual(ring[0], ring[-1])

    def test_feature(self):
        f = annot.feature(grow("SLIDEA", 3, "globally_sclerotic", "100.0", "50.0", "125.5", "75.25"), 0.25)
        self.assertEqual(f["type"], "Feature")
        self.assertEqual(f["geometry"], {"type": "Polygon", "coordinates": [
            [[400.0, 200.0], [502.0, 200.0], [502.0, 301.0], [400.0, 301.0], [400.0, 200.0]]]})
        self.assertEqual(f["properties"], {"objectType": "annotation", "name": "glomerulus 3",
                                           "classification": {"name": "globally_sclerotic",
                                                              "color": [214, 39, 40]}})

    def test_feature_classes_and_type(self):
        f = annot.feature(grow("SLIDEA", 1, "non_globally_sclerotic", "10", "10", "20", "20"), 1.0, "detection")
        self.assertEqual(f["properties"]["objectType"], "detection")
        self.assertEqual(f["properties"]["classification"]["color"], [44, 160, 44])
        f = annot.feature(grow("SLIDEA", 1, "OTHERCLASS", "10", "10", "20", "20"), 1.0)
        self.assertEqual(f["properties"]["classification"], {"name": "OTHERCLASS", "color": [127, 127, 127]})
        f = annot.feature(grow("SLIDEA", 1, "", "10", "10", "20", "20"), 1.0)
        self.assertEqual(f["properties"]["classification"]["name"], "unclassified")

    def test_feature_colors_are_copies(self):
        f = annot.feature(grow("SLIDEA", 1, "globally_sclerotic", "10", "10", "20", "20"), 1.0)
        f["properties"]["classification"]["color"][0] = 0
        self.assertEqual(annot.COLORS["globally_sclerotic"], [214, 39, 40])

    def test_feature_bad_rows(self):
        self.assertIsNone(annot.feature(grow("SLIDEA", 1, "x", "", "10", "20", "20"), 1.0))
        self.assertIsNone(annot.feature(grow("SLIDEA", 1, "x", "20", "10", "20", "20"), 1.0))
        self.assertIsNone(annot.feature(grow("SLIDEA", 1, "x", "10", "30", "20", "20"), 1.0))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.slides = [{"slide": "SLIDEA", "detect_ok": "True", "scan_mpp": "0.5"},
                       {"slide": "SLIDEB", "detect_ok": "True", "scan_mpp": ""},
                       {"slide": "SLIDEC", "detect_ok": "False", "scan_mpp": "0.5"},
                       {"slide": "SLIDED", "detect_ok": "True", "scan_mpp": "0.25"}]
        self.gloms = [grow("SLIDEA", 1, "globally_sclerotic", "10.0", "20.0", "30.0", "40.0"),
                      grow("SLIDEA", 2, "non_globally_sclerotic", "10.0", "20.0", "", "40.0"),
                      grow("SLIDEB", 1, "globally_sclerotic", "10.0", "20.0", "30.0", "40.0"),
                      grow("SLIDEZ", 1, "globally_sclerotic", "10.0", "20.0", "30.0", "40.0")]

    def test_build(self):
        docs, rep = annot.build(self.gloms, self.slides)
        self.assertEqual(sorted(docs), ["SLIDEA.geojson", "SLIDED.geojson"])
        a = docs["SLIDEA.geojson"]
        self.assertEqual(a["type"], "FeatureCollection")
        self.assertEqual(len(a["features"]), 1)
        self.assertEqual(a["features"][0]["geometry"]["coordinates"],
                         [[[20.0, 40.0], [60.0, 40.0], [60.0, 80.0], [20.0, 80.0], [20.0, 40.0]]])
        self.assertEqual(docs["SLIDED.geojson"], {"type": "FeatureCollection", "features": []})
        self.assertEqual([s["slide"] for s in rep["skipped"]], ["SLIDEB", "SLIDEC", "SLIDEZ"])
        self.assertEqual([s["reason"] for s in rep["skipped"]],
                         ["no scan_mpp (QC skipped or no MPP in the header)", "detection failed",
                          "not in slides.csv"])
        self.assertEqual((rep["files"], rep["features"], rep["dropped_rows"]), (2, 1, 1))
        self.assertEqual(rep["annot"], annot.CODE_VERSION)
        self.assertEqual(rep["object_type"], "annotation")

    def test_zero_mpp_skipped(self):
        docs, rep = annot.build([], [{"slide": "SLIDEA", "detect_ok": "True", "scan_mpp": "0"}])
        self.assertEqual(docs, {})
        self.assertEqual([s["slide"] for s in rep["skipped"]], ["SLIDEA"])

    def test_name_clash(self):
        slides = [{"slide": "SL A", "detect_ok": "True", "scan_mpp": "1"},
                  {"slide": "SL_A", "detect_ok": "True", "scan_mpp": "1"}]
        docs, rep = annot.build([], slides)
        self.assertEqual(list(docs), ["SL_A.geojson"])
        self.assertEqual(rep["skipped"], [{"slide": "SL_A", "reason": "file name clash with slide SL A"}])

    def test_order_kept(self):
        gl = [grow("SLIDEA", 2, "globally_sclerotic", "50", "50", "60", "60"),
              grow("SLIDEA", 1, "globally_sclerotic", "10", "10", "20", "20")]
        docs, _ = annot.build(gl, [{"slide": "SLIDEA", "detect_ok": "True", "scan_mpp": "1"}])
        names = [f["properties"]["name"] for f in docs["SLIDEA.geojson"]["features"]]
        self.assertEqual(names, ["glomerulus 2", "glomerulus 1"])


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


class TestMain(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="annottest")
        self.g = os.path.join(self.d, "glomeruli.csv")
        self.s = os.path.join(self.d, "slides.csv")
        self.out = os.path.join(self.d, "out")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = annot.main(argv)
        return rc, buf.getvalue()

    def test_main_ok(self):
        write_csv(self.g, GLOM_FIELDS, [grow("SLIDEA", 1, "globally_sclerotic", "10.0", "20.0", "30.0", "40.0")])
        write_csv(self.s, SLIDE_FIELDS, [{"slide": "SLIDEA", "detect_ok": True, "scan_mpp": 0.5}])
        rc, out = self.run_main(["--glomeruli", self.g, "--slides", self.s, "--out-dir", self.out,
                                 "--detections"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["features"], 1)
        with open(os.path.join(self.out, "SLIDEA.geojson"), encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(doc["features"][0]["properties"]["objectType"], "detection")
        self.assertEqual(doc["features"][0]["geometry"]["coordinates"][0][2], [60.0, 80.0])
        with open(os.path.join(self.out, annot.REPORT), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["files"], 1)

    def test_main_skipped_is_1(self):
        write_csv(self.g, GLOM_FIELDS, [])
        write_csv(self.s, SLIDE_FIELDS, [{"slide": "SLIDEA", "detect_ok": False, "scan_mpp": 0.5}])
        rc, _ = self.run_main(["--glomeruli", self.g, "--slides", self.s, "--out-dir", self.out])
        self.assertEqual(rc, 1)
        self.assertEqual(os.listdir(self.out), [annot.REPORT])

    def test_main_missing_input(self):
        write_csv(self.s, SLIDE_FIELDS, [])
        rc, out = self.run_main(["--glomeruli", self.g, "--slides", self.s, "--out-dir", self.out])
        self.assertEqual(rc, 2)
        self.assertIn("missing input file", out)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
