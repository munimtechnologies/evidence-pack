"""Tests for the LinkCheck 0.4.0 CCDI-reader check (check040.py), on the made-up snapshot of
LinkCheck's test_ccdi.py, written to a temporary folder. No network. Every expected value was
worked out by hand before the first run.

The census code (analyze.py, tag v0.5.5) reads every association as an object, so these tests
use the made-up snapshot without its one association that is not an object.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

import check040
import test_ccdi
from linkcheck import ccdi

E2_CLEAN = {"domain_name": "B", "participant_id": "b1", "associated_ids": [
    {"domain_name": "usi", "participant_id": "PAAAAA", "domain_category": "usi"},
    {"domain_name": "usi", "participant_id": "PZZZZZ"}]}
MADE_UP = {"records": 3, "pairs_exact": 2, "persons": 1, "naive_overcount": 2, "shared_ids": {}}


def make_snapshot(raw):
    test_ccdi.make_snapshot(raw)
    test_ccdi.put(raw, "mapping/page-0001.json.gz", {"participant_ids": [test_ccdi.E1, E2_CLEAN]})


class GradeOne(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        make_snapshot(self.raw)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_all_pass(self):
        g, result = check040.grade_one(self.raw, MADE_UP)
        self.assertEqual({c: v["grade"] for c, v in g.items()},
                         {"C1": "pass", "C2": "pass", "C3": "pass", "C4": "pass", "C5": "pass"})
        self.assertEqual(g["C2"]["observed"]["counts"],
                         {"link_rows": 3, "org_association": 1, "other_category_skipped": 1,
                          "usi_association": 2, "usi_served_by_no_subject": 1})
        self.assertEqual(g["C4"]["observed"]["census_pairs"], 2)
        self.assertEqual(g["C4"]["observed"]["census"],
                         {"persons": 1, "naive_overcount": 2, "linked_persons": 1,
                          "records_in_links": 3})
        self.assertEqual(result["input"]["records"], 3)

    def test_a_lost_record_is_caught(self):
        original = ccdi.read_snapshot

        def broken(raw):
            snap = original(raw)
            snap["records"] = snap["records"][:-1]
            return snap

        ccdi.read_snapshot = broken
        try:
            g, _ = check040.grade_one(self.raw, MADE_UP)
        finally:
            ccdi.read_snapshot = original
        self.assertEqual(g["C1"]["grade"], "fail")
        self.assertEqual(g["C1"]["observed"]["first_difference"], 2)
        self.assertEqual((g["C2"]["grade"], g["C3"]["grade"]), ("pass", "pass"))
        self.assertEqual(g["C5"]["grade"], "fail")


class Main(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read(self, out):
        with open(os.path.join(out, "check040.json"), encoding="utf-8") as fh:
            return fh.read()

    def test_no_snapshot(self):
        out = os.path.join(self.tmp, "out")
        root = os.path.join(self.tmp, "fresh-root")
        os.makedirs(root)
        check040.main(["--kept", os.path.join(self.tmp, "none"), "--fresh-root", root,
                       "--out", out])
        res = json.loads(self.read(out))
        self.assertEqual(res["snapshots"], [])
        self.assertEqual(set(res["grades"].values()), {"not graded"})

    def test_two_snapshots(self):
        kept = os.path.join(self.tmp, "kept")
        make_snapshot(kept)
        root = os.path.join(self.tmp, "fresh-root")
        fresh = os.path.join(root, "ccdi-raw-fresh-20261024T000000Z")
        make_snapshot(fresh)
        with open(os.path.join(fresh, "complete.json"), "w", encoding="utf-8") as fh:
            json.dump({"requests": 9}, fh)
        unfinished = os.path.join(root, "ccdi-raw-fresh-20261025T000000Z")
        make_snapshot(unfinished)
        out = os.path.join(self.tmp, "out")
        check040.main(["--kept", kept, "--fresh-root", root, "--out", out])
        text = self.read(out)
        res = json.loads(text)
        self.assertEqual(res["snapshots"],
                         ["kept second snapshot", "fresh snapshot ccdi-raw-fresh-20261024T000000Z"])
        # The made-up snapshots are not the real ones, so C5 fails and C1-C4 pass.
        self.assertEqual(res["grades"],
                         {"C1": "pass", "C2": "pass", "C3": "pass", "C4": "pass", "C5": "fail"})
        for ident in ("PAAAAA", "StudyA1", '"b1"'):
            self.assertNotIn(ident, text)

    def test_has_ids(self):
        self.assertTrue(check040.has_ids({"x": ["PABCDE"]}))
        self.assertTrue(check040.has_ids({"PABCDE": 1}))
        self.assertFalse(check040.has_ids({"CCDI-DCC": ["PCDC", "PABCD", 3]}))


if __name__ == "__main__":
    unittest.main()
