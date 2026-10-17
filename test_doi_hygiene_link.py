# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for doi_hygiene.py's article-1 link check. python -m unittest -v test_doi_hygiene_link"""
import contextlib
import io
import json
import os
import tempfile
import unittest

import doi_hygiene as dh

# A real pair from article1_forward_v2_pairs.jsonl: Journal of Fashion Marketing and Management (2020)
# cites Sustainability 8:540 with first page "1", and OpenAlex links it to Sustainability 8's article 1.
SIBLING = {"key": "ref038", "DOI": "10.3390/su8060540", "first-page": "1", "volume": "8", "year": "2016"}


def citer(refs, year=2020, doi="10.1108/JFMM-08-2019-0176"):
    return {"DOI": doi, "issued": {"date-parts": [[year, 3]]}, "reference": refs}


class VolumeOf(unittest.TestCase):
    def test_mdpi(self):
        self.assertEqual(dh.volume_of("10.3390/su8010001"), ("MDPI", "su", "8", True))
        self.assertEqual(dh.volume_of("https://doi.org/10.3390/SU8060540"), ("MDPI", "su", "8", False))
        self.assertEqual(dh.volume_of("10.3390/molecules23082059"), ("MDPI", "molecules", "23", False))
        self.assertEqual(dh.volume_of("10.3390/ijerph16010001"), ("MDPI", "ijerph", "16", True))

    def test_frontiers(self):
        self.assertEqual(dh.volume_of("10.3389/fpls.2017.00001"), ("Frontiers", "fpls", "2017", True))
        self.assertEqual(dh.volume_of("10.3389/fmicb.2016.02139"), ("Frontiers", "fmicb", "2016", False))

    def test_other_dois(self):
        for doi in ["10.1038/s41598-018-37186-2", "10.3390/su8", "10.3389/fpls.2017", "", None]:
            with self.subTest(doi=doi):
                self.assertIsNone(dh.volume_of(doi))


class ArticleOneLink(unittest.TestCase):
    def test_page1_sibling(self):
        r = dh.article_one_link("10.3390/su8010001", citer([SIBLING, {"DOI": "10.1108/x", "first-page": "1"}]))
        self.assertEqual(r["verdict"], "page1_sibling")
        self.assertEqual(r["page1_refs"], ["10.3390/su8060540"])
        self.assertEqual(r["citer"], "10.1108/jfmm-08-2019-0176")
        self.assertEqual(r["year"], 2020)
        self.assertEqual([f["kind"] for f in r["flags"]], ["article_one_link"])
        self.assertNotIn("2023-2025", r["flags"][0]["why"])

    def test_newer_citer_is_flagged_with_the_era_caveat(self):
        r = dh.article_one_link("10.3390/su8010001", citer([SIBLING], year=2024))
        self.assertEqual(r["verdict"], "page1_sibling")
        self.assertIn("2024", r["flags"][0]["why"])

    def test_cited_by_doi(self):
        refs = [SIBLING, {"DOI": "10.3390/SU8010001", "first-page": "1"}]
        r = dh.article_one_link("10.3390/su8010001", citer(refs))
        self.assertEqual(r["verdict"], "cited")
        self.assertEqual(r["flags"], [])

    def test_page_range_or_other_volume_is_unexplained(self):
        refs = [dict(SIBLING, **{"first-page": "540"}),
                {"DOI": "10.3390/su9122308", "first-page": "1"},  # Sustainability 9, not 8
                {"DOI": "10.3389/fmicb.2016.02139", "first-page": "1"},
                {"unstructured": "Jung, Sustainability 8, 1 (2016)", "first-page": "1"}]
        r = dh.article_one_link("10.3390/su8010001", citer(refs))
        self.assertEqual(r["verdict"], "unexplained")
        self.assertEqual(r["page1_refs"], [])
        self.assertEqual(r["flags"], [])

    def test_frontiers_same_year_is_the_same_volume(self):
        refs = [{"DOI": "10.3389/fpls.2017.00575", "first-page": "1"},
                {"DOI": "10.3389/fpls.2018.00575", "first-page": "1"}]
        r = dh.article_one_link("10.3389/fpls.2017.00001", citer(refs, 2019, "10.3389/fpls.2019.01424"))
        self.assertEqual(r["verdict"], "page1_sibling")
        self.assertEqual(r["page1_refs"], ["10.3389/fpls.2017.00575"])

    def test_not_covered(self):
        for a1 in ["10.3390/su8060540", "10.1038/s41598-018-37186-2"]:
            with self.subTest(article1=a1):
                r = dh.article_one_link(a1, citer([SIBLING]))
                self.assertEqual(r["verdict"], "not_covered")
                self.assertEqual(r["flags"], [])

    def test_missing_parts(self):
        r = dh.article_one_link("10.3390/su8010001", None)
        self.assertEqual((r["verdict"], r["citer"], r["year"]), ("unexplained", "", None))
        r = dh.article_one_link("10.3390/su8010001", {"DOI": "10.1/x", "published-online": {"date-parts": [[2019]]}})
        self.assertEqual(r["year"], 2019)


class LinkCli(unittest.TestCase):
    def test_link_reads_a_crossref_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "work.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"status": "ok", "message": citer([SIBLING])}, fh)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(dh.main(["link", "10.3390/su8010001", path]), 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([r["verdict"] for r in rows], ["page1_sibling"])


if __name__ == "__main__":
    unittest.main()
