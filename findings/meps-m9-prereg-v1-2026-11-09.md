# Census M9 pre-registration: repeated sentences with one number changed, and count-percent pairs with an impossible base, in AHRQ MEPS Statistical Briefs

MV2 of Munim, Inc. (mv2@munimtech.com). Made by AI agents (Claude) working in MV2's name. Written and committed
before any page was fetched for M9 (2026-11-09). Code: `meps/m9echo.py` 0.1.0 with offline tests in
`meps/test_m9echo.py` (Apache-2.0). Text CC BY 4.0. Research information about published statistics; not medical
advice. AHRQ has not been contacted.

## Why

Census M8 compared each number in a brief's text with the figure the text cites. Reading all 134 of its flags by
hand (audit A8, `findings/meps-m8-flag-audit-results-v1-2026-11-09.md`) found slips that M8 cannot see. The
clearest: Brief #450 (2014) prints in its Findings "In 2012, 67.2 percent of the population (22.5 million
individuals) had out-of-pocket expenditures for medical care that were equal to or greater than $2,000." Its
Highlights print the same sentence, word for word, with 7.2 percent, and so does Figure 2. 22.5 million people is
about 7 percent of the U.S. population, not 67 percent. Two cheap checks would have caught it:

1. **Echo:** the same sentence appears twice in one brief with one number different.
2. **Impossible base:** a percent and a head count printed as a pair imply a population size (N / P x 100) that
   cannot be right.

## Prior art (searched 2026-11-09)

- numcheck (github.com/ailanasirai/numcheck) checks whether each number in a paper's abstract appears somewhere in
  its body. It does not match a repeated sentence to its twin, and does not check count-percent arithmetic.
- The GRIM test (Brown and Heathers, 2017) checks whether a mean is possible for an integer sample size; statcheck
  recomputes p-values from test statistics. The base check here is the same idea (is the printed pair arithmetically
  possible at its printed rounding?) applied to "P percent (N million)" pairs.
- Studies of abstract-body inconsistency in journals (for example Pitkin et al., JAMA 1999) read papers by hand.
- We found no whole-series check of either kind on a federal statistical report series, and no published errata
  for these MEPS briefs beyond what our own errata table lists (`skills/meps-statbrief-errata`, table 0.3.0).

## Data

Every brief listed in `findings/meps-brief-tables-v1/tables.csv` (540 briefs, the list used by census M8 v0.2).
Pages: `https://meps.ahrq.gov/data_files/publications/st<N>/stat<N>.shtml`, fetched once each with a 3-second pause,
robots.txt checked in code before every fetch, SHA-256 of every page recorded. No data file is downloaded.

## Method (fixed in code before any fetch)

Text is read everywhere on the page, inside and outside tables (each table cell is its own block), except from a
heading Definitions, Data source(s), About MEPS(-HC), References or Suggested citation until the next h1-h6 heading
with another name (the M8 v0.2 stop rule). Blocks are split into sentences at `.`, `!` or `?` followed by space and
a capital, digit, quote or parenthesis.

**Echo detector.** A sentence's skeleton is its lower-case words with every number replaced by `#`, figure, table and
exhibit references removed, and `%` read as "percent". Two sentences in *different* blocks of one brief are an echo
flag if their skeletons are identical, at least 8 tokens long, exactly one of their numbers differs in value, and
both differing numbers have a decimal point (so years, dollar thresholds and other integers never flag). Each flag
records the kind of edit between the two digit strings: substitution, swap of two adjacent digits, extra digit,
moved decimal point, or other.

**Pair detector.** Two forms are read in one block: "P percent [up to 80 characters with no parenthesis, 'percent',
'million' or '%'] (N million" and "N million [same gap] (P percent ...)". An optional "about", "approximately",
"nearly", "roughly", "almost" or "an estimated" may open the parenthesis; "more than", "less than" and dollar
amounts never form a pair. A pair whose gap crosses a sentence end is skipped and counted. With N and P read at
their printed rounding (half a unit in the last printed digit), the base B = N / P x 100 million lies in an
interval [lo, hi]. Flags:
- **over:** lo > 345 million (more people than the United States has had in any MEPS year);
- **population:** the percent is stated "of the population" (optionally "of the U.S./civilian/noninstitutionalized/
  total/overall/entire/whole population", optionally "in YYYY", and nothing else) and [lo, hi] misses 250 to 345
  million.
For each flagged pair the code lists every one-digit edit of P and of N (substitute, delete or insert a digit, swap
two adjacent digits) that would clear every flag. These are hints for the reader, not verdicts.

**Controls.** Positive: Brief #450 must give a population flag for 67.2 / 22.5 with 7.2 among the percent repairs,
and an echo flag pairing 7.2 with 67.2. Negative: #450's "4.8 million individuals (1.5 percent)" must be read as a
pair and not flagged. Scope control: #181's Introduction says "approximately 61.1 million were enrolled" and its
Findings say "Among the 61.6 million private sector employees enrolled"; these are paraphrases, not echoes, so M9
is expected NOT to flag them. Controls are excluded from every count below.

**Gate.** At least 530 of the 540 pages fetched, and all four positive and negative control checks pass. If the gate
fails, M9 is reported as a failed run and no flag is graded.

**Hand check.** Flags are ordered by SHA-256 of `m9|kind|brief|block|a|b`. The first 40 non-control flags in that
order are read by hand, all of them if there are fewer. Each is read twice (two WebFetch reads with different
prompts) against the brief page and graded:
- **CONFLICT:** the brief prints two different numbers for one statement, or a pair that cannot be true as printed.
  Where the brief's own figure, table or arithmetic shows which number is right, say so.
- **INTENDED:** the two sentences really describe different things (for example the context outside the sentence
  names a different group or year), or the pair's base is right for what it describes.
- **SCOPE:** a population flag where "the population" means a subpopulation the brief defined earlier, whose size
  the base fits.
- **ARTEFACT:** a reading error (a wrong sentence split, a wrong pairing, a number that is not a count of people).
A CONFLICT already in errata table 0.3.0 is graded KNOWN-CONFLICT: it counts as a conflict for P6 but not as new
for P7.

## Predictions

- **P1 (gate):** the gate passes.
- **P2 (scope):** #181's 61.1 / 61.6 is not flagged.
- **P3:** the pair detector reads at least 150 count-percent pairs across the series.
- **P4:** at most 10 non-control pair flags.
- **P5:** between 1 and 40 non-control echo flags.
- **P6:** at least half of the hand-read echo flags are CONFLICT or KNOWN-CONFLICT (an identical sentence with one
  number changed should rarely be intended). Not gradable if P5 fails low.
- **P7:** at least one new CONFLICT (not in errata table 0.3.0) across both detectors.

## Outputs

`m9-summary.json` (counts, controls, gate, page hashes), `m9-pairs.csv` (every pair read, with its base interval),
`m9-flags.csv` (every flag with its check rank). Results will be published as
`findings/meps-m9-results-v1-<date>.md`. Corrections to this plan only by dated addendum.

## Limits known in advance

Paraphrased repeats (like #181) are out of scope. Integer slips are out of scope for the echo detector. The pair
detector needs the count in millions printed in a parenthesis next to the percent. A population flag can be a scope
artefact. A flag is a lead for a reader to check, not an error report, until a person has checked it.
