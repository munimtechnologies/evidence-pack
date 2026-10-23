"""Tests of probe1.py on made-up responses (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import tempfile
import unittest
import urllib.parse

import probe1

HDRS = [("Content-Type", "application/json"), ("Content-Length", "10")]
LINK = ('<https://x.example/api/v1/subject?page=1&per_page=100>; rel="first", '
        '<https://x.example/api/v1/subject?page=599&per_page=100>; rel="last"')


def subject_page(**sources):
    """Aggregated /subject body: n entries per source, or an error object for None."""
    body = []
    for src, n in sources.items():
        if n is None:
            body.append({"source": src, "errors": [{"kind": "NotFound"}]})
        else:
            body.append({"source": src,
                         "data": [{"id": {"name": "PARTICIPANT%d" % i}} for i in range(n)]})
    return json.dumps(body).encode()


def mapping_page(**domains):
    ids = [{"domain_name": d, "participant_id": "PARTICIPANT%d" % i}
           for d, n in domains.items() for i in range(n)]
    return json.dumps({"participant_ids": ids}).encode()


def world(**over):
    """Responses where every prediction holds; over replaces some, keyed like 'subject_35'."""
    r = {"info": (200, HDRS, json.dumps([{"source": "PCDC", "api_version": "v1.2.0"}]).encode()),
         "subject_1": (200, HDRS, subject_page(PCDC=100, StJude=100)),
         "mapping_1": (200, HDRS, mapping_page(pcdc=100, stjude=100)),
         "subject_35": (200, HDRS, subject_page(PCDC=None, StJude=100)),
         "mapping_35": (200, HDRS, mapping_page(stjude=100)),
         "subject_600": (200, HDRS, subject_page(PCDC=None, StJude=0)),
         "mapping_600": (200, HDRS, probe1.compact(probe1.NOT_FOUND))}
    r.update(over)
    return r


def fake(responses):
    def fetch(url):
        parts = urllib.parse.urlsplit(url)
        path = parts.path[len("/api/v1/"):].replace("subject-mapping", "mapping")
        page = urllib.parse.parse_qs(parts.query).get("page")
        status, headers, body = responses[path + ("_" + page[0] if page else "")]
        return status, headers, body, 0.1
    return fetch


def run(responses):
    with tempfile.TemporaryDirectory() as tmp:
        probe1.main(["--out", tmp], fetch=fake(responses), pause=0)
        with open(os.path.join(tmp, "probe1.json"), encoding="utf-8") as fh:
            return json.load(fh)


def by_name(out):
    return {x["name"]: x for x in out["requests"]}


class Probe1Test(unittest.TestCase):
    def test_error_object_sizes(self):
        self.assertEqual(probe1.compact(probe1.SERVER_ERROR),
                         b'{"errors":[{"kind":"NotFound","method":"GET",'
                         b'"route":"/subject-mapping","message":"Server Error."}]}')
        self.assertEqual(len(probe1.compact(probe1.SERVER_ERROR)), 100)
        self.assertEqual(len(probe1.compact(probe1.NOT_FOUND)), 118)

    def test_url_of(self):
        self.assertEqual(probe1.url_of("/info", None), probe1.FED + "/info")
        self.assertEqual(probe1.url_of("/subject", 35),
                         probe1.FED + "/subject?page=35&per_page=100")

    def test_link_rels(self):
        self.assertEqual(probe1.link_rels(LINK), {"first": 1, "last": 599})
        self.assertEqual(probe1.link_rels(""), {})
        self.assertEqual(probe1.link_rels(None), {})

    def test_fixed_error(self):
        self.assertEqual(probe1.fixed_error(probe1.compact(probe1.SERVER_ERROR)), "server_error")
        self.assertEqual(probe1.fixed_error(json.dumps(probe1.NOT_FOUND).encode()), "not_found")
        self.assertIsNone(probe1.fixed_error(b'{"participant_ids": []}'))
        self.assertIsNone(probe1.fixed_error(b"<html>"))

    def test_all_hold(self):
        out = run(world())
        self.assertEqual(out["grades"], {k: "pass" for k in ("A1", "A2", "A3", "A4", "A5", "A6")})
        self.assertEqual(out["expected_error_bytes"], {"server_error": 100, "not_found": 118})
        recs = by_name(out)
        self.assertEqual(recs["subject-35"]["sources"]["PCDC"], {"entries": None, "error": True})
        self.assertEqual(recs["mapping-35"]["entries"], 100)
        self.assertEqual(recs["mapping-600"]["fixed_error"], "not_found")
        self.assertEqual(recs["info"]["info_versions"], [["/PCDC/api_version", "v1.2.0"]])
        self.assertEqual(recs["subject-1"]["header_names"], ["content-length", "content-type"])

    def test_link_header_fails_a1(self):
        out = run(world(subject_1=(200, HDRS + [("Link", LINK)], subject_page(PCDC=100))))
        self.assertEqual(out["grades"]["A1"], "fail")
        self.assertEqual(out["grades"]["A2"], "pass")
        self.assertEqual(by_name(out)["subject-1"]["link_rels"], {"first": 1, "last": 599})

    def test_server_error_past_end_fails_a3(self):
        out = run(world(mapping_600=(200, HDRS, probe1.compact(probe1.SERVER_ERROR))))
        self.assertEqual(out["grades"]["A3"], "fail")
        rec = by_name(out)["mapping-600"]
        self.assertEqual((rec["fixed_error"], rec["bytes"]), ("server_error", 100))

    def test_pcdc_served_fails_a4_and_a5(self):
        out = run(world(subject_35=(200, HDRS, subject_page(PCDC=100, StJude=100))))
        self.assertEqual(out["grades"]["A4"], "fail")
        self.assertEqual(out["grades"]["A5"], "fail")
        self.assertEqual(out["grades"]["A6"], "pass")

    def test_non_200_fails_a2_and_a6(self):
        out = run(world(subject_600=(404, HDRS, b'{"errors": []}')))
        self.assertEqual(out["grades"]["A2"], "fail")
        self.assertEqual(out["grades"]["A6"], "fail")
        self.assertEqual(out["grades"]["A1"], "pass")

    def test_no_participant_names_written(self):
        out = run(world())
        self.assertNotIn("PARTICIPANT", json.dumps(out))


if __name__ == "__main__":
    unittest.main()
