# Pre-registration: census M8. Does the text of a MEPS Statistical Brief print a number that its cited figure does not hold? (v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the scan runs. Text CC BY 4.0; code `meps/m8text.py` 0.1.0 (Apache-2.0) with offline tests
(`meps/test_m8text.py`). Research information about published statistics, not medical advice. No endorsement by
AHRQ is implied; AHRQ has not been contacted.

## Why

Census M7 (`findings/meps-m7-totals-results-v1-2026-11-07.md`) found two figures whose Total lies outside its own
groups' range. In both, the brief's own text printed the right-looking number and the figure a number one digit away:
#567 Figure 1 prints men's combined benzodiazepine-opioid use as 1.9 where the text says 0.9; #536 Figure 13 prints
the 2020 U.S. deductible share as 86.2% where the text says 89.2 percent. M7 can only see such a slip when it pushes a
Total out of range. M8 looks for the slip itself: a number in the text, next to a citation of a figure, that the
figure does not hold although it holds a number one digit away.

## What was seen before this was written (disclosed)

- The two M7 cases above (hand-checked, two reads each) and their pages: #567 cites Figure 1 only in the subheading
  "Overall and sex (Figure 1)"; #536's paragraph ends its first sentence with "(figure 13)". Figure 13's full table
  was read (no cell is 89.2).
- M3 data (`findings/meps-brief-tables-v1/`) as used by M4, M5 and M7. No brief text has been scanned.
- Hand checks of M4, M5 and M7 (about 50 brief pages) read text near flagged figures; none was a text-figure number
  conflict apart from the two above and the #497 swap (R2b), which M8 cannot catch (both numbers are in the figure).

## Method (machine scan; `meps/m8text.py` 0.1.0)

1. **Pages.** Every brief in M3's `tables.csv` is fetched once from `meps.ahrq.gov/data_files/publications/`
   (robots.txt checked in code; 3 s between requests; one retry). Tables are read with M3's parser
   (`meps/brief_tables.py`); the SHA-256 of each page is recorded.
2. **Text blocks.** Paragraphs, list items, headings and divisions outside tables, in page order. A block is
   heading-like if it is a heading tag, or has at most 15 words and no number with a decimal point.
3. **Citations.** A block cites the figures, tables or exhibits it names ("(figure 13)", "(figures 11 and 12)",
   "(figures 6-9)", "Table 2"); if it names none, those named in the nearest heading-like block above it (a
   heading-like block that names none clears this).
4. **Numbers.** Every number with a decimal point in a block that cites a figure with cells (integers are not read).
   Verdicts, with tolerance half a unit in the text number's last digit:
   - `match`: a cell of the cited figures equals it;
   - `derived`: 100 minus a cell, or the difference of two cells in one row or one column of one table, equals it;
   - `unmatched`: otherwise.
5. **Flags.** An unmatched number is flagged when a cell of the cited figures, printed at the text's decimals, has
   the same number of digits and differs in exactly one digit or by one swap of two adjacent digits, and that cell's
   value is not itself printed in the block.
6. **Hand-check sample.** Flags are ordered by SHA-256 of `m8|<brief>|<block>|<number as printed>`. The two control
   flags are set aside; the first 30 others in that order (`check_rank` 1-30, `in_sample`) are hand-checked.
7. **Hand check.** Two separate WebFetch reads of the brief page copy the sentence holding the number, the cited
   figure's title and the near-miss cell with its row and column labels, and say what group, year and measure the
   sentence's number is about. Classes:
   - **Figure-text conflict:** the sentence's number and the near-miss cell are, by the page's own words, the same
     estimate (same measure, population, group and year), they differ, and nothing on the page explains it;
   - **Different quantity:** the sentence's number is about something the near-miss cell is not (another figure or
     table, group, year or measure; a ratio, percent change, sum or other derived number);
   - **Parser or association artefact:** the scan tied the number to the wrong figure, or misread the page.
   Only classes both reads agree on count; a disagreement gets a third read, which decides (2 of 3), and is logged.

## Predictions (graded exactly as written)

- **H1 (controls):** both control flags are produced: #567 text 0.9 with near-miss cell 1.9, and #536 text 89.2 with
  near-miss cell 86.2 (`controls` both true).
- **H2 (coverage):** at least 40% of fetched briefs have at least one checked number
  (`briefs_with_checked_numbers / fetched`).
- **H3 (agreement):** at least 60% of checked numbers are `match` or `derived` (`matched_share` >= 0.60).
- **H4 (primary):** between 1 and 10 (inclusive) of the hand-checked sample are classed Figure-text conflict.
- **H5 (false flags):** more than half of the hand-checked sample are classed Different quantity or Parser or
  association artefact.

If fewer than 30 non-control flags exist, all are hand-checked and H4/H5 are graded on them.

## Limits

Only numbers with a decimal point; integers, dollar amounts without decimals and numbers in words are not read.
Only figures and tables with an accessible data table (M3). A text number can be wrong and still match some other cell
(missed); a one-digit neighbour can exist by chance in a large figure (false flag; the hand check sorts these). The
heading rule can tie a paragraph to the wrong figure. Highlights and summaries that cite no figure are not checked. A
Figure-text conflict says that one of two printed numbers is wrong, not which, and says nothing about the data files.

## Prior art and what is new

Checking text against tables is not a new idea. The UK Government Analysis Function's "Quality statistics in
government" guidance asks producers to "cross check figures in publication against tables"; research tools check
table-text consistency in financial reports (e.g. Ping Luo's group's numerical cross-checking work; "Automatic
Consistency Checking of Table and Text in Financial Documents") and scientific papers (sciwrite-lint, arXiv
2604.08501; PRISMM-Bench, arXiv 2510.16505, finds figure-text mismatches the most common inconsistency in peer
review); statcheck recomputes test statistics in papers. What we did not find (searches 2026-11-02 to 11-07,
inconclusive as any search) is a public, pre-registered audit of a whole federal statistical report series that
matches the text's numbers against the data tables of the figures they cite, with every flag in the sample checked by
hand. M8 is a simple rule-based check, not a learned model.
