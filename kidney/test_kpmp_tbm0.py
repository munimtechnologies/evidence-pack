# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_tbm0. Fixtures use the raw sheet and column names that the census jobs
recorded (kpmp-census3-v1 results.json, describe.sheets and sheet_names)."""
import csv
import json
import os
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

from kidney import kpmp_census as kc
from kidney import kpmp_tbm0 as kt

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/package/2006/relationships"

V2_TUBS = ["x1", "x2", "y1", "y2", "Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"]
V2_GLOMS = ["x1", "x2", "y1", "y2", "Area", "Mesangial Area", "Mesangial Fraction"]
V1_TUBS = ["Total Object Area", "Area (pixel^2)", "Radius (pixel)", "In Medulla", "Average TBM Thickness",
           "Average Cell Thickness", "Luminal Fraction", "compartment_id"]


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def write_xlsx(path, sheets):
    with zipfile.ZipFile(path, "w") as z:
        wb, rels = [], []
        for k, (name, rows) in enumerate(sheets.items(), 1):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), k, k))
            rels.append('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (k, k))
            xml = []
            for ri, row in enumerate(rows, 1):
                cells = []
                for ci, v in enumerate(row):
                    if v is None:
                        continue
                    ref = "%s%d" % (_col(ci), ri)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        cells.append('<c r="%s"><v>%s</v></c>' % (ref, v))
                    else:
                        cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(str(v))))
                xml.append('<row r="%d">%s</row>' % (ri, "".join(cells)))
            z.writestr("xl/worksheets/sheet%d.xml" % k,
                       '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>' % (NS, "".join(xml)))
        z.writestr("xl/workbook.xml", '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>'
                   % (NS, RNS, "".join(wb)))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="%s">%s</Relationships>' % (PNS, "".join(rels)))


def v2_package(pdir, tbms):
    os.makedirs(pdir, exist_ok=True)
    tubs = [V2_TUBS] + [[10 * i, 10 * i + 8, 0, 5 if t == 0 else 10, t, 30.0, 0.1] for i, t in enumerate(tbms)]
    write_xlsx(os.path.join(pdir, "S-2006-000001_features_v2.xlsx"),
               {"gloms": [V2_GLOMS], "s_gloms": [V2_GLOMS], "tubs": tubs, "arts": [["x1", "x2", "y1", "y2", "Arterial Area"]]})
    with open(os.path.join(pdir, "record.json"), "w") as f:
        json.dump({"ok": True}, f)


def v1_package(pdir, rows):
    """rows: [(tbm, medulla value)]."""
    os.makedirs(pdir, exist_ok=True)
    feats = [V1_TUBS] + [[100, 90 if t == 0 else 180, 6, m, t, 28.0, 0.11, 1] for t, m in rows]
    write_xlsx(os.path.join(pdir, "final_combined_features_tubules.xlsx"),
               {"Bounding Boxes": [["x", "y"]], "Features": feats})
    with open(os.path.join(pdir, "record.json"), "w") as f:
        json.dump({"ok": True}, f)


class TestReaders(unittest.TestCase):
    def test_medulla_code(self):
        self.assertEqual([kt.medulla_code(v) for v in (1, "1", "True", "false", 0, "0.0", "", None, "x")],
                         [1, 1, 1, 0, 0, 0, None, None, None])

    def test_tubules_v2_and_v1(self):
        with tempfile.TemporaryDirectory() as d:
            v2_package(os.path.join(d, "a"), [4.0, 0, -1.0])
            rows, med, err = kt.tubules(os.path.join(d, "a"), "v2")
            self.assertEqual(err, [])
            self.assertEqual(rows, [(4.0, 30.0, 0.1, 80.0, None), (0.0, 30.0, 0.1, 40.0, None),
                                    (-1.0, 30.0, 0.1, 80.0, None)])
            self.assertEqual(med, {})
            v1_package(os.path.join(d, "b"), [(5.0, 1), (0, 0), (6.0, "True")])
            rows, med, err = kt.tubules(os.path.join(d, "b"), "v1")
            self.assertEqual(err, [])
            self.assertEqual(rows, [(5.0, 28.0, 0.11, 180.0, 1), (0.0, 28.0, 0.11, 90.0, 0),
                                    (6.0, 28.0, 0.11, 180.0, 1)])
            self.assertEqual(med, {"1": 1, "0": 1, "True": 1})


def _pkg(n_zero, n_pos, tbm=4.0, zsize=50.0, psize=200.0, med=None):
    return [(0.0, 20.0, 0.0, zsize, med)] * n_zero + [(tbm, 30.0, 0.2, psize, med)] * n_pos


class TestSummary(unittest.TestCase):
    def test_dispersion_and_odds(self):
        self.assertAlmostEqual(kt.dispersion([(0, 10), (10, 10)]), 20.0)
        self.assertIsNone(kt.dispersion([(0, 10), (0, 10)]))
        self.assertIsNone(kt.dispersion([(1, 10)]))
        self.assertAlmostEqual(kt.odds_ratio(5, 5, 1, 19), 13.0)

    def test_summarise(self):
        packages = [("A", "v2", _pkg(5, 20)), ("B", "v2", _pkg(0, 25, tbm=6.0, psize=100.0)),
                    ("C", "v1", _pkg(5, 5, med=1) + _pkg(1, 19, med=0) + [(None, 1.0, 0.1, 10.0, 0)])]
        s = kt.summarise(packages)
        v2 = s["v2"]
        self.assertEqual((v2["rows"], v2["with_tbm"], v2["zero_or_less"], v2["exactly_zero"]), (50, 50, 5, 5))
        self.assertAlmostEqual(v2["share"], 0.1)
        self.assertAlmostEqual(v2["dispersion"], 5.0 / 0.9)
        self.assertEqual(v2["slide_share"]["none"], 1)
        self.assertEqual(v2["size_median"], {"zero": 50.0, "positive": 100.0})
        self.assertAlmostEqual(v2["size_ratio"], 0.5)
        self.assertEqual(v2["slide_median_shift"], {"slides": 2, "over_5pct": 0, "median": 0.0})
        self.assertEqual(v2["cell_median"], {"zero": 20.0, "positive": 30.0})
        v1 = s["v1"]
        self.assertEqual((v1["rows"], v1["with_tbm"], v1["zero_or_less"]), (31, 30, 6))
        m = v1["medulla"]
        self.assertEqual((m["medulla_zero"], m["medulla_pos"], m["cortex_zero"], m["cortex_pos"], m["uncoded"]),
                         (5, 5, 1, 19, 0))
        self.assertAlmostEqual(m["odds_ratio"], 13.0)
        self.assertAlmostEqual(v1["slide_median_shift"]["median"], 0.0)

    def test_participants_and_rows(self):
        packages = [("A", "v2", _pkg(5, 20)), ("B", "v2", _pkg(1, 9, tbm=5.0)), ("C", "v1", _pkg(2, 30, tbm=7.0)),
                    ("D", "v1", _pkg(0, 40))]
        owner = {"A": "p1", "B": "p1", "C": "p2"}
        pt = kt.participant_table(packages, owner)
        self.assertEqual(sorted(pt), ["p1", "p2"])
        self.assertEqual((pt["p1"]["n"], pt["p1"]["zero"], len(pt["p1"]["tbm_pos"])), (35, 6, 29))
        self.assertEqual(kt.feature(pt["p1"], "tbm_pos"), 4.0)
        self.assertAlmostEqual(kt.feature(pt["p1"], "zero_share"), 6 / 35)
        scores = {"p1": {kc.ATROPHY_SCORE: 10.0}, "p2": {kc.ATROPHY_SCORE: None}}
        clin = {"p2": {"egfr": 60.0}}
        self.assertEqual(kt.test_rows(pt, "tbm_pos", "tiv", kc.ATROPHY_SCORE, scores, clin), [("v2", 4.0, 10.0, None)])
        self.assertEqual(kt.test_rows(pt, "zero_share", "clinical", "egfr", scores, clin),
                         [("v1", 2 / 32, 60.0, None)])
        pt["p2"]["tbm_pos"] = pt["p2"]["tbm_pos"][:19]
        self.assertIsNone(kt.feature(pt["p2"], "tbm_pos"))

    def test_grade(self):
        summary = {"v1": {"share": 0.02, "with_tbm": 5000, "medulla": {"medulla_zero": 50, "medulla_pos": 100,
                                                                        "cortex_zero": 30, "cortex_pos": 900,
                                                                        "odds_ratio": 15.0}},
                   "v2": {"dispersion": 1.5, "slides": 25, "size_ratio": 0.9}}
        tests = {t[0]: {"floor_ok": True, "stratified": {"rho": 0.3 * t[4], "p": 0.01}} for t in kt.TESTS}
        tests["Z6_tbm_pos_vs_egfr"]["stratified"]["p"] = 0.2
        tests["Z8_zero_share_vs_egfr"]["floor_ok"] = False
        g = kt.grade({"summary": summary, "tests": tests})
        self.assertEqual(g, {"Z1_v1_zero_share": "pass", "Z2_v2_slide_dispersion": "fail",
                             "Z3_v2_zero_smaller": "fail", "Z4_v1_medulla_odds": "pass",
                             "Z5_tbm_pos_vs_atrophy": "pass", "Z6_tbm_pos_vs_egfr": "fail",
                             "Z7_zero_share_vs_atrophy": "pass", "Z8_zero_share_vs_egfr": "untestable"})
        summary["v2"]["slides"] = 5
        summary["v1"]["medulla"]["medulla_pos"] = 10
        g = kt.grade({"summary": summary, "tests": tests})
        self.assertEqual((g["Z2_v2_slide_dispersion"], g["Z4_v1_medulla_odds"]), ("untestable", "untestable"))


FIELDS = ["Access", "Platform", "Data Format", "Data Category", "Size", "File Name", "Internal Package ID",
          "Experimental Strategy", "Workflow Type", "Participant ID", "DOIs"]


def write_list(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


class TestMainOffline(unittest.TestCase):
    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "data", "kpmp-census")
            v2_package(os.path.join(cache, "pa"), [4.0] * 20 + [0] * 5)
            v1_package(os.path.join(cache, "pb"), [(5.0, 0)] * 25 + [(0, 1)] * 2)
            seg = os.path.join(d, "seg.csv")
            write_list(seg, [
                {"Access": "open", "Size": "1 MB", "File Name": "x_S-2006-000001_Seg_Masks_Features_v2.zip",
                 "Internal Package ID": "pa", "Experimental Strategy": kc.STRATEGY, "Participant ID": "p1"},
                {"Access": "open", "Size": "1 MB", "File Name": "y_S-2311-000002_Seg_Masks_Features.zip",
                 "Internal Package ID": "pb", "Experimental Strategy": kc.STRATEGY, "Participant ID": "p2"}])
            desc = os.path.join(d, "desc.csv")
            write_list(desc, [{"Access": "open", "File Name": "t_KPMP TIV Descriptor Scores.xlsx",
                               "Internal Package ID": "tiv1", "Experimental Strategy": "Pathology Descriptor Scoring"}])
            os.makedirs(os.path.join(cache, "tiv"))
            write_xlsx(os.path.join(cache, "tiv", "tiv1.xlsx"), {"Data Table": [
                ["Participant ID", "Consensus Complete"] + list(kc.SCORE_COLUMNS),
                ["p1", "Y", 0, 5, 1, 10], ["p2", "Y", 0, 20, 2, 30]]})
            clinl = os.path.join(d, "clin.csv")
            write_list(clinl, [{"Access": "open", "File Name": "c_OpenAccessClinicalData.csv",
                                "Internal Package ID": "clin1"}])
            os.makedirs(os.path.join(cache, "clinical"))
            with open(os.path.join(cache, "clinical", "clin1.csv"), "w", newline="") as f:
                f.write("Participant ID,Baseline eGFR (ml/min/1.73m2)\np1,80\np2,40\n")
            out = os.path.join(d, "out")
            self.assertEqual(kt.main(["--file-list", seg, "--descriptor-list", desc, "--clinical-list", clinl,
                                      "--out-dir", out, "--data-dir", os.path.join(d, "data"),
                                      "--permutations", "50"]), 0)
            with open(os.path.join(out, "results.json")) as f:
                res = json.load(f)
            self.assertEqual(res["packages"], {"read": 2, "with_errors": 0, "listed": 2})
            self.assertEqual(res["participants"], {"with_packages": 2, "with_tiv": 2, "with_clinical": 2})
            self.assertEqual(res["summary"]["v2"]["zero_or_less"], 5)
            self.assertEqual(res["summary"]["v1"]["medulla"]["medulla_zero"], 2)
            self.assertEqual(res["in_medulla_raw_values"], [{"value": "0", "rows": 25}, {"value": "1", "rows": 2}])
            self.assertEqual(res["grades"]["status"], "complete")
            self.assertEqual(res["grades"]["Z5_tbm_pos_vs_atrophy"], "untestable")
            self.assertEqual(res["grades"]["Z1_v1_zero_share"], "untestable")
            self.assertNotIn("p1", json.dumps(res))


if __name__ == "__main__":
    unittest.main()
