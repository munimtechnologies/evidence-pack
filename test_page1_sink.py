# Offline tests for page1_sink.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import article1_check as a1
import openalex_article1 as oa1
import page1_sink as p

CRL = "https://api.crossref.org/works?"
CRW = "https://api.crossref.org/works/"
NAMES = [["ieee", "transactions", "magnetics"]]
FILL = [{"key": "f%d" % i, "DOI": "10.1000/f%d" % i, "first-page": "5"} for i in range(5)]

GROUPS_2017 = [{"key": "https://openalex.org/S1", "key_display_name": "IEEE Trans Magn", "count": 150},
               {"key": "https://openalex.org/S3", "key_display_name": "Mixed J", "count": 150},
               {"key": "https://openalex.org/S6", "key_display_name": "No total J", "count": 150},
               {"key": "https://openalex.org/S4", "key_display_name": "Small J", "count": 50}]
GROUPS_2022 = [{"key": "https://openalex.org/S5", "key_display_name": "IEEE Photon J", "count": 120}]
TOTALS = {"S1": 160, "S3": 400, "S5": 130, "S4": 60}
TOP_2017 = [
    {"id": "https://openalex.org/WA", "doi": "https://doi.org/10.1109/a.2017.1", "cited_by_count": 300, "title": "Sink",
     "biblio": {"volume": "54"}, "counts_by_year": [{"year": 2020, "cited_by_count": 290}, {"year": 2023, "cited_by_count": 10}]},
    {"id": "https://openalex.org/WB", "doi": "https://doi.org/10.1109/a.2017.2", "cited_by_count": 500, "title": "Real",
     "biblio": {"volume": "54"}, "counts_by_year": [{"year": 2019, "cited_by_count": 200}, {"year": 2024, "cited_by_count": 300}]},
    {"id": "https://openalex.org/WC", "doi": "https://doi.org/10.1109/a.2017.3", "cited_by_count": 100},
    {"id": "https://openalex.org/WN", "doi": None, "cited_by_count": 90}]
TOP_2022 = [{"id": "https://openalex.org/WE", "doi": "https://doi.org/10.1109/b.2022.5", "cited_by_count": 20,
             "biblio": {"volume": "14"}, "counts_by_year": [{"year": 2024, "cited_by_count": 20}]}]
TOP_HINDAWI = [{"id": "https://openalex.org/WH%d" % i, "doi": "https://doi.org/10.1155/2017/%07d" % i, "cited_by_count": 9}
               for i in range(3)] + [{"id": "https://openalex.org/WX", "doi": "https://doi.org/10.1109/x.1", "cited_by_count": 1}]
COUNTS = [{"DOI": "10.1109/a.2017.1", "is-referenced-by-count": 9},
          {"DOI": "10.1109/a.2017.2", "is-referenced-by-count": 450},
          {"DOI": "10.1109/b.2022.5", "is-referenced-by-count": 18}]
WORKS = {
    "10.1109/a.2017.1": {"DOI": "10.1109/a.2017.1", "title": ["Sink paper on decision tools"],
                         "container-title": ["IEEE Transactions on Magnetics"], "volume": "54"},
    "10.1109/a.2017.2": {"DOI": "10.1109/a.2017.2", "title": ["Phagocytosis fundamental process immunity"]},
    "10.1000/c1": {"DOI": "10.1000/c1", "issued": {"date-parts": [[2020, 3]]}, "reference": [
        {"key": "r1", "DOI": "10.1109/a.2017.7", "first-page": "1", "journal-title": "IEEE Trans. Magn.", "volume": "54"}] + FILL},
    "10.1000/c2": {"DOI": "10.1000/c2", "reference": [{"key": "r1", "DOI": "10.1109/a.2017.1"}]},
    "10.1000/c3": {"DOI": "10.1000/c3", "reference": [{"key": "x", "DOI": "10.1109/a.2017.2"}]}}
PLACE_W7 = {"id": "https://openalex.org/W7", "doi": "https://doi.org/10.1109/a.2017.7",
            "primary_location": {"source": {"id": "https://openalex.org/S1"}}, "biblio": {"volume": "54"}}


def fake(url):
    if url.startswith(CRL):
        return json.dumps({"message": {"items": COUNTS}}).encode()
    if url.startswith(CRW):
        msg = WORKS.get(urllib.parse.unquote(url[len(CRW):].split("?")[0]))
        return json.dumps({"message": msg}).encode() if msg else None
    if url.startswith(a1.OA + "?"):
        q = urllib.parse.unquote(url)
        if "group_by" in url and "biblio.first_page:1" in q:
            g = GROUPS_2017 if "publication_year:2017" in q else (GROUPS_2022 if "publication_year:2022" in q else [])
            return json.dumps({"group_by": g}).encode()
        if "group_by" in url:
            sids = q.split("primary_location.source.id:")[1].split("&")[0].split("|")
            return json.dumps({"group_by": [{"key": "https://openalex.org/" + s, "count": TOTALS[s]}
                                            for s in sids if s in TOTALS]}).encode()
        if "sort=" in url:
            if "source.id:S77," in q:
                return json.dumps({"results": TOP_HINDAWI}).encode()
            return json.dumps({"results": TOP_2017 if "publication_year:2017" in q else TOP_2022}).encode()
        if "cites:WA" in q:
            return json.dumps({"results": [{"id": "https://openalex.org/WC1", "doi": "https://doi.org/10.1000/c1"},
                                           {"id": "https://openalex.org/WC2", "doi": "https://doi.org/10.1000/c2"}]}).encode()
        if "cites:WB" in q:
            return json.dumps({"results": [{"id": "https://openalex.org/WC3", "doi": "https://doi.org/10.1000/c3"}]}).encode()
        if "referenced_works" in q:
            return json.dumps({"results": [{"id": "https://openalex.org/WC1", "doi": "https://doi.org/10.1000/c1",
                                            "referenced_works": ["https://openalex.org/WA", "https://openalex.org/W7"]}]}).encode()
        if "primary_location,biblio" in q:
            return json.dumps({"results": [PLACE_W7]}).encode()
    return None


def row(doi, oa, cr, to=None):
    return {"doi": doi, "oa_id": "https://openalex.org/" + doi, "oa": oa, "cr": cr, "e": oa1.excess(oa, cr), "to_2021": to}


def jy(sink):
    j = {"source": "S9", "year": 2017, "status": "ok", "prefix": "10.1109"}
    j["judge"] = {"rows": 25, "sink": row("s", 300, 9, 0.95) if sink else None, "control": row("c", 500, 450, 0.5),
                  "over": 1 if sink else 0, "sink_rank": 2 if sink else None}
    return j


class TestParsing(unittest.TestCase):
    def test_urls(self):
        g = urllib.parse.unquote(p.groups_url(2018))
        self.assertIn("publication_year:2018,type:article,primary_location.source.type:journal,biblio.first_page:1,"
                      "primary_location.source.host_organization:!P4310319869&", g)
        self.assertIn("group_by=primary_location.source.id", g)
        s = urllib.parse.unquote(p.totals_url(2018, ["S1", "S2"]))
        self.assertIn("publication_year:2018,type:article,primary_location.source.id:S1|S2&", s)
        self.assertIn("group_by=primary_location.source.id", s)
        t = urllib.parse.unquote(p.top_url("S1", 2019))
        self.assertIn("sort=cited_by_count:desc", t)
        self.assertIn("per-page=25", t)
        self.assertIn("title,biblio", t)

    def test_prefix_of(self):
        self.assertEqual(p.prefix_of(["10.1109/a", "10.1117/b", "10.1109/c"]), "10.1109")
        self.assertEqual(p.prefix_of(["10.1117/b", "10.1109/c"]), "10.1109")
        self.assertEqual(p.prefix_of([]), "")

    def test_journal_years(self):
        jys, info = p.journal_years(fake, 2017)
        self.assertEqual([j["source"] for j in jys], ["S1"])
        self.assertAlmostEqual(jys[0]["page1_share"], 150 / 160)
        self.assertEqual((info["groups"], info["eligible_groups"], info["no_total"], info["low_share"], info["candidates"]),
                         (4, 3, 1, 1, 1))
        self.assertEqual((info["calls"], info["failed_calls"]), (2, 0))
        with mock.patch.object(p, "SOURCE_BATCH", 2):
            self.assertEqual(p.journal_years(fake, 2017)[1]["calls"], 3)
        jys, info = p.journal_years(lambda u: None, 2017)
        self.assertEqual((jys, info["failed_calls"]), ([], 1))

    def test_examine(self):
        j = {"source": "S1", "year": 2017}
        self.assertEqual(p.examine(fake, j), 0)
        self.assertEqual([r["doi"] for r in j["top"]], ["10.1109/a.2017.1", "10.1109/a.2017.2"])
        self.assertEqual(j["top"][0]["volume"], "54")
        self.assertEqual(j["judge"]["sink"]["doi"], "10.1109/a.2017.1")
        self.assertEqual(j["judge"]["control"]["doi"], "10.1109/a.2017.2")
        self.assertEqual(j["prefix"], "10.1109")
        h = {"source": "S77", "year": 2017}
        self.assertEqual(p.examine(fake, h), 0)
        self.assertEqual(h["status"], "hindawi")
        f = {"source": "S1", "year": 2017}
        self.assertEqual(p.examine(lambda u: None, f), 1)
        self.assertEqual(f["status"], "openalex_failed")


class TestCiters(unittest.TestCase):
    def test_is_sibling(self):
        works = {"10.1109/s": ("W1", "S1", "54"), "10.1109/o": ("W2", "S2", "54"), "10.1109/v": ("W3", "S1", "55")}
        self.assertTrue(p.is_sibling({"DOI": "10.1109/S", "first-page": "1"}, "S1", "54", NAMES, works))
        self.assertFalse(p.is_sibling({"DOI": "10.1109/o"}, "S1", "54", NAMES, works))  # another journal
        self.assertFalse(p.is_sibling({"DOI": "10.1109/v"}, "S1", "54", NAMES, works))  # another volume
        self.assertFalse(p.is_sibling({"DOI": "10.1109/unknown"}, "S1", "54", NAMES, works))
        self.assertTrue(p.is_sibling({"journal-title": "IEEE Trans Magn", "volume": "54"}, "S1", "54", NAMES, works))
        self.assertFalse(p.is_sibling({"journal-title": "IEEE Trans Magn", "volume": "55"}, "S1", "54", NAMES, works))
        self.assertFalse(p.is_sibling({"journal-title": "Opt Eng", "volume": "54"}, "S1", "54", NAMES, works))
        self.assertFalse(p.is_sibling({"DOI": "10.1109/s"}, "S1", "", NAMES, works))  # no target volume

    def test_label_citer(self):
        t, w = "10.1109/a.2017.1", ["paper", "decision", "tools"]
        self.assertEqual(p.label_citer(None, t, w), ("not_in_crossref", []))
        self.assertEqual(p.label_citer(WORKS["10.1000/c2"], t, w)[0], "genuine")
        by_title = {"reference": [{"key": "a", "article-title": "A decision support paper"}]}
        self.assertEqual(p.label_citer(by_title, t, w)[0], "genuine")
        label, p1 = p.label_citer(WORKS["10.1000/c1"], t, w)
        self.assertEqual((label, [r["key"] for r in p1]), ("candidate", ["r1"]))
        self.assertEqual(p.label_citer({"reference": FILL}, t, w)[0], "unsupported")
        self.assertEqual(p.label_citer({"reference": FILL[:4]}, t, w)[0], "too_few_references")

    def test_oa_places(self):
        got, calls, failed = p.oa_places(fake, ["10.1109/a.2017.7"])
        self.assertEqual(got, {"10.1109/a.2017.7": ("https://openalex.org/W7", "S1", "54")})
        self.assertEqual((calls, failed), (1, 0))
        self.assertEqual(p.oa_places(fake, []), ({}, 0, 0))
        self.assertEqual(p.oa_places(lambda u: None, ["x"])[2], 1)

    def test_candidate_without_sibling(self):
        msg = {"reference": [{"key": "q", "DOI": "10.1109/other", "first-page": "1"}] + FILL}
        client = a1.Client(lambda u: json.dumps({"message": msg}).encode() if u.startswith(CRW) else None, pause=0)

        def f(url):
            if "cites" in urllib.parse.unquote(url):
                return json.dumps({"results": [{"id": "https://openalex.org/WQ", "doi": "https://doi.org/10.1000/q"}]}).encode()
            return json.dumps({"results": []}).encode()
        r = {"doi": "10.1109/a.2017.1", "oa_id": "https://openalex.org/WA", "volume": "54"}
        reads, info = p.read_citers(client, f, r, [], NAMES, "S1", 1, "sink")
        self.assertEqual([x["label"] for x in reads], ["unsupported"])
        self.assertEqual(info["lookup_calls"], 1)


class TestScoring(unittest.TestCase):
    def test_h1(self):
        v, d = p.score_h1([jy(i < 8) for i in range(30)])
        self.assertEqual((v, d["with_sink"], d["journal_years"]), ("supported", 8, 30))
        self.assertEqual(p.score_h1([jy(i < 7) for i in range(30)])[0], "not supported")
        self.assertEqual(p.score_h1([jy(True)] * 29)[0], "untestable")

    def test_describe(self):
        d = p.describe([jy(True), jy(False)])
        self.assertEqual(d["by_year"]["2017"]["with_sink"], 1)
        self.assertEqual(d["by_prefix_old"], {"10.1109": {"journal_years": 2, "with_sink": 1, "phantom_citations": 291}})


class TestRun(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(p, "MIN_ROWS", 1):
            res = p.run(fake, tmp)
            with open(os.path.join(tmp, "journal_years.jsonl"), encoding="utf-8") as fh:
                jys = [json.loads(x) for x in fh]
            with open(os.path.join(tmp, "reads.jsonl"), encoding="utf-8") as fh:
                reads = [json.loads(x) for x in fh]
            self.assertTrue(os.path.exists(os.path.join(tmp, "results.json")))
        self.assertEqual(res["pool"], {"old": 1, "new": 1})
        self.assertEqual(res["listing"]["2017"]["candidates"], 1)
        self.assertEqual(res["listing"]["2016"]["groups"], 0)
        self.assertEqual(res["status"], {"ok": 2})
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
        self.assertEqual(sib["siblings"][0]["oa_id"], "https://openalex.org/W7")
        self.assertEqual(sib["year"], 2020)
        self.assertEqual(res["descriptive"]["by_year"]["2017"]["phantom_citations"], 291)
        self.assertEqual(res["descriptive"]["top_sinks"][0]["doi"], "10.1109/a.2017.1")
        self.assertEqual(res["reads"]["targets"][0]["sink_sample"]["returned"], 2)
        self.assertEqual(res["reads"]["targets"][0]["volume"], "54")


if __name__ == "__main__":
    unittest.main()
