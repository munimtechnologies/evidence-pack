# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/compare.py (stage-3 grading) and glom.kept_areas. Invented numbers only: no KPMP value
appears here."""
import json
import os
import tempfile
import unittest

from kidney import compare, glom


def full():
    return {
        "slide01": {"d": 10, "d_areas_um2": [3000.0, 5000.0], "k": 12, "k_gs": 1, "k_areas_um2": [4000.0, 6000.0],
                    "floor_applied": True},
        "slide03": {"d": 30, "d_areas_um2": [4000.0], "k": 28, "k_gs": 2, "k_areas_um2": [5000.0],
                    "floor_applied": True},
        "slide04": {"d": 5, "d_areas_um2": [2500.0], "k": 20, "k_gs": 0, "k_areas_um2": [3000.0],
                    "floor_applied": True},
        "slide05": {"d": 50, "d_areas_um2": [6000.0], "k": 45, "k_gs": 1, "k_areas_um2": [7000.0],
                    "floor_applied": True},
    }


class TestRules(unittest.TestCase):
    def test_tolerance(self):
        self.assertEqual(compare.tolerance(4), 3.0)
        self.assertEqual(compare.tolerance(12), 3.0)
        self.assertEqual(compare.tolerance(20), 5.0)

    def test_within(self):
        self.assertTrue(compare.within(10, 12))
        self.assertFalse(compare.within(16, 12))
        self.assertTrue(compare.within(25, 20))
        self.assertFalse(compare.within(26, 20))
        self.assertFalse(compare.within(None, 3))
        self.assertFalse(compare.within(3, None))

    def test_shifted(self):
        self.assertEqual(compare.shifted(), [("slide01", "slide03"), ("slide03", "slide04"),
                                             ("slide04", "slide05"), ("slide05", "slide01")])

    def test_plan_constants(self):
        self.assertEqual(compare.SLIDES, ("slide01", "slide03", "slide04", "slide05"))
        self.assertEqual(compare.C2_RANGE, (0.80, 1.25))
        self.assertEqual(compare.C3_RANGE, (0.70, 1.43))
        self.assertEqual(compare.C1_NEEDED, 3)
        self.assertEqual(compare.MIN_AREA_UM2, glom.MIN_AREA_UM2)


class TestCountK(unittest.TestCase):
    def test_floor(self):
        got = compare.count_k([("glom", 1000), ("gs", 400), ("glom", 50)], mask_mpp=2.0)
        self.assertEqual(got, {"k": 1, "k_gs": 0, "floor_applied": True, "k_areas_um2": [4000.0]})

    def test_no_floor(self):
        got = compare.count_k([("glom", 1000), ("gs", 400), ("glom", 50)])
        self.assertEqual(got, {"k": 3, "k_gs": 1, "floor_applied": False, "k_areas_um2": None})

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            compare.count_k([("tubule", 10)])


class TestGrade(unittest.TestCase):
    def test_full(self):
        g = compare.grade(full())
        self.assertTrue(g["complete"])
        self.assertEqual(g["c1"]["within"], 3)
        self.assertTrue(g["c1"]["held"])
        self.assertTrue(g["c1"]["informative"])
        self.assertEqual(g["c4"]["shifted_within"], 0)
        self.assertTrue(g["c4"]["held"])
        self.assertEqual(g["c2"]["ratio"], 0.905)
        self.assertTrue(g["c2"]["held"])
        self.assertEqual(g["c3"]["ratio"], 0.8)
        self.assertTrue(g["c3"]["held"])
        self.assertEqual(g["k_floor_applied"], "yes")
        self.assertEqual(g["gs_note"], {"reported": True, "closer_to": "K minus globally sclerotic"})
        compare.check_aggregate(g)

    def test_alike_slides_make_c1_uninformative(self):
        s = {n: {"d": 10, "k": 10, "k_gs": 0, "d_areas_um2": [3000.0], "k_areas_um2": None, "floor_applied": False}
             for n in compare.SLIDES}
        g = compare.grade(s)
        self.assertTrue(g["c1"]["held"])
        self.assertEqual(g["c4"]["shifted_within"], 4)
        self.assertFalse(g["c4"]["held"])
        self.assertFalse(g["c1"]["informative"])
        self.assertFalse(g["c3"]["graded"])
        self.assertEqual(g["k_floor_applied"], "no")
        self.assertFalse(g["gs_note"]["reported"])

    def test_incomplete(self):
        s = full()
        del s["slide04"]
        g = compare.grade(s)
        self.assertFalse(g["complete"])
        self.assertEqual(g["c1"]["within"], 3)
        self.assertTrue(g["c1"]["held"])
        self.assertIsNone(g["c1"]["informative"])
        for c in ("c2", "c3", "c4"):
            self.assertFalse(g[c]["graded"])

    def test_c3_needs_k_areas_and_c2_bounds(self):
        s = full()
        s["slide05"]["k_areas_um2"] = None
        s["slide05"]["floor_applied"] = False
        s["slide05"]["d"] = 40
        g = compare.grade(s)
        self.assertFalse(g["c3"]["graded"])
        self.assertEqual(g["k_floor_applied"], "mixed")
        self.assertEqual(g["c2"]["ratio"], 0.81)
        self.assertTrue(g["c2"]["held"])
        s["slide05"]["d"] = 39          # 84 / 105 = 0.80 exactly: the bounds are inclusive
        g = compare.grade(s)
        self.assertEqual(g["c2"]["ratio"], 0.8)
        self.assertTrue(g["c2"]["held"])
        s["slide05"]["d"] = 38          # 83 / 105 = 0.7905
        g = compare.grade(s)
        self.assertEqual(g["c2"]["ratio"], 0.79)
        self.assertFalse(g["c2"]["held"])

    def test_c3_needs_d_areas(self):
        s = full()
        s["slide01"]["d_areas_um2"] = None
        self.assertFalse(compare.grade(s)["c3"]["graded"])

    def test_check_aggregate(self):
        with self.assertRaises(ValueError):
            compare.check_aggregate({"x": "slide01"})
        with self.assertRaises(ValueError):
            compare.check_aggregate({"x": "abc"}, extra=("abc",))
        self.assertEqual(compare.check_aggregate({"x": 1}), {"x": 1})


class TestIO(unittest.TestCase):
    def test_d_side_and_merge(self):
        doc = {"rows": [{"slide": "abc", "ok": True, "glomeruli": 3, "areas_um2": [2100.0, 2200.0, 2300.0]},
                        {"slide": "xyz", "ok": False}]}
        d = compare.d_side(doc, {"abc": "slide01"})
        self.assertEqual(d, {"slide01": {"d": 3, "d_areas_um2": [2100.0, 2200.0, 2300.0]}})
        m = compare.merge(d, {"slide01": {"k": 4, "k_gs": 0, "floor_applied": False, "k_areas_um2": None},
                              "slide03": {"k": 9}})
        self.assertEqual(m["slide01"]["d"], 3)
        self.assertEqual(m["slide01"]["k"], 4)
        self.assertEqual(m["slide03"], {"k": 9})

    def test_main_writes_aggregate_only(self):
        s = full()
        glom_doc = {"rows": [{"slide": "w" + n[-2:], "ok": True, "glomeruli": s[n]["d"],
                              "areas_um2": s[n]["d_areas_um2"]} for n in compare.SLIDES]}
        names = {"w" + n[-2:]: n for n in compare.SLIDES}
        k = {n: {f: s[n][f] for f in ("k", "k_gs", "k_areas_um2", "floor_applied")} for n in compare.SLIDES}
        with tempfile.TemporaryDirectory() as t:
            paths = {}
            for key, obj in (("glom", glom_doc), ("k", k), ("names", names)):
                paths[key] = os.path.join(t, key + ".json")
                with open(paths[key], "w", encoding="utf-8") as f:
                    json.dump(obj, f)
            out = os.path.join(t, "compare.json")
            rc = compare.main(["--glom", paths["glom"], "--k", paths["k"], "--names", paths["names"],
                               "--out", out])
            with open(out, encoding="utf-8") as f:
                text = f.read()
        self.assertEqual(rc, 0)
        got = json.loads(text)
        self.assertEqual(got["c1"]["within"], 3)
        self.assertEqual(got["c3"]["ratio"], 0.8)
        for n in compare.SLIDES:
            self.assertNotIn(n, text)
        self.assertNotIn("w01", text)


class TestGlomAreas(unittest.TestCase):
    def test_kept_areas(self):
        # glom 0.1.1 added kept_areas; later versions keep it unchanged, so the version is not pinned here
        # (a pin to "0.1.1" broke this test when glom 0.2.0 added object positions).
        self.assertGreaterEqual(tuple(int(p) for p in glom.CODE_VERSION.split(".")), (0, 1, 1))
        self.assertEqual(glom.kept_areas([1000, 2000, 10], 1.5), [2250.0, 4500.0])
        self.assertEqual(glom.kept_areas([], 1.5), [])
        s = glom.summarize_regions([1000, 2000, 10], 1.5)
        self.assertEqual(len(glom.kept_areas([1000, 2000, 10], 1.5)), s["glomeruli"])


if __name__ == "__main__":
    unittest.main()
