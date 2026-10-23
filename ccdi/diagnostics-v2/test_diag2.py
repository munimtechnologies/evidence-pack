"""Tests for the stage-2 post-hoc CCDI diagnostics, on made-up records only (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import analyze
import diag2


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel.endswith(".gz"):
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(obj).encode())
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def subj(org, ns, name, sex=None, vital=None, age=None, alt=(), extra=None):
    ids = [{"value": {"namespace": {"organization": org, "name": ns}, "name": n,
                      "type": "Linked"}} for n in (name,) + tuple(alt)]
    md = {"sex": {"value": sex} if sex else None, "race": [], "ethnicity": None,
          "vital_status": {"value": vital} if vital else None,
          "age_at_vital_status": {"value": age} if age is not None else None,
          "identifiers": ids}
    md.update(extra or {})
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "kind": "Participant", "metadata": md}


def org(dom, pid):
    return {"domain_name": dom, "participant_id": pid,
            "domain_category": "organizational_identifier"}


def fake_get(url):
    if "page=34&" in url:
        body = [{"source": "PCDC", "data": [subj("pcdc", "COG", "PCCCCC", "M")]}]
    elif "page=35&" in url:
        body = [{"source": "PCDC",
                 "errors": [{"kind": "NotFound", "message": "Server Error PAAAAA"}]}]
    else:
        body = [{"source": "CCDI-DCC", "data": []},
                {"source": "PCDC", "data": [subj("pcdc", "COG", "PNEWAA", "F")]}]
    return 200, json.dumps(body).encode(), 0.0


class Labels(unittest.TestCase):
    def test_link_label(self):
        self.assertEqual(diag2.link_label("COG_AALL0232_PCCCCC"), "COG_AALL0232_<USI>")
        self.assertEqual(diag2.link_label("COG_AAML03P1_PCCCCC"), "COG_AAML03P1_<USI>")
        self.assertEqual(diag2.link_label("THR01_0002"), "A{3}9{2}_9{4}")
        self.assertEqual(diag2.link_label("PXXXXB"), "<USI>")


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        raw = os.path.join(self.tmp, "raw")
        put(raw, "subject/chosen.json", {"per_page": 10, "first_page": "probe-10.json",
                                         "pages_expected": 1})
        put(raw, "subject/probe-10.json.gz", [
            {"source": "CCDI-DCC", "summary": {"counts": {"all": 2}},
             "data": [subj("dcc", "phs1", "PXXXXA", "M", "Alive", 900,
                           extra={"age_at_diagnosis": {"value": 100}}),
                      subj("dcc", "phs1", "PXXXXB", "F", "Dead", 300)]},
            {"source": "PCDC", "summary": {"counts": {"all": 1}},
             "data": [subj("pcdc", "COG", "PCCCCC", "M")]},
            {"source": "Treehouse", "summary": {"counts": {"all": 2}},
             "data": [subj("th", "treehouse", "TH-A", "F", alt=("THR01_0002",)),
                      subj("th", "treehouse", "0002", "M")]},
            {"source": "ccdi-ecDNA", "summary": {"counts": {"all": 1}},
             "data": [subj("ec", "sbp", "EC-1", "M", "Alive", 400)]}])
        put(raw, "mapping/page-0001.json.gz", {"participant_ids": [
            {"domain_name": "CCDI-DCC", "participant_id": "PXXXXA", "associated_ids": [
                org("ccdi-ecDNA", "EC-1"),
                org("PCDC", "COG_AALL0232_PCCCCC"),
                org("Treehouse", "THR01_0002"),
                org("ccdi-ecDNA", "PXXXXB"),
                org("ccdi-ecDNA", "PXXXXA"),
                org("KidsFirst", "pt-zzz")]}]})
        put(raw, "fetch-log.json", [{"file": "x", "status": 200}])
        self.raw, self.out = raw, os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_loose_links(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        entries = analyze.read_mappings(self.raw)
        by_dom, by_usi = analyze.fed_indexes(subjects)
        pairs, _, _ = analyze.mapping_links(entries, by_dom, by_usi)
        self.assertEqual(len(pairs), 1)
        r = diag2.loose_links(entries, subjects, by_dom, pairs)
        t = r["by_target_source"]
        self.assertEqual(t["PCDC"]["unresolved_links"], 1)
        self.assertEqual(t["PCDC"]["link_shapes"], [["COG_AALL0232_<USI>", 1]])
        self.assertEqual(t["PCDC"]["outcome"], {"after_last_underscore: new pair": 1})
        self.assertEqual(t["Treehouse"]["rules_matching"],
                         {"after_last_underscore": 1, "alt_identifier": 1})
        self.assertEqual(t["Treehouse"]["rule_agreement"], {"rules_disagree": 1})
        self.assertEqual(t["Treehouse"]["outcome"], {"alt_identifier: new pair": 1})
        self.assertEqual(t["ccdi-ecDNA"]["unresolved_links"], 2)
        self.assertEqual(t["ccdi-ecDNA"]["outcome"], {
            "name_in_other_source: another record of the linking source": 1,
            "name_in_other_source: the linking record itself": 1})
        self.assertEqual(t["ccdi-ecDNA"]["name_in_other_source_by_source"], {"CCDI-DCC": 2})
        self.assertNotIn("KidsFirst", t)
        n = r["new_pairs"]
        self.assertEqual(n["after_last_underscore"]["by_source_pair"]["CCDI-DCC | PCDC"]["sex"],
                         {"agree": 1})
        self.assertEqual(n["alt_identifier"]["by_source_pair"]["CCDI-DCC | Treehouse"]["sex"],
                         {"disagree": 1})
        self.assertEqual(n["all_rules"]["new_unique_pairs"], 2)
        self.assertEqual(n["all_rules"]["overcount_with_these_pairs"]["deduplicated_total"], 3)
        self.assertEqual(r["overcount_census"]["deduplicated_total"], 5)

    def test_metadata(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        entries = analyze.read_mappings(self.raw)
        by_dom, by_usi = analyze.fed_indexes(subjects)
        pairs, _, _ = analyze.mapping_links(entries, by_dom, by_usi)
        m = diag2.metadata(self.raw, pairs)
        self.assertEqual(m["served_records"], {"CCDI-DCC": 2, "PCDC": 1, "Treehouse": 2,
                                               "ccdi-ecDNA": 1})
        dcc = m["filled_keys"]["CCDI-DCC"]
        self.assertEqual((dcc["sex"], dcc["age_at_diagnosis"]), (2, 1))
        self.assertNotIn("race", dcc)
        ages = m["ecDNA_age_differences_days"]
        same = ages["CCDI-DCC: ecDNA age_at_vital_status minus age_at_vital_status"]
        self.assertEqual((same["n"], same["median"], same["ratio_median"]), (1, -500, 0.444))
        dx = ages["CCDI-DCC: ecDNA age_at_vital_status minus age_at_diagnosis"]
        self.assertEqual((dx["median"], dx["within_365_days"]), (300, 1))

    def test_probe(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        rows = diag2.probe(subjects, get=fake_get, pause=0)
        self.assertEqual(len(rows), 18)
        self.assertEqual(rows[0], {"page": 34, "per_page": 100, "status": 200, "records": 1,
                                   "not_in_snapshot": 0})
        self.assertIsNone(rows[1]["records"])
        self.assertIn("NotFound", rows[1]["error"])
        self.assertNotIn("PAAAAA", rows[1]["error"])
        self.assertEqual((rows[2]["page"], rows[2]["per_page"], rows[2]["not_in_snapshot"]),
                         (69, 50, 1))

    def test_main(self):
        diag2.main(["--raw", self.raw, "--out", self.out])
        with open(os.path.join(self.out, "diagnostics2.json"), encoding="utf-8") as fh:
            text = fh.read()
        r = json.loads(text)
        self.assertTrue(r["label"].startswith("POST HOC"))
        self.assertEqual(r["snapshot_check"], {"subjects": 6, "mapping_entries": 1, "pairs": 1,
                                               "entry_unresolved": 0})
        self.assertNotIn("page35_probe", r)
        for ident in ("PXXXXA", "PXXXXB", "PCCCCC", "EC-1", "TH-A", "THR01"):
            self.assertNotIn(ident, text)

    def test_missing_snapshot(self):
        with self.assertRaises(SystemExit):
            diag2.main(["--raw", os.path.join(self.tmp, "nope"), "--out", self.out])


if __name__ == "__main__":
    unittest.main()
