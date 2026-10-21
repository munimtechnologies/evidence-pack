"""Unit tests for claimcheck.grammar, on synthetic strings only (plan v7 section 8 step 3).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import unittest

from claimcheck import grammar as g

M = g.MINUS

DOC = "\n".join([
    "# Title",                                              # 1
    "## E. Evidence",                                       # 2
    "### E.3 Cohort (Loften et al. 2026 [8])",              # 3
    "",                                                     # 4
    "| Comparator | Remission HR (95% CI) |",               # 5
    "|---|---|",                                            # 6
    "| ACE | 1.84 (1.55-2.18) |",                            # 7
    "| ARB | 2.07 (1.73-2.48) |",                            # 8
    "",                                                     # 9
    "- **Benefit:** 1.84-2.07 times as likely [6-8].",      # 10
    "- Unrelated [5].",                                     # 11
    "## References",                                        # 12
    "5. Smith A. Title. 2020.",                             # 13
    "8. Loften B. Title. 2026.",                            # 14
    "---",                                                  # 15
    "Submitter notes (internal)",                           # 16
    "| a | b |",                                            # 17
]) + "\n"


class LinesAndCut(unittest.TestCase):
    def test_read_lines_like_bytes(self):
        self.assertEqual(g.read_lines("a\r\nb\rc\n"), ["a", "b", "c"])
        self.assertEqual(g.read_lines(""), [])

    def test_cut_rule(self):
        self.assertEqual(g.cut_count(["# T", "text", "---", "", "Submitter notes (x)", "y"]), 2)
        self.assertEqual(g.cut_count(["# T", "text", "## Notes for the submitter (x)", "y"]), 2)
        self.assertEqual(g.cut_count(["a", "b"]), 2)

    def test_strip_emphasis(self):
        self.assertEqual(g.strip_emphasis("**Rats** (_a_ b) rwe_recheck"), "Rats (a b) rwe_recheck")


class Names(unittest.TestCase):
    def test_find_word(self):
        s = "pre-registered; registered. ClinicalTrials.gov and ClinicalTrials.gov's x.registered"
        self.assertEqual(len(g.find_word(s, "registered")), 1)
        self.assertEqual(len(g.find_word(s, "ClinicalTrials.gov")), 2)

    def test_registry_ids(self):
        s = "NCT06004830, NCT050340291 and ISRCTN123; CTIS 2023-503-12-00"
        self.assertEqual([x[2] for x in g.registry_ids(s)],
                         ["NCT06004830", "ISRCTN123", "CTIS 2023-503-12-00"])

    def test_registry_names_not_in_ids_or_urls(self):
        s = "ChiCTR2500107918 at chictr.org.cn; ChiCTR lists it; see https://x.org/ChiCTR and WHO ICTRP"
        self.assertEqual([n for _, n in g.registry_names(s)], ["ChiCTR", "WHO", "ICTRP"])


class SentencesAndClauses(unittest.TestCase):
    def test_sentences(self):
        raw = ('One trial (see Smith et al. (2020). More) ended. **Two** began. '
               '(Three) "Quoted. Text" stays. e.g. lower')
        self.assertEqual([p for _, p in g.split_sentences(raw)],
                         ['One trial (see Smith et al. (2020). More) ended.', '**Two** began.',
                          '(Three) "Quoted. Text" stays. e.g. lower'])

    def test_clause(self):
        s = "Searched (11 records; ChiCTR one (a; b)); then 2 trials"
        a, b = g.clause_span(s, s.index("11"))
        self.assertEqual(s[a:b], "11 records")
        a, b = g.clause_span(s, s.index("ChiCTR"))
        self.assertEqual(s[a:b], " ChiCTR one (a; b)")
        a, b = g.clause_span(s, s.index("2 trials"))
        self.assertEqual(s[a:b], " then 2 trials")

    def test_count_phrases(self):
        s = ("Two other placebo-controlled trials; 11 ClinicalTrials.gov records; 3.5 trials; "
             "12 of the very many studies x")
        self.assertEqual([v for _, _, v in g.count_phrases(s, g1=True)], [2, 11])


class Numbers(unittest.TestCase):
    def test_g1_tokens(self):
        s = ("1.24-2.07 and 8.0-10.4% vs -0.43, " + M + "2.6; COVID-19, 12-week, 3/37, v19, E.3e, "
             "2026-10-20, [6-8], 95% CI, 3,537, .07, $5, 10:30, 7" + chr(0x3B1) + "-TMS")
        self.assertEqual([n.text for n in g.numbers(s)],
                         ["1.24", "2.07", "8.0", "10.4%", "-0.43", M + "2.6", "3,537", ".07", "$5"])

    def test_g1_values(self):
        ns = g.numbers("x -0.43 and 3,537 and 10.4%")
        self.assertEqual([n.value for n in ns], [-0.43, 3537.0, 10.4])
        self.assertEqual([n.pct for n in ns], [False, False, True])
        self.assertEqual([n.decimals for n in ns], [2, 0, 1])


class Tuples(unittest.TestCase):
    def test_g4(self):
        s = "HR 1.84 (1.55-2.18) and SMD " + M + "11.4 mm (95% CI " + M + "20.1 to " + M + "2.6)"
        self.assertEqual([(t.est.value, t.lo.value, t.hi.value, t.form) for t in g.ci_tuples(s)],
                         [(1.84, 1.55, 2.18, "G4"), (-11.4, -20.1, -2.6, "G4")])
        self.assertEqual(len(g.ci_tuples("MD 4.2 (1.1 to 7.3 points) x")), 1)

    def test_g5_and_non_tuples(self):
        s = ("(SMD 0.43, 95% CI 0.02-0.83) (TriNetX [8]; 8.0-10.4% vs 4.4-7.4%) "
             "(HR 0.77-0.81; 0.97 vs ARBs) 368 (10.4%)")
        self.assertEqual([(t.est.value, t.lo.value, t.hi.value, t.form) for t in g.ci_tuples(s)],
                         [(0.43, 0.02, 0.83, "G5")])

    def test_g3_limits(self):
        self.assertEqual(g.ci_tuples("0.80 one two three four five six seven (0.70-0.90)"), [])
        self.assertEqual(len(g.ci_tuples("0.80 one two three four five six (0.70-0.90)")), 1)
        self.assertEqual(g.ci_tuples("0.80; then (0.70-0.90)"), [])


class Citations(unittest.TestCase):
    def test_cite_keys(self):
        self.assertEqual(g.cite_keys("a [6-8] b [5, 21] c [36a] d [x]"),
                         ["6", "7", "8", "5", "21", "36a"])
        self.assertEqual(g.cite_keys("[2" + g.NDASH + "4]"), ["2", "3", "4"])


class Document(unittest.TestCase):
    def setUp(self):
        self.d = g.Doc(DOC)

    def test_cut_and_kinds(self):
        d = self.d
        self.assertEqual((d.total_lines, d.cut, len(d.lines)), (17, 14, 14))
        self.assertEqual([d.line(n).kind for n in (1, 5, 6, 7, 10, 13)],
                         ["heading", "table_header", "table_sep", "table_row", "bullet", "ref"])
        self.assertEqual((d.line(10).h2, d.line(10).h3, d.line(13).h2, d.line(13).h3), (2, 3, 12, 0))
        self.assertEqual(d.line(10).lead, "Benefit:")
        self.assertEqual(d.references(), [("5", 13), ("8", 14)])

    def test_table(self):
        t = self.d.tables[0]
        self.assertEqual(len(self.d.tables), 1)
        self.assertEqual(t.header, ["Comparator", "Remission HR (95% CI)"])
        self.assertEqual([n for n, _ in t.rows], [7, 8])
        self.assertEqual((t.heading_line, t.cites), (3, frozenset({"8"})))
        self.assertEqual(g.ci_tuples(t.rows[0][1][1])[0].est.value, 1.84)

    def test_linking_and_sentences(self):
        d = self.d
        self.assertEqual((d.linked_tables(10), d.linked_tables(11), d.linked_tables(7)), ([0], [], []))
        self.assertEqual([s.text for s in d.sentences(10)],
                         ["Benefit: 1.84-2.07 times as likely [6-8]."])
        self.assertEqual(d.sentences(5), [])


if __name__ == "__main__":
    unittest.main()
