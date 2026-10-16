# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import unittest

from faers_alpha1 import analyse, ror, search_for

# Counts read from openFDA (last_updated 2026-07-30) on 2026-10-15, before this script existed.
HAND = {
    "TERAZOSIN": {"N": 2503, "FALL": 136, "SYNCOPE": 52, "ORTHOSTATIC HYPOTENSION": 20},
    "DOXAZOSIN": {"N": 9831, "FALL": 393, "SYNCOPE": 374, "ORTHOSTATIC HYPOTENSION": 173},
    "ALFUZOSIN": {"N": 1493, "FALL": 69, "SYNCOPE": 31, "ORTHOSTATIC HYPOTENSION": 19},
    "TAMSULOSIN": {"N": 6472, "FALL": 262, "SYNCOPE": 138, "ORTHOSTATIC HYPOTENSION": 77},
    "FINASTERIDE": {"N": 15502, "FALL": 777, "SYNCOPE": 258, "ORTHOSTATIC HYPOTENSION": 130},
    "DUTASTERIDE": {"N": 3059, "FALL": 140, "SYNCOPE": 77, "ORTHOSTATIC HYPOTENSION": 55},
}


class TestRor(unittest.TestCase):
    def test_terazosin_falls_matches_hand(self):
        est, lo, hi = ror(136, 2503, 262, 6472)
        self.assertAlmostEqual(est, 1.362, places=2)
        self.assertAlmostEqual(lo, 1.101, places=2)
        self.assertAlmostEqual(hi, 1.684, places=2)

    def test_identical_arms_give_one(self):
        est, lo, hi = ror(10, 100, 10, 100)
        self.assertAlmostEqual(est, 1.0)
        self.assertLess(lo, 1.0)
        self.assertGreater(hi, 1.0)

    def test_hand_table(self):
        rows = {(r["drug"], r["event"]): r for r in analyse(HAND)}
        self.assertNotIn("ror", rows[("TAMSULOSIN", "FALL")])
        self.assertAlmostEqual(rows[("DOXAZOSIN", "SYNCOPE")]["ror"], 1.815, places=2)
        self.assertAlmostEqual(rows[("TERAZOSIN", "ORTHOSTATIC HYPOTENSION")]["ror"], 0.669, places=2)
        self.assertAlmostEqual(rows[("FINASTERIDE", "FALL")]["ror"], 1.251, places=2)
        self.assertAlmostEqual(rows[("FINASTERIDE", "SYNCOPE")]["hi"], 0.957, places=2)
        self.assertAlmostEqual(rows[("DUTASTERIDE", "ORTHOSTATIC HYPOTENSION")]["lo"], 1.073, places=2)

    def test_query_text(self):
        q = search_for("TERAZOSIN", "FALL")
        self.assertIn('generic_name:"TERAZOSIN"', q)
        self.assertIn("patientonsetageunit:801", q)
        self.assertIn('reactionmeddrapt.exact:"FALL"', q)


if __name__ == "__main__":
    unittest.main()
