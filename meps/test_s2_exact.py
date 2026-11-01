# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps/s2_exact.py (no network, no pandas, no MEPS data)."""
import csv
import io
import unittest

from meps import s2_exact as s2


def P(**kw):
    base = dict(DUPERSID="x", PERWT22F=1.0, TOTEXP22=0.0, AGE22X=-1, AGE42X=-1, AGE31X=-1, SEX=1,
                INSCOV22=1, INSURC22=1, POVCAT22=5, REGION22=2, REGION42=2, REGION31=2, MARRY22X=1,
                MARRY42X=1, MARRY31X=1, RACETHX=2, RACEV1X=1, EDUCYR=12, EMPST53=1, EMPST42=1, EMPST31=1)
    base.update(kw)
    return base


HEADER = ["Year", "stat_group", "stat_var", "stat_label", "row_group", "row_var", "row_label", "rowLevels",
          "col_group", "col_var", "col_label", "colLevels", "value", "se", "value_rd", "se_rd", "asterisk",
          "Percent", "sample_size", "caption"]


def dy(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for stat, rv, rl, cv, cl, value, ss in rows:
        w.writerow(["2022", "g", stat, "l", "rg", rv, "rlab", rl, "cg", cv, "clab", cl, value, "1", "", "", "",
                    "FALSE", ss, "cap"])
    return buf.getvalue()


class TestBasics(unittest.TestCase):
    def test_age(self):
        self.assertEqual(s2.age(P(AGE42X=7, AGE31X=6)), 7)
        self.assertIsNone(s2.age(P()))
        self.assertEqual(s2.age(P(AGE22X=0)), 0)

    def test_levels(self):
        self.assertTrue(s2.LEVELS[("insurance", "65+, No medicare")][0][1](P(INSURC22=8)))
        self.assertFalse(s2.LEVELS[("insurance", "65+, No medicare")][0][1](P(INSURC22=6)))
        self.assertTrue(s2.LEVELS[("race", s2.RACE4)][0][1](P(RACETHX=5, RACEV1X=6)))
        self.assertFalse(s2.LEVELS[("race", s2.RACE4)][0][1](P(RACETHX=1, RACEV1X=3)))
        lths = s2.LEVELS[("education", "Less than high school")][0][1]
        self.assertTrue(lths(P(AGE22X=30, EDUCYR=11)))
        self.assertFalse(lths(P(AGE22X=17, EDUCYR=11)))
        self.assertFalse(lths(P(AGE22X=30, EDUCYR=-1)))
        self.assertTrue(s2.LEVELS[("agegrps", "5-17")][0][1](P(AGE22X=5)))
        self.assertFalse(s2.LEVELS[("agegrps", "5-17")][0][1](P(AGE22X=18)))
        emp = s2.LEVELS[("employed", s2.INAPP16)][0][1]
        self.assertTrue(emp(P(AGE22X=10, EMPST53=-1, EMPST42=-1, EMPST31=-1)))
        self.assertFalse(emp(P(AGE22X=10, EMPST53=-1, EMPST42=2, EMPST31=-1)))

    def test_stats(self):
        persons = [P(PERWT22F=2.0, TOTEXP22=100.0), P(PERWT22F=1.0, TOTEXP22=400.0),
                   P(PERWT22F=1.0, TOTEXP22=0.0), P(PERWT22F=0.0, TOTEXP22=50.0)]
        s = s2.stats(persons, lambda p: True)
        self.assertEqual(s["n"], 3)
        self.assertEqual(s["n_exp"], 2)
        self.assertAlmostEqual(s["mean"], 200.0)

    def test_parse_published(self):
        text = dy([("meanEXP", "sex", "Male", "insurance", "65+, No medicare", "11537.5", "60"),
                   ("medEXP", "sex", "Male", "insurance", "65+, No medicare", "NA", "60.0")])
        pub = s2.parse_published(text)
        k = ("meanEXP", "sex", "Male", "insurance", "65+, No medicare")
        self.assertEqual(pub[k], {"value": 11537.5, "sample_size": 60})
        self.assertIsNone(pub[("medEXP",) + k[1:]]["value"])
        self.assertEqual(pub[("medEXP",) + k[1:]]["sample_size"], 60)


class TestCell(unittest.TestCase):
    def setUp(self):
        self.persons = [P(REGION22=-1, REGION42=1, INSCOV22=3, TOTEXP22=10.0),
                        P(REGION22=1, INSCOV22=3, TOTEXP22=0.0),
                        P(REGION22=-1, REGION42=1, INSCOV22=1, TOTEXP22=5.0)]
        self.cell = ("C09", "region", "Northeast", "insurance", "Uninsured, all ages", 91)

    def pub(self, ss, mean=10.0):
        k = ("region", "Northeast", "insurance", "Uninsured, all ages")
        return {("meanEXP",) + k: {"value": mean, "sample_size": ss},
                ("pctEXP",) + k: {"value": 50.0, "sample_size": ss}}

    def test_variant_b_passes(self):
        r = s2.evaluate_cell(self.persons, self.cell, self.pub(2))
        self.assertEqual(r["tried"], [{"variant": "AA", "n": 1}, {"variant": "BA", "n": 2}])
        self.assertEqual(r["variant"], "BA")
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["n_exp"], 1)
        self.assertAlmostEqual(r["mean"], 10.0)
        self.assertTrue(r["mean_ok"])
        self.assertTrue(r["passed"])
        self.assertEqual(r["pct_share"], 0.5)
        self.assertIsNone(r["published_median"])

    def test_no_variant_matches(self):
        r = s2.evaluate_cell(self.persons, self.cell, self.pub(5))
        self.assertFalse(r["passed"])
        self.assertIsNone(r["variant"])
        self.assertEqual(r["tried"], [{"variant": "AA", "n": 1}, {"variant": "BA", "n": 2}])

    def test_mean_control_fails(self):
        r = s2.evaluate_cell(self.persons, self.cell, self.pub(2, mean=20.0))
        self.assertEqual(r["variant"], "BA")
        self.assertFalse(r["mean_ok"])
        self.assertFalse(r["passed"])


def R(cid, passed, n, n_exp, pct, med=None):
    return {"cid": cid, "passed": passed, "n": n, "n_exp": n_exp, "pct_share": pct,
            "published_mean": 1.0, "published_median": med}


class TestGrade(unittest.TestCase):
    def base(self):
        rs = [R("C01", True, 60, 50, 0.83, med=5.0)]
        rs += [R("C%02d" % i, True, 100, 40, 0.40) for i in range(2, 13)]
        rs += [R("C13", False, None, None, 0.5), R("C14", False, None, None, 0.5)]
        return rs

    def test_all_held(self):
        g = s2.grade(self.base())
        self.assertEqual(g["passed_cells"], 12)
        self.assertEqual(g["P1"]["grade"], "held")
        self.assertEqual(g["P1"]["value"], 1.0)
        self.assertEqual(g["P2"]["grade"], "held")
        self.assertEqual(g["P3"]["grade"], "held")
        self.assertEqual(g["P3"]["n_exp"], 50)
        self.assertEqual(g["P4"]["grade"], "held")
        self.assertEqual(g["estimates_below_60"], 13)

    def test_p1_fails(self):
        rs = self.base()
        rs[1]["n_exp"] = 61
        g = s2.grade(rs)
        self.assertEqual(g["P1"]["grade"], "failed")
        self.assertEqual(g["P1"]["below_60"], 11)
        self.assertEqual(g["estimates_below_60"], 12)

    def test_few_pass(self):
        rs = self.base()
        for r in rs[3:12]:
            r["passed"] = False
        g = s2.grade(rs)
        self.assertEqual(g["passed_cells"], 3)
        self.assertEqual(g["P1"]["grade"], "untestable")
        self.assertEqual(g["P2"]["grade"], "failed")
        self.assertEqual(g["P4"]["grade"], "untestable")
        self.assertEqual(g["P3"]["grade"], "held")


if __name__ == "__main__":
    unittest.main()
