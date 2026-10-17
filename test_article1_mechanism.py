# Offline tests for article1_mechanism.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import article1_check as a1
import article1_mechanism as m

FPLS = {"publisher": "Frontiers", "journal": "fpls", "volume": "7", "year": 2016}
NAMES = [["frontiers", "plant", "science"], ["front", "plant", "sci"]]
TARGET = {"doi": "10.3389/fpls.2016.00001", "oa_id": "https://openalex.org/W100",
          "title": "Plant growth hormone signalling networks", "first_author": "lee"}
Z = [{"key": "z%d" % i, "DOI": "10.1/z%d" % i} for i in range(4)]


class FakeClient:
    def __init__(self, records):
        self.records, self.calls = {k.lower(): v for k, v in records.items()}, 0

    def work(self, doi):
        self.calls += 1
        return self.records.get(doi.lower())


def ounit(doi, a1_counts=(5, 100), far=None, year=2017, publisher="MDPI", confirmatory=True):
    """A unit as in article1_openalex_v2_units_oa.jsonl; far is a list of (crossref, openalex) pairs."""
    far = [(10, 10)] * 10 if far is None else far
    rows = [{"doi": doi, "cites": a1_counts[0], "oa": a1_counts[1], "oa_id": "https://openalex.org/W" + doi[-4:]}]
    rows += [{"doi": "%s-c%02d" % (doi, i), "cites": c, "oa": o, "oa_id": "https://openalex.org/C%d" % i}
             for i, (c, o) in enumerate(far)]
    return {"publisher": publisher, "journal": "x", "volume": 1, "year": year, "confirmatory": confirmatory, "rows": rows}


class TestMatching(unittest.TestCase):
    def test_tokens_and_names(self):
        self.assertEqual(m.tokens("Frontiers in Plant Science"), ["frontiers", "plant", "science"])
        msg = {"container-title": ["Frontiers in Plant Science"], "short-container-title": ["Front. Plant Sci."]}
        self.assertEqual(m.journal_names(msg), NAMES)
        self.assertEqual(m.journal_names({}), [])

    def test_same_journal(self):
        self.assertTrue(m.same_journal("Front Plant Sci", NAMES))
        self.assertTrue(m.same_journal("Frontiers in Plant Science", NAMES))
        self.assertFalse(m.same_journal("Plant Sci", NAMES))
        self.assertFalse(m.same_journal("Front Microbiol", NAMES))
        self.assertFalse(m.same_journal("", NAMES))
        self.assertFalse(m.same_journal(None, NAMES))

    def test_volume_regex(self):
        rx = m.volume_regex({"publisher": "MDPI", "journal": "s", "volume": 17, "year": 2017})
        self.assertTrue(rx.match("10.3390/s17010001"))
        self.assertFalse(rx.match("10.3390/su17010001"))
        self.assertFalse(rx.match("10.3390/s170100011"))
        self.assertFalse(rx.match("10.3390/s1701000"))
        rx = m.volume_regex(FPLS)
        self.assertTrue(rx.match("10.3389/fpls.2016.01849"))
        self.assertFalse(rx.match("10.3389/fpls.2015.00008"))
        self.assertFalse(rx.match("10.3389/fmicb.2016.00001"))

    def test_same_volume_and_page1(self):
        rx = m.volume_regex(FPLS)
        self.assertTrue(m.same_volume({"DOI": "10.3389/FPLS.2016.01849"}, FPLS, NAMES, rx))
        self.assertFalse(m.same_volume({"DOI": "10.1016/x", "journal-title": "Front Plant Sci", "volume": "7"}, FPLS, NAMES, rx))
        self.assertTrue(m.same_volume({"journal-title": "Frontiers in Plant Science", "volume": "7"}, FPLS, NAMES, rx))
        self.assertFalse(m.same_volume({"journal-title": "Frontiers in Plant Science", "volume": "6"}, FPLS, NAMES, rx))
        self.assertFalse(m.same_volume({"journal-title": "Plant Cell", "volume": "7"}, FPLS, NAMES, rx))
        self.assertTrue(m.page1({"first-page": "1"}))
        self.assertTrue(m.page1({"first-page": " 1 "}))
        self.assertTrue(m.page1({"first-page": 1}))
        self.assertFalse(m.page1({"first-page": "75"}))
        self.assertFalse(m.page1({}))

    def test_page1_refs(self):
        rx = m.volume_regex(FPLS)
        a = {"key": "a", "DOI": "10.3389/fpls.2016.00001", "first-page": "1"}
        b = {"key": "b", "DOI": "10.3389/fpls.2016.01849", "first-page": "1"}
        c = {"key": "c", "journal-title": "Frontiers in Plant Science", "volume": "7", "issue": "1930", "first-page": "1"}
        d = {"key": "d", "DOI": "10.3389/fpls.2016.00075", "first-page": "75"}
        e = {"key": "e", "DOI": "10.3389/fpls.2015.00008", "first-page": "1"}
        got = m.page1_refs({"reference": [a, b, c, d, e]}, FPLS, NAMES, rx, {"10.3389/fpls.2016.00001"})
        self.assertEqual(got, [b, c])
        self.assertEqual(m.page1_refs(None, FPLS, NAMES, rx, set()), [])

    def test_slim_and_year(self):
        self.assertEqual(m.slim({"key": "a", "DOI": "x", "volume": 7, "foo": "bar"}), {"key": "a", "DOI": "x", "volume": "7"})
        self.assertEqual(m.year_of({"issued": {"date-parts": [[2019, 3, 1]]}}), 2019)
        self.assertIsNone(m.year_of({"issued": {"date-parts": [[None]]}}))
        self.assertIsNone(m.year_of(None))
        self.assertIsNone(m.year_of({}))


class TestTargets(unittest.TestCase):
    def test_is_top(self):
        self.assertTrue(m.is_top(ounit("10.3390/a1010001")))
        self.assertFalse(m.is_top(ounit("10.3390/a1010001", far=[(10, 10)] * 9)))
        self.assertFalse(m.is_top(ounit("10.3390/a1010001", a1_counts=(5, 5))))
        self.assertFalse(m.is_top(ounit("10.3390/a1010001", a1_counts=(5, None))))

    def test_pick_targets(self):
        good = [ounit("10.3390/b1010001"), ounit("10.3390/a1010001"),
                ounit("10.3389/fpls.2017.00001", publisher="Frontiers")]
        bad = [ounit("10.3390/su8010001"), ounit("10.3390/c1010001", a1_counts=(60, 100)),
               ounit("10.3390/d1010001", year=2020), ounit("10.3390/e1010001", confirmatory=False)]
        got, pool = m.pick_targets(good + bad)
        self.assertEqual(pool, 3)
        self.assertEqual(sorted(u["rows"][0]["doi"] for u in got), sorted(u["rows"][0]["doi"] for u in good))
        two, pool = m.pick_targets(good + bad, n=2)
        self.assertEqual((len(two), len({u["rows"][0]["doi"] for u in two}), pool), (2, 2, 3))
        self.assertEqual(two, m.pick_targets(good + bad, n=2)[0])

    def test_control_of(self):
        u = ounit("10.3390/a1010001", far=[(10, 1), (30, 2), (30, 9)])
        self.assertEqual(m.control_of(u)["doi"], "10.3390/a1010001-c01")


class TestReads(unittest.TestCase):
    def test_read_target(self):
        raw = json.dumps({"results": [{"doi": "https://doi.org/10.9/c%d" % i} for i in range(3)]}).encode()
        b = {"key": "b", "DOI": "10.3389/fpls.2016.01849", "first-page": "1"}
        recs = {"10.9/c0": {"reference": [b] + Z, "issued": {"date-parts": [[2018]]}},
                "10.9/c1": {"reference": [{"key": "g", "DOI": "10.3389/fpls.2016.00001",
                                           "article-title": "Plant growth hormone signalling"}]}}
        reads, n = m.read_target(FakeClient(recs), lambda url: raw, FPLS, TARGET, NAMES, m.volume_regex(FPLS), 1)
        self.assertEqual([r["label"] for r in reads], ["unsupported", "genuine", "not_in_crossref"])
        self.assertEqual(reads[0]["page1"], [b])
        self.assertEqual((reads[0]["same_volume"], reads[0]["crossref_refs"], reads[0]["year"]), (1, 5, 2018))
        self.assertEqual(reads[0]["target_oa_id"], "https://openalex.org/W100")
        self.assertNotIn("page1", reads[1])
        self.assertIsNone(reads[2]["year"])
        self.assertEqual(n, 3)

    def test_control_citers(self):
        ctrl = {"doi": "10.3389/fpls.2016.00047", "oa_id": "https://openalex.org/W47"}
        many = json.dumps([{"citing": "omid:br/1 doi:10.9/d%d" % i} for i in range(6)]).encode()
        few = json.dumps([{"citing": "doi:10.9/d0"}]).encode()
        sample = json.dumps({"results": [{"doi": "https://doi.org/10.9/o1"}]}).encode()
        dois, src, pool = m.control_citers(lambda url: many, ctrl, 1)
        self.assertEqual((sorted(dois), src, pool), (["10.9/d%d" % i for i in range(6)], "opencitations", 6))
        self.assertEqual(m.control_citers(lambda url: many, ctrl, 1, n=2)[0], m.control_citers(lambda url: many, ctrl, 1, n=2)[0])
        fetch = lambda url: few if url.startswith(a1.OC) else sample
        self.assertEqual(m.control_citers(fetch, ctrl, 1), (["10.9/o1"], "openalex", 1))

    def test_read_control(self):
        ctrl = {"doi": "10.3389/fpls.2016.00047", "oa_id": "https://openalex.org/W47"}
        own1 = {"key": "o", "DOI": "10.3389/fpls.2016.00047", "first-page": "1"}
        own47 = {"key": "o", "DOI": "10.3389/fpls.2016.00047", "first-page": "47"}
        b = {"key": "b", "DOI": "10.3389/fpls.2016.01849", "first-page": "1"}
        cites_a1 = {"key": "g", "DOI": "10.3389/fpls.2016.00001", "article-title": "Plant growth hormone signalling"}
        recs = {"10.9/d0": {"reference": [own1]}, "10.9/d1": {"reference": [own47, b] + Z[:3]},
                "10.9/d2": {"reference": [own1, cites_a1]}, "10.9/d3": {"reference": Z[:1]}}
        oc = json.dumps([{"citing": "doi:10.9/d%d" % i} for i in range(5)]).encode()
        reads, info = m.read_control(FakeClient(recs), lambda url: oc, FPLS, ctrl, TARGET, NAMES, m.volume_regex(FPLS), 1)
        by = {r["citer"]: r for r in reads}
        self.assertEqual({k: r["status"] for k, r in by.items()},
                         {"10.9/d0": "found", "10.9/d1": "found", "10.9/d2": "cites_article1",
                          "10.9/d3": "no_matching_reference", "10.9/d4": "not_in_crossref"})
        self.assertEqual((by["10.9/d0"]["control_page1"], by["10.9/d0"]["other_page1"]), (True, 0))
        self.assertEqual((by["10.9/d1"]["control_page1"], by["10.9/d1"]["other_page1"]), (False, 1))
        self.assertEqual(by["10.9/d1"]["control_ref"]["first-page"], "47")
        self.assertEqual(by["10.9/d0"]["article1_oa_id"], "https://openalex.org/W100")
        self.assertEqual(info, {"source": "opencitations", "pool": 5, "read": 5})


class TestOpenAlex(unittest.TestCase):
    def test_oa_refs(self):
        page = json.dumps({"results": [
            {"id": "W1", "doi": "https://doi.org/10.9/A", "referenced_works": ["R1", "R2"]},
            {"id": "W2", "doi": "https://doi.org/10.9/a", "referenced_works": ["R1"]},
            {"id": "W3", "doi": "https://doi.org/10.9/b", "referenced_works": None},
            {"id": "W4", "doi": None}]}).encode()
        urls = []

        def fetch(url):
            urls.append(url)
            return page if len(urls) == 1 else None

        got, calls, failed = m.oa_refs(fetch, ["10.9/a", "10.9/b", "10.9/c"], per=2)
        self.assertEqual(got, {"10.9/a": ("W1", {"R1", "R2"}), "10.9/b": ("W3", set())})
        self.assertEqual((calls, failed), (2, 1))
        self.assertIn("referenced_works", urllib.parse.unquote_plus(urls[0]))

    def test_annotate(self):
        t = [{"label": "unsupported", "citer": "c0", "target_oa_id": "T",
              "page1": [{"DOI": "10.1/p"}, {"DOI": "10.1/q"}, {"key": "x"}]},
             {"label": "unsupported", "citer": "c9", "target_oa_id": "T", "page1": [{"DOI": "10.1/p"}]},
             {"label": "genuine", "citer": "c1"}]
        c = [{"status": "found", "citer": "c0", "article1_oa_id": "T"},
             {"status": "found", "citer": "c8", "article1_oa_id": "T"},
             {"status": "no_matching_reference", "citer": "c0"}]
        m.annotate(t, c, {"c0": ("W0", {"T", "P"})}, {"10.1/p": ("P", 5), "10.1/q": ("Q", 1)})
        self.assertEqual((t[0]["oa_found"], t[0]["oa_refs"], t[0]["oa_has_target"]), (True, 2, True))
        self.assertEqual([x.get("in_oa") for x in t[0]["page1"]], [True, False, None])
        self.assertFalse(t[1]["oa_found"])
        self.assertNotIn("in_oa", t[1]["page1"][0])
        self.assertNotIn("oa_found", t[2])
        self.assertEqual((c[0]["oa_article1"], c[1]["oa_article1"]), (True, None))
        self.assertNotIn("oa_article1", c[2])


class TestScores(unittest.TestCase):
    def test_fisher_greater(self):
        self.assertAlmostEqual(m.fisher_greater(3, 3, 0, 3), 0.05)
        self.assertAlmostEqual(m.fisher_greater(2, 3, 1, 3), 0.5)
        self.assertAlmostEqual(m.fisher_greater(0, 3, 3, 3), 1.0)
        self.assertAlmostEqual(m.fisher_greater(9, 15, 1, 15), 403104 / 155117520)

    def test_score_h1(self):
        hit, miss = {"label": "unsupported", "page1": [{}]}, {"label": "unsupported", "page1": []}
        c_hit, c_miss = {"status": "found", "other_page1": 1}, {"status": "found", "other_page1": 0}
        noise_t, noise_c = [{"label": "genuine"}], [{"status": "no_matching_reference"}]
        c = [c_hit] * 2 + [c_miss] * 18 + noise_c
        v, d = m.score_h1([hit] * 30 + [miss] * 10 + noise_t, c)
        self.assertEqual(v, "supported")
        self.assertEqual((d["unsupported"], d["with_page1"], d["share"], d["control_share"]), (40, 30, 0.75, 0.1))
        self.assertLess(d["p"], 1e-4)
        self.assertEqual(m.score_h1([hit] * 27 + [miss] * 13, c)[0], "not supported")
        self.assertEqual(m.score_h1([hit] * 30 + [miss] * 9, c)[0], "untestable")
        self.assertEqual(m.score_h1([hit] * 30 + [miss] * 10, c[:19])[0], "untestable")

    def test_score_h2(self):
        def r(p1, linked, other=0, oa=True):
            return {"status": "found", "other_page1": other, "control_page1": p1,
                    "oa_article1": linked if oa else None, "year": 2018}

        g1 = [r(True, True)] * 9 + [r(True, False)] * 6
        g0 = [r(False, True)] + [r(False, False)] * 14
        extra = [r(False, True, other=1)] * 5 + [r(False, True, oa=False)] * 5
        v, d = m.score_h2(g1 + g0 + extra)
        self.assertEqual(v, "supported")
        self.assertEqual((d["page1"], d["page1_linked"], d["other"], d["other_linked"]), (15, 9, 15, 1))
        self.assertAlmostEqual(d["p"], 403104 / 155117520)
        low = [r(True, True)] * 4 + [r(True, False)] * 11
        self.assertEqual(m.score_h2(low + g0)[0], "not supported")
        self.assertEqual(m.score_h2(g1 + g0[:14])[0], "untestable")

    def test_score_h3(self):
        def read(kept, lost, found=True):
            return {"label": "unsupported", "oa_found": found,
                    "page1": [{"in_oa": True}] * kept + [{"in_oa": False}] * lost + [{"in_oa": None}, {}]}

        v, d = m.score_h3([read(17, 3), read(5, 0, found=False), {"label": "genuine"}])
        self.assertEqual((v, d["references"], d["kept"]), ("supported", 20, 17))
        self.assertEqual(m.score_h3([read(15, 5)])[0], "not supported")
        self.assertEqual(m.score_h3([read(16, 3)])[0], "untestable")

    def test_describe(self):
        t = [{"label": "unsupported", "year": 2018, "oa_found": True, "oa_refs": 92, "crossref_refs": 90,
              "oa_has_target": True, "page1": [{"DOI": "x"}], "same_volume": 1},
             {"label": "unsupported", "year": 2023, "oa_found": False, "crossref_refs": 10, "page1": [], "same_volume": 0},
             {"label": "genuine", "year": 2019}]
        c = [{"status": "found", "other_page1": 0, "oa_article1": True, "control_page1": True, "year": 2018},
             {"status": "found", "other_page1": 0, "oa_article1": False, "control_page1": True, "year": 2023},
             {"status": "not_in_crossref", "year": None}]
        d = m.describe(t, c)
        self.assertEqual(d["target_labels"], {"unsupported": 2, "genuine": 1})
        self.assertEqual(d["control_status"], {"found": 2, "not_in_crossref": 1})
        self.assertEqual(d["unsupported_years"], {"to_2021": 1, "from_2022": 1, "unknown": 0})
        self.assertEqual((d["unsupported_in_openalex"], d["openalex_links_target"]), (1, 1))
        self.assertEqual((d["page1_refs"], d["page1_refs_with_doi"], d["unsupported_with_same_volume_ref"]), (1, 1, 1))
        self.assertEqual(d["median_openalex_minus_crossref_refs"], 2)
        self.assertEqual((d["h2_to_2021"]["page1_linked"], d["h2_to_2021"]["page1_rate"], d["h2_to_2021"]["other_rate"]),
                         (1, 1.0, None))
        self.assertEqual((d["h2_from_2022"]["page1"], d["h2_from_2022"]["page1_linked"]), (1, 0))


class TestMain(unittest.TestCase):
    def test_end_to_end(self):
        doi = "10.3389/fpls.2017.00001"
        far = [{"doi": "10.3389/fpls.2017.%05d" % n, "cites": 20, "oa": 20, "oa_id": "https://openalex.org/W%d" % n}
               for n in range(41, 51)]
        unit = {"publisher": "Frontiers", "journal": "fpls", "volume": "8", "year": 2017, "confirmatory": True,
                "rows": [{"doi": doi, "cites": 10, "oa": 200, "oa_id": "https://openalex.org/W100"}] + far}
        d = tempfile.mkdtemp()
        path = os.path.join(d, "units.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(unit) + "\n")
        recs = {doi: {"DOI": doi, "title": ["Plant growth hormone signalling networks"], "author": [{"family": "Lee"}],
                      "container-title": ["Frontiers in Plant Science"], "short-container-title": ["Front. Plant Sci."],
                      "is-referenced-by-count": 10, "issued": {"date-parts": [[2017, 1]]}},
                "10.9/c0": {"reference": [{"key": "b", "DOI": "10.3389/fpls.2017.00300", "first-page": "1"}] + Z,
                            "issued": {"date-parts": [[2019]]}}}
        for i in range(5):
            recs["10.9/d%d" % i] = {"reference": [{"key": "o", "DOI": "10.3389/fpls.2017.00041", "first-page": "1"}],
                                    "issued": {"date-parts": [[2018]]}}
        refs = [{"id": "https://openalex.org/Wc0", "doi": "https://doi.org/10.9/c0",
                 "referenced_works": ["https://openalex.org/W100", "https://openalex.org/W300"]}]
        refs += [{"id": "https://openalex.org/Wd%d" % i, "doi": "https://doi.org/10.9/d%d" % i,
                  "referenced_works": ["https://openalex.org/W100"] if i < 2 else []} for i in range(5)]

        def fetch(url):
            u = urllib.parse.unquote_plus(url)
            if url.startswith(a1.OC):
                return json.dumps([{"citing": "doi:10.9/d%d" % i} for i in range(5)]).encode()
            if "cites:" in u:
                return json.dumps({"results": [{"doi": "https://doi.org/10.9/c0"}]}).encode()
            if "referenced_works" in u:
                return json.dumps({"results": refs}).encode()
            if "cited_by_count" in u:
                return json.dumps({"results": [{"id": "https://openalex.org/W300", "doi": "https://doi.org/10.3389/fpls.2017.00300",
                                                "cited_by_count": 3}]}).encode()
            return None

        out = os.path.join(d, "out")
        with mock.patch.object(a1, "get_patient", fetch), mock.patch.object(a1, "Client", lambda: FakeClient(recs)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            m.main(["--units", path, "--out-dir", out])
        with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
            res = json.load(f)
        with open(os.path.join(out, "reads.jsonl"), encoding="utf-8") as f:
            reads = [json.loads(line) for line in f]
        self.assertEqual(res["eligible_units"], 1)
        self.assertEqual(res["targets"][0]["control"], "10.3389/fpls.2017.00041")
        self.assertEqual((res["H1"], res["H2"], res["H3"]), ("untestable", "untestable", "untestable"))
        self.assertEqual((res["H2_detail"]["page1"], res["H2_detail"]["page1_linked"]), (5, 2))
        self.assertEqual(res["descriptive"]["openalex_links_target"], 1)
        self.assertEqual(len(reads), 6)
        self.assertEqual(reads[0]["label"], "unsupported")
        self.assertTrue(reads[0]["page1"][0]["in_oa"])


if __name__ == "__main__":
    unittest.main()
