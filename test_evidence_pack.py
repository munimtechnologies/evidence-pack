import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from evidence_pack import DESIGNS, parse_study, parse_summary, pubmed_term, render, score, trial_counts  # noqa: E402

PAIR = {"slug": "methotrexate-knee-oa", "drug": "methotrexate", "condition": "knee osteoarthritis",
        "pubmed": '("osteoarthritis, knee"[mh] OR "knee osteoarthritis"[tiab])', "ctgov": "knee osteoarthritis"}


def study(nct, phases, status="COMPLETED", results=False, kind="INTERVENTIONAL"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": "Trial " + nct},
        "statusModule": {"overallStatus": status, "startDateStruct": {"date": "2019-01"},
                         "primaryCompletionDateStruct": {"date": "2022-06-30"}},
        "designModule": {"studyType": kind, "phases": phases, "enrollmentInfo": {"count": 155}},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "University of Leeds"}}},
        "hasResults": results}


class QueryTests(unittest.TestCase):
    def test_pubmed_term(self):
        base = '("methotrexate"[tiab] OR "methotrexate"[mh]) AND ("osteoarthritis, knee"[mh] OR "knee osteoarthritis"[tiab])'
        self.assertEqual(pubmed_term(PAIR), base)
        self.assertEqual(pubmed_term(PAIR, "rct"), base + " AND (randomized controlled trial[pt])")
        self.assertEqual(pubmed_term(PAIR, ("rct", "meta_analysis")),
                         base + " AND (randomized controlled trial[pt] OR meta-analysis[pt])")

    def test_pairs_file(self):
        with open(os.path.join(HERE, "pairs.json"), encoding="utf-8") as f:
            pairs = json.load(f)["pairs"]
        self.assertEqual(len(pairs), 13)
        self.assertEqual(len({p["slug"] for p in pairs}), 13)
        for p in pairs:
            self.assertEqual(set(p), {"slug", "drug", "condition", "pubmed", "ctgov"})
            self.assertEqual(p["pubmed"].count("("), p["pubmed"].count(")"))
            self.assertEqual(p["pubmed"].count('"') % 2, 0)


class ParseTests(unittest.TestCase):
    def test_parse_summary(self):
        doc = {"pubdate": "2024 Aug", "source": "Ann Intern Med", "title": "Methotrexate in knee OA (PROMOTE).",
               "pubtype": ["Journal Article", "Randomized Controlled Trial"]}
        self.assertEqual(parse_summary("39074374", doc),
                         {"pmid": "39074374", "year": "2024", "journal": "Ann Intern Med",
                          "title": "Methotrexate in knee OA (PROMOTE).",
                          "types": ["Journal Article", "Randomized Controlled Trial"]})
        self.assertEqual(parse_summary("1", {})["year"], "")

    def test_parse_study(self):
        s = parse_study(study("NCT00000001", ["PHASE3"], results=True))
        self.assertEqual((s["nct"], s["status"], s["phases"], s["enrollment"], s["sponsor"], s["has_results"]),
                         ("NCT00000001", "COMPLETED", ["PHASE3"], 155, "University of Leeds", True))
        self.assertEqual(parse_study({})["nct"], "")

    def test_trial_counts_and_score(self):
        studies = [parse_study(x) for x in (
            study("NCT1", ["PHASE3"], results=True),
            study("NCT2", ["PHASE2", "PHASE3"]),
            study("NCT3", ["PHASE1"]),
            study("NCT4", ["PHASE2"], status="RECRUITING"),
            study("NCT5", [], kind="OBSERVATIONAL"),
        )]
        t = trial_counts(studies)
        self.assertEqual(t, {"registered": 5, "interventional": 4, "phase2_or_later": 3,
                             "phase2_or_later_completed": 2, "phase2_or_later_with_results": 1,
                             "recruiting_or_active": 1})
        pubmed = dict({d: 0 for d in DESIGNS}, all=40, rct=4, meta_analysis=2)
        self.assertEqual(score(pubmed, t), 4 + 2 * 2 + 3 * 1)


class RenderTests(unittest.TestCase):
    def test_render(self):
        studies = [parse_study(study("NCT1", ["PHASE3"], results=True))]
        a = dict(PAIR, query=pubmed_term(PAIR), pubmed=dict({d: 0 for d in DESIGNS}, all=40, rct=4, meta_analysis=2),
                 papers=[{"pmid": "39074374", "year": "2024", "journal": "Ann Intern Med", "title": "PROMOTE.",
                          "types": []}],
                 studies=studies, trials=trial_counts(studies),
                 fda={"labels": 50, "boxed_labels": 30, "boxed_text": "WARNING: SEVERE TOXIC REACTIONS"}, score=11)
        b = dict(a, slug="b", drug="zzz", condition="x", papers=[], studies=[], trials=trial_counts([]),
                 fda={"labels": 0, "boxed_labels": 0, "boxed_text": ""}, score=1)
        text = render([b, a], "2026-10-14")
        self.assertIn("| methotrexate -> knee osteoarthritis | 40 | 4 | 2 | 0 | 0 | 1 | 1 | 1 | 0 | 30/50 | 11 |", text)
        self.assertLess(text.index("| methotrexate ->"), text.index("| zzz ->"))  # ranked by score
        self.assertIn("- PMID 39074374 (2024, Ann Intern Med): PROMOTE.", text)
        self.assertIn("- NCT1 PHASE3, COMPLETED, n=155, University of Leeds, results posted: Trial NCT1", text)
        self.assertIn("A boxed warning on a current label (openFDA): WARNING: SEVERE TOXIC REACTIONS", text)
        self.assertEqual(text.count("A boxed warning on a current label"), 1)


if __name__ == "__main__":
    unittest.main()
