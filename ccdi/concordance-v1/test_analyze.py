"""Tests for the CCDI concordance job, on made-up records only (no network).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import json
import os
import shutil
import tempfile
import unittest

import analyze
import fetch_ccdi


def put(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel.endswith(".gz"):
        with gzip.open(path, "wb") as fh:
            fh.write(json.dumps(obj).encode())
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def subj(org, ns, name, sex=None, race=None, eth=None, vital=None, age=None):
    md = {"sex": {"value": sex} if sex else None,
          "race": [{"value": r} for r in (race or [])],
          "ethnicity": {"value": eth} if eth else None,
          "vital_status": {"value": vital} if vital else None,
          "age_at_vital_status": {"value": age} if age is not None else None,
          "identifiers": [{"value": {"namespace": {"organization": org, "name": ns},
                                     "name": name, "type": "Linked"}}]}
    return {"id": {"namespace": {"organization": org, "name": ns}, "name": name},
            "kind": "Participant", "metadata": md}


def case(sid, project, sex, vital, age_dx=None, dtd=None, last=None, follow=None):
    return {"submitter_id": sid, "project": {"project_id": project},
            "demographic": {"sex_at_birth": sex, "race": "white",
                            "ethnicity": "not hispanic or latino", "vital_status": vital,
                            "days_to_death": dtd},
            "diagnoses": [{"age_at_diagnosis": age_dx, "days_to_last_follow_up": last}],
            "follow_ups": [{"days_to_follow_up": f} for f in (follow or [])]}


class Normalise(unittest.TestCase):
    def test_values(self):
        self.assertEqual(analyze.norm_sex("male"), "M")
        self.assertEqual(analyze.norm_sex("U"), None)
        self.assertEqual(analyze.norm_vital("Deceased"), "Dead")
        self.assertEqual(analyze.norm_vital("Not reported"), None)
        self.assertEqual(analyze.norm_eth("Not Hispanic or Latino"), "NH")
        self.assertEqual(analyze.norm_race(["White", "Unknown"]), frozenset(["White"]))
        self.assertEqual(analyze.norm_race("Reported Unknown"), frozenset())

    def test_usi(self):
        self.assertEqual(analyze.GDC_ID.match("TARGET-30-PAUMMZ").group(1), "PAUMMZ")
        self.assertEqual(analyze.GDC_ID.match("TARGET-50-PAJNCV-01").group(1), "PAJNCV")
        self.assertIsNone(analyze.GDC_ID.match("TARGET-20-SJAML045742"))

    def test_gdc_ages(self):
        dead = analyze.gdc_case(case("TARGET-30-PAAAAA", "TARGET-NBL", "female", "Dead",
                                     age_dx=100, dtd=50))
        self.assertEqual(dead["age"], 150)
        alive = analyze.gdc_case(case("TARGET-30-PAAAAB", "TARGET-NBL", "male", "Alive",
                                      age_dx=100, last=30, follow=[40, 20]))
        self.assertEqual(alive["age"], 140)


class Compare(unittest.TestCase):
    def test_vital(self):
        cv = analyze.cmp_vital
        self.assertEqual(cv("Alive", 800, "Dead", 700), "alive_after_death")
        self.assertEqual(cv("Dead", 700, "Alive", 701), "alive_then_dead")
        self.assertEqual(cv("Alive", None, "Dead", 5), "alive_dead_no_ages")
        self.assertEqual(cv(None, 1, "Dead", 5), "uninformative")
        self.assertEqual(cv("Dead", 1, "Dead", 5), "both_dead")

    def test_race(self):
        a, b = frozenset(["White"]), frozenset(["White", "Asian"])
        self.assertEqual(analyze.cmp_race(a, b), "overlap")
        self.assertEqual(analyze.cmp_race(a, frozenset(["Asian"])), "disagree")
        self.assertEqual(analyze.cmp_race(a, frozenset()), "uninformative")


class Fetch(unittest.TestCase):
    def test_full_page(self):
        page = [{"source": "A", "summary": {"counts": {"all": 5, "current": 2}},
                 "data": [{}, {}]},
                {"source": "B", "summary": {"counts": {"all": 1, "current": 1}}, "data": [{}]}]
        sizes = fetch_ccdi.page_sizes(page)
        self.assertEqual(sizes, {"A": (5, 2), "B": (1, 1)})
        self.assertTrue(fetch_ccdi.full_page(sizes, 2))
        self.assertFalse(fetch_ccdi.full_page(sizes, 3))
        self.assertFalse(fetch_ccdi.full_page({}, 2))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        raw = os.path.join(self.tmp, "raw")
        put(raw, "subject/chosen.json", {"per_page": 2, "first_page": "probe-2.json",
                                         "pages_expected": 2})
        put(raw, "subject/probe-2.json.gz", [
            {"source": "PCDC", "summary": {"counts": {"all": 2, "current": 2}},
             "data": [subj("pcdc", "COG", "PAAAAA", "M", ["White"], "Not Hispanic or Latino"),
                      subj("pcdc", "COG", "PBBBBB", "F")]},
            {"source": "KidsFirst", "summary": {"counts": {"all": 2, "current": 2}},
             "data": [subj("include-dcc", "sd-1", "pt-1", "M", ["Unknown"], None, "Dead", 1000),
                      subj("include-dcc", "sd-1", "pt-2", "F", None, None, "Alive", 500)]}])
        put(raw, "subject/page-0002.json.gz", [
            {"source": "PCDC", "summary": {"counts": {"all": 2, "current": 0}}, "data": []},
            {"source": "KidsFirst", "summary": {"counts": {"all": 2, "current": 1}},
             "data": [subj("include-dcc", "sd-1", "pt-1", "M", None, None, "Dead", 1000)]}])
        put(raw, "mapping/page-0001.json.gz", {"supplementary_domains": [], "participant_ids": [
            {"domain_name": "KidsFirst", "participant_id": "pt-1", "associated_ids": [
                {"participant_id": "PAAAAA", "domain_name": "USI",
                 "domain_category": "organizational_identifier"}]}]})
        put(raw, "gdc/cases-00000.json.gz", {"data": {"pagination": {"total": 3}, "hits": [
            case("TARGET-10-PAAAAA", "TARGET-ALL-P2", "male", "Alive", 400, None, 300, [350]),
            case("TARGET-30-PAAAAA", "TARGET-NBL", "female", "Alive", 400),
            case("TARGET-20-SJAML1", "TARGET-AML", "male", "Dead")]}})
        put(raw, "fed/subject-summary.json.gz", [{"source": "PCDC", "counts": {"total": 2}},
                                                 {"source": "KidsFirst", "counts": {"total": 3}}])
        put(raw, "fed/count-vital_status.json.gz", [
            {"source": "PCDC", "total": 2, "missing": 0,
             "values": [{"value": "Alive", "count": 2}]},
            {"source": "KidsFirst", "total": 2, "missing": 0,
             "values": [{"value": "Dead", "count": 1}, {"value": "Alive", "count": 1}]}])
        put(raw, "fetch-log.json", [{"file": "x", "status": 200}])
        self.raw, self.out = raw, os.path.join(self.tmp, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_run(self):
        analyze.main(["--raw", self.raw, "--out", self.out])
        r = json.load(open(os.path.join(self.out, "concordance.json"), encoding="utf-8"))
        a = r["A_internal_consistency"]
        self.assertEqual(a["KidsFirst"]["repeated_records"], 1)
        self.assertEqual(a["KidsFirst"]["unique_served"], 2)
        self.assertTrue(a["KidsFirst"]["fields"]["vital_status"]["consistent"])
        pv = a["PCDC"]["fields"]["vital_status"]
        self.assertFalse(pv["consistent"])
        self.assertEqual(pv["endpoint_vs_served"], {"<missing>": [0, 2], "Alive": [2, 0]})
        self.assertIsNone(a["PCDC"]["fields"]["sex"]["endpoint_total"])
        b = r["B_gdc_target"]
        self.assertEqual((b["cases"], b["cases_with_usi"], b["distinct_usis"]), (3, 2, 1))
        self.assertEqual(b["gdc_internal"]["sex"], {"disagree": 1})
        self.assertEqual(b["usis_linked_to_federation"], 1)
        self.assertEqual(b["gdc_vs_federation"]["PCDC"]["sex"], {"agree": 1})
        self.assertEqual(b["gdc_vs_federation"]["KidsFirst"]["vital"], {"alive_then_dead": 1})
        self.assertEqual(b["vital_disagreement_direction"], {"gdc_Alive_fed_Dead": 1})
        self.assertEqual(b["age_ratio_fed_over_gdc"]["n"], 1)
        c = r["C_cpi_links"]
        self.assertEqual(c["pairs"], 1)
        self.assertEqual(c["all"]["sex"], {"agree": 1})
        self.assertEqual(c["all"]["race"], {"uninformative": 1})
        self.assertEqual(r["D_overcount"], {"subjects_served": 4,
                                            "subjects_in_cross_source_links": 2,
                                            "linked_persons": 1, "deduplicated_total": 3,
                                            "naive_overcount": 1})
        g = r["grades"]
        self.assertEqual(g["H1"]["result"], "fail")
        self.assertEqual(g["H2"]["result"], "pass")
        self.assertEqual(g["H4"]["result"], "not testable")
        self.assertEqual(g["H5"]["result"], "not testable")
        self.assertEqual(g["H6"]["result"], "fail")
        self.assertEqual(g["H7"]["result"], "fail")
        text = open(os.path.join(self.out, "concordance.json"), encoding="utf-8").read()
        for ident in ("PAAAAA", "PBBBBB", "pt-1", "pt-2", "SJAML1", "TARGET-10", "TARGET-30"):
            self.assertNotIn(ident, text)


if __name__ == "__main__":
    unittest.main()
