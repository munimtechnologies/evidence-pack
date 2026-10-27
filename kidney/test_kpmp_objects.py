# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_objects (no network, no KPMP data: workbooks are built here).

Headers are the raw text census pass 2 recorded for every v2 package; sheet names are varied in
case because their raw form has not been recorded yet (only their norm() form)."""
import io
import json
import math
import os
import random
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

from kidney import kpmp_objects as ko

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
GLOM_HEADER = ["x1", "x2", "y1", "y2", "Area", "Mesangial Area", "Mesangial Fraction"]
TUB_HEADER = ["x1", "x2", "y1", "y2", "Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"]
ART_HEADER = ["x1", "x2", "y1", "y2", "Arterial Area"]


def sheet_xml(rows):
    out = ['<worksheet xmlns="%s"><sheetData>' % MAIN]
    for i, row in enumerate(rows, 1):
        out.append('<row r="%d">' % i)
        for j, v in enumerate(row):
            ref = chr(65 + j) + str(i)
            if v is None:
                continue
            if isinstance(v, str):
                out.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(v)))
            else:
                out.append('<c r="%s"><v>%r</v></c>' % (ref, v))
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def make_xlsx(sheets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        wb = ['<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (MAIN, REL)]
        rels = ['<Relationships xmlns="%s">' % PKG]
        for i, (name, rows) in enumerate(sheets.items(), 1):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': "&quot;"}), i, i))
            rels.append('<Relationship Id="rId%d" Type="worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
            z.writestr("xl/worksheets/sheet%d.xml" % i, sheet_xml(rows))
        z.writestr("xl/workbook.xml", "".join(wb) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels) + "</Relationships>")
    return buf.getvalue()


def write_package(d, sheets, n_books=1, ok=True):
    os.makedirs(d, exist_ok=True)
    for k in range(n_books):
        with open(os.path.join(d, "book%d.xlsx" % k), "wb") as f:
            f.write(make_xlsx(sheets))
    with open(os.path.join(d, "record.json"), "w", encoding="utf-8") as f:
        json.dump({"ok": ok}, f)


def synthetic_sheets(seed, n_gloms=30, n_tubs=60, n_arts=25, extreme=True):
    """A v2-like workbook: elliptical objects (fill about pi/4), one extreme tubule clustered
    with a few others, one giant misshapen glomerulus."""
    rng = random.Random(seed)
    gl = [GLOM_HEADER]
    for k in range(n_gloms):
        w, h = rng.uniform(300, 400), rng.uniform(300, 400)
        x, y = 1000 * k, 500
        area = math.pi / 4 * w * h
        mes = area * rng.uniform(0.15, 0.25)
        gl.append([x, x + w, y, y + h, area, mes, mes / area])
    if extreme:
        gl.append([90000, 93000, 500, 500 + 600, 0.3 * 3000 * 600, 0.2 * 0.3 * 3000 * 600, 0.2])
    sg = [GLOM_HEADER, [5000, 5300, 9000, 9300, 60000, 9000, 0.15]]
    tb = [TUB_HEADER]
    for k in range(n_tubs):
        x, y = rng.uniform(0, 100000), rng.uniform(0, 100000)
        tb.append([x, x + 80, y, y + 60, rng.uniform(8, 12), rng.uniform(20, 30), rng.uniform(0.1, 0.3)])
    if extreme:
        for k in range(12):
            tb.append([50000 + 10 * k, 50080 + 10 * k, 50000, 50060, 200.0 + k, 25.0, 0.2])
    ar = [ART_HEADER]
    for k in range(n_arts):
        w = rng.uniform(100, 200)
        ar.append([2000 * k, 2000 * k + w, 7000, 7000 + w, math.pi / 4 * w * w])
    return {"Gloms": gl, "s_gloms": sg, "Tubs": tb, "arts": ar}


class TestReader(unittest.TestCase):
    def test_read_xlsx_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.xlsx")
            with open(p, "wb") as f:
                f.write(make_xlsx({"Tubs": [TUB_HEADER, [1, 2.5, 3, 4, 5, 6, 0.5]]}))
            book = ko.read_xlsx(p)
        self.assertEqual(list(book), ["Tubs"])
        self.assertEqual(book["Tubs"][0], TUB_HEADER)
        self.assertEqual([ko.parse_float(x) for x in book["Tubs"][1]], [1.0, 2.5, 3.0, 4.0, 5.0, 6.0, 0.5])

    def test_load_v2_matches_sheets_by_norm_and_columns_exactly(self):
        seen = ko.Counter()
        with tempfile.TemporaryDirectory() as d:
            write_package(d, synthetic_sheets(1, extreme=False))
            st, t = ko.load_v2(d, seen)
        self.assertEqual(st, "v2")
        self.assertEqual(sorted(t), sorted(ko.SHEETS))
        self.assertEqual(len(t["gloms"]), 30)
        self.assertEqual(len(t["s_gloms"]), 1)
        self.assertEqual(len(t["tubs"]), 60)
        self.assertEqual(t["s_gloms"][0], (5000.0, 5300.0, 9000.0, 9300.0, 60000.0, 9000.0, 0.15))
        self.assertEqual(seen[("sheet_names", "Gloms|Tubs|arts|s_gloms")], 1)
        self.assertEqual(seen[("header:tubs", "|".join(TUB_HEADER))], 1)

    def test_v1_layout_is_not_v2(self):
        with tempfile.TemporaryDirectory() as d:
            write_package(d, synthetic_sheets(1, extreme=False), n_books=2)
            self.assertEqual(ko.load_v2(d), ("not_v2", None))
        with tempfile.TemporaryDirectory() as d:
            write_package(d, {"Features": [TUB_HEADER, [1, 2, 3, 4, 5, 6, 0.5]]})
            self.assertEqual(ko.load_v2(d), ("not_v2", None))

    def test_missing_exact_column(self):
        sheets = synthetic_sheets(1, extreme=False)
        sheets["Tubs"][0] = ["x1", "x2", "y1", "y2", "average tbm thickness", "Average Cell Thickness",
                             "Luminal Fraction"]
        with tempfile.TemporaryDirectory() as d:
            write_package(d, sheets)
            self.assertEqual(ko.load_v2(d), ("v2_missing_columns", None))

    def test_package_dirs_skips_folders_without_ok_record(self):
        with tempfile.TemporaryDirectory() as d:
            write_package(os.path.join(d, "a"), synthetic_sheets(1, extreme=False))
            write_package(os.path.join(d, "b"), synthetic_sheets(1, extreme=False), ok=False)
            os.makedirs(os.path.join(d, "tiv"))
            got = [os.path.basename(p) for p in ko.package_dirs(d)]
        self.assertEqual(got, ["a"])


class TestGeometryAndStats(unittest.TestCase):
    def test_box_fill_aspect(self):
        r = (0, 10, 0, 20, 100.0, 10.0, 0.1)
        self.assertEqual(ko.box(r), (0, 10, 0, 20))
        self.assertEqual(ko.fill(r), 0.5)
        self.assertEqual(ko.aspect(r), 2.0)
        self.assertIsNone(ko.box((5, 5, 0, 1, 1.0)))
        self.assertIsNone(ko.box((None, 5, 0, 1, 1.0)))
        self.assertTrue(ko.misshapen((0, 10, 0, 30, 290.0)))   # aspect 3
        self.assertTrue(ko.misshapen((0, 10, 0, 10, 40.0)))    # fill 0.4
        self.assertFalse(ko.misshapen((0, 10, 0, 10, 78.5)))

    def test_iou(self):
        self.assertEqual(ko.iou((0, 10, 0, 10), (0, 10, 0, 10)), 1.0)
        self.assertEqual(ko.iou((0, 10, 0, 10), (10, 20, 0, 10)), 0.0)
        self.assertAlmostEqual(ko.iou((0, 10, 0, 10), (5, 15, 0, 10)), 50 / 150)

    def test_mean_nn(self):
        self.assertAlmostEqual(ko.mean_nn([(0, 0), (3, 4), (10, 0)]), (5 + 5 + math.hypot(7, 4)) / 3)
        self.assertEqual(ko.mean_nn([(1, 1), (1, 1)]), 0.0)

    def test_robust_and_tails(self):
        med, s = ko.robust([1, 2, 3, 4, 100])
        self.assertEqual(med, 3)
        self.assertAlmostEqual(s, 1.4826)
        self.assertEqual(ko.robust([2, 2, 2]), (2, None))
        self.assertEqual(ko.binom_tail(5, 5), 1 / 32)
        self.assertEqual(ko.binom_tail(4, 0), 1.0)
        self.assertEqual(ko.dispersion([(1, 10), (1, 10), (1, 10)]), 0.0)
        self.assertGreater(ko.dispersion([(10, 10), (0, 10), (0, 10), (0, 10)]), 2)
        self.assertIsNone(ko.dispersion([(0, 10), (0, 10)]))


class TestIntegrity(unittest.TestCase):
    def test_counts(self):
        t = {"gloms": [(0, 10, 0, 10, 78.5, 15.7, 0.2),        # consistent, fill 0.785
                       (1, 11, 0, 10, 78.5, 15.7, 0.5),        # overlaps the first; fraction wrong
                       (100, 110, 0, 10, 150.0, 30.0, 0.2)],   # area bigger than its box
             "s_gloms": [(500, 510, 0, 10, 70.0, 7.0, 0.1)],
             "tubs": [(0, 5, 0, 5, 1.0, 2.0, 0.5), (0, 5, 0, 5, 1.0, 2.0, 0.5), (9, 9, 0, 5, 1.0, 2.0, 1.5)],
             "arts": [(0, 10, 0, 10, 50.0)]}
        it, dup = ko.integrity([("p", t)])
        self.assertEqual(it["counts"]["objects"], 8)
        self.assertEqual(it["I1_box_valid"], round(7 / 8, 6))
        self.assertEqual(it["I2_glom_fill_median"], 0.785)
        self.assertEqual(it["I3_area_in_box"], round(4 / 5, 6))
        self.assertEqual(it["I4_mesangial_consistent"], 0.75)
        self.assertEqual(it["I5_fractions_in_range"], round(6 / 7, 6))
        self.assertEqual(it["I6_glom_double_segmentation"], 0.5)
        self.assertEqual(dup, {(0, "gloms", 0), (0, "gloms", 1)})
        self.assertEqual(it["counts"]["dup_pairs_same_sheet"], 1)
        self.assertEqual(it["I7_tubule_duplicates"], round(1 / 3, 6))


class TestEndToEnd(unittest.TestCase):
    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "data", "kpmp-census")
            for k in range(4):
                write_package(os.path.join(cache, "pkg%d" % k), synthetic_sheets(k))
            write_package(os.path.join(cache, "v1pkg"), synthetic_sheets(9), n_books=3)
            os.makedirs(os.path.join(cache, "tiv"))
            out = os.path.join(d, "out")
            self.assertEqual(ko.main(["--data-dir", os.path.join(d, "data"), "--out-dir", out,
                                      "--min-packages", "4", "--min-slide-objects", "20"]), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "candidates.json"), encoding="utf-8") as f:
                cand = json.load(f)
        self.assertEqual(res["read"]["package_dirs"], 5)
        self.assertEqual(res["read"]["v2"], 4)
        self.assertEqual(res["read"]["status"], {"v2": 4, "not_v2": 1})
        self.assertEqual(res["grades"]["status"], "complete")
        self.assertEqual(set(res["grades"]) - {"status"}, set(ko.PREDICTIONS))
        for k, v in res["grades"].items():
            if k != "status":
                self.assertIn(v, ("pass", "fail", "untestable"))
        self.assertEqual(res["grades"]["I1_box_valid"], "pass")
        self.assertEqual(res["grades"]["I2_glom_fill_median"], "pass")
        self.assertEqual(res["grades"]["I4_mesangial_consistent"], "pass")
        tubs = res["rarity"]["tubs"]
        self.assertEqual(tubs["slides"], 4)
        self.assertGreaterEqual(tubs["slide_outliers"], 48)   # the 12 thick-TBM tubules per slide
        self.assertEqual(res["rarity"]["R3"]["outliers_misshapen"], 4)   # the giant glomerulus per slide
        top = cand["candidates"]["tubs"][0]
        self.assertEqual(top["feature"], "Average TBM Thickness")
        self.assertEqual(top["direction"], "high")
        self.assertNotIn("pkg", json.dumps(res))   # package names stay out of results.json

    def test_gate(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out")
            ko.main(["--data-dir", os.path.join(d, "data"), "--out-dir", out])
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
        self.assertTrue(res["grades"]["status"].startswith("gate failed"))
        self.assertEqual(res["grades"]["R4_tubule_outliers_cluster"], "pending")


if __name__ == "__main__":
    unittest.main()
