# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_clinical_peek (no network: downloads are faked)."""
import io
import json
import os
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

from kidney import kpmp_clinical_peek as cp

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/package/2006/relationships"
HEADER = ('"Access","Platform","Data Format","Data Category","Size","File Name","Internal Package ID",'
          '"Experimental Strategy","Workflow Type","Participant ID","DOIs"')
CLINICAL = ("Participant ID,Tissue Type,Sex,Age (Years) (Binned),Baseline eGFR (ml/min/1.73m2) (Binned),A1c\n"
            "27-1,AKI,Female,50-59,30-39,5.1\n"
            "27-2,CKD,Male,60-69,40-49,\n"
            "27-3,CKD,Male,60-69,60-69,6.3\n"
            "27-4,Healthy Reference,Female,40-49,90-99,5.0\n")


def make_xlsx(sheets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        wb = ['<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (NS, RNS)]
        rels = ['<Relationships xmlns="%s">' % PNS]
        for i, (name, rows) in enumerate(sheets.items(), 1):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rels.append('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i, i))
            xml_rows = []
            for ri, row in enumerate(rows, 1):
                cells = []
                for ci, val in enumerate(row):
                    if val is None:
                        continue
                    ref = "%s%d" % (chr(65 + ci), ri)
                    if isinstance(val, (int, float)):
                        cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
                    else:
                        cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(val)))
                xml_rows.append('<row r="%d">%s</row>' % (ri, "".join(cells)))
            z.writestr("xl/worksheets/sheet%d.xml" % i,
                       '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>' % (NS, "".join(xml_rows)))
        wb.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
    return buf.getvalue()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def file_list(rows):
    return HEADER + "\n" + "".join(
        '"open","","%s","Clinical","%s","%s","%s","","","%s",""\n' % (fmt, size, name, pkg, pids)
        for fmt, size, name, pkg, pids in rows)


class FakeGet:
    def __init__(self, payloads):
        self.payloads, self.urls = payloads, []

    def __call__(self, url):
        self.urls.append(url)
        for key, data in self.payloads.items():
            if key in url:
                return io.BytesIO(data)
        raise AssertionError("unexpected url " + url)


class TestLists(unittest.TestCase):
    def test_file_list_keeps_open_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.csv")
            text = file_list([("csv", "1 kB", "a_clinical.csv", "pkg1", "27-1,27-2")])
            text += '"controlled","","csv","Clinical","1 kB","b.csv","pkg2","","","27-1",""\n'
            write(p, text)
            files = cp.load_file_list(p)
            self.assertEqual([f["package"] for f in files], ["pkg1"])
            self.assertEqual(cp.participant_set(p), {"27-1", "27-2"})

    def test_participant_set_missing_path(self):
        self.assertEqual(cp.participant_set(""), set())

    def test_check_list(self):
        ok = [{"name": "a.csv", "listed": "120 kB"}]
        self.assertIsNone(cp.check_list(ok))
        self.assertIn("no open rows", cp.check_list([]))
        self.assertIn("expected at most", cp.check_list(ok * 6))
        self.assertIn("unexpected file type", cp.check_list([{"name": "a.svs", "listed": "1 MB"}]))
        self.assertIn("over", cp.check_list([{"name": "a.zip", "listed": "2 GB"}]))
        self.assertIn("unreadable size", cp.check_list([{"name": "a.csv", "listed": "big"}]))


class TestTables(unittest.TestCase):
    def test_read_delimited_comma_and_tab(self):
        h, rows = cp.read_delimited(CLINICAL.encode("utf-8"))
        self.assertEqual(h[0], "Participant ID")
        self.assertEqual(len(rows), 4)
        h, rows = cp.read_delimited(b"a\tb,c\td\n1\t2,3\t4\n")
        self.assertEqual(h, ["a", "b,c", "d"])
        self.assertEqual(rows, [["1", "2,3", "4"]])

    def test_xlsx_and_zip(self):
        x = make_xlsx({"Sheet1": [["Participant ID", "Sex"], ["27-1", "Female"], ["27-2", "Male"]]})
        t = cp.tables_of("c.xlsx", x)
        self.assertEqual(t[0][0], "c.xlsx#Sheet1")
        self.assertEqual(t[0][1], ["Participant ID", "Sex"])
        self.assertEqual(len(t[0][2]), 2)
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "c.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("folder/clinical.csv", CLINICAL)
                z.writestr("folder/dictionary.pdf", b"%PDF")
            tables, members = cp.file_tables(zp, "c.zip")
            self.assertEqual(len(tables), 1)
            self.assertEqual([m["read"] for m in members], [True, False])

    def test_id_column(self):
        self.assertEqual(cp.id_column(["Sex", "Participant ID"]), 1)
        self.assertEqual(cp.id_column(["participant_id", "x"]), 0)
        self.assertEqual(cp.id_column(["Subject ID"]), 0)
        self.assertIsNone(cp.id_column(["Sex", "Age"]))

    def test_column_summary(self):
        s = cp.column_summary(["a", "b", "a", "", None])
        self.assertEqual((s["filled"], s["empty"], s["distinct"]), (3, 2, 2))
        self.assertEqual(s["levels"], [{"value": "a", "n": 2}, {"value": "b", "n": 1}])
        s = cp.column_summary([str(i) for i in range(100)])
        self.assertNotIn("levels", s)
        self.assertEqual(s["numeric"], {"n": 100, "min": 0.0, "median": 49.5, "max": 99.0})
        s = cp.column_summary(["t%d" % i for i in range(100)])
        self.assertNotIn("levels", s)
        self.assertNotIn("numeric", s)

    def test_summarise_overlap_and_segmented_marginals(self):
        h, rows = cp.read_delimited(CLINICAL.encode("utf-8"))
        s = cp.summarise("c.csv", h, rows, {"27-2", "27-3", "99-9"}, {"27-3"})
        self.assertEqual(s["id_column"], "Participant ID")
        self.assertEqual(s["participants"]["distinct"], 4)
        self.assertEqual(s["participants"]["with_segmentation"], 2)
        self.assertEqual(s["participants"]["with_both"], 1)
        self.assertEqual(s["participants"]["segmentation_not_in_table"], 1)
        self.assertNotIn("Participant ID", [c["name"] for c in s["columns"]])
        tissue = next(c for c in s["columns"] if c["name"] == "Tissue Type")
        self.assertEqual(tissue["all"]["distinct"], 3)
        self.assertEqual(tissue["segmented"]["levels"], [{"value": "CKD", "n": 2}])
        a1c = next(c for c in s["columns"] if c["name"] == "A1c")
        self.assertEqual(a1c["all"]["empty"], 1)


class TestMain(unittest.TestCase):
    def test_end_to_end_and_no_rows_in_output(self):
        data = CLINICAL.encode("utf-8")
        with tempfile.TemporaryDirectory() as d:
            fl, seg, tiv = (os.path.join(d, n) for n in ("f.csv", "s.csv", "t.csv"))
            write(fl, file_list([("csv", "%d B" % len(data), "x_OpenClinical.csv", "pkgC", "")]))
            write(seg, file_list([("zip", "1 MB", "S-1_Seg_Masks_Features_v2.zip", "pkgS", "27-1"),
                                  ("zip", "1 MB", "S-2_Seg_Masks_Features.zip", "pkgS2", "27-3")]))
            write(tiv, file_list([("xlsx", "1 kB", "tiv.xlsx", "pkgT", "27-3,27-9")]))
            out, dd = os.path.join(d, "out"), os.path.join(d, "data")
            get = FakeGet({"pkgC": data})
            argv = ["--file-list", fl, "--seg-list", seg, "--tiv-list", tiv, "--out-dir", out, "--data-dir", dd]
            self.assertEqual(cp.main(argv, get=get), 0)
            with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
                res = json.load(f)
            self.assertIsNone(res["list_problem"])
            self.assertEqual(res["segmentation_participants"], 2)
            self.assertEqual(res["seg_and_tiv_participants"], 1)
            rec = res["files"][0]
            self.assertTrue(rec["size_ok"])
            self.assertEqual(rec["tables"][0]["participants"]["with_both"], 1)
            text = json.dumps(res)
            self.assertNotIn("27-1", text)
            self.assertNotIn("27-3", text)
            # second run uses the cache, no new download
            self.assertEqual(cp.main(argv, get=get), 0)
            self.assertEqual(len(get.urls), 1)

    def test_bad_list_downloads_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            fl = os.path.join(d, "f.csv")
            write(fl, file_list([("svs", "1 MB", "slide.svs", "pkgX", "")]))
            get = FakeGet({})
            rc = cp.main(["--file-list", fl, "--out-dir", os.path.join(d, "o"), "--data-dir", d], get=get)
            self.assertEqual(rc, 1)
            self.assertEqual(get.urls, [])


if __name__ == "__main__":
    unittest.main()
