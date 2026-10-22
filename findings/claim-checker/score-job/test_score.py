"""Unit tests for score.py on synthetic labels and flags only (no base text, no real output).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import score


def flag(module, line, evidence=(), scored=True, rule="r"):
    return {"module": module, "rule": rule, "line": line, "evidence": list(evidence),
            "scored": scored}


def mut(id_, module, line, evidence=(), operator="op"):
    return {"id": id_, "module": module, "operator": operator, "line": line,
            "evidence": list(evidence)}


COPIES = [
    {"file": "P4-cut.md", "package": "P4", "copy": 0, "mutations": []},
    {"file": "P4-copy01.md", "package": "P4", "copy": 1,
     "mutations": [mut("a", "R1", 10, [20]), mut("b", "R5", 30, [90], "cite-removal")]},
    {"file": "P4-copy02.md", "package": "P4", "copy": 2, "mutations": [mut("c", "R1", 20, [10])]},
    {"file": "P5-cut.md", "package": "P5", "copy": 0, "mutations": []},
    {"file": "P5-copy01.md", "package": "P5", "copy": 1, "mutations": [mut("d", "R3", 5)]},
]
CHECKER = {
    "P4-cut.md": [flag("R6", 50), flag("R5", 60, scored=False)],
    "P4-copy01.md": [flag("R1", 20, [10]), flag("R5", 90), flag("R6", 50)],
    "P4-copy02.md": [flag("R6", 50), flag("R8", 20)],
    "P5-cut.md": [flag("R5", 248)],
    "P5-copy01.md": [flag("R5", 248), flag("R3", 5, scored=False)],
}
BASELINE = {
    "P4-cut.md": [],
    "P4-copy01.md": [flag("R1/R1b/R7/R8", 10), flag("R3", 70)],
    "P4-copy02.md": [flag("R3", 70)],
    "P5-cut.md": [],
    "P5-copy01.md": [flag("R3", 5)],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(root):
    """Write labels.json and a checker-job out/ folder; return (labels path, out dir)."""
    root = Path(root)
    labels = root / "labels.json"
    labels.write_bytes(json.dumps({"copies": COPIES}).encode("ascii"))
    out = root / "out"
    rows = []
    for kind, flags, name in (("checker", CHECKER, score.CHECKER),
                              ("baseline", BASELINE, "keyword baseline")):
        (out / kind).mkdir(parents=True)
        for f, fl in flags.items():
            (out / kind / (f + ".json")).write_text(json.dumps({"checker": name, "flags": fl}))
    for c in COPIES:
        rows.append({"file": c["file"],
                     "checker_sha256": sha((out / "checker" / (c["file"] + ".json")).read_bytes()),
                     "baseline_sha256": sha((out / "baseline" / (c["file"] + ".json")).read_bytes())})
    (out / "summary.json").write_text(json.dumps({"checker": score.CHECKER, "problems": [],
                                                  "files": rows, "max_checker_seconds": 0.2}))
    return labels, out


class Small(unittest.TestCase):
    def test_need(self):
        self.assertEqual([score.need(n) for n in (8, 7, 5, 4, 0)], [5, 5, 4, 3, 0])

    def test_wilson(self):
        lo, hi = score.wilson(2, 4)
        self.assertAlmostEqual(lo, 0.15, places=2)
        self.assertAlmostEqual(hi, 0.85, places=2)
        self.assertIsNone(score.wilson(0, 0))

    def test_c5_dropped(self):
        kept = score.counted("P5", [flag("R5", 248), flag("R5/R5b/R6", 252), flag("R4", 248)])
        self.assertEqual([f["module"] for f in kept], ["R4"])
        self.assertEqual(len(score.counted("P4", [flag("R5", 248)])), 1)


class ScoreSet(unittest.TestCase):
    def test_checker(self):
        s = score.score_set(COPIES, CHECKER)
        self.assertEqual((s["planted"], s["caught"], s["caught_labelled"]), (4, 2, 1))
        self.assertEqual(s["secondary"], 2)       # a (R1 on its line) and b (R5 on line 90)
        self.assertEqual((s["tp_flags"], s["fp_flags"]), (2, 2))
        self.assertEqual(s["fp_list"], [("P4", "R5", 90), ("P4", "R6", 50)])
        self.assertEqual(s["fp_explained_by_secondary"], 1)
        caught = {m["id"]: (m["caught"], m["caught_by"]) for m in s["mutations"]}
        self.assertEqual(caught, {"a": (True, ["R1"]), "b": (False, []),
                                  "c": (True, ["R8"]), "d": (False, [])})

    def test_adjudication(self):
        s = score.score_set(COPIES, CHECKER, real=[["P4", "R6", 50], ["P4", "R9", 1]])
        self.assertEqual(s["fp_real_unlisted"], [("P4", "R6", 50)])
        self.assertEqual(float(s["precision_adjudicated_f"]), 0.75)

    def test_baseline(self):
        s = score.score_set(COPIES, BASELINE)
        self.assertEqual((s["caught"], s["caught_labelled"]), (2, 2))
        self.assertEqual((s["tp_flags"], s["fp_flags"]), (2, 1))


class EndToEnd(unittest.TestCase):
    def test_run(self):
        with tempfile.TemporaryDirectory() as d:
            labels, out = build(d)
            r = score.run(labels, out, expect=sha(labels.read_bytes()))
        self.assertEqual(r["problems"], [])
        self.assertEqual((r["P1"]["recall"], r["P1"]["pass"]), (0.5, False))
        m = r["P2"]["modules"]
        self.assertEqual((m["R1"]["need"], m["R1"]["pass"]), (2, True))
        self.assertEqual((m["R5"]["need"], m["R5"]["pass"]), (1, False))
        self.assertTrue(m["R4"]["pass"])
        self.assertFalse(r["P2"]["pass"])
        self.assertEqual((r["P3"]["precision"], r["P3"]["pass"]), (0.5, True))
        self.assertEqual(r["P4"]["baseline_precision"], 0.6667)
        self.assertEqual((r["P4"]["precision_ok"], r["P4"]["recall_ok"], r["P4"]["pass"]),
                         (False, True, False))
        self.assertTrue(r["P6"]["pass"])
        p = r["prediction_6_1"]
        self.assertFalse(p["holds"])
        self.assertEqual(p["other_flags"], [["P4-cut.md", "R6", "r", 50]])
        self.assertEqual(p["c5_flags"], [["P5-cut.md", "R5", "r", 248]])
        self.assertEqual(r["by_operator"]["R5 cite-removal"],
                         {"planted": 1, "caught": 0, "secondary": 1})

    def test_tampered_output_stops(self):
        with tempfile.TemporaryDirectory() as d:
            labels, out = build(d)
            (out / "checker" / "P4-copy01.md.json").write_text("{}")
            r = score.run(labels, out, expect=sha(labels.read_bytes()))
            wrong = score.run(labels, Path(d) / "out")
        self.assertEqual(r["problems"], ["checker/P4-copy01.md.json SHA-256 differs from the summary"])
        self.assertNotIn("P1", r)
        self.assertIn("labels.json SHA-256 differs from log entry 7", wrong["problems"])


if __name__ == "__main__":
    unittest.main()
