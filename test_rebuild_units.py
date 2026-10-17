# Offline tests for rebuild_units.py. Copyright 2026 Munim, Inc. (MV2). Apache-2.0.
import json
import os
import tempfile
import unittest

import rebuild_units as rb


def unit(doi, cites, far):
    return {"publisher": "MDPI", "journal": "x", "volume": 1, "year": 2016, "confirmatory": True,
            "article1": {"doi": doi, "cites": cites, "title": "t"}, "near": [],
            "far": [{"doi": doi + "f%d" % i, "cites": c} for i, c in enumerate(far)]}


class TestCompare(unittest.TestCase):
    def test_matches_and_copies_openalex(self):
        units = [unit("a", 10, [1, 2]), unit("b", 0, [5])]
        table = [{"article1_doi": "a", "article1_cites": 8, "article1_openalex": 99, "top": True, "n_far": 2},
                 {"article1_doi": "c", "article1_cites": 1, "article1_openalex": 3, "top": False, "n_far": 1}]
        c = rb.compare(units, table)
        self.assertEqual((c["v1_units"], c["rebuilt_units"], c["matched"]), (2, 2, 1))
        self.assertEqual(c["only_v1"], ["c"])
        self.assertEqual(c["only_rebuilt"], ["b"])
        self.assertEqual(c["article1_cites_change"], {"median": 2, "min": 2, "max": 2})
        self.assertEqual((c["same_top"], c["same_n_far"]), (1, 1))
        self.assertEqual(units[0]["article1"]["openalex_cites"], 99)
        self.assertNotIn("openalex_cites", units[1]["article1"])


class TestParts(unittest.TestCase):
    def test_split_keeps_order_and_limit(self):
        units = [unit("d%d" % i, i, [i]) for i in range(7)]
        one = len((json.dumps(units[0], ensure_ascii=False) + "\n").encode("utf-8"))
        with tempfile.TemporaryDirectory() as d:
            names = rb.write_parts(units, d, limit=one * 3)
            self.assertEqual(names, ["units_rebuilt_part1.jsonl", "units_rebuilt_part2.jsonl", "units_rebuilt_part3.jsonl"])
            back = []
            for n in names:
                p = os.path.join(d, n)
                self.assertLessEqual(os.path.getsize(p), one * 3 + 5)
                with open(p, encoding="utf-8") as f:
                    back += [json.loads(line) for line in f]
            self.assertEqual([u["article1"]["doi"] for u in back], ["d%d" % i for i in range(7)])

    def test_one_big_unit_still_written(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(rb.write_parts([unit("z", 1, [1])], d, limit=10), ["units_rebuilt_part1.jsonl"])


if __name__ == "__main__":
    unittest.main()
