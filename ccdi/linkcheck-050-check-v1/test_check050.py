"""Tests for check050.py on made-up data: the made-up snapshot of test_ccdi.py, graded with
LinkCheck 0.4.0 from old/ (downloaded by get_code.py) and 0.5.0. No network. Expected values
worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import os
import shutil
import tempfile
import unittest

import check050
import test_ccdi


class Plumbing(unittest.TestCase):
    def test_overall(self):
        per = [{"grades": {c: {"grade": "pass"} for c in check050.CHECKS}},
               {"grades": dict({c: {"grade": "pass"} for c in check050.CHECKS},
                               S2={"grade": "fail"}, S6={"grade": "not gradable"})}]
        got = check050.overall(per)
        self.assertEqual(got["S1"], "pass")
        self.assertEqual(got["S2"], "fail")
        self.assertEqual(got["S6"], "pass")
        self.assertEqual(check050.overall([]), {c: "not graded" for c in check050.CHECKS})
        only = [{"grades": dict({c: {"grade": "pass"} for c in check050.CHECKS},
                                S6={"grade": "not gradable"})}]
        self.assertEqual(check050.overall(only)["S6"], "not graded")

    def test_has_ids(self):
        self.assertTrue(check050.has_ids({"a": ["PABCDE"]}))
        self.assertTrue(check050.has_ids({"PABCDE": 1}))
        self.assertFalse(check050.has_ids({"PCDC": {"CCDI-DCC": 3}, "x": ["P1234"]}))

    def test_no_snapshot_grades_nothing(self):
        tmp = tempfile.mkdtemp()
        try:
            out = check050.run(os.path.join(tmp, "none"), os.path.join(tmp, "none2"))
            self.assertEqual(out["snapshots"], [])
            self.assertEqual(out["grades"], {c: "not graded" for c in check050.CHECKS})
        finally:
            shutil.rmtree(tmp)


class MadeUpSnapshot(unittest.TestCase):
    def test_grade_one(self):
        tmp = tempfile.mkdtemp()
        try:
            raw = os.path.join(tmp, "raw")
            test_ccdi.make_snapshot(raw)
            work = os.path.join(tmp, "work")
            os.makedirs(work)
            g, d = check050.grade_one(raw, work)
            self.assertEqual(g["S1"]["grade"], "pass", g["S1"])
            self.assertEqual(g["S1"]["observed"]["cohort_rows"], [1, 1])
            self.assertEqual(g["S1"]["observed"]["cohort_columns_added"],
                             ["hispanic", "hispanic_conflict", "race_standard"])
            # no CCDI-DCC in the made-up snapshot, so its 24 records are missing: S2 fails
            self.assertEqual(g["S2"]["grade"], "fail")
            self.assertEqual(g["S2"]["observed"]["values_2024_only"], {"A": {}, "B": {}})
            self.assertEqual(g["S3"]["grade"], "pass")
            self.assertEqual(g["S3"]["observed"]["read_with_ethnicity_vs_completeness"],
                             {"A": [0, 0], "B": [0, 0]})
            self.assertEqual(g["S4"]["grade"], "fail")
            self.assertEqual(g["S5"]["observed"]["ccdi_dcc_nh_implied"], 0)
            self.assertEqual(g["S5"]["grade"], "fail")
            self.assertEqual(g["S6"]["grade"], "not gradable")
            self.assertEqual(g["S6"]["observed"]["pairs"], 0)
            self.assertEqual(d["records"], 3)
            self.assertEqual(os.listdir(work), [])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
