# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_twinrel on synthetic slides built like test_kpmp_twins: two serial
sections a fixed shift apart. Twin values are set by construction (identical for mesangial fraction, cell
thickness and luminal fraction; reversed for TBM thickness), so the grades are known in advance. Workbook
fixtures use the raw v2 sheet and column names the census jobs recorded."""
import csv
import json
import os
import random
import tempfile
import unittest

from kidney import kpmp_census as kc
from kidney import kpmp_twinrel as kr
from kidney.test_kpmp_tbm0 import V2_GLOMS, V2_TUBS, write_xlsx
from kidney.test_kpmp_twins import SEG_HEADER, two_sections

N, T = 30, 40
ARTS = ["x1", "x2", "y1", "y2", "Arterial Area"]


def box(r, c, h, w):
    return [r - h / 2, r + h / 2, c - w / 2, c + w / 2]


def slide_workbook(path):
    """N glomerulus, N artery and T tubule pairs (object 2p in section 1, 2p + 1 its copy in section 2),
    plus 5 unrepeated glomeruli."""
    objs = two_sections(n=N, extra=5, tubules=T)
    rows = {"gloms": [V2_GLOMS], "s_gloms": [V2_GLOMS], "tubs": [V2_TUBS], "arts": [ARTS]}
    for k, (r, c, h, w) in enumerate(objs["gloms"]):
        mf = (k // 2 + 1) / (N + 2) if k < 2 * N else 0.5
        rows["gloms"].append(box(r, c, h, w) + [h * w, mf * h * w, mf])
    for k, (r, c, h, w) in enumerate(objs["tubs"]):
        p = k // 2
        tbm = 1.0 + (p if k % 2 == 0 else T - 1 - p)
        rows["tubs"].append(box(r, c, h, w) + [tbm, 5.0 + p, (p + 1) / (T + 2)])
    for r, c, h, w in objs["arts"]:
        rows["arts"].append(box(r, c, h, w) + [h * w])
    write_xlsx(path, rows)


class TestPairs(unittest.TestCase):
    def test_pair_up_closest_first(self):
        objs = [(0, 0, 100, 100, {}), (10, 1000, 100, 100, {}), (0, 1005, 100, 100, {}), (0, 1000, 300, 300, {})]
        self.assertEqual(kr.pair_up(objs, (0, 1000)), [(0, 2)])

    def test_null_partners_skip_twin_region_and_other_sizes(self):
        objs = [(0, 0, 100, 100, {}), (0, 1000, 100, 100, {}), (0, -1000, 100, 100, {}),
                (5000, 5000, 100, 100, {}), (9000, 9000, 300, 300, {})]
        self.assertEqual(kr.null_partners(objs, [(0, 1)], (0, 1000), random.Random(0)), [(0, 3)])

    def test_odds_ratio(self):
        self.assertEqual(kr.odds_ratio([10, 0, 0, 10]), 441.0)
        self.assertEqual(kr.odds_ratio([1, 1, 1, 1]), 1.0)

    def test_tval(self):
        self.assertIsNone(kr.tval(0.0, "log"))
        self.assertIsNone(kr.tval(None, "raw"))
        self.assertEqual(kr.tval(0.0, "raw"), 0.0)
        self.assertEqual(kr.tval(1.0, "log"), 0.0)


class TestGrade(unittest.TestCase):
    def test_gates(self):
        keys = set(kr.GRADED) | {"R5_zero_tbm_concordance"}
        g = kr.grade({}, {}, 50, None)
        self.assertEqual({k for k in keys if g[k] == "pending"}, keys)
        g = kr.grade({}, {}, 50, "fail")
        self.assertEqual({k for k in keys if g[k] == "untestable"}, keys)
        self.assertIn("T3 fail", g["status"])
        g = kr.grade({}, {}, 5, "pass")
        self.assertEqual({k for k in keys if g[k] == "untestable"}, keys)


class TestWorkbook(unittest.TestCase):
    def test_objects_reads_values_and_x_as_row(self):
        d = tempfile.mkdtemp()
        write_xlsx(os.path.join(d, "S-2006-000001_features_v2.xlsx"),
                   {"gloms": [V2_GLOMS, [100, 300, 1000, 1400, 5.0, 2.0, 0.4]], "s_gloms": [V2_GLOMS],
                    "tubs": [V2_TUBS, [0, 10, 0, 20, 0, 7.5, 0.2]], "arts": [ARTS]})
        objs = kr.objects(d)
        self.assertEqual(objs["gloms"], [(200.0, 1200.0, 200.0, 400.0,
                                          {"Mesangial Fraction": 0.4, "Area": 5.0, "Mesangial Area": 2.0})])
        self.assertEqual(objs["tubs"], [(5.0, 10.0, 10.0, 20.0, {"Average TBM Thickness": 0.0,
                                                                 "Average Cell Thickness": 7.5,
                                                                 "Luminal Fraction": 0.2})])
        self.assertEqual(objs["s_gloms"], [])
        self.assertEqual(objs["arts"], [])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data")
        pdir = os.path.join(self.data, "kpmp-census", "pkg-a")
        os.makedirs(pdir)
        slide_workbook(os.path.join(pdir, "S-2006-000001_features_v2.xlsx"))
        with open(os.path.join(pdir, "record.json"), "w", encoding="utf-8") as f:
            json.dump({"ok": True}, f)
        self.seg = os.path.join(self.tmp, "seg.csv")
        with open(self.seg, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SEG_HEADER)
            for pkg, name in (("pkg-a", "a_S-2006-000001_Seg_Masks_Features_v2.zip"),
                              ("pkg-b", "b_S-2006-000002_Seg_Masks_Features_v2.zip")):
                w.writerow(["open", "", "tif xml xlsx svs md", "Pathology", "70 MB", name, pkg, kc.STRATEGY, "",
                            "30-10000", ""])

    def run_main(self, t3):
        twins = os.path.join(self.tmp, "twins-%s.json" % t3)
        with open(twins, "w", encoding="utf-8") as f:
            json.dump({"grades": {"T3_controls": t3}}, f)
        out = os.path.join(self.tmp, "out-%s" % t3)
        self.assertEqual(kr.main(["--file-list", self.seg, "--twins-results", twins, "--data-dir", self.data,
                                  "--out-dir", out, "--boot", "20", "--min-repeat-slides", "1",
                                  "--min-pairs", "20"]), 0)
        with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_main_end_to_end(self):
        res = self.run_main("pass")
        self.assertEqual(res["packages"], {"read": 1, "not_cached": 1, "listed_v2": 2})
        self.assertEqual(res["repeat_slides"], 1)
        self.assertEqual(res["sheets"]["gloms"], {"objects": 65, "twin_pairs": N, "null_pairs": N})
        self.assertEqual(res["sheets"]["tubs"], {"objects": 2 * T, "twin_pairs": T, "null_pairs": T})
        self.assertAlmostEqual(res["features"]["gloms|Mesangial Fraction"]["rho_twin"], 1.0, places=9)
        self.assertAlmostEqual(res["features"]["tubs|Average TBM Thickness"]["rho_twin"], -1.0, places=9)
        self.assertAlmostEqual(res["features"]["tubs|Luminal Fraction"]["rho_twin"], 1.0, places=9)
        self.assertEqual(res["zero_tbm"]["twin_table"], [0, 0, 0, T])
        self.assertEqual(res["grades"], {"R1_glom_mesangial_fraction": "pass", "R2_tub_tbm_thickness": "fail",
                                         "R3_tub_luminal_fraction": "pass", "R4_tub_cell_thickness": "pass",
                                         "R5_zero_tbm_concordance": "untestable", "status": "complete"})
        self.assertNotIn("pkg-a", json.dumps(res))

    def test_main_detector_not_validated(self):
        res = self.run_main("fail")
        self.assertEqual(res["twins_T3"], "fail")
        self.assertEqual({v for k, v in res["grades"].items() if k != "status"}, {"untestable"})


if __name__ == "__main__":
    unittest.main()
