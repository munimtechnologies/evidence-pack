"""Unit tests for check_repro.py on synthetic files only (no network, no published data).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import tempfile
import unittest
from pathlib import Path

import check_repro


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


class Compare(unittest.TestCase):
    def test_equal(self):
        self.assertEqual(check_repro.compare({"a": 1, "b": [2]}, {"b": [2], "a": 1}), [])

    def test_differs(self):
        self.assertEqual(check_repro.compare({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 0}),
                         ["b", "c"])


class CheckFiles(unittest.TestCase):
    def test_empty_publication_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub = Path(tmp)
            write(pub / "labels.json", {"copies": []})
            write(pub / "sites.json", {})
            write(pub / "mutation-manifest.json", {"copies": []})
            write(pub / "checker-out" / "summary.json", {"files": []})
            problems = check_repro.check_files(pub)
        self.assertIn("labels.json SHA-256 differs from log entry 7", problems)
        self.assertIn("sites.json SHA-256 differs from log entry 7", problems)
        self.assertIn("checker summary files differ from the 20 H-A texts", problems)
        self.assertIn("checker/P4-cut.md.json missing", problems)
        self.assertIn("baseline/P5-copy10.md.json missing", problems)
        self.assertEqual(len([p for p in problems if p.endswith(" missing")]), 40)

    def test_tampered_report_and_summary(self):
        chk, base = check_repro.REPORTS["P4-cut.md"]
        with tempfile.TemporaryDirectory() as tmp:
            pub = Path(tmp)
            write(pub / "labels.json", {"copies": [{"file": "P4-cut.md", "sha256": "x"}]})
            write(pub / "sites.json", {})
            write(pub / "mutation-manifest.json", {"copies": [{"file": "P4-cut.md", "sha256": "y"}]})
            write(pub / "checker-out" / "summary.json",
                  {"files": [{"file": "P4-cut.md", "checker_sha256": chk, "baseline_sha256": "z"}],
                   "max_checker_seconds": 0.564})
            write(pub / "checker-out" / "checker" / "P4-cut.md.json", {"flags": []})
            problems = check_repro.check_files(pub)
        self.assertIn("P4-cut.md: summary hashes differ from the sealed job's", problems)
        self.assertIn("checker/P4-cut.md.json SHA-256 differs from the sealed job's", problems)
        self.assertIn("baseline/P4-cut.md.json missing", problems)
        self.assertIn("mutation manifest copy hashes differ from labels.json", problems)
        self.assertNotIn("checker summary max_checker_seconds differs from log entry 8", problems)


if __name__ == "__main__":
    unittest.main()
