# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for meps/m8diag.py (stdlib only; no network)."""
import json
import os
import tempfile
import unittest

from meps import m8diag

PAGE = ("<p>Intro (figure 1) text.</p>"
        "<table><tr><td><p>Body (figure 2) here</p>"
        "<table><tr><td>Group</td><td>12.5</td></tr></table>"
        "</td></tr></table>")


class TestDiagnose(unittest.TestCase):
    def test_zones(self):
        d = m8diag.diagnose(PAGE)
        self.assertEqual(d["tables"], 2)
        self.assertEqual(d["layout_tables"], 1)
        self.assertEqual(d["zones"]["outside"], {"chars": 22, "cites": 1})
        self.assertEqual(d["zones"]["layout"], {"chars": 20, "cites": 1})
        self.assertEqual(d["zones"]["leaf"], {"chars": 9, "cites": 0})
        self.assertEqual(d["top_leaves"], [{"chars": 10, "cells": 2, "numeric": 1, "cites": 0}])

    def test_no_tables(self):
        d = m8diag.diagnose("<h2>Findings (Figure 3)</h2><script>var x = '(figure 9)';</script>")
        self.assertEqual(d["tables"], 0)
        self.assertEqual(d["zones"]["outside"]["cites"], 1)
        self.assertEqual(d["zones"]["layout"], {"chars": 0, "cites": 0})
        self.assertEqual(d["top_leaves"], [])

    def test_main_offline(self):
        pages = {m8diag.ROBOTS: "User-agent: *\nDisallow: /x/\n", m8diag.URL % (7, 7): PAGE}
        with tempfile.TemporaryDirectory() as tmp:
            rc = m8diag.main(["--briefs", "7", "--out-dir", tmp], get=pages.get, pause=lambda s: None)
            self.assertEqual(rc, 0)
            with open(os.path.join(tmp, "m8-diag.json")) as f:
                out = json.load(f)
        self.assertEqual(out["briefs"]["7"]["layout_tables"], 1)


if __name__ == "__main__":
    unittest.main()
