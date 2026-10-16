# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Offline tests: no network.
import json
import unittest
import urllib.parse

import sink_check_v2 as s2

BUNNEY_DOI = "10.1016/j.physbeh.2017.03.040"

# Shapes copied from deposited Crossref references read in sink-check-v1 (2026-10-16).
GENUINE_TITLE = {"key": "ref_11", "doi-asserted-by": "crossref", "first-page": "139", "DOI": BUNNEY_DOI,
                 "article-title": "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) caused by high-fat diet",
                 "volume": "176", "author": "Bunney", "year": "2017", "journal-title": "Physiol. Behav."}
GENUINE_AUTHOR_ONLY = {"key": "x1", "unstructured": "Bunney PE et al. Physiol Behav 2017;176:139-148."}
DOI_ONLY = {"key": "ref28/cit28", "doi-asserted-by": "publisher", "DOI": BUNNEY_DOI}
SWAP = {"key": "3694_CR42", "doi-asserted-by": "publisher", "first-page": "139", "DOI": BUNNEY_DOI, "volume": "176",
        "author": "A Wilkinson", "year": "2017",
        "unstructured": "Wilkinson A. Screening for and treating postpartum depression and psychosis. Physiol Behav. 2017;176:139-48.",
        "journal-title": "Physiol Behav"}
SWAP_NO_DOI = {"key": "ref_67", "first-page": "139", "article-title": "AACR Project GENIE: Powering Precision M",
               "volume": "176", "author": "Dakkak", "year": "2017", "journal-title": "Physiol. Behav."}
ATTACHED = {"key": "B26", "doi-asserted-by": "publisher", "first-page": "611", "DOI": BUNNEY_DOI,
            "article-title": "Update on prevalence of periodontitis in adults in the United States: NHANES 2009 - 2012",
            "volume": "86", "author": "Eke", "year": "2015", "journal-title": "J. Periodontol."}


class Classify(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(s2.classify_ref(GENUINE_TITLE), "genuine")
        self.assertEqual(s2.classify_ref(GENUINE_AUTHOR_ONLY), "genuine")
        self.assertEqual(s2.classify_ref(DOI_ONLY), "doi_only")
        self.assertEqual(s2.classify_ref(SWAP), "other_work")
        self.assertEqual(s2.classify_ref(SWAP_NO_DOI), "other_work")
        self.assertEqual(s2.classify_ref(ATTACHED), "other_work")

    def test_subtypes(self):
        self.assertEqual(s2.subtype(SWAP), "journal_swap")
        self.assertEqual(s2.subtype(SWAP_NO_DOI), "journal_swap")
        self.assertEqual(s2.subtype(ATTACHED), "doi_attached")
        self.assertEqual(s2.subtype({"key": "z", "unstructured": "Smith 2001"}), "other")


class Records(unittest.TestCase):
    def msg(self, refs, title="Mechanisms of resistance to PD-1 blockade"):
        return {"title": [title], "issued": {"date-parts": [[2021, 3]]}, "reference": refs}

    def test_ref_record_found(self):
        rec = s2.ref_record("10.1/a", self.msg([{"key": "a", "DOI": "10.1/zzz"}, ATTACHED]))
        self.assertEqual(rec["status"], "found")
        self.assertEqual((rec["class"], rec["subtype"], rec["asserted_by"]), ("other_work", "doi_attached", "publisher"))
        self.assertEqual(rec["crossref_year"], 2021)
        self.assertFalse(rec["on_topic_crossref"])

    def test_ref_record_other_statuses(self):
        self.assertEqual(s2.ref_record("10.1/a", None)["status"], "not_in_crossref")
        self.assertEqual(s2.ref_record("10.1/a", self.msg(None))["status"], "no_reference_list")
        self.assertEqual(s2.ref_record("10.1/a", self.msg([{"key": "a", "DOI": "10.1/zzz"}]))["status"],
                         "target_not_in_list")
        rec = s2.ref_record("10.1/a", self.msg([GENUINE_TITLE], title="Diet-induced obesity in mice"))
        self.assertEqual((rec["class"], rec["subtype"]), ("genuine", ""))
        self.assertTrue(rec["on_topic_crossref"])

    def test_summarise(self):
        recs = [s2.ref_record("d%d" % i, self.msg([r])) for i, r in
                enumerate([GENUINE_TITLE, DOI_ONLY, SWAP, SWAP_NO_DOI, ATTACHED])]
        recs.append(s2.ref_record("dx", None))
        s = s2.summarise_refs(recs)
        self.assertEqual(s["sampled"], 6)
        self.assertEqual(s["found"], 5)
        self.assertEqual(s["class"], {"genuine": 1, "doi_only": 1, "other_work": 3})
        self.assertEqual(s["subtype"], {"journal_swap": 2, "doi_attached": 1, "other": 0})
        g = s["genuine_share_readable"]
        self.assertEqual((g["n"], g["k"]), (4, 1))
        self.assertAlmostEqual(g["share"], 0.25)
        for r, y in zip(recs, (2017, 2017, 2020, 2020, 2020, 2020)):
            r["year"] = y
        self.assertEqual(s2.genuine_by_year(recs), {"2017": {"n": 1, "genuine": 1}, "2020": {"n": 3, "genuine": 0}})


class Parsers(unittest.TestCase):
    def test_parse_oc(self):
        raw = json.dumps([
            {"oci": "1-2", "citing": "omid:br/06013589204 doi:10.1016/J.NPEP.2026.102587", "cited": "omid:br/1"},
            {"oci": "3-2", "citing": "omid:br/06014036551 doi:10.1038/s41598-025-20283-4 pmid:1", "cited": "x"},
            {"oci": "4-2", "citing": "omid:br/0601 pmid:2", "cited": "x"},
            {"oci": "5-2", "citing": "omid:br/06013589204 doi:10.1016/j.npep.2026.102587", "cited": "x"},
        ]).encode()
        self.assertEqual(s2.parse_oc(raw), ["10.1016/j.npep.2026.102587", "10.1038/s41598-025-20283-4"])
        self.assertEqual(s2.parse_oc(None), [])

    def test_parse_idconv(self):
        raw = json.dumps({"status": "ok", "records": [
            {"doi": "10.1016/J.PHYSBEH.2017.03.040", "pmcid": "PMC5510739", "pmid": 28363838},
            {"doi": "10.1/none", "status": "error"}]}).encode()
        self.assertEqual(s2.parse_idconv(raw), {"10.1016/j.physbeh.2017.03.040": "5510739"})
        self.assertEqual(s2.parse_idconv(None), {})


class Paging(unittest.TestCase):
    def pages(self, n_total, per_page, fail_at=None):
        calls = []

        def fetch(url):
            page = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["page"][0])
            calls.append(page)
            if fail_at == page:
                return None
            start = (page - 1) * per_page
            res = [{"id": "W%d" % i} for i in range(start, min(start + per_page, n_total))]
            return json.dumps({"meta": {"count": n_total}, "results": res}).encode()
        return fetch, calls

    def test_complete(self):
        fetch, calls = self.pages(5, 2)
        works, count, done = s2.citers_paged("W1", fetch=fetch, per_page=2)
        self.assertEqual((len(works), count, done), (5, 5, True))
        self.assertEqual(calls, [1, 2, 3])

    def test_incomplete(self):
        fetch, _ = self.pages(5, 2, fail_at=2)
        works, count, done = s2.citers_paged("W1", fetch=fetch, per_page=2)
        self.assertEqual((len(works), count, done), (2, 5, False))

    def test_first_page_fails(self):
        works, count, done = s2.citers_paged("W1", fetch=lambda url: None)
        self.assertEqual((works, count, done), ([], None, False))

    def test_get_patient_gives_up_without_sleeping_for_real(self):
        slept = []
        self.assertIsNone(s2.get_patient("http://127.0.0.1:9/never", waits=(1, 2), sleep=slept.append))
        self.assertEqual(slept, [1, 2])


if __name__ == "__main__":
    unittest.main()
