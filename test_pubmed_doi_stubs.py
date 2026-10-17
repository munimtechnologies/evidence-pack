# Offline tests for pubmed_doi_stubs.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import csv
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import pubmed_doi_stubs as pds


def article(pmid, doi, pii, title, year="2005", ref_doi="10.1000/ref-1", medline_date=False):
    date = "<MedlineDate>%s Jan-Feb</MedlineDate>" % year if medline_date else "<Year>%s</Year>" % year
    return ("<PubmedArticle><MedlineCitation><PMID Version=\"1\">%s</PMID><Article><Journal><ISSN>0197-2510</ISSN>"
            "<JournalIssue><PubDate>%s</PubDate></JournalIssue><ISOAbbreviation>JEMS</ISOAbbreviation></Journal>"
            "<ArticleTitle>%s</ArticleTitle></Article></MedlineCitation><PubmedData><ArticleIdList>"
            "<ArticleId IdType=\"pubmed\">%s</ArticleId><ArticleId IdType=\"doi\">%s</ArticleId>"
            "<ArticleId IdType=\"pii\">%s</ArticleId></ArticleIdList><ReferenceList><Reference><Citation>x</Citation>"
            "<ArticleIdList><ArticleId IdType=\"doi\">%s</ArticleId></ArticleIdList></Reference></ReferenceList>"
            "</PubmedData></PubmedArticle>") % (pmid, date, title, pmid, doi, pii, ref_doi)


def xml(*arts):
    return ("<?xml version=\"1.0\" ?><!DOCTYPE PubmedArticleSet PUBLIC \"-//NLM//DTD PubMedArticle, 1st January 2025//EN\" "
            "\"https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd\"><PubmedArticleSet>%s</PubmedArticleSet>"
            % "".join(arts)).encode("utf-8")


class FakeEu:
    def __init__(self, answer):
        self.answer, self.terms = answer, []

    def search(self, term, retmax=0):
        self.terms.append(term)
        return self.answer(term)


class Basics(unittest.TestCase):
    def test_pii_to_doi(self):
        self.assertEqual(pds.pii_to_doi("S0091674903020116"), "10.1016/S0091-6749(03)02011-6")
        self.assertEqual(pds.pii_to_doi("S0197457203003586"), "10.1016/S0197-4572(03)00358-6")
        self.assertEqual(pds.pii_to_doi("S000287030300468X"), "10.1016/S0002-8703(03)00468-X")
        self.assertEqual(pds.pii_to_doi("s0002-8703(03)00468-x"), "10.1016/S0002-8703(03)00468-X")
        self.assertEqual(pds.pii_to_doi("0002-9343(83)90123-4"), "")
        self.assertEqual(pds.pii_to_doi(""), "")
        self.assertEqual(pds.pii_to_doi(None), "")

    def test_stems(self):
        s = pds.elsevier_stems()
        self.assertEqual(len(s), 20000)
        self.assertEqual(len(set(s)), 20000)
        self.assertIn("10.1016/S0197", s)
        self.assertIn("10.1016/0002", s)
        self.assertEqual(s[0], "10.1016/S0000")

    def test_norm_and_phrase(self):
        self.assertEqual(pds.phrase("10.1016/S0197"), '"10.1016/S0197"[aid]')
        self.assertEqual(pds.norm('"10.1016/S0197"[aid]'), "10.1016/s0197")
        self.assertEqual(pds.norm('"10.1016/S0197"'), "10.1016/s0197")
        self.assertEqual(pds.norm("10.1016/S0197"), "10.1016/s0197")

    def test_title_match(self):
        self.assertTrue(pds.title_match("Gerontologic nurse practitioner care guideline: COPD in the older adult.",
                                        ["Gerontologic nurse practitioner care guideline"]))
        self.assertTrue(pds.title_match("Airway inflammation in chronic obstructive pulmonary disease: comparisons "
                                        "with asthma.", ["Airway inflammation in chronic obstructive pulmonary disease"]))
        self.assertFalse(pds.title_match("Airway inflammation in chronic obstructive pulmonary disease.",
                                         ["30 of the most innovative new products from EMS today"]))
        self.assertIsNone(pds.title_match("On it.", ["anything"]))
        self.assertEqual(pds.title_words("Care, care and CARE with data"), ["care", "data"])


class Screening(unittest.TestCase):
    def test_matched_from_translation(self):
        res = {"count": "40", "querytranslation": '"10.1016/S0197"[Publisher ID] OR "10.1016/S0091"[Publisher ID]'}
        g = ["10.1016/S0091", "10.1016/S0140", "10.1016/S0197"]
        self.assertEqual(pds.matched_in(res, g), ["10.1016/S0091", "10.1016/S0197"])

    def test_matched_fallback_to_not_found(self):
        res = {"count": "3", "querytranslation": "",
               "warninglist": {"phrasesnotfound": ['"10.1016/S0140"[aid]', "10.1016/S0022"]}}
        g = ["10.1016/S0002", "10.1016/S0022", "10.1016/S0140"]
        self.assertEqual(pds.matched_in(res, g), ["10.1016/S0002"])
        self.assertEqual(pds.matched_in({"count": "1"}, g), g)

    def test_screen_groups_and_failures(self):
        stems = ["10.1016/S%04d" % i for i in range(120)]

        def answer(term):
            if '"10.1016/S0050"' in term:
                return None
            if '"10.1016/S0101"' in term:
                return {"count": "2", "querytranslation": '"10.1016/S0101"[Publisher ID]'}
            return {"count": "0", "idlist": [], "errorlist": {"phrasesnotfound": []}}

        eu = FakeEu(answer)
        cands, failed = pds.screen(eu, stems, group=50)
        self.assertEqual(len(eu.terms), 3)
        self.assertEqual(eu.terms[0].count(" OR "), 49)
        self.assertEqual((cands, failed), (["10.1016/S0101"], 1))


class Parsing(unittest.TestCase):
    def test_parse_reads_own_ids_only(self):
        raw = xml(article("15902073", "10.1016/S0197", "S0197251005001234", "Don't <i>be</i> shocked."),
                  article("14976499", "10.1016/S0197", "S019745720300243X", "Nursing older people", year="2004",
                          medline_date=True))
        recs = pds.parse_pubmed_xml(raw)
        self.assertEqual(len(recs), 2)
        r = recs[0]
        self.assertEqual((r["pmid"], r["doi"], r["pii"], r["year"]), ("15902073", "10.1016/S0197", "S0197251005001234",
                                                                      2005))
        self.assertEqual(r["title"], "Don't be shocked.")
        self.assertEqual((r["journal"], r["issn"], r["eloc_doi"]), ("JEMS", "0197-2510", ""))
        self.assertEqual(recs[1]["year"], 2004)
        self.assertEqual(pds.parse_pubmed_xml(b"<not xml"), [])


class Scoring(unittest.TestCase):
    def rec(self, year, elsevier=True):
        return {"year": year, "elsevier": elsevier}

    def test_h1(self):
        rs = [self.rec(2004)] * 299 + [self.rec(2004, False)] * 5
        self.assertEqual(pds.score_h1(rs), ("not supported", {"n": 299}))
        self.assertEqual(pds.score_h1(rs + [self.rec(2004)])[0], "supported")

    def test_h2(self):
        rs = [self.rec(2004)] * 24 + [self.rec(2010)] * 6
        v, d = pds.score_h2(rs)
        self.assertEqual((v, d["in_window"], d["n"]), ("supported", 24, 30))
        self.assertEqual(pds.score_h2(rs + [self.rec(2011)])[0], "not supported")
        self.assertEqual(pds.score_h2(rs[:29] + [self.rec(None)])[0], "untestable")

    def test_h3(self):
        ok = {"status": "registered_match"}
        checks = [ok] * 18 + [{"status": "unregistered"}, {"status": "registered_mismatch"},
                              {"status": "no_title_words"}]
        v, d = pds.score_h3(checks)
        self.assertEqual((v, d["testable"], d["registered_match"]), ("supported", 20, 18))
        self.assertEqual(pds.score_h3(checks + [{"status": "unregistered"}])[0], "not supported")
        self.assertEqual(pds.score_h3([ok] * 19)[0], "untestable")

    def test_h4(self):
        looked = [str(i) for i in range(50)]
        found = {str(i): {} for i in range(35)}
        v, d = pds.score_h4(looked, found)
        self.assertEqual((v, d["not_found"]), ("supported", 15))
        found["35"] = {}
        self.assertEqual(pds.score_h4(looked, found)[0], "not supported")
        self.assertEqual(pds.score_h4(looked[:49], {})[0], "untestable")


class EndToEnd(unittest.TestCase):
    def test_main_offline(self):
        efetch = xml(article("15902073", "10.1016/S0197", "S0197251005001234", "Don't be shocked."),
                     article("15902076", "10.1016/S0197", "S0197251005005678", "The greatest volunteer of all."),
                     article("999", "10.1016/S0197-4572(03)00358-6", "S0197457203003586", "A full DOI"))
        calls = {"cr": [], "oa": []}

        def fake_http(url, data=None, *a, **k):
            if url.startswith(pds.EU + "esearch"):
                hit = '"10.1016/S0197"[aid]' in data["term"]
                r = {"count": "3" if hit else "0", "idlist": ["15902073", "15902076", "999"] if hit else [],
                     "querytranslation": '"10.1016/S0197"[Publisher ID]' if hit else ""}
                return json.dumps({"esearchresult": r}).encode()
            if url.startswith(pds.EU + "efetch"):
                self.assertEqual(data["id"], "999,15902073,15902076")
                return efetch
            if url.startswith(pds.CR):
                calls["cr"].append(url)
                return json.dumps({"message": {"title": ["Don't be shocked"]}}).encode() if "00123-4" in url else None
            if url.startswith(pds.OA):
                calls["oa"].append(urllib.parse.unquote(url))
                return json.dumps({"results": [{"id": "https://openalex.org/W1964695157",
                                                "doi": "https://doi.org/10.1016/s0197", "display_name": "Don't be shocked.",
                                                "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/15902073"},
                                                "cited_by_count": 2, "locations_count": 1}]}).encode()
            raise AssertionError(url)

        with mock.patch.object(pds, "http", fake_http), mock.patch.object(pds, "NCBI_PAUSE", 0), \
                mock.patch.object(pds, "CR_PAUSE", 0), mock.patch.object(pds, "OA_PAUSE", 0), \
                tempfile.TemporaryDirectory() as td:
            pds.main(["--out-dir", td, "--limit", "200"])
            with open(os.path.join(td, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            with open(os.path.join(td, "records.jsonl"), encoding="utf-8") as f:
                recs = [json.loads(x) for x in f]
            with open(os.path.join(td, "stems.csv"), encoding="utf-8") as f:
                stems = list(csv.DictReader(f))
            self.assertTrue(os.path.exists(os.path.join(td, "openalex_stub_works.jsonl")))
        self.assertEqual(res["screen"]["elsevier_stems"], 200)
        self.assertEqual(res["screen"]["candidates"], 1)
        self.assertEqual(res["screen"]["failed_groups"], 0)
        self.assertEqual(res["verified"]["all"], 2)
        self.assertEqual(res["verified"]["with_s_pii"], 2)
        self.assertEqual(res["H1"], "not supported")
        self.assertEqual(res["H2"], "untestable")
        self.assertEqual(res["H3_detail"]["registered_match"], 1)
        self.assertEqual(res["H3_detail"]["unregistered"], 1)
        self.assertEqual(res["H4_detail"], {"looked_up": 2, "not_found": 1})
        self.assertEqual(res["openalex_stub_works"], {"n": 1, "citations": 2, "locations": 1, "title_mismatch": 0})
        self.assertEqual(res["calls"]["eutils"], 4 + 1 + 1)
        self.assertEqual([r["pmid"] for r in recs], ["15902073", "15902076"])
        self.assertEqual(recs[0]["repaired_doi"], "10.1016/S0197-2510(05)00123-4")
        self.assertTrue(recs[0]["pii_matches_stem"])
        self.assertEqual(recs[0]["openalex"], "W1964695157")
        self.assertEqual(stems, [{"stem": "10.1016/S0197", "pubmed_count": "3", "verified": "2", "journals": "JEMS",
                                  "years": "2005-2005"}])
        self.assertEqual(len(calls["cr"]), 2)
        self.assertIn("ids.pmid:15902073|15902076", calls["oa"][0])


if __name__ == "__main__":
    unittest.main()
