# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_patches. Pixel tests need numpy, tifffile and Pillow and are
skipped without them; the job installs them first."""
import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile

from kidney import kpmp_patches as kp

HAVE_PIXELS = all(importlib.util.find_spec(m) is not None for m in ("numpy", "tifffile", "PIL"))

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
RNS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def _cell(ref, v):
    if isinstance(v, str):
        return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, v)
    return '<c r="%s"><v>%s</v></c>' % (ref, v)


def make_xlsx(path, sheets):
    """Minimal workbook: {sheet name: rows}, header row first."""
    with zipfile.ZipFile(path, "w") as z:
        wb, rels = [], []
        for k, (name, rows) in enumerate(sheets.items(), 1):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (name, k, k))
            rels.append('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml" Type="x"/>' % (k, k))
            body = "".join('<row r="%d">%s</row>' % (i + 1, "".join(_cell("%s%d" % (chr(65 + j), i + 1), v)
                                                                   for j, v in enumerate(r)))
                           for i, r in enumerate(rows))
            z.writestr("xl/worksheets/sheet%d.xml" % k, "<worksheet %s><sheetData>%s</sheetData></worksheet>" % (NS, body))
        z.writestr("xl/workbook.xml", "<workbook %s %s><sheets>%s</sheets></workbook>" % (NS, RNS, "".join(wb)))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
                   '</Relationships>' % "".join(rels))


GLOMS = [["x1", "x2", "y1", "y2", "Area", "Mesangial Area", "Mesangial Fraction"],
         [100, 160, 50, 110, 2800, 1400, 0.5],
         [300, 380, 200, 270, 4300, 2000, 0.4651],
         [500, 600, 300, 390, 7000, 3000, 0.4286],
         [40, 70, 400, 430, 700, 350, 0.5]]
TUBS = [["x1", "x2", "y1", "y2", "Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"],
        [10, 40, 10, 40, 5.0, 20.0, 0.1],
        [200, 230, 100, 130, 0, 18.0, 0.0]]


class TestStdlib(unittest.TestCase):
    def test_read_xlsx_and_objects(self):
        with tempfile.TemporaryDirectory() as d:
            pdir = os.path.join(d, "pkg")
            os.makedirs(pdir)
            make_xlsx(os.path.join(pdir, "features_v2.xlsx"), {"gloms": GLOMS, "tubs": TUBS, "Other": [["a"]]})
            objs = kp.package_objects(pdir)
            self.assertEqual(sorted(objs), ["gloms", "tubs"])
            self.assertEqual(len(objs["gloms"]), 4)
            self.assertEqual(objs["gloms"][0]["box"], (100.0, 160.0, 50.0, 110.0))
            self.assertEqual(objs["gloms"][1]["values"]["Mesangial Fraction"], 0.4651)
            self.assertEqual(objs["tubs"][1]["values"]["Average TBM Thickness"], 0.0)
            self.assertEqual(kp.package_objects(os.path.join(d, "missing")), {})

    def test_sheet_objects_skips_rows_without_box(self):
        rows = [["x1", "x2", "y1", "y2", "Arterial Area"], [1, 2, 3, None, 5], [1, 4, 3, 9, "7.5"]]
        self.assertEqual(kp.sheet_objects(rows), [{"box": (1.0, 4.0, 3.0, 9.0), "values": {"Arterial Area": 7.5}}])
        self.assertEqual(kp.sheet_objects([["a", "b"], [1, 2]]), [])

    def test_orientation(self):
        boxes = [(100, 160, 50, 110), (500, 600, 300, 390)]
        self.assertEqual(kp.orientation(boxes, 640, 480)["orientation"], "xy")
        self.assertEqual(kp.orientation(boxes, 480, 640)["orientation"], "yx")
        both = kp.orientation([(10, 20, 10, 20)], 640, 480)
        self.assertIsNone(both["orientation"])
        self.assertEqual((both["fit_xy"], both["fit_yx"]), (1, 1))
        self.assertIsNone(kp.orientation([], 10, 10)["orientation"])

    def test_rect_window_level(self):
        self.assertEqual(kp.to_rect((1, 2, 3, 4), "xy"), (1, 3, 2, 4))
        self.assertEqual(kp.to_rect((1, 2, 3, 4), "yx"), (3, 1, 4, 2))
        self.assertEqual(kp.crop_window((100, 100, 160, 120), 1000, 1000), (0, 0, 288, 248))
        self.assertEqual(kp.crop_window((500, 500, 900, 600), 1000, 1000), (100, 100, 1000, 1000))
        sizes = [(40000, 30000), (10000, 7500), (2500, 1875)]
        self.assertEqual(kp.pick_level(sizes, (0, 0, 2000, 1000)), (0, 1.0))
        self.assertEqual(kp.pick_level(sizes, (0, 0, 5000, 1000)), (1, 4.0))
        self.assertEqual(kp.pick_level(sizes, (0, 0, 40000, 1000)), (2, 16.0))

    def test_typical(self):
        objs = kp.sheet_objects(GLOMS)
        got = kp.typical(objs, "Area", exclude=(500.0, 600.0, 300.0, 390.0))
        # without the excluded box the areas are 700, 2800, 4300: median 2800
        self.assertEqual([o["values"]["Area"] for o in got], [2800.0, 4300.0])
        self.assertEqual(kp.typical(objs, "Missing", exclude=None), [])

    def test_load_targets(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.json")
            with open(p, "w") as f:
                json.dump({"packages": [{"package": "P", "name": "P.zip"}],
                           "targets": [{"id": "g01", "package": "P", "sheet": "gloms", "box": [1, 2, 3, 4],
                                        "feature": "Area", "direction": "low"}]}, f)
            names, targets = kp.load_targets(p)
            self.assertEqual(names, {"P": "P.zip"})
            self.assertEqual(targets[0]["box"], (1.0, 2.0, 3.0, 4.0))
            with open(p, "w") as f:
                json.dump({"packages": [], "targets": [{"id": "x", "package": "Q", "box": [1, 2, 3, 4]}]}, f)
            with self.assertRaises(ValueError):
                kp.load_targets(p)


def _image(h, w):
    import numpy as np
    yy, xx = np.mgrid[0:h, 0:w]
    return np.stack([(xx * 255 // w), (yy * 255 // h), ((xx + yy) % 256)], axis=-1).astype("uint8")


@unittest.skipUnless(HAVE_PIXELS, "numpy, tifffile and Pillow not installed")
class TestPixels(unittest.TestCase):
    def test_read_region_matches_slicing(self):
        import numpy as np
        import tifffile
        img = _image(480, 640)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.tif")
            tifffile.imwrite(p, img, tile=(128, 128), photometric="rgb")
            with tifffile.TiffFile(p) as tif:
                page = tif.pages[0]
                for l, t, w, h in ((0, 0, 640, 480), (100, 150, 300, 260), (600, 400, 40, 80), (127, 127, 2, 2)):
                    got = kp.read_region(page, l, t, w, h)
                    self.assertTrue(np.array_equal(got, img[t:t + h, l:l + w]), (l, t, w, h))

    def test_read_region_jpeg_tiles(self):
        import numpy as np
        import tifffile
        if importlib.util.find_spec("imagecodecs") is None:
            self.skipTest("imagecodecs not installed")
        img = _image(300, 400)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "j.tif")
            tifffile.imwrite(p, img, tile=(128, 128), photometric="rgb", compression="jpeg")
            with tifffile.TiffFile(p) as tif:
                page = tif.pages[0]
                full = page.asarray()
                got = kp.read_region(page, 50, 60, 300, 200)
                self.assertTrue(np.array_equal(got, full[60:260, 50:350]))
                self.assertLess(float(np.abs(got.astype(int) - img[60:260, 50:350].astype(int)).mean()), 20.0)

    def test_main_offline(self):
        import tifffile
        img = _image(480, 640)
        with tempfile.TemporaryDirectory() as d:
            svs = os.path.join(d, "slide.svs")
            tifffile.imwrite(svs, img, tile=(128, 128), photometric="rgb")
            zbytes = io.BytesIO()
            with zipfile.ZipFile(zbytes, "w") as z:
                z.write(svs, "pkg/S-0000-000001.svs")
                z.writestr("pkg/README.md", "readme")
            data = os.path.join(d, "data")
            pdir = os.path.join(data, kp.CACHE, "P1")
            os.makedirs(pdir)
            make_xlsx(os.path.join(pdir, "S_features_v2.xlsx"), {"gloms": GLOMS, "tubs": TUBS})
            targets = os.path.join(d, "targets.json")
            with open(targets, "w") as f:
                json.dump({"packages": [{"package": "P1", "name": "P1.zip"}],
                           "targets": [{"id": "g01", "package": "P1", "sheet": "gloms", "box": [500, 600, 300, 390],
                                        "feature": "Area", "direction": "high"},
                                       {"id": "g02", "package": "P1", "sheet": "gloms", "box": [1, 2, 3, 4],
                                        "feature": "Area", "direction": "low"}]}, f)
            urls = []

            def get(url):
                urls.append(url)
                return io.BytesIO(zbytes.getvalue())

            out = os.path.join(d, "out")
            res = kp.main(["--targets", targets, "--data-dir", data, "--out-dir", out], get=get, pause=lambda s: None)
            self.assertEqual(urls, ["https://atlas.kpmp.org/api/v1/file/download/P1/P1.zip"])
            rec = res["packages"][0]
            self.assertTrue(rec["ok"], rec)
            self.assertEqual(rec["slide"]["width"], 640)
            self.assertEqual(rec["orientation"]["orientation"], "xy")
            roles = [(c["target"], c["role"]) for c in rec["crops"]]
            self.assertEqual(roles, [("g01", "target"), ("g01", "typical1"), ("g01", "typical2"),
                                     ("g02", "target"), ("g02", "typical1"), ("g02", "typical2")])
            self.assertEqual(rec["crops"][0]["in_workbook"], 1)
            self.assertEqual(rec["crops"][0]["values"]["Area"], 7000.0)
            self.assertEqual(rec["crops"][3]["in_workbook"], 0)
            for c in rec["crops"]:
                self.assertTrue(os.path.exists(os.path.join(out, "patches", c["file"])), c)
            self.assertTrue(os.path.exists(os.path.join(out, "patches", rec["overview"]["file"])))
            self.assertEqual(res["summary"]["targets_in_workbook"], 1)
            self.assertEqual(res["summary"]["orientations"], ["xy"])
            with open(os.path.join(out, "results.json")) as f:
                self.assertEqual(json.load(f)["summary"]["ok"], 1)


if __name__ == "__main__":
    unittest.main()
