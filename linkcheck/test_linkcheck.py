"""Tests for LinkCheck, on the made-up records in examples/ only (no network).

Every expected number below was worked out by hand from examples/records.jsonl and
examples/links.jsonl before the tests were first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import csv
import json
import os
import shutil
import tempfile
import unittest

from linkcheck import core
from linkcheck.__main__ import main

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, "examples", "records.jsonl")
LINKS = os.path.join(HERE, "examples", "links.jsonl")
IDS = ("QA01", "QB01", "XB01", "QA02", "QB02", "QC02", "QA03", "QB03", "XB03", "QC04",
       "QB05", "QB06", "QZZZ", "COG_")


def run(rules=core.RULES, priority=("B", "A"), links=None):
    return core.check(core.read_jsonl(RECORDS),
                      links if links is not None else core.read_jsonl(LINKS),
                      rules, priority)


class Links(unittest.TestCase):
    def test_resolution(self):
        report, _ = run()
        self.assertEqual(report["links"]["rows"], 9)
        self.assertEqual(report["links"]["resolution"], {
            "alt_id: new_pair": 1, "exact: already_linked": 1, "exact: new_pair": 3,
            "exact: same_source": 1, "exact: self_reference": 1,
            "suffix: already_linked": 1, "unresolved: unresolved": 1})
        self.assertEqual((report["links"]["pairs_exact"], report["links"]["pairs_with_rules"]),
                         (3, 4))
        self.assertEqual(report["links"]["pairs_added_by_rule"], {"alt_id": 1})

    def test_exact_only(self):
        report, _ = run(rules=["exact"])
        self.assertEqual(report["rules"], ["exact"])
        self.assertEqual(report["links"]["resolution"]["unresolved: unresolved"], 3)
        self.assertEqual(report["links"]["pairs_with_rules"], 3)
        self.assertEqual(report["overcount"]["with_rules"], report["overcount"]["exact"])

    def test_link_order_does_not_matter(self):
        links = core.read_jsonl(LINKS)
        self.assertEqual(run(links=links)[0], run(links=list(reversed(links)))[0])

    def test_ambiguous_alt_id(self):
        index = core.Index([{"source": "B", "id": "R1", "alt_ids": ["XX"]},
                            {"source": "B", "id": "R2", "alt_ids": ["XX"]}])
        self.assertEqual(index.resolve("B", "XX", core.RULES), (None, "ambiguous_alt_id"))
        self.assertEqual(index.resolve("B", "R1", ("exact",)), (("B", "R1"), "exact"))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            run(rules=["fuzzy"])
        with self.assertRaises(ValueError):
            core.check([{"source": "A"}], [])
        with self.assertRaises(ValueError):
            core.check([{"source": "A", "id": "1"}], [{"a_source": "A"}])


class Report(unittest.TestCase):
    def setUp(self):
        self.report, self.rows = run()

    def test_completeness(self):
        c = self.report["completeness"]
        self.assertEqual(c["A"], {"records": 3, "repeated_records": 1, "informative": {
            "sex": 3, "race": 2, "ethnicity": 1, "vital_status": 2, "age_at_vital_status": 2}})
        self.assertEqual(c["B"]["records"], 5)
        self.assertEqual(c["B"]["informative"]["race"], 2)
        self.assertEqual(c["C"]["informative"], {"sex": 1, "race": 0, "ethnicity": 0,
                                                 "vital_status": 1, "age_at_vital_status": 1})

    def test_conflicts(self):
        exact = self.report["conflicts"]["exact"]
        self.assertEqual(exact["all"]["pairs"], 3)
        self.assertEqual(exact["all"]["sex"], {"agree": 1, "disagree": 2})
        self.assertEqual(exact["all"]["vital_status"], {"alive_after_death": 1, "both_dead": 1,
                                                        "alive_then_dead": 1})
        self.assertEqual(exact["all"]["age_at_death"], {"within_1_day": 1})
        self.assertEqual(sorted(exact["by_source_pair"]), ["A | B", "B | C"])
        self.assertEqual(exact["by_source_pair"]["A | B"]["pairs"], 2)
        rules = self.report["conflicts"]["with_rules"]["all"]
        self.assertEqual(rules["sex"], {"agree": 2, "disagree": 2})
        self.assertEqual(rules["race"], {"agree": 1, "overlap": 1, "uninformative": 2})

    def test_overcount(self):
        self.assertEqual(self.report["overcount"]["exact"], {
            "records": 10, "records_in_links": 5, "linked_persons": 2, "persons": 7,
            "naive_overcount": 3, "persons_with_2plus_records_in_one_source": 0,
            "largest_person": 3})
        r = self.report["overcount"]["with_rules"]
        self.assertEqual((r["persons"], r["records_in_links"], r["linked_persons"],
                          r["naive_overcount"]), (6, 7, 3, 4))

    def test_cohort(self):
        self.assertEqual([r["person"] for r in self.rows],
                         ["P%06d" % n for n in range(1, 7)])
        p1, p2, p3 = self.rows[:3]
        self.assertEqual((p1["sources"], p1["records"]), ("A;B", "A:QA01;B:QB01"))
        self.assertEqual((p1["sex"], p1["race"], p1["ethnicity"]), ("M", "White", "NH"))
        self.assertEqual((p1["vital_consensus"], p1["vital_latest"], p1["vital_priority"],
                          p1["vital_conflict"]), ("conflict", "conflict", "Dead", 1))
        self.assertEqual((p2["n_records"], p2["sex"], p2["sex_conflict"]), (3, "conflict", 1))
        self.assertEqual((p2["vital_consensus"], p2["vital_latest"], p2["vital_priority"]),
                         ("conflict", "Dead", "Dead"))
        self.assertEqual((p3["sex"], p3["race"], p3["race_conflict"], p3["vital_latest"]),
                         ("F", "conflict", 1, ""))
        self.assertEqual(self.rows[5]["sex"], "")

    def test_cohort_summary(self):
        self.assertEqual(self.report["cohort_summary"], {
            "persons": 6, "vital_consensus": {"conflict": 2, "missing": 4},
            "vital_latest": {"Dead": 1, "conflict": 1, "missing": 4},
            "vital_priority": {"Dead": 2, "missing": 4},
            "sex_conflict": 1, "race_conflict": 1, "ethnicity_conflict": 0,
            "vital_conflict": 2})

    def test_priority_order(self):
        _, rows = run(priority=("A",))
        self.assertEqual(rows[0]["vital_priority"], "Alive")

    def test_report_has_no_record_ids(self):
        text = json.dumps(self.report)
        for ident in IDS:
            self.assertNotIn(ident, text)

    def test_suppress(self):
        self.assertEqual(core.suppress({"a": 3, "b": 20, "c": [1, 0], "d": True, "e": "x"}, 11),
                         {"a": "<11", "b": 20, "c": ["<11", 0], "d": True, "e": "x"})
        self.assertEqual(core.suppress({"a": 3}, 0), {"a": 3})


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_main(self):
        out, cohort = os.path.join(self.tmp, "report.json"), os.path.join(self.tmp, "c.csv")
        self.assertEqual(main(["--records", RECORDS, "--links", LINKS, "--out", out,
                               "--priority", "B,A", "--cohort", cohort, "--min-cell", "2"]), 0)
        with open(out, encoding="utf-8") as fh:
            text = fh.read()
        report = json.loads(text)
        self.assertEqual(report["overcount"]["exact"]["persons"], 7)
        self.assertEqual(report["links"]["pairs_added_by_rule"], {"alt_id": "<2"})
        for ident in IDS:
            self.assertNotIn(ident, text)
        with open(cohort, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 6)
        self.assertEqual(tuple(rows[0]), core.COHORT_FIELDS)


if __name__ == "__main__":
    unittest.main()
