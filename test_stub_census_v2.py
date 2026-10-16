# Offline tests for stub_census_v2.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import csv
import json
import os
import tempfile
import unittest
from unittest import mock

import stub_census as sc
import stub_census_v2 as v2


def work(wid, doi, citers, mag=True, pmid=None, stype="repository", name="Some Repository"):
    ids = {"openalex": "https://openalex.org/" + wid, "doi": "https://doi.org/" + doi}
    if mag:
        ids["mag"] = wid[1:]
    if pmid:
        ids["pmid"] = "https://pubmed.ncbi.nlm.nih.gov/" + pmid
    loc = {"source": {"type": stype, "display_name": name}} if stype else {"source": None}
    return {"id": "https://openalex.org/" + wid, "doi": "https://doi.org/" + doi, "ids": ids,
            "display_name": "T " + wid, "publication_year": 2010, "cited_by_count": citers, "type": "article",
            "primary_location": loc}


def row(stub, citers, known=False, reg=False, mag=True, pmid="", stype="repository", rid="W1"):
    return {"stub": stub, "kind": "dash", "known": known, "id": rid, "citers": citers, "registered_in_crossref": reg,
            "has_mag": mag, "pmid": pmid, "source_type": stype}


class Rows(unittest.TestCase):
    def test_fields(self):
        r = v2.record_row(work("W123", "10.1136/bmjopen", 2230, mag=True, pmid="24238553"), "10.1136/bmjopen",
                          "dash", True)
        self.assertEqual(r["id"], "W123")
        self.assertTrue(r["has_mag"])
        self.assertEqual(r["pmid"], "24238553")
        self.assertEqual(r["source_type"], "repository")
        self.assertEqual(r["citers"], 2230)
        self.assertIsNone(r["registered_in_crossref"])

    def test_missing_location_and_ids(self):
        w = work("W9", "10.1111/j.1365", 5, mag=False, stype=None)
        w["primary_location"] = None
        r = v2.record_row(w, "10.1111/j.1365", "dash", False)
        self.assertFalse(r["has_mag"])
        self.assertEqual(r["pmid"], "")
        self.assertEqual(r["source_type"], "")
        self.assertEqual(r["source_name"], "")

    def test_known_list(self):
        self.assertEqual(len(v2.KNOWN), 73)
        self.assertEqual(len(set(v2.KNOWN)), 73)
        self.assertIn("10.1016/s0140", v2.KNOWN)
        self.assertIn("10.9790/3008", v2.KNOWN)


class Scoring(unittest.TestCase):
    def test_h1_counts_unregistered_new_stems_once(self):
        rows = [row("10.1/a%d" % i, 5) for i in range(9)] + [row("10.1/a0", 3, rid="W2")]
        rows += [row("10.1/k", 5, known=True), row("10.1/r", 5, reg=True)]
        v, new = v2.score_h1(rows)
        self.assertEqual(len(new), 9)
        self.assertEqual(v, "not supported")
        v, new = v2.score_h1(rows + [row("10.1/a9", 1)])
        self.assertEqual((v, len(new)), ("supported", 10))

    def test_h1_skips_unchecked_registration(self):
        rows = [row("10.1/a%d" % i, 5, reg=None) for i in range(12)]
        self.assertEqual(v2.score_h1(rows)[0], "not supported")

    def test_h2_citation_weighted(self):
        rows = [row("10.1/a", 60, mag=True), row("10.1/b", 40, mag=False), row("10.1/c", 1000, reg=True, mag=False)]
        v, d = v2.score_h2(rows)
        self.assertEqual((v, d["citations"], d["on_mag"]), ("supported", 100, 60))
        rows[0]["citers"] = 59
        self.assertEqual(v2.score_h2(rows)[0], "not supported")
        self.assertEqual(v2.score_h2([row("10.1/a", 0)])[0], "untestable")

    def test_h3_pmid(self):
        rows = [row("10.1/a", 5, pmid="1"), row("10.1/b", 5, pmid="2"), row("10.1/c", 5, pmid="3", reg=True)]
        self.assertEqual(v2.score_h3(rows)[0], "supported")
        rows.append(row("10.1/d", 5, pmid="4", rid="W4"))
        v, ids = v2.score_h3(rows)
        self.assertEqual((v, len(ids)), ("not supported", 3))

    def test_h4_missing_source_counts_as_not_journal(self):
        rows = [row("10.1/a", 50, stype="journal"), row("10.1/b", 50, stype=""), row("10.1/c", 49, stype="")]
        v, d = v2.score_h4(rows)
        self.assertEqual((v, d["n"], d["not_journal"]), ("supported", 2, 1))
        rows[1]["source_type"] = "journal"
        self.assertEqual(v2.score_h4(rows)[0], "not supported")
        self.assertEqual(v2.score_h4([row("10.1/a", 10)])[0], "untestable")


class EndToEnd(unittest.TestCase):
    def test_main_offline(self):
        sample = [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1234/abc-2020-1"},
                  {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1016/S0140-6736(20)1"}]
        found = [work("W10", "10.1234/abc", 120, mag=False, stype="journal"),
                 work("W11", "10.1016/s0140", 22520, mag=True),
                 work("W12", "10.1136/annrheumdis", 712, mag=False, stype="")]
        registered = {"10.1136/annrheumdis"}
        seen = {}

        def fake_lookup(stubs, *a, **k):
            seen["stubs"] = stubs
            return found, True

        def fake_oa(params, *a, **k):
            return {"meta": {"count": 10}, "group_by": [{"key": "x", "key_display_name": "Wiley", "count": 4}]}

        old_select = sc.SELECT
        try:
            with mock.patch.object(sc, "sampled", lambda *a, **k: (sample, True)), \
                    mock.patch.object(sc, "lookup", fake_lookup), \
                    mock.patch.object(sc, "oa", fake_oa), \
                    mock.patch.object(sc, "crossref", lambda d: {} if d in registered else None), \
                    tempfile.TemporaryDirectory() as td:
                v2.main(["--out-dir", td])
                with open(os.path.join(td, "results.json"), encoding="utf-8") as f:
                    res = json.load(f)
                with open(os.path.join(td, "stub_blocklist.csv"), encoding="utf-8") as f:
                    csv_rows = list(csv.DictReader(f))
                self.assertTrue(os.path.exists(os.path.join(td, "stub_records_v2.jsonl")))
        finally:
            sc.SELECT = old_select
        self.assertIn("10.1234/abc", seen["stubs"])
        self.assertIn("10.1016/s0140-6736", seen["stubs"])
        self.assertIn("10.9790/3008", seen["stubs"])
        self.assertEqual(res["sample"]["stems"], 3)
        self.assertEqual(res["sample"]["known_stems_in_sample"], 2)
        self.assertEqual(res["records"], {"all": 3, "unregistered": 2, "new": 1, "new_unregistered": 1})
        self.assertEqual(res["citations_absorbed"]["new_unregistered"], 120)
        self.assertEqual(res["H1_new_unregistered"], ["10.1234/abc"])
        self.assertEqual(res["H2_detail"]["on_mag"], 22520)
        self.assertEqual(res["H4_detail"], {"n": 2, "not_journal": 1})
        self.assertEqual([r["id"] for r in csv_rows], ["W11", "W12", "W10"])
        self.assertEqual(csv_rows[2]["wiley_share"], "0.4")
        self.assertEqual(csv_rows[0]["wiley_share"], "")


if __name__ == "__main__":
    unittest.main()
