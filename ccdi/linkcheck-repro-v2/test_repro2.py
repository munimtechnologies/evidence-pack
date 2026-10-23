"""Tests for the second LinkCheck reproduction of the CCDI census, on a made-up snapshot only
(no network). Every expected number was worked out by hand before the first run.

The made-up snapshot has two CCDI-DCC subjects with the same name in two namespaces, the
case that made the first reproduction fail.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import analyze
import ensure_snapshot2
import fetch_robust
import repro2
from linkcheck import paging

IDS = ("PAAAAA", "PBBBBB", "PCCCCC", "PZZZZZ", "TH01", "TH02", "SJ001", "THR01_0001",
       "COG_PCCCCC")
FAKE = {"absolute": {"records": 8, "pairs_exact": 2, "persons": 6, "naive_overcount": 2,
                     "linked_persons": 2, "records_in_links": 4},
        "rules": {"pairs_added_by_rule": {"alt_id": 1, "suffix": 1}, "pairs_with_rules": 4,
                  "overcount_with_rules": {"persons": 4, "naive_overcount": 4,
                                           "linked_persons": 2, "records_in_links": 6},
                  "extra_disagree": {"sex": 2, "race": 0, "ethnicity": 0}},
        "shared": {"CCDI-DCC": 1}}
FULL, EMPTY = {"participant_ids": [{"domain_name": "X"}]}, {"participant_ids": []}


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel.endswith(".gz"):
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(obj).encode())
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def subj(org, ns, name, sex=None, race=None, vital=None, age=None, alt=()):
    v = lambda x: {"value": x} if x is not None else None
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "kind": "Participant",
            "metadata": {"sex": v(sex), "race": [v(race)] if race else [], "ethnicity": None,
                         "vital_status": v(vital), "age_at_vital_status": v(age),
                         "identifiers": [{"value": {"name": a}} for a in alt]}}


def org(domain, pid, category="organizational_identifier"):
    return {"domain_name": domain, "participant_id": pid, "domain_category": category}


def make_snapshot(raw, ambiguous=False):
    put(raw, "subject/chosen.json", {"per_page": 10, "first_page": "probe-10.json",
                                     "pages_expected": 1})
    put(raw, "fed/subject-summary.json.gz", [
        {"source": "CCDI-DCC", "counts": {"total": 3}}, {"source": "PCDC", "counts": {"total": 2}},
        {"source": "Treehouse", "counts": {"total": 2}}, {"source": "StJude", "counts": {"total": 1}}])
    put(raw, "subject/probe-10.json.gz", [
        {"source": "CCDI-DCC", "data": [subj("dcc", "phs1", "PAAAAA", "Male", "White",
                                             "Alive", 100),
                                        subj("dcc", "phs2", "PAAAAA", "Male", "White"),
                                        subj("dcc", "phs1", "PBBBBB", "Female")]},
        {"source": "PCDC", "data": [subj("pcdc", "COG", "PAAAAA", "M"),
                                    subj("pcdc", "COG", "PCCCCC", "F")]},
        {"source": "Treehouse", "data": [subj("th", "TH", "TH01", "Female", alt=["THR01_0001"]),
                                         subj("th", "TH", "TH02", "Male")]},
        {"source": "StJude", "data": [subj("sj", "SJ", "SJ001", "Male")]}])
    entries = [
        {"domain_name": "phs2", "participant_id": "PAAAAA",
         "associated_ids": [{"domain_name": "USI", "participant_id": "PAAAAA"}]},
        {"domain_name": "treehouse", "participant_id": "TH01",
         "associated_ids": [org("phs1", "PBBBBB")]},
        {"domain_name": "StJude", "participant_id": "SJ001",
         "associated_ids": [org("Treehouse", "THR01_0001"), org("PCDC", "COG_PCCCCC"),
                            org("dbGaP", "x1", "other")]},
        {"domain_name": "PCDC", "participant_id": "PZZZZZ",
         "associated_ids": [{"domain_name": "USI", "participant_id": "PZZZZZ"}]}]
    if ambiguous:
        entries.append({"domain_name": "CCDI-DCC", "participant_id": "PAAAAA",
                        "associated_ids": [org("PCDC", "PCCCCC")]})
    put(raw, "mapping/page-0001.json.gz", {"participant_ids": entries})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        make_snapshot(self.raw)
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read_out(self):
        with open(os.path.join(self.out, "repro2.json"), encoding="utf-8") as fh:
            text = fh.read()
        return text, json.loads(text)


class Repro(Base):
    def test_adapt(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        records, links, counts = repro2.adapt(subjects, analyze.read_mappings(self.raw))
        self.assertEqual(len(records), 8)
        self.assertEqual((records[1]["id"], records[1]["namespace"]), ("PAAAAA", "phs2"))
        self.assertEqual(counts, {"link_rows": 6, "org_association": 3,
                                  "other_category_skipped": 1, "usi_association": 2,
                                  "usi_served_by_no_subject": 1})
        a = ("CCDI-DCC", "PAAAAA", "phs2")
        self.assertEqual(links[0], repro2.row(a, ("CCDI-DCC", "PAAAAA", "phs1")))
        self.assertEqual(links[2], repro2.row(a, ("PCDC", "PAAAAA", "COG")))
        self.assertEqual(links[3], repro2.row(("Treehouse", "TH01", ""),
                                              ("CCDI-DCC", "PBBBBB", "phs1")))

    def test_census(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        ref = repro2.census(subjects, analyze.read_mappings(self.raw))
        self.assertEqual(ref["pairs"], 2)
        self.assertEqual(ref["links"], {"entry_unresolved": 1, "org_link_resolved: phs1": 1,
                                        "org_link_unresolved: PCDC": 1,
                                        "org_link_unresolved: Treehouse": 1})
        self.assertEqual((ref["d"]["deduplicated_total"], ref["d"]["naive_overcount"]), (6, 2))

    def test_run_all_pass(self):
        r = repro2.run(self.raw, FAKE)
        self.assertEqual({k: v["grade"] for k, v in r["grades"].items()},
                         {"P1": "pass", "P2": "pass", "P3": "pass", "P4": "pass",
                          "P5": "pass", "P6": "pass", "S1": "pass", "F1": "not graded"})
        lc = r["linkcheck_report"]
        self.assertEqual(lc["links"]["resolution"], {
            "alt_id: new_pair": 1, "exact: new_pair": 2, "exact: same_source": 1,
            "exact: self_reference": 1, "suffix: new_pair": 1})
        self.assertEqual(lc["shared_ids"], {"CCDI-DCC": {"ids": 1, "records": 2}})
        self.assertEqual(r["grades"]["P4"]["observed"]["source_pairs"], 2)

    def test_shared_names(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        self.assertEqual(repro2.shared_names(subjects), {
            "groups": 1, "records": 2, "extra_records": {"CCDI-DCC": 1},
            "group_sizes": {"2": 1}, "same_namespace_name": 0, "name_is_usi": 1,
            "namespaces_involved": 2,
            "agreement": {"pairs": 1, "sex": {"agree": 1}, "ethnicity": {"uninformative": 1},
                          "race": {"agree": 1}, "vital": {"uninformative": 1},
                          "death_age": {}}})

    def test_ambiguous_id_is_not_guessed(self):
        raw = os.path.join(self.tmp, "raw-ambiguous")
        make_snapshot(raw, ambiguous=True)
        r = repro2.run(raw)
        g = r["grades"]
        self.assertEqual(g["P1"]["grade"], "pass")
        self.assertEqual(g["P2"]["grade"], "fail")
        self.assertEqual((g["P2"]["observed"]["census_pairs"], g["P2"]["observed"]["linkcheck_pairs"],
                          g["P2"]["observed"]["census_only"], g["P2"]["observed"]["linkcheck_only"]),
                         (3, 2, 1, 0))
        self.assertEqual(g["P3"]["grade"], "fail")
        self.assertEqual(g["P4"]["observed"]["source_pairs_differing"], ["CCDI-DCC | PCDC"])
        self.assertEqual((g["P5"]["grade"], g["F1"]["grade"]), ("not graded", "not graded"))
        self.assertEqual(r["linkcheck_report"]["links"]["resolution"]["unresolved: ambiguous_id"], 1)
        self.assertEqual(r["adapter_counts"]["org_association"], 4)

    def test_fetch_check(self):
        whole = paging.audit({1: {"A": 10}, 2: {"A": 10}, 3: {"A": 5}}, 10, {"A": 25})
        cut = paging.audit({1: {"A": 10}, 2: {"A": 0}}, 10, {"A": 25})
        self.assertEqual(repro2.fetch_check({"subject": whole, "mapping": whole})["grade"], "pass")
        bad = repro2.fetch_check({"subject": whole, "mapping": cut})
        self.assertEqual(bad["grade"], "fail")
        self.assertEqual(bad["observed"]["problems"],
                         {"mapping": {"A": {"pages_not_walked": 5, "unexplained": 0}}})


class Main(Base):
    def test_main_kept_snapshot(self):
        self.assertEqual(repro2.main(["--kept", self.raw, "--fresh-root", self.tmp,
                                      "--out", self.out]), 0)
        text, r = self.read_out()
        self.assertTrue(r["label"].startswith("PRE-REGISTERED"))
        self.assertEqual(r["input"]["snapshot"], "kept second snapshot")
        self.assertEqual(r["input"]["subjects"], 8)
        self.assertEqual([r["grades"][p]["grade"] for p in
                          ("P1", "P2", "P3", "P4", "P5", "P6", "S1", "F1")],
                         ["pass", "pass", "pass", "pass", "fail", "fail", "fail", "not graded"])
        for ident in IDS:
            self.assertNotIn(ident, text)

    def test_main_kept_fresh_snapshot(self):
        fresh = os.path.join(self.tmp, "ccdi-raw-fresh-20261024T000000Z")
        make_snapshot(fresh)
        put(fresh, "complete.json", {"finished_at": "2026-10-24T03:30:00Z"})
        repro2.main(["--kept", os.path.join(self.tmp, "nope"), "--fresh-root", self.tmp,
                     "--out", self.out])
        text, r = self.read_out()
        self.assertEqual(r["input"]["snapshot"],
                         "kept fresh snapshot ccdi-raw-fresh-20261024T000000Z")
        self.assertEqual({k: v["grade"] for k, v in r["grades"].items()},
                         {"P1": "pass", "P2": "pass", "P3": "pass", "P4": "pass",
                          "P5": "not graded", "P6": "not graded", "S1": "not graded",
                          "F1": "pass"})
        self.assertEqual(r["paging"]["mapping"]["sources"]["CCDI-DCC"]["lost"]["short_pages"], 2)
        for ident in IDS:
            self.assertNotIn(ident, text)

    def test_main_no_complete_snapshot(self):
        os.makedirs(os.path.join(self.tmp, "ccdi-raw-fresh-20261024T000000Z"))
        with self.assertRaises(SystemExit):
            repro2.main(["--kept", os.path.join(self.tmp, "nope"), "--fresh-root", self.tmp,
                         "--out", self.out])

    def test_complete(self):
        for name, done in (("ccdi-raw-fresh-2", True), ("ccdi-raw-fresh-1", True),
                           ("ccdi-raw-fresh-3", False), ("other", True)):
            os.makedirs(os.path.join(self.tmp, name))
            if done:
                put(self.tmp, name + "/complete.json", {})
        self.assertEqual([os.path.basename(p) for p in ensure_snapshot2.complete(self.tmp)],
                         ["ccdi-raw-fresh-1", "ccdi-raw-fresh-2"])


class Server:
    """A made-up endpoint: answers[page] is the list of bodies it gives, in turn."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, rel, url):
        self.calls.append(rel)
        return 200, self.answers[int(rel[-9:-5])].pop(0)


class Walk(unittest.TestCase):
    def test_an_empty_page_is_fetched_again(self):
        server = Server({1: [FULL], 2: [EMPTY, FULL], 3: [EMPTY]})
        retried = fetch_robust.walk("mapping", "/subject-mapping", 1, 2, 100,
                                    fetch_robust.empty_mapping, get=server, pause=0)
        self.assertEqual(server.calls, ["mapping/page-0001.json", "mapping/page-0002.json",
                                        "mapping/page-0002.json", "mapping/page-0003.json"])
        self.assertEqual(retried, [{"page": 2, "retries": 1, "empty_after": False}])

    def test_the_walk_goes_on_past_a_page_that_stays_empty(self):
        server = Server({1: [EMPTY, EMPTY, EMPTY, EMPTY], 2: [FULL], 3: [FULL]})
        retried = fetch_robust.walk("mapping", "/subject-mapping", 1, 2, 100,
                                    fetch_robust.empty_mapping, get=server, pause=0)
        self.assertEqual(len(server.calls), 6)
        self.assertEqual(retried, [{"page": 1, "retries": 3, "empty_after": True}])

    def test_empty_subject_page(self):
        self.assertTrue(fetch_robust.empty_subject([{"source": "A", "data": []},
                                                    {"source": "B", "data": []}]))
        self.assertFalse(fetch_robust.empty_subject([{"source": "A", "data": []},
                                                     {"source": "B", "data": None}]))
        self.assertFalse(fetch_robust.empty_subject([{"source": "A", "data": [{}]}]))


if __name__ == "__main__":
    unittest.main()
