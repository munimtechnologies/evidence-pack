# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import io
import unittest

import gate_compare as gc
import pm_extract as pm
import spark_eval as se

BLAST_Q = "Which paper introduced the BLAST algorithm for rapid local sequence similarity searching?"
XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
 <PubmedArticle>
  <MedlineCitation><PMID Version="1">2231712</PMID>
   <Article><Journal><JournalIssue><PubDate><Year>1990</Year></PubDate></JournalIssue>
     <ISOAbbreviation>J Mol Biol</ISOAbbreviation></Journal>
    <ArticleTitle>Basic local alignment search tool.</ArticleTitle>
    <Abstract><AbstractText>A new approach to rapid sequence comparison, basic local alignment search tool (BLAST).</AbstractText></Abstract>
    <AuthorList><Author><LastName>Altschul</LastName><Initials>SF</Initials></Author></AuthorList>
    <PublicationTypeList><PublicationType UI="D016428">Journal Article</PublicationType></PublicationTypeList>
   </Article>
  </MedlineCitation>
  <PubmedData><ArticleIdList><ArticleId IdType="pubmed">2231712</ArticleId></ArticleIdList></PubmedData>
 </PubmedArticle>
</PubmedArticleSet>
"""
# the 26 PMIDs selected by the pre-registered rule (prereg-devset-ordinary-v1.md)
SELECTED = {"1000007", "2350000", "3700000", "6400000", "7750002", "9100000", "10450000", "11800002",
            "14500000", "15850000", "17200012", "18550003", "19900000", "23950000", "25300000", "26650015",
            "28000000", "29350000", "30700000", "32050000", "33400000", "34750000", "36100000", "37450000",
            "38800000", "40150000"}


def doc(pmid, title, abstract="", year=2000, ptypes=("Journal Article",)):
    return {"pmid": str(pmid), "title": title, "abstract": abstract, "year": year, "journal": "J",
            "authors": ["A B"], "mesh": [], "keywords": [], "ptypes": list(ptypes)}


class TextTests(unittest.TestCase):
    def test_terms(self):
        self.assertEqual(se.terms(BLAST_Q), ["blast", "algorithm", "rapid", "local", "sequence", "similarity",
                                             "searching"])
        self.assertEqual(se.terms("Find the 1961 paper that introduced the Beck Depression Inventory."),
                         ["1961", "beck", "depression", "inventory"])

    def test_fts_query_and_rr(self):
        self.assertEqual(se.fts_query(["a", "b2"]), '"a" OR "b2"')
        self.assertEqual(se.rr([5, 3, 9], 3), 0.5)
        self.assertEqual(se.rr(["5", "3"], 5), 1.0)
        self.assertEqual(se.rr([1, 2, 3, 4, 5, 6], 6), 0.0)
        self.assertEqual(se.rr([], 1), 0.0)

    def test_sample_files(self):
        files = se.sample_files(40, 1306)
        self.assertEqual(len(files), 40)
        self.assertEqual((files[0], files[-1]), (1, 1306))

    def test_ordinary_devset(self):
        rows = pm.load_devset("devset_ordinary_v1.jsonl")
        self.assertEqual(len(rows), 26)
        self.assertEqual({r["pmid"] for r in rows}, SELECTED)
        self.assertEqual(len({r["info_need_id"] for r in rows}), 26)
        self.assertEqual({r["kind"] for r in rows}, {"ordinary"})
        for r in rows:
            self.assertGreaterEqual(len(se.terms(r["info_need"])), 2, r["info_need_id"])
        # pre-registered: a year in at most 1 in 5 questions
        self.assertLessEqual(sum(1 for r in rows if se.YEAR_Q.search(r["info_need"])), 5)

    def test_cue_counts(self):
        # prereg-cite-gate-v1.md: no ordinary question has a priority cue, so cite|cue = fields+ptype there
        ordinary = pm.load_devset("devset_ordinary_v1.jsonl")
        self.assertEqual([r["info_need_id"] for r in ordinary if se.CUE.search(r["info_need"].lower())], [])
        # counted by hand from the question texts before the job ran
        landmark = pm.load_devset("devset_landmark_v1.jsonl")
        self.assertEqual(len(landmark), 72)
        self.assertEqual(sum(1 for r in landmark if se.CUE.search(r["info_need"].lower())), 35)

    def test_hard_negative_part(self):
        self.assertEqual(se.hard_negative_part("/work/devset_landmark_v1.jsonl"), "hard-negatives")
        self.assertEqual(se.hard_negative_part("devset_ordinary_v1.jsonl"),
                         "hard-negatives:devset_ordinary_v1.jsonl")


class StatsTests(unittest.TestCase):
    def test_quartiles(self):
        self.assertEqual(se.quartiles([4, 1, 3, 2]), (1.75, 2.5, 3.25))
        self.assertEqual(se.quartiles([None, 5]), (5, 5, 5))
        self.assertIsNone(se.quartiles([None]))

    def test_compare(self):
        rows = [{"id": "a", "x": {"rr": 1.0}, "y": {"rr": 0.5}},
                {"id": "b", "x": {"rr": 0.0}, "y": {"rr": 1.0}},
                {"id": "c", "x": {"rr": 0.5}, "y": {"rr": 0.5}}]
        c = se.compare(rows, "x", "y")
        self.assertEqual((c["delta_mrr5"], c["helped"], c["hurt"], c["same"], c["hurt_ids"]),
                         (0.1667, 1, 1, 1, ["a"]))


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.db = se.connect(":memory:")

    def test_add_rules(self):
        self.assertTrue(se.add(self.db, doc(1, "Basic local alignment search tool"), "t"))
        self.assertFalse(se.add(self.db, doc(1, "again"), "t"))
        self.assertFalse(se.add(self.db, doc(2, "old", year=1953), "t"))
        self.assertFalse(se.add(self.db, doc(3, "new", year=2027), "t"))
        self.assertFalse(se.add(self.db, doc(4, "preprint", ptypes=("Preprint",)), "t"))
        self.assertTrue(se.add(self.db, doc(5, "no year", year=None), "t"))

    def test_add_xml(self):
        self.assertEqual(se.add_xml(self.db, io.BytesIO(XML), "efetch"), 1)
        self.assertEqual(self.db.execute("SELECT year, ptypes FROM meta WHERE pmid=2231712").fetchone(),
                         (1990, "Journal Article"))

    def test_search(self):
        se.add(self.db, doc(1, "Basic local alignment search tool",
                            "A new approach to rapid sequence comparison (BLAST).", 1990), "t")
        se.add(self.db, doc(2, "BLAST review", "We review BLAST sequence similarity searching.", 2005,
                            ("Review",)), "t")
        se.add(self.db, doc(3, "Cholesterol in rats", "Serum lipids were measured.", 1980), "t")
        hits = se.search(self.db, BLAST_Q, (3, 1, 1, 1, 0.5))
        self.assertEqual({p for p, _ in hits}, {1, 2})
        self.assertTrue(all(s > 0 for _, s in hits))


class RerankTests(unittest.TestCase):
    CANDS = [(10, 10.0), (20, 9.0), (30, 8.0)]
    META = {10: (2005, "Review"), 20: (1990, "Journal Article"), 30: (2015, "Journal Article")}

    def test_demote(self):
        self.assertEqual(se.rerank(self.CANDS, self.META, {}, "Which paper introduced BLAST?", demote=0.6),
                         [20, 30, 10])

    def test_citations(self):
        self.assertEqual(se.rerank(self.CANDS, self.META, {30: 10000}, "Find the BLAST tool", beta=0.3),
                         [30, 10, 20])

    def test_cue_gate(self):
        cites = {30: 10000}
        # no cue word: the gated prior is off, BM25 order stays
        self.assertEqual(se.rerank(self.CANDS, self.META, cites, "Find the BLAST tool", beta=0.3, gate="cue"),
                         [10, 20, 30])
        # cue word: 0.8 + 0.3 = 1.1 beats 1.0
        self.assertEqual(se.rerank(self.CANDS, self.META, cites, "Which paper introduced BLAST?", beta=0.3,
                                   gate="cue"), [30, 10, 20])

    def test_band(self):
        cites = {30: 10000}
        # 30 scores 0.8 of the top: outside a 0.85 band, inside a 0.75 band
        self.assertEqual(se.rerank(self.CANDS, self.META, cites, "Find the BLAST tool", beta=0.3, band=0.85),
                         [10, 20, 30])
        self.assertEqual(se.rerank(self.CANDS, self.META, cites, "Find the BLAST tool", beta=0.3, band=0.75),
                         [30, 10, 20])

    def test_methods_named_in_prereg(self):
        names = [n for n, _ in se.METHODS]
        for n in gc.CANDIDATES + gc.REPORTED:
            self.assertIn(n, names)
        self.assertIn(se.MISSES, names)


class DecisionTests(unittest.TestCase):
    LM = {"fields+ptype": 0.68, "fields+ptype+cite0.1": 0.75, "fields+ptype+cite|band0.8": 0.80,
          "fields+ptype+cite|cue": 0.85, "fields+ptype+cite|cue+early+year": 0.86, "fields+ptype+cite": 0.88}
    OD = {"fields+ptype": 0.81, "fields+ptype+cite0.1": 0.78, "fields+ptype+cite|band0.8": 0.80,
          "fields+ptype+cite|cue": 0.81, "fields+ptype+cite|cue+early+year": 0.80, "fields+ptype+cite": 0.74}

    def test_tie_goes_to_simpler(self):
        chosen, table = gc.decide(self.LM, self.OD)
        self.assertEqual(chosen, "fields+ptype+cite|cue")
        elig = {r["method"]: r["eligible"] for r in table}
        self.assertFalse(elig["fields+ptype+cite0.1"])  # 0.78 < 0.81 - 0.02
        self.assertFalse(elig["fields+ptype+cite"])  # reported only

    def test_reference_when_nothing_beats_it(self):
        lm = dict(self.LM, **{k: 0.5 for k in self.LM if k != "fields+ptype"})
        self.assertEqual(gc.decide(lm, self.OD)[0], "fields+ptype")


if __name__ == "__main__":
    unittest.main()
