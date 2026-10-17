# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import json
import os
import tempfile
import unittest

import spark_switch as ss

HERE = os.path.dirname(os.path.abspath(__file__))
DEVSET = next((p for p in (os.path.join(HERE, "spark", ss.NEW), os.path.join(HERE, ss.NEW), ss.NEW)
               if os.path.exists(p)), None)
# the 28 PMIDs selected by the rule in prereg-ce-switch-v1.md (targets k = 2 and 3 had none)
SELECTED = {"1675001", "3025001", "7075022", "8425004", "9775000", "11125000", "12475000", "13825014",
            "15175001", "16525000", "17875000", "19225000", "20575000", "21925000", "23275000", "24625000",
            "25975000", "27325005", "28675000", "30025000", "31375000", "32725000", "34075000", "35425000",
            "36775000", "38125005", "39475000", "40825000"}


def row(qid, cue, in_pool, chosen, ce, devset=ss.NEW):
    return {"id": qid, "cue": cue, "in_pool": in_pool, "chosen": {"rr": chosen}, "ce": {"rr": ce},
            "devset": devset}


ROWS = [row("a", False, True, 0.5, 1.0), row("b", True, True, 1.0, 0.0), row("c", False, False, 0.0, 0.0)]


class SwitchTests(unittest.TestCase):
    def test_with_switch(self):
        rows = [ss.with_switch(r) for r in ROWS]
        self.assertEqual([r["switch"]["rr"] for r in rows], [1.0, 1.0, 0.0])

    def test_summarize(self):
        s = ss.summarize([ss.with_switch(r) for r in ROWS])
        self.assertEqual((s["n"], s["in_pool"], s["cue"]), (3, 2, 1))
        self.assertEqual(s["mrr5"], {"chosen": 0.5, "ce": 0.3333, "switch": 0.6667})
        c = s["ce_vs_chosen"]
        self.assertEqual((c["helped"], c["hurt"], c["delta_mrr5"]), (["a"], ["b"], -0.1667))

    def test_cue_questions(self):
        qs = [{"info_need_id": "x", "info_need": "Which paper first described BLAST?"},
              {"info_need_id": "y", "info_need": "Find the BLAST paper."}]
        self.assertEqual(ss.cue_questions(qs), ["x"])


class HypothesisTests(unittest.TestCase):
    def summary(self, chosen, ce, hurt, in_pool):
        return {"n": 28, "in_pool": in_pool, "mrr5": {"chosen": chosen, "ce": ce, "switch": ce},
                "ce_vs_chosen": {"hurt": ["q%d" % i for i in range(hurt)]}}

    def test_all_pass_at_the_thresholds(self):
        h = ss.hypotheses(self.summary(0.80, 0.85, 3, 26))
        self.assertTrue(h["H1"]["supported"])
        self.assertEqual(h["H1"]["ce_minus_chosen"], 0.05)
        self.assertTrue(h["H2"]["supported"])
        self.assertTrue(h["H3"]["supported"])
        self.assertTrue(h["S"]["ok"])
        self.assertEqual(h["decision"], "switch is the provisional pick")

    def test_all_fail_just_past_the_thresholds(self):
        h = ss.hypotheses(self.summary(0.70, 0.74, 4, 25))
        self.assertFalse(h["H1"]["supported"])
        self.assertFalse(h["H2"]["supported"])
        self.assertFalse(h["H3"]["supported"])  # 0.70 is 0.109 below 0.809
        self.assertFalse(h["S"]["ok"])
        self.assertEqual(h["decision"], "keep chosen")


class MainTests(unittest.TestCase):
    def test_main_writes_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "per_question.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in ROWS + [row("lm", True, True, 1.0, 0.5, "devset_landmark_v1.jsonl")]:
                    f.write(json.dumps(r) + "\n")
            out = os.path.join(tmp, "out")
            self.assertEqual(ss.main(["--per-question", path, "--out", out]), 0)
            with open(os.path.join(out, "switch_results.json"), encoding="utf-8") as f:
                result = json.load(f)
            self.assertEqual(sorted(result["sets"]), ["devset_landmark_v1.jsonl", ss.NEW])
            self.assertEqual(result["sets"][ss.NEW]["role"], "pre-registered test")
            self.assertEqual(result["sets"]["devset_landmark_v1.jsonl"]["role"], "post hoc")
            self.assertEqual(result["sets"]["devset_landmark_v1.jsonl"]["mrr5"]["switch"], 1.0)
            self.assertEqual(result["hypotheses"]["decision"], "keep chosen")
            self.assertTrue(os.path.exists(os.path.join(out, "switch_results.md")))


@unittest.skipUnless(DEVSET, "devset_ordinary_v2.jsonl not found next to the tests")
class DevsetTests(unittest.TestCase):
    def test_devset_follows_the_prereg(self):
        rows = ss.load(DEVSET)
        self.assertEqual(len(rows), 28)
        self.assertEqual({r["pmid"] for r in rows}, SELECTED)
        self.assertEqual(len({r["info_need_id"] for r in rows}), 28)
        self.assertEqual({r["kind"] for r in rows}, {"ordinary"})
        self.assertEqual(ss.cue_questions(rows), [])
        self.assertLessEqual(sum(1 for r in rows if ss.YEAR_Q.search(r["info_need"])), 5)


if __name__ == "__main__":
    unittest.main()
