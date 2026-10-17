# Offline tests for article1_check.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import json
import unittest

import article1_check as a1


class FakeClient:
    def __init__(self, records):
        self.records, self.calls = {k.lower(): v for k, v in records.items()}, 0

    def work(self, doi):
        self.calls += 1
        return self.records.get(doi.lower())


def rec(doi, cites, page=None, number=None, title="A title", family="smith"):
    m = {"DOI": doi, "is-referenced-by-count": cites, "type": "journal-article", "title": [title],
         "issued": {"date-parts": [[2019, 1, 2]]}, "author": [{"family": family.title()}]}
    if page is not None:
        m["page"] = page
    if number is not None:
        m["article-number"] = number
    return m


def unit(c1, far, near=(), confirmatory=True, publisher="MDPI"):
    return {"publisher": publisher, "journal": "x", "volume": 1, "year": 2019, "confirmatory": confirmatory,
            "article1": {"doi": "10.3390/x1010001", "cites": c1, "title": "Gut bacteria adipose tissue liver",
                         "first_author": "smith", "type": "journal-article"},
            "near": [{"cites": c} for c in near], "far": [{"cites": c, "doi": "d%d" % i} for i, c in enumerate(far)]}


class TestDois(unittest.TestCase):
    def test_mdpi(self):
        self.assertEqual(a1.mdpi_doi("ijms", 20, 1, 1), "10.3390/ijms20010001")
        self.assertEqual(a1.mdpi_doi("nu", 11, 3, 41), "10.3390/nu11030041")
        self.assertEqual(a1.mdpi_doi("ijms", 23, 24, 15966), "10.3390/ijms232415966")
        self.assertEqual(a1.mdpi_doi("jcm", 8, 1, 2), "10.3390/jcm8010002")

    def test_frontiers(self):
        self.assertEqual(a1.frontiers_doi("fimmu", 2019, 1), "10.3389/fimmu.2019.00001")
        self.assertEqual(a1.frontiers_doi("fpsyg", 2018, 2545), "10.3389/fpsyg.2018.02545")

    def test_number_of(self):
        self.assertEqual(a1.number_of({"page": "1"}), "1")
        self.assertEqual(a1.number_of({"article-number": "1"}), "1")
        self.assertEqual(a1.number_of({"page": "1-15"}), "1")
        self.assertEqual(a1.number_of({}), "")

    def test_offsets_give_2019_volumes(self):
        want = {"ijms": 20, "molecules": 24, "s": 19, "nu": 11, "cancers": 11, "jcm": 8, "ijerph": 16, "ma": 12,
                "app": 9, "su": 11, "en": 12, "rs": 11, "cells": 8, "antiox": 8}
        self.assertEqual({k: 2019 - v for k, v in a1.MDPI.items()}, want)


class TestUnits(unittest.TestCase):
    def test_find_mdpi_follows_issues(self):
        c = FakeClient({"10.3390/nu11020041": rec("10.3390/nu11020041", 3, page="41")})
        msg, issue = a1.find_mdpi(c, "nu", 11, 41, 1)
        self.assertEqual(issue, 2)
        self.assertEqual(msg["page"], "41")
        msg, issue = a1.find_mdpi(c, "nu", 11, 42, 2)
        self.assertIsNone(msg)
        self.assertEqual(issue, 2)

    def test_mdpi_unit(self):
        recs = {a1.mdpi_doi("ijms", 20, 1, 1): rec(a1.mdpi_doi("ijms", 20, 1, 1), 900, page="1"),
                a1.mdpi_doi("ijms", 20, 1, 2): rec(a1.mdpi_doi("ijms", 20, 1, 2), 5, page="2"),
                a1.mdpi_doi("ijms", 20, 2, 41): rec(a1.mdpi_doi("ijms", 20, 2, 41), 7, page="41"),
                a1.mdpi_doi("ijms", 20, 2, 42): rec(a1.mdpi_doi("ijms", 20, 2, 42), 9, page="42")}
        u = a1.mdpi_unit(FakeClient(recs), "ijms", 20, near=range(2, 3), far=range(41, 43))
        self.assertEqual(u["year"], 2019)
        self.assertFalse(u["confirmatory"])  # the motivating case
        self.assertEqual(u["article1"]["cites"], 900)
        self.assertEqual([r["n"] for r in u["near"]], [2])
        self.assertEqual([r["cites"] for r in u["far"]], [7, 9])
        self.assertIsNone(a1.mdpi_unit(FakeClient({}), "ijms", 20))

    def test_frontiers_unit(self):
        recs = {a1.frontiers_doi("fimmu", 2019, 1): dict(rec(a1.frontiers_doi("fimmu", 2019, 1), 50, number="1"),
                                                         volume="10"),
                a1.frontiers_doi("fimmu", 2019, 41): rec(a1.frontiers_doi("fimmu", 2019, 41), 4, number="41")}
        u = a1.frontiers_unit(FakeClient(recs), "fimmu", 2019, near=range(2, 4), far=range(41, 43))
        self.assertEqual(u["volume"], "10")
        self.assertTrue(u["confirmatory"])
        self.assertEqual(u["article1"]["number"], "1")
        self.assertEqual(len(u["near"]), 0)
        self.assertEqual(len(u["far"]), 1)


class TestStats(unittest.TestCase):
    def test_poisson_binomial(self):
        self.assertAlmostEqual(a1.poisson_binomial_tail([0.5, 0.5], 0), 1.0)
        self.assertAlmostEqual(a1.poisson_binomial_tail([0.5, 0.5], 1), 0.75)
        self.assertAlmostEqual(a1.poisson_binomial_tail([0.5, 0.5], 2), 0.25)
        self.assertEqual(a1.poisson_binomial_tail([0.5, 0.5], 3), 0.0)

    def test_sign_test(self):
        self.assertAlmostEqual(a1.sign_test(9, 1), 11 / 1024)
        self.assertEqual(a1.sign_test(0, 0), 1.0)

    def test_ratio_and_top(self):
        self.assertAlmostEqual(a1.smoothed_ratio(9, [0, 1, 2]), 5.0)
        self.assertTrue(a1.is_top(unit(10, [9, 1])))
        self.assertFalse(a1.is_top(unit(9, [9, 1])))  # ties do not count
        self.assertFalse(a1.is_top(unit(9, [])))

    def test_score_top(self):
        far = list(range(10))
        units = [unit(100, far) for _ in range(8)] + [unit(0, far) for _ in range(2)]
        v, d = a1.score_top(units)
        self.assertEqual(v, "supported")
        self.assertEqual(d["top"], 8)
        self.assertLess(d["p"], 1e-6)
        v, d = a1.score_top([unit(0, far) for _ in range(10)])
        self.assertEqual(v, "not supported")
        v, d = a1.score_top(units[:9])
        self.assertEqual(v, "untestable")
        v, d = a1.score_top(units[:9] + [unit(100, far, confirmatory=False)])
        self.assertEqual(v, "untestable")  # non-confirmatory units are not counted

    def test_score_near(self):
        far = [1] * 10
        v, d = a1.score_near([unit(0, far, near=[5] * 10) for _ in range(10)])
        self.assertEqual(v, "supported")
        self.assertEqual(d["near_higher"], 10)
        v, d = a1.score_near([unit(0, far, near=[1] * 10) for _ in range(10)])
        self.assertEqual(v, "not supported")
        v, d = a1.score_near([unit(0, far, near=[5] * 3) for _ in range(10)])
        self.assertEqual(v, "untestable")


class TestReads(unittest.TestCase):
    words = a1.title_words("Diet-Independent Correlations between <i>Bacteria</i> and Dysfunction of Gut, Adipose Tissue")

    def test_title_words(self):
        self.assertEqual(self.words, ["independent", "correlations", "bacteria", "dysfunction", "adipose", "tissue"])

    def test_classify(self):
        self.assertEqual(a1.classify_ref({"key": "r1", "DOI": "x", "doi-asserted-by": "crossref"}, self.words, "smith"),
                         "doi_only")
        good = {"key": "r2", "DOI": "x", "unstructured": "Smith J. Diet-independent correlations between bacteria "
                                                        "and dysfunction. Int J Mol Sci 2019, 20, 1."}
        self.assertEqual(a1.classify_ref(good, self.words, "smith"), "genuine")
        bad = {"key": "r3", "DOI": "x", "article-title": "Curcumin in colorectal cancer", "volume": "20",
               "first-page": "1"}
        self.assertEqual(a1.classify_ref(bad, self.words, "smith"), "other_work")
        self.assertEqual(a1.classify_ref({"key": "r4", "DOI": "x", "author": "Smith", "volume": "20"}, self.words,
                                         "smith"), "genuine")
        self.assertEqual(a1.classify_ref({"key": "r5", "DOI": "x", "author": "Wang", "volume": "20"}, self.words,
                                         "smith"), "other_work")
        self.assertEqual(a1.classify_ref({"key": "r6", "DOI": "x", "volume": "20", "first-page": "1"}, self.words,
                                         "smith"), "undetermined")

    def test_parse_oc(self):
        raw = json.dumps([{"citing": "omid:br/1 doi:10.1/AB pmid:1"}, {"citing": "omid:br/2"},
                          {"citing": "doi:10.1/ab"}]).encode()
        self.assertEqual(a1.parse_oc(raw), ["10.1/ab"])
        self.assertEqual(a1.parse_oc(None), [])
        self.assertEqual(a1.parse_oc(b"not json"), [])

    def test_read_citers_and_h4(self):
        target = {"doi": "10.3390/x1010001", "title": "Diet-Independent Correlations between Bacteria and Dysfunction",
                  "first_author": "smith"}
        oc = json.dumps([{"citing": "doi:10.9/c%d" % i} for i in range(4)]).encode()
        recs = {"10.9/c0": {"reference": [{"key": "a", "DOI": "10.3390/X1010001", "article-title": "Curcumin and cancer"}]},
                "10.9/c1": {"reference": [{"key": "a", "DOI": "10.3390/x1010001",
                                           "unstructured": "Diet-independent correlations between bacteria"}]},
                "10.9/c2": {"reference": [{"key": "a", "DOI": "10.1/other"}]}}
        reads, n = a1.read_citers(FakeClient(recs), lambda url: oc, target, 1, n=10)
        self.assertEqual(n, 4)
        got = sorted(r.get("label") or r["status"] for r in reads)
        self.assertEqual(got, ["genuine", "no_matching_reference", "not_in_crossref", "other_work"])
        self.assertEqual(a1.share(reads), {"n": 2, "genuine": 1, "share": 0.5})

    def test_score_h4(self):
        g = [{"label": "genuine"}]
        o = [{"label": "other_work"}]
        v, d = a1.score_h4(o * 18 + g * 2, g * 9 + o * 1)
        self.assertEqual(v, "supported")
        v, d = a1.score_h4(o * 18 + g * 2, g * 5 + o * 5)
        self.assertEqual(v, "untestable (classifier failed calibration)")
        v, d = a1.score_h4(o * 5, g * 10)
        self.assertEqual(v, "untestable")
        v, d = a1.score_h4(g * 15 + o * 5, g * 10)
        self.assertEqual(v, "not supported")

    def test_h4_targets(self):
        far = [1] * 10
        hi = unit(500, far)
        hi["article1"]["doi"] = "10.3390/a"
        mid = unit(150, far)
        mid["article1"]["doi"] = "10.3390/b"
        low = unit(50, far)  # under 100 citations
        motiv = unit(900, far, confirmatory=False)
        fr = unit(900, far, publisher="Frontiers")
        got = [u["article1"]["doi"] for u in a1.h4_targets([low, mid, motiv, hi, fr])]
        self.assertEqual(got, ["10.3390/a", "10.3390/b"])

    def test_openalex_counts(self):
        raw = json.dumps({"results": [{"doi": "https://doi.org/10.3390/IJMS20010001", "cited_by_count": 7}]}).encode()
        got, calls = a1.openalex_counts(lambda url: raw, ["10.3390/ijms20010001"])
        self.assertEqual(got, {"10.3390/ijms20010001": 7})
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
