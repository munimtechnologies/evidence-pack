# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the 2026-10-17 operational amendment to pubmed_commentin (no network)."""
import io
import unittest
import urllib.error
import urllib.parse
from unittest import mock

import pubmed_commentin as pc


def ids_of(body):
    return urllib.parse.parse_qs(body.decode())["id"][0].split(",")


def xml_for(ids):
    return ("<PubmedArticleSet>" + "".join(
        f"<PubmedArticle><MedlineCitation><PMID>{i}</PMID></MedlineCitation></PubmedArticle>"
        for i in ids) + "</PubmedArticleSet>").encode()


class FakeResp:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.data


def http_error(code, body=b"<ERROR>Failed to connect to PubOne service</ERROR>"):
    return urllib.error.HTTPError("https://example.org/x", code, "err", {}, io.BytesIO(body))


class TestEfetchSplit(unittest.TestCase):
    def test_large_batch_fails_pieces_succeed(self):
        def fetch(body):
            ids = ids_of(body)
            if len(ids) > pc.EFETCH_SPLIT:
                raise RuntimeError("HTTP 400")
            return xml_for(ids)

        pmids = [str(i) for i in range(1, 46)]
        errors = []
        out = pc.efetch(pmids, errors, fetch)
        self.assertEqual(sorted(out, key=int), pmids)
        self.assertEqual(errors, [])

    def test_bad_piece_is_logged_not_fatal(self):
        def fetch(body):
            ids = ids_of(body)
            if "13" in ids:
                raise RuntimeError("HTTP 400")
            return xml_for(ids)

        pmids = [str(i) for i in range(1, 46)]
        errors = []
        out = pc.efetch(pmids, errors, fetch)
        self.assertEqual(len(out), 25)
        self.assertNotIn("13", out)
        self.assertEqual(pc.efetch_failed_count(errors), 20)
        self.assertEqual(len(errors), 1)

    def test_gives_up_after_repeated_failures(self):
        calls = []

        def fetch(body):
            calls.append(len(ids_of(body)))
            raise RuntimeError("down")

        pmids = [str(i) for i in range(1, 251)]
        errors = []
        out = pc.efetch(pmids, errors, fetch)
        self.assertEqual(out, {})
        self.assertEqual(len(calls), 1 + pc.EFETCH_BATCH // pc.EFETCH_SPLIT)
        self.assertEqual(pc.efetch_failed_count(errors), 250)
        self.assertEqual(errors[-1]["error"], "skipped after repeated failures")

    def test_no_errors_list(self):
        out = pc.efetch(["5", "6"], None, lambda body: xml_for(ids_of(body)))
        self.assertEqual(sorted(out), ["5", "6"])


class TestHttpRetry(unittest.TestCase):
    def test_400_final_by_default(self):
        with mock.patch.object(pc.urllib.request, "urlopen", side_effect=http_error(400)) as u, \
                mock.patch.object(pc.time, "sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                pc.http("https://example.org/x")
        self.assertEqual(u.call_count, 1)

    def test_400_retried_for_ncbi(self):
        effects = [http_error(400), http_error(400), FakeResp(b"ok")]
        with mock.patch.object(pc.urllib.request, "urlopen", side_effect=effects) as u, \
                mock.patch.object(pc.time, "sleep"):
            self.assertEqual(pc.ncbi("https://example.org/x"), b"ok")
        self.assertEqual(u.call_count, 3)

    def test_404_still_final(self):
        with mock.patch.object(pc.urllib.request, "urlopen", side_effect=http_error(404)) as u, \
                mock.patch.object(pc.time, "sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                pc.http("https://example.org/x", retry_400=True)
        self.assertEqual(u.call_count, 1)

    def test_persistent_400_reports_body(self):
        effects = [http_error(400), http_error(400), http_error(400)]
        with mock.patch.object(pc.urllib.request, "urlopen", side_effect=effects) as u, \
                mock.patch.object(pc.time, "sleep"):
            with self.assertRaises(RuntimeError) as cm:
                pc.http("https://example.org/x", tries=3, retry_400=True)
        self.assertEqual(u.call_count, 3)
        self.assertIn("HTTP 400", str(cm.exception))
        self.assertIn("PubOne", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
