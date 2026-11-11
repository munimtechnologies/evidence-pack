# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/compare6.py (stage 6 grading). Invented boxes only: no KPMP value appears here."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from kidney import compare6


def box(cx, cy, half):
    return [cx, cy, cx - half, cy - half, cx + half, cy + half, (2 * half) ** 2]


def make(n, ns_hits=3, far=0, far_label="ns", gs=True, gs_label="gs", spacing=10000.0):
    """Each slide: K = 4 non-sclerotic objects in a row and (if gs) 1 sclerotic one. D = the first `ns_hits`
    non-sclerotic objects (called ns), the sclerotic one (called gs_label) and `far` objects far from everything
    (called far_label)."""
    out = {}
    for i in range(n):
        base = spacing * i
        kns = [box(base + 300 * j, 0.0, 50) for j in range(4)]
        kgs = [box(base + 1200, 0.0, 50)] if gs else []
        ds = [box(base + 300 * j, 0.0, 50) for j in range(ns_hits)]
        cls = ["ns"] * ns_hits
        if gs:
            ds.append(box(base + 1200, 0.0, 50))
            cls.append(gs_label)
        for f in range(far):
            ds.append(box(base + 400 * f, 5000.0, 50))
            cls.append(far_label)
        out["test6%02d" % (i + 1)] = {"d_objects": ds, "d_classes": cls, "k_objects": {"glom": kns, "gs": kgs}}
    return out


def arm_a(n=10, **kw):
    """Stage 5-like: finds everything sclerotic, misses one normal glomerulus per slide, two extra GS calls."""
    return make(n, ns_hits=3, far=2, far_label="gs", **kw)


def arm_b(n=10, **kw):
    return make(n, ns_hits=4, **kw)


class TestGrade(unittest.TestCase):
    def test_all_hold(self):
        g = compare6.grade(arm_a(), arm_b(), 1500, 1500)
        self.assertEqual((g["planned"], g["complete_both"], g["gate"]), (12, 10, True))
        self.assertEqual(g["q1"]["value"], 1.0)
        self.assertEqual(g["q2"]["value"], 0.667)
        self.assertEqual((g["q3"]["value"], g["q4"]["value"], g["q5"]["value"]), (1.0, 1.0, 1.0))
        self.assertEqual((g["q6"]["value"], g["q6"]["gs_share_d"], g["q6"]["gs_share_k"]), (0.0, 0.2, 0.2))
        self.assertEqual(g["q7"]["value"], 0.333)
        self.assertEqual((g["q8"]["shift_mean_recall_a"], g["q8"]["shift_mean_recall_b"]), (0.0, 0.0))
        for q in compare6.PREDICTIONS:
            self.assertTrue(g[q]["held"], q)
        self.assertTrue(g["q3"]["informative"])
        self.assertEqual(g["held"], 8)
        self.assertTrue(g["gs_floor_met"])
        a = g["arm_a"]
        self.assertEqual((a["precision"], a["share_d"], a["gs_call_precision"], a["recall_all"]),
                         (0.667, 0.5, 0.333, 0.8))
        self.assertEqual((a["gs_called_gs"], a["ns_called_ns"], a["median_iou"]), (1.0, 1.0, 1.0))
        self.assertEqual(g["arm_b"]["iou_0_3"], {"recall_gs": 1.0, "recall_ns": 1.0, "precision": 1.0})

    def test_no_improvement(self):
        g = compare6.grade(arm_a(), arm_a(), 1500, 1500)
        held = [q for q in compare6.PREDICTIONS if g[q]["held"]]
        self.assertEqual(held, ["q1", "q2", "q4", "q8"])
        self.assertEqual((g["q3"]["value"], g["q5"]["value"], g["q6"]["value"], g["q7"]["value"]),
                         (0.667, 0.75, 0.3, 0.0))
        self.assertEqual(g["held"], 4)

    def test_no_sclerotic(self):
        g = compare6.grade(arm_a(gs=False), arm_b(gs=False), 1500, 1500)
        for q in ("q1", "q4", "q6"):
            self.assertFalse(g[q]["graded"], q)
        self.assertFalse(g["gs_floor_met"])
        self.assertEqual((g["q2"]["value"], g["q3"]["value"], g["q7"]["value"]), (0.6, 1.0, 0.4))
        self.assertEqual(g["held"], 5)
        self.assertIsNone(g["arm_b"]["gs_call_precision"])

    def test_gates(self):
        g = compare6.grade(arm_a(9), arm_b(9), 1500, 1500)
        self.assertEqual((g["complete_both"], g["gate"], g["held"]), (9, False, 0))
        for q in compare6.PREDICTIONS:
            self.assertFalse(g[q]["graded"])
        g = compare6.grade(arm_a(12), arm_b(12), 1500, 299)
        self.assertFalse(g["gate"])
        self.assertEqual(g["q1"]["why"], "fewer than 300 training steps in an arm")
        self.assertFalse(compare6.grade(arm_a(12), arm_b(12), None, 1500)["gate"])
        self.assertTrue(compare6.grade(arm_a(12), arm_b(12), 300, 300)["gate"])

    def test_only_slides_complete_for_both_arms_count(self):
        a, b = arm_a(12), arm_b(12)
        del b["test612"]
        b["test611"]["d_classes"] = b["test611"]["d_classes"][:-1]
        g = compare6.grade(a, b, 1500, 1500)
        self.assertEqual((g["complete_both"], g["gate"]), (10, True))
        self.assertEqual(compare6.common_slides(a, b, compare6.plan_names6())[-1], "test610")

    def test_control_fails_when_slides_overlap(self):
        g = compare6.grade(arm_a(spacing=0.0), arm_b(spacing=0.0), 1500, 1500)
        self.assertEqual((g["q8"]["shift_mean_recall_a"], g["q8"]["shift_mean_recall_b"]), (0.8, 1.0))
        self.assertFalse(g["q8"]["held"])
        self.assertFalse(g["q1"]["informative"])
        self.assertEqual(g["held"], 7)

    def test_plan_names(self):
        names = compare6.plan_names6()
        self.assertEqual((names[0], names[-1], len(names)), ("test601", "test612", 12))


class TestMain(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        a, b = arm_a(), arm_b()

        def det(slides):
            return {"train_steps": 1500,
                    "rows": [{"slide": s, "ok": True, "objects": r["d_objects"], "classes": r["d_classes"]}
                             for s, r in slides.items()] + [{"slide": "test611", "ok": False}]}

        k_doc = {s: {"k": 5, "k_gs": 1, "k_objects": r["k_objects"]} for s, r in a.items()}
        with tempfile.TemporaryDirectory() as d:
            pa, pb, pk, po = (os.path.join(d, f) for f in ("detA.json", "detB.json", "k6.json", "compare6.json"))
            for path, doc in ((pa, det(a)), (pb, det(b)), (pk, k_doc)):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compare6.main(["--det-a", pa, "--det-b", pb, "--k", pk, "--out", po])
            self.assertEqual(code, 0)
            with open(po, encoding="utf-8") as f:
                doc = json.load(f)
        self.assertEqual((doc["complete_both"], doc["held"], doc["train_steps_a"]), (10, 8, 1500))
        self.assertNotIn("test6", buf.getvalue())
        self.assertNotIn("test6", json.dumps(doc))


if __name__ == "__main__":
    unittest.main()
