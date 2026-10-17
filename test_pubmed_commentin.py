# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for pubmed_commentin (no network)."""
import random
import unittest

import pubmed_commentin as pc

FIXTURE = b"""<?xml version="1.0" ?>
<PubmedArticleSet>
<PubmedArticle>
 <MedlineCitation Status="MEDLINE" Owner="NLM">
  <PMID Version="1">40274279</PMID>
  <Article PubModel="Print">
   <Journal><JournalIssue CitedMedium="Internet"><PubDate><Year>2025</Year><Month>May</Month><Day>27</Day></PubDate></JournalIssue></Journal>
   <ELocationID EIdType="doi" ValidYN="Y">10.1001/jama.2025.3471</ELocationID>
   <PublicationTypeList><PublicationType UI="D016449">Randomized Controlled Trial</PublicationType></PublicationTypeList>
  </Article>
  <MedlineJournalInfo><MedlineTA>JAMA</MedlineTA></MedlineJournalInfo>
  <CommentsCorrectionsList>
   <CommentsCorrections RefType="CommentIn"><RefSource>doi: 10.1001/jamanetworkopen.2023.3646</RefSource></CommentsCorrections>
   <CommentsCorrections RefType="CommentIn"><RefSource>JAMA. 2025 Jun 17;333(23):2058-2060. doi: 10.1001/jama.2025.4321.</RefSource><PMID Version="1">40366665</PMID></CommentsCorrections>
   <CommentsCorrections RefType="ErratumIn"><RefSource>JAMA. 2025;1:1</RefSource><PMID Version="1">1</PMID></CommentsCorrections>
   <CommentsCorrections RefType="CommentIn"><RefSource>Some letter without identifiers</RefSource></CommentsCorrections>
  </CommentsCorrectionsList>
 </MedlineCitation>
 <PubmedData>
  <ArticleIdList><ArticleId IdType="pubmed">40274279</ArticleId><ArticleId IdType="doi">10.1001/JAMA.2025.3471</ArticleId></ArticleIdList>
  <ReferenceList><Reference><Citation>x</Citation><ArticleIdList><ArticleId IdType="doi">10.9999/ref</ArticleId></ArticleIdList></Reference></ReferenceList>
 </PubmedData>
</PubmedArticle>
<PubmedArticle>
 <MedlineCitation>
  <PMID Version="1">40366665</PMID>
  <Article><Journal><JournalIssue><PubDate><MedlineDate>2025 Jun-Jul</MedlineDate></PubDate></JournalIssue></Journal></Article>
  <CommentsCorrectionsList><CommentsCorrections RefType="CommentOn"><RefSource>JAMA. 2025</RefSource><PMID Version="1">40366680</PMID></CommentsCorrections></CommentsCorrectionsList>
 </MedlineCitation>
 <PubmedData><ArticleIdList><ArticleId IdType="pubmed">40366665</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle>
</PubmedArticleSet>
"""


class TestClassify(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(pc.classify("doi: 10.1001/jama.2020.1511", ""), "bare_doi")
        self.assertEqual(pc.classify("doi: 10.1001/jama.2020.1511.", ""), "bare_doi")
        self.assertEqual(pc.classify("JAMA. 2025;1:2. doi: 10.1001/jama.2025.1.", ""), "other_nopmid")
        self.assertEqual(pc.classify("doi: 10.1001/jama.2020.1511", "123"), "pmid")
        self.assertEqual(pc.classify("", ""), "other_nopmid")

    def test_ref_doi(self):
        self.assertEqual(pc.ref_doi("doi: 10.1001/JAMA.2020.1511"), "10.1001/jama.2020.1511")
        self.assertEqual(pc.ref_doi("JAMA. 2025 Jun 17;333(23):2058-2060. doi: 10.1001/jama.2025.4321."),
                         "10.1001/jama.2025.4321")
        self.assertEqual(pc.ref_doi("no identifier"), "")


class TestParse(unittest.TestCase):
    def setUp(self):
        self.arts = pc.parse_articles(FIXTURE)

    def test_record(self):
        a = self.arts[0]
        self.assertEqual(a["pmid"], "40274279")
        self.assertEqual(a["doi"], "10.1001/jama.2025.3471")
        self.assertEqual(a["ta"], "JAMA")
        self.assertEqual(a["year"], 2025)
        self.assertEqual(a["pubtypes"], ["Randomized Controlled Trial"])
        self.assertEqual([c["cls"] for c in a["comment_in"]], ["bare_doi", "pmid", "other_nopmid"])
        self.assertEqual([c["doi"] for c in a["comment_in"]],
                         ["10.1001/jamanetworkopen.2023.3646", "10.1001/jama.2025.4321", ""])
        self.assertEqual(a["comment_in"][1]["pmid"], "40366665")
        self.assertEqual(a["comment_on"], [])

    def test_second_record(self):
        b = self.arts[1]
        self.assertEqual(b["pmid"], "40366665")
        self.assertEqual(b["doi"], "")
        self.assertEqual(b["year"], 2025)
        self.assertEqual(b["comment_on"], ["40366680"])
        self.assertEqual(b["comment_in"], [])

    def test_links_and_tallies(self):
        arts = {a["pmid"]: a for a in self.arts}
        recs = {"40274279": ("jama_network", "JAMA", 2025), "40366665": ("jama_network", "JAMA", 2025)}
        links = pc.build_links(arts, recs)
        self.assertEqual(len(links), 3)
        self.assertEqual(pc.tally(links), {"jama_network": {"pmid": 1, "bare_doi": 1, "other_nopmid": 1}})
        self.assertEqual(pc.prefix_tally(links), {"jama_network": [1, 1]})
        by_year = pc.breakdown(arts, recs, "year")
        self.assertEqual(by_year["jama_network|2025"],
                         {"records": 2, "with_bare_doi": 1, "links": 3, "bare_doi_links": 1})


class TestDates(unittest.TestCase):
    def test_earlier(self):
        self.assertTrue(pc.earlier([2024, 12, 10], [2025, 5, 27]))
        self.assertFalse(pc.earlier([2025, 9, 1], [2025, 8, 19]))
        self.assertFalse(pc.earlier([2025, 8], [2025, 8, 19]))
        self.assertTrue(pc.earlier([2025, 7], [2025, 8, 19]))
        self.assertIsNone(pc.earlier([], [2025]))

    def test_crossref_batches(self):
        calls = []

        def fake(url):
            calls.append(url)
            return {"message": {"items": [{"DOI": "10.1001/JAMA.2024.17482",
                                           "published": {"date-parts": [[2024, 12, 10]]},
                                           "type": "journal-article", "title": ["What Is Knee Osteoarthritis?"]}]}}

        dois = {f"10.1001/x.{i}" for i in range(45)} | {"", "10.1/a,b"}
        out = pc.crossref_dates(dois, fake)
        self.assertEqual(len(calls), 3)
        self.assertEqual(out["10.1001/jama.2024.17482"]["date"], [2024, 12, 10])

    def test_crossref_fallback(self):
        def fake(url):
            if "filter=" in url:
                raise ValueError("bad batch")
            return {"message": {"DOI": "10.1001/a", "published": {"date-parts": [[2020, 1]]}}}

        errors = []
        out = pc.crossref_dates({"10.1001/a"}, fake, errors)
        self.assertEqual(out["10.1001/a"]["date"], [2020, 1])
        self.assertEqual(len(errors), 1)

    def test_dating_and_reciprocity_tallies(self):
        links = [{"group": "g", "cls": "bare_doi", "earlier": True},
                 {"group": "g", "cls": "bare_doi", "earlier": False},
                 {"group": "g", "cls": "bare_doi", "earlier": None}]
        self.assertEqual(pc.dating_tally(links), {"g": {"bare_doi": [2, 1]}})
        checks = [{"group": "g", "cls": "pmid", "reciprocal": True},
                  {"group": "g", "cls": "pmid", "reciprocal": None}]
        self.assertEqual(pc.reciprocity_tally(checks), {"g": {"pmid": [1, 1]}})


class TestJudge(unittest.TestCase):
    def test_judge(self):
        self.assertEqual(pc.judge([(100, 5, ">=", 0.02, 100), (200, 0, "<=", 0.005, 100)]), "supported")
        self.assertEqual(pc.judge([(99, 50, ">=", 0.02, 100)]), "untestable")
        self.assertEqual(pc.judge([(100, 1, ">=", 0.02, 100)]), "not supported")

    def test_verdicts(self):
        t = {"jama_network": {"pmid": 900, "bare_doi": 100, "other_nopmid": 0},
             "control": {"pmid": 1000, "bare_doi": 0, "other_nopmid": 0}}
        dating = {"jama_network": {"bare_doi": [50, 45], "pmid": [50, 1]}}
        recip = {"jama_network": {"bare_doi": [40, 0], "pmid": [40, 39]}}
        prefix = {"jama_network": [100, 100]}
        self.assertEqual(pc.verdicts(t, dating, recip, prefix),
                         {"H1": "supported", "H2": "supported", "H3": "supported", "H4": "supported"})
        self.assertEqual(pc.verdicts({}, {}, {}, {})["H1"], "untestable")


class TestConstants(unittest.TestCase):
    def test_pilot_held_out(self):
        self.assertEqual(len(pc.PILOT_PMIDS), 76)
        self.assertIn("40274279", pc.PILOT_PMIDS)

    def test_sample(self):
        self.assertEqual(pc.sample([1, 2], 5, random.Random(1)), [1, 2])
        a = pc.sample(list(range(100)), 10, random.Random(pc.SEED))
        b = pc.sample(list(range(100)), 10, random.Random(pc.SEED))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 10)


if __name__ == "__main__":
    unittest.main()
