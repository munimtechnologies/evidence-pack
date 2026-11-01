# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.meps_geo (no network)."""
import json
import os
import tempfile
import unittest

from meps import meps_geo as g

NAV = "<div>Home</div><div>Data and Publications</div>"
PAGE_569 = ("<html><body>" + NAV + "<h1>Bone Density Scan</h1><p>Figure 7. Percentage by region and MSA</p>"
            "<p>Non-MSA 43.3</p><p>Rural residence</p></body></html>")
PAGE_549 = "<html><body>" + NAV + "<p>2020 MEPS internal data file with MSA variables</p></body></html>"
PAGE_OTHER = "<html><body>" + NAV + "<p>Total expenses by age</p></body></html>"
CB_PRESENT = ("<html><body><p>MEPS HC-155 2012 FULL YEAR CONSOLIDATED DATA CODEBOOK</p>"
              "<table><tr><td>0</td><td>NON-MSA</td><td>4,624</td></tr></table></body></html>")
CB_ABSENT = "<html><body><p>MEPS HC 243</p><p>2022 FULL YEAR CONSOLIDATED DATA CODEBOOK</p></body></html>"

CSV = ("number,year,year_source,status,cls,n_ids,file_ids,markers,section_chars,in_listing,url\n"
       "569,2025,page,ok,PUF,1,H243,,304,True,u\n"
       "549,2024,page,ok,NONPUBLIC,1,H224,internal,200,True,u\n"
       "100,2005,page,ok,PUF,1,H70,,100,True,u\n"
       "101,2005,page,ok,IC,0,,,100,True,u\n"
       "102,2010,page,ok,NOID,0,,,100,True,u\n")


class TestParts(unittest.TestCase):
    def test_html_lines(self):
        self.assertEqual(g.html_lines("<p>a  b</p><script>x</script><div>c</div>"), ["a b", "c"])

    def test_anchor(self):
        self.assertEqual(g.anchor("H243"), "post")
        self.assertEqual(g.anchor("H155 H243"), "post")
        self.assertEqual(g.anchor("H155 H147"), "pre")
        self.assertEqual(g.anchor("H163"), "post")
        self.assertEqual(g.anchor("H160A H2010"), "none")
        self.assertEqual(g.anchor(""), "none")
        self.assertEqual(g.fyc_years("H105 H243 H243A"), [2006, 2022])

    def test_fyc_map(self):
        self.assertEqual(g.FYC["H163"], 2013)
        self.assertEqual(len(set(g.FYC.values())), len(g.FYC))
        self.assertEqual(sorted(g.FYC.values()), list(range(1996, 2025)))

    def test_hits(self):
        lines = ["by MSA status", "Non-MSA 43.3", "nonmetropolitan areas", "MSAT score", "Rural", "urbanization"]
        self.assertEqual(g.hits(lines, g.MSA_RX), ["by MSA status", "Non-MSA 43.3", "nonmetropolitan areas"])
        self.assertEqual(g.hits(lines, g.UR_RX), ["Rural"])

    def test_boilerplate(self):
        bp = g.boilerplate([["nav", "a"], ["nav", "b"], ["nav", "c"]])
        self.assertEqual(bp, {"nav"})
        self.assertEqual(g.boilerplate([]), set())

    def test_codebook_status(self):
        self.assertEqual(g.codebook_status(CB_PRESENT), "present")
        self.assertEqual(g.codebook_status(CB_ABSENT), "absent")
        self.assertEqual(g.codebook_status("<p>Error</p>"), "unknown")

    def test_fetch_retries(self):
        calls = []

        def get(url):
            calls.append(url)
            return 500, ""
        self.assertEqual(g.fetch("u", get=get, pause=lambda s: None), ("http500", ""))
        self.assertEqual(len(calls), 3)
        self.assertEqual(g.fetch("u", get=lambda u: (404, ""), pause=lambda s: None), ("404", ""))


class TestRun(unittest.TestCase):
    def fake_get(self, url):
        if "codebook" in url:
            if "MSA11" in url or "MSA12" in url:
                return 200, CB_PRESENT
            return 200, CB_ABSENT
        if "st569/" in url:
            return 200, PAGE_569
        if "st549/" in url:
            return 200, PAGE_549
        if "st102/" in url:
            return 404, ""
        return 200, PAGE_OTHER

    def test_run(self):
        d = tempfile.mkdtemp()
        out = g.run(d, get=self.fake_get, pause=lambda s: None, delay=0, briefs_text=CSV)
        self.assertIsNone(out["error"])
        self.assertEqual(out["n_hc_briefs"], 4)
        self.assertEqual(out["n_fetched"], 3)
        self.assertEqual(out["codebook"]["2012"]["status"], "present")
        self.assertEqual(out["codebook"]["2013"]["status"], "absent")
        gr = out["grades"]
        self.assertEqual(gr["P2"]["grade"], "held")
        self.assertEqual(gr["P3"]["grade"], "held")
        self.assertEqual(gr["P4"]["grade"], "untestable")
        self.assertEqual(gr["P1_candidates"], [569])
        with open(os.path.join(d, "geo-briefs.csv"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("569,2025,PUF,H243,2022,post,ok,2,1,", text)
        with open(os.path.join(d, "snippets.jsonl"), encoding="utf-8") as f:
            sn = [json.loads(ln) for ln in f]
        self.assertEqual([s["number"] for s in sn], [569, 549])
        self.assertNotIn("Home", json.dumps(sn))

    def test_grade_p3_failed_and_p4(self):
        rows = []
        for i in range(10):
            rows.append({"number": 1000 + i, "cls": "PUF", "status": "ok", "anchor": "post",
                         "msa_hits": 1 if i < 2 else 0})
            rows.append({"number": 2000 + i, "cls": "PUF", "status": "ok", "anchor": "pre",
                         "msa_hits": 1 if i < 5 else 0})
        cb = {y: {"status": "absent"} for y in range(2011, 2024)}
        cb[2011] = {"status": "present"}
        gr = g.grade(rows, cb)
        self.assertEqual(gr["P3"]["grade"], "failed")
        self.assertEqual(gr["P4"]["grade"], "held")
        self.assertEqual(gr["P4"]["share_post"], 0.2)
        self.assertEqual(gr["P2"]["grade"], "untestable")
        self.assertEqual(gr["P1_candidates"], [1000, 1001])


if __name__ == "__main__":
    unittest.main()
