# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/prep.py (standard library only; invented names and ids, no KPMP data)."""
import json
import os
import tempfile
import unittest

from kidney import prep


def row(pkg, part, name=None, access="open", v2=True):
    return {"Access": access, "Internal Package ID": pkg, "Participant ID": part,
            "File Name": name or ("x_%s_Seg_Masks_Features%s.zip" % (pkg, "_v2" if v2 else ""))}


ROWS = [row("P3", "PA"), row("P1", "PB", v2=False), row("P2", "PB"), row("P4", "PC", access="controlled"),
        row("P5", "PD"), row("P6", "PA"), row("P2", "PB")]


class TestRows(unittest.TestCase):
    def test_v2_rows_keeps_open_v2_in_order(self):
        self.assertEqual([r["Internal Package ID"] for r in prep.v2_rows(ROWS)], ["P3", "P2", "P5", "P6", "P2"])

    def test_part_map(self):
        pmap, bad = prep.part_map(ROWS)
        self.assertEqual(bad, 0)
        self.assertEqual(pmap, {"P3": "PA", "P1": "PB", "P2": "PB", "P4": "PC", "P5": "PD", "P6": "PA"})

    def test_part_map_drops_ambiguous(self):
        pmap, bad = prep.part_map([row("P1", "PA"), row("P1", "PB"), row("P2", "PC")])
        self.assertEqual(bad, 1)
        self.assertEqual(pmap, {"P2": "PC"})


class TestPlan(unittest.TestCase):
    def test_names_count_across_batches(self):
        b = prep.plan(prep.v2_rows(ROWS), 3)
        self.assertEqual([[s["slide"] for s in x] for x in b], [["d2s001", "d2s002", "d2s003"], ["d2s004"]])
        self.assertEqual([[s["package"] for s in x] for x in b], [["P3", "P2", "P5"], ["P6"]])
        self.assertEqual(b[0][0]["name"], "x_P3_Seg_Masks_Features_v2.zip")

    def test_width_grows(self):
        rows = [row("Q%04d" % i, "G%d" % i) for i in range(1000)]
        b = prep.plan(rows, 600, prefix="s")
        self.assertEqual([len(x) for x in b], [600, 400])
        self.assertEqual(b[0][0]["slide"], "s0001")
        self.assertEqual(b[1][-1]["slide"], "s1000")

    def test_bad_batch_size(self):
        with self.assertRaises(ValueError):
            prep.plan(ROWS, 0)


class TestGroups(unittest.TestCase):
    def test_plan_groups(self):
        pmap, _ = prep.part_map(ROWS)
        gmap, prob = prep.groups(prep.plan(prep.v2_rows(ROWS), 2), pmap)
        self.assertEqual(gmap, {"d2s001": "PA", "d2s002": "PB", "d2s003": "PD", "d2s004": "PA"})
        self.assertEqual(prob, {"name_reused": 0, "package_twice": 0, "no_participant": 0})

    def test_reused_name_is_caught(self):
        pmap = {"P1": "PA", "P2": "PB", "P3": "PC"}
        a = [{"slide": "slide01", "package": "P1"}, {"slide": "slide02", "package": "P3"}]
        b = [{"slide": "slide01", "package": "P2"}]
        gmap, prob = prep.groups([a, b], pmap)
        self.assertEqual(gmap, {"slide02": "PC"})
        self.assertEqual(prob, {"name_reused": 1, "package_twice": 0, "no_participant": 0})

    def test_package_twice_and_missing(self):
        pmap = {"P1": "PA"}
        a = [{"slide": "s1", "package": "P1"}, {"slide": "s2", "package": "P1"}, {"slide": "s3", "package": "P9"},
             {"slide": "s1", "package": "P1"}]
        gmap, prob = prep.groups([a], pmap)
        self.assertEqual(gmap, {"s1": "PA"})
        self.assertEqual(prob, {"name_reused": 0, "package_twice": 1, "no_participant": 1})

    def test_participants(self):
        pmap = {"P1": "PB", "P2": "PA", "P3": "PB"}
        parts, missing = prep.participants([[{"package": "P1"}, {"package": "P2"}], [{"package": "P3"},
                                                                                     {"package": "P7"}]], pmap)
        self.assertEqual(parts, ["PA", "PB"])
        self.assertEqual(missing, 1)


def det(rows, **kw):
    d = {"code_version": "0.1.0", "gsdet": "0.2.0", "window": 288, "rows": rows}
    d.update(kw)
    return d


class TestMerge(unittest.TestCase):
    def test_merge_det_first_ok_row(self):
        a = det([{"slide": "s1", "ok": False}, {"slide": "s2", "ok": True, "classes": ["gs"]}])
        b = det([{"slide": "s1", "ok": True, "classes": ["ns"]}, {"slide": "s2", "ok": True, "classes": ["ns"]},
                 {"slide": "s3", "ok": False}])
        doc, st = prep.merge_det([a, b])
        self.assertEqual([r["slide"] for r in doc["rows"]], ["s1", "s2", "s3"])
        self.assertEqual(doc["rows"][0]["classes"], ["ns"])
        self.assertEqual(doc["rows"][1]["classes"], ["gs"])
        self.assertFalse(doc["rows"][2]["ok"])
        self.assertEqual(st, {"documents": 2, "rows_read": 5, "slides": 3, "slides_ok": 2})
        self.assertEqual(doc["gsdet"], "0.2.0")
        self.assertEqual(doc["merged_documents"], 2)

    def test_merge_det_refuses_mixed_models(self):
        with self.assertRaises(ValueError):
            prep.merge_det([det([]), det([], train_steps=1500)])
        with self.assertRaises(ValueError):
            prep.merge_det([det([]), det([], window=256)])
        with self.assertRaises(ValueError):
            prep.merge_det([])

    def test_merge_k(self):
        a = {"s1": {"k_objects": {"glom": [], "gs": []}}, "s2": {"k_objects": None}}
        b = {"s1": {"k_objects": {"gs": [], "glom": []}}, "s3": {"k_objects": {"glom": [[1]], "gs": []}}}
        doc, conflicts = prep.merge_k([a, b])
        self.assertEqual(list(doc), ["s1", "s2", "s3"])
        self.assertEqual(conflicts, 0)
        doc, conflicts = prep.merge_k([a, {"s2": {"k_objects": {"glom": [], "gs": []}}}])
        self.assertEqual(conflicts, 1)
        self.assertIsNone(doc["s2"]["k_objects"])


class TestMain(unittest.TestCase):
    def test_plan_and_participants_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "files.csv")
            cols = ["Access", "File Name", "Internal Package ID", "Participant ID"]
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(",".join('"%s"' % c for c in cols) + "\n")
                for r in ROWS:
                    f.write(",".join('"%s"' % r[c] for c in cols) + "\n")
            out = os.path.join(d, "plan")
            self.assertEqual(prep.main(["plan", "--csv", path, "--batch-size", "3", "--out-dir", out]), 0)
            self.assertEqual(sorted(os.listdir(out)), ["batch-01.json", "batch-02.json", "groups.json"])
            with open(os.path.join(out, "groups.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["d2s004"], "PA")
            tr = os.path.join(d, "train.json")
            self.assertEqual(prep.main(["participants", "--csv", path, "--lists",
                                        os.path.join(out, "batch-01.json"), "--out", tr]), 0)
            with open(tr, encoding="utf-8") as f:
                self.assertEqual(json.load(f), ["PA", "PB", "PD"])

    def test_merge_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2, o = (os.path.join(d, n) for n in ("a.json", "b.json", "o.json"))
            for p, doc in ((p1, {"s1": {"k_objects": None}}), (p2, {"s1": {"k_objects": {"glom": [], "gs": []}}})):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            self.assertEqual(prep.main(["merge-k", "--k", p1, p1, "--out", o]), 0)
            self.assertEqual(prep.main(["merge-k", "--k", p1, p2, "--out", o]), 1)
            for p, doc in ((p1, det([{"slide": "s1", "ok": True}])), (p2, det([{"slide": "s2", "ok": False}]))):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            self.assertEqual(prep.main(["merge-det", "--det", p1, p2, "--out", o]), 0)
            with open(o, encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
