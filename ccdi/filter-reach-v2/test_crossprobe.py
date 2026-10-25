"""Tests for crossprobe.py on a made-up federation (no network). They run inside the sealed job
before any request.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import collections
import gzip
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import crossprobe as cp
import reachprobe as rp

# Thresholds scaled to the made-up federation below.
TOY = {"DCC_FILTER_U": (7, 7), "DCC_COUNT_U": (10, 10), "DCC_UNREACHED": (3, 3)}


def rec(org, ns, name, sex=None, race=None, eth=None, vital=None):
    md = {}
    if sex is not None:
        md["sex"] = {"value": sex}
    if race is not None:
        md["race"] = [{"value": race}]
    if eth is not None:
        md["ethnicity"] = {"value": eth}
    if vital is not None:
        md["vital_status"] = {"value": vital}
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "metadata": md}


class Fed:
    """A made-up federation. StJude: 178 subjects with ethnicity and no vital status; its vital
    status filter reads ethnicity when cross is "all" (only for shared values when "shared",
    never when "none"). CCDI-DCC: 30 subjects; 3 stored as "Unknown" are served and counted as
    "U" but reached only by the raw value. PCDC: errors on vital status."""

    def __init__(self, cross="all", raw_ok=True):
        eths = (["Unknown"] * 3 + ["Not reported"] * 150 + ["Hispanic or Latino"] * 5
                + ["Not Hispanic or Latino"] * 20)
        self.st = [rec("StJude", "sj-ns", "SUBJ-ST-%d" % i, sex="F", race="White", eth=e)
                   for i, e in enumerate(eths)]
        self.dcc, self.stored = [], {}
        for i in range(30):
            stored = ("Male" if i < 10 else "Female" if i < 20
                      else "Not Reported" if i < 27 else "Unknown")
            r = rec("CCDI", "phs-a" if i % 2 else "phs-b", "SUBJ-DCC-%d" % i,
                    sex={"Male": "M", "Female": "F"}.get(stored, "U"), race="White",
                    eth="Not reported", vital="Alive")
            self.dcc.append(r)
            self.stored[r["id"]["name"]] = stored
        self.cross, self.raw_ok, self.urls = cross, raw_ok, []

    def st_match(self, field, value):
        if field == "vital_status":
            if self.cross == "none" or (self.cross == "shared" and value not in cp.SHARED):
                return [] if self.cross == "none" else None
            field = "ethnicity"
        return [r for r in self.st if value in rp.values_of(r, field)]

    def dcc_match(self, field, value):
        if field == "sex":
            if value not in ("M", "F", "U") and not self.raw_ok:
                return None
            stored = {"M": "Male", "F": "Female", "U": "Not Reported"}.get(value, value)
            return [r for r in self.dcc if self.stored[r["id"]["name"]] == stored]
        return [r for r in self.dcc if value in rp.values_of(r, field)]

    @staticmethod
    def count_item(name, recs, field):
        c, missing = collections.Counter(), 0
        for r in recs:
            vs = rp.values_of(r, field)
            if vs == [rp.MISSING]:
                missing += 1
            else:
                c.update(vs)
        return {"source": name, "total": len(recs), "missing": missing,
                "values": [{"value": v, "count": n} for v, n in sorted(c.items())]}

    def __call__(self, url):
        self.urls.append(url)
        parts = urllib.parse.urlsplit(url)
        path = parts.path[len("/api/v1"):]
        if path.startswith("/subject/by/"):
            field = path.split("/")[3]
            body = [self.count_item("StJude", self.st, field),
                    self.count_item("CCDI-DCC", self.dcc, field),
                    {"source": "PCDC", "errors": [{"kind": "ServerConnection"}]}]
            return 200, json.dumps(body).encode(), 0.0
        q = dict(urllib.parse.parse_qsl(parts.query))
        page, per = int(q.pop("page")), int(q.pop("per_page"))
        (field, value), = q.items()
        items = []
        for name, hits in (("StJude", self.st_match(field, value)),
                           ("CCDI-DCC", self.dcc_match(field, value))):
            if hits is None:
                items.append({"source": name, "errors": [{"kind": "InvalidParameters"}]})
            else:
                items.append({"source": name, "summary": {"counts": {"all": len(hits)}},
                              "data": hits[(page - 1) * per:page * per]})
        if field == "vital_status":
            items.append({"source": "PCDC", "errors": [{"kind": "InvalidParameters"}]})
        else:
            items.append({"source": "PCDC", "summary": {"counts": {"all": 0}}, "data": []})
        return 200, json.dumps(items).encode(), 0.0


def write_snapshot(root, fed):
    raw = os.path.join(root, "ccdi-fresh-v1", "ccdi-raw-fresh-20261024T020144Z", "subject")
    os.makedirs(raw)
    with open(os.path.join(raw, "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"first_page": "page-0001.json"}, fh)
    body = [{"source": "StJude", "data": fed.st}, {"source": "CCDI-DCC", "data": fed.dcc},
            {"source": "PCDC", "data": []}]
    with gzip.open(os.path.join(raw, "page-0001.json.gz"), "wb") as fh:
        fh.write(json.dumps(body).encode())


class CrossProbeTest(unittest.TestCase):

    def run_probe(self, fed, snapshot=True):
        with tempfile.TemporaryDirectory() as tmp:
            data, out = os.path.join(tmp, "data"), os.path.join(tmp, "out")
            os.makedirs(data)
            if snapshot:
                write_snapshot(data, fed)
            self.assertEqual(cp.main(["--out", out, "--data-dir", data], fetch=fed, pause=0), 0)
            with open(os.path.join(out, "crossprobe.json"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertNotIn("SUBJ-", text)
        return json.loads(text)

    def test_request_plan(self):
        self.assertEqual(len(cp.totals_plan()), 18)
        fed = Fed()
        with mock.patch.multiple(cp, **TOY):
            self.run_probe(fed)
        # 2 counts + 18 totals + walks of 1, 1, 2, 2 and 1 pages
        self.assertEqual(len(fed.urls), 27)
        self.assertTrue(all(u.startswith(rp.FED) for u in fed.urls))

    def test_all_hold_on_cross_wired_federation(self):
        with mock.patch.multiple(cp, **TOY):
            res = self.run_probe(Fed())
        self.assertEqual(set(res["grades"].values()), {"pass"}, res["grades"])
        self.assertEqual(res["reading"], {"stjude_vital_filter": "reads_ethnicity",
                                          "dcc_sex_u": "else_bucket_found"})
        self.assertEqual(res["stjude"]["same_subjects"]["Not reported"],
                         {"vital_walk": 150, "ethnicity_walk": 150, "both": 150,
                          "vital_only": 0, "ethnicity_only": 0})
        self.assertEqual(res["stjude"]["snapshot"]["Unknown"]["vital_status_of_walked"],
                         {rp.MISSING: 3})
        un = res["ccdi_dcc"]["unreached"]
        self.assertEqual((un["served_u"], un["unreached"]), (10, 3))
        self.assertEqual(un["values_of_unreached"]["sex"], {"U": 3})
        self.assertEqual(res["pcdc"]["reading"], "both_unavailable")

    def test_real_thresholds_fail_on_toy_sizes(self):
        res = self.run_probe(Fed())
        g = res["grades"]
        self.assertEqual((g["S1"], g["S2"], g["S3"], g["D3"]), ("pass",) * 4)
        self.assertEqual((g["D1"], g["D2"]), ("fail", "fail"))

    def test_not_cross_wired(self):
        with mock.patch.multiple(cp, **TOY):
            res = self.run_probe(Fed(cross="none"))
        g = res["grades"]
        self.assertEqual((g["S1"], g["S2"], g["S3"]), ("fail",) * 3)
        self.assertEqual(res["reading"]["stjude_vital_filter"], "other")
        self.assertEqual(g["D1"], "pass")

    def test_cross_wired_on_shared_values_only(self):
        with mock.patch.multiple(cp, **TOY):
            res = self.run_probe(Fed(cross="shared"))
        g = res["grades"]
        self.assertEqual((g["S1"], g["S2"], g["S3"]), ("pass", "pass", "fail"))
        self.assertEqual(res["reading"]["stjude_vital_filter"],
                         "matches_ethnicity_on_shared_values")

    def test_raw_values_rejected(self):
        with mock.patch.multiple(cp, **TOY):
            res = self.run_probe(Fed(raw_ok=False))
        self.assertEqual(res["grades"]["D3"], "fail")
        self.assertEqual(res["reading"]["dcc_sex_u"], "raw_rejected")
        self.assertEqual(res["grades"]["D1"], "pass")

    def test_without_snapshot(self):
        with mock.patch.multiple(cp, **TOY):
            res = self.run_probe(Fed(), snapshot=False)
        self.assertEqual(res["grades"]["D2"], "fail")
        self.assertIsNone(res["ccdi_dcc"]["unreached"])
        self.assertEqual(res["grades"]["S2"], "pass")

    def test_served_in_full_rejects_short_walk(self):
        w = {"field": "sex", "target": cp.DCC, "pages_planned": 2, "statuses": [200],
             "keys": [("CCDI-DCC", "o", "n", str(i)) for i in range(150)],
             "by_field": {"sex": {"CCDI-DCC": {"pages": 2, "entries": 150, "with_value": 150,
                                               "error_pages": 0, "error_kinds": [],
                                               "totals": [160], "values": {"U": 150},
                                               "first_total": 160}}}}
        self.assertFalse(cp.served_in_full(w))
        w["by_field"]["sex"]["CCDI-DCC"]["first_total"] = 150
        self.assertTrue(cp.served_in_full(w))
        w["keys"][1] = w["keys"][0]
        self.assertFalse(cp.served_in_full(w))


if __name__ == "__main__":
    unittest.main()
