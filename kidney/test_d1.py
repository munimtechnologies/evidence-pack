# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/d1.py on synthetic numbers only (no KPMP data). Made with AI agents (Claude) in MV2's name."""
import json
import math
import os
import tempfile
import unittest

from kidney import d1

B = [5.0, 5.0, 0.0, 0.0, 10.0, 10.0, 100.0]


def kobj(n_ns, n_gs):
    return {"k_objects": {"glom": [B] * n_ns, "gs": [B] * n_gs}}


class TestTally(unittest.TestCase):
    def test_tally(self):
        docs = [{"code_version": "0.1.0", "gsdet": "0.2.0", "rows": [
            {"slide": "SLA", "ok": True, "classes": ["gs", "ns", "ns", "ns"]},
            {"slide": "SLB", "ok": True, "classes": ["gs", "gs"]},
            {"slide": "SLC", "ok": False},
            {"slide": "SLD", "ok": True, "classes": ["ns"]},
            {"slide": "SLE", "ok": True, "classes": ["ns"]}]},
            {"rows": [{"slide": "SLA", "ok": True, "classes": ["gs"]},
                      {"slide": "SLC", "ok": True, "classes": ["ns", "ns"]},
                      {"slide": "SLF", "ok": False}]}]
        groups = {"SLA": "PA", "SLB": "PA", "SLC": "PB", "SLE": "PB", "SLF": "PB"}
        k_doc = {"SLA": kobj(3, 1), "SLB": kobj(1, 0), "SLC": kobj(2, 1), "SLE": {"k_objects": None}}
        per, st = d1.tally(docs, k_doc, groups)
        self.assertEqual(per, {"PA": [3, 6, 1, 5], "PB": [0, 2, 1, 3]})
        self.assertEqual(st, {"slides": 6, "failed": 1, "no_group": 1, "no_k": 1, "used": 3})

    def test_shares(self):
        per = {"PA": [3, 6, 1, 5], "PB": [0, 2, 1, 3]}
        self.assertEqual(d1.shares(per, ["PB"], 5), {"PA": (0.5, 0.2)})
        self.assertEqual(d1.shares(per, (), 2), {"PA": (0.5, 0.2), "PB": (0.0, 1 / 3)})
        self.assertEqual(d1.shares(per, (), 3), {"PA": (0.5, 0.2)})


class TestOneSided(unittest.TestCase):
    X = [1, 2, 3, 4, 5, 6, 7, 8]
    Y = [8, 7, 6, 5, 4, 3, 2, 1]

    def test_expected_direction(self):
        r, p = d1.one_sided(self.X, self.Y, -1, 199, 11)
        self.assertEqual(r, -1.0)
        self.assertLessEqual(p, 0.05)
        self.assertAlmostEqual(p * 200, round(p * 200), places=9)

    def test_wrong_direction(self):
        self.assertEqual(d1.one_sided(self.X, self.Y, 1, 199, 11), (-1.0, 1.0))

    def test_no_shuffles(self):
        self.assertEqual(d1.one_sided(self.X, self.Y, -1, 0, 11), (-1.0, 1.0))

    def test_undefined(self):
        self.assertEqual(d1.one_sided([1, 1, 1], [1, 2, 3], -1, 9, 11), (None, None))
        self.assertEqual(d1.one_sided([], [], -1, 9, 11), (None, None))

    def test_deterministic(self):
        y = [3, 1, 4, 1, 5, 9, 2, 6]
        self.assertEqual(d1.one_sided(self.X, y, 1, 50, 11), d1.one_sided(self.X, y, 1, 50, 11))


class TestClin(unittest.TestCase):
    def test_clin_test(self):
        sh = {"PA": (0.1, 0.2), "PB": (0.2, 0.1), "PC": (0.3, 0.3), "PD": (0.4, 0.5), "PE": (0.9, 0.9)}
        clin = {"PA": {"egfr": 90, "hypertension": 0}, "PB": {"egfr": 80, "hypertension": 0},
                "PC": {"egfr": 60, "hypertension": 1}, "PD": {"egfr": 40, "hypertension": None},
                "PE": {"egfr": None, "hypertension": 1}, "PZ": {"egfr": 10}}
        out = d1.clin_test(sh, clin, "egfr", -1, sorted(sh) + ["PZ"], 9, 11)
        self.assertEqual(out["n"], 4)
        self.assertEqual(out["rho_detector"], -1.0)
        self.assertAlmostEqual(out["rho_label"], -0.8)
        y = [90, 80, 60, 40]
        self.assertEqual(out["p_detector"], d1.one_sided([0.1, 0.2, 0.3, 0.4], y, -1, 9, 11)[1])
        self.assertEqual(out["p_label"], d1.one_sided([0.2, 0.1, 0.3, 0.5], y, -1, 9, 11)[1])
        self.assertEqual(d1.clin_test(sh, clin, "hypertension", 1, sorted(sh), 9, 11)["n"], 4)


class TestAgreement(unittest.TestCase):
    def test_agreement(self):
        sh = {"PA": (0.5, 0.25), "PB": (0.25, 0.25), "PC": (0.75, 0.5)}
        a = d1.agreement(sh, ["PA", "PB", "PC", "PX"])
        self.assertEqual(a["n"], 3)
        self.assertAlmostEqual(a["rho"], 1.5 / math.sqrt(3.0))
        self.assertEqual(a["mean_detector"], 0.5)
        self.assertAlmostEqual(a["mean_label"], 1.0 / 3.0)
        self.assertAlmostEqual(a["mean_bias"], 0.5 / 3.0)
        self.assertEqual(a["median_bias"], 0.25)

    def test_empty(self):
        a = d1.agreement({}, ["PA"])
        self.assertEqual((a["n"], a["rho"], a["mean_bias"]), (0, None, None))


class TestReadings(unittest.TestCase):
    @staticmethod
    def make(n, rd, pd, rl, rh, ph, ra):
        return ({"n": n, "rho_detector": rd, "p_detector": pd, "rho_label": rl, "p_label": pd},
                {"n": n, "rho_detector": rh, "p_detector": ph, "rho_label": rh, "p_label": ph},
                {"n": n, "rho": ra})

    def test_pass(self):
        r = d1.readings(*self.make(60, -0.3, 0.001, -0.35, 0.2, 0.04, 0.7))
        self.assertEqual(r, {"d1a": "pass", "d1b": "pass", "d1c": "pass", "d1d": "pass"})

    def test_gap_boundary(self):
        self.assertEqual(d1.readings(*self.make(60, -0.3, 0.001, -0.4, 0.2, 0.04, 0.7))["d1b"], "pass")

    def test_fail(self):
        r = d1.readings(*self.make(60, -0.3, 0.01, -0.45, -0.1, 0.01, 0.69))
        self.assertEqual(r, {"d1a": "fail", "d1b": "fail", "d1c": "fail", "d1d": "fail"})
        self.assertEqual(d1.readings(*self.make(60, 0.3, 0.001, 0.3, 0.2, 0.04, 0.7))["d1a"], "fail")

    def test_not_graded(self):
        r = d1.readings(*self.make(59, -0.3, 0.001, -0.35, 0.2, 0.04, 0.7))
        self.assertEqual(set(r.values()), {"not graded"})
        r = d1.readings(*self.make(60, None, None, -0.35, None, None, None))
        self.assertEqual(set(r.values()), {"not graded"})
        r = d1.readings(*self.make(60, -0.3, 0.001, None, 0.2, 0.04, 0.7))
        self.assertEqual((r["d1a"], r["d1b"]), ("pass", "not graded"))


def synthetic():
    spec = [("SLA", "PA", 1, 1, 90, 0), ("SLB", "PB", 2, 1, 80, 0), ("SLC", "PC", 3, 2, 70, 1),
            ("SLD", "PD", 4, 3, 60, 1), ("SLE", "PE", 5, 4, 50, 1), ("SLT", "PT", 0, 0, 100, 0)]
    rows = [{"slide": s, "ok": True, "classes": ["gs"] * dg + ["ns"] * (5 - dg)} for s, _, dg, _, _, _ in spec]
    k_doc = {s: kobj(5 - kg, kg) for s, _, _, kg, _, _ in spec}
    groups = {s: g for s, g, *_ in spec}
    clin = {g: {"egfr": e, "hypertension": h} for _, g, _, _, e, h in spec}
    return rows, k_doc, groups, clin


class TestGrade(unittest.TestCase):
    def test_grade(self):
        rows, k_doc, groups, clin = synthetic()
        doc = d1.grade([{"code_version": "0.1.0", "gsdet": "0.2.0", "rows": rows}], k_doc, groups, ["PT"], clin,
                       dev=["PE"], n_perm=99, min_part=3)
        self.assertEqual(doc["n_participants"], 5)
        self.assertEqual(doc["n_train_participants_excluded"], 1)
        self.assertEqual(doc["share_slides_failed"], 0.0)
        self.assertEqual(doc["detector_documents"], ["0.1.0/0.2.0"])
        self.assertEqual(doc["egfr"]["n"], 5)
        self.assertEqual(doc["egfr"]["rho_detector"], -1.0)
        self.assertAlmostEqual(doc["egfr"]["rho_label"], round(-9.5 / math.sqrt(95.0), 4))
        self.assertAlmostEqual(doc["agreement"]["rho"], round(9.5 / math.sqrt(95.0), 4))
        self.assertAlmostEqual(doc["agreement"]["mean_bias"], 0.16)
        self.assertGreater(doc["hypertension"]["rho_detector"], 0)
        self.assertEqual(doc["reported"]["egfr_without_dev"]["n"], 4)
        self.assertEqual(doc["reported"]["train_agreement"]["n"], 1)
        self.assertIsNone(doc["reported"]["train_agreement"]["rho"])
        rd = doc["readings"]
        self.assertEqual((rd["d1b"], rd["d1d"]), ("pass", "pass"))
        self.assertIn(rd["d1a"], ("pass", "fail"))
        self.assertIn(rd["d1c"], ("pass", "fail"))

    def test_cli(self):
        rows, k_doc, groups, clin = synthetic()
        with tempfile.TemporaryDirectory() as t:
            paths = {}
            for name, doc in (("det1", {"code_version": "0.2.0", "rows": rows[:3]}), ("det2", {"rows": rows[3:]}),
                              ("k1", {s: k_doc[s] for s in ("SLA", "SLB", "SLC")}),
                              ("k2", {s: k_doc[s] for s in ("SLD", "SLE", "SLT")}), ("groups", groups),
                              ("train", ["PT"]), ("dev", ["PE"]), ("clinical", clin)):
                paths[name] = os.path.join(t, name + ".json")
                with open(paths[name], "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            out = os.path.join(t, "d1.json")
            rc = d1.main(["--det", paths["det1"], paths["det2"], "--k", paths["k1"], paths["k2"], "--groups",
                          paths["groups"], "--train", paths["train"], "--dev", paths["dev"], "--clinical",
                          paths["clinical"], "--n-perm", "9", "--out", out])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as f:
                text = f.read()
        doc = json.loads(text)
        self.assertEqual(doc["code_version"], d1.CODE_VERSION)
        self.assertEqual(doc["n_participants"], 5)
        self.assertEqual(set(doc["readings"].values()), {"not graded"})
        for s in ("SLA", "SLE", "SLT", "PA", "PE", "PT"):
            self.assertNotIn(s, text)


if __name__ == "__main__":
    unittest.main()
