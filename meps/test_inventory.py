# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.inventory (synthetic HTML; no network)."""
import json
import os
import tempfile
import unittest

from meps import inventory as v

HEAD = ('<table><tr><th><a href="download_data_files_codebook.jsp?PUFId=H243&sortBy=Name">Name</a></th>'
        '<th>Start</th><th>End</th><th>Description</th></tr>')
ROWF = ('<tr><td><a href="download_data_files_codebook.jsp?PUFId=H243&varName=%s">%s</a></td>'
        '<td>%d</td><td>%d</td><td>%s</td></tr>')


def page(rows):
    body = "".join(ROWF % (n, n, i * 2 + 1, i * 2 + 2, d) for i, (n, d) in enumerate(rows))
    return "<html><body>" + HEAD + body + "</table></body></html>"


def rec(name, desc=""):
    return {"name": name, "start": None, "end": None, "description": desc}


class TestParse(unittest.TestCase):
    def test_rows(self):
        p = page([("ACCELI42", "PERS ELIGIBLE FOR ACCESS SUPPLEMENT-R4/2"), ("MSA12", "MSA FOR 12/31/12"),
                  ("ACCELI42", "dup"), ("ABC", "A &amp; <b>B</b>")])
        out = v.parse(p)
        self.assertEqual([r["name"] for r in out], ["ACCELI42", "MSA12", "ABC"])
        self.assertEqual(out[0]["start"], "1")
        self.assertEqual(out[0]["end"], "2")
        self.assertEqual(out[0]["description"], "PERS ELIGIBLE FOR ACCESS SUPPLEMENT-R4/2")
        self.assertEqual(out[2]["description"], "A & B")

    def test_fallback(self):
        out = v.parse('<a href="?varName=abc">abc</a> <a href="?varName=abc">x</a> varName=DEF')
        self.assertEqual([r["name"] for r in out], ["ABC", "DEF"])
        self.assertEqual(out[0]["description"], "")

    def test_rules(self):
        self.assertTrue(v.is_msa(rec("MSA12")))
        self.assertTrue(v.is_msa(rec("X", "METROPOLITAN STATISTICAL AREA")))
        self.assertTrue(v.is_msa(rec("X", "core-based msa indicator")))
        self.assertFalse(v.is_msa(rec("X", "STATEMENT")))
        self.assertTrue(v.is_geo(rec("X", "STATE OF RESIDENCE")))
        self.assertFalse(v.is_geo(rec("X", "STATEMENT RECEIVED")))
        self.assertFalse(v.is_geo(rec("REGION12", "CENSUS REGION AS OF 12/31/12")))

    def test_controls(self):
        c = v.controls("H155", {"PERWT12F", "REGION12", "VARSTR"})
        self.assertEqual(c, {"PERWT12F": True, "REGION12": True, "VARSTR": True, "VARPSU": False})
        self.assertIn("PERWT22F", v.controls("H243", set()))
        self.assertEqual(len(v.FILES), 14)


class TestGateGrade(unittest.TestCase):
    def test_gate(self):
        recs = [rec("V%d" % i) for i in range(1416)] + [rec(h) for h in v.H243_HAS]
        self.assertTrue(v.gate({"H243": recs})["passed"])
        self.assertFalse(v.gate({"H243": recs + [rec("PSAQWT22F")]})["passed"])
        self.assertFalse(v.gate({})["passed"])

    def inv(self):
        return {fid: ([rec("MSA%02d" % (y % 100))] if y < 2013 else [rec("REGION%02d" % (y % 100))])
                for fid, y in v.FILES.items()}

    def test_grade_held(self):
        g = v.grade(self.inv())
        self.assertEqual(g["P1"]["grade"], "held")
        self.assertEqual(g["P2"]["grade"], "held")

    def test_grade_failed(self):
        inv = self.inv()
        inv["H233"].append(rec("X", "MSA FOR 12/31/21"))
        g = v.grade(inv)
        self.assertEqual(g["P1"]["grade"], "failed")
        self.assertEqual(g["P1"]["with_msa"], ["H233"])
        inv = self.inv()
        del inv["H256"]
        del inv["H147"]
        g = v.grade(inv)
        self.assertEqual(g["P1"]["grade"], "failed")
        self.assertEqual(g["P2"]["grade"], "failed")


class TestBuild(unittest.TestCase):
    def fake(self, robots):
        def get(url):
            if url == v.ROBOTS:
                return robots
            return page([("REGION12", "CENSUS REGION")])
        return get

    def test_robots_allow(self):
        waits = []
        inv, err = v.build(get=self.fake("User-agent: *\nDisallow: /mepsweb/data_files/pufs/\n"),
                           pause=waits.append)
        self.assertEqual(len(inv), 14)
        self.assertEqual(err, {})
        self.assertEqual(waits, [10] * 13)

    def test_robots_block(self):
        inv, err = v.build(get=self.fake("User-agent: *\nDisallow: /mepsweb/data_stats/\n"),
                           pause=lambda s: None)
        self.assertEqual(inv, {})
        self.assertEqual(len(err), 14)

    def test_main(self):
        tmp = tempfile.mkdtemp()
        rc = v.main(["--out-dir", tmp], get=self.fake(""), pause=lambda s: None, allowed=lambda u: True)
        self.assertEqual(rc, 0)
        with open(os.path.join(tmp, "inventory.json")) as f:
            out = json.load(f)
        self.assertEqual(len(out["n_by_file"]), 14)
        self.assertFalse(out["gate"]["passed"])
        self.assertTrue(os.path.exists(os.path.join(tmp, "inventory", "H243.csv")))
        self.assertTrue(os.path.exists(os.path.join(tmp, "geo-candidates.csv")))
        self.assertEqual(out["geo_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
