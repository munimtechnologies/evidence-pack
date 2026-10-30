# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_triage. The render test needs numpy, tifffile and Pillow and is
skipped without them; the job installs them first."""
import csv
import importlib.util
import io
import json
import os
import random
import tempfile
import unittest
import zipfile

from kidney import kpmp_triage as kt

HAVE_PIXELS = all(importlib.util.find_spec(m) is not None for m in ("numpy", "tifffile", "PIL"))

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
RNS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
HEADER = ["Access", "Platform", "Data Format", "Data Category", "Size", "File Name", "Internal Package ID",
          "Experimental Strategy", "Workflow Type", "Participant ID", "DOIs"]
SEG = "Segmentation Masks & Pathomics Vectors"


def _cell(ref, v):
    if v is None:
        return ""
    if isinstance(v, str):
        return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, v)
    return '<c r="%s"><v>%s</v></c>' % (ref, v)


def xlsx_bytes(sheets):
    """Minimal workbook: {sheet name: rows}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
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
    return buf.getvalue()


def write_list(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(HEADER)
        for access, size, name, package, strategy, pid in rows:
            w.writerow([access, "", "tif xml xlsx svs md", "Pathology", size, name, package, strategy, "", pid, ""])


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


TUBS = [["Tubule features"],
        ["x1", "x2", "y1", "y2", "Average TBM Thickness", "Luminal Fraction"],
        [0, 10, 0, 10, "0", 0.1],
        [0, 20, 0, 10, 2.5, 0.2],
        [0, None, 0, 10, 1.0, 0.1],
        [5, 15, 5, 25, None, 0.3],
        [1, 2, 3, 4, "-1", 0]]


def box(w, h):
    return (0.0, float(w), 0.0, float(h))


class TestStdlib(unittest.TestCase):
    def test_parse_size(self):
        self.assertEqual(kt.parse_size("128 MB"), 128e6)
        self.assertAlmostEqual(kt.parse_size("1.2 GB"), 1.2e9)
        self.assertEqual(kt.parse_size(""), 0.0)
        self.assertEqual(kt.parse_size("big"), 0.0)

    def test_load_v2_packages(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "list.csv")
            write_list(p, [("open", "1 MB", "a_S-1_Seg_Masks_Features.zip", "P1", SEG, "30-1"),
                           ("open", "2 MB", "b_S-2_Seg_Masks_Features_v2.zip", "P2", SEG, "30-2"),
                           ("controlled", "2 MB", "c_S-3_Seg_Masks_Features_v2.zip", "P3", SEG, "30-3"),
                           ("open", "2 MB", "d_S-4_v2.zip", "P4", "Other", "30-4")])
            got = kt.load_v2_packages(p)
            self.assertEqual(got, [{"package": "P2", "name": "b_S-2_Seg_Masks_Features_v2.zip", "listed": "2 MB",
                                    "participants": ["30-2"]}])

    def test_tubule_rows(self):
        got = kt.tubule_rows({"gloms": [["x1"], [1]], "Tubs ": TUBS})
        self.assertEqual(got, [(0.0, (0.0, 10.0, 0.0, 10.0)), (2.5, (0.0, 20.0, 0.0, 10.0)),
                               (-1.0, (1.0, 2.0, 3.0, 4.0))])
        self.assertEqual(kt.tubule_rows({"tubs": [["x1", "x2", "y1", "y2"], [1, 2, 3, 4]]}), [])
        self.assertEqual(kt.tubule_rows({}), [])

    def test_workbook_rows(self):
        with tempfile.TemporaryDirectory() as d:
            z1 = os.path.join(d, "one.zip")
            with zipfile.ZipFile(z1, "w") as z:
                z.writestr("pkg/S_features_v2.xlsx", xlsx_bytes({"tubs": TUBS}))
                z.writestr("pkg/README.md", "readme")
            self.assertEqual(len(kt.workbook_rows(z1, d)), 3)
            z2 = os.path.join(d, "two.zip")
            with zipfile.ZipFile(z2, "w") as z:
                z.writestr("a.xlsx", xlsx_bytes({"tubs": TUBS}))
                z.writestr("b.xlsx", xlsx_bytes({"tubs": TUBS}))
            self.assertIsNone(kt.workbook_rows(z2, d))
            self.assertFalse(os.path.exists(os.path.join(d, "book.xlsx")))

    def test_pick_pairs(self):
        # zero areas 100, 400, 900; measured 110, 380, 1000, 50. Each zero's nearest (log scale) is
        # distinct, so the result does not depend on the random draw order.
        rows = [(0.0, box(10, 10)), (-0.5, box(20, 20)), (0.0, box(30, 30)),
                (3.0, box(11, 10)), (2.0, box(19, 20)), (4.0, box(25, 40)), (1.0, box(5, 10))]
        pairs = kt.pick_pairs(rows, random.Random(1), n=3, min_zero=3, min_measured=4)
        got = sorted((kt.area(p["zero"][1]), kt.area(p["measured"][1])) for p in pairs)
        self.assertEqual(got, [(100.0, 110.0), (400.0, 380.0), (900.0, 1000.0)])
        ratios = sorted(round(p["area_ratio"], 4) for p in pairs)
        self.assertEqual(ratios, [0.95, 1.1, 1.1111])
        self.assertIsNone(kt.pick_pairs(rows, random.Random(1), n=3, min_zero=4, min_measured=4))
        self.assertIsNone(kt.pick_pairs(rows, random.Random(1), n=3, min_zero=3, min_measured=5))

    def test_sign_p(self):
        self.assertEqual(kt.sign_p(3, 3), 0.125)
        self.assertEqual(kt.sign_p(0, 4), 1.0)
        self.assertEqual(kt.sign_p(9, 10), 11 / 1024)
        self.assertEqual(kt.sign_p(0, 0), 1.0)

    def test_load_readings(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.csv")
            write_csv(p, ["id", "category", "note"], [["c001", "a", "x"], ["c002", "E", ""]])
            self.assertEqual(kt.load_readings(p), {"c001": "A", "c002": "E"})
            write_csv(p, ["id", "category"], [["c001", "G"]])
            with self.assertRaises(ValueError):
                kt.load_readings(p)
            write_csv(p, ["id", "category"], [["c001", "A"], ["c001", "B"]])
            with self.assertRaises(ValueError):
                kt.load_readings(p)

    def _pairs(self):
        return [{"id": "c001", "block": "1", "pair": "01-1", "group": "zero", "duplicate_of": ""},
                {"id": "c002", "block": "1", "pair": "01-1", "group": "measured", "duplicate_of": ""},
                {"id": "c003", "block": "1", "pair": "01-2", "group": "zero", "duplicate_of": ""},
                {"id": "c004", "block": "1", "pair": "01-2", "group": "measured", "duplicate_of": ""},
                {"id": "c005", "block": "2", "pair": "02-1", "group": "zero", "duplicate_of": ""},
                {"id": "c006", "block": "2", "pair": "02-1", "group": "measured", "duplicate_of": ""},
                {"id": "c007", "block": "1", "pair": "01-1", "group": "zero", "duplicate_of": "c001"}]

    def test_grade_small(self):
        readings = {"c001": "A", "c002": "E", "c003": "D", "c004": "E", "c005": "E", "c006": "B", "c007": "A"}
        res = kt.grade(readings, self._pairs(), min_pairs=3, min_blocks=2)
        self.assertTrue(res["gate"]["pass"])
        self.assertEqual(res["gate"]["unreadable_share"], 0.0)
        v1 = res["tests"]["V1_abnormal"]
        self.assertEqual((v1["zero_only"], v1["measured_only"], v1["p"], v1["grade"]), (2, 1, 0.5, "untestable"))
        v2 = res["tests"]["V2_atrophic"]
        self.assertEqual((v2["zero_only"], v2["measured_only"], v2["p"]), (1, 0, 0.5))
        v3 = res["tests"]["V3_artefact"]
        self.assertEqual((v3["zero_only"], v3["measured_only"]), (1, 0))
        self.assertEqual(res["tests"]["V4_consistency"], {"agree": 1, "n": 1, "share": 1.0, "grade": "untestable"})
        self.assertEqual(res["table"], {"zero": {"A": 1, "D": 1, "E": 1}, "measured": {"B": 1, "E": 2}})

    def test_grade_gate_fails_on_missing(self):
        readings = {"c001": "A", "c002": "E", "c003": "D", "c004": "E", "c005": "E", "c007": "A"}
        res = kt.grade(readings, self._pairs(), min_pairs=3, min_blocks=2)
        self.assertFalse(res["gate"]["pass"])
        self.assertEqual(res["gate"]["missing"], ["c006"])
        self.assertEqual(res["gate"]["readable_pairs"], 2)
        self.assertEqual(set(res["grades"].values()), {"untestable"})

    def test_grade_pass(self):
        pairs, readings = [], {}
        for k in range(8):
            z, m = "c%03d" % (2 * k + 1), "c%03d" % (2 * k + 2)
            pairs += [{"id": z, "block": "1", "pair": "01-%d" % k, "group": "zero", "duplicate_of": ""},
                      {"id": m, "block": "1", "pair": "01-%d" % k, "group": "measured", "duplicate_of": ""}]
            readings[z], readings[m] = "A", "E"
        res = kt.grade(readings, pairs, min_pairs=8, min_blocks=1)
        self.assertEqual(res["tests"]["V1_abnormal"]["p"], 1 / 256)
        self.assertEqual(res["grades"]["V1_abnormal"], "pass")
        self.assertTrue(res["tests"]["V1_abnormal"]["bonferroni"])
        self.assertEqual(res["grades"]["V2_atrophic"], "pass")
        self.assertEqual(res["grades"]["V3_artefact"], "untestable")
        self.assertEqual(res["grades"]["V4_consistency"], "untestable")


def _image(h, w):
    import numpy as np
    yy, xx = np.mgrid[0:h, 0:w]
    return np.stack([(xx * 255 // w), (yy * 255 // h), ((xx + yy) % 256)], axis=-1).astype("uint8")


@unittest.skipUnless(HAVE_PIXELS, "numpy, tifffile and Pillow not installed")
class TestRender(unittest.TestCase):
    def test_render_offline(self):
        import tifffile
        tubs = [["x1", "x2", "y1", "y2", "Average TBM Thickness"],
                [100, 140, 100, 140, 0], [300, 340, 200, 250, 0],
                [500, 540, 100, 140, 3.0], [200, 245, 300, 345, 2.0], [590, 620, 400, 430, 1.0]]
        with tempfile.TemporaryDirectory() as d:
            svs = os.path.join(d, "slide.svs")
            tifffile.imwrite(svs, _image(480, 640), tile=(128, 128), photometric="rgb")
            zbytes = io.BytesIO()
            with zipfile.ZipFile(zbytes, "w") as z:
                z.write(svs, "pkg/S-0000-000001_PAS.svs")
                z.writestr("pkg/S-0000-000001_features_v2.xlsx", xlsx_bytes({"tubs": tubs}))
            flist = os.path.join(d, "list.csv")
            write_list(flist, [("open", "1 MB", "a_S-1_Seg_Masks_Features_v2.zip", "P1", SEG, "30-1"),
                               ("open", "1 MB", "b_S-2_Seg_Masks_Features_v2.zip", "P2", SEG, "30-2")])
            urls = []

            def get(url):
                urls.append(url)
                return io.BytesIO(zbytes.getvalue())

            out = os.path.join(d, "out")
            man = kt.render(flist, out, get=get, pause=lambda s: None, n_packages=2, per_package=2, min_zero=2,
                            min_measured=2, duplicates=1)
            self.assertEqual(len(urls), 2)
            self.assertEqual((man["blocks"], man["pairs"], man["crops"], man["duplicates"]), (2, 4, 8, 1))
            self.assertEqual(man["orientations"], {"xy": 2})
            ids = ["c%03d" % i for i in range(1, 10)]
            self.assertEqual(man["ids"], ids)
            self.assertEqual(sorted(os.listdir(os.path.join(out, "patches"))), [i + ".jpg" for i in ids])
            with open(os.path.join(out, "key", "key.json")) as f:
                crops = json.load(f)["crops"]
            self.assertEqual(sum(1 for c in crops if c["duplicate_of"]), 1)
            self.assertEqual({c["orientation"] for c in crops}, {"xy"})
            self.assertEqual(sorted(c["tbm"] for c in crops if not c["duplicate_of"] and c["group"] == "zero"),
                             [0.0] * 4)
            pair_rows = kt.load_pairs(os.path.join(out, "key", "pairs.csv"))
            self.assertEqual(len(pair_rows), 9)
            res = kt.grade({r["id"]: "E" for r in pair_rows}, pair_rows, min_pairs=4, min_blocks=2)
            self.assertTrue(res["gate"]["pass"])
            self.assertEqual(res["tests"]["V4_consistency"]["agree"], 1)
            with open(os.path.join(out, "manifest.json")) as f:
                self.assertNotIn("P1", f.read())


if __name__ == "__main__":
    unittest.main()
