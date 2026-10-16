# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for dash_dois.py (no network)."""
import json
import unittest

import dash_dois as dd

GOOD = {"10.1038/s41572-020-00224-3", "10.1186/1471-2407-12-332"}
OTHER_RA = {"10.12102/j.issn.1009-6493.2019.16.012"}


def fake(url, timeout=60):
    if url.startswith(dd.CROSSREF):
        doi = dd.urllib.parse.unquote(url[len(dd.CROSSREF):].split("?")[0])
        return (200, b"{}") if doi.lower() in GOOD else (404, b"")
    if url.startswith(dd.HANDLES):
        doi = dd.urllib.parse.unquote(url[len(dd.HANDLES):])
        return (200, b"{}") if doi.lower() in OTHER_RA else (404, b"")
    return None, b"unexpected"


class TextTests(unittest.TestCase):
    def test_has_dash(self):
        self.assertTrue(dd.has_dash("10.1038/s41572‐020‐00224‐3"))
        self.assertTrue(dd.has_dash("10.1/a–b"))
        self.assertFalse(dd.has_dash("10.1038/s41572-020-00224-3"))
        self.assertFalse(dd.has_dash(""))

    def test_normalise(self):
        self.assertEqual(dd.normalise("10.1038/s41572‐020‐00224‐3"), "10.1038/s41572-020-00224-3")
        self.assertEqual(dd.normalise("10.1/a−b‑c"), "10.1/a-b-c")
        self.assertEqual(dd.normalise("10.1/ab­c"), "10.1/abc")
        self.assertEqual(dd.normalise("10.1/plain-doi"), "10.1/plain-doi")


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.look = dd.Lookup(fetch=fake)

    def test_dash_fixed(self):
        r = dd.classify("10.1038/s41572‐020‐00224‐3", self.look)
        self.assertEqual((r["dash"], r["raw"], r["normalised"]), (True, "not-found", "crossref"))

    def test_dash_other_ra(self):
        r = dd.classify("10.12102/j.issn.1009‐6493.2019.16.012", self.look)
        self.assertEqual(r["normalised"], "other-ra")

    def test_dash_still_fails(self):
        r = dd.classify("10.1/none‐here", self.look)
        self.assertEqual((r["raw"], r["normalised"]), ("not-found", "not-found"))

    def test_plain(self):
        r = dd.classify("10.3322/caac", self.look)
        self.assertEqual((r["dash"], r["raw"], r["normalised"]), (False, "not-found", ""))
        self.assertEqual(dd.classify("10.1186/1471-2407-12-332", self.look)["raw"], "crossref")

    def test_cache(self):
        dd.classify("10.3322/caac", self.look)
        n = self.look.calls
        dd.classify("10.3322/CAAC", self.look)
        self.assertEqual(self.look.calls, n)

    def test_tally(self):
        recs = [dd.classify(d, self.look) for d in (
            "10.1038/s41572‐020‐00224‐3", "10.12102/j.issn.1009‐6493.2019.16.012",
            "10.1/none‐here", "10.3322/caac", "10.1186/1471-2407-12-332")]
        t = dd.tally(recs)
        self.assertEqual(t["publisher_dois"], 5)
        self.assertEqual(t["dash"], 3)
        self.assertEqual(t["dash_raw_fails"], 3)
        self.assertEqual(t["dash_fixed"], 2)
        self.assertEqual(t["dash_still_fails"], 1)
        self.assertEqual(t["plain_fails"], 1)
        self.assertEqual(t["raw_resolves"], 1)
        self.assertEqual(t["errors"], 0)

    def test_tally_error(self):
        t = dd.tally([{"doi": "x", "dash": False, "raw": "error", "normalised": ""}])
        self.assertEqual((t["errors"], t["plain_fails"]), (1, 0))


class AuditTests(unittest.TestCase):
    def test_audit_counts_only_publisher_asserted(self):
        record = {"message": {"publisher": "Wiley", "member": "311", "container-title": ["J"], "reference": [
            {"key": "a", "DOI": "10.1038/s41572‐020‐00224‐3", "doi-asserted-by": "publisher"},
            {"key": "b", "DOI": "10.1/whatever", "doi-asserted-by": "crossref"},
            {"key": "c", "unstructured": "no doi"}]}}

        def fetch(url, timeout=60):
            if url.startswith(dd.CROSSREF + "10.9999/ma"):
                return 200, json.dumps(record).encode()
            return fake(url, timeout)

        row, recs = dd.audit("1", "10.9999/ma", dd.Lookup(fetch=fake), fetch=fetch)
        self.assertEqual(row["status"], "audited")
        self.assertEqual(row["publisher"], "Wiley")
        self.assertEqual(len(recs), 1)
        self.assertEqual(row["tally"]["dash_fixed"], 1)
        self.assertEqual(recs[0]["pmid"], "1")

    def test_audit_missing(self):
        row, recs = dd.audit("1", "10.9999/absent", dd.Lookup(fetch=fake), fetch=fake)
        self.assertEqual((row["status"], recs), ("not-in-crossref", []))

    def test_pubmed_dois(self):
        body = {"result": {"1": {"articleids": [{"idtype": "pubmed", "value": "1"},
                                                {"idtype": "doi", "value": " 10.1/x "}]}, "2": {}}}
        got = dd.pubmed_dois(["1", "2"], fetch=lambda url, timeout=60: (200, json.dumps(body).encode()))
        self.assertEqual(got, {"1": "10.1/x", "2": ""})


if __name__ == "__main__":
    unittest.main()
