# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for dash_census.py (no network)."""
import json
import random
import unittest
import urllib.parse

import dash_census as dc

DASHED = "10.1038/s41572‐020‐00224‐3"
GOOD = {"10.1038/s41572-020-00224-3", "10.1186/1471-2407-12-332", "10.3322/caac.21834"}


def ref(doi, by="publisher"):
    return {"key": doi, "DOI": doi, "doi-asserted-by": by}


def item(doi, refs, publisher="Wiley", issued=(2026, 3, 5)):
    return {"DOI": doi, "publisher": publisher, "container-title": ["J Test"],
            "issued": {"date-parts": [list(issued)]}, "reference": refs}


def fake(url, timeout=60):
    if url.startswith(dc.CROSSREF + "/"):
        doi = urllib.parse.unquote(url[len(dc.CROSSREF) + 1:].split("?")[0])
        return (200, b"{}") if doi.lower() in GOOD else (404, b"")
    if url.startswith(dc.HANDLES):
        return 404, b""
    return None, b"unexpected"


class TextTests(unittest.TestCase):
    def test_dash_helpers(self):
        self.assertTrue(dc.has_dash(DASHED))
        self.assertFalse(dc.has_dash("10.1186/1471-2407-12-332"))
        self.assertTrue(dc.has_hyphen("10.1186/1471-2407-12-332"))
        self.assertTrue(dc.has_hyphen(DASHED))
        self.assertFalse(dc.has_hyphen("10.3322/caac.21834"))
        self.assertEqual(dc.normalise(DASHED), "10.1038/s41572-020-00224-3")
        self.assertEqual(dc.normalise("10.1/a–b­c"), "10.1/a-bc")
        self.assertEqual(dc.dash_codes("10.1/a–b‐c‐d"), ["U+2010", "U+2013"])

    def test_wilson(self):
        lo, hi = dc.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, delta=0.001)
        self.assertAlmostEqual(hi, 0.7634, delta=0.001)
        self.assertEqual(dc.wilson(0, 0), (None, None))
        self.assertEqual(dc.wilson(0, 10)[0], 0.0)


class RowTests(unittest.TestCase):
    def test_article_row(self):
        r = dc.article_row(item("10.9/a", [ref(DASHED), ref("10.1186/1471-2407-12-332"), ref("10.3322/caac.21834"),
                                           ref("10.1/x-y", by="crossref"), {"key": "u", "unstructured": "no doi"}]),
                           "311")
        self.assertEqual((r["references"], r["publisher_dois"], r["hyphen_dois"], r["dash_dois"]), (5, 3, 2, 1))
        self.assertEqual(r["dash_codes"], ["U+2010"])
        self.assertEqual(r["ascii_hyphen"], ["10.1186/1471-2407-12-332"])
        self.assertEqual(len(r["plain"]), 2)
        self.assertEqual(r["issued"], "2026-03-05")
        self.assertEqual(dc.article_row({"DOI": "10.9/z"}, "78")["issued"], "")

    def test_member_summary(self):
        rows = [dc.article_row(item("10.9/a", [ref(DASHED), ref("10.1186/1471-2407-12-332")]), "311"),
                dc.article_row(item("10.9/b", [ref("10.1186/1471-2407-12-332")]), "311"),
                dc.article_row(item("10.9/c", [ref("10.3322/caac.21834")]), "311")]
        s = dc.member_summary(rows)
        self.assertEqual((s["articles"], s["with_hyphen_dois"], s["affected"], s["mixed"]), (3, 2, 1, 1))
        self.assertEqual((s["hyphen_dois"], s["dash_dois"]), (3, 1))
        self.assertAlmostEqual(s["share"], 0.5)
        self.assertEqual(s["publisher"], "Wiley")
        self.assertEqual(dc.breakdown(rows, "month"), [["2026-03", 1, 2]])


class DrawTests(unittest.TestCase):
    def test_draw_dedupes_and_counts_failures(self):
        pages = [{"message": {"items": [item("10.9/A", []), item("10.9/b", [])]}},
                 {"message": {"items": [item("10.9/a", []), item("10.9/c", [])]}}]
        calls = []

        def fetch(url, timeout=60):
            calls.append(url)
            if len(calls) > len(pages):
                return 500, b""
            return 200, json.dumps(pages[len(calls) - 1]).encode()

        items, failed = dc.draw("311", 3, fetch)
        self.assertEqual([i["DOI"] for i in items], ["10.9/A", "10.9/b", "10.9/c"])
        self.assertEqual(failed, 1)
        self.assertIn("member:311", calls[0])
        self.assertIn("sample=100", calls[0])


class ResolveTests(unittest.TestCase):
    def test_resolution(self):
        look = dc.Lookup(fetch=fake)
        recs = dc.resolution([("10.9/a", DASHED), ("10.9/a", "10.1186/1471-2407-12-332"), ("10.9/a", "10.1/nope")],
                             look)
        self.assertEqual((recs[0]["raw"], recs[0]["normalised"]), ("not-found", "crossref"))
        self.assertEqual((recs[1]["raw"], recs[1]["normalised"]), ("crossref", ""))
        self.assertEqual(recs[2]["raw"], "not-found")
        n = look.calls
        look.resolve("10.1/NOPE")
        self.assertEqual(look.calls, n)

    def test_pick_is_seeded(self):
        pool = [("a", str(i)) for i in range(10)]
        self.assertEqual(dc.pick(pool, 3, random.Random(1)), dc.pick(list(reversed(pool)), 3, random.Random(1)))
        self.assertEqual(len(dc.pick(pool, 30, random.Random(1))), 10)


def downstream_fetch(url, timeout=60):
    if url.startswith(dc.OPENCITATIONS):
        body = [{"oci": "1-2", "citing": "omid:br/1 doi:10.9/c", "cited": "omid:br/2 doi:10.1/A openalex:W1"}]
        return 200, json.dumps(body).encode()
    if url.startswith(dc.OPENALEX + "/doi:"):
        return 200, json.dumps({"id": "W9", "referenced_works": ["W1", "W3"]}).encode()
    if url.startswith(dc.OPENALEX + "?"):
        flt = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["filter"][0]
        known = {"10.1/a": "W1", "10.1/x-y": "W2", "10.1/b": "W3"}
        res = [{"id": known[d], "doi": "https://doi.org/" + d}
               for d in (x.replace("https://doi.org/", "") for x in flt[len("doi:"):].split("|")) if d in known]
        return 200, json.dumps({"results": res}).encode()
    return None, b""


class DownstreamTests(unittest.TestCase):
    def test_oc_cited(self):
        self.assertEqual(dc.oc_cited("10.9/c", downstream_fetch), {"10.1/a"})
        self.assertEqual(dc.oc_cited("10.9/c", lambda u, timeout=60: (200, b"[]")), set())
        self.assertIsNone(dc.oc_cited("10.9/c", lambda u, timeout=60: (None, b"down")))

    def test_oa_ids(self):
        self.assertEqual(dc.oa_ids(["10.1/A", "10.1/b", "10.1/zz", "10.1/c,d"], downstream_fetch),
                         {"10.1/a": "W1", "10.1/b": "W3"})

    def test_citation_check(self):
        rows = {"10.9/c": {"plain": ["10.1/A", "10.1/b"]}}
        recs = dc.citation_check([("10.9/c", "10.1/x‐y")], rows, random.Random(dc.SEED), downstream_fetch)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["dashed"], ["10.1/x-y"])
        self.assertEqual(sorted(r["controls"]), ["10.1/a", "10.1/b"])
        self.assertTrue(r["oc_indexed"])
        self.assertEqual(r["oc_dashed"], [False])
        self.assertEqual(dict(zip(r["controls"], r["oc_controls"])), {"10.1/a": True, "10.1/b": False})
        self.assertTrue(r["oa_indexed"])
        self.assertEqual(r["oa_dashed"], [False])
        self.assertEqual(r["oa_controls"], [True, True])
        self.assertNotIn("oa_refs", r)


class VerdictTests(unittest.TestCase):
    def setUp(self):
        wiley = [dc.article_row(item("10.9/w%d" % i, [ref(DASHED)] if i < 6 else [ref("10.1186/1471-2407-12-332")]),
                                "311") for i in range(20)]
        other = [dc.article_row(item("10.8/e%d" % i, [ref("10.1186/1471-2407-12-332")], publisher="Elsevier BV"),
                                "78") for i in range(20)]
        self.rows = wiley
        self.summ = {"311": dc.member_summary(wiley), "78": dc.member_summary(other),
                     "56": dc.member_summary([])}
        self.res_dash = [{"citing": "c", "doi": DASHED, "raw": "not-found", "normalised": "crossref"}] * 10
        self.res_ctrl = [{"citing": "c", "doi": "x", "raw": "crossref", "normalised": ""}] * 10
        rec = {"citing": "c", "dashed": ["d"], "controls": ["e"], "oc_error": False, "oc_indexed": True,
               "oc_dashed": [False], "oc_controls": [True], "oa_error": False, "oa_indexed": True,
               "oa_dashed": [False], "oa_controls": [True]}
        self.cites = [dict(rec, oc_indexed=(i < 5)) for i in range(25)]

    def test_verdicts(self):
        v = dc.verdicts(self.summ, self.res_dash, self.res_ctrl, self.cites)
        self.assertEqual((v["H1"]["k"], v["H1"]["n"]), (6, 20))
        self.assertEqual(v["H1"]["verdict"], "supported")
        self.assertEqual(v["H2"]["members"]["78"]["verdict"], "holds")
        self.assertEqual(v["H2"]["members"]["56"]["verdict"], "no data")
        self.assertEqual((v["H2"]["holds"], v["H2"]["fails"]), (1, 0))
        self.assertEqual(v["H3"]["verdict"], "supported")
        self.assertEqual(v["H4"]["verdict"], "supported")
        self.assertEqual(v["H5"]["verdict"], "supported")
        self.assertEqual(v["H5"]["dash_present"], [0, 25])
        self.assertEqual(v["H6"]["verdict"], "not testable")
        self.assertEqual(v["H6"]["articles"], 5)
        text = dc.report(self.summ, v, self.rows, [{"member": "311", "draws": 3, "failed": 0, "articles": 20}])
        self.assertIn("H1 Wiley article share: 6/20", text)
        self.assertIn("2026-03: 6/20", text)

    def test_h4_not_supported_when_dash_resolves(self):
        res = [{"citing": "c", "doi": DASHED, "raw": "crossref", "normalised": "crossref"}] * 10
        self.assertEqual(dc.verdicts(self.summ, res, self.res_ctrl, self.cites)["H4"]["verdict"], "not supported")


if __name__ == "__main__":
    unittest.main()
