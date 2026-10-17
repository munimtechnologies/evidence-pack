# Offline tests for hindawi_sink.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import article1_check as a1
import hindawi_sink as h
import openalex_article1 as oa1

CRL = "https://api.crossref.org/works?"
CRW = "https://api.crossref.org/works/"
NAMES = [["biomed", "research", "international"]]
FILL = [{"key": "f%d" % i, "DOI": "10.1000/f%d" % i, "first-page": "5"} for i in range(5)]

TOP_2017 = [
    {"id": "https://openalex.org/WA", "doi": "https://doi.org/10.1155/2017/1111111", "cited_by_count": 300, "title": "Sink",
     "counts_by_year": [{"year": 2020, "cited_by_count": 290}, {"year": 2023, "cited_by_count": 10}]},
    {"id": "https://openalex.org/WB", "doi": "https://doi.org/10.1155/2017/2222222", "cited_by_count": 500, "title": "Real",
     "counts_by_year": [{"year": 2019, "cited_by_count": 200}, {"year": 2024, "cited_by_count": 300}]},
    {"id": "https://openalex.org/WC", "doi": "https://doi.org/10.1155/2016/3333333", "cited_by_count": 100},
    {"id": "https://openalex.org/WD", "doi": "https://doi.org/10.1155/2017/4444444", "cited_by_count": 100}]
TOP_2022 = [{"id": "https://openalex.org/WE", "doi": "https://doi.org/10.1155/2022/5555555", "cited_by_count": 20,
             "counts_by_year": [{"year": 2024, "cited_by_count": 20}]}]
COUNTS = [{"DOI": "10.1155/2017/1111111", "is-referenced-by-count": 9},
          {"DOI": "10.1155/2017/2222222", "is-referenced-by-count": 450},
          {"DOI": "10.1155/2022/5555555", "is-referenced-by-count": 18}]
WORKS = {
    "10.1155/2017/1111111": {"DOI": "10.1155/2017/1111111", "title": ["Sink paper on decision tools"],
                             "container-title": ["BioMed Research International"]},
    "10.1155/2017/2222222": {"DOI": "10.1155/2017/2222222", "title": ["Phagocytosis fundamental process immunity"]},
    "10.1000/c1": {"DOI": "10.1000/c1", "issued": {"date-parts": [[2020, 3]]}, "reference": [
        {"key": "r1", "DOI": "10.1155/2017/7777777", "first-page": "1", "journal-title": "Biomed. Res. Int.", "volume": "2017"}] + FILL},
    "10.1000/c2": {"DOI": "10.1000/c2", "reference": [{"key": "r1", "DOI": "10.1155/2017/1111111"}]},
    "10.1000/c3": {"DOI": "10.1000/c3", "reference": [{"key": "x", "DOI": "10.1155/2017/2222222"}]}}


def fake(url):
    if url.startswith(CRL):
        if "facet=issn" in url:
            return json.dumps({"message": {"facets": {"issn": {"values": {"https://id.crossref.org/issn/1111-1111": 10}}}}}).encode()
        return json.dumps({"message": {"items": COUNTS}}).encode()
    if url.startswith(CRW):
        msg = WORKS.get(urllib.parse.unquote(url[len(CRW):].split("?")[0]))
        return json.dumps({"message": msg}).encode() if msg else None
    if url.startswith(a1.OA + "?"):
        if "group_by" in url:
            n = 150 if ("2017" in url or "2022" in url) else 50
            return json.dumps({"group_by": [{"key": "https://openalex.org/S1", "key_display_name": "J1", "count": n}]}).encode()
        if "cites%3AWA" in url:
            return json.dumps({"results": [{"id": "https://openalex.org/WC1", "doi": "https://doi.org/10.1000/c1"},
                                           {"id": "https://openalex.org/WC2", "doi": "https://doi.org/10.1000/c2"}]}).encode()
        if "cites%3AWB" in url:
            return json.dumps({"results": [{"id": "https://openalex.org/WC3", "doi": "https://doi.org/10.1000/c3"}]}).encode()
        if "referenced_works" in url:
            return json.dumps({"results": [{"id": "https://openalex.org/WC1", "doi": "https://doi.org/10.1000/c1",
                                            "referenced_works": ["https://openalex.org/WA", "https://openalex.org/W7"]}]}).encode()
        if "sort=" in url:
            return json.dumps({"results": TOP_2017 if "2017" in url else TOP_2022}).encode()
        return json.dumps({"results": [{"id": "https://openalex.org/W7", "doi": "https://doi.org/10.1155/2017/7777777",
                                        "cited_by_count": 40}]}).encode()
    return None


def row(doi, oa, cr, to=None):
    return {"doi": doi, "oa_id": "https://openalex.org/" + doi, "oa": oa, "cr": cr, "e": oa1.excess(oa, cr), "to_2021": to}


def jy(sink, s_to=0.95, c_to=0.5):
    j = {"source": "S9", "year": 2017, "status": "ok"}
    j["judge"] = {"rows": 25, "sink": row("s", 300, 9, s_to) if sink else None, "control": row("c", 500, 450, c_to),
                  "over": 1 if sink else 0, "sink_rank": 2 if sink else None}
    return j


def read(label, role="sink"):
    return {"role": role, "label": label}


class TestParsing(unittest.TestCase):
    def test_doi_year(self):
        self.assertEqual(h.doi_year("10.1155/2017/6353510"), 2017)
        self.assertEqual(h.doi_year(" 10.1155/2013/849529 "), 2013)
        self.assertIsNone(h.doi_year("10.1155/2017/abc"))
        self.assertIsNone(h.doi_year("10.3390/ijms18010001"))
        self.assertIsNone(h.doi_year(None))

    def test_parse_issns(self):
        data = {"message": {"facets": {"issn": {"values": {"https://id.crossref.org/issn/2314-6141": 5,
                                                           "http://id.crossref.org/issn/1942-090x": 3, "junk": 1}}}}}
        self.assertEqual(h.parse_issns(data), ["1942-090X", "2314-6141"])
        self.assertIsNone(h.parse_issns({}))
        self.assertIsNone(h.parse_issns(None))

    def test_parse_groups(self):
        data = {"group_by": [{"key": "https://openalex.org/S1", "key_display_name": "J1", "count": 150},
                             {"key": "unknown", "count": 3}]}
        self.assertEqual(h.parse_groups(data), [("S1", "J1", 150)])
        self.assertEqual(h.parse_groups(None), [])

    def test_urls(self):
        self.assertTrue(h.issn_url(2017).startswith(CRL))
        self.assertIn("prefix%3A10.1155", h.issn_url(2017))
        self.assertIn("2017-12-31", h.issn_url(2017))
        u = h.sources_url(2018, ["1111-1111", "2222-2222"])
        self.assertIn("publication_year%3A2018", u)
        self.assertIn("1111-1111%7C2222-2222", u)
        self.assertIn("group_by=primary_location.source.id", u)
        t = h.top_url("S1", 2019)
        self.assertIn("primary_location.source.id%3AS1%2Cpublication_year%3A2019", t)
        self.assertIn("sort=cited_by_count%3Adesc", t)
        self.assertIn("per-page=25", t)

    def test_to_2021(self):
        self.assertEqual(h.to_2021([{"year": 2021, "cited_by_count": 3}, {"year": 2022, "cited_by_count": 1}]), 0.75)
        self.assertIsNone(h.to_2021([]))
        self.assertIsNone(h.to_2021(None))

    def test_crossref_counts(self):
        self.assertEqual(h.crossref_counts(fake, ["10.1155/2017/1111111"])["10.1155/2017/2222222"], 450)
        self.assertEqual(h.crossref_counts(fake, []), {})
        self.assertIsNone(h.crossref_counts(lambda u: None, ["10.1155/2017/1111111"]))

    def test_journal_years_failure(self):
        jys, info = h.journal_years(lambda u: None, 2017)
        self.assertEqual(jys, [])
        self.assertEqual(info["failed_calls"], 1)


class TestJudge(unittest.TestCase):
    def test_sink(self):
        d = h.judge([row("b", 500, 450), row("a", 300, 9), row("c", 100, 95)])
        self.assertEqual(d["sink"]["doi"], "a")
        self.assertEqual(d["sink_rank"], 2)
        self.assertEqual(d["control"]["doi"], "b")
        self.assertEqual(d["over"], 1)
        self.assertAlmostEqual(d["max_e"], 30.1)
        self.assertAlmostEqual(d["second_e"], 501 / 451)

    def test_small_gap_is_not_a_sink(self):
        d = h.judge([row("a", 40, 0), row("b", 500, 450), row("c", 100, 95)])
        self.assertIsNone(d["sink"])
        self.assertIsNone(d["sink_rank"])
        self.assertEqual(d["control"]["doi"], "b")
        self.assertAlmostEqual(d["max_e"], 41.0)

    def test_small_outlier_does_not_hide_the_sink(self):
        d = h.judge([row("a", 30, 0), row("d", 600, 40), row("b", 500, 450)])
        self.assertEqual(d["sink"]["doi"], "d")
        self.assertEqual(d["sink_rank"], 1)
        self.assertEqual(d["over"], 1)

    def test_empty(self):
        d = h.judge([])
        self.assertEqual((d["rows"], d["sink"], d["control"]), (0, None, None))

    def test_examine(self):
        j = {"source": "S1", "year": 2017}
        self.assertEqual(h.examine(fake, j), 0)
        self.assertEqual([r["doi"] for r in j["top"]], ["10.1155/2017/1111111", "10.1155/2017/2222222"])
        self.assertEqual(j["judge"]["sink"]["doi"], "10.1155/2017/1111111")
        self.assertEqual(j["judge"]["sink_rank"], 2)
        self.assertAlmostEqual(j["judge"]["sink"]["to_2021"], 290 / 300)
        self.assertEqual(j["judge"]["control"]["doi"], "10.1155/2017/2222222")
        j = {"source": "S1", "year": 2017}
        self.assertEqual(h.examine(lambda u: None, j), 1)
        self.assertEqual(j["status"], "openalex_failed")


class TestCiters(unittest.TestCase):
    def test_siblings(self):
        refs = [{"DOI": "10.1155/2017/7777777", "first-page": "1", "journal-title": "Biomed. Res. Int."},
                {"DOI": "10.1155/2017/8888888", "first-page": "1"},  # no journal title: the DOI's year is enough
                {"DOI": "10.1155/2017/9999999", "first-page": "1", "journal-title": "Oxid Med Cell Longev"},
                {"DOI": "10.1155/2016/7777777", "first-page": "1", "journal-title": "Biomed Res Int"},
                {"DOI": "10.1155/2017/6666666", "first-page": "12", "journal-title": "Biomed Res Int"},
                {"DOI": "10.1155/2017/1111111", "first-page": "1"},  # the target itself
                {"journal-title": "BioMed Res Int", "volume": "2017", "first-page": "1"},
                {"journal-title": "BioMed Res Int", "year": "2017", "first-page": "1"},
                {"journal-title": "BioMed Res Int", "volume": "2016", "first-page": "1"}]
        got = h.siblings(refs, "10.1155/2017/1111111", NAMES, 2017)
        self.assertEqual([refs.index(r) for r in got], [0, 1, 6, 7])

    def test_label_citer(self):
        t, w = "10.1155/2017/1111111", ["paper", "decision", "tools"]
        self.assertEqual(h.label_citer(None, t, w, NAMES, 2017), ("not_in_crossref", []))
        self.assertEqual(h.label_citer(WORKS["10.1000/c2"], t, w, NAMES, 2017)[0], "genuine")
        by_title = {"reference": [{"key": "a", "article-title": "A decision support paper"}]}
        self.assertEqual(h.label_citer(by_title, t, w, NAMES, 2017)[0], "genuine")
        label, sib = h.label_citer(WORKS["10.1000/c1"], t, w, NAMES, 2017)
        self.assertEqual((label, [r["key"] for r in sib]), ("sibling", ["r1"]))
        self.assertEqual(h.label_citer({"reference": FILL}, t, w, NAMES, 2017)[0], "unsupported")
        self.assertEqual(h.label_citer({"reference": FILL[:4]}, t, w, NAMES, 2017)[0], "too_few_references")


class TestScoring(unittest.TestCase):
    def test_h1(self):
        v, d = h.score_h1([jy(i < 12) for i in range(30)])
        self.assertEqual((v, d["with_sink"], d["journal_years"]), ("supported", 12, 30))
        self.assertEqual(h.score_h1([jy(i < 11) for i in range(30)])[0], "not supported")
        self.assertEqual(h.score_h1([jy(True)] * 29)[0], "untestable")

    def test_h2(self):
        old = [jy(i < 12) for i in range(30)]
        v, d = h.score_h2(old, [jy(False)] * 30)
        self.assertEqual(v, "supported")
        self.assertLess(d["p"], 0.001)
        self.assertGreater(d["p"], 0)
        self.assertEqual(h.score_h2(old, [jy(i < 2) for i in range(30)])[0], "not supported")  # 2/30 > 0.05
        self.assertEqual(h.score_h2(old, [jy(False)] * 29)[0], "untestable")

    def test_h3(self):
        t = [read("sibling")] * 30 + [read("unsupported")] * 10 + [read("genuine")] * 5 + [read("not_in_crossref")] * 3
        c = [read("genuine", "control")] * 30 + [read("unsupported", "control")] * 5
        v, d = h.score_h3(t, c)
        self.assertEqual((v, d["readable"], d["sibling"], d["sink_genuine"]), ("supported", 40, 30, 5))
        bad = [read("genuine", "control")] * 20 + [read("unsupported", "control")] * 15
        self.assertEqual(h.score_h3(t, bad)[0], "untestable (classifier failed calibration)")
        self.assertEqual(h.score_h3(t[1:], c)[0], "untestable")
        low = [read("sibling")] * 20 + [read("unsupported")] * 20
        self.assertEqual(h.score_h3(low, c)[0], "not supported")

    def test_h4(self):
        r = {"label": "sibling", "siblings": [{"in_oa": i < 16} for i in range(20)] + [{"in_oa": None}]}
        v, d = h.score_h4([r])
        self.assertEqual((v, d["references"], d["kept"]), ("supported", 20, 16))
        r2 = {"label": "sibling", "siblings": [{"in_oa": True}] * 19}
        self.assertEqual(h.score_h4([r2])[0], "untestable")

    def test_h5(self):
        v, d = h.score_h5([jy(True) for _ in range(10)] + [jy(False)])
        self.assertEqual((v, d["pairs"], d["sink_higher"]), ("supported", 10, 10))
        self.assertAlmostEqual(d["p"], 1 / 1024)
        self.assertEqual(h.score_h5([jy(True, s_to=0.85) for _ in range(10)])[0], "not supported")
        self.assertEqual(h.score_h5([jy(True) for _ in range(9)])[0], "untestable")

    def test_pick_is_order_free(self):
        pool = [{"source": "S%d" % i, "year": 2016 + i % 4} for i in range(50)]
        self.assertEqual(h.pick(pool, 10, 1), h.pick(list(reversed(pool)), 10, 1))
        self.assertEqual(len(h.pick(pool, 80, 1)), 50)


class TestRun(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(h, "MIN_ROWS", 1):
            res = h.run(fake, tmp)
            with open(os.path.join(tmp, "journal_years.jsonl"), encoding="utf-8") as fh:
                jys = [json.loads(x) for x in fh]
            with open(os.path.join(tmp, "reads.jsonl"), encoding="utf-8") as fh:
                reads = [json.loads(x) for x in fh]
            self.assertTrue(os.path.exists(os.path.join(tmp, "results.json")))
        self.assertEqual(res["pool"], {"old": 1, "new": 1})
        self.assertEqual(res["listing"]["2017"]["eligible"], 1)
        self.assertEqual(res["listing"]["2016"]["eligible"], 0)
        self.assertEqual(res["failed_examinations"], 0)
        self.assertEqual([(j["year"], j["era"]) for j in jys], [(2017, "old"), (2022, "new")])
        self.assertEqual(res["H1"], "untestable")
        self.assertEqual(res["H1_detail"]["with_sink"], 1)
        self.assertEqual(res["H2_detail"]["new_with_sink"], 0)
        self.assertEqual(res["H5_detail"]["sink_higher"], 1)
        self.assertEqual(res["labels"], {"sink": {"sibling": 1, "genuine": 1}, "control": {"genuine": 1}})
        self.assertEqual(res["H3"], "untestable (classifier failed calibration)")
        self.assertEqual(res["H4_detail"], {"references": 1, "kept": 1, "share": 1.0})
        sib = [r for r in reads if r["label"] == "sibling"][0]
        self.assertTrue(sib["oa_has_target"])
        self.assertEqual(sib["year"], 2020)
        self.assertEqual(res["descriptive"]["2017"]["phantom_citations"], 291)
        self.assertEqual(res["descriptive"]["2022"]["with_sink"], 0)
        self.assertEqual(res["reads"]["targets"][0]["sink_sample"], 2)
        self.assertEqual(res["reads"]["targets"][0]["control_sample"], 1)


if __name__ == "__main__":
    unittest.main()
