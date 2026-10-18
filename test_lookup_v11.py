# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the v1.1 changes to integrity_check.py and commentin_check.py (no network).

- PubMed esearch can return a short or empty idlist with no error. A DOI is absent only if esearch
  names it under warninglist.quotedphrasesnotfound (shape read live on 2026-10-18: two unknown DOIs
  come back as '"10.1016/s0140"[doi]' and '"10.9999/not.a.real.doi.12345"[doi]', count "0").
- Crossref type "journal" (10.17485/ijst, read live 2026-10-18) gives status not_an_article.
- commentin_check allows one day in "earlier": 36218585 (2020/03/02) is the "Comment in" target of
  32125402 (2020/03/03), both read live on 2026-10-18."""
import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import commentin_check as cc  # noqa: E402
import integrity_check as ic  # noqa: E402

A, B, C = "10.1001/a.1", "10.1001/b.2", "10.1001/c.3"
REC_A = {"uid": "1", "articleids": [{"idtype": "doi", "value": A}]}
REC_B = {"uid": "2", "articleids": [{"idtype": "doi", "value": B}]}
X, Y = "10.1001/jama.2025.0001", "10.1001/jama.2025.0002"
SRC = {"uid": "100", "sortpubdate": "2025/01/07 00:00",
       "references": [{"refsource": "doi: " + X, "reftype": "Comment in", "pmid": ""},
                      {"refsource": "doi: " + Y, "reftype": "Comment in", "pmid": ""}]}
IJST = "10.17485/ijst"
CR_IJST = {"DOI": IJST, "type": "journal", "title": ["Indian Journal of Science and Technology"]}


def esearch(ids, notfound=()):
    return {"header": {"type": "esearch", "version": "0.3"},
            "esearchresult": {"count": str(len(ids)), "retmax": str(len(ids)), "retstart": "0",
                              "idlist": list(ids), "translationset": [],
                              "warninglist": {"phrasesignored": [],
                                              "quotedphrasesnotfound": ['"%s"[doi]' % d for d in notfound],
                                              "outputmessages": []}}}


class ScriptedGet:
    """esearch answers come from a list, one per call; esummary answers from a dict."""

    def __init__(self, replies, summaries):
        self.replies = list(replies)
        self.summaries = summaries
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if "esearch.fcgi" in url:
            return self.replies.pop(0), None
        if "esummary.fcgi" in url:
            ids = url.rsplit("id=", 1)[1].split(",")
            result = {"uids": ids}
            for i in ids:
                result[i] = self.summaries.get(i) or {"uid": i, "error": "cannot get document summary"}
            return {"result": result}, None
        return None, "unexpected url " + url


def no_pause(seconds):
    return None


class TestNotFound(unittest.TestCase):
    def test_live_shape(self):
        data = {"esearchresult": {"count": "0", "idlist": [], "warninglist": {"quotedphrasesnotfound": [
            '"10.1016/s0140"[doi]', '"10.9999/NOT.A.REAL.DOI.12345"[doi]'], "outputmessages": ["No items found."]}}}
        self.assertEqual(ic.not_found_dois(data), {"10.1016/s0140", "10.9999/not.a.real.doi.12345"})

    def test_top_level_and_missing(self):
        self.assertEqual(ic.not_found_dois({"warninglist": {"quotedphrasesnotfound": ['"%s"[doi]' % A]}}), {A})
        self.assertEqual(ic.not_found_dois({"esearchresult": {"idlist": []}}), set())
        self.assertEqual(ic.not_found_dois(None), set())
        self.assertEqual(ic.not_found_dois({"warninglist": {"quotedphrasesnotfound": ["no quotes"]}}), set())


class TestPubmedLookup(unittest.TestCase):
    def test_named_absent_is_absent(self):
        get = ScriptedGet([esearch(["1"], notfound=[B, C])], {"1": REC_A})
        out = ic.pubmed_lookup([], [A, B, C], get, no_pause)
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["absent_dois"], [B, C])
        self.assertEqual(out["doi_to_pmid"], {A: "1"})
        self.assertEqual(len(get.urls), 2)

    def test_short_batch_retried_then_error(self):
        get = ScriptedGet([esearch(["1"]), esearch(["1"])], {"1": REC_A})
        out = ic.pubmed_lookup([], [A, B, C], get, no_pause)
        self.assertEqual(len(get.urls), 3)
        self.assertEqual(out["errors"], ["esearch from %s: short batch, 1 PMIDs for 3 DOIs not named absent" % A])
        self.assertEqual(out["absent_dois"], [])
        self.assertEqual(out["doi_to_pmid"], {A: "1"})

    def test_empty_batch_recovers_on_retry(self):
        get = ScriptedGet([esearch([]), esearch(["1", "2"], notfound=[C])], {"1": REC_A, "2": REC_B})
        out = ic.pubmed_lookup([], [A, B, C], get, no_pause)
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["absent_dois"], [C])
        self.assertEqual(sorted(out["by_pmid"]), ["1", "2"])
        self.assertEqual(len(get.urls), 3)

    def test_run_keeps_unconfirmed_doi_unknown_without_crossref(self):
        get = ScriptedGet([esearch([]), esearch([])], {})
        records, errors = ic.run([A], get=get, pause=no_pause, use_crossref=False, today="2026-10-18")
        self.assertEqual(len(errors), 1)
        self.assertEqual(records[0]["status"], "unknown")


class TestCommentinAbsent(unittest.TestCase):
    def test_absent_vs_unread_in_one_run(self):
        get = ScriptedGet([esearch([], notfound=[X]), esearch([], notfound=[X])], {"100": SRC})
        records, errors = cc.check(["100"], get=get, pause=no_pause, today="2026-10-18")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("esearch from %s: short batch" % X))
        links = records[0]["links"]
        self.assertEqual([l["tgt_doi"] for l in links], [X, Y])
        self.assertEqual(links[0]["flags"], ["bare_doi", "target_not_in_pubmed"])
        self.assertEqual(links[1]["flags"], ["bare_doi", "target_unread"])
        self.assertEqual((records[0]["counts"]["target_not_in_pubmed"], records[0]["counts"]["target_unread"]), (1, 1))
        self.assertEqual(len(get.urls), 3)


class TestEarlierTolerance(unittest.TestCase):
    def test_is_earlier(self):
        self.assertFalse(cc.is_earlier((2020, 3, 2), (2020, 3, 3)))
        self.assertFalse(cc.is_earlier((2020, 3, 3), (2020, 3, 3)))
        self.assertTrue(cc.is_earlier((2020, 3, 1), (2020, 3, 3)))
        self.assertTrue(cc.is_earlier((2019,), (2020, 3, 3)))
        self.assertFalse(cc.is_earlier((2020,), (2020, 3, 3)))
        self.assertIsNone(cc.is_earlier((), (2020, 3, 3)))
        self.assertTrue(cc.is_earlier((2020, 2, 30), (2020, 3, 3)))

    def test_dieleman_link_not_earlier(self):
        src = {"uid": "32125402", "pubdate": "2020 Mar 3", "sortpubdate": "2020/03/03 00:00",
               "references": [{"refsource": "doi: 10.1001/jamahealthforum.2020.0238", "reftype": "Comment in",
                               "pmid": ""}]}
        tgt = {"uid": "36218585", "pubdate": "2020 Mar 2", "sortpubdate": "2020/03/02 00:00",
               "title": "The Complex Mosaic of Health Care Spending in the United States.",
               "pubtype": ["Journal Article"], "references": []}
        out = cc.describe({"input": "32125402", "pmid": "32125402", "doi": None}, src, {"36218585": tgt},
                          {"10.1001/jamahealthforum.2020.0238": "36218585"}, False, "2026-10-18", set())
        link = out["links"][0]
        self.assertEqual((link["tgt_date"], link["earlier"], link["reciprocal"]), ("2020-03-02", False, False))
        self.assertEqual(link["flags"], ["bare_doi", "not_reciprocal"])


class TestNotAnArticle(unittest.TestCase):
    def test_journal_doi(self):
        entry = {"input": IJST, "pmid": None, "doi": IJST, "raw": None}
        rec = ic.combine(entry, None, CR_IJST, None, "2026-10-18")
        self.assertEqual((rec["status"], rec["said_by"]), ("not_an_article", ["crossref"]))
        self.assertIn("journal_level", [f["kind"] for f in rec["hygiene"]])

    def test_retraction_still_wins(self):
        item = dict(CR_IJST, **{"updated-by": [{"DOI": "10.1/n", "type": "retraction"}]})
        rec = ic.combine({"input": IJST, "pmid": None, "doi": IJST, "raw": None}, None, item, None, "2026-10-18")
        self.assertEqual(rec["status"], "retracted")

    def test_article_stays_clear(self):
        item = dict(CR_IJST, type="journal-article")
        rec = ic.combine({"input": IJST, "pmid": None, "doi": IJST, "raw": None}, None, item, None, "2026-10-18")
        self.assertEqual(rec["status"], "clear")

    def run_main(self, argv):
        def crossref_only(url):
            if "api.crossref.org" in url:
                return {"message": {"items": [CR_IJST]}}, None
            return None, "unexpected url " + url
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ic, "http_json", crossref_only), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ic.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_fail_on_levels(self):
        code, out, err = self.run_main([IJST, "--no-pubmed", "--fail-on", "not_an_article", "--blocklist", ""])
        self.assertEqual(code, 2)
        self.assertIn("1 checked: 1 not_an_article", err)
        code, _, _ = self.run_main([IJST, "--no-pubmed", "--fail-on", "concern", "--blocklist", ""])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
