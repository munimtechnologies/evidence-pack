# Offline tests for openalex_article1.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import json
import os
import tempfile
import unittest

import openalex_article1 as oa


class FakeClient:
    def __init__(self, records):
        self.records, self.calls = {k.lower(): v for k, v in records.items()}, 0

    def work(self, doi):
        self.calls += 1
        return self.records.get(doi.lower())


def row(doi, cites, o=None, title="Gut bacteria adipose tissue liver", family="smith"):
    return {"doi": doi, "cites": cites, "oa": o, "oa_id": "https://openalex.org/W" + doi[-3:] if o is not None else "",
            "title": title, "first_author": family}


def unit(a1_cr, a1_oa, far, year=2018, publisher="MDPI", confirmatory=True, doi="10.3390/x1010001"):
    """far is a list of (crossref, openalex) pairs."""
    return {"publisher": publisher, "journal": "x", "volume": 1, "year": year, "confirmatory": confirmatory,
            "article1": row(doi, a1_cr, a1_oa),
            "far": [row("10.3390/x10100%02d" % (41 + i), c, o) for i, (c, o) in enumerate(far)]}


class TestBasics(unittest.TestCase):
    def test_norm_doi(self):
        self.assertEqual(oa.norm_doi("https://doi.org/10.3390/IJMS17010001"), "10.3390/ijms17010001")
        self.assertEqual(oa.norm_doi("http://dx.doi.org/10.1/A"), "10.1/a")
        self.assertEqual(oa.norm_doi(None), "")

    def test_excess(self):
        self.assertAlmostEqual(oa.excess(9, 4), 2.0)
        self.assertAlmostEqual(oa.excess(0, 0), 1.0)

    def test_load_units(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "u.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"a": 1}) + "\n\n" + json.dumps({"a": 2}) + "\n")
        self.assertEqual(oa.load_units(p), [{"a": 1}, {"a": 2}])


class TestOpenAlex(unittest.TestCase):
    def test_openalex_works(self):
        page = json.dumps({"results": [
            {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.3390/A", "cited_by_count": 5},
            {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.3390/a", "cited_by_count": 9},
            {"id": "https://openalex.org/W3", "doi": "https://doi.org/10.3390/b", "cited_by_count": 3},
            {"id": "https://openalex.org/W4", "doi": None, "cited_by_count": 99}]}).encode()
        urls = []

        def fetch(url):
            urls.append(url)
            return page if len(urls) == 1 else None

        got, calls, failed = oa.openalex_works(fetch, ["10.3390/a", "10.3390/b", "10.3390/c"], per=2)
        self.assertEqual(got, {"10.3390/a": ("https://openalex.org/W2", 9), "10.3390/b": ("https://openalex.org/W3", 3)})
        self.assertEqual((calls, failed), (2, 1))
        self.assertIn("filter=doi%3A10.3390%2Fa%7C10.3390%2Fb", urls[0])

    def test_attach(self):
        u = {"article1": {"doi": "10.3390/A"}, "far": [{"doi": "10.3390/b"}, {"doi": "10.3390/c"}]}
        oa.attach([u], {"10.3390/a": ("W1", 4), "10.3390/b": ("W2", 0)})
        self.assertEqual((u["article1"]["oa"], u["article1"]["oa_id"]), (4, "W1"))
        self.assertEqual(u["far"][0]["oa"], 0)
        self.assertEqual((u["far"][1]["oa"], u["far"][1]["oa_id"]), (None, ""))

    def test_sample_citers(self):
        raw = json.dumps({"results": [{"id": "W9", "doi": "https://doi.org/10.9/C1"}, {"id": "W8", "doi": None},
                                      {"id": "W7", "doi": "https://doi.org/10.9/c1"}]}).encode()
        urls = []

        def fetch(url):
            urls.append(url)
            return raw

        dois, n = oa.sample_citers(fetch, "https://openalex.org/W123", 5, n=40)
        self.assertEqual(dois, ["10.9/c1"])
        self.assertEqual(n, 3)
        self.assertIn("filter=cites%3AW123", urls[0])
        self.assertIn("sample=40", urls[0])
        self.assertIn("seed=5", urls[0])
        self.assertEqual(oa.sample_citers(lambda url: None, "W1", 1), ([], 0))
        self.assertEqual(oa.sample_citers(lambda url: b"[1]", "W1", 1), ([], 0))


class TestScores(unittest.TestCase):
    def test_eligible(self):
        far10 = [(10, 10)] * 10
        good = unit(5, 50, far10)
        self.assertEqual(oa.eligible([good], oa.OLD), [good])
        self.assertEqual(oa.eligible([good], oa.NEW), [])
        self.assertEqual(oa.eligible([unit(5, 50, far10, confirmatory=False)], oa.OLD), [])
        self.assertEqual(oa.eligible([unit(5, None, far10)], oa.OLD), [])
        self.assertEqual(oa.eligible([unit(5, 50, [(10, 10)] * 9 + [(10, None)])], oa.OLD), [])
        self.assertEqual(oa.eligible([unit(5, 50, far10, publisher="Frontiers")], oa.OLD, ("MDPI",)), [])

    def test_unit_excess(self):
        e1, ec = oa.unit_excess(unit(4, 9, [(1, 1), (0, None), (3, 7)]))
        self.assertAlmostEqual(e1, 2.0)
        self.assertEqual(ec, [1.0, 2.0])

    def test_score_excess(self):
        far = [(9, 9)] * 10  # every control has E = 1
        hot = [unit(9, 99, far) for _ in range(8)] + [unit(9, 9, far) for _ in range(2)]  # E1 = 10 in 8 units
        v, d = oa.score_excess(hot)
        self.assertEqual(v, "supported")
        self.assertEqual(d["top"], 8)
        self.assertAlmostEqual(d["expected_top"], 10 / 11)
        self.assertAlmostEqual(d["median_effect"], 10.0)
        self.assertLess(d["p"], 1e-6)
        v, d = oa.score_excess([unit(9, 9, far) for _ in range(10)])
        self.assertEqual(v, "not supported")
        self.assertEqual(d["top"], 0)  # ties do not count
        v, d = oa.score_excess(hot[:9])
        self.assertEqual(v, "untestable")

    def test_score_era(self):
        old = [unit(9, 29, [(9, 29)] * 10) for _ in range(10)]  # control E = 3
        new = [unit(9, 9, [(9, 9)] * 10, year=2022) for _ in range(10)]  # control E = 1
        v, d = oa.score_era(old, new)
        self.assertEqual(v, "supported")
        self.assertAlmostEqual(d["ratio"], 3.0)
        v, d = oa.score_era(new, new)
        self.assertEqual(v, "not supported")
        v, d = oa.score_era(old[:9], new)
        self.assertEqual(v, "untestable")


class TestReads(unittest.TestCase):
    words = ["independent", "correlations", "bacteria", "dysfunction"]

    def test_classify_citer(self):
        doi = "10.3390/x1010001"
        f = oa.classify_citer
        self.assertEqual(f(None, doi, self.words, "smith"), ("not_in_crossref", None))
        other = {"key": "a", "DOI": "10.3390/X1010001", "article-title": "Curcumin and cancer"}
        self.assertEqual(f({"reference": [other]}, doi, self.words, "smith"), ("other_work", other))
        by_title = {"key": "b", "unstructured": "Smith J. Diet-independent correlations between bacteria. 2019"}
        self.assertEqual(f({"reference": [{"key": "c", "DOI": "10.1/z"}, by_title]}, doi, self.words, "smith"),
                         ("genuine", by_title))
        five = [{"key": str(i), "DOI": "10.1/z%d" % i} for i in range(5)]
        self.assertEqual(f({"reference": five}, doi, self.words, "smith"), ("unsupported", None))
        self.assertEqual(f({"reference": five[:4]}, doi, self.words, "smith"), ("too_few_references", None))
        self.assertEqual(f({}, doi, self.words, "smith"), ("too_few_references", None))
        only = {"key": "d", "DOI": doi}
        self.assertEqual(f({"reference": [only]}, doi, self.words, "smith"), ("doi_only", only))

    def test_read_oa_citers(self):
        raw = json.dumps({"results": [{"doi": "https://doi.org/10.9/c%d" % i} for i in range(3)]}).encode()
        recs = {"10.9/c0": {"reference": [{"key": "a", "DOI": "10.3390/x1010001", "article-title": "Curcumin"}]},
                "10.9/c1": {"reference": [{"key": str(i), "DOI": "10.1/z%d" % i} for i in range(6)]}}
        target = row("10.3390/x1010001", 1, 50, title="Diet-Independent Correlations between Bacteria and Dysfunction")
        reads, info = oa.read_oa_citers(FakeClient(recs), lambda url: raw, target, 1)
        self.assertEqual([r["label"] for r in reads], ["other_work", "unsupported", "not_in_crossref"])
        self.assertEqual(reads[0]["ref"]["article-title"], "Curcumin")
        self.assertNotIn("ref", reads[1])
        self.assertEqual(info, {"returned": 3, "with_doi": 3})

    def test_share_and_h4(self):
        g, o, u, d = [{"label": "genuine"}], [{"label": "other_work"}], [{"label": "unsupported"}], [{"label": "doi_only"}]
        self.assertEqual(oa.share(g + o + u + d), {"n": 3, "genuine": 1, "share": 1 / 3})
        self.assertEqual(oa.score_h4(u * 18 + g * 2, g * 9 + o)[0], "supported")
        self.assertEqual(oa.score_h4(u * 18 + g * 2, g * 5 + u * 5)[0], "untestable (classifier failed calibration)")
        self.assertEqual(oa.score_h4(u * 5, g * 10)[0], "untestable")
        self.assertEqual(oa.score_h4(g * 15 + u * 5, g * 10)[0], "not supported")

    def test_targets_and_control(self):
        far = [(5, 9), (5, 30), (2, 30)]
        a = unit(10, 500, far, doi="10.3390/a1010001")
        b = unit(10, 200, far, doi="10.3390/b1010001")
        c = unit(10, 900, far, doi="10.3390/c1010001")
        c["article1"]["title"] = "On it"  # fewer than 3 title words
        e = unit(10, 300, far, doi="10.3390/e1010001")
        f = unit(10, 100, far, doi="10.3390/f1010001")
        got = [u["article1"]["doi"] for u in oa.h4_targets([f, b, c, a, e])]
        self.assertEqual(got, ["10.3390/a1010001", "10.3390/e1010001", "10.3390/b1010001"])
        ctrl = oa.h4_control(a)
        self.assertEqual((ctrl["oa"], ctrl["doi"]), (30, "10.3390/x1010042"))
        self.assertIsNone(oa.h4_control(unit(1, 1, [(1, None)])))

    def test_table_row(self):
        r = oa.table_row(unit(4, 9, [(1, 1)] * 3))
        self.assertAlmostEqual(r["article1_excess"], 2.0)
        self.assertEqual((r["n_far_oa"], r["far_median_excess"], r["top"]), (3, 1.0, True))
        r = oa.table_row(unit(4, None, [(1, 1)]))
        self.assertEqual((r["article1_excess"], r["n_far_oa"], r["top"]), (None, 0, False))


if __name__ == "__main__":
    unittest.main()
