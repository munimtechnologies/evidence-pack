# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for commentin_check.py (no network). The fixtures copy the fields PubMed esummary
returned on 2026-10-18 for the JAMA 2025 metformin knee-osteoarthritis trial (PMID 40274279) and the
two JAMA Network items its bare-DOI "Comment in" links point to (39541114, a 2024 patient page, and
36939700, a 2023 cohort study), and for an NEJM letter (38507769) whose "Comment in" target, a
Nat Rev Nephrol comment (38012264), is older than the letter but names it back."""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import commentin_check as cc  # noqa: E402
import integrity_check as ic  # noqa: E402

RCT_DOI = "10.1001/jama.2025.3471"
PAGE_DOI = "10.1001/jama.2024.17482"
COHORT_DOI = "10.1001/jamanetworkopen.2023.3646"
LETTER_DOI = "10.1056/nejmc2401126"
NRN_DOI = "10.1038/s41581-023-00795-w"

RCT = {"uid": "40274279", "pubdate": "2025 May 27", "sortpubdate": "2025/05/27 00:00",
       "title": "Metformin for Knee Osteoarthritis in Patients With Overweight or Obesity: A Randomized Clinical Trial.",
       "pubtype": ["Clinical Trial, Phase III", "Journal Article", "Randomized Controlled Trial"],
       "articleids": [{"idtype": "pubmed", "value": "40274279"}, {"idtype": "doi", "value": RCT_DOI}],
       "references": [{"refsource": "doi: 10.1001/jamanetworkopen.2023.3646", "reftype": "Comment in",
                       "pmid": "", "note": ""},
                      {"refsource": "doi: 10.1001/jama.2024.17482", "reftype": "Comment in",
                       "pmid": "", "note": ""}]}
PAGE = {"uid": "39541114", "pubdate": "2024 Dec 10", "sortpubdate": "2024/12/10 00:00",
        "title": "What Is Knee Osteoarthritis?", "pubtype": ["Journal Article"],
        "articleids": [{"idtype": "doi", "value": PAGE_DOI}], "references": []}
COHORT = {"uid": "36939700", "pubdate": "2023 Mar 1", "sortpubdate": "2023/03/01 00:00",
          "title": "Development of Osteoarthritis in Adults With Type 2 Diabetes Treated With Metformin vs a Sulfonylurea.",
          "pubtype": ["Journal Article"], "articleids": [{"idtype": "doi", "value": COHORT_DOI}],
          "references": []}
LETTER = {"uid": "38507769", "pubdate": "2024 Mar 21", "sortpubdate": "2024/03/21 00:00",
          "title": "Sparsentan in IgA Nephropathy.", "pubtype": ["Letter", "Comment"],
          "articleids": [{"idtype": "doi", "value": "10.1056/NEJMc2401126"}],
          "references": [{"refsource": "N Engl J Med. 2023 Dec 28;389(26):2436-2445. doi: 10.1056/NEJMoa2308550.",
                          "reftype": "Comment on", "pmid": "37921461", "note": ""},
                         {"refsource": "Nat Rev Nephrol. 2024 Jan;20(1):6. doi: 10.1038/s41581-023-00795-w.",
                          "reftype": "Comment in", "pmid": "38012264", "note": ""}]}
NRN = {"uid": "38012264", "pubdate": "2024 Jan", "sortpubdate": "2024/01/01 00:00",
       "title": "Renoprotective effects of sparsentan: clinical trial evidence in IgA nephropathy and FSGS.",
       "pubtype": ["Journal Article", "Comment"], "articleids": [{"idtype": "doi", "value": NRN_DOI}],
       "references": [{"refsource": "Lancet. 2023 Dec 2;402(10417):2077-2090. doi: 10.1016/S0140-6736(23)02302-4.",
                       "reftype": "Comment on", "pmid": "37931634", "note": ""},
                      {"refsource": "N Engl J Med. 2024 Mar 21;390(12):1154-1155. doi: 10.1056/NEJMc2401126.",
                       "reftype": "Comment on", "pmid": "38507769", "note": ""}]}
SUMMARIES = {"40274279": RCT, "39541114": PAGE, "36939700": COHORT, "38507769": LETTER, "38012264": NRN}
DOIS = {RCT_DOI: "40274279", PAGE_DOI: "39541114", COHORT_DOI: "36939700", LETTER_DOI: "38507769",
        NRN_DOI: "38012264"}


class FakeGet:
    """Stands in for integrity_check.http_json: answers esearch and esummary URLs from the fixtures.
    Like PubMed, esearch names each DOI it has no record for under quotedphrasesnotfound.
    Calls numbered fail_from or later return HTTP 400."""

    def __init__(self, summaries=None, fail_from=None):
        self.urls = []
        self.summaries = SUMMARIES if summaries is None else summaries
        self.fail_from = fail_from

    def __call__(self, url):
        self.urls.append(url)
        if self.fail_from is not None and len(self.urls) >= self.fail_from:
            return None, "HTTP 400"
        q = urllib.parse.unquote(url)
        if "esearch.fcgi" in url:
            ids = [p for d, p in DOIS.items() if '"%s"[doi]' % d in q and p in self.summaries]
            missing = ['"%s"[doi]' % d for d in re.findall(r'"([^"]+)"\[doi\]', q)
                       if not (d in DOIS and DOIS[d] in self.summaries)]
            return {"esearchresult": {"count": str(len(ids)), "idlist": ids,
                                      "warninglist": {"quotedphrasesnotfound": missing}}}, None
        if "esummary.fcgi" in url:
            ids = url.rsplit("id=", 1)[1].split(",")
            result = {"uids": ids}
            for i in ids:
                result[i] = self.summaries.get(i) or {"uid": i, "error": "cannot get document summary"}
            return {"result": result}, None
        return None, "unexpected url " + url


def no_pause(seconds):
    return None


class TestParts(unittest.TestCase):
    def test_comment_links(self):
        rec = {"references": [
            {"refsource": "Lancet. 1998 Feb 28;351(9103):611-2", "reftype": "Comment in", "pmid": 9500313},
            {"refsource": "Lancet. 2010 Feb 6;375(9713):445", "reftype": "Retraction in", "pmid": 20137807},
            {"refsource": "doi:  10.1001/JAMA.2024.17482.", "reftype": "Comment In", "pmid": ""},
            {"refsource": "Letter to the editor, 2020", "reftype": "Comment in", "pmid": None}]}
        links = cc.comment_links(rec)
        self.assertEqual([l["cls"] for l in links], ["pmid", "bare_doi", "other_nopmid"])
        self.assertEqual(links[0]["tgt_pmid"], "9500313")
        self.assertIsNone(links[0]["tgt_doi"])
        self.assertEqual(links[1]["tgt_doi"], PAGE_DOI)
        self.assertIsNone(links[1]["tgt_pmid"])
        self.assertEqual(links[1]["refsource"], "doi: 10.1001/JAMA.2024.17482.")
        self.assertEqual((links[2]["tgt_pmid"], links[2]["tgt_doi"]), (None, None))

    def test_comment_on_pmids(self):
        self.assertEqual(cc.comment_on_pmids(NRN), {"37931634", "38507769"})
        self.assertEqual(cc.comment_on_pmids(LETTER), {"37921461"})
        self.assertEqual(cc.comment_on_pmids(None), set())

    def test_dates(self):
        self.assertEqual(cc.sort_date(RCT), (2025, 5, 27))
        self.assertEqual(cc.sort_date({"pubdate": "2024 Jan"}), (2024,))
        self.assertEqual(cc.sort_date({}), ())
        self.assertEqual(cc.iso((2025, 5, 27)), "2025-05-27")
        self.assertEqual(cc.iso((2024,)), "2024")
        self.assertIsNone(cc.iso(()))

    def test_no_target_id(self):
        rec = {"sortpubdate": "2020/01/01 00:00",
               "references": [{"refsource": "Letter to the editor, 2020", "reftype": "Comment in", "pmid": ""}]}
        out = cc.describe({"input": "1", "pmid": "1", "doi": None}, rec, {}, {}, False, "2026-10-18")
        self.assertEqual(out["links"][0]["flags"], ["other_nopmid", "no_target_id"])
        self.assertEqual((out["counts"]["no_target_id"], out["counts"]["to_read"]), (1, 1))
        self.assertIsNone(out["doi"])
        self.assertEqual(out["date"], "2020-01-01")

    def test_comment_on_other(self):
        # Shaped on JAMA Oncol 2017: 28208186 links 28208180, a comment PubMed records on 28208174.
        src = {"uid": "28208186", "sortpubdate": "2017/08/01 00:00",
               "references": [{"refsource": "doi: 10.1001/jamaoncol.2016.6722", "reftype": "Comment in", "pmid": ""}]}
        tgt = {"uid": "28208180", "sortpubdate": "2017/08/01 00:00", "pubtype": ["Journal Article", "Comment"],
               "references": [{"refsource": "JAMA Oncol. 2017 Aug 01;3(8):1043-1050. doi: 10.1001/jamaoncol.2016.6749.",
                               "reftype": "Comment on", "pmid": "28208174"}]}
        out = cc.describe({"input": "28208186", "pmid": "28208186", "doi": None}, src, {"28208180": tgt},
                          {"10.1001/jamaoncol.2016.6722": "28208180"}, False, "2026-10-18")
        link = out["links"][0]
        self.assertEqual((link["tgt_pmid"], link["earlier"], link["reciprocal"]), ("28208180", False, False))
        self.assertEqual(link["tgt_comment_on"], ["28208174"])
        self.assertEqual(link["flags"], ["bare_doi", "not_reciprocal", "comment_on_other"])
        self.assertEqual(out["counts"]["comment_on_other"], 1)


class TestCheck(unittest.TestCase):
    def test_end_to_end(self):
        get = FakeGet()
        records, errors = cc.check(["40274279", "10.1056/NEJMc2401126"], get=get, pause=no_pause,
                                   today="2026-10-18")
        self.assertEqual(errors, [])
        self.assertEqual(len(get.urls), 4)
        rct, letter = records
        self.assertEqual((rct["found"], rct["date"], rct["doi"]), (True, "2025-05-27", RCT_DOI))
        self.assertEqual([l["tgt_pmid"] for l in rct["links"]], ["36939700", "39541114"])
        self.assertEqual([l["tgt_date"] for l in rct["links"]], ["2023-03-01", "2024-12-10"])
        for l in rct["links"]:
            self.assertEqual(l["flags"], ["bare_doi", "earlier", "not_reciprocal"])
            self.assertEqual((l["earlier"], l["reciprocal"], l["tgt_found"]), (True, False, True))
        self.assertEqual(rct["links"][1]["tgt_title"], "What Is Knee Osteoarthritis?")
        self.assertEqual(rct["counts"], {"links": 2, "pmid": 0, "bare_doi": 2, "other_nopmid": 0,
                                         "no_target_id": 0, "target_not_in_pubmed": 0, "target_unread": 0,
                                         "earlier": 2, "not_reciprocal": 2, "comment_on_other": 0,
                                         "to_read": 2})
        self.assertEqual(rct["links"][0]["tgt_comment_on"], [])
        self.assertEqual((letter["pmid"], letter["doi"]), ("38507769", LETTER_DOI))
        self.assertEqual(len(letter["links"]), 1)
        link = letter["links"][0]
        self.assertEqual((link["cls"], link["tgt_pmid"], link["tgt_doi"]), ("pmid", "38012264", NRN_DOI))
        self.assertEqual((link["earlier"], link["reciprocal"]), (True, True))
        self.assertEqual(link["flags"], ["earlier"])
        self.assertEqual(link["tgt_comment_on"], ["37931634", "38507769"])
        self.assertEqual(link["tgt_pubtypes"], ["Journal Article", "Comment"])
        self.assertEqual(letter["checked_at"], "2026-10-18")

    def test_target_not_in_pubmed(self):
        get = FakeGet(summaries={"40274279": RCT})
        records, errors = cc.check(["40274279"], get=get, pause=no_pause, today="2026-10-18")
        self.assertEqual(errors, [])
        self.assertEqual(len(get.urls), 2)
        for l in records[0]["links"]:
            self.assertEqual(l["flags"], ["bare_doi", "target_not_in_pubmed"])
            self.assertEqual((l["tgt_pmid"], l["tgt_found"], l["earlier"], l["reciprocal"]),
                             (None, False, None, None))

    def test_failed_target_lookup_is_unread_not_absent(self):
        get = FakeGet(fail_from=3)
        records, errors = cc.check(["40274279", "10.1056/NEJMc2401126"], get=get, pause=no_pause,
                                   today="2026-10-18")
        self.assertEqual(len(errors), 2)
        self.assertTrue(errors[0].startswith("esearch from " + PAGE_DOI))
        self.assertTrue(errors[1].startswith("esummary from 38012264"))
        self.assertEqual([l["flags"] for l in records[0]["links"]],
                         [["bare_doi", "target_unread"], ["bare_doi", "target_unread"]])
        self.assertEqual(records[1]["links"][0]["flags"], ["target_unread"])
        self.assertIsNone(records[1]["links"][0]["reciprocal"])

    def test_unknown_and_invalid(self):
        get = FakeGet()
        records, errors = cc.check(["99999999", "junk", "99999999"], get=get, pause=no_pause,
                                   today="2026-10-18")
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(len(get.urls), 1)
        self.assertEqual([r["found"] for r in records], [False, False])
        self.assertEqual(records[0]["counts"]["links"], 0)
        self.assertIsNone(records[1]["pmid"])


class TestMain(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ic, "http_json", FakeGet()), mock.patch.object(ic.time, "sleep", no_pause), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cc.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_fail_on_flag(self):
        code, out, err = self.run_main(["40274279", "--fail-on-flag"])
        self.assertEqual(code, 2)
        self.assertEqual(out.count("\n"), 1)
        self.assertIn('"cls": "bare_doi"', out)
        self.assertIn("1 records (1 found in PubMed): 2 Comment in links (0 pmid, 2 bare_doi, "
                      "0 other_nopmid); 2 flagged to read; 0 lookup errors", err)

    def test_no_links_passes(self):
        code, out, err = self.run_main(["38012264", "--fail-on-flag"])
        self.assertEqual(code, 0)
        self.assertIn('"links": []', out)

    def test_out_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "comment_links.jsonl")
            code, out, err = self.run_main(["40274279", "--out", path])
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(len(lines), 1)
        self.assertIn('"tgt_pmid": "36939700"', lines[0])


if __name__ == "__main__":
    unittest.main()
