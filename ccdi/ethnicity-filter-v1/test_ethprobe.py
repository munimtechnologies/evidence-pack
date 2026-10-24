"""Tests of ethprobe.py on made-up responses (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import tempfile
import unittest
import urllib.parse

import ethprobe

NAMES = {e: n for n, _, e in ethprobe.REQUESTS if e}
ALL = {"CCDI-DCC": 59795, "KidsFirst": 38440, "PCDC": 24332, "StJude": 14681, "Treehouse": 12723}


def subject_body(totals):
    """Aggregated /subject body at per_page 1: a total per source, or an error object for None."""
    body = []
    for src, n in totals.items():
        if n is None:
            body.append({"source": src, "errors": [{"kind": "InvalidParameters",
                                                    "message": "made up"}]})
        else:
            body.append({"source": src, "summary": {"counts": {"all": n, "current": min(n, 1)}},
                         "data": [{"id": {"namespace": "x", "name": "PARTICIPANT%d" % i}}
                                  for i in range(min(n, 1))]})
    return json.dumps(body).encode()


def count_body(values):
    return json.dumps([{"source": src, "total": sum(v.values()), "missing": 0,
                        "values": [{"value": k, "count": c} for k, c in v.items()]}
                       for src, v in values.items()]).encode()


def world(**over):
    """Responses where every prediction holds; over replaces some (keys use _ for -)."""
    r = {"info": (200, json.dumps([{"source": "CCDI-DCC", "api_version": "v1.3.0"}]).encode()),
         "count": (200, count_body({"CCDI-DCC": {"Hispanic or Latino": 4090,
                                                 "Not reported": 55705},
                                    "KidsFirst": {"Hispanic or Latino": 4824,
                                                  "Not Hispanic or Latino": 23336}})),
         "all": (200, subject_body(ALL)),
         "hispanic": (200, subject_body({"CCDI-DCC": 4090, "KidsFirst": 4824, "PCDC": 2916,
                                         "StJude": 909, "Treehouse": 553})),
         "not_reported": (200, subject_body({"CCDI-DCC": 55705, "KidsFirst": 5000, "PCDC": 100,
                                             "StJude": 3000, "Treehouse": 3000})),
         "not_hispanic": (200, subject_body({"CCDI-DCC": 0, "KidsFirst": 23336, "PCDC": 17747,
                                             "StJude": 10505, "Treehouse": 8323})),
         "unknown": (200, subject_body({"CCDI-DCC": 0, "KidsFirst": 3000, "PCDC": 3000,
                                        "StJude": 200, "Treehouse": 60})),
         "not_allowed": (200, subject_body({"CCDI-DCC": 0, "KidsFirst": 0, "PCDC": 0,
                                            "StJude": 0, "Treehouse": 0}))}
    r.update(over)
    return r


def fake(responses):
    def fetch(url):
        parts = urllib.parse.urlsplit(url)
        path = parts.path[len("/api/v1"):]
        if path == "/info":
            key = "info"
        elif path.endswith("/count"):
            key = "count"
        else:
            eth = urllib.parse.parse_qs(parts.query).get("ethnicity")
            key = NAMES[eth[0]].replace("-", "_") if eth else "all"
        status, body = responses[key]
        return status, body, 0.1
    return fetch


def run(responses):
    with tempfile.TemporaryDirectory() as tmp:
        ethprobe.main(["--out", tmp], fetch=fake(responses), pause=0)
        with open(os.path.join(tmp, "ethprobe.json"), encoding="utf-8") as fh:
            return json.load(fh)


class EthProbeTest(unittest.TestCase):
    def test_url_of(self):
        self.assertEqual(ethprobe.url_of("/info", None), ethprobe.FED + "/info")
        self.assertEqual(ethprobe.url_of("/subject/by/ethnicity/count", None),
                         ethprobe.FED + "/subject/by/ethnicity/count")
        self.assertEqual(ethprobe.url_of("/subject", None),
                         ethprobe.FED + "/subject?page=1&per_page=1")
        self.assertEqual(ethprobe.url_of("/subject", "Not Hispanic or Latino"),
                         ethprobe.FED + "/subject?page=1&per_page=1"
                         "&ethnicity=Not%20Hispanic%20or%20Latino")

    def test_eight_requests_five_values(self):
        self.assertEqual(len(ethprobe.REQUESTS), 8)
        self.assertEqual(sorted(NAMES), ["Hispanic or Latino", "Not Hispanic or Latino",
                                         "Not allowed to collect", "Not reported", "Unknown"])

    def test_all_hold(self):
        out = run(world())
        self.assertEqual(out["grades"], {k: "pass" for k in ("E1", "E2", "E3", "E4", "E5")})
        self.assertEqual(out["reading"], "silent_zero")
        self.assertEqual(out["totals"]["not-hispanic"]["sum_all"], 23336 + 17747 + 10505 + 8323)
        self.assertEqual(out["totals"]["all"]["sum_all"], sum(ALL.values()))
        recs = {x["name"]: x for x in out["requests"]}
        self.assertEqual(recs["info"]["info_versions"], [["/CCDI-DCC/api_version", "v1.3.0"]])
        self.assertEqual(recs["count"]["count"]["CCDI-DCC"]["values"],
                         {"Hispanic or Latino": 4090, "Not reported": 55705})

    def test_source_name_any_case(self):
        out = run(world(not_hispanic=(200, subject_body({"ccdi-dcc": 0, "kidsfirst": 23336,
                                                         "PCDC": 17747, "StJude": 10505,
                                                         "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E1"], "pass")
        self.assertEqual(out["grades"]["E2"], "pass")

    def test_mapped_value_fails_e1(self):
        out = run(world(not_hispanic=(200, subject_body({"CCDI-DCC": 55705, "KidsFirst": 23336,
                                                         "PCDC": 17747, "StJude": 10505,
                                                         "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E1"], "fail")
        self.assertEqual(out["grades"]["E2"], "pass")
        self.assertEqual(out["reading"], "matches_not_reported")

    def test_error_item_fails_e1(self):
        out = run(world(not_hispanic=(200, subject_body({"CCDI-DCC": None, "KidsFirst": 23336,
                                                         "PCDC": 17747, "StJude": 10505,
                                                         "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E1"], "fail")
        self.assertEqual(out["reading"], "error")
        recs = {x["name"]: x for x in out["requests"]}
        self.assertEqual(recs["not-hispanic"]["sources"]["CCDI-DCC"]["error_kinds"],
                         ["InvalidParameters"])

    def test_missing_source_fails_e1(self):
        out = run(world(not_hispanic=(200, subject_body({"KidsFirst": 23336, "PCDC": 17747,
                                                         "StJude": 10505, "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E1"], "fail")
        self.assertEqual(out["reading"], "missing")

    def test_non_200_fails_e1_and_e2(self):
        out = run(world(not_hispanic=(502, b"<html>bad gateway</html>")))
        self.assertEqual(out["grades"]["E1"], "fail")
        self.assertEqual(out["grades"]["E2"], "fail")
        self.assertEqual(out["reading"], "missing")
        self.assertEqual(out["grades"]["E3"], "pass")

    def test_other_source_error_or_small_fails_e2(self):
        out = run(world(not_hispanic=(200, subject_body({"CCDI-DCC": 0, "KidsFirst": 23336,
                                                         "PCDC": None, "StJude": 10505,
                                                         "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E2"], "fail")
        self.assertEqual(out["grades"]["E1"], "pass")
        out = run(world(not_hispanic=(200, subject_body({"CCDI-DCC": 0, "KidsFirst": 23336,
                                                         "PCDC": 17747, "StJude": 999,
                                                         "Treehouse": 8323}))))
        self.assertEqual(out["grades"]["E2"], "fail")

    def test_unknown_served_fails_e3(self):
        out = run(world(unknown=(200, subject_body({"CCDI-DCC": 55705, "KidsFirst": 3000}))))
        self.assertEqual(out["grades"]["E3"], "fail")
        self.assertEqual(out["grades"]["E1"], "pass")

    def test_closure_off_by_one_fails_e4(self):
        out = run(world(hispanic=(200, subject_body({"CCDI-DCC": 4091, "KidsFirst": 4824}))))
        self.assertEqual(out["grades"]["E4"], "fail")
        small = dict(ALL, **{"CCDI-DCC": 50000})
        out = run(world(all=(200, subject_body(small)),
                        hispanic=(200, subject_body({"CCDI-DCC": 4000})),
                        not_reported=(200, subject_body({"CCDI-DCC": 46000}))))
        self.assertEqual(out["grades"]["E4"], "fail")

    def test_count_with_standard_value_fails_e5(self):
        body = count_body({"CCDI-DCC": {"Hispanic or Latino": 4090, "Not reported": 50000,
                                        "Not Hispanic or Latino": 5705}})
        out = run(world(count=(200, body)))
        self.assertEqual(out["grades"]["E5"], "fail")
        out = run(world(count=(200, count_body({"KidsFirst": {"Unknown": 3}}))))
        self.assertEqual(out["grades"]["E5"], "fail")

    def test_no_participant_names_written(self):
        out = run(world())
        self.assertNotIn("PARTICIPANT", json.dumps(out))


if __name__ == "__main__":
    unittest.main()
