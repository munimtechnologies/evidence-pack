# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r2rest (no network, no MEPS file)."""
import csv
import json
import os
import tempfile
import unittest
import zipfile

from meps import r2conc, r2rest


def _row(duid, fam, rp, w, pov, age, oop, exp):
    return {"DUID": duid, "CPSFAMID": fam, "FCRP1231": str(rp), "FAMWT15C": str(w), "POVCAT15": str(pov),
            "AGELAST": str(age), "TOTSLF15": str(oop), "TOTEXP15": str(exp)}


ROWS_507 = [
    _row("10001", "A", 1, 100.0, 1, 30, 50, 200),
    _row("10001", "A", 0, 100.0, 1, 5, 20, 0),
    _row("10001", "A", -1, 0.0, 1, 70, 999, 999),   # left before 12/31: not a member
    _row("10002", "A", 1, 300.0, 5, 40, 3000, 5000),
    _row("10002", "A", 0, 300.0, 5, 41, 0, 0),
    _row("10002", "B", 1, 200.0, 4, 22, 150, 150),
    _row("10003", "A", 1, 50.0, 3, 66, 10, 10),       # elderly member: family excluded
    _row("10004", "A", 1, 400.0, 2, 35, 0, 0),        # no expense: excluded from the figures
    _row("10005", "A", 1, 0.0, 2, 35, 5, 5),          # zero family weight
]


def _person(w, age, ins, x, **vals):
    svc, pay = r2rest.comp_names("13")
    v = {n: 0.0 for n in svc + pay}
    for k, val in vals.items():
        v[k + "13"] = float(val)
    return {"w": float(w), "age": age, "ins": ins, "x": float(x), "v": v}


class TestCells(unittest.TestCase):
    def test_507_cells(self):
        c = r2rest.BRIEFS[507]["cells"]
        self.assertEqual(len(c), 40)
        self.assertEqual(len({x[0] for x in c}), 40)
        self.assertEqual(sum(1 for x in c if x[2] == "median"), 10)
        self.assertEqual(sum(1 for x in c if x[2] == "dist"), 30)
        self.assertEqual((c[0][0], c[0][4]), ("F1-All", "451"))
        self.assertEqual((c[5][0], c[5][4]), ("F2-lt100-All", "25%"))
        self.assertEqual((c[19][0], c[19][4]), ("F2-gt2500-High", "22%"))
        self.assertEqual((c[20][0], c[20][4]), ("F3-All", "451"))
        self.assertEqual((c[25][0], c[25][4]), ("F4-All-lt100", "25%"))
        self.assertEqual((c[39][0], c[39][4]), ("F4-2A1C-gt2500", "19%"))

    def test_491_cells(self):
        c = r2rest.BRIEFS[491]["cells"]
        e = r2rest.BRIEFS[491]["extra"]
        self.assertEqual(len(c), 40)
        self.assertEqual(len(e), 20)
        self.assertEqual(len({x[0] for x in c + e}), 60)
        self.assertEqual((c[0][0], c[0][4]), ("F1-IP-Total", "27.9"))
        self.assertEqual((c[14][0], c[14][4]), ("F1-HHOTH-65plus", "8.5"))
        self.assertEqual((c[15][0], c[15][4]), ("F2-IP-AnyPriv", "24.1"))
        self.assertEqual((c[39][0], c[39][4]), ("F2-HHOTH-AnyPriv", "3.6"))
        self.assertEqual((e[0][0], e[0][4]), ("F2-HHOTH-PubOnly", "7.5"))
        self.assertEqual((e[12][0], e[12][4]), ("F3-OOP-lt65", "14.5"))
        self.assertEqual((e[19][0], e[19][4]), ("F3-OTH-65plus", "7.3"))

    def test_fields(self):
        f = r2rest.fields_491("13")
        self.assertEqual(len(f), 5 + 10 + 12)
        self.assertIn("ERTEXP13", f)
        self.assertIn("TOTOPU13", f)
        self.assertEqual(len(r2rest.fields_507()), 8)


class TestQuantiles(unittest.TestCase):
    def test_sas_interpolation(self):
        self.assertAlmostEqual(r2rest.wquantile_sas([(0, 1), (10, 2), (20, 1)], 0.5), 5.0)
        self.assertAlmostEqual(r2rest.wquantile_sas([(0, 1), (10, 1), (20, 1), (30, 1)], 0.5), 10.0)
        self.assertAlmostEqual(r2rest.wquantile_sas([(5, 3), (9, 1)], 0.5), 5.0)

    def test_lower(self):
        self.assertEqual(r2rest.wquantile_lower([(0, 1), (10, 2), (20, 1)], 0.5), 10)
        self.assertEqual(r2rest.wquantile_lower([(5, 3), (9, 1)], 0.5), 5)

    def test_band(self):
        self.assertEqual(r2rest.band(0), "lt100")
        self.assertEqual(r2rest.band(99.99), "lt100")
        self.assertEqual(r2rest.band(100), "100-2500")
        self.assertEqual(r2rest.band(2500), "100-2500")
        self.assertEqual(r2rest.band(2500.01), "gt2500")


class TestFamilies(unittest.TestCase):
    def test_build_and_estimate(self):
        fams, d = r2rest.build_families(ROWS_507)
        self.assertEqual(d["families"], 5)
        self.assertEqual(d["members_zero_famwt"], 1)
        self.assertEqual(d["keys_ref_not_1"], 0)
        by = {f["key"]: f for f in fams}
        self.assertEqual((by["10001A"]["oop"], by["10001A"]["exp"]), (70.0, 200.0))
        self.assertFalse(by["10001A"]["elderly"])
        self.assertEqual(r2rest.structure(by["10001A"]), "1A1C")
        self.assertEqual(r2rest.structure(by["10002A"]), "2A0C")
        self.assertEqual(r2rest.structure(by["10002B"]), "1A0C")
        self.assertTrue(by["10003A"]["elderly"])
        est, diag = r2rest.fam_estimates(fams)
        self.assertAlmostEqual(est[("median", ("inc", "All"))], 150.0)
        self.assertAlmostEqual(est[("median_lower", ("inc", "All"))], 150.0)
        self.assertAlmostEqual(est[("dist", ("inc", "All", "lt100"))], 100.0 / 6)
        self.assertAlmostEqual(est[("dist", ("inc", "All", "100-2500"))], 200.0 / 6)
        self.assertAlmostEqual(est[("dist", ("str", "All", "gt2500"))], 50.0)
        self.assertAlmostEqual(est[("median", ("inc", "Poor"))], 70.0)
        self.assertAlmostEqual(est[("median", ("inc", "High"))], 3000.0)
        self.assertAlmostEqual(est[("median", ("inc", "Middle"))], 150.0)
        self.assertNotIn(("median", ("inc", "Low")), est)
        self.assertAlmostEqual(est[("median", ("str", "1A1C"))], 70.0)
        self.assertNotIn(("median", ("str", "2A1C")), est)
        self.assertEqual(diag["n"]["inc:Low"], 0)
        self.assertEqual(diag["n"]["inc:All"], 3)
        self.assertAlmostEqual(diag["population_weighted"], 600.0)
        self.assertAlmostEqual(diag["nonelderly_families_weighted"], 1000.0)
        self.assertAlmostEqual(diag["share_with_expense"], 60.0)
        self.assertAlmostEqual(diag["table1_crosstab_exploratory"]["Poor|1A1C"]["weighted"], 100.0)

    def test_gate(self):
        g = {"rows": 9, "pos": {"FAMWT15C": 7}, "zero": {"TOTEXP15": 3},
             "counts": {"FCRP1231": {-1: 1, 0: 2, 1: 6}}}
        self.assertTrue(r2rest.gate(ROWS_507, g, ["TOTSLF15", "TOTEXP15"])["passed"])
        g2 = dict(g, counts={"FCRP1231": {0: 2, 1: 6}})
        res = r2rest.gate(ROWS_507, g2, ["TOTSLF15", "TOTEXP15"])
        self.assertFalse(res["passed"])
        self.assertEqual(res["unexpected_FCRP1231"], [-1])


class TestServices(unittest.TestCase):
    def test_shares(self):
        p1 = _person(1, 30, 1, 100, IPTEXP=50, OBVEXP=30, RXEXP=20, TOTPRV=60, TOTSLF=40)
        p2 = _person(3, 70, 4, 200, OBVEXP=100, RXEXP=50, HHAEXP=50, TOTMCR=150, TOTOPU=50)
        est, d = r2rest.svc_estimates([p1, p2], "13")
        self.assertAlmostEqual(est[("share", ("type", "IP", "Total"))], 5000.0 / 700)
        self.assertAlmostEqual(est[("share", ("type", "AMB", "Total"))], 33000.0 / 700)
        self.assertAlmostEqual(est[("share", ("type", "HHOTH", "Total"))], 15000.0 / 700)
        self.assertAlmostEqual(est[("share", ("type", "DENT", "Total"))], 0.0)
        self.assertAlmostEqual(est[("share", ("type", "IP", "lt65"))], 50.0)
        self.assertAlmostEqual(est[("share", ("type", "AMB", "65plus"))], 50.0)
        self.assertAlmostEqual(est[("share", ("type", "RX", "McrOnly"))], 25.0)
        self.assertAlmostEqual(est[("share", ("type", "IP", "AnyPriv"))], 50.0)
        self.assertNotIn(("share", ("type", "IP", "PubOnly")), est)
        self.assertAlmostEqual(est[("share", ("payer", "PRIV", "Total"))], 6000.0 / 700)
        self.assertAlmostEqual(est[("share", ("payer", "MCR", "Total"))], 45000.0 / 700)
        self.assertAlmostEqual(est[("share", ("payer", "OTH", "65plus"))], 25.0)
        self.assertEqual((d["svc_mismatch"], d["pay_mismatch"], d["ins_age_conflict"]), (0, 0, 0))
        self.assertEqual(d["group_n"]["Total"], 2)
        self.assertEqual(d["group_n"]["PubOnly"], 0)


class TestEvaluate(unittest.TestCase):
    def test_evaluate(self):
        est = {("median", ("inc", "All")): 450.6, ("median_lower", ("inc", "All")): 440.0,
               ("dist", ("inc", "All", "lt100")): 25.4}
        cells = [("a", 1, "median", ("inc", "All"), "451"), ("b", 2, "dist", ("inc", "All", "lt100"), "25%"),
                 ("c", 2, "dist", ("inc", "Low", "lt100"), "33%")]
        res = r2rest.evaluate(cells, est)
        self.assertEqual([r["status"] for r in res], ["computed", "computed", "no estimate"])
        self.assertTrue(res[0]["exact"] and res[0]["close"] and res[0]["underspecified"])
        self.assertEqual(res[0]["alt_lower_median"], 440.0)
        self.assertTrue(res[1]["exact"])
        self.assertFalse(res[1]["underspecified"])
        t = r2conc.tally(res)
        self.assertEqual((t["computable"], t["close"], t["exact"]), (3, 2, 2))


INV = [["H181", "2015", "DUID", "1", "5", "DWELLING UNIT ID"],
       ["H181", "2015", "CPSFAMID", "6", "6", "CPSFAMID"],
       ["H181", "2015", "FCRP1231", "7", "8", "REF PERSON OF 12/31 CPS FAMILY"],
       ["H181", "2015", "FAMWT15C", "9", "14", "POV ADJ FAMILY WGT"],
       ["H181", "2015", "POVCAT15", "15", "15", "POVERTY CATEGORY"],
       ["H181", "2015", "AGELAST", "16", "17", "AGE LAST"],
       ["H181", "2015", "TOTSLF15", "18", "21", "SELF"],
       ["H181", "2015", "TOTEXP15", "22", "25", "TOTAL"]]
LINES = ["10001A 10100.0130  50 200", "10001A 00100.01 5  20   0"]


class TestMain(unittest.TestCase):
    def test_gate_fails_cleanly(self):
        d = tempfile.mkdtemp()
        inv_path = os.path.join(d, "H181.csv")
        with open(inv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "data_year", "name", "start", "end", "description"])
            w.writerows(INV)
        zp = os.path.join(d, "h181dat.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("h181.dat", "\r\n".join(LINES) + "\r\n")
        rows = r2conc.load_ascii(zp, r2conc.positions(r2conc.read_inventory(inv_path), r2rest.fields_507()))
        self.assertEqual(rows[0]["FCRP1231"], "1")
        self.assertEqual(rows[1]["AGELAST"], "5")
        self.assertEqual(rows[0]["FAMWT15C"], "0100.0")
        out = os.path.join(d, "out")
        rc = r2rest.main(["--brief", "507", "--data", zp, "--inventory", inv_path, "--out-dir", out])
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "r2rest-507.json")) as f:
            res = json.load(f)
        self.assertIsNone(res["error"])
        self.assertFalse(res["gate"]["passed"])
        self.assertEqual(res["gate"]["families"], [1, 14522])
        self.assertNotIn("cells", res)
        self.assertEqual(len(res["data"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
