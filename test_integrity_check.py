# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for integrity_check.py (no network). The fixtures copy the shapes that PubMed
esummary and Crossref returned on 2026-10-17 for the retracted Wakefield 1998 Lancet paper
(PMID 9500320), its 2010 retraction notice, and a clear 2025 JAMA trial."""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import integrity_check as ic  # noqa: E402

WAKE_DOI = "10.1016/s0140-6736(97)11096-0"
JAMA_DOI = "10.1001/jama.2025.3471"
NOTICE_DOI = "10.1016/s0140-6736(10)60175-4"

WAKE = {"uid": "9500320", "pubdate": "1998 Feb 28", "source": "Lancet",
        "title": "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children.",
        "pubtype": ["Journal Article", "Research Support, Non-U.S. Gov't", "Retracted Publication"],
        "articleids": [{"idtype": "pubmed", "value": "9500320"}, {"idtype": "doi", "value": WAKE_DOI}],
        "references": [
            {"refsource": "Lancet. 1998 Feb 28;351(9103):611-2", "reftype": "Comment in", "pmid": 9500313},
            {"refsource": "Lancet. 2004 Mar 6;363(9411):750", "reftype": "Retraction in", "pmid": 15016483},
            {"refsource": "Lancet. 2010 Feb 6;375(9713):445", "reftype": "Retraction in", "pmid": 20137807},
            {"refsource": "Eur J Gastroenterol Hepatol. 2011 Nov;23(11):1082",
             "reftype": "Expression of concern in", "pmid": 21971344}]}
JAMA = {"uid": "40274279", "pubdate": "2025 Apr 24", "source": "JAMA",
        "title": "Metformin for Knee Osteoarthritis in Patients With Overweight or Obesity: A Randomized Clinical Trial.",
        "pubtype": ["Clinical Trial, Phase III", "Journal Article", "Randomized Controlled Trial"],
        "articleids": [{"idtype": "pubmed", "value": "40274279"}, {"idtype": "doi", "value": JAMA_DOI}],
        "references": [{"refsource": "doi: 10.1001/jama.2024.17482", "reftype": "Comment in", "pmid": None}]}
NOTICE = {"uid": "20137807", "pubdate": "2010 Feb 6", "source": "Lancet",
          "title": "Retraction--Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children.",
          "pubtype": ["Retraction Notice"],
          "articleids": [{"idtype": "doi", "value": "10.1016/S0140-6736(10)60175-4"}],
          "references": [{"refsource": "Lancet. 1998 Feb 28;351(9103):637-41", "reftype": "Retraction of", "pmid": 9500320}]}
CR_WAKE = {"DOI": WAKE_DOI, "type": "journal-article", "issued": {"date-parts": [[1998, 2]]},
           "title": ["RETRACTED: Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children"],
           "updated-by": [
               {"DOI": "10.1016/s0140-6736(04)15715-2", "type": "correction", "label": "Correction",
                "source": "retraction-watch", "updated": {"date-parts": [[2004, 3, 6]]}, "record-id": "17269"},
               {"DOI": NOTICE_DOI, "type": "retraction", "label": "Retraction",
                "source": "retraction-watch", "updated": {"date-parts": [[2010, 2, 6]]}, "record-id": "4036"}]}
CR_JAMA = {"DOI": JAMA_DOI, "type": "journal-article", "issued": {"date-parts": [[2025, 4, 24]]},
           "title": ["Metformin for Knee Osteoarthritis in Patients With Overweight or Obesity"]}
CR_NOTICE = {"DOI": NOTICE_DOI, "type": "journal-article", "issued": {"date-parts": [[2010, 2]]},
             "title": ["Retraction - Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children"],
             "update-to": [{"DOI": WAKE_DOI, "type": "retraction", "label": "Retraction",
                            "source": "retraction-watch", "updated": {"date-parts": [[2010, 2, 6]]}}]}
SUMMARIES = {"9500320": WAKE, "40274279": JAMA, "20137807": NOTICE}
PMID_OF = {JAMA_DOI: "40274279", WAKE_DOI: "9500320"}


class FakeGet:
    """Stands in for http_json: answers esearch, esummary and Crossref URLs from the fixtures.
    Like PubMed, esearch names each DOI it has no record for under quotedphrasesnotfound."""

    def __init__(self, fail_first=0):
        self.urls = []
        self.fail_first = fail_first

    def __call__(self, url):
        self.urls.append(url)
        if self.fail_first > 0:
            self.fail_first -= 1
            return None, "HTTP 400"
        q = urllib.parse.unquote(url)
        if "esearch.fcgi" in url:
            asked = re.findall(r'"([^"]+)"\[doi\]', q)
            ids = [PMID_OF[d] for d in asked if d in PMID_OF]
            missing = ['"%s"[doi]' % d for d in asked if d not in PMID_OF]
            return {"esearchresult": {"count": str(len(ids)), "idlist": ids,
                                      "warninglist": {"quotedphrasesnotfound": missing}}}, None
        if "esummary.fcgi" in url:
            ids = url.rsplit("id=", 1)[1].split(",")
            result = {"uids": ids}
            for i in ids:
                result[i] = SUMMARIES.get(i) or {"uid": i, "error": "cannot get document summary"}
            return {"result": result}, None
        if "api.crossref.org" in url:
            items = [it for it in (CR_WAKE, CR_JAMA, CR_NOTICE) if "doi:" + it["DOI"] in q]
            return {"message": {"items": items}}, None
        return None, "unexpected url " + url


def no_pause(seconds):
    return None


class TestParsing(unittest.TestCase):
    def test_parse_token(self):
        self.assertEqual(ic.parse_token("9500320")["pmid"], "9500320")
        self.assertEqual(ic.parse_token("PMID: 9500320")["pmid"], "9500320")
        t = ic.parse_token("https://doi.org/10.1016/S0140-6736(97)11096-0")
        self.assertEqual((t["pmid"], t["doi"]), (None, WAKE_DOI))
        self.assertEqual(ic.parse_token("10.1001/jama.2025.3471.")["doi"], JAMA_DOI)
        bad = ic.parse_token("junk")
        self.assertEqual((bad["pmid"], bad["doi"]), (None, None))

    def test_read_file(self):
        text = ("# refs\n9500320\n"
                "Pan F et al. JAMA 2025. doi: 10.1001/jama.2025.3471. PMID: 40274279\n"
                "https://doi.org/10.1016/S0140-6736(97)11096-0\n\n")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "refs.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            tokens = ic.read_file(path)
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0], "9500320")
        self.assertEqual(ic.parse_token(tokens[1])["doi"], JAMA_DOI)
        self.assertEqual(tokens[2], "40274279")
        self.assertEqual(ic.parse_token(tokens[3])["doi"], WAKE_DOI)

    def test_chunks(self):
        self.assertEqual(ic.chunks([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])
        self.assertEqual(ic.chunks([], 3), [])


class TestStatus(unittest.TestCase):
    def test_pubmed_status_retracted(self):
        s = ic.pubmed_status(WAKE)
        self.assertTrue(s["retracted"])
        self.assertTrue(s["concern"])
        self.assertFalse(s["corrected"])
        self.assertFalse(s["is_notice"])
        self.assertEqual(len(s["notices"]), 3)
        self.assertEqual(s["year"], 1998)

    def test_pubmed_status_clear_and_notice(self):
        s = ic.pubmed_status(JAMA)
        self.assertEqual((s["retracted"], s["concern"], s["corrected"], s["notices"]), (False, False, False, []))
        n = ic.pubmed_status(NOTICE)
        self.assertTrue(n["is_notice"])
        self.assertFalse(n["retracted"])
        self.assertEqual(n["notice_of"][0]["pmid"], 9500320)

    def test_crossref_status_retracted(self):
        s = ic.crossref_status(CR_WAKE)
        self.assertTrue(s["retracted"])
        self.assertTrue(s["corrected"])
        self.assertFalse(s["concern"])
        self.assertTrue(s["title_prefix"])
        self.assertEqual([u["type"] for u in s["updates"]], ["correction", "retraction"])
        self.assertEqual(s["updates"][1]["date"], "2010-02-06")
        self.assertEqual(s["updates"][1]["source"], "retraction-watch")
        self.assertEqual(s["year"], 1998)

    def test_crossref_status_notice_and_clear(self):
        n = ic.crossref_status(CR_NOTICE)
        self.assertTrue(n["is_notice"])
        self.assertFalse(n["retracted"])
        self.assertEqual(n["notice_of"], [{"type": "retraction", "doi": WAKE_DOI}])
        c = ic.crossref_status(CR_JAMA)
        self.assertEqual((c["retracted"], c["concern"], c["corrected"], c["updates"]), (False, False, False, []))
        self.assertEqual(c["year"], 2025)

    def test_title_prefix(self):
        self.assertTrue(ic.TITLE_PREFIX.match("RETRACTED ARTICLE: Something"))
        self.assertTrue(ic.TITLE_PREFIX.match("WITHDRAWN: Something"))
        self.assertFalse(ic.TITLE_PREFIX.match("Retracted articles in biomedicine: a review"))

    def test_overall(self):
        self.assertEqual(ic.overall(None, None), ("unknown", []))
        clear = {"retracted": False, "concern": False, "corrected": False}
        self.assertEqual(ic.overall(clear, None), ("clear", []))
        self.assertEqual(ic.overall(dict(clear, concern=True), dict(clear, retracted=True)),
                         ("retracted", ["crossref"]))
        self.assertEqual(ic.overall(dict(clear, retracted=True), dict(clear, retracted=True)),
                         ("retracted", ["pubmed", "crossref"]))


class TestRun(unittest.TestCase):
    TOKENS = ["9500320", JAMA_DOI, "https://doi.org/10.1016/S0140-6736(97)11096-0", "junk", "10.1016/s0140"]

    def test_end_to_end(self):
        get = FakeGet()
        records, errors = ic.run(self.TOKENS, get=get, pause=no_pause, today="2026-10-17")
        self.assertEqual(errors, [])
        self.assertEqual(len(get.urls), 3)
        self.assertEqual([r["status"] for r in records], ["retracted", "clear", "retracted", "invalid", "unknown"])
        self.assertEqual(records[0]["doi"], WAKE_DOI)
        self.assertEqual(records[0]["said_by"], ["pubmed", "crossref"])
        self.assertEqual(records[0]["year"], 1998)
        self.assertEqual(records[1]["pmid"], "40274279")
        self.assertEqual(records[1]["hygiene"], [])
        self.assertEqual(records[2]["pmid"], "9500320")
        self.assertEqual(records[4]["hygiene"][0]["kind"], "stub")
        self.assertIsNone(records[4]["pubmed"])
        self.assertEqual(records[3]["pmid"], None)
        self.assertTrue(all(r["checked_at"] == "2026-10-17" for r in records))

    def test_failed_esearch_degrades_not_clears(self):
        get = FakeGet(fail_first=1)
        records, errors = ic.run(self.TOKENS, get=get, pause=no_pause, today="2026-10-17")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("esearch"))
        self.assertEqual([r["status"] for r in records], ["retracted", "clear", "retracted", "invalid", "unknown"])
        self.assertIsNone(records[1]["pubmed"])
        self.assertIsNotNone(records[1]["crossref"])

    def test_no_crossref_leaves_doi_only_unknown(self):
        get = FakeGet()
        records, errors = ic.run([JAMA_DOI, "10.1016/s0140"], get=get, pause=no_pause,
                                 use_crossref=False, today="2026-10-17")
        self.assertEqual([r["status"] for r in records], ["clear", "unknown"])
        self.assertTrue(all("crossref" not in u for u in get.urls))

    def test_duplicates_dropped(self):
        get = FakeGet()
        records, _ = ic.run([JAMA_DOI, JAMA_DOI + ".", "https://doi.org/" + JAMA_DOI],
                            get=get, pause=no_pause, today="2026-10-17")
        self.assertEqual(len(records), 1)


class TestHttp(unittest.TestCase):
    def test_retries_400_then_succeeds(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            calls.append(req.full_url)
            if len(calls) < 3:
                raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, None)
            return io.BytesIO(b'{"ok": 1}')

        with mock.patch.object(ic.urllib.request, "urlopen", fake_urlopen):
            data, err = ic.http_json("https://example.test/a", sleep=no_pause)
        self.assertEqual((data, err), ({"ok": 1}, None))
        self.assertEqual(len(calls), 3)

    def test_404_is_final(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        with mock.patch.object(ic.urllib.request, "urlopen", fake_urlopen):
            data, err = ic.http_json("https://example.test/a", sleep=no_pause)
        self.assertEqual((data, err), (None, "HTTP 404"))
        self.assertEqual(len(calls), 1)

    def test_gives_up_after_tries(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 503, "Busy", {}, None)

        with mock.patch.object(ic.urllib.request, "urlopen", fake_urlopen):
            data, err = ic.http_json("https://example.test/a", tries=4, sleep=no_pause)
        self.assertEqual((data, err), (None, "HTTP 503"))
        self.assertEqual(len(calls), 4)


class TestMain(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ic, "http_json", FakeGet()), mock.patch.object(ic.time, "sleep", no_pause), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ic.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_fail_on_retracted(self):
        code, out, err = self.run_main(["9500320", "--fail-on", "retracted", "--blocklist", ""])
        self.assertEqual(code, 2)
        self.assertEqual(out.count("\n"), 1)
        self.assertIn('"status": "retracted"', out)
        self.assertIn("1 checked: 1 retracted", err)

    def test_clear_passes(self):
        code, out, err = self.run_main([JAMA_DOI, "--fail-on", "concern", "--blocklist", ""])
        self.assertEqual(code, 0)
        self.assertIn('"status": "clear"', out)

    def test_out_file_and_no_pubmed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "checked.jsonl")
            code, out, err = self.run_main([JAMA_DOI, "--no-pubmed", "--out", path, "--blocklist", ""])
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(len(lines), 1)
        self.assertIn('"pubmed": null', lines[0])
        self.assertIn('"status": "clear"', lines[0])


if __name__ == "__main__":
    unittest.main()
