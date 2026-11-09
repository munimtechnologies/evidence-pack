# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/compare3b.py (stage-3b grading). Invented numbers only: no KPMP value appears here."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from kidney import compare3b

KNS = [4, 10, 16, 24, 36, 52, 74, 104, 146, 205, 288, 404]   # far enough apart that no shifted pair is within


def fixture():
    names = compare3b.plan_names()
    out = {}
    for i, (name, kns) in enumerate(zip(names, KNS)):
        d = 600 if i == 11 else kns
        out[name] = {"d": d, "d_areas_um2": [3000.0], "k": kns + 1, "k_gs": 1, "floor_applied": True,
                     "k_areas_um2": [2500.0, 4000.0], "k_areas_by_kind": {"glom": [4000.0], "gs": [2500.0]}}
    return out


class TestHelpers(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(compare3b.N_PLANNED, 12)
        self.assertEqual(compare3b.MIN_COMPLETE, 10)
        self.assertEqual(compare3b.B1_RANGE, (0.80, 1.25))
        self.assertEqual(compare3b.B6_RANGE, (0.70, 1.43))
        self.assertEqual(compare3b.B3_MARGIN, 2)
        self.assertEqual(compare3b.GS_MIN, 5)
        self.assertEqual(compare3b.B5_MIN_RHO, 0.50)
        names = compare3b.plan_names()
        self.assertEqual((len(names), names[0], names[11]), (12, "slide3b01", "slide3b12"))

    def test_needed_b2(self):
        self.assertEqual([compare3b.needed_b2(n) for n in (12, 11, 10, 3)], [8, 8, 7, 2])

    def test_cyclic_shifts(self):
        self.assertEqual(compare3b.cyclic_shift_counts([10, 50, 100], [10, 50, 100]), [0, 0])
        self.assertEqual(compare3b.cyclic_shift_counts([10, 50, 100], [50, 100, 10]), [0, 3])

    def test_ranks_and_spearman(self):
        self.assertEqual(compare3b.ranks([3, 1, 3, 2]), [3.5, 1.0, 3.5, 2.0])
        self.assertEqual(compare3b.spearman([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertEqual(compare3b.spearman([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertIsNone(compare3b.spearman([1, 1, 1], [1, 2, 3]))
        self.assertIsNone(compare3b.spearman([1, 2], [1, 2]))


class TestGrade(unittest.TestCase):
    def test_full(self):
        g = compare3b.grade_b(fixture())
        self.assertEqual((g["planned"], g["complete"], g["gate"]), (12, 12, True))
        self.assertEqual(g["b1"]["ratio"], 1.144)            # 1559 / 1363
        self.assertTrue(g["b1"]["held"])
        self.assertEqual((g["b2"]["within"], g["b2"]["of"], g["b2"]["needed"]), (11, 12, 8))
        self.assertTrue(g["b2"]["held"])
        self.assertTrue(g["b2"]["informative"])
        self.assertEqual((g["b3"]["shift_mean_within"], g["b3"]["shift_max_within"]), (0, 0))
        self.assertTrue(g["b3"]["held"])
        self.assertEqual(g["b4"]["ratio_to_all_k"], 1.134)   # 1559 / 1375; 184 < 196, so closer to all of K
        self.assertFalse(g["b4"]["held"])
        self.assertEqual(g["b5"]["rho"], 1.0)
        self.assertTrue(g["b5"]["held"])
        self.assertEqual(g["b6"]["ratio"], 0.75)
        self.assertTrue(g["b6"]["held"])
        self.assertEqual(g["gs_share_of_k"], 0.009)          # 12 / 1375
        self.assertEqual(g["held"], 5)

    def test_gate(self):
        s = fixture()
        for name in compare3b.plan_names()[:3]:
            del s[name]
        g = compare3b.grade_b(s)
        self.assertEqual((g["complete"], g["gate"]), (9, False))
        for b in compare3b.PREDICTIONS:
            self.assertFalse(g[b]["graded"])

    def test_ten_complete_is_enough(self):
        s = fixture()
        s["slide3b01"]["k"] = None
        del s["slide3b02"]
        g = compare3b.grade_b(s)
        self.assertEqual((g["complete"], g["gate"]), (10, True))
        self.assertEqual((g["b2"]["within"], g["b2"]["of"], g["b2"]["needed"]), (9, 10, 7))

    def test_alike_slides(self):
        s = {n: {"d": 10, "k": 11, "k_gs": 1, "d_areas_um2": None, "k_areas_by_kind": {"glom": None, "gs": None}}
             for n in compare3b.plan_names()}
        g = compare3b.grade_b(s)
        self.assertEqual(g["b1"]["ratio"], 1.0)
        self.assertTrue(g["b2"]["held"])
        self.assertEqual(g["b3"]["shift_mean_within"], 12)
        self.assertFalse(g["b3"]["held"])
        self.assertFalse(g["b2"]["informative"])
        self.assertTrue(g["b4"]["held"])
        self.assertEqual(g["b4"]["ratio_to_all_k"], 0.909)
        self.assertFalse(g["b5"]["graded"])
        self.assertFalse(g["b6"]["graded"])
        self.assertEqual(g["held"], 3)

    def test_b4_needs_five_sclerotic(self):
        s = fixture()
        for n in compare3b.plan_names()[:8]:
            s[n]["k"] -= 1
            s[n]["k_gs"] = 0
        g = compare3b.grade_b(s)
        self.assertFalse(g["b4"]["graded"])


class TestMain(unittest.TestCase):
    def test_writes_aggregate_only(self):
        s = fixture()
        glom_doc = {"rows": [{"slide": n, "ok": True, "glomeruli": r["d"], "areas_um2": r["d_areas_um2"]}
                             for n, r in s.items()]}
        k = {n: {f: r[f] for f in ("k", "k_gs", "floor_applied", "k_areas_um2", "k_areas_by_kind")}
             for n, r in s.items()}
        with tempfile.TemporaryDirectory() as t:
            gp, kp, op = (os.path.join(t, x) for x in ("glom.json", "k.json", "out.json"))
            for path, obj in ((gp, glom_doc), (kp, k)):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(obj, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = compare3b.main(["--glom", gp, "--k", kp, "--out", op])
            with open(op, encoding="utf-8") as f:
                text = f.read()
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(text)["b2"]["within"], 11)
        self.assertNotIn("slide3b", text)
        self.assertNotIn("slide3b", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
