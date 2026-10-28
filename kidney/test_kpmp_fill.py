# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_fill: range reads over an in-memory zip shaped like a KPMP package,
and the HTTP layer against a fake opener. No network."""
import csv
import io
import json
import os
import random
import tempfile
import unittest
import zipfile

from kidney import kpmp_census as kc
from kidney import kpmp_fill as kf

SEG_HEADER = ["Access", "Platform", "Data Format", "Data Category", "Size", "File Name", "Internal Package ID",
              "Experimental Strategy", "Workflow Type", "Participant ID", "DOIs"]
WORKBOOK = b"workbook bytes " * 200
FINAL = "https://example.org/final"


def package_zip():
    """A zip like a KPMP package: a large incompressible slide and mask, and the small members kept."""
    rnd = random.Random(7)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pkg/S-2006-000001_PAS.svs", rnd.randbytes(400_000))
        z.writestr("pkg/S-2006-000001_features_v2.xlsx", WORKBOOK)
        z.writestr("pkg/S-2006-000001_mask.ome.xml", "<OME/>")
        z.writestr("pkg/README.md", "# README\n")
        z.writestr("pkg/S-2006-000001_mask.tif", rnd.randbytes(100_000))
    return buf.getvalue()


class Fake:
    def __init__(self, data):
        self.data, self.calls = data, []

    def fetch(self, url, start, end):
        self.calls.append((start, end))
        return self.data[start:end + 1]

    def probe(self, url):
        return (FINAL, len(self.data)), ""


class FakeResp:
    def __init__(self, status, body=b"", headers=None):
        self.status, self.body, self.headers = status, body, headers or {}
        self.read_called = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        self.read_called = True
        return self.body

    def geturl(self):
        return FINAL


def no_probe(url):
    raise AssertionError("probed a cached package")


class TestRangeFile(unittest.TestCase):
    def test_seek_read_tell(self):
        data = bytes(range(256)) * 40
        fk = Fake(data)
        f = kf.RangeFile("u", len(data), fk.fetch, block=1000)
        self.assertEqual(f.read(10), data[:10])
        self.assertEqual(f.tell(), 10)
        self.assertEqual(f.read(5), data[10:15])
        self.assertEqual(len(fk.calls), 1)
        f.seek(-22, 2)
        self.assertEqual(f.read(), data[-22:])
        self.assertEqual(f.read(5), b"")
        f.seek(3000)
        self.assertEqual(f.read(2500), data[3000:5500])
        f.seek(-100, 1)
        self.assertEqual(f.tell(), 5400)
        self.assertEqual(f.read(50), data[5400:5450])
        self.assertEqual(len(fk.calls), 3)
        with self.assertRaises(OSError):
            f.seek(-1)

    def test_zip_member_without_the_slide(self):
        data = package_zip()
        f = kf.RangeFile("u", len(data), Fake(data).fetch, block=4096)
        with zipfile.ZipFile(f) as z:
            self.assertIn("pkg/README.md", z.namelist())
            self.assertEqual(z.read("pkg/S-2006-000001_features_v2.xlsx"), WORKBOOK)
        self.assertLess(f.bytes, len(data) // 4)


class TestFillPackage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = {"package": "pkg-1", "name": "abc_S-2006-000001_Seg_Masks_Features_v2.zip", "listed": "1 MB",
                  "participants": ["30-10000"], "version": "v2", "slide": "S-2006-000001"}

    def test_range_fill_keeps_small_members(self):
        data = package_zip()
        fk = Fake(data)
        rec = kf.fill_package(self.p, self.tmp, fk.probe, fk.fetch, block=4096)
        self.assertTrue(rec["ok"], rec.get("error"))
        self.assertEqual(rec["via"], "range")
        pdir = os.path.join(self.tmp, "pkg-1")
        self.assertEqual(sorted(os.listdir(pdir)), ["README.md", "S-2006-000001_features_v2.xlsx",
                                                    "S-2006-000001_mask.ome.xml", "record.json"])
        with open(os.path.join(pdir, "S-2006-000001_features_v2.xlsx"), "rb") as f:
            self.assertEqual(f.read(), WORKBOOK)
        with open(os.path.join(pdir, "record.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f)["ok"])
        self.assertEqual(len(rec["members"]), 5)
        self.assertLess(rec["bytes_read"], len(data) // 4)
        self.assertFalse(rec["size_ok"])
        again = kf.fill_package(self.p, self.tmp, no_probe, fk.fetch)
        self.assertEqual(again, {"ok": True, "cached": True, "via": "range"})

    def test_no_range_skips_without_download(self):
        rec = kf.fill_package(self.p, self.tmp, lambda url: (None, "HTTP 200"), None)
        self.assertFalse(rec["ok"])
        self.assertTrue(rec["range_unsupported"])
        self.assertEqual(rec["error"], "HTTP 200")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "pkg-1", "record.json")))

    def test_bad_zip_writes_no_record(self):
        fk = Fake(b"not a zip" * 100)
        rec = kf.fill_package(self.p, self.tmp, fk.probe, fk.fetch, block=64)
        self.assertFalse(rec["ok"])
        self.assertIn("BadZipFile", rec["error"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "pkg-1", "record.json")))


class TestHttp(unittest.TestCase):
    def test_probe_206(self):
        seen = []

        def opener(req, timeout):
            seen.append(req.get_header("Range"))
            return FakeResp(206, b"P", {"Content-Range": "bytes 0-0/123456"})
        got, why = kf.http_probe("https://atlas.example.org/x", opener)
        self.assertEqual(got, (FINAL, 123456))
        self.assertEqual(why, "")
        self.assertEqual(seen, ["bytes=0-0"])

    def test_probe_200_is_not_read(self):
        resp = FakeResp(200, b"whole archive")
        got, why = kf.http_probe("https://atlas.example.org/x", lambda req, timeout: resp)
        self.assertIsNone(got)
        self.assertEqual(why, "HTTP 200")
        self.assertFalse(resp.read_called)

    def test_probe_bad_content_range(self):
        got, why = kf.http_probe("https://atlas.example.org/x",
                                 lambda req, timeout: FakeResp(206, b"P", {"Content-Range": "bytes 0-0/*"}))
        self.assertIsNone(got)
        self.assertIn("Content-Range", why)

    def test_probe_error(self):
        def opener(req, timeout):
            raise OSError("refused")
        got, why = kf.http_probe("https://atlas.example.org/x", opener)
        self.assertIsNone(got)
        self.assertIn("refused", why)

    def test_range(self):
        def opener(req, timeout):
            self.assertEqual(req.get_header("Range"), "bytes=10-19")
            return FakeResp(206, b"0123456789")
        self.assertEqual(kf.http_range("https://example.org/u", 10, 19, opener), b"0123456789")
        resp = FakeResp(200, b"whole")
        with self.assertRaises(kf.RangeUnsupported):
            kf.http_range("https://example.org/u", 0, 9, lambda req, timeout: resp)
        self.assertFalse(resp.read_called)

    def test_range_retries(self):
        calls = []

        def opener(req, timeout):
            calls.append(1)
            if len(calls) < 3:
                raise OSError("reset")
            return FakeResp(206, b"ok")
        self.assertEqual(kf.http_range("https://example.org/u", 0, 1, opener, pause=lambda s: None), b"ok")
        self.assertEqual(len(calls), 3)


class TestMain(unittest.TestCase):
    def test_main_fills_then_finds_cached(self):
        tmp = tempfile.mkdtemp()
        seg = os.path.join(tmp, "seg.csv")
        with open(seg, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SEG_HEADER)
            for k in range(2):
                w.writerow(["open", "", "tif xml xlsx svs md", "Pathology", "1 MB",
                            "id%d_S-2006-00000%d_Seg_Masks_Features_v2.zip" % (k, k), "pkg-%d" % k,
                            kc.STRATEGY, "", "30-1000%d" % k, ""])
        desc, clin = os.path.join(tmp, "desc.csv"), os.path.join(tmp, "clin.csv")
        for path in (desc, clin):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(SEG_HEADER)
        fk = Fake(package_zip())
        data_dir, out_dir = os.path.join(tmp, "data"), os.path.join(tmp, "out")
        argv = ["--file-list", seg, "--descriptor-list", desc, "--clinical-list", clin,
                "--data-dir", data_dir, "--out-dir", out_dir]
        self.assertEqual(kf.main(argv, probe=fk.probe, fetch=fk.fetch), 0)
        with open(os.path.join(out_dir, "fill.json"), encoding="utf-8") as f:
            res = json.load(f)
        self.assertEqual(res["listed"], 2)
        self.assertEqual(res["status"], {"filled_range": 2})
        self.assertEqual(res["whole_files"], {})
        for k in range(2):
            self.assertTrue(os.path.exists(os.path.join(data_dir, "kpmp-census", "pkg-%d" % k, "record.json")))
        self.assertEqual(kf.main(argv, probe=no_probe, fetch=fk.fetch), 0)
        with open(os.path.join(out_dir, "fill.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["status"], {"already_cached": 2})


if __name__ == "__main__":
    unittest.main()
