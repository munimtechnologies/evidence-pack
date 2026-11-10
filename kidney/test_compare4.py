# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/compare4.py (stage 4 object matching). Invented boxes only: no KPMP value appears here."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from kidney import compare4


def box(cx, cy, half):
    return [cx, cy, cx - half, cy - half, cx + half, cy + half, (2 * half) ** 2]


def make_slides(n, d_shift=0.0, gs=True, spacing=10000.0):
    """Each slide: 4 non-sclerotic K objects in a row, 1 sclerotic K object, and 4 D objects: three on the first
    three non-sclerotic objects (moved by d_shift in x) and one far from everything."""
    out = {}
    for i in range(n):
        base = spacing * i
        kns = [box(base + 300 * j, 0.0, 50) for j in range(4)]
        kgs = [box(base + 1200, 0.0, 50)] if gs else []
        ds = [box(base + 300 * j + d_shift, 0.0, 50) for j in range(3)] + [box(base, 5000.0, 50)]
        out["slide3b%02d" % (i + 1)] = {"d_objects": ds, "k_objects": {"glom": kns, "gs": kgs}}
    return out


class TestGeometry(unittest.TestCase):
    def test_iou(self):
        self.assertAlmostEqual(compare4.box_iou(box(0, 0, 10), box(10, 0, 10)), 1 / 3.0)
        self.assertAlmostEqual(compare4.box_iou(box(0, 0, 10), box(5, 0, 10)), 0.6)
        self.assertEqual(compare4.box_iou(box(0, 0, 10), box(0, 0, 10)), 1.0)
        self.assertEqual(compare4.box_iou(box(0, 0, 10), box(20, 0, 10)), 0.0)
        self.assertEqual(compare4.box_iou(box(0, 0, 10), box(100, 100, 10)), 0.0)

    def test_match_one_to_one(self):
        self.assertEqual(compare4.match([box(0, 0, 10), box(5, 0, 10)], [box(0, 0, 10)]), [(0, 0, 1.0)])
        self.assertEqual(compare4.match([box(0, 0, 10)], [box(5, 0, 10), box(0, 0, 10)]), [(0, 1, 1.0)])
        self.assertEqual(compare4.match([box(0, 0, 10), box(0, 0, 10)], [box(0, 0, 10)]), [(0, 0, 1.0)])

    def test_match_threshold(self):
        self.assertEqual(compare4.match([box(0, 0, 10)], [box(10, 0, 10)]), [])
        got = compare4.match([box(0, 0, 10)], [box(10, 0, 10)], min_iou=0.3)
        self.assertEqual([(i, j) for i, j, _ in got], [(0, 0)])
        self.assertEqual(compare4.match([], [box(0, 0, 10)]), [])

    def test_tally(self):
        t = compare4.tally([box(0, 0, 10), box(100, 0, 10), box(500, 0, 10)],
                           [box(0, 0, 10), box(300, 0, 10)], [box(102, 0, 10)])
        self.assertEqual((t["d"], t["d_hit"], t["ns"], t["ns_hit"], t["gs"], t["gs_hit"]), (3, 2, 2, 1, 1, 1))
        self.assertEqual((t["dx"], t["dy"]), ([0, 2], [0, 0]))


class TestGrade(unittest.TestCase):
    def test_all_hold(self):
        g = compare4.grade_o(make_slides(10))
        self.assertEqual((g["complete"], g["gate"]), (10, True))
        self.assertEqual(g["o1"]["recall_ns"], 0.75)
        self.assertTrue(g["o1"]["held"])
        self.assertTrue(g["o1"]["informative"])
        self.assertEqual(g["o2"]["precision"], 0.75)
        self.assertTrue(g["o2"]["held"])
        self.assertEqual(g["o3"]["recall_gap"], 0.75)
        self.assertTrue(g["o3"]["held"])
        self.assertEqual(g["o4"]["recall_gs"], 0.0)
        self.assertTrue(g["o4"]["held"])
        self.assertEqual(g["o5"]["shift_mean_recall"], 0.0)
        self.assertTrue(g["o5"]["held"])
        self.assertEqual((g["o6"]["median_dx_um"], g["o6"]["median_dy_um"]), (0.0, 0.0))
        self.assertTrue(g["o6"]["held"])
        self.assertEqual(g["held"], 6)
        self.assertEqual(g["exploratory"]["gs_share_of_k"], 0.2)
        self.assertEqual(g["exploratory"]["median_iou_matched"], 1.0)

    def test_offset_fails_alignment_only(self):
        g = compare4.grade_o(make_slides(10, d_shift=10.0))
        self.assertTrue(g["o1"]["held"])
        self.assertEqual(g["o6"]["median_dx_um"], -10.0)
        self.assertFalse(g["o6"]["held"])
        self.assertEqual(g["held"], 5)

    def test_gate(self):
        g = compare4.grade_o(make_slides(9))
        self.assertEqual((g["complete"], g["gate"]), (9, False))
        for o in compare4.PREDICTIONS:
            self.assertFalse(g[o]["graded"])

    def test_incomplete_slides_do_not_count(self):
        s = make_slides(12)
        s["slide3b11"]["d_objects"] = None
        del s["slide3b12"]["k_objects"]["gs"]
        g = compare4.grade_o(s)
        self.assertEqual((g["complete"], g["gate"]), (10, True))

    def test_sclerotic_gate(self):
        g = compare4.grade_o(make_slides(10, gs=False))
        self.assertFalse(g["o3"]["graded"])
        self.assertFalse(g["o4"]["graded"])
        self.assertTrue(g["o1"]["held"])
        self.assertIsNone(g["exploratory"]["recall_gs_at_0_5"])

    def test_control_fails_when_slides_overlap(self):
        g = compare4.grade_o(make_slides(10, spacing=0.0))
        self.assertEqual(g["o5"]["shift_mean_recall"], 0.6)
        self.assertFalse(g["o5"]["held"])
        self.assertFalse(g["o1"]["informative"])
        self.assertTrue(g["o1"]["held"])


class TestMain(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        slides = make_slides(10)
        glom_doc = {"rows": [{"slide": s, "ok": True, "glomeruli": 4, "objects": r["d_objects"]}
                             for s, r in slides.items()] + [{"slide": "slide3b11", "ok": False}]}
        k_doc = {s: {"k": 5, "k_gs": 1, "k_objects": r["k_objects"]} for s, r in slides.items()}
        with tempfile.TemporaryDirectory() as d:
            gp, kp, op = (os.path.join(d, f) for f in ("glom.json", "k.json", "compare4.json"))
            with open(gp, "w", encoding="utf-8") as f:
                json.dump(glom_doc, f)
            with open(kp, "w", encoding="utf-8") as f:
                json.dump(k_doc, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compare4.main(["--glom", gp, "--k", kp, "--out", op])
            self.assertEqual(code, 0)
            with open(op, encoding="utf-8") as f:
                doc = json.load(f)
        self.assertEqual((doc["complete"], doc["held"]), (10, 6))
        self.assertNotIn("slide3b", buf.getvalue())
        self.assertNotIn("slide3b", json.dumps(doc))

    def test_d_side_needs_objects(self):
        doc = {"rows": [{"slide": "a", "ok": True, "objects": []}, {"slide": "b", "ok": True},
                        {"slide": "c", "ok": False, "objects": []}]}
        self.assertEqual(compare4.d_objects_side(doc), {"a": {"d_objects": []}})


if __name__ == "__main__":
    unittest.main()
