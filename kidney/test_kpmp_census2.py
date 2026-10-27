# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_census2 (no network: downloads are faked)."""
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import test_kpmp_census as t1

DESC = ("Aperio Image Library v12.0.16 \r\n16256x17850 [0,100 15943x17750] (240x240) J2K/YUV16 Q=70"
        "|AppMag = 40|MPP = 0.2527|Left = 27")
TIV_ROW = ('"open","","xlsx","Pathology","469 kB","u9_KPMP TIV Descriptor Scores 10.12.2026.xlsx","pkg-t",'
           '"Pathology Descriptor Scoring","","1-1,1-2",""')


def classic_tiff(desc, e="<"):
    d = desc.encode("latin-1") + b"\0"
    ifd, n = 8, 2
    data_off = ifd + 2 + n * 12 + 4
    head = (b"II" if e == "<" else b"MM") + struct.pack(e + "HI", 42, ifd)
    entries = struct.pack(e + "HHII", 256, 4, 1, 100) + struct.pack(e + "HHII", 270, 2, len(d), data_off)
    return head + struct.pack(e + "H", n) + entries + struct.pack(e + "I", 0) + d


def big_tiff(desc):
    d = desc.encode("latin-1") + b"\0"
    ifd = 16
    data_off = ifd + 8 + 20 + 8
    head = b"II" + struct.pack("<HHHQ", 43, 8, 0, ifd)
    return head + struct.pack("<Q", 1) + struct.pack("<HHQQ", 270, 2, len(d), data_off) + struct.pack("<Q", 0) + d


def svs_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", t1.README)
        z.writestr("S-1_PAS_1of2.svs", classic_tiff(DESC))
        z.writestr("S-1.ome.tif", b"0" * 10)
    return buf.getvalue()


def fill_v1_dir(path):
    os.makedirs(path, exist_ok=True)
    books = {
        "final_combined_features_non_globally_sclerotic_gloms.xlsx": {
            "features": [["Nuclei Number", "Area (pixel^2)", "Radius (pixel)", "Area", "Mesangial Area",
                          "Mesangial Fraction", "compartment_id"],
                         [5, 16000, 70, 1000, 200, 0.2, 1], [6, 32000, 100, 2000, 300, 0.15, 2]],
            "bounding boxes": [["x1", "y1", "x2", "y2", "compartment_ids"], [0, 0, 1, 1, 1]]},
        "final_combined_features_tubules.xlsx": {
            "features": [["Nuclei Number", "Area (pixel^2)", "Average TBM Thickness", "Average Cell Thickness",
                          "Luminal Fraction"],
                         [1, 500, 1.0, 7.0, 0.1], [2, 600, 2.0, 8.0, 0.3], [3, 700, 3.0, 9.0, 0.2]]},
        "final_combined_features_muscular_vessels.xlsx": {"features": [["Luminal ratio", "Arterial Area"], [0.5, 100]]},
        "final_combined_features_peritubular_capillaries.xlsx": {"features": [["Area"], [3]]},
    }
    for fn, sheets in books.items():
        with open(os.path.join(path, fn), "wb") as f:
            f.write(t1.make_xlsx(sheets))
    with open(os.path.join(path, "S-2311-011607_PAS_1of2.ome.xml"), "wb") as f:
        f.write(t1.ome_xml(channels=("tubules", "glomeruli")))
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
        f.write("README for KPMP package download.\n")


class TestTiff(unittest.TestCase):
    def test_tiff_description(self):
        self.assertEqual(k2.tiff_description(io.BytesIO(classic_tiff(DESC))), DESC)
        self.assertEqual(k2.tiff_description(io.BytesIO(classic_tiff(DESC, ">"))), DESC)
        self.assertEqual(k2.tiff_description(io.BytesIO(big_tiff(DESC))), DESC)
        inline = (b"MM" + struct.pack(">HI", 42, 8) + struct.pack(">H", 1) + struct.pack(">HHI", 270, 2, 3)
                  + b"ab\0\0" + struct.pack(">I", 0))
        self.assertEqual(k2.tiff_description(io.BytesIO(inline)), "ab")
        self.assertIsNone(k2.tiff_description(io.BytesIO(b"not a tiff at all")))

    def test_svs_info(self):
        s = k2.svs_info(DESC)
        self.assertEqual((s["aperio"], s["mpp"], s["appmag"]), (True, 0.2527, 40.0))
        self.assertEqual(k2.svs_info(None), {"aperio": False, "mpp": None, "appmag": None})

    def test_fetch_svs_mpp(self):
        data = svs_zip()
        p = {"package": "pkg-1", "version": "v2", "name": "u_S-1_Seg_Masks_Features_v2.zip"}
        with tempfile.TemporaryDirectory() as tmp:
            rec = k2.fetch_svs_mpp(p, tmp, get=lambda url: io.BytesIO(data), pause=lambda s: None)
            self.assertEqual(os.listdir(tmp), [])
            bad = k2.fetch_svs_mpp(p, tmp, get=t1.FakeHTTP404(), pause=lambda s: None)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["svs_members"], 1)
        self.assertEqual(rec["mpp"], 0.2527)
        self.assertEqual(rec["appmag"], 40.0)
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"], "HTTP 404")
        self.assertIsNone(bad["mpp"])

    def test_svs_sample(self):
        order = [{"package": "a", "version": "v2"}, {"package": "b", "version": "v1"},
                 {"package": "c", "version": "v2"}, {"package": "d", "version": "v2"}]
        self.assertEqual([p["package"] for p in k2.svs_sample(order, 2)], ["a", "b", "c"])


class TestReaders2(unittest.TestCase):
    def test_col_key(self):
        self.assertEqual(k2.col_key("  Area (pixel^2) "), "area (pixel^2)")
        self.assertEqual(k2.col_key("Average  TBM Thickness"), "average tbm thickness")

    def test_analyse_dir2_v1(self):
        with tempfile.TemporaryDirectory() as d:
            fill_v1_dir(d)
            a = k2.analyse_dir2(d, "v1")
        self.assertEqual(a["errors"], [])
        self.assertEqual(a["xlsx"], 4)
        self.assertEqual(sorted(a["sheets"]), ["arts", "gloms", "tubs", "v1:peritubular_capillaries"])
        self.assertEqual(a["sheets"]["gloms"]["n_rows"], 2)
        self.assertEqual(a["sheets"]["tubs"]["n_rows"], 3)
        self.assertEqual(a["sheets"]["arts"]["n_rows"], 1)
        m = a["medians"]
        self.assertEqual(m["glom_area"], 1500.0)
        self.assertEqual(m["glom_area_px"], 24000.0)
        self.assertEqual(m["tbm"], 2.0)
        self.assertEqual(m["cell"], 8.0)
        self.assertEqual(m["lumen"], 0.2)
        self.assertEqual(a["area_ratio_median"], 0.0625)
        self.assertEqual(a["sheets"]["gloms"]["header"][1], "Area (pixel^2)")

    def test_analyse_dir2_v2(self):
        with tempfile.TemporaryDirectory() as d:
            t1.fill_package_dir(d)
            a = k2.analyse_dir2(d, "v2")
        self.assertEqual(a["errors"], [])
        self.assertEqual(a["medians"]["glom_area"], 2400.0)
        self.assertEqual(a["medians"]["tbm"], 10.0)
        self.assertNotIn("glom_area_px", a["medians"])
        self.assertIsNone(a["area_ratio_median"])
        self.assertTrue(a["readme"]["ifta_note"])


def med_records(n1, n2, v1, v2, f1="tbm", f2="tbm"):
    return ([{"version": "v1", "analysis": {"medians": {f1: v1}}} for _ in range(n1)]
            + [{"version": "v2", "analysis": {"medians": {f2: v2}}} for _ in range(n2)])


def svs_recs():
    return ([{"version": "v2", "ok": True, "mpp": 0.2527, "appmag": 40.0} for _ in range(12)]
            + [{"version": "v1", "ok": True, "mpp": 0.2527, "appmag": 40.0} for _ in range(3)]
            + [{"version": "v1", "ok": True, "mpp": None, "appmag": None},
               {"version": "v1", "ok": False, "mpp": None, "appmag": None}])


class TestSummaries(unittest.TestCase):
    def test_version_ratio2(self):
        r = k2.version_ratio2(med_records(10, 10, 1.25, 5.0), "tbm", "tbm", 1, 0.25)
        self.assertEqual(r["raw_ratio"], 4.0)
        self.assertAlmostEqual(r["converted_ratio"], 1.0)
        self.assertIsNone(k2.version_ratio2(med_records(9, 10, 1.25, 5.0), "tbm", "tbm", 1, 0.25)["raw_ratio"])
        self.assertIsNone(k2.version_ratio2(med_records(10, 10, 1.25, 5.0), "tbm", "tbm", 1, None)["converted_ratio"])
        ps = k2.version_ratio2(med_records(10, 10, 400000.0, 410000.0, "glom_area_px", "glom_area"),
                               "glom_area", "glom_area_px", None, None)
        self.assertAlmostEqual(ps["raw_ratio"], 1.025)
        self.assertIsNone(ps["converted_ratio"])
        self.assertEqual(ps["v1"]["feature"], "glom_area_px")

    def test_area_ratio_summary(self):
        recs = ([{"version": "v1", "analysis": {"area_ratio_median": 0.0625}} for _ in range(10)]
                + [{"version": "v2", "analysis": {"area_ratio_median": 1.0}},
                   {"version": "v1", "analysis": None}])
        s = k2.area_ratio_summary(recs)
        self.assertEqual(s["packages"], 10)
        self.assertEqual(s["median"], 0.0625)
        self.assertEqual(s["implied_mpp"], 0.25)

    def test_mpp_summary(self):
        m = k2.mpp_summary(svs_recs())
        self.assertEqual((m["sampled"], m["downloaded"], m["with_mpp"]), (17, 16, 15))
        self.assertEqual((m["v2"]["packages"], m["v2"]["median"]), (12, 0.2527))
        self.assertEqual(m["v1"]["packages"], 3)
        self.assertEqual(m["appmag"], [{"appmag": 40.0, "packages": 15}, {"appmag": None, "packages": 1}])
        self.assertEqual(m["all"]["distinct"], [{"mpp": 0.2527, "packages": 15}])

    def test_participant_table2(self):
        recs = [{"participants": ["p1"], "version": "v2",
                 "analysis": {"sheets": {"tubs": {"n_rows": 25}}, "values": {"tbm": [4.0], "lumen": [0.2]}}},
                {"participants": ["p2"], "version": "v1",
                 "analysis": {"sheets": {"tubs": {"n_rows": 25}}, "values": {"tbm": [1.0]}}}]
        pt = k2.participant_table2(recs, 0.25)
        self.assertEqual(pt["p1"]["conv"]["tbm"], [1.0])
        self.assertEqual(pt["p1"]["conv"]["lumen"], [0.2])
        self.assertEqual(pt["p1"]["raw"]["tbm"], [4.0])
        self.assertEqual(pt["p2"]["conv"]["tbm"], [1.0])
        self.assertEqual(k2.participant_table2(recs, None)["p1"]["conv"]["tbm"], [])


class TestTiv2(unittest.TestCase):
    def test_load_descriptor(self):
        rows = [TIV_ROW,
                '"open","","pdf","Pathology","1 MB","u8_readme.pdf","pkg-u","Pathology Descriptor Scoring","","",""',
                '"controlled","","xlsx","Pathology","1 MB","u7_x.xlsx","pkg-v","Pathology Descriptor Scoring","","",""']
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "desc.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join([t1.HEADER] + rows) + "\n")
            got = k2.load_descriptor(path)
        self.assertEqual(got, [{"package": "pkg-t", "name": "u9_KPMP TIV Descriptor Scores 10.12.2026.xlsx",
                                "listed": "469 kB"}])

    def test_tiv_scores(self):
        sheets = {"Notes": [["About"]],
                  "Scores": [["KPMP TIV"], ["Participant ID", "Consensus Complete", kc.ATROPHY_SCORE],
                             ["1-1", "Y", "5.0"], ["1-2", "N", "1"]]}
        scores, info = k2.tiv_scores(sheets)
        self.assertEqual(info["sheet"], "Scores")
        self.assertEqual(info["sheet_names"], ["Notes", "Scores"])
        self.assertEqual(info["header"], ["Participant ID", "Consensus Complete", kc.ATROPHY_SCORE])
        self.assertEqual(info["usable"], 1)
        self.assertEqual(scores["1-1"][kc.ATROPHY_SCORE], 5.0)
        none, info2 = k2.tiv_scores({"Notes": [["About"]]})
        self.assertEqual(none, {})
        self.assertNotIn("header", info2)
        self.assertEqual(k2.tiv_sheet({"Data Table": [["x"]], "Other": [["Participant ID"]]}), "Data Table")


class TestGrade2(unittest.TestCase):
    def _res(self, analysed=20, area_median=0.0625):
        good = {"n": 40, "rho": 0.3, "p_one_sided": 0.01}
        return {"census": {"listed": 20, "analysed": analysed},
                "mpp": k2.mpp_summary(svs_recs()),
                "area_ratio": {"packages": 10, "median": area_median, "implied_mpp": area_median ** 0.5},
                "unit_checks": {
                    "tbm": k2.version_ratio2(med_records(10, 10, 1.25, 5.0), "tbm", "tbm", 1, 0.25),
                    "glom_area": k2.version_ratio2(med_records(10, 10, 100.0, 1600.0, "glom_area", "glom_area"),
                                                   "glom_area", "glom_area", 2, 0.25),
                    "pixel_scale": k2.version_ratio2(med_records(10, 10, 400000.0, 410000.0, "glom_area_px",
                                                                 "glom_area"), "glom_area", "glom_area_px", None,
                                                     None)},
                "agreement": {"P7_lumen_vs_abnormal_lumen": {"conv": good},
                              "P8_tbm_vs_atrophy": {"conv": {"n": 40, "rho": 0.3, "p_one_sided": 0.2}},
                              "P9_cell_vs_injury_other": {"conv": {"n": 40, "rho": -0.2, "p_one_sided": 0.02}}}}

    def test_grade2(self):
        g = k2.grade2(self._res())
        self.assertEqual(g["status"], "complete")
        for k in ("S1_svs_mpp", "U1_v1_area_microns", "U2_pixel_scale", "U3_mpp_agree", "P2_tbm_raw_ratio",
                  "P3_tbm_converted_ratio", "P4_glom_area_raw_ratio", "P5_glom_area_converted_ratio",
                  "P7_lumen_vs_abnormal_lumen", "P9_cell_vs_injury_other"):
            self.assertEqual(g[k], "pass", k)
        self.assertEqual(g["P8_tbm_vs_atrophy"], "fail")
        px = k2.grade2(self._res(area_median=1.0))
        self.assertEqual(px["U1_v1_area_microns"], "fail")
        self.assertEqual(px["U3_mpp_agree"], "fail")
        mixed = self._res()
        mixed["mpp"] = k2.mpp_summary(svs_recs() + [{"version": "v2", "ok": True, "mpp": 0.5, "appmag": 20.0}])
        self.assertEqual(k2.grade2(mixed)["S1_svs_mpp"], "fail")
        part = k2.grade2(self._res(analysed=10))
        self.assertEqual(part["status"], "incomplete")
        self.assertEqual(part["S1_svs_mpp"], "pending")


class TestMain2Offline(unittest.TestCase):
    def test_main_from_cache(self):
        rows = [
            '"open","","tif xml xlsx svs md","Pathology","11.8 MB","u1_S-1904-008128_Seg_Masks_Features_v2.zip",'
            '"pkg-1","Segmentation Masks & Pathomics Vectors","","34-10050",""',
            '"open","","tif xml xlsx svs md","Pathology","128 MB","u2_S-2311-011607_Seg_Masks_Features.zip",'
            '"pkg-2","Segmentation Masks & Pathomics Vectors","","30-11154",""',
        ]
        tiv = t1.make_xlsx({"Data Table": [["Participant ID", "Consensus Complete", kc.ATROPHY_SCORE],
                                           ["34-10050", "Y", "5.0"], ["30-11154", "Y", "10.0"]]})
        zdata = svs_zip()
        calls = []

        def get(url):
            calls.append(url)
            if "/pkg-t/" in url:
                return io.BytesIO(tiv)
            if "/pkg-1/" in url or "/pkg-2/" in url:
                return io.BytesIO(zdata)
            raise AssertionError("unexpected url " + url)

        with tempfile.TemporaryDirectory() as d:
            csv_path, desc_path = os.path.join(d, "list.csv"), os.path.join(d, "desc.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("\n".join([t1.HEADER] + rows) + "\n")
            with open(desc_path, "w", encoding="utf-8") as f:
                f.write("\n".join([t1.HEADER, TIV_ROW]) + "\n")
            data, out = os.path.join(d, "data"), os.path.join(d, "out")
            t1.fill_package_dir(os.path.join(data, "kpmp-census", "pkg-1"))
            fill_v1_dir(os.path.join(data, "kpmp-census", "pkg-2"))
            for pkg in ("pkg-1", "pkg-2"):
                with open(os.path.join(data, "kpmp-census", pkg, "record.json"), "w", encoding="utf-8") as f:
                    json.dump({"ok": True, "size_ok": True, "download": {"ok": True, "bytes": 1},
                               "members": [], "kept": []}, f)
            self.assertEqual(k2.main(["--file-list", csv_path, "--descriptor-list", desc_path, "--out-dir", out,
                                      "--data-dir", data, "--permutations", "20"],
                                     get=get, pause=lambda s: None), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "progress.jsonl"), encoding="utf-8") as f:
                progress = f.read().splitlines()
            self.assertTrue(os.path.exists(os.path.join(data, "kpmp-census", "tiv", "pkg-t.xlsx")))
        self.assertEqual(res["census"], {"listed": 2, "analysed": 2, "cached": 2, "downloaded_this_run": 0})
        self.assertEqual((res["mpp"]["sampled"], res["mpp"]["with_mpp"]), (2, 2))
        self.assertIsNone(res["mpp_hat"])
        self.assertEqual(res["tiv"]["usable"], 2)
        self.assertEqual(res["tiv_file"]["listed"], "469 kB")
        self.assertEqual(res["participants"]["with_tiv"], 2)
        self.assertEqual(res["area_ratio"]["packages"], 1)
        self.assertEqual(res["area_ratio"]["median"], 0.0625)
        self.assertIn("tubs", res["describe"]["sheets"]["v1"])
        g = res["grades"]
        self.assertEqual(g["status"], "complete")
        for k in ("S1_svs_mpp", "U1_v1_area_microns", "P2_tbm_raw_ratio", "P8_tbm_vs_atrophy"):
            self.assertEqual(g[k], "untestable", k)
        self.assertEqual(len(progress), 4)
        self.assertEqual(len(calls), 3)
        for row in res["packages"]:
            self.assertNotIn("participants", row)


if __name__ == "__main__":
    unittest.main()
