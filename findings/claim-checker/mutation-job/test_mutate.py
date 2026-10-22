"""Unit tests for mutate.py on synthetic text only (no base text is read).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import contextlib
import hashlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

import mutate

DOC = (
    "# Title\n"
    "\n"
    "- A claim 0.5 (0.1-0.9) here.\n"
    "- Another 0.5 (0.1-0.9) there.\n"
    "| H1 | H2 |\n"
    "|---|---|\n"
    "| a | 1.2 |\n"
    "## References\n"
    "1. Ref one.\n"
    "\n"
    "---\n"
    "Submitter notes here.\n"
)


def cut_lines():
    lines = DOC.encode("utf-8").splitlines(keepends=True)
    return lines[:mutate.cut_count(lines)]


def site(sid, module, package, line, find="x", replace="y", evidence=(), group=None):
    s = {"id": sid, "module": module, "package": package, "line": line,
         "find": find, "replace": replace, "evidence": list(evidence), "operator": "op"}
    if group:
        s["group"] = group
    return s


class Cut(unittest.TestCase):
    def test_cut_rule(self):
        lines = DOC.encode("utf-8").splitlines(keepends=True)
        self.assertEqual(mutate.cut_count(lines), 10)
        self.assertEqual(mutate.cut_count([b"a\n", b"b\n"]), 2)
        self.assertEqual(mutate.cut_count([b"a\n", b"Submitter notes\n"]), 1)
        self.assertEqual(mutate.cut_count([b"a\n", b"\n", b"## Notes for the submitter\n"]), 2)


class Sites(unittest.TestCase):
    def test_site_problem(self):
        lines = cut_lines()
        ok = site("a", "R1", "P4", 3, "0.9)", "0.8)", evidence=[4])
        self.assertIsNone(mutate.site_problem(ok, lines))
        self.assertIn("3 times", mutate.site_problem(site("b", "R1", "P4", 3, "0.", "1."), lines))
        self.assertEqual(mutate.site_problem(site("c", "R1", "P4", 9, "Ref", "Fer"), lines),
                         "in the reference list")
        self.assertEqual(mutate.site_problem(site("d", "R1", "P4", 8, "References", "R"), lines),
                         "in the reference list")
        self.assertEqual(mutate.site_problem(site("e", "R1", "P4", 5, "H1", "H3"), lines),
                         "a table header row")
        self.assertEqual(mutate.site_problem(site("f", "R1", "P4", 6, "---", "--"), lines),
                         "a table separator row")
        self.assertIsNone(mutate.site_problem(site("g", "R1", "P4", 7, "1.2", "1.3"), lines))
        self.assertEqual(mutate.site_problem(site("h", "R1", "P4", 11, "---", "-"), lines),
                         "line outside the cut text")
        self.assertEqual(mutate.site_problem(site("i", "R1", "P4", 3, "here", "here", ), lines),
                         "find empty, or replace missing, unchanged or multi-line")
        self.assertEqual(mutate.site_problem(site("j", "R1", "P4", 3, "here", "x", [99]), lines),
                         "evidence line outside the cut text")


class Draw(unittest.TestCase):
    def test_quota_overflow_and_shortfall(self):
        sites = [site(f"A{i}", "A", "P4", 3) for i in range(5)]
        sites += [site(f"A5{i}", "A", "P5", 3) for i in range(2)]
        sites += [site("B0", "B", "P5", 3)]
        drawn, reserve, short = mutate.draw(sites, ["A", "B"], ["P4", "P5"],
                                            random.Random(1), 8, 4)
        self.assertEqual(len(drawn[("A", "P4")]), 5)
        self.assertEqual(len(drawn[("A", "P5")]), 2)
        self.assertEqual(reserve[("A", "P4")], [])
        self.assertEqual(short, {"A": 1, "B": 7})
        self.assertEqual(len(drawn[("B", "P5")]), 1)
        self.assertEqual(drawn[("B", "P4")], [])
        again = mutate.draw(sites, ["A", "B"], ["P4", "P5"], random.Random(1), 8, 4)[0]
        self.assertEqual([s["id"] for s in again[("A", "P4")]],
                         [s["id"] for s in drawn[("A", "P4")]])

    def test_quota_four_each(self):
        sites = [site(f"A{i}", "A", p, 3) for p in ("P4", "P5") for i in range(6)]
        drawn, reserve, short = mutate.draw(sites, ["A"], ["P4", "P5"],
                                            random.Random(2), 8, 4)
        self.assertEqual((len(drawn[("A", "P4")]), len(drawn[("A", "P5")])), (4, 4))
        self.assertEqual((len(reserve[("A", "P4")]), len(reserve[("A", "P5")])), (2, 2))
        self.assertEqual(short, {"A": 0})


class Layout(unittest.TestCase):
    def test_collides(self):
        self.assertTrue(mutate.collides(site("a", "A", "P", 3, evidence=[4]), site("b", "B", "P", 4)))
        self.assertTrue(mutate.collides(site("a", "A", "P", 4), site("b", "B", "P", 3, evidence=[4])))
        self.assertTrue(mutate.collides(site("a", "A", "P", 3), site("b", "B", "P", 3)))
        self.assertFalse(mutate.collides(site("a", "A", "P", 7), site("b", "B", "P", 9)))
        self.assertTrue(mutate.collides(site("a", "A", "P", 7, group="g"),
                                        site("b", "B", "P", 9, group="g")))

    def test_redraw_from_reserve(self):
        a1, a2 = site("a1", "A", "P", 3), site("a2", "A", "P", 7)
        b1, b2 = site("b1", "B", "P", 3), site("b2", "B", "P", 9)
        drawn = {("A", "P"): [a1, a2], ("B", "P"): [b1]}
        reserve = {("A", "P"): [], ("B", "P"): [b2]}
        log = []
        copies = mutate.layout(drawn, reserve, ["A", "B"], "P", log)
        self.assertEqual([[s["id"] for s in c] for c in copies], [["a1", "b2"], ["a2"]])
        self.assertEqual([e["event"] for e in log], ["collision", "redrawn"])
        self.assertEqual(log[0]["with"], ["a1"])

    def test_new_copy_when_nothing_fits(self):
        a1, b1 = site("a1", "A", "P", 3), site("b1", "B", "P", 3)
        drawn = {("A", "P"): [a1], ("B", "P"): [b1]}
        reserve = {("A", "P"): [], ("B", "P"): []}
        log = []
        copies = mutate.layout(drawn, reserve, ["A", "B"], "P", log)
        self.assertEqual([[s["id"] for s in c] for c in copies], [["a1"], ["b1"]])
        self.assertEqual([e["event"] for e in log], ["collision", "new copy", "moved"])

    def test_move_to_other_copy(self):
        a1, a2 = site("a1", "A", "P", 3), site("a2", "A", "P", 7)
        b1 = site("b1", "B", "P", 3)
        drawn = {("A", "P"): [a1, a2], ("B", "P"): [b1]}
        reserve = {("A", "P"): [], ("B", "P"): []}
        log = []
        copies = mutate.layout(drawn, reserve, ["A", "B"], "P", log)
        self.assertEqual([[s["id"] for s in c] for c in copies], [["a1"], ["a2", "b1"]])
        self.assertEqual([e["event"] for e in log], ["collision", "moved"])
        self.assertEqual(log[1]["copy"], 2)


class Apply(unittest.TestCase):
    def test_apply_keeps_lines(self):
        lines = cut_lines()
        out = mutate.apply(lines, [site("a", "R1", "P4", 3, "0.9)", "0.7)")])
        self.assertEqual(len(out), len(lines))
        self.assertEqual(out[2], b"- A claim 0.5 (0.1-0.7) here.\n")
        self.assertEqual(out[3], lines[3])
        with self.assertRaises(ValueError):
            mutate.apply(lines, [site("b", "R1", "P4", 3, "0.", "1.")])


class EndToEnd(unittest.TestCase):
    def _spec(self, d, base):
        return {"seed": 20261021, "target_per_module": 8, "per_package": 4,
                "modules": ["R1"],
                "packages": {"P4": {"file": "p.md", "sha256_whole": base["sha256_whole"],
                                    "sha256_cut": base["sha256_cut"],
                                    "cut_lines": base["cut_lines"]}},
                "sites": [site("s1", "R1", "P4", 3, "0.9)", "0.8)", [4]),
                          site("s2", "R1", "P4", 4, "there", "here and there", [3]),
                          site("s3", "R1", "P4", 3, "0.", "1.")],
                "out_of_scope": {"R1": "note"}}

    def test_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "p.md").write_bytes(DOC.encode("utf-8"))
            base = mutate.load_base(d / "p.md")
            self.assertEqual(base["cut_lines"], 10)
            (d / "sites.json").write_text(json.dumps(self._spec(d, base)))
            with contextlib.redirect_stdout(io.StringIO()):
                code = mutate.main(["--sites", str(d / "sites.json"), "--base-dir", str(d),
                                    "--out-dir", str(d / "out")])
            self.assertEqual(code, 0)
            report = json.loads((d / "out" / "report.json").read_text())
            labels_bytes = (d / "out" / "labels.json").read_bytes()
            self.assertEqual(report["labels_sha256"], hashlib.sha256(labels_bytes).hexdigest())
            self.assertEqual(report["planted_total"], 2)
            self.assertEqual(report["shortfall"], {"R1": 6})
            self.assertEqual(report["copies"], {"P4": 2})
            self.assertEqual([x["id"] for x in report["invalid_sites"]], ["s3"])
            manifest = json.loads((d / "out" / "manifest.json").read_text())
            self.assertEqual([c["file"] for c in manifest["copies"]],
                             ["P4-cut.md", "P4-copy01.md", "P4-copy02.md"])
            self.assertNotIn("mutations", json.dumps(manifest))
            labels = json.loads(labels_bytes)
            muts = [m for c in labels["copies"] for m in c["mutations"]]
            self.assertEqual(sorted(m["id"] for m in muts), ["s1", "s2"])
            cut = (d / "out" / "P4-cut.md").read_bytes()
            self.assertEqual(hashlib.sha256(cut).hexdigest(), base["sha256_cut"])
            for c in manifest["copies"]:
                data = (d / "out" / c["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), c["sha256"])
                self.assertEqual(len(data.splitlines()), 10)

    def test_hash_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "p.md").write_bytes(DOC.encode("utf-8"))
            spec = self._spec(d, mutate.load_base(d / "p.md"))
            spec["packages"]["P4"]["sha256_cut"] = "0" * 64
            (d / "sites.json").write_text(json.dumps(spec))
            with contextlib.redirect_stdout(io.StringIO()):
                code = mutate.main(["--sites", str(d / "sites.json"), "--base-dir", str(d),
                                    "--out-dir", str(d / "out")])
            self.assertEqual(code, 2)
            self.assertFalse((d / "out" / "labels.json").exists())


if __name__ == "__main__":
    unittest.main()
