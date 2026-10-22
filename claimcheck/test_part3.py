"""Unit tests for claimcheck part 3 (R6-b, R7-b), the keyword baseline and the command line,
on synthetic strings and temporary files only (plan v7 section 8 step 3).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import tempfile
import unittest

from claimcheck import baseline as b
from claimcheck import cli
from claimcheck import grammar as g
from claimcheck import modules3 as m

PDOC = "\n".join([
    "## E.4 Pre-registered survey check",                                              # 1
    "- The analysis was pre-registered [13].",                                         # 2
    "- The follow-up was pre-registered [14].",                                        # 3
    "- Pre-registered checks found nothing.",                                          # 4
    "- A trial should be pre-registered.",                                             # 5
    '- He called it "pre-registered" [13].',                                           # 6
    "- The plan (plan-a.md) was pre-registered.",                                      # 7
    "- It was preregistered and pre-registration was done.",                           # 8
    "## H. Next steps",                                                                # 9
    "- The study was pre-registered.",                                                 # 10
    "## References",                                                                   # 11
    "13. Munim, Inc. evidence-pack: findings/plan-a.md, results-a.md.",                # 12
    "14. Munim, Inc. evidence-pack: findings/plan-b.md.",                              # 13
]) + "\n"

PLAN_BEFORE = ("# Pre-registration 3\n\nThis plan is committed **before** any data is read.\n\n"
               "## Method\n\n- Written after the results of trial X were published.\n")
PLAN_AFTER = ("# Pre-registration 3b\n\n## Status and honesty note\n\nThis follow-up was written "
              "**after** the primary results of pre-registration 3 were seen. The checks were "
              "fixed before they ran.\n")
PLAN_ORDER = ("# Plan\n\n## Status\n\nThis plan was written before the results; after that "
              "nothing changed.\n")

JDOC = "\n".join([
    "## E.3c Recheck",                                                                 # 1
    "- The rwe_recheck tool re-derived 3 estimates from Loften 2026 [1] and "
    "Palzes 2021 [2]; it flagged 1 row.",                                              # 2
    "- rwe_recheck also read 4 estimates from Smith 2020 [3].",                        # 3
    "- Two estimates came from Farokhnia, also via rwe_recheck.",                      # 4
    '- A note: "rwe_recheck" saw Jones 2019.',                                         # 5
    "- No rwe_recheck estimates disagreed; 0 rows flagged.",                           # 6
    "- Loften 2026 was re-read by hand, 5 estimates.",                                 # 7
    "## References",                                                                   # 8
    "1. Loften A, et al. Title. 2026. PMID 42132959.",                                 # 9
    "2. Palzes VA, et al. Title. 2021. PMID 34341493.",                                # 10
    "3. Farokhnia M, et al. Title. 2022. PMID 36123420.",                              # 11
]) + "\n"

ROWS = [
    {"label": "Loften remission", "source": "Loften 2026 PMID 42132959", "flags": []},
    {"label": "Loften intoxication", "source": "Loften 2026 PMID 42132959", "flags": ["centre"]},
    {"label": "Palzes difference", "source": "Palzes 2021 PMID 34341493", "flags": []},
    {"label": "Pan VAS", "source": "Pan 2025 PMID 40274279", "flags": []},
]

BDOC = "\n".join([
    "## A. One",                                                                       # 1
    "- There was no difference in 12 trials.",                                         # 2
    "- It was approved 5 years ago.",                                                  # 3
    "- All 3 values were small.",                                                      # 4
    "- The SMD was -0.40 (-0.70 to -0.10).",                                           # 5
    "| Dose | Note |",                                                                 # 6
    "|---|---|",                                                                       # 7
    "| 10 mg/kg | Overall |",                                                          # 8
    "## B. Two",                                                                       # 9
    "- We read 12 papers; the first version ran.",                                     # 10
    "- Nothing here.",                                                                 # 11
]) + "\n"


def _write(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))
    return path


def _tool():
    return m.Tool("rwe_recheck", "recheck.json", ROWS, ("label", "source"), "flags")


class Plans(unittest.TestCase):
    def test_status_note(self):
        self.assertFalse(m.plan_after_results(PLAN_BEFORE))    # "after" only outside the note
        self.assertTrue(m.plan_after_results(PLAN_AFTER))
        self.assertFalse(m.plan_after_results(PLAN_ORDER))     # no "results" after "after"

    def test_load_plans(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "a.md", PLAN_BEFORE)
            _write(d, "b.md", PLAN_AFTER)
            _write(d, "c.txt", PLAN_AFTER)
            self.assertEqual(m.load_plans(d), {"a.md": False, "b.md": True})

    def test_names_file(self):
        self.assertTrue(m.names_file("findings/plan-a.md, x", "plan-a.md"))
        self.assertTrue(m.names_file("see `plan-a.md`.", "plan-a.md"))
        self.assertFalse(m.names_file("old-plan-a.md", "plan-a.md"))
        self.assertFalse(m.names_file("plan-a.md5", "plan-a.md"))

    def test_r6_b(self):
        doc = g.Doc(PDOC)
        self.assertEqual(m.r6_b(doc, None), [])
        flags = m.r6_b(doc, {"plan-a.md": False, "plan-b.md": True})
        self.assertEqual([(f.line, f.rule, f.evidence, f.span) for f in flags],
                         [(3, "b-after", (13,), "pre-registered"),
                          (4, "b-no-plan", (), "Pre-registered")])
        self.assertEqual(flags[0].data, {"plans": ["plan-b.md"]})


class Jobs(unittest.TestCase):
    def test_package_rows_and_counts(self):
        doc = g.Doc(JDOC)
        self.assertEqual(len(m.package_rows(doc, _tool())), 3)          # Pan's PMID not cited
        self.assertEqual(m.file_counts(doc, _tool()), {3, 1})

    def test_stated_counts(self):
        self.assertEqual([v for _, _, v in m.stated_counts("read 3 estimates and 1 row")], [3, 1])
        self.assertEqual([v for _, _, v in m.stated_counts("Two of the 27 CIs [4]")], [2, 27])
        self.assertEqual(m.stated_counts("from Loften 2026 [1] and 5 trials"), [])

    def test_r7_b(self):
        doc = g.Doc(JDOC)
        self.assertEqual(m.r7_b(doc, None), [])
        flags = m.r7_b(doc, [_tool()])
        self.assertEqual([(f.line, f.rule, f.span) for f in flags],
                         [(3, "b-count", "4"), (3, "b-name", "Smith"),
                          (4, "b-count", "Two"), (4, "b-name", "Farokhnia")])
        self.assertEqual(flags[0].data["file_counts"], [1, 3])

    def test_load_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "recheck.json", json.dumps({"n_rows": 4, "rows": ROWS}))
            man = _write(d, "manifest.json", json.dumps({"tools": [
                {"name": "rwe_recheck", "file": "recheck.json", "rows": "rows",
                 "labels": ["label", "source"], "flags": "flags"}]}))
            tools = m.load_manifest(man)
        self.assertEqual((tools[0].name, len(tools[0].rows), tools[0].labels, tools[0].flags),
                         ("rwe_recheck", 4, ("label", "source"), "flags"))


class Baseline(unittest.TestCase):
    def test_groups(self):
        flags = b.baseline(g.Doc(BDOC))
        self.assertEqual([(f.line, f.module, f.span) for f in flags], [
            (2, "R3", "no difference"), (2, "R2/R2b", "12 trials"), (2, "R1/R1b/R7/R8", "12"),
            (3, "R4", "years"),
            (4, "R2/R2b", "All"), (4, "R1/R1b/R7/R8", "All 3"),
            (5, "R1/R1b/R7/R8", "negative SMD/DiD"),
            (8, "R1/R1b/R7/R8", "mg/kg"),
            (10, "R5/R5b/R6", "first"), (10, "R1/R1b/R7/R8", "12"),
        ])


class CommandLine(unittest.TestCase):
    def test_checker_json(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = _write(d, "pkg.md", PDOC)
            plans = os.path.join(d, "plans")
            os.mkdir(plans)
            _write(plans, "plan-a.md", PLAN_BEFORE)
            _write(plans, "plan-b.md", PLAN_AFTER)
            out = os.path.join(d, "out.json")
            self.assertEqual(cli.main([pkg, "--plans", plans, "--deadline", "2027-03-26",
                                       "--json", out]), 0)
            with open(out, encoding="utf-8") as fh:
                rep = json.load(fh)
        self.assertEqual((rep["package"], rep["lines_total"], rep["lines_cut"]), ("pkg.md", 13, 13))
        r6b = [(f["line"], f["rule"]) for f in rep["flags"]
               if f["module"] == "R6" and f["rule"].startswith("b-")]
        self.assertEqual(r6b, [(3, "b-after"), (4, "b-no-plan")])
        scored = [f for f in rep["flags"] if f["scored"]]
        self.assertEqual(rep["scored"], len(scored))
        self.assertEqual(sum(rep["counts"].values()), len(scored))

    def test_jobs_and_baseline_json(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = _write(d, "pkg.md", JDOC)
            _write(d, "recheck.json", json.dumps({"rows": ROWS}))
            man = _write(d, "manifest.json", json.dumps({"tools": [
                {"name": "rwe_recheck", "file": "recheck.json", "rows": "rows",
                 "labels": ["label", "source"], "flags": "flags"}]}))
            out = os.path.join(d, "out.json")
            cli.main([pkg, "--jobs", man, "--json", out])
            with open(out, encoding="utf-8") as fh:
                rep = json.load(fh)
            bpkg = _write(d, "base.md", BDOC)
            bout = os.path.join(d, "bout.json")
            self.assertEqual(b.main([bpkg, "--json", bout]), 0)
            with open(bout, encoding="utf-8") as fh:
                brep = json.load(fh)
        r7b = [(f["line"], f["rule"]) for f in rep["flags"] if f["module"] == "R7"
               and f["rule"].startswith("b-")]
        self.assertEqual(r7b, [(3, "b-count"), (3, "b-name"), (4, "b-count"), (4, "b-name")])
        self.assertEqual(len(brep["flags"]), 10)
        self.assertEqual(brep["counts"]["R1/R1b/R7/R8"], 5)


if __name__ == "__main__":
    unittest.main()
