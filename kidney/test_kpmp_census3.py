# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_census3 (no network: downloads are faked)."""
import io
import json
import os
import tempfile
import unittest
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_census3 as k3
from kidney import test_kpmp_census as t1
from kidney import test_kpmp_census2 as t2


def fill_v1_caps(path):
    """A v1 package whose sheets are named "Features" (pass 2 asked for "features" and read nothing)."""
    os.makedirs(path, exist_ok=True)
    books = {
        "final_combined_features_non_globally_sclerotic_gloms.xlsx": {
            "Features": [["Nuclei Number", "Area (pixel^2)", "Radius (pixel)", "Area", "Mesangial Area",
                          "Mesangial Fraction", "compartment_id"],
                         [5, 16000, 70, 1000, 200, 0.2, 1], [6, 32000, 100, 2000, 300, 0.15, 2]],
            "Bounding Boxes": [["x1", "y1", "x2", "y2", "compartment_ids"], [0, 0, 1, 1, 1]]},
        "final_combined_features_tubules.xlsx": {
            "Features": [["Nuclei Number", "Area (pixel^2)", "Average TBM Thickness", "Average Cell Thickness",
                          "Luminal Fraction"],
                         [1, 500, 1.0, 7.0, 0.1], [2, 600, 2.0, 8.0, 0.3], [3, 700, 3.0, 9.0, 0.2]]},
        "final_combined_features_muscular_vessels.xlsx": {"Features": [["Luminal ratio", "Arterial Area"],
                                                                       [0.5, 100]]},
    }
    for fn, sheets in books.items():
        with open(os.path.join(path, fn), "wb") as f:
            f.write(t1.make_xlsx(sheets))
    with open(os.path.join(path, "S-2311-011607_PAS_1of2.ome.xml"), "wb") as f:
        f.write(t1.ome_xml(channels=("tubules", "glomeruli")))
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
        f.write("README for KPMP package download.\n")


class TestReader3(unittest.TestCase):
    def test_pass2_reader_misses_capitalised_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            fill_v1_caps(d)
            a2 = k2.analyse_dir2(d, "v1")
        self.assertEqual(a2["sheets"]["tubs"]["n_rows"], 0)
        self.assertNotIn("tbm", a2["medians"])

    def test_analyse_dir3_v1(self):
        seen = Counter()
        with tempfile.TemporaryDirectory() as d:
            fill_v1_caps(d)
            a = k3.analyse_dir3(d, "v1", seen)
        self.assertEqual(a["errors"], [])
        self.assertEqual(a["xlsx"], 3)
        self.assertEqual(sorted(a["sheets"]), ["arts", "gloms", "tubs"])
        self.assertEqual(a["sheets"]["tubs"]["n_rows"], 3)
        self.assertEqual(a["sheets"]["gloms"]["n_rows"], 2)
        m = a["medians"]
        self.assertEqual(m["glom_area"], 1500.0)
        self.assertEqual(m["glom_area_px"], 24000.0)
        self.assertEqual(m["tbm"], 2.0)
        self.assertEqual(m["cell"], 8.0)
        self.assertEqual(m["lumen"], 0.2)
        self.assertEqual(a["area_ratio_median"], 0.0625)
        self.assertEqual(k3.sheet_names_report(seen), [
            {"version": "v1", "kind": "matched", "names": "Features", "books": 3},
            {"version": "v1", "kind": "names", "names": "Bounding Boxes|Features", "books": 1},
            {"version": "v1", "kind": "names", "names": "Features", "books": 2}])

    def test_book_without_features_sheet(self):
        seen = Counter()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "final_combined_features_tubules.xlsx")
            with open(path, "wb") as f:
                f.write(t1.make_xlsx({"Sheet1": [["Average TBM Thickness"], [1.0]]}))
            got = k3.book_sheets3(path, "final_combined_features_tubules.xlsx", "v1", seen)
        self.assertEqual(got, {"tubs": []})
        self.assertEqual(seen[("v1", "matched", "")], 1)

    def test_v2_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            t1.fill_package_dir(d)
            a2, a3 = k2.analyse_dir2(d, "v2"), k3.analyse_dir3(d, "v2")
        self.assertEqual(a3["medians"], a2["medians"])
        self.assertEqual(a3["medians"]["tbm"], 10.0)


class TestTail(unittest.TestCase):
    def test_quantile(self):
        self.assertAlmostEqual(k3.quantile([5, 1, 3, 2, 4], 0.9), 4.6)
        self.assertAlmostEqual(k3.quantile([5, 1, 3, 2, 4], 0.1), 1.4)
        self.assertEqual(k3.quantile([5, 1, 3, 2, 4], 0.5), 3)
        self.assertEqual(k3.quantile([7], 0.9), 7)
        self.assertIsNone(k3.quantile([], 0.9))

    def test_agreement_q(self):
        ptable, scores = {}, {}
        for i, (top, score) in enumerate(((10, 0.0), (20, 5.0), (30, 10.0), (40, 20.0), (50, 30.0)), 1):
            ptable["p%d" % i] = {"versions": {"v2"}, "n_tubs": 25, "raw": {"tbm": [1, 2, top]}}
            scores["p%d" % i] = {kc.ATROPHY_SCORE: score}
        ptable["p6"] = {"versions": {"v1"}, "n_tubs": 25, "raw": {"tbm": [1, 2, 99]}}
        scores["p6"] = {kc.ATROPHY_SCORE: 0.0}
        ptable["p7"] = {"versions": {"v2"}, "n_tubs": 5, "raw": {"tbm": [1, 2, 99]}}
        scores["p7"] = {kc.ATROPHY_SCORE: 0.0}
        ptable["p8"] = {"versions": {"v2"}, "n_tubs": 25, "raw": {"tbm": [1, 2, 99]}}
        a = k3.agreement_q(ptable, scores, "tbm", kc.ATROPHY_SCORE, 1, 0.9, {"v2"}, 200, 1)
        self.assertEqual(a["n"], 5)
        self.assertEqual(a["rho"], 1.0)
        self.assertTrue(0 < a["p_one_sided"] <= 1)
        med = kc.agreement(ptable, scores, "tbm", kc.ATROPHY_SCORE, 1, "raw", {"v2"}, 0)
        self.assertEqual(med["n"], 5)
        self.assertIsNone(med["rho"])
        self.assertEqual(k3.agreement_q(ptable, scores, "tbm", kc.ATROPHY_SCORE, 1, 0.9, {"v1"}, 0)["n"], 1)


class TestGrade3(unittest.TestCase):
    def _res(self, analysed=20):
        good = {"n": 40, "rho": 0.3, "p_one_sided": 0.01}
        return {"census": {"listed": 20, "analysed": analysed},
                "mpp": k2.mpp_summary(t2.svs_recs()),
                "area_ratio": {"packages": 10, "median": 0.0625, "implied_mpp": 0.25},
                "unit_checks": {
                    "tbm": k2.version_ratio2(t2.med_records(10, 10, 1.25, 5.0), "tbm", "tbm", 1, 0.25),
                    "glom_area": k2.version_ratio2(t2.med_records(10, 10, 100.0, 1600.0, "glom_area", "glom_area"),
                                                   "glom_area", "glom_area", 2, 0.25),
                    "pixel_scale": k2.version_ratio2(t2.med_records(10, 10, 400000.0, 410000.0, "glom_area_px",
                                                                    "glom_area"), "glom_area", "glom_area_px",
                                                     None, None)},
                "agreement": {"P7_lumen_vs_abnormal_lumen": {"conv": good},
                              "P8_tbm_vs_atrophy": {"conv": good},
                              "P9_cell_vs_injury_other": {"conv": good},
                              "V7_lumen_vs_abnormal_lumen_v1": {"v1_only": good},
                              "V8_tbm_vs_atrophy_v1": {"v1_only": {"n": 20, "rho": 0.5, "p_one_sided": 0.01}},
                              "V9_cell_vs_injury_other_v1": {"v1_only": {"n": 40, "rho": 0.2, "p_one_sided": 0.01}},
                              "T7_lumen_p90_vs_abnormal_lumen": {"v2_only": good},
                              "T8_tbm_p90_vs_atrophy": {"v2_only": {"n": 40, "rho": 0.3, "p_one_sided": 0.2}},
                              "T9_cell_p10_vs_injury_other": {"v2_only": {"n": 40, "rho": -0.2,
                                                                          "p_one_sided": 0.02}}}}

    def test_grade3(self):
        g = k3.grade3(self._res())
        self.assertEqual(g["status"], "complete")
        self.assertEqual((g["S1_svs_mpp"], g["U1_v1_area_microns"], g["P3_tbm_converted_ratio"]),
                         ("pass", "pass", "pass"))
        self.assertEqual(g["V7_lumen_vs_abnormal_lumen_v1"], "pass")
        self.assertEqual(g["V8_tbm_vs_atrophy_v1"], "untestable")
        self.assertEqual(g["V9_cell_vs_injury_other_v1"], "fail")
        self.assertEqual(g["T7_lumen_p90_vs_abnormal_lumen"], "pass")
        self.assertEqual(g["T8_tbm_p90_vs_atrophy"], "fail")
        self.assertEqual(g["T9_cell_p10_vs_injury_other"], "pass")
        self.assertNotIn("P7_lumen_vs_abnormal_lumen", g)
        part = k3.grade3(self._res(analysed=10))
        self.assertEqual(part["status"], "incomplete")
        self.assertEqual((part["S1_svs_mpp"], part["V7_lumen_vs_abnormal_lumen_v1"]), ("pending", "pending"))


class TestMain3Offline(unittest.TestCase):
    def test_main_from_cache(self):
        rows = [
            '"open","","tif xml xlsx svs md","Pathology","11.8 MB","u1_S-1904-008128_Seg_Masks_Features_v2.zip",'
            '"pkg-1","Segmentation Masks & Pathomics Vectors","","34-10050",""',
            '"open","","tif xml xlsx svs md","Pathology","128 MB","u2_S-2311-011607_Seg_Masks_Features.zip",'
            '"pkg-2","Segmentation Masks & Pathomics Vectors","","30-11154",""',
        ]
        tiv = t1.make_xlsx({"Data Table": [["Participant ID", "Consensus Complete", kc.ATROPHY_SCORE],
                                           ["34-10050", "Y", "5.0"], ["30-11154", "Y", "10.0"]]})
        zdata = t2.svs_zip()
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
                f.write("\n".join([t1.HEADER, t2.TIV_ROW]) + "\n")
            data, out = os.path.join(d, "data"), os.path.join(d, "out")
            t1.fill_package_dir(os.path.join(data, "kpmp-census", "pkg-1"))
            fill_v1_caps(os.path.join(data, "kpmp-census", "pkg-2"))
            for pkg in ("pkg-1", "pkg-2"):
                with open(os.path.join(data, "kpmp-census", pkg, "record.json"), "w", encoding="utf-8") as f:
                    json.dump({"ok": True, "size_ok": True, "download": {"ok": True, "bytes": 1},
                               "members": [], "kept": []}, f)
            self.assertEqual(k3.main(["--file-list", csv_path, "--descriptor-list", desc_path, "--out-dir", out,
                                      "--data-dir", data, "--permutations", "20"],
                                     get=get, pause=lambda s: None), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(out, "progress.jsonl"), encoding="utf-8") as f:
                progress = f.read().splitlines()
        self.assertEqual(res["prereg"], k3.PREREG)
        self.assertEqual(res["census"], {"listed": 2, "analysed": 2, "cached": 2, "downloaded_this_run": 0})
        self.assertEqual(res["describe"]["sheets"]["v1"]["tubs"]["rows"], 3)
        self.assertEqual(res["area_ratio"]["packages"], 1)
        self.assertEqual(res["area_ratio"]["median"], 0.0625)
        self.assertIn({"version": "v1", "kind": "matched", "names": "Features", "books": 3}, res["sheet_names"])
        self.assertIn({"version": "v2", "kind": "names", "names": "arts|gloms|tubs", "books": 1}, res["sheet_names"])
        self.assertEqual(res["participants"]["by_version"], {"v1": 1, "v2": 1})
        self.assertEqual(res["agreement"]["T8_tbm_p90_vs_atrophy"]["v2_only"]["n"], 0)
        g = res["grades"]
        self.assertEqual(g["status"], "complete")
        for k in ("S1_svs_mpp", "U1_v1_area_microns", "V8_tbm_vs_atrophy_v1", "T8_tbm_p90_vs_atrophy"):
            self.assertEqual(g[k], "untestable", k)
        self.assertNotIn("P8_tbm_vs_atrophy", g)
        self.assertEqual(len(progress), 4)
        self.assertEqual(len(calls), 3)
        for row in res["packages"]:
            self.assertNotIn("participants", row)


if __name__ == "__main__":
    unittest.main()
