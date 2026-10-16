# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Checks bucher_fung.py against the hand-computed values in the candidate-6 note."""
import unittest

import bucher_fung


class TestBucher(unittest.TestCase):
    def setUp(self):
        self.r = {(x["drug"], x["outcome"], x["window"]): x for x in bucher_fung.run()}

    def check(self, key, hr, lo, hi):
        x = self.r[key]
        self.assertAlmostEqual(x["hr"], hr, delta=0.005)
        self.assertAlmostEqual(x["lo"], lo, delta=0.01)
        self.assertAlmostEqual(x["hi"], hi, delta=0.01)

    def test_terazosin(self):
        self.check(("terazosin", "AD", "overall"), 0.745, 0.646, 0.859)
        self.check(("terazosin", "PD", "overall"), 0.822, 0.714, 0.947)
        self.check(("terazosin", "AD", ">1yr"), 0.767, 0.643, 0.914)
        self.check(("terazosin", "PD", ">1yr"), 0.747, 0.630, 0.887)
        self.check(("terazosin", "death", "overall"), 1.043, 0.994, 1.095)

    def test_doxazosin(self):
        self.check(("doxazosin", "AD", "overall"), 0.857, 0.756, 0.972)
        self.check(("doxazosin", "PD", "overall"), 0.878, 0.771, 1.000)


if __name__ == "__main__":
    unittest.main()
