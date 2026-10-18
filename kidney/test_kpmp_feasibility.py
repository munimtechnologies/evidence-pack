# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney/kpmp_feasibility.py (standard library only; no network)."""
import io
import os
import re
import tempfile
import unittest
import urllib.error
import zipfile

try:
    from kidney import kpmp_feasibility as kf
except ImportError:  # run from inside kidney/
    import kpmp_feasibility as kf

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
ODR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class FakeResponse(io.BytesIO):
    def __init__(self, data, ctype="application/octet-stream"):
        super().__init__(data)
        self.headers = {"Content-Type": ctype}


def make_xlsx(target):
    wb = (f'<workbook xmlns="{MAIN}" xmlns:r="{ODR}"><sheets>'
          '<sheet name="Scores" sheetId="1" r:id="rId1"/><sheet name="Notes" sheetId="2" r:id="rId2"/>'
          '</sheets></workbook>')
    rels = (f'<Relationships xmlns="{RELS}">'
            '<Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="x" Target="/xl/worksheets/sheet2.xml"/></Relationships>')
    sst = (f'<sst xmlns="{MAIN}"><si><t>Participant ID</t></si><si><t>Mesangial expansion</t></si>'
           '<si><t>27-10074</t></si><si><r><t>34-</t></r><r><t>10050</t></r></si><si><t>present</t></si></sst>')
    s1 = (f'<worksheet xmlns="{MAIN}"><sheetData>'
          '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
          '<c r="C1" t="inlineStr"><is><t>Score</t></is></c></row>'
          '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>4</v></c><c r="C2"><v>2</v></c></row>'
          '<row r="3"><c r="A3" t="s"><v>3</v></c><c r="C3"><v>0</v></c></row>'
          '<row r="4"><c r="A4" t="s"><v>2</v></c><c r="B4" t="s"><v>4</v></c><c r="C4"><v>1</v></c></row>'
          '</sheetData></worksheet>')
    s2 = (f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
          '<c r="B1" t="inlineStr"><is><t>note</t></is></c></row></sheetData></worksheet>')
    with zipfile.ZipFile(target, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", s1)
        z.writestr("xl/worksheets/sheet2.xml", s2)


SCORES = [["Participant ID", "Mesangial expansion", "Score"], ["27-10074", "present", "2"],
          ["34-10050", None, "0"], ["27-10074", "present", "1"]]


class SizeAndUrlTest(unittest.TestCase):
    def test_parse_size(self):
        self.assertEqual(kf.parse_size("11.8 MB"), 11_800_000)
        self.assertEqual(kf.parse_size("357 kB"), 357_000)
        self.assertEqual(kf.parse_size("2.37 GB"), 2_370_000_000)
        self.assertEqual(kf.parse_size("1 GB"), 1_000_000_000)
        self.assertEqual(kf.parse_size("512 B"), 512)

    def test_size_ok(self):
        self.assertTrue(kf.size_ok(11_900_000, "11.8 MB"))
        self.assertFalse(kf.size_ok(12_100_000, "11.8 MB"))
        self.assertFalse(kf.size_ok(0, "357 kB"))

    def test_download_url_quotes_spaces(self):
        self.assertEqual(kf.download_url("p-1", "a b_c.xlsx"),
                         "https://atlas.kpmp.org/api/v1/file/download/p-1/a%20b_c.xlsx")

    def test_targets_are_well_formed(self):
        keys = [t["key"] for t in kf.TARGETS]
        self.assertEqual(keys, ["seg_small", "pas_small", "tiv", "pas_large"])
        for t in kf.TARGETS:
            self.assertRegex(t["package"], UUID)
            self.assertRegex(t["name"][:36], UUID)
            self.assertEqual(t["name"][36], "_")
            self.assertGreater(kf.parse_size(t["listed"]), 0)
        by = {t["key"]: t for t in kf.TARGETS}
        self.assertIn("S-1904-008128_", by["seg_small"]["name"])
        self.assertIn("S-1904-008128_PAS_", by["pas_small"]["name"])
        self.assertIn("_PAS_", by["pas_large"]["name"])
        self.assertEqual(by["seg_small"]["participant"], by["pas_small"]["participant"])


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self.tmp.name, "f.bin")

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_then_cached(self):
        calls, pauses = [], []

        def get(url):
            calls.append(url)
            return FakeResponse(b"x" * 1000)

        r = kf.download("u", self.dest, "1 kB", get=get, pause=pauses.append)
        self.assertTrue(r["ok"])
        self.assertFalse(r["cached"])
        self.assertEqual(r["bytes"], 1000)
        self.assertEqual(r["tries"], 1)
        with open(self.dest, "rb") as f:
            self.assertEqual(len(f.read()), 1000)
        r2 = kf.download("u", self.dest, "1 kB", get=get, pause=pauses.append)
        self.assertTrue(r2["cached"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(pauses, [])
        self.assertFalse(os.path.exists(self.dest + ".part"))

    def test_404_is_final(self):
        pauses = []

        def get(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        r = kf.download("u", self.dest, "1 kB", get=get, pause=pauses.append)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "HTTP 404")
        self.assertEqual(r["tries"], 1)
        self.assertEqual(pauses, [])
        self.assertFalse(os.path.exists(self.dest))
        self.assertFalse(os.path.exists(self.dest + ".part"))

    def test_transient_error_is_retried(self):
        pauses, n = [], []

        def get(url):
            n.append(1)
            if len(n) == 1:
                raise ConnectionResetError("reset")
            return FakeResponse(b"abc")

        r = kf.download("u", self.dest, None, get=get, pause=pauses.append)
        self.assertTrue(r["ok"])
        self.assertEqual(r["tries"], 2)
        self.assertEqual(pauses, [5])

    def test_gives_up_after_tries(self):
        pauses = []

        def get(url):
            raise TimeoutError("slow")

        r = kf.download("u", self.dest, None, get=get, pause=pauses.append, tries=3)
        self.assertFalse(r["ok"])
        self.assertEqual(r["tries"], 3)
        self.assertEqual(pauses, [5, 10])
        self.assertIn("TimeoutError", r["error"])


class GeometryTest(unittest.TestCase):
    def test_aligned(self):
        self.assertEqual(kf.aligned((1000, 800), (8000, 6400)), 8)
        self.assertEqual(kf.aligned((1000, 800), (1000, 800)), 1)
        self.assertEqual(kf.aligned((1000, 800), (8001, 6401)), 8)
        self.assertIsNone(kf.aligned((1000, 900), (8000, 6400)))

    def test_hw_of(self):
        self.assertEqual(kf.hw_of((100, 200)), (100, 200))
        self.assertEqual(kf.hw_of((100, 200, 3)), (100, 200))
        self.assertEqual(kf.hw_of((3, 100, 200)), (100, 200))
        self.assertEqual(kf.hw_of((1, 100, 200)), (100, 200))
        self.assertIsNone(kf.hw_of((5, 6, 7, 8)))

    def test_description(self):
        desc = ("Aperio Image Library v12.0.15 \r\n46000x32914 [0,100 46000x32914] (240x240) JPEG/RGB Q=70"
                "|AppMag = 40|StripeWidth = 2032|MPP = 0.2527|Left = 1")
        self.assertEqual(kf.mpp_from_description(desc), 0.2527)
        self.assertEqual(kf.mag_from_description(desc), 40.0)
        self.assertIsNone(kf.mpp_from_description("no tags"))


class TablesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "t.xlsx")
        make_xlsx(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_xlsx(self):
        sheets = kf.read_xlsx(self.path)
        self.assertEqual(list(sheets), ["Scores", "Notes"])
        self.assertEqual(sheets["Scores"], SCORES)
        self.assertEqual(sheets["Notes"], [[None, "note"]])

    def test_read_xlsx_from_bytes(self):
        with open(self.path, "rb") as f:
            sheets = kf.read_xlsx(io.BytesIO(f.read()))
        self.assertEqual(sheets["Scores"][2], ["34-10050", None, "0"])

    def test_participants(self):
        n, per_sheet = kf.participants(kf.read_xlsx(self.path))
        self.assertEqual(n, 2)
        self.assertEqual(per_sheet, {"Scores": {"column": 0, "ids": 2}})

    def test_summarise_table(self):
        s = kf.summarise_table(SCORES)
        self.assertEqual(s["header"], ["Participant ID", "Mesangial expansion", "Score"])
        self.assertEqual(s["n_rows"], 3)
        self.assertEqual(s["header_row"], 0)
        cols = {c["name"]: c for c in s["columns"]}
        self.assertEqual(cols["Participant ID"]["distinct"], 2)
        self.assertEqual(cols["Participant ID"]["values"], {"27-10074": 2, "34-10050": 1})
        self.assertEqual(cols["Mesangial expansion"]["filled"], 2)
        self.assertEqual(cols["Mesangial expansion"]["values"], {"present": 2})
        self.assertEqual(cols["Score"]["distinct"], 3)

    def test_summarise_table_hides_values_of_wide_columns(self):
        rows = [["id"]] + [[f"27-{10000 + i}"] for i in range(13)]
        s = kf.summarise_table(rows)
        self.assertEqual(s["columns"][0]["distinct"], 13)
        self.assertNotIn("values", s["columns"][0])

    def test_summarise_empty(self):
        self.assertEqual(kf.summarise_table([[None], []])["n_rows"], 0)

    def test_tiv_report(self):
        r = kf.tiv_report(self.path)
        self.assertTrue(r["ok"])
        self.assertEqual(r["participants"], 2)
        self.assertEqual(r["sheets"]["Scores"]["n_rows"], 3)


class PackageTest(unittest.TestCase):
    def test_list_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("a/", "")
            z.writestr("a/x_mask.TIF", b"1234")
            z.writestr("a/y.tif", b"12")
            z.writestr("a/s.svs", b"123")
            z.writestr("README.md", "hello")
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
            info = kf.list_zip(z)
        self.assertEqual(info["by_ext"], {"md": 1, "svs": 1, "tif": 2})
        self.assertEqual(len(info["members"]), 4)
        self.assertEqual({m["name"]: m["bytes"] for m in info["members"]}["a/x_mask.TIF"], 4)

    def test_xml_summary(self):
        data = (b'<Annotations MicronsPerPixel="0.25"><Annotation Id="1"><Regions>'
                b'<Region Id="1"/><Region Id="2"/></Regions></Annotation></Annotations>')
        s = kf.xml_summary(data)
        self.assertEqual(s["root"], "Annotations")
        self.assertEqual(s["elements"], 5)
        self.assertEqual(s["top_tags"]["Region"], 2)
        self.assertEqual(s["root_attrs"], {"MicronsPerPixel": "0.25"})


def passing():
    dl = {k: {"ok": True, "size_ok": True, "bytes": 100} for k in ("seg_small", "pas_small", "tiv", "pas_large")}
    return {"downloads": dl,
            "slides": {"pas_small": {"ok": True, "levels": [[8000, 6400, 3]], "low_read_seconds": 1.0,
                                     "tiles_decoded": 64, "rss_mb_after": 300},
                       "pas_large": {"ok": True, "levels": [[80000, 64000, 3]], "low_read_seconds": 20.0,
                                     "tiles_decoded": 64, "rss_mb_after": 1500}},
            "package": {"ok": True, "masks": [{"factor": 1}], "svs_members": [{"bytes": 100}]},
            "tiv": {"ok": True, "participants": 341}, "large_minutes": 12.0}


class VerdictTest(unittest.TestCase):
    def test_all_pass(self):
        v = kf.verdicts(passing())
        self.assertEqual(v["overall"], "feasible")
        for k in ("P1_access", "P2_small_slide", "P3_large_slide", "P4_mask_alignment",
                  "P5_tiv_participants", "P6_package_holds_slide"):
            self.assertEqual(v[k], "pass", k)

    def test_large_slide_over_memory(self):
        r = passing()
        r["slides"]["pas_large"]["rss_mb_after"] = 2600
        v = kf.verdicts(r)
        self.assertEqual(v["P3_large_slide"], "fail")
        self.assertEqual(v["overall"], "feasible for small slides only")

    def test_large_download_failed(self):
        r = passing()
        r["downloads"]["pas_large"] = {"ok": False, "size_ok": False}
        del r["slides"]["pas_large"]
        self.assertEqual(kf.verdicts(r)["P3_large_slide"], "fail")

    def test_package_missing(self):
        r = passing()
        r["downloads"]["seg_small"] = {"ok": False, "size_ok": False}
        r["package"] = {}
        v = kf.verdicts(r)
        self.assertEqual(v["P1_access"], "fail")
        self.assertEqual(v["P4_mask_alignment"], "untestable")
        self.assertEqual(v["P6_package_holds_slide"], "untestable")
        self.assertEqual(v["overall"], "not shown feasible")

    def test_mask_not_aligned(self):
        r = passing()
        r["package"]["masks"] = [{"factor": None}]
        v = kf.verdicts(r)
        self.assertEqual(v["P4_mask_alignment"], "fail")
        self.assertEqual(v["overall"], "not shown feasible")

    def test_tiv_count_outside_window_does_not_change_overall(self):
        r = passing()
        r["tiv"]["participants"] = 300
        v = kf.verdicts(r)
        self.assertEqual(v["P5_tiv_participants"], "fail")
        self.assertEqual(v["overall"], "feasible")

    def test_slow_small_slide(self):
        r = passing()
        r["slides"]["pas_small"]["low_read_seconds"] = 75
        self.assertEqual(kf.verdicts(r)["P2_small_slide"], "fail")


if __name__ == "__main__":
    unittest.main()
