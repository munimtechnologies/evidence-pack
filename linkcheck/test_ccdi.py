"""Tests for LinkCheck 0.4.0's CCDI snapshot reader (linkcheck/ccdi.py), on a made-up snapshot
written to a temporary folder. No network. Every expected value was worked out by hand
before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

from linkcheck import ccdi


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8")
    with gzip.open(path, "wb") as fh:
        fh.write(body)


def subj(org, ns, name, sex=None, race=(), vital=None, age=None, alt=()):
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "metadata": {"sex": {"value": sex}, "race": [{"value": r} for r in race],
                         "ethnicity": None, "vital_status": {"value": vital},
                         "age_at_vital_status": {"value": age},
                         "identifiers": [{"value": {"name": a}} for a in alt]}}


A1 = subj("OrgA", "StudyA1", "PAAAAA", "Female", ["White"], "Dead", 1000)
A2 = subj("OrgA", "StudyA2", "a2", "Male", (), "Alive", 500)
B1 = subj("OrgB", "StudyB", "b1", "Female", ["White"], "Alive", 900, alt=["PAAAAA"])
E1 = {"domain_name": "StudyA2", "participant_id": "a2", "associated_ids": [
    {"domain_name": "StudyB", "participant_id": "b1",
     "domain_category": "organizational_identifier"},
    {"domain_name": "dbGaP", "participant_id": "x1", "domain_category": "other"}]}
E2 = {"domain_name": "B", "participant_id": "b1", "associated_ids": [
    {"domain_name": "usi", "participant_id": "PAAAAA", "domain_category": "usi"},
    {"domain_name": "usi", "participant_id": "PZZZZZ"}, "junk"]}
E3 = {"domain_name": "Nowhere", "participant_id": "z1", "associated_ids": []}

REC_A1 = {"source": "A", "id": "PAAAAA", "namespace": "StudyA1", "alt_ids": [],
          "sex": "Female", "race": ["White"], "ethnicity": None, "vital_status": "Dead",
          "age_at_vital_status": 1000}
REC_A2 = {"source": "A", "id": "a2", "namespace": "StudyA2", "alt_ids": [], "sex": "Male",
          "race": [], "ethnicity": None, "vital_status": "Alive", "age_at_vital_status": 500}
REC_B1 = {"source": "B", "id": "b1", "namespace": "StudyB", "alt_ids": ["PAAAAA"],
          "sex": "Female", "race": ["White"], "ethnicity": None, "vital_status": "Alive",
          "age_at_vital_status": 900}
LINKS = [{"a_source": "A", "a_id": "a2", "a_namespace": "StudyA2",
          "b_source": "B", "b_id": "b1", "b_namespace": "StudyB"},
         {"a_source": "B", "a_id": "b1", "a_namespace": "",
          "b_source": "A", "b_id": "PAAAAA", "b_namespace": "StudyA1"},
         {"a_source": "B", "a_id": "b1", "a_namespace": "",
          "b_source": "B", "b_id": "b1", "b_namespace": "StudyB"}]


def make_snapshot(raw):
    """Two sources, per_page 2. /subject: page 1 is the chosen probe; page 2 repeats A1 and
    B's part is an error past its end; page 3 is empty. An unused probe is never read.
    /subject-mapping: page 1 holds E1 and E2, page 2 an entry no source serves, page 3 the
    aggregator's 'Server Error.' body."""
    os.makedirs(os.path.join(raw, "subject"))
    with open(os.path.join(raw, "subject", "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_page": 2, "first_page": "probe-2.json", "pages_expected": 2}, fh)
    put(raw, "subject/probe-2.json.gz",
        [{"source": "A", "data": [A1, A2]}, {"source": "B", "data": [B1]}])
    put(raw, "subject/probe-1000.json.gz", [{"source": "A", "data": [A2]}])
    put(raw, "subject/page-0002.json.gz",
        [{"source": "A", "data": [A1]},
         {"source": "B", "errors": [{"kind": "NotFound", "message": "past the end"}]}])
    put(raw, "subject/page-0003.json.gz", [{"source": "A", "data": []}, {"source": "B", "data": []}])
    put(raw, "mapping/page-0001.json.gz", {"participant_ids": [E1, E2]})
    put(raw, "mapping/page-0002.json.gz", {"participant_ids": [E3]})
    put(raw, "mapping/page-0003.json.gz", b"Server Error.")
    put(raw, "fed/subject-summary.json.gz",
        [{"source": "A", "counts": {"total": 3}}, {"source": "B", "counts": {"total": 1}},
         {"source": "C", "counts": {}}])


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        make_snapshot(self.raw)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_records(self):
        snap = ccdi.read_snapshot(self.raw)
        self.assertEqual(snap["per_page"], 2)
        self.assertEqual(snap["records"], [REC_A1, REC_A2, REC_B1])
        self.assertEqual(snap["facts"], {"A": {"entries": 3, "repeats": 1, "error_pages": 0},
                                         "B": {"entries": 1, "repeats": 0, "error_pages": 1}})

    def test_links(self):
        snap = ccdi.read_snapshot(self.raw)
        self.assertEqual(snap["links"], LINKS)
        self.assertEqual(snap["link_counts"], {
            "association_not_an_object": 1, "link_rows": 3, "org_association": 1,
            "other_category_skipped": 1, "usi_association": 2, "usi_served_by_no_subject": 1})
        self.assertEqual(snap["mapping_entries"], 3)

    def test_pages_and_totals(self):
        snap = ccdi.read_snapshot(self.raw)
        self.assertEqual(snap["subject_pages"],
                         {1: {"A": 2, "B": 1}, 2: {"A": 1, "B": None}, 3: {"A": 0, "B": 0}})
        self.assertEqual(snap["mapping_pages"], {1: {"A": 1, "B": 1}, 2: {}, 3: None})
        self.assertEqual(snap["unmapped_mapping_entries"], 1)
        self.assertEqual(snap["totals"], {"A": 3, "B": 1})

    def test_check(self):
        result, rows = ccdi.check(self.raw, ("exact",))
        rep = result["linkcheck"]
        self.assertEqual(rep["rules"], ["exact"])
        self.assertEqual(rep["links"]["resolution"],
                         {"exact: new_pair": 2, "exact: self_reference": 1})
        self.assertEqual(rep["links"]["pairs_exact"], 2)
        oc = rep["overcount"]["exact"]
        self.assertEqual((oc["records"], oc["persons"], oc["naive_overcount"],
                          oc["persons_with_2plus_records_in_one_source"]), (3, 1, 2, 1))
        self.assertEqual(rep["conflicts"]["exact"]["all"]["sex"], {"agree": 1, "disagree": 1})
        self.assertEqual(rep["shared_ids"], {})
        self.assertEqual(len(rows), 1)
        subj_audit, map_audit = result["paging"]["subject"], result["paging"]["mapping"]
        self.assertEqual((subj_audit["flags"], subj_audit["refetch_pages"],
                          subj_audit["required_last_page"]), ([], [], 2))
        self.assertEqual(subj_audit["sources"]["B"]["errors_past_end"], 1)
        self.assertEqual(subj_audit["sources"]["A"]["unexplained"], 0)
        self.assertEqual(map_audit["flag_counts"], {"short": 2})
        self.assertEqual(map_audit["whole_page_failures"], [3])
        self.assertEqual(map_audit["refetch_pages"], [2])
        self.assertEqual(result["input"]["unmapped_mapping_entries"], 1)
        self.assertTrue(result["tool"].startswith("linkcheck ccdi 0.4.0"))

    def test_main(self):
        out = os.path.join(self.tmp, "result.json")
        recs = os.path.join(self.tmp, "records.jsonl")
        self.assertEqual(ccdi.main(["--raw", self.raw, "--out", out, "--records", recs]), 0)
        with open(out, encoding="utf-8") as fh:
            text = fh.read()
        result = json.loads(text)
        self.assertEqual(result["input"]["records"], 3)
        self.assertEqual(result["linkcheck"]["links"]["pairs_exact"], 2)
        for ident in ("PAAAAA", "StudyB", '"b1"', '"a2"'):
            self.assertNotIn(ident, text)
        with open(recs, encoding="utf-8") as fh:
            self.assertEqual(len(fh.read().splitlines()), 3)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "links.jsonl")))


class SeveralNamespaces(unittest.TestCase):
    def test_domain_name_of_several_namespaces(self):
        records = [{"source": "A", "id": "x", "namespace": "Shared", "alt_ids": []},
                   {"source": "B", "id": "y", "namespace": "Shared", "alt_ids": []}]
        entries = [{"domain_name": "shared", "participant_id": "y", "associated_ids": [
            {"domain_name": "Shared", "participant_id": "x",
             "domain_category": "organizational_identifier"},
            {"domain_name": "Shared", "participant_id": "q",
             "domain_category": "organizational_identifier"}]}]
        links, counts = ccdi.links_from(records, entries)
        self.assertEqual(links, [
            {"a_source": "B", "a_id": "y", "a_namespace": "Shared",
             "b_source": "A", "b_id": "x", "b_namespace": "Shared"},
            {"a_source": "B", "a_id": "y", "a_namespace": "Shared",
             "b_source": "A", "b_id": "q", "b_namespace": "Shared"}])
        self.assertEqual(counts, {"domain_name_of_several_namespaces": 3, "link_rows": 2,
                                  "org_association": 2})


if __name__ == "__main__":
    unittest.main()
