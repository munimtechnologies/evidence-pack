# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for phantom_refs (no network)."""
import unittest

import phantom_refs as pr

TITLE = "Systemic lupus erythematosus: diagnosis and clinical management"
OTHER = "Metformin for knee osteoarthritis in overweight adults"


class FakeLook:
    def __init__(self, titles=None, handles=None, hits=(), works=None):
        self.titles, self.handles, self.hits, self.works = titles or {}, handles or {}, hits, works or {}

    def title(self, doi):
        return self.titles.get(doi.lower(), {"status": "absent", "title": ""})

    def handle(self, doi):
        return self.handles.get(doi.lower(), "not-found")

    def biblio(self, query):
        return None if self.hits is None else list(self.hits)

    def work(self, doi):
        return self.works.get(doi, ("absent", None))


def found(title):
    return {"status": "found", "title": title}


class TextTests(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(pr.tokens("<i>In vivo</i> effects of Caf&eacute; on the heart"),
                         ["vivo", "effects", "cafe", "heart"])
        self.assertEqual(pr.tokens("Type 2 diabetes"), ["type", "2", "diabetes"])

    def test_containment(self):
        self.assertEqual(pr.containment(["a", "b"], ["a", "c"]), 0.5)
        self.assertEqual(pr.containment([], ["a"]), 0.0)

    def test_clean_doi(self):
        self.assertEqual(pr.clean_doi("https://doi.org/10.1000/xyz."), "10.1000/xyz")
        self.assertEqual(pr.clean_doi("doi: 10.1000/ab c"), "10.1000/abc")
        self.assertEqual(pr.clean_doi("10.1000/abc)"), "10.1000/abc")
        self.assertEqual(pr.clean_doi("10.1016/S0140-6736(19)30546-X"), "10.1016/S0140-6736(19)30546-X")

    def test_judge(self):
        self.assertEqual(pr.judge({"article-title": TITLE}, "Systemic lupus erythematosus: Diagnosis and clinical "
                                                             "management"), ("match", 1.0))
        self.assertEqual(pr.judge({"article-title": TITLE}, OTHER), ("mismatch", 0.0))
        unstructured = ("Fava A, Petri M. Systemic lupus erythematosus: diagnosis and clinical management. "
                        "J Autoimmun. 2019;96:1-13.")
        self.assertEqual(pr.judge({"unstructured": unstructured}, TITLE), ("match", 1.0))
        self.assertEqual(pr.judge({"article-title": "Systemic lupus erythematosus"}, TITLE), ("match", 1.0))
        self.assertEqual(pr.judge({"article-title": TITLE}, "Erratum"), ("short", None))
        self.assertEqual(pr.judge({"volume": "96"}, TITLE), ("untitled", None))


class SamplingTests(unittest.TestCase):
    def test_picks(self):
        self.assertEqual(pr.picks([str(i) for i in range(1, 11)], 4), ["1", "3", "6", "8"])

    def test_order(self):
        o = pr.order(240)
        self.assertEqual(sorted(o), list(range(240)))
        self.assertEqual(o, pr.order(240))
        self.assertNotEqual(o, list(range(240)))

    def test_wilson(self):
        lo, hi = pr.wilson(0, 10)
        self.assertAlmostEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)
        lo, hi = pr.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertEqual(pr.wilson(0, 0), (0.0, 0.0))


class CheckTests(unittest.TestCase):
    def test_match(self):
        rec = pr.check_ref({"DOI": "10.1/A", "article-title": TITLE}, FakeLook(titles={"10.1/a": found(TITLE)}))
        self.assertEqual((rec["status"], rec["fixed"]), ("match", ""))

    def test_fixed_after_cleaning(self):
        rec = pr.check_ref({"DOI": "10.1/a.", "article-title": TITLE}, FakeLook(titles={"10.1/a": found(TITLE)}))
        self.assertEqual((rec["status"], rec["fixed"]), ("match", "10.1/a"))

    def test_other_registration_agency(self):
        rec = pr.check_ref({"DOI": "10.5281/zenodo.1", "article-title": TITLE},
                           FakeLook(handles={"10.5281/zenodo.1": "exists"}))
        self.assertEqual(rec["status"], "other-ra")

    def test_not_found_and_error(self):
        self.assertEqual(pr.check_ref({"DOI": "10.9/none"}, FakeLook())["status"], "not-found")
        look = FakeLook(titles={"10.1/e": {"status": "error", "title": ""}})
        self.assertEqual(pr.check_ref({"DOI": "10.1/e"}, look)["status"], "error")

    def test_search(self):
        ref = {"article-title": TITLE, "author": "Fava"}
        hit = {"doi": "10.2/real", "title": TITLE}
        self.assertEqual(pr.search(ref, "10.1/wrong", FakeLook(hits=[hit]))["outcome"], "real-work-other-doi")
        self.assertEqual(pr.search(ref, "10.1/wrong", FakeLook(hits=[{"doi": "10.2/x", "title": OTHER}]))["outcome"],
                         "unresolved")
        self.assertEqual(pr.search(ref, "10.1/wrong", FakeLook(hits=[]))["outcome"], "unresolved")
        self.assertEqual(pr.search(ref, "10.1/wrong", FakeLook(hits=[{"doi": "10.1/WRONG", "title": TITLE}]))["outcome"],
                         "search-returns-cited")
        self.assertEqual(pr.search({"volume": "1"}, "x", FakeLook())["outcome"], "no-text")
        self.assertEqual(pr.search(ref, "x", FakeLook(hits=None))["outcome"], "search-error")


def sample_look():
    refs = [
        {"key": "r1", "DOI": "10.1/a", "doi-asserted-by": "publisher", "article-title": TITLE},
        {"key": "r2", "DOI": "10.1/b", "doi-asserted-by": "publisher", "article-title": TITLE},
        {"key": "r3", "DOI": "10.1/c", "doi-asserted-by": "crossref"},
        {"key": "r4", "unstructured": "Some book. 1999."},
        {"key": "r5", "DOI": "10.9/none", "doi-asserted-by": "publisher"},
    ]
    return FakeLook(titles={"10.1/a": found(TITLE), "10.1/b": found(OTHER)}, hits=[],
                    works={"10.9/ma": ("found", {"references-count": 5, "reference": refs}),
                           "10.9/empty": ("found", {"reference": []})})


class AuditTests(unittest.TestCase):
    def test_audit_ma(self):
        row, flags = pr.audit_ma("123", {"doi": "10.9/ma", "journal": "J"}, sample_look())
        self.assertEqual((row["status"], row["n_refs"], row["references_count"]), ("audited", 5, 5))
        self.assertEqual(row["counts"], {"match": 1, "mismatch": 1, "unresolved": 1, "crossref-asserted": 1,
                                         "no-doi": 1, "not-found": 1, "no-text": 1})
        self.assertEqual([f["outcome"] for f in flags], ["unresolved", "no-text"])
        self.assertEqual(flags[0]["pmid"], "123")
        self.assertEqual(flags[0]["ref"]["article-title"], TITLE)

    def test_audit_ma_skips(self):
        look = sample_look()
        self.assertEqual(pr.audit_ma("1", {}, look)[0]["status"], "no-doi")
        self.assertEqual(pr.audit_ma("2", {"doi": "10.9/gone"}, look)[0]["status"], "not-in-crossref")
        self.assertEqual(pr.audit_ma("3", {"doi": "10.9/empty"}, look)[0]["status"], "no-references")

    def test_summarise(self):
        row, flags = pr.audit_ma("123", {"doi": "10.9/ma"}, sample_look())
        rows = [row, {"pmid": "2", "status": "no-references"}, {"pmid": "3", "status": "audited", "counts": {"match": 4}}]
        s = pr.summarise(rows, flags, 240)
        self.assertEqual((s["n_processed"], s["n_audited"], s["publisher_dois_checked"]), (3, 2, 7))
        self.assertEqual((s["primary_mas_with_unresolved"], s["mas_with_any_flag"], s["unresolved_refs"]), (1, 1, 1))
        self.assertAlmostEqual(s["unresolved_per_checked"], 1 / 7)
        self.assertEqual(s["ma_status"], {"audited": 2, "no-references": 1})
        md = pr.results_md(s, {"n": 10, "count_whole": 10, "sha256": "x"})
        self.assertIn("1 / 2 = 50.0%", md)


if __name__ == "__main__":
    unittest.main()
