# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import unittest

import nhanes_spiro as ns

try:
    import statsmodels  # noqa: F401
    HAVE_SM = True
except ImportError:
    HAVE_SM = False


class TestParsing(unittest.TestCase):
    def test_code(self):
        self.assertEqual(ns.code(5.397605346934028e-79), 0)
        self.assertEqual(ns.code(2.0), 2)
        self.assertIsNone(ns.code(float("nan")))
        self.assertIsNone(ns.code("x"))
        self.assertIsNone(ns.code(None))

    def test_ingredients(self):
        self.assertEqual(ns.ingredients("Hydrochlorothiazide; Spironolactone"),
                         ["HYDROCHLOROTHIAZIDE", "SPIRONOLACTONE"])
        self.assertEqual(ns.ingredients(b"LISINOPRIL"), ["LISINOPRIL"])
        self.assertEqual(ns.ingredients(float("nan")), [])
        self.assertEqual(ns.ingredients(""), [])

    def test_drinks_and_heavy(self):
        self.assertIsNone(ns.drinks(777))
        self.assertIsNone(ns.drinks(999))
        self.assertIsNone(ns.drinks(0))
        self.assertIsNone(ns.drinks(None))
        self.assertEqual(ns.drinks(32), 15)
        self.assertEqual(ns.drinks(3.0), 3)
        self.assertEqual(ns.heavy(4, True), 1)
        self.assertEqual(ns.heavy(4, False), 0)
        self.assertEqual(ns.heavy(5, False), 1)

    def test_years(self):
        self.assertAlmostEqual(ns.TOTAL_YEARS, 15.2, places=9)
        self.assertNotIn(ns.SPIRO, ns.ANTIHYPERTENSIVES)


class TestRx(unittest.TestCase):
    def test_summarize(self):
        rx = ns.summarize_rx([
            (1, "SPIRONOLACTONE", 400), (1, "Amlodipine; Benazepril", 30), (1, "METFORMIN", None),
            (2, "EPLERENONE", 10), (2, "LISINOPRIL", 10),
            (3, "HYDROCHLOROTHIAZIDE; SPIRONOLACTONE", 99999), (3, "SPIRONOLACTONE", 60),
        ])
        self.assertEqual(rx[1], {"spiro": True, "excluded": False, "n_other": 2, "spiro_days": 400})
        self.assertEqual(rx[2], {"spiro": False, "excluded": True, "n_other": 1, "spiro_days": None})
        self.assertEqual(rx[3], {"spiro": True, "excluded": False, "n_other": 1, "spiro_days": 60})


class TestRows(unittest.TestCase):
    RAW = {"RIDAGEYR": 55, "BPQ020": 1, "MCQ160B": 2, "MCQ160L": 2, "ALQ130": 6,
           "RIAGENDR": 2, "RIDRETH1": 3, "DMDEDUC2": 9}
    RX = {"spiro": True, "excluded": False, "n_other": 5, "spiro_days": 120}

    def test_eligible(self):
        self.assertEqual(ns.analysis_row(dict(self.RAW), dict(self.RX)), {
            "age": 55, "female": 1, "race": 3, "educ": 0, "y": 6, "heavy": 1,
            "spiro": 1, "spiro_days": 120, "n_other": 4})

    def test_exclusions(self):
        for key, val in (("BPQ020", 2), ("MCQ160L", 1), ("MCQ160B", None), ("RIDAGEYR", 19), ("ALQ130", 999)):
            raw = dict(self.RAW)
            raw[key] = val
            self.assertIsNone(ns.analysis_row(raw, dict(self.RX)), key)
        self.assertIsNone(ns.analysis_row(dict(self.RAW), None))
        self.assertIsNone(ns.analysis_row(dict(self.RAW), dict(self.RX, excluded=True)))
        self.assertIsNone(ns.analysis_row(dict(self.RAW), dict(self.RX, spiro=False, n_other=0)))
        self.assertIsNotNone(ns.analysis_row(dict(self.RAW), dict(self.RX, spiro=False, n_other=1)))


class TestModel(unittest.TestCase):
    def test_design(self):
        rows = [{"spiro": 1, "age": 50, "female": 0, "race": 3, "educ": 5, "cycle": "A", "n_other": 1},
                {"spiro": 0, "age": 60, "female": 0, "race": 1, "educ": 5, "cycle": "B", "n_other": 2}]
        X, names = ns.design(rows, ["A", "B"])
        self.assertEqual(names, ["const", "spiro", "age", "age2", "race1", "cycle:B", "n_other"])
        self.assertEqual(X[0], [1.0, 1.0, 5.0, 25.0, 0.0, 0.0, 1.0])
        X, names = ns.design(rows, ["A", "B"], adjusted=False)
        self.assertEqual(names, ["const", "spiro"])

    def test_decide(self):
        self.assertEqual(ns.decide(-0.5, -0.1), "supported")
        self.assertEqual(ns.decide(0.1, 0.4), "contradicted")
        self.assertEqual(ns.decide(-0.3, 0.2), "inconclusive")

    @unittest.skipUnless(HAVE_SM, "statsmodels not installed")
    def test_fit(self):
        rows = [{"spiro": i % 2, "y": 2.0 - (i % 2) + ((i % 5) - 2) * 0.1, "w": 1.0,
                 "cluster": "c%d" % (i % 10)} for i in range(40)]
        r = ns.fit(rows, "y", ["A"], adjusted=False)
        self.assertEqual((r["n"], r["n_spiro"], r["clusters"]), (40, 20, 10))
        self.assertAlmostEqual(r["beta"], -1.0, places=9)
        self.assertEqual(r["decision"], "supported")


if __name__ == "__main__":
    unittest.main()
