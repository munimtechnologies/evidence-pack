# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for census M9 (meps/m9echo.py). MV2 of Munim, Inc.; made by AI agents (Claude) in his name."""
import json
import os
import tempfile
import unittest

from meps import m9echo as m9

HL = ("In 2012, 7.2 percent of the population (22.5 million individuals) had out-of-pocket expenditures for "
      "medical care that were equal to or greater than $2,000.")
FD = ("In 2012, 67.2 percent of the population (22.5 million individuals) had out-of-pocket expenditures for "
      "medical care that were equal to or greater than $2,000. Nearly 4.8 million individuals (1.5 percent) paid "
      "$5,000 or more out of pocket for their medical care (figure 2).")
PAGE450 = ("<html><body><h2>Highlights</h2><ul><li>" + HL + "</li></ul><h2>Findings</h2><p>" + FD +
           "</p><h2>References</h2><p>In 2012, 9.9 percent of the population (1.0 million) x.</p></body></html>")
PAGE181 = ("<html><body><h2>Introduction</h2><p>Of those employees who worked where health insurance was offered, "
           "approximately 61.1 million were enrolled.</p><h2>Findings</h2><p>Among the 61.6 million private sector "
           "employees enrolled in employer-sponsored health insurance in 2005, 63.9 percent were enrolled in plans "
           "with a deductible (figure 1).</p></body></html>")
PAGE999 = "<html><body><p>About 48.0 million adults (1.5 percent) had a visit.</p></body></html>"


class TestPieces(unittest.TestCase):
    def test_edit_kind(self):
        self.assertEqual(m9.edit_kind("7.2", "67.2"), "extra digit")
        self.assertEqual(m9.edit_kind("27.36", "27.3"), "extra digit")
        self.assertEqual(m9.edit_kind("1.9", "0.9"), "substitution")
        self.assertEqual(m9.edit_kind("86.2", "89.2"), "substitution")
        self.assertEqual(m9.edit_kind("41.4", "14.4"), "swap")
        self.assertEqual(m9.edit_kind("7.2", "72"), "point")
        self.assertEqual(m9.edit_kind("12.5", "19.8"), "other")

    def test_edits(self):
        e = m9.edits("67.2")
        for s in ("7.2", "6.2", "76.2", "167.2", "67.25"):
            self.assertIn(s, e)
        for s in ("67.2", "67.", "067.2"):
            self.assertNotIn(s, e)
        self.assertIn("67.2", m9.edits("7.2"))
        self.assertNotIn("07.2", m9.edits("7.2"))

    def test_base_interval(self):
        lo, hi = m9.base_interval("22.5", "67.2")
        self.assertAlmostEqual(lo, 22.45 / 67.25 * 100)
        self.assertAlmostEqual(hi, 22.55 / 67.15 * 100)
        lo, hi = m9.base_interval("23", "7")
        self.assertAlmostEqual(lo, 300.0)
        self.assertAlmostEqual(hi, 23.5 / 6.5 * 100)

    def test_skeleton(self):
        t1, n1 = m9.skeleton(HL)
        t2, n2 = m9.skeleton(FD.split(" Nearly")[0])
        self.assertEqual(t1, t2)
        self.assertEqual(len(t1), 26)
        self.assertEqual(n1, ["2012", "7.2", "22.5", "2,000"])
        self.assertEqual(n2, ["2012", "67.2", "22.5", "2,000"])
        t3, n3 = m9.skeleton("Share 4.0% of adults (figure 1).")
        self.assertEqual(t3, ("share", "#", "percent", "of", "adults"))
        self.assertEqual(n3, ["4.0"])


class TestPairs(unittest.TestCase):
    def test_control_block(self):
        pairs, skipped = m9.find_pairs(FD)
        self.assertEqual(skipped, 0)
        self.assertEqual([(p["form"], p["pct"], p["count"], p["pop"]) for p in pairs],
                         [("A", "67.2", "22.5", True), ("B", "1.5", "4.8", False)])
        self.assertEqual(pairs[0]["flags"], ["population"])
        self.assertEqual(pairs[0]["repairs_p"], ["7.2"])
        self.assertIn("222.5", pairs[0]["repairs_n"])
        self.assertEqual(pairs[1]["flags"], [])
        self.assertEqual(pairs[1]["repairs_p"], [])

    def test_highlight_pair_fits(self):
        pairs, _ = m9.find_pairs(HL)
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["pop"])
        self.assertEqual(pairs[0]["flags"], [])

    def test_over_and_bounds(self):
        pairs, _ = m9.find_pairs("About 48.0 million adults (1.5 percent) had a visit.")
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["flags"], ["over"])
        self.assertEqual(m9.find_pairs("Some 42.1 percent of adults (more than 90 million) did.")[0], [])
        self.assertEqual(m9.find_pairs("It was $4.9 million (2.0 percent) of spending.")[0], [])

    def test_cross_sentence_skipped(self):
        pairs, skipped = m9.find_pairs("Some 12.0 percent. Of these, the group (5.0 million people) was small.")
        self.assertEqual(pairs, [])
        self.assertEqual(skipped, 1)

    def test_population_tail(self):
        pairs, _ = m9.find_pairs("Some 4.8 million people (1.5 percent of the population) paid more.")
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["pop"])
        self.assertEqual(pairs[0]["flags"], [])
        pairs, _ = m9.find_pairs("Some 4.8 million people (1.5 percent of the population aged 65) paid more.")
        self.assertFalse(pairs[0]["pop"])


class TestEchoes(unittest.TestCase):
    def test_echo_rules(self):
        a = "The share of adults with any expense was 85.0 percent in the nation."
        b = "The share of adults with any expense was 86.0 percent in the nation (figure 1)."
        out = m9.echoes([(0, a), (2, b)])
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["a"], out[0]["b"], out[0]["edit"]), ("85.0", "86.0", "substitution"))
        self.assertEqual(m9.echoes([(0, a), (0, b)]), [])
        y1 = "In 2012, the mean expense per person was $4,500 for adults."
        y2 = "In 2013, the mean expense per person was $4,500 for adults."
        self.assertEqual(m9.echoes([(0, y1), (1, y2)]), [])
        two1 = "Men 12.5 percent and women 14.5 percent had a visit in the year."
        two2 = "Men 12.6 percent and women 14.6 percent had a visit in the year."
        self.assertEqual(m9.echoes([(0, two1), (1, two2)]), [])
        self.assertEqual(m9.echoes([(0, "Rate 1.5 here."), (1, "Rate 2.5 here.")]), [])


class TestPages(unittest.TestCase):
    def test_page450(self):
        res, st = m9.check_page(PAGE450)
        self.assertEqual(st["stopped"], 1)
        self.assertEqual([(p["pct"], p["count"], p["flags"]) for p in res["pairs"]],
                         [("7.2", "22.5", []), ("67.2", "22.5", ["population"]), ("1.5", "4.8", [])])
        self.assertEqual(len(res["echoes"]), 1)
        e = res["echoes"][0]
        self.assertEqual((e["block"], e["block2"], e["a"], e["b"], e["edit"]), (1, 3, "7.2", "67.2", "extra digit"))

    def test_page181_scope(self):
        res, _ = m9.check_page(PAGE181)
        self.assertEqual(res, {"pairs": [], "echoes": []})

    def test_summarise(self):
        results = {450: m9.check_page(PAGE450), 181: m9.check_page(PAGE181), 999: m9.check_page(PAGE999)}
        s, rows, flags = m9.summarise(results, {450: "2014", 181: "2007", 999: "2026"}, {}, fetch_min=3)
        self.assertEqual(s["pairs"], 4)
        self.assertEqual(s["pairs_population"], 2)
        self.assertEqual(s["pair_flags"], 1)
        self.assertEqual(s["pair_flag_kinds"], {"pair:over": 1})
        self.assertEqual(s["echo_flags"], 0)
        self.assertEqual(s["controls"], {"pair_450": True, "echo_450": True, "neg_450_parsed": True,
                                         "neg_450_unflagged": True, "scope_181_flagged": False})
        self.assertTrue(s["gate"]["passed"])
        self.assertEqual(len(flags), 3)
        real = [f for f in flags if not f["control"]]
        self.assertEqual([(f["number"], f["check_rank"], f["in_sample"]) for f in real], [(999, 1, True)])
        s2, _, _ = m9.summarise(results, {}, {})
        self.assertFalse(s2["gate"]["passed"])


class TestMain(unittest.TestCase):
    def test_main_offline(self):
        pages = {"st450/": PAGE450, "st181/": PAGE181}

        def get(url):
            if url == m9.ROBOTS:
                return b"User-agent: *\nDisallow: /data_files/pufs/\n"
            for k, v in pages.items():
                if k in url:
                    return v.encode("utf-8")
            raise OSError("not found")

        with tempfile.TemporaryDirectory() as d:
            tables = os.path.join(d, "tables.csv")
            with open(tables, "w", encoding="utf-8") as f:
                f.write("number,year\n450,2014\n181,2007\n")
            out = os.path.join(d, "out")
            rc = m9.main(["--tables", tables, "--out-dir", out, "--delay", "0", "--fetch-min", "2"], get=get,
                         pause=lambda s: None)
            self.assertEqual(rc, 0)
            for name in ("m9-pairs.csv", "m9-flags.csv", "m9-summary.json"):
                self.assertTrue(os.path.exists(os.path.join(out, name)))
            with open(os.path.join(out, "m9-summary.json")) as f:
                s = json.load(f)
            self.assertEqual(s["fetched"], 2)
            self.assertTrue(s["gate"]["passed"])
            self.assertEqual(sorted(s["sha256"]), ["181", "450"])
            with open(os.path.join(out, "m9-pairs.csv"), encoding="utf-8") as f:
                self.assertEqual(len(f.read().strip().splitlines()), 4)


if __name__ == "__main__":
    unittest.main()
