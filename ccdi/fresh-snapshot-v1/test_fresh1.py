"""Tests for fresh1.py, on the made-up snapshot of test_repro2.py only (no network). Every
expected number was worked out by hand before the first run.

The made-up snapshot has one CCDI-DCC name (USI-shaped) served in two namespaces, phs1 and
phs2. The census links the phs2 record to PCDC and, in the ambiguous variant, the phs1
record to another PCDC record.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

import analyze
import fresh1
from test_repro2 import make_snapshot, put

ONE = {"pairs": 1, "sex": {"agree": 1}, "ethnicity": {"uninformative": 1},
       "race": {"agree": 1}, "vital": {"uninformative": 1}, "death_age": {}}
NONE = {"sex": 0, "ethnicity": 0, "race": 0, "vital": 0, "death_age": 0}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def described(self, ambiguous=False):
        raw = os.path.join(self.tmp, "raw")
        make_snapshot(raw, ambiguous)
        _, _, subjects, _ = analyze.read_subjects(raw)
        return fresh1.describe(subjects, analyze.read_mappings(raw))


class Describe(Base):
    def test_one_record_linked(self):
        d = self.described()
        self.assertEqual(d["groups"], 1)
        self.assertEqual(d["extra_records"], {"CCDI-DCC": 1})
        self.assertEqual(d["group_sizes"], {"2": 1})
        self.assertEqual(d["same_namespace_name"], 0)
        self.assertEqual(d["groups_by_name_shape"], {"usi": 1})
        self.assertEqual(d["agreement_by_name_shape"], {"usi": ONE})
        self.assertEqual(d["conflicts_by_name_shape"], {"usi": NONE})
        self.assertEqual(d["namespace_pairs"], {"phs1 | phs2": 1})
        self.assertEqual(d["linkage"], {"only_some_in_links": 1})
        self.assertEqual(d["census_persons"], 6)
        self.assertEqual(d["persons_if_shared_names_are_one_person"], 5)

    def test_two_records_in_different_persons(self):
        d = self.described(ambiguous=True)
        self.assertEqual(d["linkage"], {"different_persons_by_links": 1})
        self.assertEqual(d["census_persons"], 5)
        self.assertEqual(d["persons_if_shared_names_are_one_person"], 4)

    def test_persons_matches_section_d(self):
        raw = os.path.join(self.tmp, "raw")
        make_snapshot(raw, True)
        _, _, subjects, _ = analyze.read_subjects(raw)
        by_dom, by_usi = analyze.fed_indexes(subjects)
        pairs, _, _ = analyze.mapping_links(analyze.read_mappings(raw), by_dom, by_usi)
        self.assertEqual(fresh1.persons(len(subjects), pairs),
                         analyze.section_d(subjects, pairs)["deduplicated_total"])


class Grade(unittest.TestCase):
    def shared(self, **change):
        s = dict(fresh1.SHARED2, groups_by_name_shape={"other": 46, "usi": 41},
                 conflicts_by_name_shape={"other": dict(NONE), "usi": dict(NONE)})
        s.update(change)
        return s

    def test_all_pass(self):
        g = fresh1.grade(dict(fresh1.TOTALS2), self.shared())
        self.assertEqual({k: v["grade"] for k, v in g.items()},
                         {"G1": "pass", "G2": "pass", "G3": "pass"})

    def test_misses(self):
        totals = dict(fresh1.TOTALS2, PCDC=24433)
        shared = self.shared(groups=88, conflicts_by_name_shape={
            "other": dict(NONE, sex=1), "usi": dict(NONE)})
        g = fresh1.grade(totals, shared)
        self.assertEqual(g["G1"]["grade"], "fail")
        self.assertEqual(g["G1"]["observed"]["differing"], ["PCDC"])
        self.assertEqual(g["G2"]["grade"], "fail")
        self.assertEqual(g["G3"]["grade"], "fail")
        self.assertEqual(g["G3"]["observed"]["conflicts"], {"other": {"sex": 1}})

    def test_one_shape_only_fails_g3(self):
        g = fresh1.grade(dict(fresh1.TOTALS2), self.shared(
            groups_by_name_shape={"usi": 87}, conflicts_by_name_shape={"usi": dict(NONE)}))
        self.assertEqual(g["G3"]["grade"], "fail")


class Main(Base):
    def fresh_root(self):
        root = os.path.join(self.tmp, "fresh")
        snap = os.path.join(root, "ccdi-raw-fresh-20261024T000000Z")
        make_snapshot(snap)
        put(snap, "complete.json", {"requests": 4})
        return root

    def test_main(self):
        out = os.path.join(self.tmp, "out")
        fresh1.main(["--fresh-root", self.fresh_root(), "--kept",
                     os.path.join(self.tmp, "none"), "--out", out])
        with open(os.path.join(out, "fresh1.json"), encoding="utf-8") as fh:
            text = fh.read()
        r = json.loads(text)
        self.assertEqual(r["fresh_snapshot"], "ccdi-raw-fresh-20261024T000000Z")
        self.assertEqual(r["fresh"]["totals"],
                         {"CCDI-DCC": 3, "PCDC": 2, "Treehouse": 2, "StJude": 1})
        self.assertEqual({k: v["grade"] for k, v in r["grades"].items()},
                         {"G1": "fail", "G2": "fail", "G3": "fail"})
        self.assertNotIn("kept_second_snapshot", r)
        self.assertNotIn("PBBBBB", text)

    def test_main_describes_kept_snapshot(self):
        kept = os.path.join(self.tmp, "kept")
        make_snapshot(kept, True)
        out = os.path.join(self.tmp, "out")
        fresh1.main(["--fresh-root", self.fresh_root(), "--kept", kept, "--out", out])
        with open(os.path.join(out, "fresh1.json"), encoding="utf-8") as fh:
            r = json.load(fh)
        self.assertEqual(r["kept_second_snapshot"]["shared_names"]["linkage"],
                         {"different_persons_by_links": 1})

    def test_no_fresh_snapshot(self):
        with self.assertRaises(SystemExit):
            fresh1.main(["--fresh-root", os.path.join(self.tmp, "fresh"),
                         "--out", os.path.join(self.tmp, "out")])


if __name__ == "__main__":
    unittest.main()
