# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_subset."""
import contextlib
import csv
import io
import os
import tempfile
import unittest

from kidney import kpmp_census as kc
from kidney import kpmp_subset as ks

HEAD = ["Access", "Platform", "Data Format", "Data Category", "Size", "File Name", "Internal Package ID",
        "Experimental Strategy", "Workflow Type", "Participant ID", "DOIs"]


def row(name, package, size, participant):
    return ["open", "", "tif xml xlsx svs md", "Pathology", size, name, package, kc.STRATEGY, "", participant, ""]


class TestSubset(unittest.TestCase):
    def test_keeps_one_version(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, "files.csv"), os.path.join(d, "sub", "files-v2.csv")
            with open(src, "w", newline="", encoding="utf-8-sig") as f:  # with a BOM, as exported
                w = csv.writer(f, quoting=csv.QUOTE_ALL)
                w.writerow(HEAD)
                w.writerow(row("aaa_S-2311-011607_Seg_Masks_Features.zip", "pkg1", "128 MB", "30-1"))
                w.writerow(row("bbb_S-1908-000893_Seg_Masks_Features_v2.zip", "pkg2", "71.8 MB", "31-2"))
                w.writerow(row("ccc_S-1908-009781_Seg_Masks_Features_v2.zip", "pkg3", "67.7 MB", "30-3"))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ks.main(["--file-list", src, "--version", "v2", "--out", dst]), 0)
            self.assertEqual(ks.subset(src, os.path.join(d, "files-v1.csv"), "v1"), {"kept": 1, "dropped": 2})
            with open(dst, encoding="utf-8") as f:
                first = f.readline()
            v2 = kc.load_packages(dst)
            v1 = kc.load_packages(os.path.join(d, "files-v1.csv"))
        self.assertTrue(first.startswith('"Access","Platform","Data Format"'))
        self.assertEqual([p["package"] for p in v2], ["pkg2", "pkg3"])
        self.assertEqual({p["version"] for p in v2}, {"v2"})
        self.assertEqual(v2[0]["listed"], "71.8 MB")
        self.assertEqual(v2[0]["participants"], ["31-2"])
        self.assertEqual(v2[1]["slide"], "S-1908-009781")
        self.assertEqual([p["package"] for p in v1], ["pkg1"])


if __name__ == "__main__":
    unittest.main()
