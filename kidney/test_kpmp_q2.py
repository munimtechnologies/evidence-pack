# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_q2 (no network: downloads are faked)."""
import io
import json
import os
import tempfile
import unittest
from collections import Counter

from kidney import kpmp_q2 as q2
from kidney import test_kpmp_census as t1
from kidney import test_kpmp_census3 as t3

CLIN_ROW = '"open","","csv","Clinical","212 kB","u5_20260930_OpenAccessClinicalData.csv","pkg-c","","","",""'
CLIN_CSV = ("Participant ID,Diabetes History,Baseline eGFR (ml/min/1.73m2),Proteinuria (mg) (Binned)\n"
            "34-10050,Yes,56.5,>=1000 mg/g cr\n30-11154,No,80.1,<150 mg/g cr\n")


def synthetic_table():
    ex_v1 = {"values": {"glom_area": [100.0] * 6, "tbm": [1.0] * 25}, "n": Counter({"gloms": 6, "tubs": 25}),
             "books": {"gloms", "tubs"}, "errors": []}
    ex_v2 = {"values": {"glom_area": [400.0] * 6, "tbm": [4.0] * 25},
             "n": Counter({"gloms": 6, "s_gloms": 2, "tubs": 25}), "books": {"gloms", "s_gloms", "tubs"}, "errors": []}
    ex_c = {"values": {"glom_area": [1.0] * 4}, "n": Counter({"gloms": 4}), "books": {"gloms"}, "errors": []}
    return [("a", "v1", ex_v1), ("b", "v2", ex_v2), ("c", "v2", ex_c)]


class TestClinical(unittest.TestCase):
    def test_code_value(self):
        self.assertEqual(q2.code_value("diabetes", "Yes"), 1)
        self.assertIsNone(q2.code_value("diabetes", "Don't know"))
        self.assertEqual(q2.code_value("egfr", " 56.6 "), 56.6)
        self.assertEqual(q2.code_value("age_bin", "60-69 Years"), 60)
        self.assertIsNone(q2.code_value("age_bin", "Unknown"))
        self.assertEqual(q2.code_value("proteinuria", ">=1000 mg/g cr"), 4)
        self.assertEqual(q2.code_value("albuminuria", "<30 mg/g cr"), 1)
        self.assertIsNone(q2.code_value("a1c", ""))


class TestFeatures(unittest.TestCase):
    def test_extract_v1(self):
        with tempfile.TemporaryDirectory() as d:
            t3.fill_v1_caps(d)
            ex = q2.extract_package(d, "v1")
        self.assertEqual(ex["errors"], [])
        self.assertEqual(ex["books"], {"arts", "gloms", "tubs"})
        self.assertEqual((ex["n"]["gloms"], ex["n"]["tubs"], ex["n"]["arts"]), (2, 3, 1))
        v = ex["values"]
        self.assertEqual(v["glom_area"], [1000.0, 2000.0])
        self.assertEqual(v["mesangial_fraction"], [0.2, 0.15])
        self.assertEqual(v["tbm"], [1.0, 2.0, 3.0])
        self.assertEqual(v["arterial_area"], [100.0])

    def test_extract_v2(self):
        with tempfile.TemporaryDirectory() as d:
            t1.fill_package_dir(d)
            ex = q2.extract_package(d, "v2")
        self.assertEqual(ex["books"], {"arts", "gloms", "tubs"})
        self.assertEqual((ex["n"]["gloms"], ex["n"]["tubs"], ex["n"]["arts"]), (2, 3, 0))
        self.assertEqual(ex["values"]["glom_area"], [1600.0, 3200.0])
        self.assertEqual(ex["values"]["mesangial_fraction"], [0.25, 0.25])
        self.assertEqual(ex["values"]["tbm"], [8.0, 12.0, 10.0])

    def test_participant_table(self):
        pt = q2.participant_table(synthetic_table(), 0.5)
        self.assertEqual(q2.feature_value(pt["b"], "glom_area", "conv"), 100.0)
        self.assertEqual(q2.feature_value(pt["b"], "glom_area", "raw"), 400.0)
        self.assertEqual(q2.feature_value(pt["b"], "tbm", "conv"), 2.0)
        self.assertEqual(q2.feature_value(pt["a"], "glom_area", "conv"), 100.0)
        self.assertIsNone(q2.feature_value(pt["c"], "glom_area", "conv"))
        self.assertEqual(q2.feature_value(pt["a"], "sclerotic_share"), 0.0)
        self.assertFalse(pt["a"]["scl_ok"])
        self.assertEqual(q2.feature_value(pt["b"], "sclerotic_share"), 0.25)
        self.assertTrue(pt["b"]["scl_ok"])
        self.assertIsNone(q2.feature_value(pt["c"], "sclerotic_share"))
        self.assertIsNone(q2.feature_value(pt["a"], "lumen", "raw"))
        self.assertEqual(q2.participant_table(synthetic_table(), None)["b"]["conv"]["glom_area"], [])
        clin = {"a": {"diabetes": 0, "age_bin": 60}, "b": {"diabetes": 1, "age_bin": None}, "c": {"diabetes": 1}}
        self.assertEqual(q2.rows_for(pt, clin, "glom_area", "diabetes"),
                         [("v1", 100.0, 0, 60), ("v2", 100.0, 1, None)])
        self.assertEqual(q2.rows_for(pt, clin, "sclerotic_share", "diabetes", require_scl_ok=True),
                         [("v2", 0.25, 1, None)])


class TestStats(unittest.TestCase):
    def test_pooled(self):
        rows = [("v1", float(i), float(i), None) for i in range(1, 11)]
        t = q2.stat_test(rows, 1, 200, 1, False)
        self.assertEqual((t["n"], t["strata"], t["rho"]), (10, [10], 1.0))
        self.assertEqual(t["p"], 1 / 201)
        self.assertNotIn("p", q2.stat_test(rows, 1, 0, 1, False))

    def test_stratified(self):
        rows = ([("v1", float(i), float(i), None) for i in range(1, 11)]
                + [("v2", float(i), float(-i), None) for i in range(1, 13)])
        t = q2.stat_test(rows, 1, 0, 1, True)
        self.assertEqual(t["strata"], [10, 12])
        self.assertAlmostEqual(t["rho"], -1 / 11)
        small = rows[:10] + [("v2", float(i), float(-i), None) for i in range(1, 6)]
        s = q2.stat_test(small, 1, 0, 1, True)
        self.assertEqual((s["n"], s["strata"], s["rho"]), (10, [10], 1.0))
        self.assertEqual(q2.stat_test([], 1, 100, 1, True), {"n": 0, "strata": [], "rho": None})

    def test_holm_floor_grade(self):
        adj = q2.holm([0.01, 0.04, 0.03])
        for got, want in zip(adj, [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(got, want)
        arm = [("v1", 1.0, 0, None)] * 30
        self.assertFalse(q2.floor_ok(arm + [("v1", 1.0, 1, None)] * 29, "binary"))
        self.assertTrue(q2.floor_ok(arm + [("v1", 1.0, 1, None)] * 30, "binary"))
        self.assertFalse(q2.floor_ok([("v1", 1.0, 2.0, None)] * 29, "numeric"))
        self.assertTrue(q2.floor_ok([("v1", 1.0, 2.0, None)] * 30, "numeric"))
        self.assertEqual(q2.grade_test({"rho": -0.3, "p": 0.01}, -1), "pass")
        self.assertEqual(q2.grade_test({"rho": 0.3, "p": 0.01}, -1), "fail")
        self.assertEqual(q2.grade_test({"rho": None}, 1), "untestable")

    def test_control_mode(self):
        self.assertEqual(q2.control_mode("glom_area", {"P5_glom_area_converted_ratio": "pass"}, 0.25), "pooled")
        self.assertEqual(q2.control_mode("glom_area", {"P5_glom_area_converted_ratio": "fail"}, 0.25), "stratified")
        self.assertEqual(q2.control_mode("glom_area", {"P5_glom_area_converted_ratio": "pass"}, None), "stratified")
        self.assertEqual(q2.control_mode("tbm", {"P3_tbm_converted_ratio": "pass"}, 0.25), "pooled")
        self.assertEqual(q2.control_mode("mesangial_fraction", {}, None), "pooled")
        self.assertEqual(q2.control_mode("sclerotic_share", {}, None), "pooled")

    def test_split_halves(self):
        ids = ["p%d" % i for i in range(10)]
        e, c = q2.split_halves(ids)
        self.assertEqual((len(e), len(c)), (5, 5))
        self.assertEqual(e | c, set(ids))
        self.assertEqual(q2.split_halves(list(reversed(ids))), (e, c))

    def test_discovery(self):
        ptable, clin = {}, {}
        for i in range(1, 41):
            pid = "p%02d" % i
            ptable[pid] = {"versions": {"v2"}, "n": Counter({"tubs": 25}), "raw": {"tbm": [float(i)] * 25},
                           "conv": {"tbm": [float(i)] * 25}, "scl": [0, 0], "scl_ok": True}
            clin[pid] = {"age_bin": i}
        res = q2.discovery(ptable, clin, 200)
        self.assertEqual(res["halves"], [20, 20])
        self.assertEqual(len(res["pairs"]), 58)
        self.assertEqual((res["carried"], res["confirmed"]), (1, 1))
        hit = [r for r in res["pairs"] if r["carried"]][0]
        self.assertEqual((hit["feature"], hit["clinical"], hit["direction"]), ("tbm", "age_bin", 1))
        self.assertEqual(hit["holm_p"], 1 / 201)


class TestMainQ2Offline(unittest.TestCase):
    def test_main(self):
        rows = [
            '"open","","tif xml xlsx svs md","Pathology","11.8 MB","u1_S-1904-008128_Seg_Masks_Features_v2.zip",'
            '"pkg-1","Segmentation Masks & Pathomics Vectors","","34-10050",""',
            '"open","","tif xml xlsx svs md","Pathology","128 MB","u2_S-2311-011607_Seg_Masks_Features.zip",'
            '"pkg-2","Segmentation Masks & Pathomics Vectors","","30-11154",""',
        ]
        calls = []

        def get(url):
            calls.append(url)
            if "/pkg-c/" in url:
                return io.BytesIO(CLIN_CSV.encode("utf-8"))
            raise AssertionError("unexpected url " + url)

        with tempfile.TemporaryDirectory() as d:
            seg, clin_list, census = (os.path.join(d, n) for n in ("seg.csv", "clin.csv", "census.json"))
            with open(seg, "w", encoding="utf-8") as f:
                f.write("\n".join([t1.HEADER] + rows) + "\n")
            with open(clin_list, "w", encoding="utf-8") as f:
                f.write("\n".join([t1.HEADER, CLIN_ROW]) + "\n")
            with open(census, "w", encoding="utf-8") as f:
                json.dump({"prereg": "x", "mpp_hat": 0.25, "grades": {"P3_tbm_converted_ratio": "pass",
                                                                      "P5_glom_area_converted_ratio": "fail"}}, f)
            data, out = os.path.join(d, "data"), os.path.join(d, "out")
            t1.fill_package_dir(os.path.join(data, "kpmp-census", "pkg-1"))
            t3.fill_v1_caps(os.path.join(data, "kpmp-census", "pkg-2"))
            for pkg in ("pkg-1", "pkg-2"):
                with open(os.path.join(data, "kpmp-census", pkg, "record.json"), "w", encoding="utf-8") as f:
                    json.dump({"ok": True}, f)
            self.assertEqual(q2.main(["--file-list", seg, "--clinical-list", clin_list, "--census-results", census,
                                      "--out-dir", out, "--data-dir", data, "--permutations", "20"],
                                     get=get, pause=lambda s: None), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                text = f.read()
        res = json.loads(text)
        self.assertEqual((res["packages"]["read"], res["packages"]["listed"]), (2, 2))
        self.assertEqual(res["clinical"]["participants"], 2)
        self.assertEqual(res["clinical"]["coded"]["egfr"], 2)
        self.assertIn("Sex", res["clinical"]["missing_columns"])
        self.assertEqual(res["participants"]["with_clinical"], 2)
        self.assertEqual(res["participants"]["by_version"], {"v1": 1, "v2": 1})
        self.assertEqual(res["participants"]["v1_without_sclerotic_book"], 1)
        self.assertEqual(res["controls"]["C1_glom_area_vs_diabetes"]["graded_on"], "stratified")
        self.assertEqual(res["controls"]["C4_tbm_vs_egfr"]["graded_on"], "pooled")
        g = res["grades"]
        self.assertEqual(g["status"], "complete")
        for key, _, _, _ in q2.CONTROLS:
            self.assertEqual(g[key], "untestable", key)
        self.assertEqual((res["discovery"]["halves"], res["discovery"]["carried"]), ([1, 1], 0))
        self.assertEqual(len(calls), 1)
        self.assertNotIn("34-10050", text)
        self.assertNotIn("30-11154", text)


if __name__ == "__main__":
    unittest.main()
