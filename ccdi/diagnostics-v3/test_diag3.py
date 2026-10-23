"""Tests for the stage-3 post-hoc CCDI diagnostics, on made-up records only (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest
import urllib.parse

import analyze
import diag3


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel.endswith(".gz"):
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(obj).encode())
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def subj(org, ns, name, sex=None):
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "kind": "Participant",
            "metadata": {"sex": {"value": sex} if sex else None, "race": [],
                         "ethnicity": None, "vital_status": None,
                         "age_at_vital_status": None, "identifiers": []}}


ERROR = {"kind": "NotFound", "message": "Server Error PAAAAA"}


def fake_get(url):
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query)
    key = (int(q["page"][0]), int(q["per_page"][0]))
    if u.path.endswith("/subject-mapping"):
        body = {"participant_ids": [
            {"domain_name": "PCDC", "participant_id": "PNEWAA"},
            {"domain_name": "CCDI-DCC", "participant_id": "PXXXXA"},
            {"domain_name": "odd-node", "participant_id": "PODDAA"}]}
        if key == (35, 100):
            body["errors"] = [ERROR]
        return 200, json.dumps(body).encode(), 0.0
    if key in ((347, 10), (3463, 1)):
        pcdc = {"source": "PCDC", "errors": [ERROR]}
    elif key == (3460, 1):
        pcdc = {"source": "PCDC", "data": [subj("pcdc", "COG", "PCCCCC", "M")]}
    else:
        pcdc = {"source": "PCDC", "data": [subj("pcdc", "COG", "PNEWAA", "F")]}
    return 200, json.dumps([{"source": "CCDI-DCC", "data": []}, pcdc]).encode(), 0.0


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        raw = os.path.join(self.tmp, "raw")
        put(raw, "subject/chosen.json", {"per_page": 10, "first_page": "probe-10.json",
                                         "pages_expected": 1})
        put(raw, "subject/probe-10.json.gz", [
            {"source": "CCDI-DCC", "summary": {"counts": {"all": 1}},
             "data": [subj("dcc", "phs1", "PXXXXA", "M")]},
            {"source": "PCDC", "summary": {"counts": {"all": 1}},
             "data": [subj("pcdc", "COG", "PCCCCC", "M")]}])
        put(raw, "mapping/page-0001.json.gz", {"participant_ids": [
            {"domain_name": "CCDI-DCC", "participant_id": "PXXXXA", "associated_ids": []},
            {"domain_name": "PCDC", "participant_id": "PCCCCC", "associated_ids": []}]})
        self.raw, self.out = raw, os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read_out(self):
        with open(os.path.join(self.out, "diagnostics3.json"), encoding="utf-8") as fh:
            text = fh.read()
        return text, json.loads(text)

    def test_subject_probe(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        rows = diag3.subject_probe(subjects, get=fake_get, pause=0)
        self.assertEqual(len(rows), 21)
        self.assertEqual((rows[0]["page"], rows[0]["per_page"], rows[0]["records"]),
                         (347, 10, None))
        self.assertIn("NotFound", rows[0]["error"])
        self.assertNotIn("PAAAAA", rows[0]["error"])
        self.assertEqual(rows[1], {"page": 3456, "per_page": 1, "status": 200, "records": 1,
                                   "not_in_snapshot": 1})
        self.assertEqual((rows[5]["page"], rows[5]["not_in_snapshot"]), (3460, 0))
        self.assertIsNone(rows[8]["records"])

    def test_subject_probe_without_snapshot(self):
        seen = set()
        rows = diag3.subject_probe(None, get=fake_get, pause=0, seen=seen)
        self.assertEqual(rows[1], {"page": 3456, "per_page": 1, "status": 200, "records": 1,
                                   "not_in_snapshot": None})
        self.assertIsNone(rows[8]["records"])
        self.assertEqual(seen, {"CCDI-DCC", "PCDC"})

    def test_mapping_probe(self):
        _, _, subjects, _ = analyze.read_subjects(self.raw)
        entries = analyze.read_mappings(self.raw)
        sources = {s["source"] for s in subjects.values()}
        rows = diag3.mapping_probe(entries, sources, get=fake_get, pause=0)
        self.assertEqual(len(rows), 34)
        self.assertEqual(rows[0]["entries"], {"CCDI-DCC": 1, "PCDC": 1, "other": 1})
        self.assertEqual(rows[0]["not_in_snapshot"], {"PCDC": 1, "other": 1})
        self.assertNotIn("other_keys", rows[0])
        self.assertIn("NotFound", rows[1]["other_keys"])
        self.assertNotIn("PAAAAA", rows[1]["other_keys"])
        self.assertEqual((rows[-1]["page"], rows[-1]["per_page"]), (3475, 1))

    def test_mapping_probe_without_snapshot(self):
        rows = diag3.mapping_probe(None, {"CCDI-DCC", "PCDC"}, get=fake_get, pause=0)
        self.assertEqual(rows[0]["entries"], {"CCDI-DCC": 1, "PCDC": 1, "other": 1})
        self.assertIsNone(rows[0]["not_in_snapshot"])
        self.assertIn("NotFound", rows[1]["other_keys"])

    def test_main(self):
        diag3.main(["--raw", self.raw, "--out", self.out], get=fake_get, pause=0)
        text, r = self.read_out()
        self.assertTrue(r["label"].startswith("POST HOC"))
        self.assertEqual(r["snapshot_check"], {"found": True, "subjects": 2, "mapping_entries": 2})
        self.assertEqual(r["sources"], ["CCDI-DCC", "PCDC"])
        self.assertEqual(r["failing_positions_at_per_page_1"], [3463])
        for ident in ("PXXXXA", "PCCCCC", "PNEWAA", "PODDAA", "PAAAAA", "odd-node"):
            self.assertNotIn(ident, text)

    def test_missing_snapshot(self):
        with self.assertRaises(SystemExit):
            diag3.main(["--raw", os.path.join(self.tmp, "nope"), "--out", self.out],
                       get=fake_get, pause=0)

    def test_main_allow_missing_snapshot(self):
        diag3.main(["--raw", os.path.join(self.tmp, "nope"), "--out", self.out,
                    "--allow-missing-snapshot"], get=fake_get, pause=0)
        text, r = self.read_out()
        self.assertEqual(r["snapshot_check"], {"found": False})
        self.assertEqual(r["sources"], ["CCDI-DCC", "PCDC"])
        self.assertEqual(r["failing_positions_at_per_page_1"], [3463])
        self.assertIsNone(r["mapping_probe"][0]["not_in_snapshot"])
        self.assertEqual(r["mapping_probe"][0]["entries"], {"CCDI-DCC": 1, "PCDC": 1, "other": 1})
        for ident in ("PXXXXA", "PCCCCC", "PNEWAA", "PODDAA", "PAAAAA", "odd-node"):
            self.assertNotIn(ident, text)


if __name__ == "__main__":
    unittest.main()
