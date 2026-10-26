# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_census (no network: downloads are faked)."""
import io
import json
import os
import tempfile
import unittest
import urllib.error
import zipfile
from xml.sax.saxutils import escape

from kidney import kpmp_census as kc

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/package/2006/relationships"
HEADER = ('"Access","Platform","Data Format","Data Category","Size","File Name","Internal Package ID",'
          '"Experimental Strategy","Workflow Type","Participant ID","DOIs"')
TUBS = ["x1", "x2", "y1", "y2", "Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"]
GLOMS = ["x1", "x2", "y1", "y2", "Area", "Mesangial Area", "Mesangial Fraction"]
README = ("README for KPMP package download.\n"
          "  - In v2 Measurements represented as either unitless, pixels, pixels squared\n"
          "NOTE: ome.tif file past S-2006-005094 (alphanumerically) do NOT contain annotations for "
          "interstitial fibrosis and tubular atrophy (IFTA)\n")


def make_xlsx(sheets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        wb = ['<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (NS, RNS)]
        rels = ['<Relationships xmlns="%s">' % PNS]
        for i, (name, rows) in enumerate(sheets.items(), 1):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rels.append('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i, i))
            xml_rows = []
            for ri, row in enumerate(rows, 1):
                cells = []
                for ci, val in enumerate(row):
                    if val is None:
                        continue
                    ref = "%s%d" % (chr(65 + ci), ri)
                    if isinstance(val, (int, float)):
                        cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
                    else:
                        cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(val)))
                xml_rows.append('<row r="%d">%s</row>' % (ri, "".join(cells)))
            z.writestr("xl/worksheets/sheet%d.xml" % i,
                       '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>' % (NS, "".join(xml_rows)))
        wb.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
    return buf.getvalue()


def ome_xml(mpp="0.25", unit=None, channels=("glomeruli", "IFTA")):
    unit_attr = ' PhysicalSizeXUnit="%s"' % unit if unit else ""
    chans = "".join('<Channel ID="Channel:0:%d" Name="%s"/>' % (i, c) for i, c in enumerate(channels))
    return ('<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"><Image ID="Image:0">'
            '<Pixels DimensionOrder="XYCZT" PhysicalSizeX="%s" PhysicalSizeY="%s"%s SizeX="100" SizeY="50" '
            'SizeC="%d" Type="uint16">%s<TiffData/></Pixels></Image></OME>'
            % (mpp, mpp, unit_attr, len(channels), chans)).encode("utf-8")


def features_xlsx():
    return make_xlsx({"gloms": [GLOMS, [1, 2, 3, 4, 1600, 400, 0.25], [1, 2, 3, 4, 3200, 800, 0.25]],
                      "tubs": [TUBS, [0, 0, 0, 0, 8, 20, 0.1], [0, 0, 0, 0, 12, 24, 0.3],
                               [0, 0, 0, 0, 10, 22, 0.2]],
                      "arts": [["x1", "x2", "y1", "y2", "Arterial Area"]]})


def fill_package_dir(path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "S-1904-008128_PAS_2of2_features_v2.xlsx"), "wb") as f:
        f.write(features_xlsx())
    with open(os.path.join(path, "S-1904-008128_PAS_2of2.ome.xml"), "wb") as f:
        f.write(ome_xml())
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)


class TestUnits(unittest.TestCase):
    def test_norm_and_power(self):
        self.assertEqual(kc.norm("Area (pixels)"), "area")
        self.assertEqual(kc.norm("  Average TBM  Thickness "), "average tbm thickness")
        self.assertEqual(kc.unit_power("Luminal Fraction"), 0)
        self.assertEqual(kc.unit_power("Mesangial Fraction"), 0)
        self.assertEqual(kc.unit_power("Mesangial Area"), 2)
        self.assertEqual(kc.unit_power("Average TBM Thickness"), 1)
        self.assertIsNone(kc.unit_power("Count"))

    def test_convert(self):
        self.assertEqual(kc.convert(10, "v1", 1, 0.25), 10)
        self.assertEqual(kc.convert(10, "v2", 1, 0.25), 2.5)
        self.assertEqual(kc.convert(16, "v2", 2, 0.25), 1.0)
        self.assertEqual(kc.convert(0.5, "v2", 0, None), 0.5)
        self.assertIsNone(kc.convert(3, "v2", 1, None))
        self.assertIsNone(kc.convert(3, "v2", None, 0.25))
        self.assertIsNone(kc.convert(None, "v1", 1, 0.25))

    def test_sizes_versions_slides(self):
        self.assertEqual(kc.parse_size("1 GB"), 10**9)
        self.assertEqual(kc.parse_size("11.8 MB"), 11800000)
        self.assertTrue(kc.size_ok(11806912, "11.8 MB"))
        self.assertFalse(kc.size_ok(5000000, "11.8 MB"))
        self.assertEqual(kc.version_of("a_S-1904-008128_Seg_Masks_Features_v2.zip"), "v2")
        self.assertEqual(kc.version_of("a_S-2311-011607_Seg_Masks_Features.zip"), "v1")
        self.assertEqual(kc.slide_of("a_S-1904-008128_Seg_Masks_Features_v2.zip"), "S-1904-008128")
        self.assertEqual(kc.slide_of("no slide here.zip"), "")


class TestFileList(unittest.TestCase):
    def test_load_and_order(self):
        rows = [
            '"open","","tif xml xlsx svs md","Pathology","11.8 MB","u1_S-1904-008128_Seg_Masks_Features_v2.zip",'
            '"pkg-b","Segmentation Masks & Pathomics Vectors","","34-10050",""',
            '"open","","tif xml xlsx svs md","Pathology","128 MB","u2_S-2311-011607_Seg_Masks_Features.zip",'
            '"pkg-a","Segmentation Masks & Pathomics Vectors","","30-11154,30-11155",""',
            '"open","","svs","Pathology","11.2 MB","u3_S-1904-008128_PAS_2of2.svs",'
            '"pkg-c","Light Microscopic Whole Slide Images","PAS","34-10050",""',
            '"controlled","","tif xml xlsx svs md","Pathology","1 MB","u4_S-2000-000001_Seg_Masks_Features.zip",'
            '"pkg-d","Segmentation Masks & Pathomics Vectors","","1-1",""',
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "list.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join([HEADER] + rows) + "\n")
            pk = kc.load_packages(path)
        self.assertEqual([p["package"] for p in pk], ["pkg-b", "pkg-a"])
        self.assertEqual(pk[0]["version"], "v2")
        self.assertEqual(pk[1]["version"], "v1")
        self.assertEqual(pk[1]["participants"], ["30-11154", "30-11155"])
        self.assertEqual(pk[0]["slide"], "S-1904-008128")
        many = [{"package": "p%03d" % i, "name": "n%d" % i} for i in range(30)]
        o1, o2 = kc.census_order(many), kc.census_order(list(reversed(many)))
        self.assertEqual(o1, o2)
        self.assertEqual(sorted(p["package"] for p in o1), [p["package"] for p in many])
        self.assertNotEqual([p["package"] for p in o1], [p["package"] for p in many])


class TestReaders(unittest.TestCase):
    def test_ome_info(self):
        o = kc.ome_info(ome_xml())
        self.assertEqual(o["mpp"], 0.25)
        self.assertEqual(o["channels"], ["glomeruli", "IFTA"])
        self.assertIsNone(kc.ome_info(ome_xml(unit="nm"))["mpp"])
        self.assertEqual(kc.ome_info(ome_xml(unit="um"))["mpp"], 0.25)

    def test_readme_info(self):
        r = kc.readme_info(README)
        self.assertTrue(r["v2_pixels_sentence"])
        self.assertTrue(r["ifta_note"])
        self.assertEqual(len(r["sha256"]), 64)
        self.assertFalse(kc.readme_info("nothing")["ifta_note"])

    def test_analyse_dir_v2_and_v1(self):
        with tempfile.TemporaryDirectory() as d:
            fill_package_dir(d)
            a2 = kc.analyse_dir(d, "v2")
            a1 = kc.analyse_dir(d, "v1")
        self.assertEqual(a2["errors"], [])
        self.assertEqual(a2["xlsx"], 1)
        self.assertEqual(a2["sheets"]["tubs"]["n_rows"], 3)
        self.assertEqual(a2["sheets"]["gloms"]["n_rows"], 2)
        self.assertEqual(a2["sheets"]["arts"]["n_rows"], 0)
        f = a2["features"]
        self.assertEqual(f["tbm"]["median_raw"], 10.0)
        self.assertEqual(f["tbm"]["median_conv"], 2.5)
        self.assertEqual(f["cell"]["median_conv"], 5.5)
        self.assertEqual(f["lumen"]["median_conv"], 0.2)
        self.assertEqual(f["glom_area"]["median_raw"], 2400.0)
        self.assertEqual(f["glom_area"]["median_conv"], 150.0)
        self.assertEqual(f["tbm"]["n"], 3)
        self.assertEqual(a1["features"]["tbm"]["median_conv"], 10.0)
        self.assertTrue(a2["readme"]["ifta_note"])
        self.assertEqual(a2["ome"]["mpp"], 0.25)

    def test_tiv_table(self):
        sheets = {"Data Table": [
            ["KPMP TIV"], [], [None],
            ["Participant ID", "Release Date", "Consensus Complete", kc.LUMEN_SCORE, kc.ATROPHY_SCORE],
            ["1-1", "Q1 2025", "Y", "10.0", "5.0"],
            ["1-2", "Q1 2025", "y", "n/a", "0.0"],
            ["1-3", "Q1 2025", "N", "1", "1"],
            ["1-4", "Q1 2025", "Y", "1", "1"],
            ["1-4", "Q1 2026", "Y", "2", "2"]]}
        scores, info = kc.tiv_table(sheets)
        self.assertEqual(sorted(scores), ["1-1", "1-2"])
        self.assertEqual(scores["1-1"][kc.LUMEN_SCORE], 10.0)
        self.assertIsNone(scores["1-2"][kc.LUMEN_SCORE])
        self.assertEqual(scores["1-2"][kc.ATROPHY_SCORE], 0.0)
        self.assertEqual(info["participants"], 4)
        self.assertEqual(info["rows"], 5)
        self.assertEqual(info["duplicated"], 1)
        self.assertEqual(info["not_consensus"], 1)
        self.assertEqual(info["usable"], 2)
        self.assertEqual(info["missing_columns"], [kc.INJURY_SCORE, kc.FIBROSIS_SCORE])
        self.assertEqual(kc.tiv_table({})[0], {})


class FakeHTTP404:
    def __call__(self, url):
        raise urllib.error.HTTPError(url, 404, "not found", None, None)


class TestFetch(unittest.TestCase):
    def _zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("README.md", README)
            z.writestr("pkg/S-1_features_v2.xlsx", features_xlsx())
            z.writestr("S-1.ome.xml", ome_xml())
            z.writestr("S-1.ome.tif", b"0" * 10)
            z.writestr("S-1.svs", b"1" * 10)
        return buf.getvalue()

    def test_fetch_keeps_small_members_and_caches(self):
        data = self._zip()
        p = {"package": "pkg-1", "name": "u_S-1_Seg_Masks_Features_v2.zip", "listed": "%d B" % len(data)}
        calls = []

        def get(url):
            calls.append(url)
            return io.BytesIO(data)

        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as tmp:
            rec = kc.fetch_package(p, cache, tmp, get=get, pause=lambda s: None)
            self.assertTrue(rec["ok"])
            self.assertTrue(rec["size_ok"])
            self.assertFalse(rec["cached"])
            self.assertEqual(rec["kept"], ["README.md", "S-1_features_v2.xlsx", "S-1.ome.xml"])
            self.assertEqual(len(rec["members"]), 5)
            self.assertEqual(len(rec["download"]["sha256"]), 64)
            self.assertEqual(sorted(os.listdir(os.path.join(cache, "pkg-1"))),
                             ["README.md", "S-1.ome.xml", "S-1_features_v2.xlsx", "record.json"])
            self.assertEqual(os.listdir(tmp), [])
            self.assertIn("/pkg-1/u_S-1_Seg_Masks_Features_v2.zip", calls[0])

            def no_get(url):
                raise AssertionError("cached package downloaded again")

            again = kc.fetch_package(p, cache, tmp, get=no_get)
            self.assertTrue(again["cached"])
            a = kc.analyse_dir(os.path.join(cache, "pkg-1"), "v2")
            self.assertEqual(a["features"]["tbm"]["median_conv"], 2.5)

    def test_fetch_404_is_final(self):
        pauses = []
        p = {"package": "pkg-2", "name": "x.zip", "listed": "1 MB"}
        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as tmp:
            rec = kc.fetch_package(p, cache, tmp, get=FakeHTTP404(), pause=pauses.append)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["download"]["error"], "HTTP 404")
            self.assertEqual(rec["download"]["tries"], 1)
            self.assertEqual(pauses, [])
            self.assertFalse(os.path.exists(os.path.join(cache, "pkg-2", "record.json")))


class TestStats(unittest.TestCase):
    def test_ranks_and_spearman(self):
        self.assertEqual(kc.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
        self.assertAlmostEqual(kc.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(kc.spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)
        self.assertIsNone(kc.spearman([1, 2], [1, 2]))
        self.assertIsNone(kc.spearman([1, 1, 1], [1, 2, 3]))

    def test_perm_p(self):
        x = list(range(8))
        self.assertLess(kc.perm_p(x, x, 1, n_perm=200, seed=1), 0.05)
        self.assertGreater(kc.perm_p(x, x, -1, n_perm=200, seed=1), 0.9)


def ratio_records(v1, v2_raw, v2_conv, feature):
    recs = [{"version": "v1", "analysis": {"features": {feature: {"median_raw": v1, "median_conv": v1}}}}
            for _ in range(10)]
    recs += [{"version": "v2", "analysis": {"features": {feature: {"median_raw": v2_raw, "median_conv": v2_conv}}}}
             for _ in range(10)]
    return recs


class TestCensus(unittest.TestCase):
    def test_version_ratio(self):
        r = kc.version_ratio(ratio_records(10.0, 40.0, 10.1, "tbm"), "tbm")
        self.assertEqual(r["raw_ratio"], 4.0)
        self.assertAlmostEqual(r["converted_ratio"], 1.01)
        few = kc.version_ratio(ratio_records(10.0, 40.0, 10.1, "tbm")[:15], "tbm")
        self.assertIsNone(few["raw_ratio"])
        self.assertIsNone(kc.version_ratio([], "tbm")["converted_ratio"])

    def test_ifta_check(self):
        def rec(slide, chans):
            return {"slide": slide, "analysis": {"ome": {"channels": chans}}}

        before = [rec("S-1904-008128", ["glomeruli", "IFTA"]) for _ in range(9)] + [rec("S-2006-005094", ["g"])]
        after = [rec("S-2107-011577", ["glomeruli"]) for _ in range(5)]
        ok = kc.ifta_check(before + after)
        self.assertEqual((ok["before"], ok["before_with_ifta"], ok["after"], ok["after_with_ifta"]), (10, 9, 5, 0))
        self.assertEqual(ok["grade"], "pass")
        self.assertEqual(kc.ifta_check(before + after + [rec("S-2401-002334", ["IFTA"])])["grade"], "fail")
        self.assertEqual(kc.ifta_check([rec("S-1904-008128", ["g"]), rec("S-2401-002334", ["g"])])["grade"],
                         "untestable")

    def test_participants_and_agreement(self):
        recs, scores = [], {}
        for k in range(40):
            pid = "p%02d" % k
            recs.append({"participants": [pid], "version": "v2",
                         "analysis": {"sheets": {"tubs": {"n_rows": 25}}, "ome": {"mpp": 0.25},
                                      "values": {"tbm": [4.0 * k]}}})
            scores[pid] = {kc.ATROPHY_SCORE: float(k)}
        recs.append({"participants": ["q1", "q2"], "version": "v2",
                     "analysis": {"sheets": {"tubs": {"n_rows": 99}}, "ome": {"mpp": 0.25}, "values": {"tbm": [1.0]}}})
        recs.append({"participants": ["small"], "version": "v1",
                     "analysis": {"sheets": {"tubs": {"n_rows": 5}}, "ome": None, "values": {"tbm": [1.0]}}})
        scores["small"] = {kc.ATROPHY_SCORE: 1.0}
        pt = kc.participant_table(recs)
        self.assertNotIn("q1", pt)
        self.assertEqual(pt["p03"]["conv"]["tbm"], [3.0])
        self.assertEqual(pt["p03"]["raw"]["tbm"], [12.0])
        a = kc.agreement(pt, scores, "tbm", kc.ATROPHY_SCORE, 1, "conv", None, 200, 1)
        self.assertEqual(a["n"], 40)
        self.assertAlmostEqual(a["rho"], 1.0)
        self.assertLess(a["p_one_sided"], 0.05)
        self.assertEqual(kc.agreement(pt, scores, "tbm", kc.ATROPHY_SCORE, 1, "conv", {"v1"}, 0)["n"], 0)
        self.assertNotIn("p_one_sided", kc.agreement(pt, scores, "tbm", kc.ATROPHY_SCORE, 1, "raw", None, 0))

    def _res(self, analysed):
        u = {"tbm": kc.version_ratio(ratio_records(10.0, 40.0, 10.1, "tbm"), "tbm"),
             "glom_area": kc.version_ratio(ratio_records(100.0, 1600.0, 100.0, "glom_area"), "glom_area")}
        good = {"n": 40, "rho": 0.3, "p_one_sided": 0.01}
        return {"census": {"listed": 20, "attempted": 20, "download_ok_size_ok": 20, "analysed": analysed},
                "unit_checks": u, "ifta": {"grade": "pass"},
                "agreement": {"P7_lumen_vs_abnormal_lumen": {"conv": good},
                              "P8_tbm_vs_atrophy": {"conv": {"n": 40, "rho": 0.3, "p_one_sided": 0.2}},
                              "P9_cell_vs_injury_other": {"conv": {"n": 40, "rho": -0.2, "p_one_sided": 0.02}}}}

    def test_grade(self):
        g = kc.grade(self._res(20))
        self.assertEqual(g["status"], "complete")
        self.assertEqual(g["P1_access"], "pass")
        self.assertEqual(g["P2_tbm_raw_ratio"], "pass")
        self.assertEqual(g["P3_tbm_converted_ratio"], "pass")
        self.assertEqual(g["P4_glom_area_raw_ratio"], "pass")
        self.assertEqual(g["P5_glom_area_converted_ratio"], "pass")
        self.assertEqual(g["P6_ifta_note"], "pass")
        self.assertEqual(g["P7_lumen_vs_abnormal_lumen"], "pass")
        self.assertEqual(g["P8_tbm_vs_atrophy"], "fail")
        self.assertEqual(g["P9_cell_vs_injury_other"], "pass")
        self.assertNotIn("D1_tbm_vs_fibrosis", g)
        part = kc.grade(self._res(10))
        self.assertEqual(part["status"], "incomplete")
        self.assertEqual(part["P1_access"], "pass")
        self.assertEqual(part["P2_tbm_raw_ratio"], "pending")


class TestMainOffline(unittest.TestCase):
    def test_main_from_cache(self):
        rows = [
            '"open","","tif xml xlsx svs md","Pathology","11.8 MB","u1_S-1904-008128_Seg_Masks_Features_v2.zip",'
            '"pkg-1","Segmentation Masks & Pathomics Vectors","","34-10050",""',
            '"open","","tif xml xlsx svs md","Pathology","128 MB","u2_S-2311-011607_Seg_Masks_Features.zip",'
            '"pkg-2","Segmentation Masks & Pathomics Vectors","","30-11154",""',
        ]
        tiv = make_xlsx({"Data Table": [["Participant ID", "Consensus Complete", kc.ATROPHY_SCORE],
                                        ["34-10050", "Y", "5.0"], ["30-11154", "Y", "10.0"]]})
        with tempfile.TemporaryDirectory() as d:
            csv_path = os.path.join(d, "list.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("\n".join([HEADER] + rows) + "\n")
            data, out = os.path.join(d, "data"), os.path.join(d, "out")
            for pkg in ("pkg-1", "pkg-2"):
                pdir = os.path.join(data, "kpmp-census", pkg)
                fill_package_dir(pdir)
                with open(os.path.join(pdir, "record.json"), "w", encoding="utf-8") as f:
                    json.dump({"ok": True, "size_ok": True, "download": {"ok": True, "bytes": 1},
                               "members": [], "kept": []}, f)
            os.makedirs(os.path.join(data, "kpmp-census", "tiv"))
            with open(os.path.join(data, "kpmp-census", "tiv", "tiv.xlsx"), "wb") as f:
                f.write(tiv)
            self.assertEqual(kc.main(["--file-list", csv_path, "--out-dir", out, "--data-dir", data,
                                      "--permutations", "20"]), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "progress.jsonl"), encoding="utf-8") as f:
                progress = f.read().splitlines()
        self.assertEqual(res["census"]["listed"], 2)
        self.assertEqual(res["census"]["analysed"], 2)
        self.assertEqual(res["census"]["cached_before_this_run"], 2)
        self.assertEqual(res["grades"]["status"], "complete")
        self.assertEqual(res["grades"]["P1_access"], "pass")
        self.assertEqual(res["grades"]["P2_tbm_raw_ratio"], "untestable")
        self.assertEqual(res["grades"]["P8_tbm_vs_atrophy"], "untestable")
        self.assertEqual(res["tiv"]["usable"], 2)
        self.assertEqual(res["participants"]["with_tiv"], 2)
        self.assertEqual(len(progress), 2)
        for row in res["packages"]:
            self.assertNotIn("participants", row)
        self.assertEqual((res["ifta"]["before"], res["ifta"]["after"]), (1, 1))
        self.assertEqual(res["ifta"]["grade"], "fail")


if __name__ == "__main__":
    unittest.main()
