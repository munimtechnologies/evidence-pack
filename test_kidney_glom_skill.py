# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the kidney-glom-check skill: its SKILL.md front matter, the numbers it quotes, and its
scripts/zip_range.py on local zip files (no network). Made with AI agents (Claude) working in MV2's name."""
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HERE, "skills", "kidney-glom-check")
RESULTS = os.path.join(HERE, "findings", "kidney-glom-stage4-results-v1-2026-11-10.md")


def load_zip_range():
    path = os.path.join(SKILL_DIR, "scripts", "zip_range.py")
    spec = importlib.util.spec_from_file_location("kidney_skill_zip_range", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


zr = load_zip_range()

A = b"stored member " * 1000
B = bytes(range(256)) * 4000  # 1,024,000 bytes, deflated


def make_zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("models/"), b"")
        z.writestr("models/a/one.pth", A, compress_type=zipfile.ZIP_STORED)
        z.writestr("models/b/two.pth", B, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("other/three.txt", b"x", compress_type=zipfile.ZIP_DEFLATED)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestSkillFile(unittest.TestCase):
    def test_front_matter(self):
        text = read(os.path.join(SKILL_DIR, "SKILL.md"))
        self.assertTrue(text.startswith("---\n"))
        head = text.split("---\n")[1]
        self.assertIn("name: kidney-glom-check\n", head)
        self.assertIn("license: Apache-2.0\n", head)
        self.assertIn("description: Use when", head)
        self.assertEqual(head.count("license:"), 1)

    def test_quoted_numbers_match_results_note(self):
        skill = read(os.path.join(SKILL_DIR, "SKILL.md"))
        note = read(RESULTS)
        for value in ("0.734", "0.777", "0.000", "0.912", "0.965", "0.813", "0.157"):
            self.assertIn(value, skill, value)
            self.assertIn(value, note, value)
        self.assertIn("0.805", skill)
        self.assertIn("0.912 x 0.805 = 0.734", note)

    def test_ascii_only(self):
        for path in (os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(SKILL_DIR, "scripts", "zip_range.py")):
            self.assertTrue(all(ord(c) < 128 for c in read(path)), path)


class TestZipRange(unittest.TestCase):
    def test_listing_and_extract(self):
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "t.zip")
            make_zip(zp)
            src = zr.FileSource(zp)
            members, z64 = zr.listing(src)
            self.assertFalse(z64)
            self.assertEqual([m["name"] for m in members],
                             ["models/", "models/a/one.pth", "models/b/two.pth", "other/three.txt"])
            self.assertEqual(members[1]["method"], 0)
            self.assertEqual(members[2]["method"], 8)
            self.assertEqual(members[2]["usize"], 1024000)
            n, ok = zr.extract(src, members[2], os.path.join(d, "x", "two.pth"))
            self.assertTrue(ok)
            self.assertEqual(n, len(B))
            with open(os.path.join(d, "x", "two.pth"), "rb") as f:
                self.assertEqual(f.read(), B)

    def test_main(self):
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "t.zip")
            make_zip(zp)
            out, dest = os.path.join(d, "out"), os.path.join(d, "dest")
            rc = zr.main(["--file", zp, "--out-dir", out, "--prefix", "models/", "--dest", dest])
            self.assertEqual(rc, 0)
            with open(os.path.join(out, "extract.json"), encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual((rep["members"], rep["files"], rep["selected"]), (4, 3, 2))
            self.assertEqual([e["crc_ok"] for e in rep["extracted"]], [True, True])
            with open(os.path.join(dest, "models", "a", "one.pth"), "rb") as f:
                self.assertEqual(f.read(), A)
            self.assertFalse(os.path.exists(os.path.join(dest, "other", "three.txt")))
            zr.main(["--file", zp, "--out-dir", out, "--prefix", "models/", "--dest", dest])
            with open(os.path.join(out, "extract.json"), encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual([e["cached"] for e in rep["extracted"]], [True, True])
            with self.assertRaises(SystemExit):
                zr.main(["--file", zp, "--out-dir", out, "--prefix", "models/", "--dest", dest, "--max-bytes", "10"])


if __name__ == "__main__":
    unittest.main()
