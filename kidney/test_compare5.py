# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/compare5.py (stage 5 grading). Invented boxes only: no KPMP value appears here."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from kidney import compare5


def box(cx, cy, half):
    return [cx, cy, cx - half, cy - half, cx + half, cy + half, (2 * half) ** 2]


def make_slides(n, gs=True, gs_label="gs", spacing=10000.0):
    """Each slide: 4 non-sclerotic K objects in a row and 1 sclerotic K object; D: three objects on the first three
    non-sclerotic ones (called ns), one on the sclerotic one (called gs_label) and one far from everything (ns)."""
    out = {}
    for i in range(n):
        base = spacing * i
        kns = [box(base + 300 * j, 0.0, 50) for j in range(4)]
        kgs = [box(base + 1200, 0.0, 50)] if gs else []
        ds = [box(base + 300 * j, 0.0, 50) for j in range(3)] + [box(base, 5000.0, 50)]
        cls = ["ns", "ns", "ns", "ns"]
        if gs:
            ds.append(box(base + 1200, 0.0, 50))
            cls.append(gs_label)
        out["slide3b%02d" % (i + 1)] = {"d_objects": ds, "d_classes": cls, "k_objects": {"glom": kns, "gs": kgs}}
    return out


class TestTally(unittest.TestCase):
    def test_tally(self):
        t = compare5.tally5([box(0, 0, 10), box(100, 0, 10), box(500, 0, 10)], ["gs", "gs", "ns"],
                            [box(0, 0, 10), box(300, 0, 10)], [box(102, 0, 10)])
        self.assertEqual([t[k] for k in compare5.KEYS], [3, 2, 2, 2, 1, 1, 1, 1, 0])


class TestGrade(unittest.TestCase):
    def test_all_hold(self):
        g = compare5.grade_p(make_slides(10), 1500)
        self.assertEqual((g["complete"], g["gate"]), (10, True))
        self.assertEqual(g["p1"]["recall_gs"], 1.0)
        self.assertEqual(g["p2"]["recall_ns"], 0.75)
        self.assertEqual(g["p3"]["precision"], 0.8)
        self.assertEqual((g["p4"]["gs_called_gs"], g["p4"]["ns_called_ns"]), (1.0, 1.0))
        self.assertEqual((g["p5"]["gs_share_d"], g["p5"]["gs_share_k"], g["p5"]["diff"]), (0.2, 0.2, 0.0))
        self.assertEqual(g["p6"]["shift_mean_recall"], 0.0)
        for p in compare5.PREDICTIONS:
            self.assertTrue(g[p]["held"], p)
        self.assertTrue(g["p1"]["informative"])
        self.assertEqual(g["held"], 6)
        ex = g["exploratory"]
        self.assertEqual(ex["recall_all_k"], 0.8)
        self.assertTrue(ex["both_classes_at_0_70"])
        self.assertEqual(ex["median_iou_matched"], 1.0)
        self.assertIsNone(ex["spearman_gs_share"])
        self.assertEqual(ex["slides_in_spearman"], 10)

    def test_wrong_class(self):
        g = compare5.grade_p(make_slides(10, gs_label="ns"), 1500)
        self.assertTrue(g["p1"]["held"])
        self.assertEqual(g["p4"]["gs_called_gs"], 0.0)
        self.assertFalse(g["p4"]["held"])
        self.assertEqual(g["p5"]["gs_share_d"], 0.0)
        self.assertEqual(g["p5"]["diff"], -0.2)
        self.assertFalse(g["p5"]["held"])
        self.assertEqual(g["held"], 4)

    def test_no_sclerotic(self):
        g = compare5.grade_p(make_slides(10, gs=False), 1500)
        for p in ("p1", "p4", "p5"):
            self.assertFalse(g[p]["graded"], p)
        self.assertTrue(g["p2"]["held"])
        self.assertEqual(g["p3"]["precision"], 0.75)
        self.assertFalse(g["p3"]["held"])
        self.assertFalse(g["exploratory"]["both_classes_at_0_70"])

    def test_gates(self):
        g = compare5.grade_p(make_slides(9), 1500)
        self.assertEqual((g["complete"], g["gate"]), (9, False))
        for p in compare5.PREDICTIONS:
            self.assertFalse(g[p]["graded"])
        g = compare5.grade_p(make_slides(12), 299)
        self.assertFalse(g["gate"])
        self.assertEqual(g["p1"]["why"], "fewer than 300 training steps")
        self.assertFalse(compare5.grade_p(make_slides(12), None)["gate"])
        self.assertTrue(compare5.grade_p(make_slides(12), 300)["gate"])

    def test_incomplete_slides_do_not_count(self):
        s = make_slides(12)
        s["slide3b11"]["d_classes"] = s["slide3b11"]["d_classes"][:-1]
        del s["slide3b12"]["k_objects"]["gs"]
        g = compare5.grade_p(s, 1500)
        self.assertEqual((g["complete"], g["gate"]), (10, True))

    def test_control_fails_when_slides_overlap(self):
        g = compare5.grade_p(make_slides(10, spacing=0.0), 1500)
        self.assertEqual(g["p6"]["shift_mean_recall"], 0.8)
        self.assertFalse(g["p6"]["held"])
        self.assertFalse(g["p1"]["informative"])
        self.assertEqual(g["held"], 5)


class TestMain(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        slides = make_slides(10)
        det = {"train_steps": 900,
               "rows": [{"slide": s, "ok": True, "objects": r["d_objects"], "classes": r["d_classes"]}
                        for s, r in slides.items()] + [{"slide": "slide3b11", "ok": False}]}
        k_doc = {s: {"k": 5, "k_gs": 1, "k_objects": r["k_objects"]} for s, r in slides.items()}
        with tempfile.TemporaryDirectory() as d:
            dp, kp, op = (os.path.join(d, f) for f in ("det5.json", "k.json", "compare5.json"))
            with open(dp, "w", encoding="utf-8") as f:
                json.dump(det, f)
            with open(kp, "w", encoding="utf-8") as f:
                json.dump(k_doc, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compare5.main(["--det", dp, "--k", kp, "--out", op])
            self.assertEqual(code, 0)
            with open(op, encoding="utf-8") as f:
                doc = json.load(f)
        self.assertEqual((doc["complete"], doc["held"], doc["train_steps"]), (10, 6, 900))
        self.assertNotIn("slide3b", buf.getvalue())
        self.assertNotIn("slide3b", json.dumps(doc))

    def test_det_side(self):
        doc = {"rows": [{"slide": "a", "ok": True, "objects": [], "classes": []}, {"slide": "b", "ok": True,
                                                                                    "objects": []},
                        {"slide": "c", "ok": False, "objects": [], "classes": []}]}
        self.assertEqual(compare5.det_side(doc), {"a": {"d_objects": [], "d_classes": []}})


if __name__ == "__main__":
    unittest.main()
