# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/kmask.py (KPMP mask reader for stages 3, 3b and 4). Invented sizes and counts only: no
KPMP value appears here. The numpy tests are skipped when numpy is not installed."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from kidney import kmask

OME = ('<?xml version="1.0" encoding="UTF-8"?><!-- comment -->'
       '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"><Image ID="Image:0"><Pixels ID="Pixels:0" '
       'SizeC="4" SizeX="100" SizeY="50"><Channel ID="Channel:0:0" Name="cortex"/>'
       '<Channel ID="Channel:0:1" Name="non-globally-sclerotic glomeruli"/>'
       '<Channel ID="Channel:0:2" Name="Globally-Sclerotic  Glomeruli"/>'
       '<Channel ID="Channel:0:3" Name="tubules"/></Pixels></Image></OME>')

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


class TestChannels(unittest.TestCase):
    def test_names_from_ome(self):
        self.assertEqual(kmask.ome_channel_names(OME), ["cortex", "non-globally-sclerotic glomeruli",
                                                        "Globally-Sclerotic  Glomeruli", "tubules"])
        self.assertEqual(kmask.ome_channel_names(""), [])
        self.assertEqual(kmask.ome_channel_names("<<not xml"), [])

    def test_kinds(self):
        self.assertEqual(kmask.channel_kinds(kmask.ome_channel_names(OME)), {1: "glom", 2: "gs"})

    def test_kinds_refuse(self):
        with self.assertRaises(ValueError):
            kmask.channel_kinds(["cortex", "tubules"])
        with self.assertRaises(ValueError):
            kmask.channel_kinds(["non-globally-sclerotic glomeruli"])
        with self.assertRaises(ValueError):
            kmask.channel_kinds(["non-globally-sclerotic glomeruli", "Non-Globally-Sclerotic Glomeruli",
                                 "globally-sclerotic glomeruli"])


class TestGeometry(unittest.TestCase):
    def test_pick_level(self):
        shapes = [(20000, 50000), (10000, 25000), (5000, 12500), (2500, 6250)]
        self.assertEqual(kmask.pick_level(shapes), 2)
        self.assertEqual(kmask.pick_level(shapes, max_pixels=250_000_000), 1)
        self.assertEqual(kmask.pick_level(shapes, max_pixels=1_000_000_000), 0)
        self.assertEqual(kmask.pick_level(shapes, max_pixels=10), 3)

    def test_mask_mpp(self):
        self.assertEqual(kmask.mask_mpp(0.25, (50000, 20000), (50000, 20000), 12500), 1.0)
        self.assertEqual(kmask.mask_mpp(0.25, [50000, 20000], (50000, 20000), 50000), 0.25)
        self.assertIsNone(kmask.mask_mpp(0.25, (50000, 20000), (50000, 20001), 12500))
        self.assertIsNone(kmask.mask_mpp(None, (50000, 20000), (50000, 20000), 12500))
        self.assertIsNone(kmask.mask_mpp(0.25, (50000, 20000), (50000, 20000), 0))

    def test_y_scale(self):
        self.assertAlmostEqual(kmask.y_scale(2.0, (50000, 20000), (12500, 5000)), 2.0)
        self.assertAlmostEqual(kmask.y_scale(2.0, (50000, 20000), (12500, 4000)), 2.5)
        self.assertIsNone(kmask.y_scale(None, (50000, 20000), (12500, 5000)))


class TestObjects(unittest.TestCase):
    def test_add_counts(self):
        self.assertEqual(kmask.add_counts({}, [(0, 5), (3, 10), (3, 2), (7, 0)]), {3: 12})
        self.assertEqual(kmask.add_counts({3: 1}, [(3, 2), (4, 1)]), {3: 3, 4: 1})

    def test_objects(self):
        px = {"gs": {2: 50}, "glom": {5: 10, 1: 20}}
        self.assertEqual(kmask.objects(px), [("glom", 20), ("glom", 10), ("gs", 50)])
        self.assertEqual(kmask.objects({}), [])

    def test_slide_k_with_floor(self):
        px = {"glom": {1: 2500, 2: 1999, 3: 2000}, "gs": {9: 3000}}
        k = kmask.slide_k(px, 1.0)
        self.assertEqual(k, {"k": 3, "k_gs": 1, "floor_applied": True,
                             "k_areas_um2": [2000.0, 2500.0, 3000.0],
                             "k_areas_by_kind": {"glom": [2000.0, 2500.0], "gs": [3000.0]}})
        k = kmask.slide_k({"glom": {1: 8000}, "gs": {}}, 0.5)
        self.assertEqual((k["k"], k["k_areas_um2"]), (1, [2000.0]))
        self.assertEqual(k["k_areas_by_kind"], {"glom": [2000.0], "gs": []})

    def test_slide_k_without_mpp(self):
        px = {"glom": {1: 2500, 2: 1999}, "gs": {9: 3000}}
        self.assertEqual(kmask.slide_k(px, None), {"k": 3, "k_gs": 1, "floor_applied": False, "k_areas_um2": None,
                                                   "k_areas_by_kind": {"glom": None, "gs": None}})

    def test_sheet_check(self):
        px = {"glom": {1: 5, 2: 6}, "gs": {}}
        self.assertTrue(kmask.sheet_check(px, {"gloms": 2, "s_gloms": 0}))
        self.assertFalse(kmask.sheet_check(px, {"gloms": 3, "s_gloms": 0}))
        self.assertFalse(kmask.sheet_check(px, {"gloms": 2}))
        self.assertIsNone(kmask.sheet_check(px, None))


class TestObjectStats(unittest.TestCase):
    STATS = {"glom": {5: [2, 1, 0, 0, 0, 1, 0], 3: [3, 3, 2, 0, 0, 2, 1]}, "gs": {7: [4, 6, 16, 0, 4, 3, 4]}}

    def test_add_stats(self):
        rows = [(0, 5, 0, 0, 0, 0, 0, 0), (3, 2, 1, 4, 0, 2, 1, 2), (3, 1, 5, 3, 5, 3, 5, 3), (4, 0, 0, 0, 0, 0, 0, 0)]
        self.assertEqual(kmask.add_stats({}, rows), {3: [3, 6, 7, 0, 2, 5, 3]})

    def test_counts_from_stats(self):
        self.assertEqual(kmask.counts_from_stats(self.STATS), {"glom": {5: 2, 3: 3}, "gs": {7: 4}})

    def test_object_record(self):
        self.assertEqual(kmask.object_record([3, 3, 2, 0, 0, 2, 1], 2.0, 2.0), [3.0, 2.3, 0.0, 0.0, 6.0, 4.0, 12.0])
        self.assertEqual(kmask.object_record([3, 3, 2, 0, 0, 2, 1], 2.0, 4.0), [3.0, 4.7, 0.0, 0.0, 6.0, 8.0, 12.0])

    def test_k_objects(self):
        got = kmask.k_objects(self.STATS, 2.0, 2.0, min_area_um2=10)
        self.assertEqual(got, {"glom": [[3.0, 2.3, 0.0, 0.0, 6.0, 4.0, 12.0]],
                               "gs": [[4.0, 9.0, 0.0, 8.0, 8.0, 10.0, 16.0]]})
        self.assertIsNone(kmask.k_objects(self.STATS, None, None))

    def test_k_objects_keep_what_count_k_keeps(self):
        stats = {"glom": {1: [2500, 0, 0, 0, 0, 0, 0], 2: [1999, 0, 0, 0, 0, 0, 0], 4: [2000, 0, 0, 0, 0, 0, 0]},
                 "gs": {9: [3000, 0, 0, 0, 0, 0, 0]}}
        objs = kmask.k_objects(stats, 1.0, 1.0)
        k = kmask.slide_k(kmask.counts_from_stats(stats), 1.0)
        self.assertEqual(len(objs["glom"]) + len(objs["gs"]), k["k"])
        self.assertEqual(len(objs["gs"]), k["k_gs"])
        self.assertEqual(sorted(o[6] for o in objs["glom"]), k["k_areas_by_kind"]["glom"])


class TestFolderAndOutput(unittest.TestCase):
    def test_slide_names(self):
        with tempfile.TemporaryDirectory() as d:
            for f in ("slide03.ome.tif", "slide01.OME.TIF", "slide01.svs", "slide01_features.xlsx", "x.tif"):
                open(os.path.join(d, f), "w").close()
            self.assertEqual(kmask.slide_names(d), ["slide01", "slide03"])
            self.assertEqual(kmask.slide_names(d, {"slide03"}), ["slide03"])

    def test_aggregate_names_nothing(self):
        diag = {"slide01": {"ok": True, "mask_mpp": 1.0, "sheet_match": True},
                "slide03": {"ok": True, "mask_mpp": None, "sheet_match": None},
                "slide04": {"ok": True, "mask_mpp": 1.0, "sheet_match": False},
                "slide05": {"ok": False, "errors": ["x"]}}
        agg = kmask.aggregate(diag)
        self.assertEqual(agg, {"code_version": kmask.CODE_VERSION, "slides": 4, "ok": 3, "mpp_linked": 2,
                               "sheet_checked": 2, "sheet_match": 1})
        text = json.dumps(agg)
        for name in diag:
            self.assertNotIn(name, text)

    def test_main_bad_mask_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "slide01.ome.tif"), "w").close()
            out, diag = os.path.join(d, "k.json"), os.path.join(d, "diag.json")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = kmask.main(["--masks", d, "--wsi", d, "--out", out, "--diag", diag])
            self.assertEqual(code, 1)
            with open(out, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {})
            with open(diag, encoding="utf-8") as f:
                rec = json.load(f)["slide01"]
            self.assertFalse(rec["ok"])
            self.assertTrue(rec["errors"])
            printed = json.loads(buf.getvalue())
            self.assertEqual((printed["slides"], printed["ok"]), (1, 0))
            self.assertNotIn("slide01", buf.getvalue())

    def test_main_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = kmask.main(["--masks", d, "--wsi", d, "--out", os.path.join(d, "k.json")])
            self.assertEqual(code, 1)


@unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
class TestPlanes(unittest.TestCase):
    def plane(self):
        import numpy as np
        a = np.zeros((5, 4), dtype=np.uint16)
        a[0, 0] = 3
        a[1, 1:3] = 3
        a[4, :] = 7
        return a

    def test_counts_in_strips(self):
        a = self.plane()
        self.assertEqual(kmask.plane_counts(a, strip_rows=2), {3: 3, 7: 4})
        self.assertEqual(kmask.plane_counts(a, strip_rows=100), {3: 3, 7: 4})

    def test_stats_in_strips(self):
        import numpy as np
        a = self.plane()
        want = {3: [3, 3, 2, 0, 0, 2, 1], 7: [4, 6, 16, 0, 4, 3, 4]}
        self.assertEqual(kmask.plane_stats(a, strip_rows=2), want)
        self.assertEqual(kmask.plane_stats(a, strip_rows=1), want)
        self.assertEqual(kmask.plane_stats(a, strip_rows=100), want)
        self.assertEqual({lab: st[0] for lab, st in kmask.plane_stats(a).items()}, kmask.plane_counts(a))
        self.assertEqual(kmask.plane_stats(np.zeros((3, 3), dtype=np.uint8)), {})

    def test_refuses_float(self):
        import numpy as np
        with self.assertRaises(ValueError):
            kmask.plane_counts(np.zeros((2, 2), dtype=np.float32))
        with self.assertRaises(ValueError):
            kmask.plane_stats(np.zeros((2, 2), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
