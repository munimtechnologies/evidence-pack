# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for kidney.kpmp_twins on synthetic slides: two serial sections a fixed shift apart, and
one section with no repeat. Workbook fixtures use the raw v2 sheet and column names the census jobs
recorded (gloms, s_gloms, tubs, arts; x1 | x2 | y1 | y2)."""
import csv
import json
import os
import random
import tempfile
import unittest

from kidney import kpmp_census as kc
from kidney import kpmp_twins as kw
from kidney.test_kpmp_tbm0 import write_xlsx

SEG_HEADER = ["Access", "Platform", "Data Format", "Data Category", "Size", "File Name", "Internal Package ID",
              "Experimental Strategy", "Workflow Type", "Participant ID", "DOIs"]
HEAD = ["x1", "x2", "y1", "y2", "Area"]
OFFSET = (300.0, 40000.0)


def two_sections(seed=1, n=30, extra=0, tubules=0, offset=OFFSET):
    """n glomeruli and n arteries (and some tubules) in one section, each repeated in a second section
    shifted by offset with small jitter; extra unrepeated glomeruli far away."""
    rng = random.Random(seed)
    objs = {s: [] for s in kw.SHEETS}
    for sheet, count in (("gloms", n), ("arts", n), ("tubs", tubules)):
        for _ in range(count):
            r, c = rng.uniform(1000, 11000), rng.uniform(1000, 11000)
            h, w = rng.uniform(200, 400), rng.uniform(200, 400)
            objs[sheet].append((r, c, h, w))
            objs[sheet].append((r + offset[0] + rng.uniform(-20, 20), c + offset[1] + rng.uniform(-20, 20),
                                h * rng.uniform(0.97, 1.03), w * rng.uniform(0.97, 1.03)))
    for _ in range(extra):
        objs["gloms"].append((rng.uniform(20000, 30000), rng.uniform(80000, 90000),
                              rng.uniform(200, 400), rng.uniform(200, 400)))
    return objs


def one_section(seed=2, n=60):
    rng = random.Random(seed)
    objs = {s: [] for s in kw.SHEETS}
    for sheet in ("gloms", "arts"):
        for _ in range(n):
            objs[sheet].append((rng.uniform(1000, 30000), rng.uniform(1000, 90000),
                                rng.uniform(200, 400), rng.uniform(200, 400)))
    return objs


class TestGeometry(unittest.TestCase):
    def test_displacements(self):
        objs = [(0, 0, 100, 100), (0, 3000, 105, 100), (0, 1000, 100, 100), (5000, 0, 300, 300)]
        self.assertEqual(sorted(kw.displacements(objs)), [(0, 2000), (0, 3000)])

    def test_mode(self):
        disps = [(0, 5000)] * 3 + [(100, 5100)] * 2 + [(9000, 9000)]
        count, pairs = kw.mode(disps)
        self.assertEqual(count, 5)
        self.assertEqual(len(pairs), 5)
        self.assertEqual(kw.mode([]), (0, []))

    def test_offset_error_either_sign(self):
        self.assertEqual(kw.offset_error([300, 40000], [-300, -40000]), 0)
        self.assertEqual(kw.offset_error([300, 40000], [300, 40100]), 100)


class TestDetect(unittest.TestCase):
    def test_two_sections_found(self):
        objs = two_sections(extra=5, tubules=100)
        d = kw.detect(objs)
        self.assertTrue(d["repeat"])
        self.assertGreaterEqual(d["mode"], 60)
        self.assertLess(d["null_max"], d["mode"])
        self.assertLess(abs(d["offset"][0] - OFFSET[0]), 50)
        self.assertLess(abs(d["offset"][1] - OFFSET[1]), 50)
        t = kw.twins(objs, d["offset"])
        self.assertEqual(t["gloms"], [65, 60])
        self.assertEqual(t["arts"], [60, 60])
        self.assertEqual(t["tubs"], [200, 200])
        self.assertEqual(t["s_gloms"], [0, 0])

    def test_one_section_not_found(self):
        d = kw.detect(one_section())
        self.assertFalse(d["repeat"])
        self.assertIsNone(d["offset"])
        self.assertLess(d["mode"], kw.MIN_PAIRS)


class TestWorkbook(unittest.TestCase):
    def test_objects_reads_x_as_row(self):
        d = tempfile.mkdtemp()
        write_xlsx(os.path.join(d, "S-2006-000001_features_v2.xlsx"),
                   {"gloms": [HEAD, [100, 300, 1000, 1400, 5.0], [500, 400, 0, 10, 1.0]],
                    "s_gloms": [HEAD], "tubs": [HEAD, [0, 10, 0, 20, 1.0]],
                    "arts": [["x1", "x2", "y1", "y2", "Arterial Area"]]})
        objs = kw.objects(d)
        self.assertEqual(objs["gloms"], [(200.0, 1200.0, 200.0, 400.0)])
        self.assertEqual(objs["tubs"], [(5.0, 10.0, 10.0, 20.0)])
        self.assertEqual(objs["s_gloms"], [])
        self.assertEqual(objs["arts"], [])


class TestMain(unittest.TestCase):
    def test_main_end_to_end(self):
        tmp = tempfile.mkdtemp()
        data = os.path.join(tmp, "data")
        pdir = os.path.join(data, "kpmp-census", "pkg-a")
        os.makedirs(pdir)
        objs = two_sections(extra=5, tubules=20)
        write_xlsx(os.path.join(pdir, "S-2006-000001_features_v2.xlsx"),
                   {s: [HEAD] + [[r - h / 2, r + h / 2, c - w / 2, c + w / 2, h * w] for r, c, h, w in objs[s]]
                    for s in kw.SHEETS})
        with open(os.path.join(pdir, "record.json"), "w", encoding="utf-8") as f:
            json.dump({"ok": True}, f)
        seg = os.path.join(tmp, "seg.csv")
        with open(seg, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SEG_HEADER)
            for pkg, name in (("pkg-a", "a_S-2006-000001_Seg_Masks_Features_v2.zip"),
                              ("pkg-b", "b_S-2006-000002_Seg_Masks_Features_v2.zip"),
                              ("pkg-c", "c_S-1908-000003_Seg_Masks_Features.zip")):
                w.writerow(["open", "", "tif xml xlsx svs md", "Pathology", "70 MB", name, pkg, kc.STRATEGY, "",
                            "30-10000", ""])
        ctrl = os.path.join(tmp, "controls.json")
        with open(ctrl, "w", encoding="utf-8") as f:
            json.dump({"controls": [{"package": "pkg-a", "offset": [-300, -40000]}]}, f)
        out = os.path.join(tmp, "out")
        self.assertEqual(kw.main(["--file-list", seg, "--controls", ctrl, "--data-dir", data, "--out-dir", out,
                                  "--min-slides", "1"]), 0)
        with open(os.path.join(out, "results.json"), encoding="utf-8") as f:
            res = json.load(f)
        self.assertEqual(res["packages"], {"read": 1, "not_cached": 1, "listed_v2": 2})
        self.assertEqual(res["summary"]["repeat"], 1)
        self.assertEqual(res["summary"]["sheets"]["gloms"]["with_twin"], 60)
        self.assertEqual(res["summary"]["sheets"]["tubs"]["with_twin"], 40)
        self.assertTrue(res["controls"][0]["ok"])
        self.assertEqual(res["grades"], {"T1_repeat_share": "pass", "T2_glom_twin_share": "untestable",
                                         "T3_controls": "untestable", "status": "complete"})
        self.assertNotIn("pkg-a", json.dumps(res))
        self.assertTrue(os.path.exists(os.path.join(out, "slides.json")))


if __name__ == "__main__":
    unittest.main()
