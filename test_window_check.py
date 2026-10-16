# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import unittest

import window_check as wc

SPEC = {"title": "t", "subsets": {"general AUD samples": "general"}, "studies": [
    {"nct": "A", "tags": ["general"]},
    {"nct": "B", "tags": ["comorbid"]},
    {"nct": "C", "tags": ["general"]},
    {"nct": "D", "tags": ["general"], "sensitivity_only": True},
]}


class TestWindows(unittest.TestCase):
    def test_apply(self):
        out = wc.apply_windows(SPEC, {"B": "after", "C": "mixed"})
        rows = {s["nct"]: s for s in out["studies"]}
        self.assertEqual(rows["A"]["tags"], ["general", "on_treatment", "general_on"])
        self.assertEqual(rows["B"]["window"], "after")
        self.assertTrue(rows["B"]["sensitivity_only"])
        self.assertEqual(rows["C"]["tags"], ["general"])
        self.assertNotIn("sensitivity_only", rows["C"])
        self.assertTrue(rows["D"]["sensitivity_only"])
        self.assertEqual(out["subsets"]["outcome window fully on treatment"], "on_treatment")
        self.assertEqual(out["subsets"]["general AUD samples"], "general")

    def test_input_unchanged(self):
        wc.apply_windows(SPEC, {"B": "after"})
        self.assertEqual(SPEC["studies"][1], {"nct": "B", "tags": ["comorbid"]})

    def test_check_flags_misses(self):
        got = {key: {"k": k} for key, k in wc.EXPECTED_K.items()}
        for _, stem, key, field, want in wc.EXPECTED:
            got.setdefault((stem, key), {})[field] = want + 0.005
        ok, rows = wc.check(got)
        self.assertTrue(ok)
        got[("gabapentin_aud", "on_treatment")]["g"] = -0.40
        ok, rows = wc.check(got)
        self.assertFalse(ok)
        self.assertEqual(sum(1 for r in rows if not r[3]), 1)

    def test_every_audited_nct_is_named_once(self):
        ids = [n for w in wc.WINDOWS.values() for n in w]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), ["NCT00183196", "NCT00705523", "NCT01014533"])


if __name__ == "__main__":
    unittest.main()
