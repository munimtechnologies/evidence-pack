# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/d2.py on synthetic numbers only (no KPMP data). Made with AI agents (Claude) in MV2's name."""
import importlib.util
import json
import math
import os
import tempfile
import unittest

from kidney import anom, d2

HAS_NP = importlib.util.find_spec("numpy") is not None


def box(x0, y0, x1, y1):
    return [(x0 + x1) / 2.0, (y0 + y1) / 2.0, x0, y0, x1, y1, (x1 - x0) * (y1 - y0)]


B0, B1, B2 = box(0, 0, 10, 10), box(20, 20, 30, 30), box(50, 50, 60, 60)


def obj(group, lab, det, clipped, x=None):
    return {"group": group, "x": x if x is not None else [0.0], "det": det, "lab": lab, "clipped": clipped}


class TestLabels(unittest.TestCase):
    def test_match_classes(self):
        kobj = {"glom": [box(0, 0, 10, 10)], "gs": [box(21, 21, 31, 31)]}
        self.assertEqual(d2.kpmp_labels([B0, B1, B2], kobj), ["ns", "gs", None])

    def test_no_k(self):
        self.assertEqual(d2.kpmp_labels([B0, B1], None), [None, None])


class TestSplit(unittest.TestCase):
    def test_properties(self):
        pids = ["P%02d" % i for i in range(10)]
        ref, ev = d2.split(pids, ["P00", "P01", "ZZ"])
        self.assertEqual(len(ref), 5)  # 2 train + ceil(8 * 0.3) = 3
        self.assertEqual(len(ev), 5)
        self.assertEqual(sorted(ref + ev), pids)
        self.assertFalse(set(ref) & set(ev))
        self.assertIn("P00", ref)
        self.assertIn("P01", ref)
        self.assertNotIn("ZZ", ref)
        self.assertEqual(d2.split(list(reversed(pids)), ["P01", "P00"]), (ref, ev))


class TestCollect(unittest.TestCase):
    def test_collect(self):
        emb_doc = {"rows": [
            {"slide": "SLA", "ok": True, "objects": [B0, B1, B2], "classes": ["ns", "gs", "ns"],
             "emb": [[1.0], [2.0], None], "clipped": [False, True, False]},
            {"slide": "SLX", "ok": True, "objects": [B0], "classes": ["ns"], "emb": [[1.0]], "clipped": [False]},
            {"slide": "SLB", "ok": False}]}
        k_doc = {"SLA": {"k_objects": {"glom": [B0], "gs": [B1]}}}
        objs, skipped = d2.collect(emb_doc, k_doc, {"SLA": "PA", "SLB": "PB"}, "emb")
        self.assertEqual(objs, [{"group": "PA", "x": [1.0], "det": "ns", "lab": "ns", "clipped": False},
                                {"group": "PA", "x": [2.0], "det": "gs", "lab": "gs", "clipped": True}])
        self.assertEqual(skipped, {"no_group": 1, "no_vector": 1, "no_k": 0})


class TestShare(unittest.TestCase):
    def test_gs_share(self):
        a = B0
        k_doc = {"SLA": {"k_objects": {"glom": [a, a, a], "gs": [a]}}, "SLB": {"k_objects": {"glom": [a], "gs": []}},
                 "SLC": {"k_objects": None}, "SLD": {"k_objects": {"glom": [a], "gs": [a]}}}
        groups = {"SLA": "PA", "SLB": "PA", "SLC": "PB"}
        self.assertEqual(d2.gs_share(k_doc, groups), {"PA": 0.2})

    def test_ref_standardize(self):
        self.assertEqual(d2.ref_standardize([[1.0, 5.0], [3.0, 5.0]], [[4.0, 7.0]]), [[2.0, 0.0]])


class TestSide(unittest.TestCase):
    def setUp(self):
        spec = [("PA", "gs", "gs", False, 10), ("PA", "ns", "ns", False, 1), ("PA", "ns", "ns", False, 2),
                ("PB", "gs", "gs", False, 9), ("PB", "ns", "ns", False, 3), ("PB", "ns", "ns", False, 8),
                ("PC", "ns", "ns", False, 4), ("PC", "ns", "ns", False, 5), ("PC", "ns", "ns", True, 100),
                ("PR", "ns", "ns", False, 50), ("PA", None, "ns", False, 99), ("PB", "ns", "gs", False, 0.5)]
        self.objs = [obj(g, l, d, c) for g, l, d, c, _ in spec]
        self.scores = [float(s) for *_, s in spec]
        self.share = {"PA": 0.1, "PB": 0.2, "PC": 0.3}
        self.clin = {"PA": {"egfr": 50}, "PB": {"egfr": 40}, "PC": {"egfr": 30}}

    def run_side(self, min_gs=2):
        return d2.side(self.objs, self.scores, ["PA", "PB", "PC"], self.share, self.clin, n_perm=9, seed=11,
                       permille=500, min_gs=min_gs, min_eligible=2, min_field_n=99)

    def test_side(self):
        s = self.run_side()
        self.assertEqual(s["auroc_gs_vs_ns"], 1.0)
        self.assertAlmostEqual(s["top_concentration"], 2.0 / 3.0)
        self.assertEqual(s["burden_participants"], 3)
        self.assertEqual(s["fields"]["egfr"], {"n": 3, "graded": False})
        self.assertEqual(s["fields"]["proteinuria"], {"n": 0, "graded": False})

    def test_burden_excludes_det_gs_and_clipped(self):
        d_scores = [1.0, 2.0, 3.0, 8.0, 4.0, 5.0]
        d_groups = ["PA", "PA", "PB", "PB", "PC", "PC"]
        self.assertEqual(anom.burden(d_scores, d_groups, 500), {"PA": 0.0, "PB": 0.5, "PC": 1.0})

    def test_too_few_gs(self):
        self.assertIsNone(self.run_side(min_gs=3)["auroc_gs_vs_ns"])


class TestFields(unittest.TestCase):
    def test_field_tests(self):
        names = ["P%d" % i for i in range(1, 7)]
        bur = dict(zip(names, [0.0, 0.5, 1.0, 0.25, 0.75, 0.1]))
        share = dict(zip(names, [0.1, 0.4, 0.2, 0.3, 0.6, 0.5]))
        hyp = [1, 0, 1, 0, 1, 1]
        clin = {n: {"egfr": 7 - i, "hypertension": hyp[i - 1]} for i, n in enumerate(names, 1)}
        for n in names[:4]:
            clin[n]["diabetes"] = 1 if n in ("P1", "P3") else 0
        out = d2.field_tests(bur, share, clin, n_perm=50, seed=11, min_n=5)
        self.assertEqual(out["diabetes"], {"n": 4, "graded": False})
        self.assertEqual(out["proteinuria"], {"n": 0, "graded": False})
        x = [bur[n] for n in names]
        z = [share[n] for n in names]
        exp = {}
        for f, y in (("egfr", [6, 5, 4, 3, 2, 1]), ("hypertension", hyp)):
            r, p = anom.perm_p(x, y, z, 50, 11)
            self.assertEqual(out[f]["n"], 6)
            self.assertEqual(out[f]["graded"], r is not None)
            self.assertEqual(out[f].get("partial_rho"), r)
            if r is not None:
                exp[f] = p
        graded = [f for f in ("egfr", "hypertension") if f in exp]
        for f, a in zip(graded, anom.holm([exp[f] for f in graded])):
            self.assertEqual(out[f]["holm_p"], a)


class TestReadings(unittest.TestCase):
    @staticmethod
    def sides(a_emb, a_base, conc, holm_p):
        fields = {f: {"n": 0, "graded": False} for f in d2.FIELDS}
        fields["egfr"] = {"n": 60, "graded": True, "partial_rho": 0.3, "p": holm_p, "holm_p": holm_p}
        emb = {"auroc_gs_vs_ns": a_emb, "top_concentration": conc, "fields": fields}
        base = {"auroc_gs_vs_ns": a_base, "top_concentration": None, "fields": {}}
        return emb, base

    def test_pass(self):
        r = d2.readings(60, *self.sides(0.9, 0.8, 0.2, 0.01))
        self.assertEqual(r, {"g1": "pass", "r1": "pass", "r2": "pass", "r3": "pass", "informative": True})

    def test_fail(self):
        r = d2.readings(60, *self.sides(0.79, 0.76, 0.25, 0.2))
        self.assertEqual(r, {"g1": "fail", "r1": "fail", "r2": "fail", "r3": "fail", "informative": False})

    def test_not_graded(self):
        r = d2.readings(10, *self.sides(0.9, 0.8, 0.2, 0.01))
        self.assertEqual(set(r[k] for k in d2.READINGS), {"not graded"})
        self.assertFalse(r["informative"])
        r = d2.readings(60, *self.sides(None, 0.8, 0.2, 0.01))
        self.assertEqual((r["g1"], r["r1"], r["informative"]), ("not graded", "not graded", False))


@unittest.skipUnless(HAS_NP, "numpy not installed")
class TestScores(unittest.TestCase):
    def test_ref_scores(self):
        objs = [obj("PR", "ns", "ns", False, [0.0, 0.0]), obj("PR", "ns", "ns", False, [2.0, 0.0]),
                obj("PR", "ns", "ns", False, [0.0, 2.0]), obj("PR", "ns", "ns", False, [2.0, 2.0]),
                obj("PR", "gs", "gs", False, [100.0, 100.0]), obj("PR", "ns", "ns", True, [50.0, -50.0]),
                obj("PA", "ns", "ns", False, [1.0, 1.0]), obj("PA", "ns", "ns", False, [5.0, 5.0])]
        s = d2.ref_scores(objs, ["PR"])
        self.assertEqual(len(s), len(objs))
        self.assertEqual(s[6], 0.0)
        self.assertAlmostEqual(s[7], math.sqrt(32.0), places=6)

    def test_cli(self):
        emb_doc = {"code_version": "0.1.0", "gsdet": "0.2.0", "rows": [
            {"slide": "SLA", "ok": True, "objects": [B0, B1], "classes": ["ns", "ns"], "emb": [[0.0, 1.0], [1.0, 0.0]],
             "base": [[1.0, 2.0], [2.0, 1.0]], "clipped": [False, False]},
            {"slide": "SLB", "ok": True, "objects": [B0, B1], "classes": ["ns", "gs"], "emb": [[0.5, 0.5], [1.0, 1.0]],
             "base": [[1.5, 2.5], [3.0, 3.0]], "clipped": [False, False]}]}
        k_doc = {"SLA": {"k_objects": {"glom": [B0, B1], "gs": []}}, "SLB": {"k_objects": {"glom": [B0], "gs": [B1]}}}
        with tempfile.TemporaryDirectory() as t:
            paths = {}
            for name, doc in (("emb", emb_doc), ("k", k_doc), ("groups", {"SLA": "PA", "SLB": "PB"}),
                              ("train", ["PA"]), ("clinical", {})):
                paths[name] = os.path.join(t, name + ".json")
                with open(paths[name], "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            out = os.path.join(t, "d2.json")
            rc = d2.main(["--emb", paths["emb"], "--k", paths["k"], "--groups", paths["groups"], "--train",
                          paths["train"], "--clinical", paths["clinical"], "--n-perm", "9", "--out", out])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as f:
                doc = json.load(f)
        self.assertEqual(doc["code_version"], d2.CODE_VERSION)
        self.assertEqual((doc["n_ref_participants"], doc["n_eval_participants"]), (2, 0))
        self.assertEqual(set(doc["readings"][k] for k in d2.READINGS), {"not graded"})
        for s in ("SLA", "SLB", "PA", "PB"):
            self.assertNotIn(s, json.dumps(doc))


if __name__ == "__main__":
    unittest.main()
