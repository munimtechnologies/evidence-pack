"""Tests for the LinkCheck 0.3.1 real-data check, on a made-up snapshot written to a temporary
folder (no network). Every expected number below was worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

import check031
from test_ccdi_pages import ent, rec, write_gz

# per_page 2. Source S (total 3) ends on page 2. Source T (total 2) answers every page after
# its end with an error object. /subject-mapping page 3 is the fixed "not found" object.
NOT_FOUND = {"errors": [{"kind": "NotFound", "method": "GET", "route": "/subject-mapping",
                         "message": "Participants IDs are not found."}]}
FILES = {
    "subject/probe-2.json": [{"source": "S", "data": [rec("S1", "ns-s"), rec("S2", "ns-s")]},
                             {"source": "T", "data": [rec("T1", "ns-t"), rec("T2", "ns-t")]}],
    "subject/page-0002.json": [{"source": "S", "data": [rec("S3", "ns-s")]},
                               {"source": "T", "errors": [{"kind": "NotFound",
                                                           "message": "secret-T9 gone"}]}],
    "subject/page-0003.json": [{"source": "S", "data": []},
                               {"source": "T", "errors": [{"kind": "NotFound",
                                                           "message": "past end"}]}],
    "mapping/page-0001.json": {"participant_ids": [ent("S", "S1"), ent("S", "S2"),
                                                   ent("T", "T1"), ent("T", "T2")]},
    "mapping/page-0002.json": {"participant_ids": [ent("S", "S3")]},
    "mapping/page-0003.json": NOT_FOUND,
    "fed/subject-summary.json": [{"source": "S", "counts": {"total": 3}},
                                 {"source": "T", "counts": {"total": 2}}]}
EXPECTED = {"pages": 3, "last": 2, "subject_flags": []}


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        for rel, body in FILES.items():
            write_gz(os.path.join(self.raw, rel), json.dumps(body).encode())
        with open(os.path.join(self.raw, "subject", "chosen.json"), "w", encoding="utf-8") as fh:
            json.dump({"per_page": 2, "first_page": "probe-2.json", "pages_expected": 2}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_body_walk(self):
        pages, rejected, kinds = check031.body_walk(self.raw)
        self.assertEqual(pages, {1: {"S": 2, "T": 2}, 2: {"S": 1, "T": None},
                                 3: {"S": 0, "T": None}})
        self.assertEqual((rejected, kinds), ([], {"T | NotFound": 2}))

    def test_all_hold_on_fixture(self):
        result = check031.run(self.raw, EXPECTED, cut=2)
        self.assertEqual({r: g["grade"] for r, g in result["grades"].items()},
                         {"R1": "pass", "R2": "pass", "R3": "pass", "R4": "pass"})
        self.assertEqual(result["grades"]["R4"]["observed"],
                         {"subject_first_empty": 3, "mapping_first_empty": 3})
        self.assertEqual(result["replay_cut"], {"cut_at": 2, "refetch_count": 1,
                                                "refetch_first": 2, "refetch_last": 2})
        self.assertEqual(result["subject"]["sources"]["T"]["errors_past_end"], 2)

    def test_grader_can_fail(self):
        result = check031.run(self.raw)
        self.assertEqual([result["grades"][r]["grade"] for r in ("R1", "R2", "R3", "R4")],
                         ["fail"] * 4)

    def test_rejected_page(self):
        write_gz(os.path.join(self.raw, "subject", "page-0004.json"), b'{"oops": 1}')
        pages, rejected, _ = check031.body_walk(self.raw)
        self.assertEqual((sorted(pages), rejected), ([1, 2, 3], [4]))
        r1 = check031.run(self.raw, dict(EXPECTED, pages=4), cut=2)["grades"]["R1"]
        self.assertEqual((r1["grade"], r1["observed"]["rejected"],
                          r1["observed"]["differing_pages"]), ("fail", [4], [4]))

    def test_main_keeps_no_ids_or_messages(self):
        out = os.path.join(self.tmp, "out")
        self.assertEqual(check031.main(["--raw", self.raw, "--out", out]), 0)
        with open(os.path.join(out, "check031.json"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(json.loads(text)["input"]["snapshot"], "kept second snapshot")
        for secret in ("S1", "S3", "T2", "secret-T9", "past end", "not found"):
            self.assertNotIn(secret, text)

    def test_main_without_snapshot(self):
        out = os.path.join(self.tmp, "out")
        self.assertEqual(check031.main(["--raw", os.path.join(self.tmp, "none"),
                                        "--out", out]), 0)
        with open(os.path.join(out, "check031.json"), encoding="utf-8") as fh:
            result = json.load(fh)
        self.assertEqual({r: g["grade"] for r, g in result["grades"].items()},
                         {r: "not graded" for r in ("R1", "R2", "R3", "R4")})


if __name__ == "__main__":
    unittest.main()
