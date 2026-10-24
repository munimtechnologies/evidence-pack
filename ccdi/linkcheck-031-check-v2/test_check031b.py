"""Tests for the second try of the LinkCheck 0.3.1 real-data check, on the made-up snapshot of
test_check031.py written to temporary folders (no network). Every expected value below was
worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

import check031b
from test_ccdi_pages import write_gz
from test_check031 import EXPECTED, FILES

R, T = ["R1", "R2", "R3", "R4"], ["T1", "T2", "T3", "T4"]
RETRIES = {"subject": [], "mapping": [{"page": 2, "retries": 1, "empty_after": False}]}


def write_snapshot(raw, complete=None, retries=None):
    for rel, body in FILES.items():
        write_gz(os.path.join(raw, rel), json.dumps(body).encode())
    with open(os.path.join(raw, "subject", "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_page": 2, "first_page": "probe-2.json", "pages_expected": 2}, fh)
    for name, body in (("complete.json", complete), ("retries.json", retries)):
        if body is not None:
            with open(os.path.join(raw, name), "w", encoding="utf-8") as fh:
                json.dump(body, fh)


def grades(result):
    return {n: g["grade"] for n, g in result["grades"].items()}


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kept = os.path.join(self.tmp, "kept")
        self.root = os.path.join(self.tmp, "fresh")
        self.fresh = os.path.join(self.root, "ccdi-raw-fresh-20261024T000000Z")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_kept_snapshot_comes_first_and_grades_r(self):
        write_snapshot(self.kept)
        write_snapshot(self.fresh, {"requests": 9}, RETRIES)
        result = check031b.run(self.kept, self.root)
        self.assertEqual(result["input"]["snapshot"], "kept second snapshot")
        # The fixture is not the second snapshot, so v0.8.5's numbers fail on it.
        self.assertEqual(grades(result), dict({r: "fail" for r in R},
                                              **{t: "not graded" for t in T}))
        self.assertEqual(result["grades"]["T1"]["why"], "the kept second snapshot was used")
        self.assertNotIn("fresh_complete", result)

    def test_fresh_snapshot_grades_t(self):
        write_snapshot(self.fresh, {"requests": 9}, RETRIES)
        result = check031b.run(self.kept, self.root, EXPECTED, cut=2)
        self.assertEqual(result["input"]["snapshot"],
                         "fresh snapshot ccdi-raw-fresh-20261024T000000Z")
        self.assertEqual(grades(result), dict({r: "not graded" for r in R},
                                              **{t: "pass" for t in T}))
        self.assertEqual(result["grades"]["R1"]["why"], "no kept second snapshot on this machine")
        self.assertEqual(result["grades"]["T4"]["observed"],
                         {"subject_first_empty": 3, "mapping_first_empty": 3})
        self.assertEqual(result["replay_cut"], {"cut_at": 2, "refetch_count": 1,
                                                "refetch_first": 2, "refetch_last": 2})
        self.assertEqual((result["fresh_complete"], result["fresh_retries"]),
                         ({"requests": 9}, RETRIES))

    def test_fresh_grader_can_fail(self):
        write_snapshot(self.fresh, {"requests": 9})
        result = check031b.run(self.kept, self.root)
        self.assertEqual([grades(result)[t] for t in T], ["fail"] * 4)
        self.assertIsNone(result["fresh_retries"])

    def test_only_complete_fresh_snapshots_count(self):
        older = os.path.join(self.root, "ccdi-raw-fresh-20261023T000000Z")
        write_snapshot(older, {"requests": 9})
        write_snapshot(self.fresh)
        self.assertEqual(check031b.pick(self.kept, self.root),
                         (older, "fresh snapshot ccdi-raw-fresh-20261023T000000Z"))
        shutil.rmtree(older)
        self.assertEqual(check031b.pick(self.kept, self.root), (None, None))
        result = check031b.run(self.kept, self.root)
        self.assertEqual(grades(result), {n: "not graded" for n in R + T})
        self.assertEqual(result["grades"]["T3"]["why"], "no complete snapshot on this machine")
        self.assertIsNone(result["input"]["snapshot"])

    def test_main_keeps_no_ids_or_messages(self):
        write_snapshot(self.fresh, {"requests": 9}, RETRIES)
        out = os.path.join(self.tmp, "out")
        self.assertEqual(check031b.main(["--kept", self.kept, "--fresh-root", self.root,
                                         "--out", out]), 0)
        with open(os.path.join(out, "check031b.json"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(json.loads(text)["input"]["snapshot"],
                         "fresh snapshot ccdi-raw-fresh-20261024T000000Z")
        for secret in ("S1", "S2", "S3", "secret-T9", "past end", "not found"):
            self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
