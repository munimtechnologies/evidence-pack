# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the v1.1 changes to kidney/kpmp_feasibility.py (standard library only; no network).

Run v1 (2026-10-18) scored P4 "fail" because hw_of() returned None for the 7-plane KPMP mask.
These tests pin the measured shapes from that run and the new range probe."""
import io
import unittest
import urllib.error

try:
    from kidney import kpmp_feasibility as kf
except ImportError:  # run from inside kidney/
    import kpmp_feasibility as kf


class FakeRangeResponse(io.BytesIO):
    def __init__(self, data, status, content_range=""):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Range": content_range} if content_range else {}


class HwOfV11Test(unittest.TestCase):
    def test_seven_plane_mask_measured_in_run_v1(self):
        # S-1904-008128_PAS_2of2.ome.tif: shape (7, 17750, 15943) uint16; slide level 0: (17750, 15943, 3)
        self.assertEqual(kf.hw_of((7, 17750, 15943)), (17750, 15943))
        self.assertEqual(kf.aligned(kf.hw_of((7, 17750, 15943)), kf.hw_of((17750, 15943, 3))), 1)

    def test_plane_limit(self):
        self.assertEqual(kf.MAX_PLANES, 16)
        self.assertEqual(kf.hw_of((16, 100, 200)), (100, 200))
        self.assertIsNone(kf.hw_of((17, 100, 200)))
        self.assertEqual(kf.hw_of((17, 100, 200), max_planes=17), (100, 200))

    def test_v1_cases_unchanged(self):
        self.assertEqual(kf.hw_of((100, 200)), (100, 200))
        self.assertEqual(kf.hw_of((100, 200, 3)), (100, 200))
        self.assertEqual(kf.hw_of((3, 100, 200)), (100, 200))
        self.assertEqual(kf.hw_of((1, 100, 200)), (100, 200))
        self.assertIsNone(kf.hw_of((5, 6, 7, 8)))

    def test_version(self):
        self.assertEqual(kf.VERSION, "1.1")


class RangeProbeTest(unittest.TestCase):
    def test_honoured_206(self):
        seen = []

        def get(url, headers):
            seen.append((url, dict(headers)))
            return FakeRangeResponse(b"P" * 1024, 206, "bytes 0-1023/11806912")

        p = kf.range_probe("http://example.invalid/pkg.zip", get=get)
        self.assertEqual(seen, [("http://example.invalid/pkg.zip", {"Range": "bytes=0-1023"})])
        self.assertEqual(p, {"ok": True, "status": 206, "content_range": "bytes 0-1023/11806912",
                             "bytes": 1024, "honoured": True})

    def test_ignored_200_reads_one_extra_byte_only(self):
        def get(url, headers):
            return FakeRangeResponse(b"P" * 5000, 200)

        p = kf.range_probe("http://example.invalid/pkg.zip", get=get)
        self.assertEqual(p["status"], 200)
        self.assertEqual(p["bytes"], 1025)
        self.assertFalse(p["honoured"])
        self.assertEqual(p["content_range"], "")

    def test_http_error(self):
        def get(url, headers):
            raise urllib.error.HTTPError(url, 416, "Range Not Satisfiable", {}, None)

        p = kf.range_probe("http://example.invalid/pkg.zip", get=get)
        self.assertEqual(p, {"ok": False, "error": "HTTP 416", "honoured": False})

    def test_other_error(self):
        def get(url, headers):
            raise TimeoutError("slow")

        p = kf.range_probe("http://example.invalid/pkg.zip", get=get)
        self.assertFalse(p["ok"])
        self.assertFalse(p["honoured"])
        self.assertIn("TimeoutError", p["error"])

    def test_custom_nbytes(self):
        def get(url, headers):
            self.assertEqual(headers, {"Range": "bytes=0-9"})
            return FakeRangeResponse(b"P" * 10, 206, "bytes 0-9/100")

        p = kf.range_probe("u", get=get, nbytes=10)
        self.assertTrue(p["honoured"])
        self.assertEqual(p["bytes"], 10)


if __name__ == "__main__":
    unittest.main()
