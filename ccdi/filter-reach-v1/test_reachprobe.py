"""Tests for reachprobe.py (ccdi/filter-reach-v1) on made-up data; no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import collections
import copy
import gzip
import json
import os
import tempfile
import unittest
import urllib.parse

import reachprobe as rp

NHL = "Not Hispanic or Latino"


def person(name, ns, true, served=None):
    """A made-up subject: filters and counts match its true values; entries carry served."""
    return {"name": name, "ns": ns, "true": true, "served": true if served is None else served}


def made_up():
    unk = {"sex": "F", "race": ["Unknown"], "ethnicity": "Unknown"}
    hidden = {"sex": "M", "race": None, "ethnicity": None}
    shown = {"sex": "M", "race": ["Unknown"], "ethnicity": "Unknown"}
    white = {"sex": "F", "race": ["White"], "ethnicity": NHL, "vital_status": "Alive"}
    kf = [person("PID-K%d" % i, "study-a", unk) for i in range(1, 7)]
    kf += [person("PID-K%d" % i, "study-b", hidden, shown) for i in range(7, 10)]
    kf.append(person("PID-K10", "study-a", {"sex": "F", "race": None, "ethnicity": "Unknown"},
                     {"sex": "F", "race": ["Unknown"], "ethnicity": "Unknown"}))
    kf += [person("PID-K%d" % i, "study-a", white) for i in (11, 12)]
    pc_served = {"sex": "F", "race": ["White"], "ethnicity": NHL}
    pcdc = [person("PID-P%d" % i, "pcdc-1", dict(pc_served, vital_status="Alive"), pc_served)
            for i in (1, 2, 3)]
    pcdc.append(person("PID-P4", "pcdc-1", dict(pc_served, vital_status="Dead"), pc_served))
    sj = [person("PID-S%d" % i, "sj-1", {"sex": "M", "race": ["Black or African American"],
                                         "ethnicity": "Hispanic or Latino"}) for i in (1, 2)]
    return {"KidsFirst": kf, "PCDC": pcdc, "StJude": sj}


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def entry(src, r):
    md = {}
    for f, v in r["served"].items():
        if v is not None:
            md[f] = [{"value": x} for x in v] if isinstance(v, list) else {"value": v}
    return {"id": {"namespace": {"organization": src, "name": r["ns"]}, "name": r["name"]},
            "metadata": md}


def fake_fed(records=None, status=200, bad=()):
    """A made-up federation. bad: labels ("walk race") whose responses get status 502."""
    records = made_up() if records is None else records
    calls = []

    def fetch(url):
        parts = urllib.parse.urlsplit(url)
        calls.append(url)
        if parts.path.endswith("/count"):
            field = parts.path.split("/")[-2]
            body = []
            for src, recs in records.items():
                c = collections.Counter()
                for r in recs:
                    c.update(as_list(r["true"].get(field)))
                body.append({"source": src, "total": sum(c.values()), "missing": 0,
                             "values": [{"value": v, "count": n} for v, n in sorted(c.items())]})
            return status, json.dumps(body).encode(), 0.0
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query).items()}
        page, per = int(q.pop("page")), int(q.pop("per_page"))
        (field, value), = q.items()
        body = []
        for src, recs in records.items():
            hits = [r for r in recs if value in as_list(r["true"].get(field))]
            chunk = hits[(page - 1) * per:page * per]
            body.append({"source": src, "summary": {"counts": {"all": len(hits)}},
                         "data": [entry(src, r) for r in chunk]})
        code = 502 if per == rp.PER_PAGE and ("walk " + field) in bad else status
        return code, json.dumps(body).encode(), 0.0
    fetch.calls = calls
    return fetch


def make_snapshot(root, records=None):
    records = made_up() if records is None else records
    sub = os.path.join(root, "subject")
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_page": 100, "first_page": "probe-100.json"}, fh)
    body = [{"source": src, "summary": {"counts": {"all": len(recs)}},
             "data": [entry(src, r) for r in recs]} for src, recs in records.items()]
    body.append({"source": "Treehouse", "errors": [{"kind": "NotFound"}]})
    with gzip.open(os.path.join(sub, "probe-100.json.gz"), "wb") as fh:
        fh.write(json.dumps(body).encode())


SRCS = ("CCDI-DCC", "KidsFirst", "PCDC", "StJude", "Treehouse", "ccdi-ecDNA", "ccdi-iusccc-pst")


def setc(cs, src, field, value, **kw):
    hit = [c for c in cs if (c["source"], c["field"], c["value"]) == (src, field, value)]
    hit[0].update(kw)


def big():
    """Grading inputs at the sizes seen on 2026-10-22 to 2026-10-25, all predictions holding."""
    cs = [{"field": f, "value": v, "source": s, "served": 1000, "count": 1000, "filter": 1000,
           "filter_error_kinds": []} for f in rp.FIELDS for v in rp.VALUES[f] for s in SRCS]
    setc(cs, "KidsFirst", "ethnicity", "Unknown", served=10280, count=8284, filter=8284)
    setc(cs, "KidsFirst", "race", "Unknown", served=11266, count=8607, filter=8607)
    for v, n in (("Alive", 17134), ("Dead", 4952), ("Unknown", 2346)):
        setc(cs, "PCDC", "vital_status", v, served=0, count=n, filter=n)
    over = {"status": 200, "sources": {"PCDC": {"all": 17134, "entries": 100, "error": False,
                                                "error_kinds": [], "values": {rp.MISSING: 100},
                                                "with_value": 0}}}

    def w(n, pages):
        return {"statuses": [200], "pages_planned": pages, "by_source": {"KidsFirst": {
            "pages": pages, "entries": n, "with_value": n, "error_pages": 0, "error_kinds": [],
            "totals": [n], "values": {"Unknown": n}, "first_total": n}}}
    walks = {"ethnicity": w(8284, 83), "race": w(8607, 87)}
    kf = {"ethnicity": {"unreached": 1996, "walked_not_in_snapshot": 0},
          "race": {"unreached": 2659, "walked_not_in_snapshot": 0}, "both_unreached": 1990}
    return cs, over, walks, kf


class ReachProbeTest(unittest.TestCase):
    def test_url_of(self):
        self.assertEqual(rp.url_of("/subject", [("page", 1), ("per_page", 1),
                                                ("vital_status", "Not reported")]),
                         rp.FED + "/subject?page=1&per_page=1&vital_status=Not%20reported")
        self.assertEqual(rp.url_of("/subject/by/race/count"), rp.FED + "/subject/by/race/count")

    def test_values_of(self):
        self.assertEqual(rp.values_of({"metadata": {"race": [{"value": "White"},
                                                             {"value": "Unknown"}]}}, "race"),
                         ["White", "Unknown"])
        self.assertEqual(rp.values_of({"metadata": {"sex": {"value": "F"}}}, "sex"), ["F"])
        self.assertEqual(rp.values_of({"metadata": {}}, "race"), [rp.MISSING])
        self.assertEqual(rp.values_of({"metadata": {"race": []}}, "race"), [rp.MISSING])
        self.assertEqual(rp.values_of({}, "sex"), [rp.MISSING])
        self.assertEqual(rp.values_of({"metadata": {"ethnicity": {"value": ""}}}, "ethnicity"),
                         [rp.MISSING])

    def test_count_items(self):
        parsed = [{"source": "A", "total": 3, "missing": 1, "values": [{"value": "F", "count": 2}]},
                  {"source": "B", "errors": [{"kind": "NotFound"}]}, "junk"]
        self.assertEqual(rp.count_items(parsed), {
            "A": {"error": False, "error_kinds": [], "total": 3, "missing": 1, "values": {"F": 2}},
            "B": {"error": True, "error_kinds": ["NotFound"], "total": None, "missing": None,
                  "values": {}}})

    def test_main_on_made_up_federation(self):
        fetch = fake_fed()
        with tempfile.TemporaryDirectory() as d:
            make_snapshot(os.path.join(d, "data", "ccdi-raw-fresh-20261024T020144Z"))
            out = os.path.join(d, "out")
            rp.main(["--out", out, "--data-dir", os.path.join(d, "data")], fetch=fetch, pause=0)
            with open(os.path.join(out, "reachprobe.json"), encoding="utf-8") as fh:
                text = fh.read()
        self.assertNotIn("PID", text)
        self.assertEqual(len(fetch.calls), 4 + 20 + 1 + 1 + 1)
        res = json.loads(text)
        self.assertEqual(res["grades"], {"R1": "fail", "R2": "fail", "R3": "fail",
                                         "K1": "pass", "K2": "fail", "K3": "pass"})
        self.assertEqual(res["reading"]["kidsfirst_overlap"], "shared")
        self.assertEqual(res["overlap"], 1.0)
        kf = res["kidsfirst"]
        self.assertEqual((kf["ethnicity"]["served_unknown"], kf["ethnicity"]["unreached"]), (10, 3))
        self.assertEqual((kf["race"]["served_unknown"], kf["race"]["unreached"]), (10, 4))
        self.assertEqual((kf["both_unreached"], kf["either_unreached"]), (3, 4))
        self.assertEqual(kf["ethnicity"]["walked_not_in_snapshot"], 0)
        self.assertEqual(kf["by_namespace"]["study-b"],
                         {"subjects": 3, "eth_unknown": 3, "race_unknown": 3,
                          "eth_unreached": 3, "race_unreached": 3, "both_unreached": 3})
        self.assertEqual(kf["by_namespace"]["study-a"]["race_unreached"], 1)
        self.assertEqual(kf["by_namespace"]["study-a"]["eth_unreached"], 0)
        self.assertEqual(kf["values_of_unreached"]["race_unreached"]["sex"], {"F": 1, "M": 3})
        self.assertEqual(kf["values_of_unreached"]["ethnicity_unreached"]["vital_status"],
                         {rp.MISSING: 3})
        cells = {(c["source"], c["field"], c["value"]): c for c in res["cells"]}
        c = cells[("KidsFirst", "ethnicity", "Unknown")]
        self.assertEqual((c["served"], c["count"], c["filter"]), (10, 7, 7))
        c = cells[("PCDC", "vital_status", "Alive")]
        self.assertEqual((c["served"], c["count"], c["filter"]), (0, 3, 3))
        self.assertEqual(res["over_page"]["sources"]["PCDC"]["values"], {rp.MISSING: 3})
        self.assertEqual(res["snapshot"]["subjects"], {"KidsFirst": 12, "PCDC": 4, "StJude": 2})
        self.assertEqual(len(res["requests"]), 27)
        self.assertNotIn("keys", res["walks"][0])

    def test_main_without_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out")
            rp.main(["--out", out, "--data-dir", os.path.join(d, "none")], fetch=fake_fed(),
                    pause=0)
            with open(os.path.join(out, "reachprobe.json"), encoding="utf-8") as fh:
                res = json.load(fh)
        self.assertIsNone(res["kidsfirst"])
        self.assertEqual((res["grades"]["K2"], res["grades"]["K3"]), ("fail", "fail"))
        self.assertEqual(res["reading"]["kidsfirst_overlap"], "none")
        self.assertTrue(all(c["served"] is None for c in res["cells"]))

    def test_all_hold_at_real_sizes(self):
        g = rp.grade(*big())
        self.assertEqual(set(g.values()), {"pass"}, g)
        self.assertEqual(rp.reading(g, big()[3]),
                         {"count_and_filter": "agree", "under_reach": "kidsfirst_unknown_only",
                          "pcdc_vital_status": "filter_without_value",
                          "kidsfirst_overlap": "shared"})

    def test_r1_tolerance_and_mismatch(self):
        cs, over, walks, kf = big()
        setc(cs, "StJude", "sex", "M", count=1001)
        self.assertEqual(rp.grade(cs, over, walks, kf)["R1"], "pass")
        setc(cs, "StJude", "sex", "M", count=1002)
        g = rp.grade(cs, over, walks, kf)
        self.assertEqual((g["R1"], g["R2"], g["R3"]), ("fail", "pass", "pass"))

    def test_r1_needs_enough_cells(self):
        cs, over, walks, kf = big()
        for c in cs[99:]:
            c["count"] = None
        self.assertEqual(rp.grade(cs, over, walks, kf)["R1"], "fail")

    def test_r2_extra_gap_or_wrong_size(self):
        cs, over, walks, kf = big()
        setc(cs, "StJude", "sex", "F", served=1050)
        g = rp.grade(cs, over, walks, kf)
        self.assertEqual((g["R1"], g["R2"]), ("pass", "fail"))
        cs, over, walks, kf = big()
        setc(cs, "KidsFirst", "ethnicity", "Unknown", served=9000)
        self.assertEqual(rp.grade(cs, over, walks, kf)["R2"], "fail")

    def test_r3_value_served_or_counted_low(self):
        cs, over, walks, kf = big()
        over["sources"]["PCDC"]["values"] = {"Alive": 100}
        self.assertEqual(rp.grade(cs, over, walks, kf)["R3"], "fail")
        cs, over, walks, kf = big()
        setc(cs, "PCDC", "vital_status", "Dead", count=3000, filter=3000)
        self.assertEqual(rp.grade(cs, over, walks, kf)["R3"], "fail")

    def test_k1_k2(self):
        cs, over, walks, kf = big()
        walks["race"]["statuses"] = [200, 502]
        self.assertEqual(rp.grade(cs, over, walks, kf)["K1"], "fail")
        cs, over, walks, kf = big()
        kf["race"]["walked_not_in_snapshot"] = 11
        self.assertEqual(rp.grade(cs, over, walks, kf)["K2"], "fail")

    def test_k3_readings(self):
        cs, over, walks, kf = big()
        kf["both_unreached"] = 1000
        g = rp.grade(cs, over, walks, kf)
        self.assertEqual(g["K3"], "fail")
        self.assertEqual(rp.reading(g, kf)["kidsfirst_overlap"], "partly_shared")
        kf["both_unreached"] = 100
        self.assertEqual(rp.reading(g, kf)["kidsfirst_overlap"], "separate")

    def test_failed_walk_fails_k1(self):
        with tempfile.TemporaryDirectory() as d:
            make_snapshot(os.path.join(d, "data", "snap"))
            out = os.path.join(d, "out")
            rp.main(["--out", out, "--data-dir", os.path.join(d, "data")],
                    fetch=fake_fed(bad=("walk race",)), pause=0)
            with open(os.path.join(out, "reachprobe.json"), encoding="utf-8") as fh:
                res = json.load(fh)
        self.assertEqual(res["grades"]["K1"], "fail")
        self.assertEqual(res["walks"][1]["statuses"], [502])

    def test_find_snapshot_prefers_newest_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("ccdi-raw-snapshot2",
                        os.path.join("ccdi-fresh-v1", "ccdi-raw-fresh-20261023T214658Z"),
                        os.path.join("x", "ccdi-raw-fresh-20261024T020144Z")):
                make_snapshot(os.path.join(d, rel))
            self.assertEqual(rp.find_snapshot(d),
                             os.path.join(d, "x", "ccdi-raw-fresh-20261024T020144Z"))


if __name__ == "__main__":
    unittest.main()
