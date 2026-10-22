"""Unit tests for claimcheck.modules2 part 2 (R2, R2b, R3, R4, R5b, R7-a, R8), on synthetic
strings only (plan v7 section 8 step 3).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import unittest
from datetime import date

from claimcheck import grammar as g
from claimcheck import modules2 as m

TDOC = "\n".join([
    "## E.3 Results [8]",                                                              # 1
    "| Outcome | HR (95% CI) | Rate |",                                                # 2
    "|---|---|---|",                                                                   # 3
    "| A | 0.77 (0.64-0.92) | 8.0% |",                                                 # 4
    "| B | 0.81 (0.70-0.95) | 9.9% |",                                                 # 5
    "| C | 0.97 (0.80-1.10) | 10.4% |",                                                # 6
    "- HR 0.77-0.81 for outcome A and B, CI below 1 in two of three outcomes [8].",    # 7
    "- HR 0.77-0.85 overall [8].",                                                     # 8
    "- Rate 8.0%-10.4% in 2 outcome rows [8].",                                        # 9
    "- HR below 1 in two of three [8].",                                               # 10
    "- Ranges 1-2 here [9].",                                                          # 11
    "- Values 1.0-2.0 in total [8].",                                                  # 12
    "- HR in one of three [8].",                                                       # 13
]) + "\n"

RDOC = "\n".join([
    "## E.2 Registered trials",                                                        # 1
    "- Three trials are registered on ClinicalTrials.gov: NCT01234567, NCT07654321 "
    "and a pilot trial.",                                                              # 2
    "- We found 2 records in ChiCTR (ChiCTR2500107918) and ISRCTN12345678.",           # 3
    "- PubMed lists 40 records.",                                                      # 4
    "- Two trials are registered, listed below:",                                      # 5
    "  - NCT01111111 (Smith 2020)",                                                    # 6
    "  - NCT02222222 (Jones 2021)",                                                    # 7
    "  - ISRCTN87654321",                                                              # 8
    "Next paragraph.",                                                                 # 9
    "- **Other registered trials:** NCT03333333 (Lee 2022); the SPIRO study; none.",   # 10
    "- No trials are registered on ClinicalTrials.gov.",                               # 11
]) + "\n"

CDOC = "\n".join([
    "## C. Effects",                                                                   # 1
    "- There was no difference, MD 0.12 (-0.56 to 0.81).",                             # 2
    "- Lower risk with use (aHR 1.05, 0.94-1.18); stronger effect in women, "
    "SMD 0.40 (0.10-0.70).",                                                           # 3
    "- No clear difference was seen; there was no benefit.",                           # 4
    "- No difference given in the source.",                                            # 5
    "- Weaker in rats, HR 0.80 (0.70-0.90).",                                          # 6
]) + "\n"

DDOC = "\n".join([
    "# Package",                                                                       # 1
    "## Overview",                                                                     # 2
    "- Spironolactone was first approved 1960-01-21 in the US.",                       # 3
    "## B. Background",                                                                # 4
    "- It has been more than 65 years on the US market.",                              # 5
    "- It has been about 60 years on the market.",                                     # 6
    "- No trial is registered.",                                                       # 7
    "- As of 2026-10-20, no trial is registered.",                                     # 8
    "- **Result (as of 2026-10-20):** None has posted results.",                       # 9
    "**Registered trials** (searched 2026-10-15):",                                    # 10
    "- One trial is unreported.",                                                      # 11
    "- The trial ended (primary completion 2024-12-31); no results posted as of "
    "2026-10-20, nearly 22 months after its planned completion.",                      # 12
    "- Results came 3 years ago.",                                                     # 13
    '- The drug is "not yet recruiting" and cannot be published.',                     # 14
]) + "\n"

LDOC = "\n".join([
    "## E.5 Checks",                                                                   # 1
    "- We checked four studies (Chenchula, Guo, Kao and Chen Z) with the tool.",       # 2
    "- Three trials were read: Pan, Aiad; Alimoradi also reported KOOS.",              # 3
    "- We read 27 records: VA 9; KPNC 9; Optum 4; MarketScan 5.",                      # 4
    "- We read 3 studies (Pan, Aiad).",                                                # 5
    "- We found 0 studies (Pan) in 2019.",                                             # 6
    "- We read five studies (all small).",                                             # 7
]) + "\n"

MDOC = "\n".join([
    "## C. Animal evidence",                                                           # 1
    "- **Mouse data:** In mice, 200 mg/kg is about 16 mg/kg by body surface area, "
    "or about 1.1 g/day for 70 kg.",                                                   # 2
    "- In rats, 100 mg/kg (body surface area) is about 20 mg/kg, "
    "or about 1.1 g/day for 60 kg.",                                                   # 3
    "- A rat dose of 50 mg/kg was used; see PMC and DailyMed.",                        # 4
    "### E.6 Sources",                                                                 # 5
    "- PubMed, Europe PMC and ClinicalTrials.gov.",                                    # 6
    "## References",                                                                   # 7
    "1. Smith A. Title. Orange Book listing, 2020. PMID 12345678.",                    # 8
]) + "\n"


class Tables(unittest.TestCase):
    def test_columns(self):
        cols = m.columns(g.Doc(TDOC))[0]
        self.assertEqual([sorted(c.words) for c in cols], [["Outcome"], ["HR"], ["Rate"]])
        self.assertEqual(cols[1].rows[2], (0.97, (0.80, 1.10)))
        self.assertEqual([(v.value, v.pct) for v in cols[2].values],
                         [(8.0, True), (9.9, True), (10.4, True)])

    def test_ranges_skip_intervals(self):
        text = "HR 0.80 (0.70-0.90), 95% CI 1.2-1.5, 0.5, 0.6-0.7 and 3 to 4"
        self.assertEqual([(a.text, b.text) for a, b, _ in m.ranges(text)], [("3", "4")])

    def test_r2(self):
        flags = m.r2(g.Doc(TDOC))
        self.assertEqual([(f.line, f.rule, f.scored) for f in flags],
                         [(8, "range", True), (9, "range-in-K", True), (10, "N-of-M", True),
                          (12, "out-of-scope", False), (13, "no-predicate", False)])
        self.assertEqual(flags[0].evidence, (2, 4, 5, 6))
        self.assertEqual(flags[1].span, "8.0%-10.4% in 2 outcome")


class RegistryCounts(unittest.TestCase):
    def test_r2b(self):
        flags = m.r2b(g.Doc(RDOC))
        self.assertEqual([(f.line, f.evidence, f.data["stated"], len(f.data["in_scope"]))
                          for f in flags],
                         [(2, (), 3, 2), (3, (), 2, 1), (5, (6, 7, 8), 2, 3)])
        self.assertEqual(flags[1].data["out_of_scope"], ["ISRCTN12345678"])

    def test_r5b(self):
        self.assertEqual([(f.line, f.rule, f.span) for f in m.r5b(g.Doc(RDOC))],
                         [(2, "item", "a pilot trial"), (10, "lead", "the SPIRO study"),
                          (10, "lead", "none")])

    def test_pieces(self):
        self.assertEqual(m._pieces("A (x, y), B; C and D and E."),
                         ["A (x, y)", "B", "C and D", "E"])


class Direction(unittest.TestCase):
    def test_r3(self):
        self.assertEqual([(f.line, f.rule, f.span) for f in m.r3(g.Doc(CDOC))],
                         [(2, "ci-includes-null", "no difference"),
                          (3, "ci-includes-null", "Lower risk"),
                          (4, "no-ci", "no benefit")])


class Dates(unittest.TestCase):
    def test_anchors(self):
        s = "checked 2026-10-20 and 5 March 2026; re-read the page on 2026-10-01"
        self.assertEqual([d for _, _, d in m.anchors(s)], [date(2026, 10, 20), date(2026, 10, 1)])

    def test_months_between(self):
        self.assertAlmostEqual(m._months_between(date(2024, 12, 31), date(2026, 10, 20)),
                               21.657, places=2)

    def test_r4(self):
        flags = m.r4(g.Doc(DDOC))
        self.assertEqual([(f.line, f.rule, f.scored) for f in flags],
                         [(6, "a", True), (7, "b", True), (13, "a-unbound", False)])
        self.assertEqual(flags[0].data["start"], "1960-01-21")
        self.assertEqual(flags[0].data["end"], "2027-03-26")


class Lists(unittest.TestCase):
    def test_r7_a(self):
        self.assertEqual([(f.line, f.data["stated"], f.data["readings"]) for f in m.r7_a(g.Doc(LDOC))],
                         [(3, 3, {"A": 2, "B": 2}), (5, 3, {"A": 2, "B": 1})])


class Doses(unittest.TestCase):
    def test_r8_dose(self):
        self.assertEqual([(f.line, f.rule, f.evidence) for f in m.r8_dose(g.Doc(MDOC))],
                         [(3, "hed", ()), (3, "total", ()), (3, "weight", (2,))])

    def test_r8_sources(self):
        self.assertEqual([(f.span, f.line, f.evidence) for f in m.r8_sources(g.Doc(MDOC))],
                         [("PMC", 4, (5, 6)), ("DailyMed", 4, (5, 6)), ("Orange Book", 8, (5, 6))])


class Check(unittest.TestCase):
    def test_check_doc(self):
        self.assertEqual([(f.line, f.module, f.rule) for f in m.check(g.Doc(CDOC))],
                         [(1, "R1b", "b"), (2, "R3", "ci-includes-null"),
                          (3, "R3", "ci-includes-null"), (4, "R3", "no-ci")])


if __name__ == "__main__":
    unittest.main()
