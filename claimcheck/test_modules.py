"""Unit tests for claimcheck.modules part 1 (R1, R1b, R5, R6-a), on synthetic strings only
(plan v7 section 8 step 3).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import unittest

from claimcheck import grammar as g
from claimcheck import modules as m

DOC = "\n".join([
    "# Package",                                                                       # 1
    "## B. Background",                                                                # 2
    "- Loften et al. 2026 [8] found HR 1.84 (1.55-2.18) for remission.",              # 3
    "- The SAUD trial and the RWE study are cited; Smith 2020 reported more.",         # 4
    '- Planned in run 3 and v19; see API v2, release v0.4, "gate 2" and 2026 run.',    # 5
    "## C. Effects",                                                                   # 6
    "### C.1 Animal",                                                                  # 7
    "- SMD -0.43 (95% CI -0.80 to -0.06) in rats.",                                    # 8
    "- SMD 0.25 (0.10-0.40) in mice.",                                                 # 9
    "### C.2 Human",                                                                   # 10
    "- Negative = benefit. MD -1.2 (-2.0 to -0.4) and MD 0.8 (0.1-1.5).",              # 11
    "- Remission HR 1.84 (1.55-2.19) in the cohort; odds 0.50 (0.60-0.90).",           # 12
    "## References",                                                                   # 13
    "1. Smith A, Jones B. Title. J 2020;1:1. PMID 12345678.",                          # 14
    "2. Smith A. Other. J 2020;2:2.",                                                  # 15
    "8. Loften A, Wang Q. Spironolactone study. Psychopharmacology 2026. doi:10.1007/xyz.",  # 16
    "9. Unused C. Never cited. J 2019.",                                               # 17
    "10. World Health Organization. Report, 2021.",                                    # 18
]) + "\n"

TDOC = "\n".join([
    "## E. Tables",                                  # 1
    "| Study | SMD (95% CI) |",                      # 2
    "|---|---|",                                     # 3
    "| A | -0.20 (-0.40 to 0.00) |",                 # 4
    "| B | -0.20 (-0.40 to 0.10) |",                 # 5
    "- Pooled -0.20 (-0.40 to 0.10) overall.",       # 6
]) + "\n"


def brief(flags):
    return [(f.line, f.module, f.rule, f.evidence) for f in flags]


class Tuples(unittest.TestCase):
    def test_r1_twins_by_position(self):
        self.assertEqual(brief(m.r1(g.Doc(DOC))), [(12, "R1", "twin", (3,))])

    def test_r1_skips_rows_of_one_table(self):
        self.assertEqual(brief(m.r1(g.Doc(TDOC))), [(6, "R1", "twin", (4,))])

    def test_r1b_a(self):
        flags = m.r1b_a(g.Doc(DOC))
        self.assertEqual(brief(flags), [(12, "R1b", "a", ())])
        self.assertEqual(flags[0].span, "0.50 (0.60-0.90")


class SignConvention(unittest.TestCase):
    def test_section_without_convention(self):
        flags = m.r1b_b(g.Doc(DOC))
        self.assertEqual(brief(flags), [(7, "R1b", "b", (8, 9))])
        self.assertEqual(flags[0].data, {"negative_lines": [8], "positive_lines": [9]})

    def test_table_header_names_measure(self):
        self.assertEqual(brief(m.r1b_b(g.Doc(TDOC))), [(1, "R1b", "b", (4, 5))])


class References(unittest.TestCase):
    def test_parse_person(self):
        r = m.parse_reference("29", 1, "29. Pitt B, Zannad F, et al.; RALES Investigators. "
                              "N Engl J Med 1999;341(10):709-717. "
                              "doi:10.1056/NEJM199909023411001. PMID 10471456.")
        self.assertEqual((r.surname, r.initials, r.org), ("Pitt", "B", ""))
        self.assertEqual((r.years, r.pmids), (frozenset({"1999"}), frozenset({"10471456"})))
        self.assertEqual(r.dois, frozenset({"10.1056/nejm199909023411001"}))

    def test_parse_organisation(self):
        r = m.parse_reference("10", 1, "10. World Health Organization. Report, 2021.")
        self.assertEqual((r.surname, r.org, r.org_initials, r.years),
                         ("", "World Health Organization", "WHO", frozenset({"2021"})))
        r = m.parse_reference("3", 1, "3. *Munim, Inc.* evidence-pack, 2026-10-15 results.")
        self.assertEqual((r.org, r.years), ("Munim", frozenset()))

    def test_author_year_candidates(self):
        s = ("Zhang C 2022 and Georgescu & Wren 2018, PMID 1; May 2020; OARSI 2019; "
             "Osteoarthritis Initiative 2019; Jiang 2025's table; Loften et al. 2026 [8]; 2019-2021")
        self.assertEqual([c[2:] for c in m.author_year_candidates(s)],
                         [("Zhang", "C", "2022", False), ("Georgescu", "", "2018", False),
                          ("Jiang", "", "2025", False), ("Loften", "", "2026", True)])

    def test_r5(self):
        flags = m.r5(g.Doc(DOC))
        self.assertEqual(sorted((f.line, f.rule, f.span, f.evidence) for f in flags),
                         [(4, "acronym", "SAUD", ()),
                          (4, "author-year-ambiguous", "Smith 2020", (14, 15)),
                          (17, "never-cited", "[9]", ()),
                          (18, "never-cited", "[10]", ())])


class Labels(unittest.TestCase):
    def test_mask_quotes(self):
        self.assertEqual(m.mask_quotes('a "run 3" b'), 'a "     " b')

    def test_r6_a(self):
        self.assertEqual([(f.line, f.span) for f in m.r6_a(g.Doc(DOC))],
                         [(5, "run 3"), (5, "v19")])


class Check(unittest.TestCase):
    def test_check_doc(self):
        self.assertEqual([(f.line, f.module, f.rule) for f in m.check(g.Doc(DOC))],
                         [(4, "R5", "acronym"), (4, "R5", "author-year-ambiguous"),
                          (5, "R6", "a"), (5, "R6", "a"), (7, "R1b", "b"),
                          (12, "R1", "twin"), (12, "R1b", "a"),
                          (17, "R5", "never-cited"), (18, "R5", "never-cited")])
        self.assertEqual(m.check(g.Doc(TDOC))[0].as_dict()["evidence"], [4, 5])


if __name__ == "__main__":
    unittest.main()
