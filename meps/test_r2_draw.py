# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r2_draw (no network; a fake beacon)."""
import json
import os
import tempfile
import unittest

from meps import r2_draw as d

HDR = "number,year,year_source,status,cls,n_ids,file_ids,markers,section_chars,in_listing,url\n"
ROWS = [
    "491,2016,page,ok,PUF,1,H163,,120,True,u",
    "490,2015,page,ok,PUF,1,H163,,120,True,u",      # too early
    "502,2017,page,ok,PUF,1,H175,,276,True,u",      # not an FYC file
    "505,2017,page,ok,PUF,2,H174 H178A,,183,True,u",  # two files
    "508,2018,page,ok,NONPUBLIC,2,H171 H181,restricted,385,True,u",
    "521,2019,page,ok,PUF,1,H192,,125,True,u",
    "533,2021,page,ok,PUF,1,H209,,125,True,u",
    "540,2022,page,ok,PUF,1,H216,,120,True,u",
    "554,2024,page,ok,PUF,1,H233,,409,True,u",
    "558,2024,page,ok,PUF,1,H233,,416,True,u",
    "569,2025,page,ok,PUF,1,H243,,304,True,u",      # excluded (R1)
    "570,2025,page,error,PUF,1,H243,,0,True,u",     # status not ok
]
OV = "00000000000000FF" + "AB" * 56


def rows():
    import csv
    import io
    return list(csv.DictReader(io.StringIO(HDR + "\n".join(ROWS) + "\n")))


def pulse(ts=d.PULSE_ISO, ov=OV):
    return {"pulse": {"uri": "u", "chainIndex": 2, "pulseIndex": 1, "timeStamp": ts, "outputValue": ov}}


class TestDraw(unittest.TestCase):
    def test_eligible(self):
        el = d.eligible(rows())
        self.assertEqual([n for n, _ in el], [491, 521, 533, 540, 554, 558])
        self.assertEqual(dict(el)[554], "H233")

    def test_fyc(self):
        self.assertEqual(len(d.FYC), 12)
        self.assertEqual(d.FYC["H243"], 2022)
        self.assertEqual(d.PULSE_MS, 1793570400000 + 12 * 3600 * 1000)

    def test_seed(self):
        self.assertEqual(d.seed_from(OV), 255)
        with self.assertRaises(ValueError):
            d.seed_from("ABC")

    def test_draw(self):
        nums = [491, 521, 533, 540, 554, 558, 493]
        a = d.draw(nums, 255)
        self.assertEqual(len(a), 5)
        self.assertEqual(len(set(a)), 5)
        self.assertTrue(set(a) <= set(nums))
        self.assertEqual(a, d.draw(list(reversed(nums)), 255))

    def test_fetch_waits_for_exact_pulse(self):
        seq = [pulse(ts="2026-11-02T09:59:00.000Z"), RuntimeError("down"), pulse()]
        waits = []

        def get(url):
            self.assertIn(str(d.PULSE_MS), url)
            v = seq.pop(0)
            if isinstance(v, Exception):
                raise v
            return v
        p = d.fetch_pulse(get=get, pause=waits.append, tries=5, wait=7)
        self.assertEqual(p["timeStamp"], d.PULSE_ISO)
        self.assertEqual(waits, [7, 7])

    def test_fetch_gives_up(self):
        with self.assertRaises(RuntimeError):
            d.fetch_pulse(get=lambda u: pulse(ts="x"), pause=lambda s: None, tries=3)

    def test_main(self):
        tmp = tempfile.mkdtemp()
        b = os.path.join(tmp, "briefs.csv")
        with open(b, "w", newline="", encoding="utf-8") as f:
            f.write(HDR + "\n".join(ROWS) + "\n")
        rc = d.main(["--briefs", b, "--out-dir", tmp], get=lambda u: pulse(), pause=lambda s: None)
        self.assertEqual(rc, 0)
        with open(os.path.join(tmp, "r2-draw.json")) as f:
            out = json.load(f)
        self.assertEqual(out["n_eligible"], 6)
        self.assertEqual(out["seed"], 255)
        self.assertEqual(len(out["sample"]), 5)
        self.assertEqual([s["order"] for s in out["sample"]], [1, 2, 3, 4, 5])
        self.assertIsNone(out["error"])


if __name__ == "__main__":
    unittest.main()
