"""Tests for walkprobe.py (ccdi/ethnicity-filter-v2) on made-up data; no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import tempfile
import unittest
import urllib.parse

import walkprobe as wp

COUNTS = {"Not reported": {"CCDI-DCC": 55705, "KidsFirst": 0, "StJude": 3234},
          "Unknown": {"CCDI-DCC": 0, "KidsFirst": 8284, "StJude": 31},
          "Hispanic or Latino": {"CCDI-DCC": 4090, "KidsFirst": 4824, "StJude": 909}}
UNSERVED = {("StJude", "Not reported"): 0, ("StJude", "Unknown"): 0}
SNAP = {"path": "made-up",
        "values": {"KidsFirst": {"Hispanic or Latino": 4824, "Not Hispanic or Latino": 23336,
                                 "Unknown": 10280},
                   "StJude": {"Hispanic or Latino": 909, "Not reported": 3234, "Unknown": 31}}}


def fake_fed(caps=None, status=200, wrong=(), names=None, counts=None):
    """A made-up federation. caps: (source, value) -> the most entries it ever serves for that
    filter; wrong: (source, value) pairs whose entries carry another ethnicity value."""
    caps = UNSERVED if caps is None else caps
    counts = COUNTS if counts is None else counts
    names = names or {}
    calls = []

    def fetch(url):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        page, per, eth = int(q["page"][0]), int(q["per_page"][0]), q["ethnicity"][0]
        calls.append((eth, page))
        body = []
        for src, n in counts[eth].items():
            start = (page - 1) * per
            k = max(0, min(per, n - start))
            if (src, eth) in caps:
                k = max(0, min(k, caps[(src, eth)] - start))
            value = "Not Hispanic or Latino" if (src, eth) in wrong else eth
            data = [{"id": {"namespace": {"organization": src, "name": "ns"},
                            "name": "PID%d" % (start + i)},
                     "metadata": {"ethnicity": {"value": value}}} for i in range(k)]
            body.append({"source": names.get(src, src), "summary": {"counts": {"all": n}},
                         "data": data})
        return status, json.dumps(body).encode(), 0.0
    fetch.calls = calls
    return fetch


def write_gz(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(json.dumps(obj).encode())


def rec(src, name, eth):
    md = {} if eth is None else {"ethnicity": {"value": eth}}
    return {"id": {"namespace": {"organization": src, "name": "ns"}, "name": name},
            "metadata": md}


def make_snapshot(root):
    sub = os.path.join(root, "subject")
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_page": 2, "first_page": "probe-2.json"}, fh)
    write_gz(os.path.join(sub, "probe-2.json.gz"), [
        {"source": "KidsFirst", "data": [rec("KidsFirst", "PID1", "Unknown"),
                                         rec("KidsFirst", "PID2", None)]},
        {"source": "StJude", "data": [rec("StJude", "PID3", "Not reported"),
                                      rec("StJude", "PID4", "Unknown")]},
        {"source": "PCDC", "errors": [{"kind": "NotFound"}]}])
    write_gz(os.path.join(sub, "page-0002.json.gz"), [
        {"source": "KidsFirst", "data": [rec("KidsFirst", "PID1", "Unknown"),
                                         rec("KidsFirst", "PID5", "Hispanic or Latino")]},
        {"source": "StJude", "data": [rec("StJude", "PID6", "Not reported")]}])
    with gzip.open(os.path.join(sub, "page-0003.json.gz"), "wb") as fh:
        fh.write(b"not json")


class WalkProbeTest(unittest.TestCase):
    def walks(self, **kw):
        return wp.run_walks(fake_fed(**kw), pause=0)

    def test_url_of(self):
        u = wp.url_of("Not reported", 3)
        self.assertTrue(u.startswith(wp.FED + "/subject?"))
        self.assertIn("page=3", u)
        self.assertIn("per_page=100", u)
        self.assertIn("ethnicity=Not%20reported", u)

    def test_pages_planned(self):
        fetch = fake_fed()
        walks = wp.run_walks(fetch, pause=0)
        self.assertEqual([walks[n]["pages_planned"] for n in ("not-reported", "unknown", "hispanic")],
                         [33, 83, 10])
        self.assertEqual(len(fetch.calls), 126)
        self.assertEqual(fetch.calls[0], ("Not reported", 1))
        self.assertEqual(fetch.calls[-1], ("Hispanic or Latino", 10))

    def test_all_hold(self):
        walks = self.walks()
        g = wp.grade(walks, SNAP)
        self.assertEqual(set(g.values()), {"pass"}, g)
        self.assertEqual(wp.reading(g, walks), {"stjude": "counted_not_served",
                                                "kidsfirst": "unreached"})

    def test_stjude_served_fails_f1_f2(self):
        walks = self.walks(caps={})
        g = wp.grade(walks, SNAP)
        self.assertEqual((g["F1"], g["F2"], g["F3"], g["F4"]), ("fail", "fail", "pass", "pass"))
        self.assertEqual(wp.reading(g, walks)["stjude"], "served_in_full")

    def test_partial(self):
        walks = self.walks(caps={("StJude", "Not reported"): 100, ("StJude", "Unknown"): 0})
        g = wp.grade(walks, SNAP)
        self.assertEqual(g["F1"], "fail")
        self.assertEqual(wp.reading(g, walks)["stjude"], "partial")

    def test_wrong_value_fails_control(self):
        g = wp.grade(self.walks(wrong={("StJude", "Hispanic or Latino")}), SNAP)
        self.assertEqual((g["F1"], g["F3"]), ("pass", "fail"))

    def test_kidsfirst_reached_in_snapshot_fails_f5(self):
        snap = {"values": {"KidsFirst": {"Unknown": 8284},
                           "StJude": {"Not reported": 3234, "Unknown": 31}}}
        walks = self.walks()
        g = wp.grade(walks, snap)
        self.assertEqual((g["F4"], g["F5"], g["F6"]), ("pass", "fail", "pass"))
        self.assertEqual(wp.reading(g, walks)["kidsfirst"], "other")

    def test_filter_reaching_every_unknown_fails_f5(self):
        counts = json.loads(json.dumps(COUNTS))
        counts["Unknown"]["KidsFirst"] = 10280
        g = wp.grade(self.walks(counts=counts), SNAP)
        self.assertEqual((g["F4"], g["F5"]), ("pass", "fail"))

    def test_non_200_fails(self):
        g = wp.grade(self.walks(status=502), SNAP)
        self.assertEqual([g[k] for k in ("F1", "F2", "F3", "F4")], ["fail"] * 4)

    def test_source_name_any_case(self):
        g = wp.grade(self.walks(names={"StJude": "stjude", "KidsFirst": "KIDSFIRST"}), SNAP)
        self.assertEqual(set(g.values()), {"pass"}, g)

    def test_no_snapshot_fails_f5_f6(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(wp.find_snapshot(d))
        g = wp.grade(self.walks(), None)
        self.assertEqual((g["F5"], g["F6"]), ("fail", "fail"))

    def test_snapshot_values(self):
        with tempfile.TemporaryDirectory() as d:
            make_snapshot(d)
            s = wp.snapshot_values(d)
        self.assertEqual((s["pages_read"], s["pages_unreadable"]), (2, 1))
        self.assertEqual(s["values"]["KidsFirst"],
                         {"Unknown": 1, wp.MISSING: 1, "Hispanic or Latino": 1})
        self.assertEqual(s["values"]["StJude"], {"Not reported": 2, "Unknown": 1})
        self.assertNotIn("PCDC", s["values"])
        self.assertEqual(s["subjects"], {"KidsFirst": 3, "StJude": 3})

    def test_find_snapshot_prefers_newest_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("ccdi-raw-snapshot2",
                        os.path.join("ccdi-fresh-v1", "ccdi-raw-fresh-20261023T214658Z"),
                        os.path.join("x", "ccdi-raw-fresh-20261024T020144Z")):
                make_snapshot(os.path.join(d, rel))
            self.assertEqual(wp.find_snapshot(d),
                             os.path.join(d, "x", "ccdi-raw-fresh-20261024T020144Z"))

    def test_main_writes_no_identifiers(self):
        with tempfile.TemporaryDirectory() as d:
            make_snapshot(os.path.join(d, "data", "ccdi-raw-fresh-20261024T020144Z"))
            out = os.path.join(d, "out")
            wp.main(["--out", out, "--data-dir", os.path.join(d, "data")],
                    fetch=fake_fed(), pause=0)
            with open(os.path.join(out, "walkprobe.json"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertNotIn("PID", text)
        res = json.loads(text)
        self.assertEqual(res["grades"]["F1"], "pass")
        self.assertEqual(res["grades"]["F6"], "fail")
        self.assertEqual(len(res["walks"]), 3)


if __name__ == "__main__":
    unittest.main()
