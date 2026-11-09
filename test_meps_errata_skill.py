# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests for the meps-statbrief-errata agent skill (skills/meps-statbrief-errata/). Standard library only;
no network. Made with AI agents (Claude) working in MV2's name."""
import contextlib
import importlib.util
import io
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "skills", "meps-statbrief-errata")
SCRIPT = os.path.join(SKILL, "scripts", "meps_errata.py")
TABLE = os.path.join(SKILL, "data", "meps-statbrief-errata.csv")

_spec = importlib.util.spec_from_file_location("meps_errata", SCRIPT)
me = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(me)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = me.main(argv)
    return code, buf.getvalue()


class TestTable(unittest.TestCase):
    def setUp(self):
        self.rows = me.load(TABLE)

    def test_default_path_is_bundled_table(self):
        self.assertEqual(os.path.normcase(me.default_csv()), os.path.normcase(os.path.normpath(TABLE)))

    def test_shape(self):
        self.assertEqual(len(self.rows), 41)
        ids = [r["id"] for r in self.rows]
        self.assertEqual(len(set(ids)), 41)
        self.assertEqual(len([i for i in ids if i.startswith("MEPS-E")]), 28)
        for r in self.rows:
            self.assertRegex(r["id"], r"^MEPS-[EDR]\d{3}$")
            self.assertTrue(r["brief"].isdigit(), r["id"])
            self.assertTrue(r["what"], r["id"])
            self.assertRegex(r["note"], r"^findings/meps-[a-z0-9-]+\.md$")

    def test_e_ids_are_consecutive(self):
        e = [r["id"] for r in self.rows if r["id"].startswith("MEPS-E")]
        self.assertEqual(e, ["MEPS-E%03d" % i for i in range(1, 29)])

    def test_id_prefix_matches_kind(self):
        for r in self.rows:
            p = r["id"][5]
            if r["kind"] == "reproduction":
                self.assertEqual(p, "R", r["id"])
            elif r["kind"] == "documentation gap":
                self.assertEqual(p, "D", r["id"])
            else:
                self.assertEqual(p, "E", r["id"])

    def test_ascii_only(self):
        with open(TABLE, "rb") as f:
            data = f.read()
        self.assertTrue(all(b < 128 for b in data))

    def test_reproduction_totals(self):
        rep = [r for r in self.rows if r["kind"] == "reproduction"]
        self.assertEqual(len(rep), 11)
        self.assertEqual(sum(r["cells"] for r in rep), 430)
        self.assertEqual(sum(r["computable"] for r in rep), 408)
        self.assertEqual(sum(r["exact"] for r in rep), 347)
        self.assertEqual(sum(r["close"] for r in rep), 374)
        self.assertEqual([r["brief"] for r in rep if me.reproduces(r) is False], ["558"])
        for r in rep:
            self.assertLessEqual(r["computable"], r["cells"])
            self.assertLessEqual(r["exact"], r["computable"])
            self.assertLessEqual(r["close"], r["computable"])

    def test_slips_have_no_counts(self):
        for r in self.rows:
            if r["kind"] != "reproduction":
                self.assertIsNone(r["computable"], r["id"])
                self.assertIsNone(me.reproduces(r))


class TestSelect(unittest.TestCase):
    def setUp(self):
        self.rows = me.load(TABLE)

    def ids(self, **kw):
        return [r["id"] for r in me.select(self.rows, **kw)]

    def test_brief(self):
        self.assertEqual(self.ids(brief="558"), ["MEPS-E008", "MEPS-E009", "MEPS-R011"])
        self.assertEqual(self.ids(brief="#558"), self.ids(brief="stat558"))
        self.assertEqual(self.ids(brief="481"), ["MEPS-E013", "MEPS-E014", "MEPS-E019", "MEPS-E022", "MEPS-E023"])
        self.assertEqual(self.ids(brief="192"), ["MEPS-E018", "MEPS-E024"])
        self.assertEqual(self.ids(brief="99"), ["MEPS-E026", "MEPS-E027"])
        self.assertEqual(self.ids(brief="9999"), [])

    def test_value(self):
        self.assertEqual(self.ids(brief="558", value="6.2"), ["MEPS-E009"])
        self.assertEqual(self.ids(brief="491", value="14.4%"), ["MEPS-E012"])
        self.assertEqual(self.ids(value="89.2"), ["MEPS-E011"])
        self.assertEqual(self.ids(brief="481", value="17.9"), ["MEPS-E013"])
        self.assertEqual(self.ids(brief="481", value="27.36"), ["MEPS-E019"])
        self.assertEqual(self.ids(brief="78", value="18.1"), ["MEPS-E015"])
        self.assertEqual(self.ids(brief="192", value="19.0 percent"), ["MEPS-E018"])
        self.assertEqual(self.ids(value="67.2"), ["MEPS-E021"])
        self.assertEqual(self.ids(brief="434", value="41.4"), ["MEPS-E020"])
        self.assertEqual(self.ids(brief="558", value="11.1"), [])
        self.assertEqual(self.ids(value="no number"), [])

    def test_kind_grep_ids(self):
        self.assertEqual(self.ids(kind="Figure vs text"),
                         ["MEPS-E010", "MEPS-E011", "MEPS-E012", "MEPS-E013", "MEPS-E015", "MEPS-E016",
                          "MEPS-E018", "MEPS-E019", "MEPS-E020", "MEPS-E026"])
        self.assertEqual(self.ids(kind="text"),
                         ["MEPS-E005", "MEPS-E014", "MEPS-E017", "MEPS-E021", "MEPS-E023", "MEPS-E025"])
        self.assertEqual(self.ids(kind="label"),
                         ["MEPS-E006", "MEPS-E007", "MEPS-E008", "MEPS-E022", "MEPS-E027", "MEPS-E028"])
        self.assertEqual(self.ids(kind="truncated cell"), ["MEPS-E024"])
        self.assertEqual(self.ids(grep="DEDUCTIBLE"), ["MEPS-E011"])
        self.assertEqual(self.ids(grep="policy level"), ["MEPS-E027"])
        self.assertEqual(self.ids(ids=["MEPS-D001"]), ["MEPS-D001"])

    def test_numbers(self):
        self.assertEqual(me.numbers("-0.9%; 14.531"), [0.9, 14.531])
        self.assertEqual(me.numbers("26."), [26.0])
        self.assertEqual(me.numbers(""), [])


class TestSummaryAndMain(unittest.TestCase):
    def test_summary(self):
        lines = me.summary(me.load(TABLE))
        self.assertEqual(lines[0], "41 items")
        self.assertIn("  reproduction: 11", lines)
        self.assertIn("  figure vs text: 10", lines)
        self.assertIn("  text: 6", lines)
        self.assertIn("  label: 6", lines)
        self.assertIn("  truncated cell: 1", lines)
        self.assertEqual(lines[-1], "reproduction: 11 briefs, 347 of 408 computable cells exact, 374 close; "
                                    "not reproducing: #558")

    def test_main_codes(self):
        code, out = run(["--brief", "497"])
        self.assertEqual(code, 0)
        self.assertIn("MEPS-E001", out)
        self.assertIn("stat497.shtml", out)
        code, out = run(["--brief", "450"])
        self.assertEqual(code, 0)
        self.assertIn("MEPS-E021", out)
        self.assertIn("meps-m8-flag-audit-results-v1-2026-11-09.md", out)
        code, out = run(["--brief", "9999"])
        self.assertEqual(code, 1)
        self.assertIn("not proof", out)
        code, out = run(["--summary"])
        self.assertEqual((code, out.splitlines()[0]), (0, "41 items"))
        code, out = run(["--version"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("meps_errata 0.1.0, table 0.3.0"))
        code, _ = run(["--csv", os.path.join(HERE, "no-such-table.csv")])
        self.assertEqual(code, 2)

    def test_main_json(self):
        import json
        code, out = run(["--brief", "558", "--value", "6.2", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual([r["id"] for r in json.loads(out)], ["MEPS-E009"])

    def test_bad_header(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,brief\nX,1\n")
            code, _ = run(["--csv", p])
        self.assertEqual(code, 2)


class TestSkillFile(unittest.TestCase):
    def test_frontmatter(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---\n")[1]
        self.assertIn("name: meps-statbrief-errata\n", front)
        self.assertIn("license: Apache-2.0", front)
        desc = re.search(r"^description: (.+)$", front, re.M).group(1)
        self.assertLess(len(desc), 1024)
        self.assertIn("28 known slips", desc)
        self.assertIn("scripts/meps_errata.py", text)
        self.assertIn("table 0.3.0: 41 rows", text)
        self.assertNotIn("MIT", text)


class TestAuditTally(unittest.TestCase):
    """The A8 hand-audit tally behind rows MEPS-E018 to MEPS-E020."""
    PATH = os.path.join(HERE, "findings", "meps-m8-flag-audit-v1", "a8-tally.csv")

    def test_tally(self):
        import csv
        with open(self.PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 101)
        ranks = [int(r["check_rank"]) for r in rows]
        self.assertEqual(ranks, sorted(ranks))
        skip = {25, 27, 39, 55, 60, 78, 92, 93, 94, 105, 110, 126, 129}
        self.assertEqual(ranks, [k for k in range(21, 135) if k not in skip])
        classes = {}
        for r in rows:
            classes[r["class"]] = classes.get(r["class"], 0) + 1
        self.assertEqual(classes, {"Different quantity": 75, "Parser or association artefact": 23,
                                   "Figure-text conflict": 3})
        conflicts = [(r["check_rank"], r["brief"], r["reads"]) for r in rows if r["class"] == "Figure-text conflict"]
        self.assertEqual(conflicts, [("40", "192", "2 of 2"), ("70", "481", "2 of 2"), ("88", "434", "2 of 2")])


if __name__ == "__main__":
    unittest.main()
