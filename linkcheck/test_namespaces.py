"""Tests for LinkCheck 0.3.0's namespaces: records of one source that share an id (no network).

Every expected number below was worked out by hand before the tests were first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import unittest

from linkcheck import core

RECORDS = [
    {"source": "D", "id": "P1", "namespace": "s1", "sex": "Male"},
    {"source": "D", "id": "P1", "namespace": "s2", "sex": "Female"},
    {"source": "D", "id": "P1", "namespace": "s1", "sex": "Female"},
    {"source": "K", "id": "P1", "sex": "M"},
    {"source": "D", "id": "P2", "namespace": "s1"}]
LINKS = [
    {"a_source": "K", "a_id": "P1", "b_source": "D", "b_id": "P1"},
    {"a_source": "K", "a_id": "P1", "b_source": "D", "b_id": "P1", "b_namespace": "s1"},
    {"a_source": "K", "a_id": "P1", "b_source": "D", "b_id": "P1", "b_namespace": "s2"},
    {"a_source": "D", "a_id": "P1", "a_namespace": "s1",
     "b_source": "D", "b_id": "P1", "b_namespace": "s2"}]


class Namespaces(unittest.TestCase):
    def setUp(self):
        self.index = core.Index(RECORDS)

    def test_keys_and_repeats(self):
        self.assertEqual(sorted(self.index.records), [("D", "P1", "s1"), ("D", "P1", "s2"),
                                                      ("D", "P2", "s1"), ("K", "P1")])
        self.assertEqual(dict(self.index.repeats), {"D": 1})
        self.assertEqual(self.index.records[("D", "P1", "s1")]["sex"], "M")
        self.assertEqual(self.index.shared_ids(), {"D": {"ids": 1, "records": 2}})

    def test_resolve(self):
        r = self.index.resolve
        self.assertEqual(r("D", "P1", core.RULES), (None, "ambiguous_id"))
        self.assertEqual(r("D", "P1", ("exact",), "s2"), (("D", "P1", "s2"), "exact"))
        self.assertEqual(r("D", "P1", core.RULES, "s9"), (None, "unresolved"))
        self.assertEqual(r("D", "P2", ("exact",)), (("D", "P2", "s1"), "exact"))
        self.assertEqual(r("D", "X_P2", core.RULES), (("D", "P2", "s1"), "suffix"))
        self.assertEqual(r("D", "X_P1", core.RULES), (None, "unresolved"))
        self.assertEqual(r("K", "P1", ("exact",)), (("K", "P1"), "exact"))

    def test_records_without_a_namespace_keep_their_key(self):
        index = core.Index([{"source": "A", "id": "1", "namespace": None}])
        self.assertEqual(list(index.records), [("A", "1")])
        self.assertEqual(index.shared_ids(), {})

    def test_check(self):
        report, rows = core.check(RECORDS, LINKS)
        self.assertEqual(report["links"]["resolution"], {
            "exact: new_pair": 2, "exact: same_source": 1, "unresolved: ambiguous_id": 1})
        self.assertEqual(report["links"]["pairs_exact"], 2)
        self.assertEqual(report["overcount"]["exact"], {
            "records": 4, "records_in_links": 3, "linked_persons": 1, "persons": 2,
            "naive_overcount": 2, "persons_with_2plus_records_in_one_source": 1,
            "largest_person": 3})
        self.assertEqual(report["conflicts"]["exact"]["all"]["sex"], {"agree": 1, "disagree": 1})
        self.assertEqual(sorted(report["conflicts"]["exact"]["by_source_pair"]), ["D | K"])
        self.assertEqual(report["completeness"]["D"]["repeated_records"], 1)
        self.assertEqual(report["shared_ids"], {"D": {"ids": 1, "records": 2}})
        self.assertEqual((rows[0]["records"], rows[0]["sex"]), ("D:P1:s1;D:P1:s2;K:P1", "conflict"))
        text = json.dumps(report)
        for ident in ("P1", "P2"):
            self.assertNotIn(ident, text)


if __name__ == "__main__":
    unittest.main()
