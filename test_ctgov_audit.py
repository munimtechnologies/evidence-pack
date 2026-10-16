# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import json
import os
import tempfile
import unittest

import ctgov_audit as ca


def om(title, unit, param, disp, rows, desc="", otype="PRIMARY"):
    """Outcome measure in API v2 shape; rows = [(gid, n, value, spread, lower, upper)]."""
    meas = []
    for gid, n, value, spread, lower, upper in rows:
        m = {"groupId": gid, "value": value}
        if spread is not None:
            m["spread"] = spread
        if lower is not None:
            m["lowerLimit"] = lower
        if upper is not None:
            m["upperLimit"] = upper
        meas.append(m)
    return {
        "type": otype, "title": title, "description": desc, "unitOfMeasure": unit,
        "paramType": param, "dispersionType": disp,
        "groups": [{"id": r[0], "title": "Group " + r[0]} for r in rows],
        "denoms": [{"units": "Participants",
                    "counts": [{"groupId": r[0], "value": str(r[1])} for r in rows]}],
        "classes": [{"categories": [{"measurements": meas}]}],
    }


class Helpers(unittest.TestCase):
    def test_num_and_half_unit(self):
        self.assertIsNone(ca.num("NA"))
        self.assertEqual(ca.num("1,234.5"), 1234.5)
        self.assertAlmostEqual(ca.half_unit("26.7"), 0.05)
        self.assertEqual(ca.half_unit("18"), 0.5)
        self.assertAlmostEqual(ca.half_unit("0.082"), 0.0005)

    def test_kinds(self):
        self.assertEqual(ca.disp_kind("Standard Deviation"), "SD")
        self.assertEqual(ca.disp_kind("STANDARD_ERROR"), "SE")
        self.assertEqual(ca.disp_kind("INTER_QUARTILE_RANGE"), "IQR")
        self.assertEqual(ca.disp_kind("FULL_RANGE"), "RANGE")
        self.assertEqual(ca.disp_kind("CONFIDENCE_95"), "CI")
        self.assertEqual(ca.disp_kind("NA"), "")
        self.assertEqual(ca.param_kind("MEAN"), "MEAN")
        self.assertEqual(ca.param_kind("Mean"), "MEAN")
        self.assertEqual(ca.param_kind("LEAST_SQUARES_MEAN"), "LSMEAN")
        self.assertEqual(ca.param_kind("GEOMETRIC_LEAST_SQUARES_MEAN"), "GEOMETRIC")
        self.assertEqual(ca.param_kind("MEDIAN"), "MEDIAN")
        self.assertEqual(ca.param_kind("NUMBER"), "NUMBER")

    def test_bounds_for(self):
        self.assertEqual(ca.bounds_for("Percent Days of Heavy Drinking", "percentage of days of heavy drinking"),
                         (0.0, 100.0, "percent"))
        self.assertIsNone(ca.bounds_for("Change in Percentage of Heavy Drinking Days", "percent heavy drinking days"))
        self.assertIsNone(ca.bounds_for("Percentage of Participants With Response at Week 12",
                                        "percentage of participants"))
        self.assertIsNone(ca.bounds_for("FEV1 at Week 12", "percent predicted"))
        self.assertEqual(ca.bounds_for("Abstinent days", "proportion of days"), (0.0, 1.0, "proportion"))
        self.assertEqual(ca.bounds_for("Daily Activity", "% of Day"), (0.0, 100.0, "percent"))

    def test_bounds_need_time_word_in_unit(self):
        # v0.2 false positives: the time word was only in the title
        self.assertIsNone(ca.bounds_for("Y-balance Testing at Week 12", "Percentage of limb length"))
        self.assertIsNone(ca.bounds_for("AUEC(Final Extent) on Day 1", "%*h"))
        self.assertIsNone(ca.bounds_for("Tacrolimus Fluctuation Was Measured at Day 21.", "percentage"))

    def test_unbounded_quantities(self):
        # v0.5 false positives from the v0.4 census
        self.assertIsNone(ca.bounds_for("Mean Treatment Adherence (%)", "Percentage of days",
                                        "Adherence was measured with a medication possession ratio (MPR)"))
        self.assertEqual(ca.bounds_for("Mean Treatment Adherence (%)", "Percentage of days"),
                         (0.0, 100.0, "percent"))
        self.assertIsNone(ca.bounds_for("Rate of Mutation Clearance During Treatment",
                                        "proportion of variant alleles per day"))
        self.assertIsNone(ca.bounds_for("Time in range AUC", "percent of time"))

    def test_scale_bounds(self):
        self.assertEqual(ca.scale_bounds("CAPS-5 total score", "score on a scale",
                                         "PTSD symptom diagnostic interview CAPS-5 score range = 0 - 80 "
                                         "Higher scores = more severe PTSD symptoms"), (0.0, 80.0, "scale"))
        self.assertEqual(ca.scale_bounds("Pain intensity", "units on a scale",
                                         "Scores range from 0 (no pain) to 10 (worst pain)."),
                         (0.0, 10.0, "scale"))
        self.assertEqual(ca.scale_bounds("The Penn Alcohol Craving Scale", "score on a scale",
                                         "This Scale measures alcohol craving. The maximum score is 30, "
                                         "the minimum score is 0."), (0.0, 30.0, "scale"))
        self.assertEqual(ca.scale_bounds("Pain", "units on a scale", "Rated on a 0-100 mm visual analogue scale."),
                         (0.0, 100.0, "scale"))
        self.assertIsNone(ca.scale_bounds("Symptom score", "score on a scale", "Each item is scored 0-4."))
        self.assertIsNone(ca.scale_bounds("Symptom score", "score on a scale",
                                          "Total ranges 0-10; the second part ranges 0-100."))
        self.assertIsNone(ca.scale_bounds("Symptom score", "mg/dL", "Scores range from 0 to 10."))
        self.assertIsNone(ca.scale_bounds("Change in pain", "units on a scale", "Scores range from 0 to 10."))
        # v0.5: an area under a 0-100 VAS curve is not bounded by 0-100
        self.assertIsNone(ca.scale_bounds("Perceived Satiety (Area Under the Curve)", "score on a scale",
                                          "Rated on a 0-100 mm visual analogue scale."))

    def test_average_range_is_not_a_scale(self):
        # v0.6: NCT00085202 as posted; 85-115 is where average scores fall, not the limits
        self.assertIsNone(ca.scale_bounds("Processing Speed for Two Risk Group at Enrollment", "score on a scale",
                                          "This score measure of Processing Speed based on Visual Matching and "
                                          "Decision Speed tests. Mean=100, SD=15, Average Range 85-115. "
                                          "Higher is better."))

    def test_study_clustered(self):
        a = {"nonInferiorityComment": "Hierarchical linear model accounting for randomization of communities "
                                      "and clustering of children within communities"}
        self.assertTrue(ca.study_clustered([{"analyses": [a]}]))
        self.assertFalse(ca.study_clustered([{"analyses": [{"statisticalMethod": "ANCOVA"}]}]))
        self.assertFalse(ca.study_clustered([{"analyses": [{"groupDescription": "cluster headache attacks"}]}]))
        self.assertFalse(ca.study_clustered([{"description": "no analyses posted"}]))

    def test_sd_max(self):
        self.assertAlmostEqual(ca.sd_max(50, 0, 100, 2), 70.7107, places=3)
        self.assertAlmostEqual(ca.sd_max(50, 0, 100, None), 50.0)
        self.assertEqual(ca.sd_max(0, 0, 100, 10), 0.0)


class Checks(unittest.TestCase):
    def test_sd_above_max_percent_days(self):
        m = om("Percent Days Abstinent", "percentage of days", "MEAN", "Standard Deviation",
               [("OG000", 20, "10.0", "45.0", None, None), ("OG001", 84, "62.8", "45.4", None, None)])
        flags = ca.check_measure(m, "NCT00000001")
        self.assertEqual([f["check"] for f in flags], ["sd_above_max"])
        self.assertEqual(flags[0]["group"], "Group OG000")
        self.assertEqual(flags[0]["tier"], "impossible")
        self.assertAlmostEqual(flags[0]["limit"], 30.848, places=2)

    def test_sd_above_max_level_stays_impossible(self):
        # NCT03808909 as posted: mean 19.85, SD 44.509, n 9; cap about 42.31
        m = om("Percentage of Days With Drinking or Substance Use", "percentage of days", "MEAN",
               "Standard Deviation", [("OG000", 9, "19.85", "44.509", None, None)],
               desc="average percentage of days of alcohol or other substance use for each group")
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags], [("sd_above_max", "impossible")])
        self.assertAlmostEqual(flags[0]["limit"], 42.31, places=1)

    def test_change_description_demotes_sd_above_max(self):
        # NCT04623086 as posted: description "Change in nocturnal ... time in range"
        m = om("Nocturnal Percent Time in Range of 70-180 mg/dL", "percentage of time in measured period",
               "MEAN", "Standard Deviation",
               [("OG000", 19, "5.1", "34.6", None, None), ("OG001", 18, "-7", "34.2", None, None)],
               desc="Change in nocturnal (defined as midnight to 0600 hours) time in range")
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags],
                         [("sd_above_max_if_level", "suspect"), ("mean_below_floor", "suspect")])

    def test_change_class_title_demotes_sd_above_max(self):
        # NCT05785832 as posted: class "Change from Baseline", mean 1, SD 14, n 104
        m = om("Time in Range 70-180 mg/dL", "percentage of time", "MEAN", "Standard Deviation",
               [("OG000", 104, "1", "14", None, None)])
        m["classes"][0]["title"] = "Change from Baseline"
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags], [("sd_above_max_if_level", "suspect")])

    def test_negative_sibling_demotes_sd_above_max(self):
        # NCT03477838 as posted: "Time in Hyperglycemia" 1.5 (SD 30.4) next to "Time in Therapeutic goal" -3.17
        m = om("Glycemic Variability", "percent time in range", "MEAN", "Standard Deviation",
               [("OG000", 14, "1.5", "30.4", None, None), ("OG001", 14, "-3.17", "23.5", None, None)])
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags],
                         [("sd_above_max_if_level", "suspect"), ("mean_below_floor", "suspect")])

    def test_sd_above_width_ignores_change_guard(self):
        # an SD wider than the whole width is impossible even for a change score
        m = om("Daily Activity", "% of Day", "MEAN", "Standard Deviation",
               [("OG000", 46, "15.64", "8362", None, None)], desc="Change in daily activity")
        self.assertEqual([f["check"] for f in ca.check_measure(m)], ["sd_above_width"])

    def test_sd_above_width(self):
        # NCT02240186 as posted: "% of Day", mean 15.64, SD 8362, n 46
        m = om("Daily Activity", "% of Day", "MEAN", "Standard Deviation",
               [("OG000", 46, "15.64", "8362", None, None)])
        flags = ca.check_measure(m)
        self.assertEqual([f["check"] for f in flags], ["sd_above_width"])
        self.assertEqual(flags[0]["tier"], "impossible")
        self.assertAlmostEqual(flags[0]["limit"], 101.105, places=2)

    def test_mean_outside_bounds(self):
        m = om("Percent Days Abstinent", "percentage of days", "MEAN", "STANDARD_DEVIATION",
               [("OG000", 20, "104.0", "5.0", None, None)])
        self.assertEqual([f["check"] for f in ca.check_measure(m)], ["mean_outside_bounds"])

    def test_negative_mean_is_suspect_not_impossible(self):
        m = om("Percent Days Abstinent", "percentage of days", "MEAN", "Standard Deviation",
               [("OG000", 18, "-7", "34.2", None, None), ("OG001", 18, "-140", "5", None, None)])
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags],
                         [("mean_below_floor", "suspect"), ("mean_outside_bounds", "impossible")])

    def test_median_outside_iqr_and_inverted_ci(self):
        m = om("Time to relapse", "days", "MEDIAN", "INTER_QUARTILE_RANGE",
               [("OG000", 30, "5.0", None, "6.0", "9.0"), ("OG001", 30, "7.0", None, "6.0", "9.0")])
        self.assertEqual([f["check"] for f in ca.check_measure(m)], ["center_outside_interval"])
        c = om("Ratio", "ratio", "GEOMETRIC_MEAN", "CONFIDENCE_95",
               [("OG000", 30, "2.0", None, "2.5", "1.5")])
        self.assertEqual([f["check"] for f in ca.check_measure(c)], ["inverted_interval"])

    def test_rounding_and_edges_pass(self):
        ci = om("Rate ratio", "ratio", "NUMBER", "CONFIDENCE_95", [("OG000", 14, "0.89", None, "0.89", "0.98")])
        self.assertEqual(ca.check_measure(ci), [])
        iqr = om("Days", "days", "MEDIAN", "INTER_QUARTILE_RANGE", [("OG000", 30, "5", None, "6", "9")])
        self.assertEqual(ca.check_measure(iqr), [])
        lsm = om("Days", "days", "LEAST_SQUARES_MEAN", "FULL_RANGE", [("OG000", 30, "5.0", None, "6.0", "9.0")])
        self.assertEqual(ca.check_measure(lsm), [])

    def test_negative_sd(self):
        m = om("Weight", "kg", "MEAN", "Standard Deviation", [("OG000", 10, "80.1", "-3.2", None, None)])
        self.assertEqual([f["check"] for f in ca.check_measure(m)], ["negative_dispersion"])

    def test_suspect_proportion_sd(self):
        m = om("Change in Percentage of Heavy Drinking Days", "percent heavy drinking days", "MEAN",
               "Standard Deviation", [("OG000", 72, "-36.2", "0.41", None, None),
                                      ("OG001", 79, "-25.1", ".36", None, None)])
        flags = ca.check_measure(m)
        self.assertEqual([f["check"] for f in flags], ["sd_scale_suspect", "sd_scale_suspect"])
        self.assertEqual({f["tier"] for f in flags}, {"suspect"})

    def test_scale_sd_above_max(self):
        m = om("Pain intensity", "units on a scale", "MEAN", "Standard Deviation",
               [("OG000", 30, "9.5", "4.0", None, None), ("OG001", 30, "5.0", "3.0", None, None)],
               desc="Scores range from 0 (no pain) to 10 (worst pain).")
        flags = ca.check_measure(m)
        self.assertEqual([f["check"] for f in flags], ["scale_sd_above_max"])
        self.assertEqual(flags[0]["tier"], "scale")

    def test_se_implies_sd_above_width(self):
        # v0.4: SE 30.0 with n 50 means SD about 212 on a 0-100 measure; SE 3.0 (SD about 21) passes
        m = om("Percent Days Abstinent", "percentage of days", "MEAN", "Standard Error",
               [("OG000", 50, "40.0", "30.0", None, None), ("OG001", 50, "45.0", "3.0", None, None)])
        flags = ca.check_measure(m)
        self.assertEqual([(f["check"], f["tier"]) for f in flags], [("se_implies_sd_above_width", "se_implied")])
        self.assertEqual(flags[0]["group"], "Group OG000")
        self.assertAlmostEqual(flags[0]["limit"], 101.015, places=2)
        self.assertAlmostEqual(flags[0]["ratio"], 2.096, places=2)

    def test_se_implied_on_stated_scale(self):
        m = om("Pain intensity", "units on a scale", "MEAN", "Standard Error",
               [("OG000", 40, "5.0", "2.0", None, None)],
               desc="Scores range from 0 (no pain) to 10 (worst pain).")
        self.assertEqual([f["check"] for f in ca.check_measure(m)], ["se_implies_sd_above_width"])

    def test_se_implied_skips_model_means(self):
        m = om("Percent Days Abstinent", "percentage of days", "LEAST_SQUARES_MEAN", "Standard Error",
               [("OG000", 50, "40.0", "30.0", None, None)])
        self.assertEqual(ca.check_measure(m), [])

    def test_se_implied_skips_bounds_the_means_do_not_fit(self):
        # v0.6: NCT03674892 as posted: total-score means 59.6 and 53.31 under a per-item "0-10"
        m = om("Quality of Life as Measured Daily With OPAS at 45 Days", "units on a scale", "MEAN",
               "Standard Error", [("OG000", 12, "59.6", "8.91", None, None), ("OG001", 6, "53.31", "26.01", None, None)],
               desc="Scores range from 0 to 10.")
        stats = ca.Counter()
        self.assertEqual(ca.check_measure(m, stats=stats), [])
        self.assertEqual(stats["measures_se_bounds_misfit"], 1)

    def test_cluster_demotes_se_implied(self):
        # v0.6: NCT01881373 as posted: community-randomised, n 2859, SE 0.35 on a 1-9 score
        m = om("Sleep Disturbance Score", "units on a scale", "MEAN", "Standard Error",
               [("OG000", 2859, "-0.4", "0.35", None, None), ("OG001", 2786, "0.3", "0.19", None, None)],
               desc="Scores range from 1 to 9.", otype="SECONDARY")
        self.assertEqual([(f["check"], f["tier"]) for f in ca.check_measure(m)],
                         [("se_implies_sd_above_width", "se_implied")] * 2)
        self.assertEqual([(f["check"], f["tier"]) for f in ca.check_measure(m, clustered=True)],
                         [("se_implied_cluster", "suspect")] * 2)


class EndToEnd(unittest.TestCase):
    def test_run_from_jsonl(self):
        study = {"protocolSection": {"identificationModule": {"nctId": "NCT00000002"},
                                     "sponsorCollaboratorsModule": {"leadSponsor": {"name": "X", "class": "OTHER"}},
                                     "statusModule": {"resultsFirstPostDateStruct": {"date": "2019-05-01"}}},
                 "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
                     om("Percent Days Abstinent", "percentage of days", "MEAN", "Standard Deviation",
                        [("OG000", 20, "10.0", "45.0", None, None)])]}}}
        clean = {"protocolSection": {"identificationModule": {"nctId": "NCT00000003"}},
                 "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
                     om("Weight", "kg", "MEAN", "Standard Deviation", [("OG000", 10, "80.1", "3.2", None, None)])]}}}
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.jsonl")
            with open(src, "w", encoding="utf-8") as f:
                f.write(json.dumps(study) + "\n" + json.dumps(clean) + "\n")
            out = os.path.join(d, "out")
            self.assertEqual(ca.main(["--input", src, "--out-dir", out]), 0)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as f:
                s = json.load(f)
            self.assertEqual(s["stats"]["studies"], 2)
            self.assertEqual(s["per_check"]["sd_above_max"]["studies"], 1)
            self.assertEqual(s["by_sponsor_class"]["OTHER"]["with_impossible"], 1)
            self.assertEqual(s["by_results_year"]["2019"]["with_impossible"], 1)
            self.assertEqual(s["studies_by_tier"], {"impossible": ["NCT00000002"]})
            self.assertTrue(os.path.exists(os.path.join(out, "raw", "NCT00000002.json")))
            self.assertFalse(os.path.exists(os.path.join(out, "raw", "NCT00000003.json")))
            with open(os.path.join(out, "flags.csv"), encoding="utf-8") as f:
                self.assertEqual(len(f.read().strip().splitlines()), 2)

    def test_clustered_study_end_to_end(self):
        m = om("Sleep Disturbance Score", "units on a scale", "MEAN", "Standard Error",
               [("OG000", 2859, "-0.4", "0.35", None, None)], desc="Scores range from 1 to 9.")
        m["analyses"] = [{"nonInferiorityComment": "Hierarchical model accounting for clustering of children"}]
        study = {"protocolSection": {"identificationModule": {"nctId": "NCT00000004"}},
                 "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [m]}}}
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.jsonl")
            with open(src, "w", encoding="utf-8") as f:
                f.write(json.dumps(study) + "\n")
            out = os.path.join(d, "out")
            self.assertEqual(ca.main(["--input", src, "--out-dir", out]), 0)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as f:
                s = json.load(f)
            self.assertEqual(s["stats"]["studies_clustered"], 1)
            self.assertIn("se_implied_cluster", s["per_check"])
            self.assertNotIn("se_implies_sd_above_width", s["per_check"])
            self.assertEqual(s["studies_by_tier"], {})


if __name__ == "__main__":
    unittest.main()
