# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Checks trinetx_audit.py against values computed by hand in run 28."""
import json
import os
import unittest

import trinetx_audit as ta

HERE = os.path.dirname(os.path.abspath(__file__))

CENTRE_FLAGS = ["k9 Peregoff opioid prescriptions 4 years",
                "k14 Yong COVID-19 Delta period"]


class TestHelpers(unittest.TestCase):
    def test_wilson(self):
        lo, hi = ta.wilson(2, 102)
        self.assertAlmostEqual(lo, 0.00539, delta=0.0005)
        self.assertAlmostEqual(hi, 0.06869, delta=0.0005)

    def test_verdict(self):
        self.assertEqual(ta.verdict(0.0054, 0.0687), "consistent with the benchmark")
        self.assertEqual(ta.verdict(0.08, 0.2), "higher than MEDLINE")
        self.assertEqual(ta.verdict(0.0, 0.05), "lower than MEDLINE")

    def test_printed_z_range(self):
        lo, hi = ta.printed_z_range("<0.0001")
        self.assertAlmostEqual(lo, 3.8906, delta=0.001)
        self.assertEqual(hi, float("inf"))
        lo, hi = ta.printed_z_range(".006")
        self.assertAlmostEqual(lo, 2.723, delta=0.005)
        self.assertAlmostEqual(hi, 2.776, delta=0.005)


class TestSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "trinetx_rows.json"), encoding="utf-8") as f:
            cls.out = ta.audit(json.load(f)["rows"])
        cls.by = {r["label"]: r for r in cls.out["rows"]}

    def test_counts(self):
        self.assertEqual(self.out["n_rows"], 102)
        self.assertEqual(len(self.by), 102)
        self.assertEqual(self.out["n_papers"], 39)

    def test_primary(self):
        p = self.out["primary"]
        self.assertEqual(p["centre_flagged"], CENTRE_FLAGS)
        self.assertEqual(p["verdict"], "consistent with the benchmark")

    def test_flags_are_centre_only(self):
        got = {r["label"]: r["flags"] for r in self.out["rows"] if r["flags"]}
        self.assertEqual(got, {k: ["centre"] for k in CENTRE_FLAGS})

    def test_midpoints(self):
        m = self.by["k9 Peregoff opioid prescriptions 4 years"]["checks"]["centre"]["midpoint"]
        self.assertAlmostEqual(m, 0.9041, delta=0.0005)
        m = self.by["k14 Yong COVID-19 Delta period"]["checks"]["centre"]["midpoint"]
        self.assertAlmostEqual(m, 4.139, delta=0.005)

    def test_borderline_passes(self):
        for label in ("k6 Chang OSA 2 years", "k37 Yang cerebrovascular diseases",
                      "k14 Yong overall", "k34 Thakkar all-cause mortality"):
            self.assertEqual(self.by[label]["flags"], [], label)

    def test_secondary(self):
        s = self.out["secondary"]
        self.assertEqual(s["papers_flagged"], ["40905294", "42243216"])
        self.assertAlmostEqual(s["paper_wilson95"][0], 0.0142, delta=0.001)
        self.assertAlmostEqual(s["paper_wilson95"][1], 0.1689, delta=0.001)
        self.assertEqual(s["count_rows"], 2)
        self.assertEqual(s["count_rows_flagged"], [])

    def test_kishimori_table(self):
        t = self.by["k39 Kishimori death 12 months"]["checks"]["table"]
        self.assertAlmostEqual(t["woolf"]["est"], 0.6704, delta=0.0005)
        self.assertAlmostEqual(t["woolf"]["lo"], 0.6332, delta=0.0005)
        self.assertAlmostEqual(t["woolf"]["hi"], 0.7097, delta=0.0005)
        t = self.by["k39 Kishimori hospitalization 12 months"]["checks"]["table"]
        self.assertAlmostEqual(t["woolf"]["est"], 0.7775, delta=0.0005)

    def test_exploratory_p(self):
        e = self.out["exploratory_p"]
        self.assertEqual(e["rows_with_p"], 15)
        self.assertEqual(e["flagged"], ["k27 Kido hospitalization or ER visits"])
        pc = self.by["k27 Kido hospitalization or ER visits"]["p_check"]
        self.assertAlmostEqual(pc["p_from_ci"], 0.857, delta=0.01)
        self.assertTrue(self.by["k9 Peregoff opioid prescriptions 4 years"]["p_check"]["ok"])


if __name__ == "__main__":
    unittest.main()
