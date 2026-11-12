# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/usage.py (standard library only; invented names and ids, no KPMP data)."""
import csv
import json
import os
import tempfile
import unittest

from kidney import usage


def row(pkg, part, name=None):
    return {"Access": "open", "Internal Package ID": pkg, "Participant ID": part,
            "File Name": name or ("x_%s_Seg_Masks_Features_v2.zip" % pkg)}


ROWS = [row("P1", "PA", "x_P1_old.zip"), row("P1", "PA"), row("P2", "PB"), row("P3", "PB"), row("P4", "PC"),
        row("P5", "")]
V2 = "x_%s_Seg_Masks_Features_v2.zip"


class TestParse(unittest.TestCase):
    def test_parse_use(self):
        self.assertEqual(usage.parse_use("stage6:train=a/b.json"), ("stage6", "train", "a/b.json"))
        self.assertEqual(usage.parse_use("d-pass:pass=C:/x/y.json"), ("d-pass", "pass", "C:/x/y.json"))

    def test_parse_use_refuses(self):
        for bad in ("train=p", "s:training=p", "s:train", "s:train=", ":train=p", "a;b:train=p"):
            with self.assertRaises(ValueError):
                usage.parse_use(bad)

    def test_items(self):
        got = usage.items([{"slide": "S1", "package": "P1", "name": "N"}, "P2", {"package": "P3", "name": ""}])
        self.assertEqual(got, [("P1", "N"), ("P2", None), ("P3", None)])
        for bad in ({"P1": 1}, [{"slide": "S1"}], [""]):
            with self.assertRaises(ValueError):
                usage.items(bad)

    def test_default_name(self):
        self.assertEqual(usage.default_name(["x_P1_old.zip", V2 % "P1"]), V2 % "P1")
        self.assertEqual(usage.default_name(["a.zip", "b.zip"]), "a.zip")


class TestBuild(unittest.TestCase):
    def test_clean_table(self):
        uses = [("stage6", "train", [("P1", V2 % "P1"), ("P2", None)]),
                ("stage6", "test", [("P4", None)]),
                ("stage6", "excluded", [("P3", None)]),
                ("d-pass", "pass", [("P4", None), ("P1", None)])]
        table, rep = usage.build(ROWS, uses)
        self.assertEqual([t["internal_package_id"] for t in table], ["P1", "P2", "P4", "P3"])
        self.assertEqual([t["participant_id"] for t in table], ["PA", "PB", "PC", "PB"])
        self.assertEqual(table[0]["kpmp_file_name"], V2 % "P1")
        self.assertEqual(table[1]["kpmp_file_name"], V2 % "P2")
        self.assertEqual(table[0]["kinds"], "train; pass")
        self.assertEqual(table[2]["kinds"], "test; pass")
        self.assertEqual(table[3]["kinds"], "excluded")
        self.assertEqual(table[0]["how_used"], "d-pass: " + usage.KIND_TEXT["pass"] + "; stage6: "
                         + usage.KIND_TEXT["train"])
        self.assertEqual(rep["problems"], {"not_in_file_list": 0, "no_participant": 0, "name_mismatch": 0})
        self.assertEqual(rep["leaks"], {"stage_package": 0, "stage_participant": 0, "excluded_used": 0,
                                        "any_package": 0, "any_participant": 0})
        self.assertEqual(rep["by_kind"], {"train": 2, "dev": 0, "test": 1, "pass": 2, "qc": 0, "excluded": 1})
        self.assertEqual(rep["by_use"], {"d-pass:pass": 2, "stage6:train": 2, "stage6:test": 1,
                                         "stage6:excluded": 1})
        self.assertEqual(rep["packages"], 4)
        self.assertEqual(rep["participants"], 3)
        self.assertTrue(rep["ok"])

    def test_default_name_used_when_list_has_none(self):
        table, rep = usage.build(ROWS, [("s", "pass", [("P1", None)])])
        self.assertEqual(table[0]["kpmp_file_name"], V2 % "P1")
        self.assertTrue(rep["ok"])

    def test_participant_leak_within_stage(self):
        uses = [("stage4", "train", [("P1", None), ("P2", None)]), ("stage4", "dev", [("P3", None)]),
                ("stage5", "train", [("P4", None)]), ("stage5", "test", [("P1", None)])]
        _, rep = usage.build(ROWS, uses)
        self.assertEqual(rep["leaks"], {"stage_package": 0, "stage_participant": 1, "excluded_used": 0,
                                        "any_package": 1, "any_participant": 2})
        self.assertFalse(rep["ok"])

    def test_package_leak_within_stage(self):
        _, rep = usage.build(ROWS, [("s", "train", [("P1", None)]), ("s", "test", [("P1", None)])])
        self.assertEqual(rep["leaks"]["stage_package"], 1)
        self.assertEqual(rep["leaks"]["stage_participant"], 1)
        self.assertFalse(rep["ok"])

    def test_overlap_across_stages_is_reported_not_failed(self):
        _, rep = usage.build(ROWS, [("stage5", "train", [("P1", None)]), ("stage6", "test", [("P1", None)])])
        self.assertEqual(rep["leaks"], {"stage_package": 0, "stage_participant": 0, "excluded_used": 0,
                                        "any_package": 1, "any_participant": 1})
        self.assertTrue(rep["ok"])

    def test_problems(self):
        uses = [("s", "train", [("P9", "N9.zip"), ("P5", None), ("P2", "WRONG.zip")]),
                ("s", "pass", [("P2", "OTHER.zip")])]
        table, rep = usage.build(ROWS, uses)
        self.assertEqual(rep["problems"], {"not_in_file_list": 1, "no_participant": 1, "name_mismatch": 1})
        self.assertEqual((table[0]["kpmp_file_name"], table[0]["participant_id"]), ("N9.zip", ""))
        self.assertEqual(table[2]["kpmp_file_name"], "WRONG.zip")
        self.assertFalse(rep["ok"])

    def test_excluded_but_used(self):
        table, rep = usage.build(ROWS, [("s", "excluded", [("P1", None)]), ("s", "pass", [("P1", None)])])
        self.assertEqual(rep["leaks"]["excluded_used"], 1)
        self.assertEqual(table[0]["kinds"], "pass; excluded")
        self.assertFalse(rep["ok"])

    def test_nothing_used_is_not_ok(self):
        table, rep = usage.build(ROWS, [("s", "train", [])])
        self.assertEqual(table, [])
        self.assertFalse(rep["ok"])


class TestMain(unittest.TestCase):
    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "files.csv")
            cols = ["Access", "File Name", "Internal Package ID", "Participant ID"]
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(",".join('"%s"' % c for c in cols) + "\n")
                for r in ROWS:
                    f.write(",".join('"%s"' % r[c] for c in cols) + "\n")
            tr, te, ex = (os.path.join(d, n) for n in ("train.json", "test.json", "excl.json"))
            for p, doc in ((tr, [{"slide": "D2S001", "package": "P1", "name": V2 % "P1"},
                                 {"slide": "D2S002", "package": "P2", "name": V2 % "P2"}]),
                           (te, [{"slide": "T1", "package": "P4", "name": V2 % "P4"}]),
                           (ex, ["P3"])):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            out, rep = os.path.join(d, "usage.csv"), os.path.join(d, "report.json")
            base = ["--csv", path, "--use", "stage6:train=" + tr, "--use", "stage6:test=" + te,
                    "--use", "stage6:excluded=" + ex, "--out", out]
            self.assertEqual(usage.main(base + ["--report", rep]), 0)
            with open(out, encoding="utf-8", newline="") as f:
                rd = csv.DictReader(f)
                rows = list(rd)
                self.assertEqual(rd.fieldnames, list(usage.COLUMNS))
            self.assertEqual([r["internal_package_id"] for r in rows], ["P1", "P2", "P4", "P3"])
            self.assertEqual(rows[0]["participant_id"], "PA")
            self.assertEqual(rows[2]["kinds"], "test")
            with open(rep, encoding="utf-8") as f:
                r = json.load(f)
            self.assertTrue(r["ok"])
            self.assertEqual(r["packages"], 4)
            self.assertEqual(usage.main(base + ["--use", "stage6:dev=" + tr]), 1)
            for spec in ("stage6:bogus=" + tr, "s:train=" + os.path.join(d, "missing.json")):
                with self.assertRaises(SystemExit) as cm:
                    usage.main(["--csv", path, "--use", spec, "--out", out])
                self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
