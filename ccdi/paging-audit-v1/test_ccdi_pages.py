"""Tests for the CCDI paging audit, on a made-up snapshot written to a temporary folder
(no network). Every expected number below was worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import ccdi_pages


def rec(name, ns):
    return {"id": {"namespace": {"organization": "O", "name": ns}, "name": name}, "metadata": {}}


def ent(dom, pid):
    return {"domain_name": dom, "participant_id": pid, "associated_ids": []}


# Source S (total 4, namespace ns-s) errors on page 2. Source T (total 3, namespace T-study)
# answers its page past the end with an error. On /subject-mapping, S's page 2 is one entry
# short with no error; one entry names a domain that matches no source.
FILES = {
    "subject/probe-2.json": [{"source": "S", "data": [rec("S1", "ns-s"), rec("S2", "ns-s")]},
                             {"source": "T", "data": [rec("T1", "T-study"), rec("T2", "T-study")]}],
    "subject/probe-4.json": [{"source": "S", "data": [rec("S%d" % i, "ns-s") for i in range(4)]}],
    "subject/page-0002.json": [{"source": "S", "error": {"kind": "NotFound"}},
                               {"source": "T", "data": [rec("T3", "T-study")]}],
    "subject/page-0003.json": [{"source": "S", "data": []},
                               {"source": "T", "error": {"kind": "NotFound"}}],
    "mapping/page-0001.json": {"participant_ids": [ent("S", "S1"), ent("S", "S2"),
                                                   ent("t-study", "T1"), ent("T-study", "T2")]},
    "mapping/page-0002.json": {"participant_ids": [ent("ns-s", "S3"), ent("T-study", "T3"),
                                                   ent("Nowhere", "X1")]},
    "mapping/page-0003.json": {"participant_ids": []},
    "fed/subject-summary.json": [{"source": "S", "counts": {"total": 4}},
                                 {"source": "T", "counts": {"total": 3}}]}
EXPECTED = {"per_page": 2, "pages": 3, "totals": {"S": 4, "T": 3},
            "subject_past_end": {"S": 0, "T": 1},
            "subject_flags": [[2, "S", "error", None, 2]],
            "mapping_flags": [[2, "S", "short", 1, 2]],
            "lost": {"subject": {"S": 2}, "mapping": {"S": 1}}, "unmapped": 1}


def write_gz(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path + ".gz", "wb") as fh:
        fh.write(body)


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        for rel, body in FILES.items():
            write_gz(os.path.join(self.raw, rel), json.dumps(body).encode())
        with open(os.path.join(self.raw, "subject", "chosen.json"), "w", encoding="utf-8") as fh:
            json.dump({"per_page": 2, "first_page": "probe-2.json", "pages_expected": 2}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_walks(self):
        per_page, pages, domains, names = ccdi_pages.subject_walk(self.raw)
        self.assertEqual(per_page, 2)
        self.assertEqual(pages, {1: {"S": 2, "T": 2}, 2: {"S": None, "T": 1},
                                 3: {"S": 0, "T": None}})
        self.assertEqual(domains, {"s": "S", "ns-s": "S", "t": "T", "t-study": "T"})
        self.assertEqual(ccdi_pages.mapping_walk(self.raw, domains, names),
                         ({1: {"S": 2, "T": 2}, 2: {"S": 1, "T": 1}, 3: {}}, 1))
        self.assertEqual(ccdi_pages.summary_totals(self.raw), {"S": 4, "T": 3})

    def test_grades_with_expected_numbers(self):
        result = ccdi_pages.run(self.raw, EXPECTED)
        self.assertEqual({q: g["grade"] for q, g in result["grades"].items()},
                         {q: "pass" for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")})
        self.assertFalse(result["grades"]["Q5"]["observed"]["vacuous"])
        self.assertEqual(result["mapping"]["sources"]["S"]["short_pages"], [[2, 1]])

    def test_grader_can_fail(self):
        grades = ccdi_pages.run(self.raw, ccdi_pages.SNAPSHOT2)["grades"]
        self.assertEqual([grades[q]["grade"] for q in ("Q1", "Q2", "Q3", "Q4")], ["fail"] * 4)
        report = ccdi_pages.run(self.raw)
        report["mapping"]["flags"].append({"page": 3, "source": "T", "kind": "short",
                                           "entries": 0, "expected": 1})
        q5 = ccdi_pages.grade(report["subject"], report["mapping"], 1)["Q5"]
        self.assertEqual((q5["grade"], q5["observed"]["not_flagged_on_subject"]),
                         ("fail", [[3, "T"]]))

    def test_main_on_fresh_snapshot(self):
        out = os.path.join(self.tmp, "out")
        self.assertEqual(ccdi_pages.main(["--raw", os.path.join(self.tmp, "none"),
                                          "--fallback-raw", self.raw, "--out", out]), 0)
        with open(os.path.join(out, "paging-audit.json"), encoding="utf-8") as fh:
            result = json.load(fh)
        self.assertEqual(result["input"]["snapshot"], "fresh snapshot taken by this job")
        self.assertEqual({q: g["grade"] for q, g in result["grades"].items()},
                         {"Q1": "not graded", "Q2": "not graded", "Q3": "not graded",
                          "Q4": "not graded", "Q5": "pass", "Q6": "pass"})
        text = json.dumps(result)
        for ident in ("S1", "S3", "T2", "X1", "Nowhere"):
            self.assertNotIn(ident, text)

    def test_whole_page_failure(self):
        write_gz(os.path.join(self.tmp, "bad", "mapping", "page-0001.json"), b"Server Error")
        self.assertEqual(ccdi_pages.mapping_walk(os.path.join(self.tmp, "bad"), {}, {}),
                         ({1: None}, 0))


if __name__ == "__main__":
    unittest.main()
