"""Tests for the post-hoc CCDI diagnostics, on made-up records only (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import diag


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel.endswith(".gz"):
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(obj).encode())
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def subj(org, ns, name, sex=None, vital=None, age=None, alt=()):
    ids = [{"value": {"namespace": {"organization": org, "name": ns}, "name": n,
                      "type": "Linked"}} for n in (name,) + tuple(alt)]
    md = {"sex": {"value": sex} if sex else None, "race": [], "ethnicity": None,
          "vital_status": {"value": vital} if vital else None,
          "age_at_vital_status": {"value": age} if age is not None else None,
          "identifiers": ids}
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "kind": "Participant", "metadata": md}


class Helpers(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(diag.shape("PT_00A"), "A{2}_9{2}A")
        self.assertEqual(diag.shape("PAAAAA"), "A{6}")
        self.assertEqual(diag.shape("pt-1"), "a{2}-9")

    def test_scrub(self):
        text = diag.scrub("NotFound: cohort too small for PAAAAA in sd-12345")
        self.assertNotIn("PAAAAA", text)
        self.assertNotIn("12345", text)
        self.assertIn("NotFound", text)

    def test_quantiles(self):
        q = diag.quantiles([5, 1, 3])
        self.assertEqual((q["n"], q["min"], q["median"], q["max"]), (3, 1, 3, 5))
        self.assertIsNone(diag.quantiles([]))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        raw = os.path.join(self.tmp, "raw")
        put(raw, "subject/chosen.json", {"per_page": 2, "first_page": "probe-2.json",
                                         "pages_expected": 2})
        put(raw, "subject/probe-2.json.gz", [
            {"source": "PCDC",
             "errors": [{"kind": "NotFound", "message": "cohort too small PAAAAA 12345"}]},
            {"source": "CCDI-DCC", "summary": {"counts": {"all": 2, "current": 2}},
             "data": [subj("dcc", "phs1", "PXXXXA", "M", "Alive", 900),
                      subj("dcc", "phs1", "PXXXXB", "F", "Dead", 100)]},
            {"source": "ccdi-ecDNA", "summary": {"counts": {"all": 1, "current": 1}},
             "data": [subj("ec", "ecDNA", "EC-1", "F", "Dead", 500)]}])
        put(raw, "subject/page-0002.json.gz", [
            {"source": "PCDC", "summary": {"counts": {"all": 3, "current": 1}},
             "data": [subj("pcdc", "COG", "PCCCCC", None, None, None, alt=("pcdc-00007",))]},
            {"source": "CCDI-DCC", "summary": {"counts": {"all": 2, "current": 0}}, "data": []},
            {"source": "ccdi-ecDNA", "summary": {"counts": {"all": 1, "current": 0}},
             "errors": [{"kind": "InvalidParameters"}]}])
        put(raw, "mapping/page-0001.json.gz", {"participant_ids": [
            {"domain_name": "CCDI-DCC", "participant_id": "PXXXXA", "associated_ids": [
                {"participant_id": "EC-1", "domain_name": "ccdi-ecDNA",
                 "domain_category": "organizational_identifier"},
                {"participant_id": "pcdc-00007", "domain_name": "PCDC",
                 "domain_category": "organizational_identifier"}]}]})
        put(raw, "fetch-log.json", [{"file": "x", "status": 200}])
        self.raw, self.out = raw, os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_failed_pages_in_range_only(self):
        rows = diag.failed_pages(self.raw)
        self.assertEqual([(r["source"], r["page"]) for r in rows], [("PCDC", 1)])
        self.assertNotIn("PAAAAA", rows[0]["message"])
        self.assertIn("errors", rows[0]["keys"])

    def test_run(self):
        keep = os.path.join(self.tmp, "keep")
        diag.main(["--raw", self.raw, "--out", self.out, "--keep", keep])
        self.assertTrue(os.path.exists(os.path.join(keep, "subject", "chosen.json")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "snapshot2", "concordance.json")))
        text = open(os.path.join(self.out, "diagnostics.json"), encoding="utf-8").read()
        r = json.loads(text)
        p = r["pairs"]
        ages = p["age_difference_days_second_minus_first"]["CCDI-DCC | ccdi-ecDNA"]
        self.assertEqual(ages["Alive/Dead"]["median"], -400)
        self.assertEqual(ages["Alive/Dead"]["first_older"], 1)
        self.assertEqual(p["vital_disagreement_direction"],
                         {"CCDI-DCC | ccdi-ecDNA": {"CCDI-DCC=Alive, ccdi-ecDNA=Dead": 1}})
        self.assertEqual(p["sex_disagreements"],
                         {"CCDI-DCC [phs1] M vs ccdi-ecDNA [ecDNA] F": 1})
        u = r["unresolved_links"]["PCDC"]
        self.assertEqual(u["unresolved_links"], 1)
        self.assertEqual(u["would_resolve_by"]["alt_identifier_in_source"], 1)
        self.assertEqual(u["would_resolve_by"]["case_insensitive_name"], 0)
        self.assertEqual(u["served_name_shapes"], [["A{6}", 1]])
        m = r["missing_by_namespace"]["PCDC"]["top_by_sex_null"][0]
        self.assertEqual((m["ns"], m["records"], m["sex_null"]), ("COG", 1, 1))
        self.assertTrue(r["label"].startswith("POST HOC"))
        for ident in ("PXXXXA", "PXXXXB", "EC-1", "pcdc-00007", "PCCCCC", "PAAAAA", "12345"):
            self.assertNotIn(ident, text)


if __name__ == "__main__":
    unittest.main()
