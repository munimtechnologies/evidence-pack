# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.sumtab_check (no network)."""
import json
import os
import tempfile
import unittest

from meps import sumtab_check as sc

HEADER = ("Year,stat_group,stat_var,stat_label,row_group,row_var,row_label,rowLevels,col_group,col_var,"
          "col_label,colLevels,value,se,value_rd,se_rd,asterisk,Percent,sample_size,caption")


def row(stat, level, value, ss):
    return ",".join(["2022", "g", stat, "l", "", "agegrps", "Age", level, "", "ind", "", "Total",
                     value, "1", "", "", "", "FALSE", ss, '"Caption, with comma"'])


# Cell A: everything carries n (900); B: pctEXP ~100%, so excluded from the
# expenditure comparison; C: n 70, 60% with an expense, meanEXP published (P5 example);
# D: expenditure rows carry a smaller count (340), as correct code would.
TABLE = "\n".join([
    HEADER,
    row("totPOP", "18-64", "200000", "900"),
    row("pctEXP", "18-64", "80.0", "900"),
    row("meanEXP", "18-64", "7000", "900"),
    row("medEXP", "18-64", "2000", "900"),
    row("totPOP", "65+", "50000", "300"),
    row("pctEXP", "65+", "99.95", "300"),
    row("totPOP", "Under 5", "20000", "70"),
    row("pctEXP", "Under 5", "60.0", "70"),
    row("meanEXP", "Under 5", "1500", "70"),
    row("medEXP", "Under 5", "", "70"),
    row("totPOP", "5-17", "60000", "400"),
    row("pctEXP", "5-17", "85.0", "400"),
    row("meanEXP", "5-17", "2500", "340"),
    row("medEXP", "5-17", "900", "340"),
    row("totEXP", "5-17", "150000", "400"),
]) + "\n"


def mk(cells, equal, low=3):
    part = {"cells": cells, "equal": equal}
    return {"meanEXP": dict(part), "medEXP": dict(part), "control": dict(part), "low_n_published": low}


class ScanTests(unittest.TestCase):
    def test_scan(self):
        cells, stats, n = sc.scan(TABLE)
        self.assertEqual(n, 15)
        self.assertEqual(len(cells), 4)
        self.assertIn("totEXP", stats)
        key = ("", "agegrps", "Under 5", "", "ind", "Total")
        self.assertEqual(cells[key]["medEXP"][0], {"70"})
        self.assertEqual(cells[key]["medEXP"][1], [None])

    def test_helpers(self):
        self.assertIsNone(sc.to_float(""))
        self.assertIsNone(sc.to_float("nan"))
        self.assertEqual(sc._one_int({"1077"}), 1077)
        self.assertIsNone(sc._one_int({"1", "2"}))
        self.assertIsNone(sc._one_int(set()))
        self.assertEqual(sc._one_value([None, 3.0, 3.0]), 3.0)
        self.assertIsNone(sc._one_value([1.0, 2.0]))


class CompareTests(unittest.TestCase):
    def test_compare(self):
        cells, _, _ = sc.scan(TABLE)
        res, ex = sc.compare(cells)
        self.assertEqual(res["pct_scale"], 100.0)
        self.assertEqual(res["control"]["cells"], 4)
        self.assertEqual(res["control"]["equal"], 4)
        for s in ("meanEXP", "medEXP"):
            self.assertEqual((res[s]["cells"], res[s]["equal"], res[s]["less"], res[s]["greater"]), (3, 2, 1, 0))
            self.assertEqual(res[s]["share_equal"], 0.6667)
        self.assertEqual(res["low_n_published"], 1)
        self.assertEqual(ex[0]["rowLevels"], "Under 5")
        self.assertEqual(ex[0]["stat_var"], "meanEXP")
        self.assertEqual(ex[0]["est_persons_with_expense"], 42.0)

    def test_fraction_scale(self):
        t = "\n".join([HEADER, row("totPOP", "x", "1", "100"), row("pctEXP", "x", "0.5", "100"),
                       row("meanEXP", "x", "10", "100")])
        res, ex = sc.compare(sc.scan(t)[0])
        self.assertEqual(res["pct_scale"], 1.0)
        self.assertEqual(res["meanEXP"]["equal"], 1)
        self.assertEqual(ex, [])


class GradeTests(unittest.TestCase):
    def test_held(self):
        g = sc.grade({2021: mk(150, 150), 2022: mk(200, 199)}, 2022)
        self.assertEqual(g["P1"], {"value": 0.995, "cells": 200, "grade": "held"})
        self.assertEqual(g["P2"]["grade"], "held")
        self.assertEqual(g["P3"]["grade"], "untestable")
        self.assertEqual(g["P4"]["grade"], "held")
        self.assertEqual(g["P5"], {"value": 3, "grade": "held"})

    def test_failed(self):
        g = sc.grade({2022: mk(200, 150, low=0)}, 2022)
        self.assertEqual(g["P1"], {"value": 0.75, "cells": 200, "grade": "failed"})
        self.assertEqual(g["P5"]["grade"], "not graded")

    def test_untestable(self):
        g = sc.grade({2022: mk(99, 99)}, 2022)
        self.assertEqual(g["P1"]["grade"], "untestable")
        self.assertEqual(g["P5"]["grade"], "not graded")
        self.assertEqual(sc.grade({}, None)["P4"]["grade"], "untestable")

    def test_p3(self):
        per = {y: mk(100, 100) for y in range(2000, 2020)}
        per[2005] = mk(100, 98)
        g = sc.grade(per, 2019)
        self.assertEqual(g["P3"], {"years": 20, "years_below": [2005], "grade": "failed"})
        per[2005] = mk(100, 99)
        self.assertEqual(sc.grade(per, 2019)["P3"]["grade"], "held")


class CodeTests(unittest.TestCase):
    def test_code_lines(self):
        text = ('x <- 1\n  mutate(sample_size = ifelse(value %in% c("meanEXP", "medEXP"), n_exp, n)) %>%\n'
                '  suppress = (RSE > 0.5),\n')
        lines, found = sc.code_lines(text)
        self.assertEqual([i for i, _ in lines], [2, 3])
        self.assertTrue(found)
        self.assertFalse(sc.code_lines('ifelse(stat_var %in% c("meanEXP","medEXP"), n_exp, n)')[1])

    def test_lfs(self):
        self.assertTrue(sc.is_lfs(b"version https://git-lfs.github.com/spec/v1\noid sha256:x"))
        self.assertFalse(sc.is_lfs(b"Year,stat_group"))


class RunTests(unittest.TestCase):
    def test_run(self):
        sha = "abc123"
        pages = {
            sc.API + "/commits/main": json.dumps({"sha": sha}).encode(),
            sc.API + "/contents/" + sc.APP + "?ref=" + sha: json.dumps(
                [{"name": "DY2021.csv"}, {"name": "DY2022.csv"}, {"name": "README.md"}]).encode(),
            sc.RAW.format(sha=sha, path=sc.CODE): b'suppress = (RSE > 0.5),\nvalue %in% c("meanEXP","medEXP")\n',
            sc.RAW.format(sha=sha, path=sc.APP + "/DY2021.csv"): TABLE.encode(),
            sc.RAW.format(sha=sha, path=sc.APP + "/DY2022.csv"): b"version https://git-lfs.github.com/spec/v1\n",
            sc.MEDIA.format(sha=sha, path=sc.APP + "/DY2022.csv"): TABLE.encode(),
        }

        def get(url):
            return (200, pages[url]) if url in pages else (404, b"")

        with tempfile.TemporaryDirectory() as d:
            o = sc.run(d, get=get, pause=lambda s: None)
            self.assertEqual(o["sha"], sha)
            self.assertEqual(o["primary_year"], 2022)
            self.assertEqual([f["lfs"] for f in o["files"]], [False, True])
            self.assertTrue(o["code"]["tested_line_found"])
            self.assertEqual(o["code"]["n_lines"], 1)
            self.assertEqual(o["grades"]["P1"]["grade"], "untestable")
            for name in ("sumtab.json", "per-year.csv", "low-n-published.csv", "code-lines.txt"):
                self.assertTrue(os.path.exists(os.path.join(d, name)))
            with open(os.path.join(d, "low-n-published.csv"), encoding="utf-8") as f:
                self.assertEqual(len(f.read().strip().splitlines()), 3)

    def test_run_no_commit(self):
        with tempfile.TemporaryDirectory() as d:
            o = sc.run(d, get=lambda url: (500, b""), pause=lambda s: None)
            self.assertEqual(o["error"], "commit lookup http500")
            self.assertTrue(os.path.exists(os.path.join(d, "sumtab.json")))


if __name__ == "__main__":
    unittest.main()
