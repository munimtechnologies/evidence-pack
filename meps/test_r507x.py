# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps.r507x (no network, no MEPS file)."""
import csv
import json
import os
import tempfile
import unittest
import zipfile

from meps import r2conc, r2rest, r507x


def _m(duid, fam, rp, w, pov, age, oop, exp, pid, pw=500.0, insc=1, rel=1, mo=-1, da=-1, a15=None, a31=None,
       a42=None, a53=None):
    ages = {"AGE15X": a15, "AGE31X": a31, "AGE42X": a42, "AGE53X": a53}
    r = {"DUID": duid, "CPSFAMID": fam, "FCRP1231": str(rp), "FAMWT15C": str(w), "POVCAT15": str(pov),
         "AGELAST": str(age), "TOTSLF15": str(oop), "TOTEXP15": str(exp), "PID": str(pid), "PERWT15F": str(pw),
         "INSC1231": str(insc), "REFRL15X": str(rel), "MOPID53X": str(mo), "DAPID53X": str(da)}
    for k, v in ages.items():
        r[k] = str(age if v is None else v)
    return r


ROWS = [
    _m("10001", "A", 1, 100.0, 1, 30, 50, 200, 101),
    _m("10001", "A", 0, 100.0, 1, 0, 20, 300, 102, rel=4, mo=101, a15=0, a31=-1, a42=-1, a53=0),  # newborn
    _m("10002", "A", 1, 200.0, 5, 40, 1000, 3000, 101),
    _m("10002", "A", 0, 200.0, 5, 41, 0, 0, 102, rel=2),
    _m("10002", "A", 0, 200.0, 5, 10, 0, 0, 103, rel=6),                       # grandchild, no parent present
    _m("10003", "A", 1, 50.0, 3, 25, 150, 150, 101),
    _m("10003", "A", 0, 50.0, 3, 17, 0, 0, 102, pw=0.0, insc=2, rel=8),        # sibling, out of scope
    _m("10004", "A", 1, 70.0, 4, 70, 10, 10, 101),                             # elderly: excluded
    _m("10005", "A", 1, 80.0, 4, 30, 0, 0, 101),                               # no expense: excluded
    _m("10006", "A", -1, 0.0, 2, 50, 5, 5, 101),                               # not a 12/31 member
]

EXPECT = {  # rule -> (family A, family B, family C)
    "R0": ("1A1C", "2A1C", "1A1C"), "R1": ("1A1C", "2A1C", "1A1C"), "R2": ("1A0C", "2A1C", "1A1C"),
    "R3": ("1A0C", "2A1C", "1A1C"), "R4": ("1A1C", "2A1C", "1A1C"), "R5": ("1A1C", "2A1C", "1A0C"),
    "R6": ("1A1C", "2A1C", "1A0C"), "R7": ("1A1C", "2A0C", "1A0C"), "R8": ("1A1C", "2A0C", "1A0C"),
}


class TestRules(unittest.TestCase):
    def test_rule_list(self):
        self.assertEqual([r[0] for r in r507x.RULES], ["R%d" % i for i in range(9)])
        self.assertEqual(len(r507x.STR_CELLS), 16)
        self.assertEqual(sum(r507x.TABLE1.values()), 97196955)
        for s, tot in r507x.TABLE1_COLS.items():
            self.assertEqual(sum(v for k, v in r507x.TABLE1.items() if k.endswith(s)), tot)

    def test_build_and_classify(self):
        fams, bad = r507x.build(ROWS)
        self.assertEqual((len(fams), bad), (5, 0))
        by = {f["key"]: f for f in fams}
        self.assertEqual(by["10002A"]["pids"], {101, 102, 103})
        self.assertEqual((by["10001A"]["oop"], by["10001A"]["exp"]), (70.0, 500.0))
        self.assertTrue(by["10004A"]["elderly"])
        for rid, _, rule in r507x.RULES:
            got = tuple(r507x.classify(by[k], rule) for k in ("10001A", "10002A", "10003A"))
            self.assertEqual(got, EXPECT[rid], rid)

    def test_age_bin(self):
        self.assertEqual([r507x.age_bin(a) for a in (-1, 0, 17, 18, 64, 65, 85, 86, -8)],
                         [0, 1, 1, 2, 2, 3, 3, None, None])

    def test_compare(self):
        c = r507x.compare({"a": 9.5, "b": 9.49}, {"a": 10, "b": 10, "c": 0})
        self.assertTrue(c["a"]["exact"])
        self.assertFalse(c["b"]["exact"])
        self.assertTrue(c["c"]["exact"])
        self.assertAlmostEqual(c["b"]["gap"], -0.51)

    def test_analyze(self):
        fams, _ = r507x.build(ROWS)
        res, summary = r507x.analyze(fams)
        by = {r["rule"]: r for r in res}
        self.assertEqual(summary["population_families"], 3)
        self.assertEqual(summary["reproducing_rules"], [])
        self.assertEqual(summary["best_rule"], "R0")
        self.assertFalse(summary["E1_some_rule_reproduces_all_16"])
        self.assertAlmostEqual(by["R0"]["table1"]["Poor|1A1C"]["ours"], 100.0)
        self.assertAlmostEqual(by["R2"]["table1"]["Poor|1A0C"]["ours"], 100.0)
        self.assertAlmostEqual(by["R2"]["table1"]["Poor|1A1C"]["ours"], 0.0)
        self.assertAlmostEqual(by["R7"]["table1"]["High|2A0C"]["ours"], 200.0)
        self.assertAlmostEqual(by["R5"]["table1"]["Low|1A0C"]["ours"], 50.0)
        self.assertAlmostEqual(by["R0"]["families_with_adult_weighted"], 350.0)
        self.assertEqual(by["R0"]["no_adult_families"], 0)
        self.assertEqual(by["R0"]["struct_cells_n"], 16)

    def test_gate_x(self):
        g = {"pos": {"PERWT15F": 9}, "counts": {"INSC1231": {1: 9, 2: 1}}, "neg1": {"MOPID53X": 9},
             "age_bins": {"AGE31X": [1, 2, 6, 1]}}
        res = r507x.gate_x(ROWS, g)
        self.assertTrue(res["passed"], res)
        g2 = dict(g, age_bins={"AGE31X": [0, 3, 6, 1]})
        self.assertFalse(r507x.gate_x(ROWS, g2)["passed"])


WIDTHS = [("DUID", 5), ("CPSFAMID", 1), ("FCRP1231", 2), ("FAMWT15C", 8), ("POVCAT15", 1), ("AGELAST", 2),
          ("TOTSLF15", 6), ("TOTEXP15", 6), ("PID", 3), ("PERWT15F", 8), ("INSC1231", 1), ("REFRL15X", 2),
          ("MOPID53X", 3), ("DAPID53X", 3), ("AGE15X", 2), ("AGE31X", 2), ("AGE42X", 2), ("AGE53X", 2)]


class TestMain(unittest.TestCase):
    def test_gate_fails_cleanly(self):
        self.assertEqual(sorted(n for n, _ in WIDTHS), sorted(r2rest.fields_507() + r507x.EXTRA))
        d = tempfile.mkdtemp()
        inv_path = os.path.join(d, "H181.csv")
        start, inv = 1, []
        for name, width in WIDTHS:
            inv.append(["H181", "2015", name, str(start), str(start + width - 1), name])
            start += width
        with open(inv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "data_year", "name", "start", "end", "description"])
            w.writerows(inv)
        lines = ["".join(r[n].rjust(width) for n, width in WIDTHS) for r in ROWS]
        zp = os.path.join(d, "h181dat.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("h181.dat", "\r\n".join(lines) + "\r\n")
        pos = r2conc.positions(r2conc.read_inventory(inv_path), r2rest.fields_507() + r507x.EXTRA)
        rows = r2conc.load_ascii(zp, pos)
        self.assertEqual(rows, ROWS)
        out = os.path.join(d, "out")
        rc = r507x.main(["--data", zp, "--inventory", inv_path, "--out-dir", out])
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "r507x.json")) as f:
            res = json.load(f)
        self.assertIsNone(res["error"])
        self.assertFalse(res["gate"]["passed"])
        self.assertEqual(res["gate"]["families"], [5, 14522])
        self.assertNotIn("rules", res)
        self.assertEqual(len(res["data"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
