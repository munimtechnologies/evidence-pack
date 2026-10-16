# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Offline tests: no network.
import json
import unittest
import urllib.parse

import sink_census as sc


def cby(pairs):
    return [{"year": y, "cited_by_count": n} for y, n in pairs.items()]


# counts_by_year as OpenAlex served them on 2026-10-16
BUNNEY = {"id": "https://openalex.org/W2599766179", "publication_year": 2017, "cited_by_count": 2102,
          "counts_by_year": cby({2026: 40, 2025: 101, 2024: 139, 2023: 206, 2022: 284, 2021: 724, 2020: 570,
                                 2019: 28, 2018: 2, 2017: 3, 2016: 1, 2013: 1})}
SCIREP = {"id": "https://openalex.org/W2983201012", "publication_year": 2019, "cited_by_count": 1770,
          "counts_by_year": cby({2018: 1, 2019: 20, 2020: 566, 2021: 1136, 2022: 9, 2023: 13, 2024: 18,
                                 2025: 5, 2026: 2})}
NORMAL = {"id": "W2320839214", "publication_year": 2016,
          "counts_by_year": cby({2016: 5, 2017: 16, 2018: 29, 2019: 19, 2020: 93, 2021: 35, 2022: 27})}
RAMP = {"id": "W2318441640", "publication_year": 2015,
        "counts_by_year": cby({2013: 1, 2015: 7, 2016: 112, 2017: 176, 2018: 140, 2019: 130})}

T_BUNNEY = {"doi": "10.1016/j.physbeh.2017.03.040", "family": "Bunney", "volume": "176", "first_page": "139",
            "title": "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) "
                     "caused by high-fat diet", "crossref_count": 1191}
# Shapes copied from Crossref deposits read on 2026-10-16 (10.1002/jbio.202000318 ref e_1_2_7_23_1, and sink-check-v1)
CHOUDHARY = {"key": "e_1_2_7_23_1", "first-page": "139", "volume": "176", "author": "Choudhary D.",
             "year": "2016", "journal-title": "Physiol. Behav."}
GENUINE = {"key": "ref_11", "doi-asserted-by": "crossref", "DOI": "10.1016/J.PHYSBEH.2017.03.040",
           "author": "Bunney", "year": "2017", "volume": "176", "first-page": "139"}
DOI_ONLY = {"key": "ref28", "doi-asserted-by": "publisher", "DOI": "10.1016/j.physbeh.2017.03.040"}
ATTACHED = {"key": "B26", "doi-asserted-by": "publisher", "DOI": "10.1016/j.physbeh.2017.03.040",
            "article-title": "Update on prevalence of periodontitis in adults in the United States: NHANES 2009 - 2012",
            "volume": "86", "author": "Eke", "year": "2015", "journal-title": "J. Periodontol."}
UNSTRUCTURED = {"key": "x1", "unstructured": "Bunney PE, Zink AN, Holm AA. Physiol Behav 2017;176:139-48."}
OTHER = {"key": "y", "doi-asserted-by": "publisher", "DOI": "10.1158/0008-5472.can-08-3126"}


class Jump(unittest.TestCase):
    def test_known_sinks_flag(self):
        r, y, n = sc.jump(BUNNEY)
        self.assertEqual((y, n), (2020, 570))
        self.assertAlmostEqual(r, 38.0)
        self.assertTrue(sc.flagged(BUNNEY))
        r, y, n = sc.jump(SCIREP)
        self.assertEqual((y, n), (2020, 566))
        self.assertAlmostEqual(r, 566 / 10.5)
        self.assertTrue(sc.flagged(SCIREP))

    def test_normal_and_ramp_do_not_flag(self):
        r, y, _ = sc.jump(NORMAL)
        self.assertEqual(y, 2020)
        self.assertAlmostEqual(r, 93 / 24.0)
        self.assertFalse(sc.flagged(NORMAL))
        r, y, _ = sc.jump(RAMP)
        self.assertEqual(y, 2016)
        self.assertAlmostEqual(r, 11.2)
        self.assertFalse(sc.flagged(RAMP))  # first-year ramp needs 25, not 8

    def test_nothing_big_enough(self):
        self.assertEqual(sc.jump({"publication_year": 2018, "counts_by_year": cby({2020: 49})}), (0.0, None, 0))
        self.assertFalse(sc.flagged({"publication_year": 2018, "counts_by_year": []}))


class Coherence(unittest.TestCase):
    def test_top_share(self):
        data = {"meta": {"count": 567}, "group_by": [
            {"key": "unknown", "key_display_name": "unknown", "count": 90},
            {"key": "https://openalex.org/subfields/1312", "key_display_name": "Molecular Biology", "count": 57},
            {"key": "https://openalex.org/subfields/2737", "key_display_name": "Physiology", "count": 22}]}
        t = sc.top_share(data)
        self.assertEqual((t["subfield"], t["n"]), ("Molecular Biology", 567))
        self.assertAlmostEqual(t["share"], 57 / 567)
        self.assertIsNone(sc.top_share(None))
        self.assertIsNone(sc.top_share({"meta": {"count": 0}, "group_by": []})["share"])

    def test_is_sink(self):
        self.assertTrue(sc.is_sink(True, {"share": 0.10, "n": 567}))
        self.assertFalse(sc.is_sink(True, {"share": 0.55, "n": 360}))
        self.assertFalse(sc.is_sink(True, {"share": 0.10, "n": 49}))
        self.assertFalse(sc.is_sink(False, {"share": 0.10, "n": 567}))
        self.assertFalse(sc.is_sink(True, None))
        self.assertFalse(sc.is_sink(True, {"share": None, "n": 567}))


class Snowball(unittest.TestCase):
    def test_cocited_counts_each_citer_once_and_skips_seeds(self):
        citers = [{"referenced_works": ["https://openalex.org/W1", "https://openalex.org/W1", "W2599766179", "W2"]},
                  {"referenced_works": ["W1", "W3"]},
                  {"referenced_works": ["W1", "W2"]},
                  {"referenced_works": None}]
        cnt = sc.cocited(citers, sc.SEEDS)
        self.assertEqual(dict(cnt), {"W1": 3, "W2": 2, "W3": 1})
        self.assertEqual(sc.candidates(cnt, k=2), ["W1", "W2"])
        self.assertEqual(sc.candidates(cnt, k=1, top=2), ["W1", "W2"])


class References(unittest.TestCase):
    def test_find_and_classify(self):
        hit = sc.find_ref([OTHER, CHOUDHARY], T_BUNNEY)
        self.assertIs(hit, CHOUDHARY)
        self.assertEqual(sc.classify_ref(hit, T_BUNNEY), "other_work")
        self.assertEqual(sc.classify_ref(sc.find_ref([OTHER, GENUINE], T_BUNNEY), T_BUNNEY), "genuine")
        self.assertEqual(sc.classify_ref(sc.find_ref([DOI_ONLY], T_BUNNEY), T_BUNNEY), "doi_only")
        self.assertEqual(sc.classify_ref(sc.find_ref([ATTACHED], T_BUNNEY), T_BUNNEY), "other_work")
        self.assertIs(sc.find_ref([OTHER, UNSTRUCTURED], T_BUNNEY), UNSTRUCTURED)
        self.assertEqual(sc.classify_ref(UNSTRUCTURED, T_BUNNEY), "genuine")
        self.assertIsNone(sc.find_ref([OTHER], T_BUNNEY))
        titled = {"key": "z", "unstructured": "Orexin activation counteracts decreases in nonexercise activity "
                                              "thermogenesis caused by high-fat diet. 2017."}
        self.assertEqual(sc.classify_ref(sc.find_ref([titled], T_BUNNEY), T_BUNNEY), "genuine")

    def test_target_meta(self):
        msg = {"title": ["Orexin activation"], "author": [{"family": "Bunney"}], "volume": "176",
               "page": "139-148", "is-referenced-by-count": 1191}
        t = sc.target_meta("https://doi.org/10.1016/J.PHYSBEH.2017.03.040", msg)
        self.assertEqual((t["doi"], t["family"], t["volume"], t["first_page"], t["crossref_count"]),
                         ("10.1016/j.physbeh.2017.03.040", "Bunney", "176", "139", 1191))
        t = sc.target_meta("10.1038/x", {"article-number": "16885", "volume": "9"})
        self.assertEqual((t["first_page"], t["family"], t["crossref_count"]), ("16885", "", None))

    def test_read_citer_and_verdict(self):
        msg = lambda refs: {"reference": refs}
        reads = [sc.read_citer("a", T_BUNNEY, msg([OTHER, CHOUDHARY])),
                 sc.read_citer("b", T_BUNNEY, msg([GENUINE])),
                 sc.read_citer("c", T_BUNNEY, msg([DOI_ONLY])),
                 sc.read_citer("d", T_BUNNEY, msg([OTHER])),
                 sc.read_citer("e", T_BUNNEY, msg(None)),
                 sc.read_citer("f", T_BUNNEY, None)]
        self.assertEqual([r["status"] for r in reads], ["found", "found", "found", "target_not_in_list",
                                                        "no_reference_list", "not_in_crossref"])
        v = sc.verdict(reads)
        self.assertEqual((v["n_listed"], v["genuine"], v["verdict"]), (3, 1, "unverified"))
        self.assertEqual(v["class"], {"other_work": 1, "genuine": 1, "doi_only": 1})
        many = [sc.read_citer(str(i), T_BUNNEY, msg([CHOUDHARY])) for i in range(9)] + [reads[1]]
        self.assertEqual(sc.verdict(many)["verdict"], "confirmed")
        many = [reads[1]] * 3 + [reads[3]] * 7
        self.assertEqual(sc.verdict(many)["verdict"], "not_confirmed")

    def test_mechanism(self):
        self.assertEqual(sc.mechanism(1191, 2102)[1], "crossref_deposits")
        self.assertEqual(sc.mechanism(40, 1770)[1], "openalex_matching")
        self.assertEqual(sc.mechanism(None, 1770), (None, "unknown"))


class Calls(unittest.TestCase):
    def fake(self, total, fail_at=None):
        calls = []

        def fetch(url):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            page, per = int(q["page"][0]), int(q["per-page"][0])
            calls.append(page)
            if page == fail_at:
                return None
            n = min(total, int(q["sample"][0]))
            res = [{"id": "W%d" % i} for i in range((page - 1) * per, min(page * per, n))]
            return json.dumps({"meta": {"count": n, "cost_usd": 0.0001}, "results": res}).encode()
        return fetch, calls

    def test_sampled_pages(self):
        fetch, calls = self.fake(1000)
        b = sc.Budget(cap=10)
        works, done = sc.sampled("x", 5, 1, "id", fetch, b, per_page=2)
        self.assertEqual((len(works), done, calls), (5, True, [1, 2, 3]))
        self.assertEqual(b.calls, 3)
        self.assertAlmostEqual(b.cost, 0.0003)

    def test_sampled_small_population_and_failure(self):
        fetch, _ = self.fake(3)
        works, done = sc.sampled("x", 20, 1, "id", fetch, sc.Budget(), per_page=2)
        self.assertEqual((len(works), done), (3, True))
        fetch, _ = self.fake(1000, fail_at=2)
        b = sc.Budget()
        works, done = sc.sampled("x", 5, 1, "id", fetch, b, per_page=2)
        self.assertEqual((len(works), done, b.failed), (2, False, 1))

    def test_budget_cap(self):
        fetch, calls = self.fake(1000)
        b = sc.Budget(cap=2)
        works, done = sc.sampled("x", 10, 1, "id", fetch, b, per_page=2)
        self.assertEqual((len(works), done, b.calls, b.refused, calls), (4, False, 2, 1, [1, 2]))

    def test_get_patient_gives_up_without_sleeping_for_real(self):
        slept = []
        self.assertIsNone(sc.get_patient("http://127.0.0.1:9/never", waits=(1, 2), sleep=slept.append))
        self.assertEqual(slept, [1, 2])


if __name__ == "__main__":
    unittest.main()
