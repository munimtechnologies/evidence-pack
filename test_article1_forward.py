# Offline tests for article1_forward.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import contextlib
import io
import json
import os
import tempfile
import unittest

import article1_check as a1
import article1_forward as f

W1 = {"DOI": "10.1000/W1", "issued": {"date-parts": [[2020, 5]]}, "reference": [
    {"key": "a", "DOI": "10.3390/ijms18012345", "first-page": "1", "volume": "18", "journal-title": "Int J Mol Sci"},
    {"key": "b", "DOI": "10.3390/ijms18010100", "first-page": "100"},
    {"key": "c", "DOI": "10.3389/fpls.2016.00075", "first-page": "75"},
    {"key": "d", "DOI": "10.1016/j.x.2019.01.001", "first-page": "1"}]}
W2 = {"DOI": "10.1000/w2", "issued": {"date-parts": [[2021]]}, "reference": [
    {"key": "a", "DOI": "10.3390/ijms18010200", "first-page": "200"}]}
W3 = {"DOI": "10.1000/w3", "issued": {"date-parts": [[2024]]}, "reference": [
    {"key": "a", "DOI": "10.3390/ijms18015000", "first-page": "1"}]}

OA_WORKS = [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/w1",
             "referenced_works": ["https://openalex.org/WA1", "https://openalex.org/X"]},
            {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1000/w2", "referenced_works": ["https://openalex.org/X"]},
            {"id": "https://openalex.org/W3", "doi": "https://doi.org/10.1000/w3", "referenced_works": ["https://openalex.org/X"]}]
OA_FIRSTS = [{"id": "https://openalex.org/WA1", "doi": "https://doi.org/10.3390/ijms18010001", "cited_by_count": 500},
             {"id": "https://openalex.org/WF1", "doi": "https://doi.org/10.3389/fpls.2016.00001", "cited_by_count": 900}]


def fake(url):
    if url.startswith("https://api.crossref.org/works?"):
        items = [W1, W2] if "2019-01-01" in url else [W3]
        return json.dumps({"status": "ok", "message": {"items": items}}).encode()
    if url.startswith(a1.OA + "?") and "referenced_works" in url:
        return json.dumps({"results": OA_WORKS}).encode()
    if url.startswith(a1.OA + "?"):
        return json.dumps({"results": OA_FIRSTS}).encode()
    return None


def pair(era, exposed, oa):
    return {"era": era, "volume": "ijms 18", "article1": "10.3390/ijms18010001",
            "page1": [{"key": "a"}] if exposed else [], "oa": oa}


class TestVolumes(unittest.TestCase):
    def test_volume_of(self):
        self.assertEqual(f.volume_of("10.3390/ijms18010005"), ("ijms 18", "10.3390/ijms18010001"))
        self.assertEqual(f.volume_of(" 10.3390/IJMS18012345 "), ("ijms 18", "10.3390/ijms18010001"))
        self.assertEqual(f.volume_of("10.3390/s16010001"), ("s 16", "10.3390/s16010001"))
        self.assertIsNone(f.volume_of("10.3390/ijms22010005"))  # 2021 volume
        self.assertIsNone(f.volume_of("10.3390/foo16010001"))  # journal not covered
        self.assertEqual(f.volume_of("10.3389/fpls.2016.01849"), ("fpls 2016", "10.3389/fpls.2016.00001"))
        self.assertIsNone(f.volume_of("10.3389/fpls.2021.660460"))
        self.assertIsNone(f.volume_of("10.3389/fpls.2015.00008"))
        self.assertIsNone(f.volume_of(""))
        self.assertIsNone(f.volume_of(None))

    def test_pairs_of(self):
        got, dropped = f.pairs_of(W1)
        self.assertEqual(sorted(got), ["fpls 2016", "ijms 18"])
        self.assertEqual(dropped, 0)
        self.assertEqual(got["ijms 18"]["refs"], 2)
        self.assertEqual([x["DOI"] for x in got["ijms 18"]["page1"]], ["10.3390/ijms18012345"])
        self.assertEqual(got["ijms 18"]["article1"], "10.3390/ijms18010001")
        self.assertEqual(got["fpls 2016"]["page1"], [])

    def test_blind_page1_drops_unexposed_only(self):
        w = {"reference": [{"key": "a", "DOI": "10.3390/ijms18010200", "first-page": "200"},
                           {"key": "b", "DOI": "10.3389/fpls.2016.00010", "first-page": "1"},
                           {"key": "c", "journal-title": "Some J", "volume": "3", "first-page": "1"}]}
        got, dropped = f.pairs_of(w)
        self.assertEqual(sorted(got), ["fpls 2016"])
        self.assertEqual(dropped, 1)

    def test_citing_article1_drops_the_pair(self):
        w = {"reference": [{"key": "a", "DOI": "10.3389/fneur.2017.00001", "first-page": "1"},
                           {"key": "b", "DOI": "10.3389/fneur.2017.00057", "first-page": "1"}]}
        self.assertEqual(f.pairs_of(w), ({}, 0))
        self.assertEqual(f.pairs_of({}), ({}, 0))


class TestSampling(unittest.TestCase):
    def test_sample_url(self):
        u = f.sample_url("old")
        self.assertTrue(u.startswith("https://api.crossref.org/works?sample=100&"))
        self.assertIn("2019-01-01", u)
        self.assertIn("2021-12-31", u)
        self.assertIn("select=DOI%2Cissued%2Creference", u)
        self.assertNotIn("select", f.sample_url("new", select=False))
        self.assertIn("2023-01-01", f.sample_url("new"))

    def test_parse_sample(self):
        self.assertEqual(f.parse_sample(b'{"message": {"items": [{"DOI": "x"}]}}'), [{"DOI": "x"}])
        self.assertEqual(f.parse_sample(b'{"message": {}}'), [])
        self.assertIsNone(f.parse_sample(None))
        self.assertIsNone(f.parse_sample(b"not json"))
        self.assertIsNone(f.parse_sample(b'{"message": ["error"]}'))

    def test_collect_stops_when_enough(self):
        pairs, info, seen = f.collect(fake, "old", max_calls=3, enough=1)
        self.assertEqual(info["calls"], 1)
        self.assertEqual(info["works"], 2)
        self.assertEqual(info["citers"], 2)
        self.assertEqual(info["pairs"], 3)
        self.assertEqual(info["exposed"], 1)
        self.assertEqual(seen, ["10.1000/w1", "10.1000/w2"])
        self.assertEqual([(p["citer"], p["volume"], p["year"]) for p in pairs],
                         [("10.1000/w1", "fpls 2016", 2020), ("10.1000/w1", "ijms 18", 2020), ("10.1000/w2", "ijms 18", 2021)])

    def test_collect_counts_duplicates(self):
        pairs, info, seen = f.collect(fake, "old", max_calls=2, enough=5)
        self.assertEqual(info["calls"], 2)
        self.assertEqual(info["works"], 2)
        self.assertEqual(info["duplicates"], 2)
        self.assertEqual(info["pairs"], 3)

    def test_collect_gives_up_after_failures(self):
        calls = []

        def broken(url):
            calls.append(url)
            return None

        pairs, info, seen = f.collect(broken, "new", max_calls=150, enough=5)
        self.assertEqual(info["calls"], f.MAX_FAILS)
        self.assertEqual(info["failed_calls"], f.MAX_FAILS)
        self.assertEqual(len(calls), 2 * f.MAX_FAILS)  # each call retried once without select
        self.assertEqual(pairs, [])

    def test_choose(self):
        ps = [dict(pair("old", False, None), citer="c%03d" % i) for i in range(400)] + [dict(pair("old", True, None), citer="e")]
        got = f.choose(ps, 1)
        self.assertEqual(len(got), 1 + f.N_UNEXPOSED)
        self.assertEqual(got[0]["citer"], "e")
        self.assertEqual(got, f.choose(list(reversed(ps)), 1))


class TestScoring(unittest.TestCase):
    def test_h1(self):
        old = [pair("old", True, i < 10) for i in range(20)] + [pair("old", False, i < 1) for i in range(60)]
        v, d = f.score_h1(old)
        self.assertEqual(v, "supported")
        self.assertEqual((d["exposed"], d["exposed_linked"], d["unexposed"], d["unexposed_linked"]), (20, 10, 60, 1))
        self.assertLess(d["p"], 0.01)
        v, d = f.score_h1([pair("old", True, i < 4) for i in range(20)] + [pair("old", False, False)] * 60)
        self.assertEqual(v, "not supported")  # 0.20 < 0.30
        v, d = f.score_h1(old[:14] + old[20:])
        self.assertEqual(v, "untestable")
        v, d = f.score_h1(old + [pair("old", True, None)] * 5)
        self.assertEqual(d["exposed"], 20)  # pairs without an OpenAlex answer are left out

    def test_h2(self):
        old = [pair("old", True, i < 10) for i in range(20)]
        v, d = f.score_h2(old, [pair("new", True, False)] * 20)
        self.assertEqual(v, "supported")
        self.assertAlmostEqual(d["p"], 30045015 / 137846528820)
        v, d = f.score_h2(old, [pair("new", True, i < 5) for i in range(20)])
        self.assertEqual(v, "not supported")  # 0.25 > 0.10
        v, d = f.score_h2(old, [pair("new", True, False)] * 10)
        self.assertEqual(v, "untestable")
        self.assertEqual(d["new_exposed"], 10)


class TestRun(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            res = f.run(fake, tmp, max_calls=3, enough=1)
            with open(os.path.join(tmp, "pairs.jsonl"), encoding="utf-8") as fh:
                rows = [json.loads(x) for x in fh]
            with open(os.path.join(tmp, "sampled_old.txt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "10.1000/w1\n10.1000/w2\n")
            self.assertTrue(os.path.exists(os.path.join(tmp, "results.json")))
        self.assertEqual(len(rows), 4)
        self.assertEqual(res["sampling"]["old"]["exposed"], 1)
        self.assertEqual(res["sampling"]["new"]["pairs"], 1)
        self.assertEqual(res["openalex"]["citers_found"], 3)
        self.assertEqual(res["openalex"]["article1s_found"], 2)
        links = {(r["citer"], r["volume"]): r["oa"] for r in rows}
        self.assertEqual(links, {("10.1000/w1", "ijms 18"): True, ("10.1000/w1", "fpls 2016"): False,
                                 ("10.1000/w2", "ijms 18"): False, ("10.1000/w3", "ijms 18"): False})
        self.assertEqual(res["H1"], "untestable")
        self.assertEqual(res["H1_detail"]["exposed_linked"], 1)
        self.assertEqual(res["H2"], "untestable")
        self.assertEqual(res["H2_detail"]["new_rate"], 0.0)
        self.assertEqual(res["descriptive"]["old"]["by_publisher"]["Frontiers"]["unexposed"], 1)


if __name__ == "__main__":
    unittest.main()
