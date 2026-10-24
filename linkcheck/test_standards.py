"""Tests for LinkCheck 0.5.0's OMB race/ethnicity reading (core.race_standard, core.hispanic
and the report's "standards" section), on made-up records. No network. Every expected value
was worked out by hand before the first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import shutil
import tempfile
import unittest

from linkcheck import ccdi, core
import test_ccdi

NH, H = "Not Hispanic or Latino", "Hispanic or Latino"
RECORDS = [
    {"source": "A", "id": "a1", "race": ["White"], "ethnicity": NH},
    {"source": "A", "id": "a2", "race": [H, "White"]},
    {"source": "A", "id": "a3", "race": ["Asian"]},
    {"source": "A", "id": "a4", "race": ["Middle Eastern or North African"], "ethnicity": H},
    {"source": "A", "id": "a5", "race": [H], "ethnicity": NH},
    {"source": "A", "id": "a6", "race": ["Not Reported"], "ethnicity": "Unknown"},
    {"source": "B", "id": "b1", "race": ["White"], "ethnicity": H},
    {"source": "B", "id": "b2", "race": "White"},
    {"source": "B", "id": "b3", "race": ["Asian"], "ethnicity": NH},
    {"source": "B", "id": "b4", "race": ["Native Hawaiian or Pacific Islander"]},
]
LINKS = [{"a_source": "A", "a_id": a, "b_source": "B", "b_id": b}
         for a, b in (("a1", "b1"), ("a2", "b2"), ("a3", "b3"), ("a4", "b4"), ("a5", "b1"))]


def run(declared=None):
    return core.check(RECORDS, LINKS, ("exact",), (), declared)


class Readings(unittest.TestCase):
    def test_one_record_at_a_time(self):
        index = core.Index(RECORDS)
        got = {k[1]: v for k, v in core.readings(index).items()}
        self.assertEqual(got, {
            "a1": ("1997", "NH"), "a2": ("2024", "H"), "a3": ("undetermined", None),
            "a4": ("both", "H"), "a5": ("contradictory", None), "a6": ("no_value", None),
            "b1": ("1997", "H"), "b2": ("undetermined", None), "b3": ("1997", "NH"),
            "b4": ("undetermined", None)})

    def test_declared_fills_only_undetermined(self):
        index = core.Index(RECORDS)
        got = {k[1]: v for k, v in core.readings(index, {"A": "2024", "B": "1997"}).items()}
        self.assertEqual(got["a3"], ("declared_2024", "NH_implied"))
        self.assertEqual(got["a1"], ("1997", "NH"))
        self.assertEqual(got["a6"], ("no_value", None))
        self.assertEqual(got["b2"], ("declared_1997", None))
        self.assertEqual(got["b4"], ("declared_1997", None))

    def test_comma_joined_list(self):
        index = core.Index([
            {"source": "A", "id": "x", "race": ["White, Hispanic or Latino"], "ethnicity": H},
            {"source": "A", "id": "y", "race": "Asian, Unknown"},
            {"source": "A", "id": "z", "race": ["White, Hispanic or Latino"],
             "ethnicity": "Not reported"}])
        x, y, z = (index.records[("A", i)] for i in ("x", "y", "z"))
        self.assertEqual(x["race"], frozenset())
        self.assertEqual(x["race_2024"], frozenset({"White", "Hispanic or Latino"}))
        self.assertEqual(y["race_2024"], frozenset())
        got = {k[1]: v for k, v in core.readings(index).items()}
        self.assertEqual(got, {"x": ("both", "H"), "y": ("no_value", None),
                               "z": ("2024", "H")})

    def test_1997_reading_is_unchanged(self):
        index = core.Index(RECORDS)
        self.assertEqual(index.records[("A", "a2")]["race"], frozenset({"White"}))
        self.assertEqual(index.records[("A", "a4")]["race"], frozenset())
        self.assertEqual(index.records[("B", "b4")]["race"], frozenset())
        self.assertEqual(index.records[("B", "b4")]["race_2024"],
                         frozenset({"Native Hawaiian or other Pacific Islander"}))
        rep, _ = run()
        self.assertEqual(rep["completeness"]["A"]["informative"]["race"], 3)
        self.assertEqual(rep["completeness"]["A"]["informative"]["ethnicity"], 3)
        self.assertEqual(rep["conflicts"]["exact"]["all"]["race"],
                         {"agree": 3, "uninformative": 2})
        self.assertEqual(rep["conflicts"]["exact"]["all"]["ethnicity"],
                         {"disagree": 2, "uninformative": 3})


class Report(unittest.TestCase):
    def test_by_source(self):
        rep, _ = run()
        st = rep["standards"]
        self.assertEqual(st["declared"], {})
        self.assertEqual(st["by_source"]["A"], {
            "records": 6,
            "convention": {"1997": 1, "2024": 1, "both": 1, "contradictory": 1,
                           "no_value": 1, "undetermined": 1},
            "hispanic": {"H": 2, "NH": 1, "unknown": 3},
            "hispanic_in_race_list": 2,
            "values_2024_only": {"Hispanic or Latino": 2, "Middle Eastern or North African": 1}})
        self.assertEqual(st["by_source"]["B"], {
            "records": 4, "convention": {"1997": 2, "undetermined": 2},
            "hispanic": {"H": 1, "NH": 1, "unknown": 2},
            "hispanic_in_race_list": 0, "values_2024_only": {}})

    def test_pairs(self):
        rep, _ = run()
        allp = rep["standards"]["pairs"]["exact"]["all"]
        self.assertEqual(allp, {
            "pairs": 5,
            "hispanic": {"disagree": 1, "uninformative": 4},
            "race_2024": {"agree": 3, "disagree": 1, "uninformative": 1},
            "conventions": {"1997 | 1997": 1, "1997 | contradictory": 1,
                            "1997 | undetermined": 1, "2024 | undetermined": 1,
                            "both | undetermined": 1},
            "implied_nh_vs_stated": {}})
        self.assertEqual(sorted(rep["standards"]["pairs"]["exact"]["by_source_pair"]), ["A | B"])
        self.assertEqual(rep["standards"]["persons_hispanic_conflict"],
                         {"exact": 1, "with_rules": 1})

    def test_declared(self):
        rep, _ = run({"A": "2024"})
        st = rep["standards"]
        self.assertEqual(st["declared"], {"A": "2024"})
        self.assertEqual(st["by_source"]["A"]["convention"],
                         {"1997": 1, "2024": 1, "both": 1, "contradictory": 1,
                          "declared_2024": 1, "no_value": 1})
        self.assertEqual(st["by_source"]["A"]["hispanic"],
                         {"H": 2, "NH": 1, "NH_implied": 1, "unknown": 2})
        allp = st["pairs"]["exact"]["all"]
        self.assertEqual(allp["hispanic"], {"agree": 1, "disagree": 1, "uninformative": 3})
        self.assertEqual(allp["implied_nh_vs_stated"], {"NH": 1})
        self.assertEqual(allp["conventions"]["1997 | declared_2024"], 1)
        self.assertEqual(st["persons_hispanic_conflict"]["exact"], 1)

    def test_declaring_does_not_change_the_1997_sections(self):
        a, _ = run()
        b, _ = run({"A": "2024", "B": "1997"})
        for key in a:
            if key != "standards":
                self.assertEqual(a[key], b[key], key)

    def test_cohort(self):
        _, rows = run()
        self.assertEqual(tuple(rows[0]), core.COHORT_FIELDS)
        got = [(r["records"], r["hispanic"], r["hispanic_conflict"], r["race_standard"])
               for r in rows]
        self.assertEqual(got, [
            ("A:a1;A:a5;B:b1", "conflict", 1, "1997;contradictory"),
            ("A:a2;B:b2", "H", 0, "2024;undetermined"),
            ("A:a3;B:b3", "NH", 0, "1997;undetermined"),
            ("A:a4;B:b4", "H", 0, "both;undetermined"),
            ("A:a6", "", 0, "no_value")])
        _, rows = run({"A": "2024"})
        self.assertEqual((rows[2]["hispanic"], rows[2]["race_standard"]),
                         ("NH", "1997;declared_2024"))

    def test_no_record_ids_in_report(self):
        rep, _ = run({"A": "2024"})
        text = json.dumps(rep)
        for r in RECORDS:
            self.assertNotIn('"%s"' % r["id"], text)

    def test_bad_declarations(self):
        with self.assertRaises(ValueError):
            run({"A": "2020"})
        with self.assertRaises(ValueError):
            core.parse_declared("A")
        with self.assertRaises(ValueError):
            core.parse_declared("=2024")
        self.assertEqual(core.parse_declared(""), {})
        self.assertEqual(core.parse_declared("CCDI-DCC=2024, B=1997"),
                         {"CCDI-DCC": "2024", "B": "1997"})


class Snapshot(unittest.TestCase):
    def test_ccdi_declared(self):
        tmp = tempfile.mkdtemp()
        try:
            raw = os.path.join(tmp, "raw")
            test_ccdi.make_snapshot(raw)
            plain, _ = ccdi.check(raw, ("exact",))
            self.assertEqual(plain["linkcheck"]["standards"]["by_source"]["A"]["convention"],
                             {"no_value": 1, "undetermined": 1})
            declared, _ = ccdi.check(raw, ("exact",), (), {"A": "2024"})
            st = declared["linkcheck"]["standards"]
            self.assertEqual(st["by_source"]["A"]["convention"],
                             {"declared_2024": 1, "no_value": 1})
            self.assertEqual(st["by_source"]["A"]["hispanic"], {"NH_implied": 1, "unknown": 1})
            self.assertEqual(st["pairs"]["exact"]["all"]["implied_nh_vs_stated"], {})
            out = os.path.join(tmp, "r.json")
            self.assertEqual(ccdi.main(["--raw", raw, "--out", out, "--declare", "A=2024"]), 0)
            with open(out, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["linkcheck"]["standards"]["declared"],
                                 {"A": "2024"})
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
