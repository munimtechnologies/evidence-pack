"""Tests for the LinkCheck reproduction of the CCDI census, on a made-up snapshot only (no
network). Every expected number was worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import analyze
import repro

IDS = ("PAAAAA", "PBBBBB", "PCCCCC", "PZZZZZ", "TH01", "TH02", "SJ001", "THR01_0001",
       "COG_PCCCCC")
FAKE = {"absolute": {"records": 7, "pairs_exact": 2, "persons": 5, "naive_overcount": 2,
                     "linked_persons": 2, "records_in_links": 4},
        "rules": {"pairs_added_by_rule": {"alt_id": 1, "suffix": 1}, "pairs_with_rules": 4,
                  "overcount_with_rules": {"persons": 3, "naive_overcount": 4,
                                           "linked_persons": 2, "records_in_links": 6},
                  "extra_disagree": {"sex": 2, "race": 0, "ethnicity": 0}}}


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


def make_snapshot(raw):
    put(raw, "subject/chosen.json", {"per_page": 10, "first_page": "probe-10.json",
                                     "pages_expected": 1})
    put(raw, "subject/probe-10.json.gz", [
        {"source": "CCDI-DCC", "data": [subj("dcc", "phs1", "PAAAAA", "Male", "White",
                                             "Alive", 100),
                                        subj("dcc", "phs1", "PBBBBB", "Female")]},
        {"source": "PCDC", "data": [subj("pcdc", "COG", "PAAAAA", "M"),
                                    subj("pcdc", "COG", "PCCCCC", "F")]},
        {"source": "Treehouse", "data": [subj("th", "TH", "TH01", "Female", alt=["THR01_0001"]),
                                         subj("th", "TH", "TH02", "Male")]},
        {"source": "StJude", "data": [subj("sj", "SJ", "SJ001", "Male")]}])
    put(raw, "mapping/page-0001.json.gz", {"participant_ids": [
        {"domain_name": "CCDI-DCC", "participant_id": "PAAAAA",
         "associated_ids": [{"domain_name": "USI", "participant_id": "PAAAAA"}]},
        {"domain_name": "treehouse", "participant_id": "TH01",
         "associated_ids": [org("CCDI-DCC", "PBBBBB")]},
        {"domain_name": "StJude", "participant_id": "SJ001",
         "associated_ids": [org("Treehouse", "THR01_0001"), org("PCDC", "COG_PCCCCC"),
                            org("dbGaP", "x1", "other")]},
        {"domain_name": "PCDC", "participant_id": "PZZZZZ",
         "associated_ids": [{"domain_name": "USI", "participant_id": "PZZZZZ"}]}]})


class Repro(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        make_snapshot(self.raw)
        self.out = os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read_out(self):
        with open(os.path.join(self.out, "repro.json"), encoding="utf-8") as fh:
            text = fh.read()
        return text, json.loads(text)

    def test_adapt(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        records, links, counts = repro.adapt(subjects, analyze.read_mappings(self.raw))
        self.assertEqual(len(records), 7)
        self.assertEqual(records[4]["alt_ids"], ["THR01_0001"])
        self.assertEqual(counts, {"link_rows": 5, "org_association": 3,
                                  "other_category_skipped": 1, "usi_association": 2,
                                  "usi_served_by_no_subject": 1})
        self.assertEqual(links[0], repro.row("CCDI-DCC", "PAAAAA", "CCDI-DCC", "PAAAAA"))
        self.assertEqual(links[1], repro.row("CCDI-DCC", "PAAAAA", "PCDC", "PAAAAA"))
        self.assertEqual(links[2], repro.row("Treehouse", "TH01", "CCDI-DCC", "PBBBBB"))

    def test_census(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        ref = repro.census(subjects, analyze.read_mappings(self.raw))
        self.assertEqual(ref["pairs"], 2)
        self.assertEqual(ref["links"], {"entry_unresolved": 1, "org_link_resolved: CCDI-DCC": 1,
                                        "org_link_unresolved: PCDC": 1,
                                        "org_link_unresolved: Treehouse": 1})
        self.assertEqual((ref["d"]["deduplicated_total"], ref["d"]["naive_overcount"]), (5, 2))

    def test_run_all_pass(self):
        r = repro.run(self.raw, FAKE)
        self.assertEqual({k: v["grade"] for k, v in r["grades"].items()},
                         {"P1": "pass", "P2": "pass", "P3": "pass", "P4": "pass",
                          "P5": "pass", "P6": "pass"})
        lc = r["linkcheck_report"]
        self.assertEqual(lc["links"]["resolution"], {
            "alt_id: new_pair": 1, "exact: new_pair": 2, "exact: self_reference": 1,
            "suffix: new_pair": 1})
        self.assertEqual(lc["conflicts"]["exact"]["all"]["sex"], {"agree": 2})
        self.assertEqual(lc["conflicts"]["with_rules"]["all"]["sex"], {"agree": 2, "disagree": 2})
        self.assertEqual(r["grades"]["P4"]["observed"]["source_pairs"], 2)

    def test_grade_catches_a_difference(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        entries = analyze.read_mappings(self.raw)
        records, links, _ = repro.adapt(subjects, entries)
        ref = repro.census(subjects, entries)
        report, _ = repro.core.check(records, links[:2])
        index = repro.core.Index(records)
        pairs, _ = repro.core.resolve_links(index, links[:2])
        g = repro.grade(ref, report, {p for p, r in pairs.items() if r == "exact"}, 7)
        self.assertEqual(g["P1"]["grade"], "pass")
        self.assertEqual(g["P2"]["grade"], "fail")
        self.assertEqual((g["P2"]["observed"]["census_only"], g["P2"]["observed"]["linkcheck_only"]),
                         (1, 0))
        self.assertEqual(g["P3"]["grade"], "fail")
        self.assertEqual(g["P4"]["observed"]["source_pairs_differing"], ["CCDI-DCC | Treehouse"])
        self.assertEqual(g["P5"]["grade"], "not graded")

    def test_main_kept_snapshot(self):
        self.assertEqual(repro.main(["--raw", self.raw, "--out", self.out]), 0)
        text, r = self.read_out()
        self.assertTrue(r["label"].startswith("PRE-REGISTERED"))
        self.assertEqual(r["input"]["snapshot"], "kept second snapshot")
        self.assertEqual(r["input"]["subjects"], 7)
        self.assertEqual([r["grades"][p]["grade"] for p in ("P1", "P2", "P3", "P4", "P5", "P6")],
                         ["pass", "pass", "pass", "pass", "fail", "fail"])
        for ident in IDS:
            self.assertNotIn(ident, text)

    def test_main_fresh_snapshot(self):
        repro.main(["--raw", os.path.join(self.tmp, "nope"), "--fallback-raw", self.raw,
                    "--out", self.out])
        _, r = self.read_out()
        self.assertEqual(r["input"]["snapshot"], "fresh snapshot taken by this job")
        self.assertEqual(r["grades"]["P2"]["grade"], "pass")
        self.assertEqual(r["grades"]["P6"]["grade"], "not graded")

    def test_main_no_snapshot(self):
        with self.assertRaises(SystemExit):
            repro.main(["--raw", os.path.join(self.tmp, "nope"), "--out", self.out])


if __name__ == "__main__":
    unittest.main()
