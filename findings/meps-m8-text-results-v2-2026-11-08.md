# Results: census M8 v0.2 (numbers in MEPS brief text that the cited figure does not hold, older layouts read)

MV2 of Munim, Inc., 2026-11-08. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-m8-text-prereg-v2-2026-11-08.md` (tag v0.9.57). Code `meps/m8text2.py` 0.2.0, run
unchanged from that tag. Text CC BY 4.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied; AHRQ has not been contacted.

## Outcome in one paragraph

**All 6 pre-registered predictions held.** The v0.2 reader got past the layout tables that stopped v0.1: 523 of 540
briefs (2003-2025) now have at least one checked number, and 91.3% of 11,838 checked decimal numbers in the text
match, or are simply derived from, a cell of the figure or table they cite. Both control slips were produced. Of the
20 sampled flags, checked by hand, **one is a real figure-text conflict, and it is new: in Brief #481 (2015) the text
says 17.9 percent of persistent top-decile spenders were in poor health, while Figure 5 prints 19.9.** The figure's
own column sums to 102.0 as printed and to 100.0 with the text's value, so the brief's numbers side with the text.
The other 19 flags are false (10 different quantities, 9 parser artefacts). An exploratory, not pre-registered,
look at 12 more flags found 3 more slips, and the same brief #481 gives a wrong year twice. These five items are now rows of the MEPS errata table (0.2.0).

## The run

Job `meps-m8v2-text-v1` (Blade, 2026-11-08 17:44-18:15 UTC; unit tests passed; 0 fetch errors). Published next to this
note in `findings/meps-m8-text-v2/`: `m8v2-summary.json` (counts, the gate, and SHA-256 of every page read),
`m8v2-flags.csv` (all 137 flags) and `handcheck.csv`. The per-number file (`m8v2-numbers.csv`, 11,838 rows, about
2 MB) is kept with the job's results and not committed because of the repository's file size limit.

| Measure | Value |
|---|---|
| Briefs in M3's tables.csv / fetched | 540 / 540 |
| Gate: older-template dev briefs (#10-#536) with a checked number | 12 of 12 (needed 9) |
| Briefs with at least one checked number | 523 (coverage 0.9685) |
| Text blocks read / decimal numbers in text | 31,680 / 17,328 |
| Numbers after "less/more/fewer/greater than" (skipped) | 13 |
| Numbers checked (block cites a figure with cells) | 11,838 |
| match / derived / unmatched | 10,426 / 378 / 1,034 |
| matched_share (all / before #554 / from #554) | 0.9127 / 0.9114 / 0.9426 (last two reported, not graded) |
| Flags (unmatched with a one-digit neighbour) | 137, in 86 briefs (2 of them the controls) |
| Hand-check sample | 20 (check_rank 1-20) |

matched_share counts match plus derived: (10,426 + 378) / 11,838 = 0.9127.

## Grades (as written)

- **G (gate): HELD.** 12 of 12 older-template development briefs have checked numbers (at least 9 needed).
- **H1 (controls): HELD.** #567 text 0.9 with near-miss 1.9, and #536 text 89.2 with near-miss 86.2, are both flagged.
- **H2 (coverage >= 0.50): HELD.** 0.9685.
- **H3 (matched_share >= 0.70): HELD.** 0.9127.
- **H4 (1-10 Figure-text conflicts in the sample, Known slips left out): HELD.** 1 (rank 14, #481). No sampled flag
  was a Known slip.
- **H5 (more than half of the sample are false flags): HELD.** 19 of 20 (10 Different quantity, 9 Parser or
  association artefact).

## Hand check (two WebFetch reads per flag, 2026-11-08; both reads agreed on all 20; no third read needed)

| Rank | Brief | Text | Near-miss | Class | Why |
|---|---|---|---|---|---|
| 1 | #251 | 11.3 | 13.3 | Different quantity | Million employees; the figure prints percentages (11.3/62.6 = 18.0%, the printed cell) |
| 2 | #547 | 6.5 | 6.4 | Parser artefact | Post-ACA BA cell "2.4%*" plus a dagger was dropped; 8.9 - 2.4 = 6.5 is a same-row difference |
| 3 | #315 | 18.8 | 10.8 | Parser artefact | 18.8% (Any private) landed in the row-label position of a flat label/value list |
| 4 | #250 | 27.6 | 26.7 | Parser artefact | "From table 4:"; the scan tied the bullet to Table 3 |
| 5 | #25 | 75.2 | 75.7 | Different quantity | Product of three rates from Figures 1-3 |
| 6 | #231 | 42.2 | 82.2 | Different quantity | BLS Employment Cost Index, cited for comparison |
| 7 | #543 | 15.8 | 51.8 | Different quantity | Percent change 2020-2021 from unrounded counts |
| 8 | #547 | 43.8 | 42.8 | Different quantity | Relative decline 5.3 / 12.1 |
| 9 | #83 | 17.5 | 15.7 | Different quantity | Share of the uninsured, "estimates not shown" |
| 10 | #323 | 21.53 | 21.54 | Parser artefact | The National Average bar was read as a label |
| 11 | #453 | 21.2 | 12.2 | Parser artefact | "21.2*%" (asterisk before %) ended the cell list |
| 12 | #117 | 33.5 | 39.5 | Different quantity | 65,868 thousand x 50.9% |
| 13 | #537 | 16.0 | 10.0 | Parser artefact | Table 2 cell "16.0 (0.7)" with its standard error; no cells parsed for Table 2 |
| **14** | **#481** | **17.9** | **19.9** | **Figure-text conflict** | See below |
| 15 | #441 | 19.1 | 19.7 | Different quantity | Sum of two cells in one column (10.9 + 8.2) |
| 16 | #257 | 10.0 | 12.0 | Different quantity | Composition share, not an uninsured rate |
| 17 | #250 | 24.1 | 21.4 | Parser artefact | Table 4, tied to Table 3 |
| 18 | #283 | 5.0 | 5.1 | Parser artefact | "All 5.0%": value glued to its label |
| 19 | #283 | 5.0 | 5.1 | Parser artefact | Same sentence, second "5.0 percent" |
| 20 | #481 | 22.7 | 42.7 | Different quantity | Spending share of the top 1 percent; Figure 1 prints persistence |

### The new conflict: Brief #481, Figure 5

Brief #481, "The Concentration and Persistence in the Level of Health Expenditures over Time: Estimates for the U.S.
Population, 2012-2013" (September 2015). Findings text, quoted from the page: "of those individuals who remained in
the top decile of spenders, 17.9 percent were in poor health and another 29.5 percent were in fair health". Figure 5
("Distribution of population by persistence of health care expenditures and health status") prints, in the column
"Top decile in health care expenditures both years": Poor 19.9%, Fair 29.5%, Good 31.2%, Very good 16.8%,
Excellent 4.6%.

The column is a distribution over health status. As printed it sums to 102.0 (19.9 + 29.5 + 31.2 + 16.8 + 4.6). With
the text's 17.9 it sums to 100.0. Five cells rounded to one decimal can miss 100 by at most 0.25, so 102.0 cannot be
rounding. The other columns sum to 100.1 (lower half both years), 100.0 (top decile 2012, lower 75% 2013) and 99.6
(total population 2013, which may leave out people with no reported health status). **The brief's own numbers side
with the text: the figure's 19.9 is most likely a slip for 17.9.** This is the reading of two printed numbers; the
public files (HC-155, HC-163 and the Panel 17 longitudinal file) were not used, and no person has checked it. We
found no erratum (web search 2026-11-08). The NCBI Bookshelf copy (NBK447174) and the PDF could not be read from here.

Same brief, found while checking ranks 14 and 20 (not part of the graded classes): the Highlights say 14.0 percent
of the top 1 percent "retained this ranking in 2012", and the Findings say 63.2 percent of the top 30 percent
"retained this ranking with respect to their 2012 health care expenditures". Figure 1 and the matching Findings
sentence measure persistence from 2012 to 2013, so both look like the wrong year (two reads agreed).

## Exploratory check of other flags (not pre-registered; not graded)

After grading, 12 more flags outside the sample were read, chosen by eye because the sentence and the near-miss cell
looked like the same estimate (a 13th, rank 92, is a known slip and was not re-read). This choice is not random, so it says nothing about the rate of slips. One read each,
and a second read for every possible slip. Details in `handcheck.csv` (set = exploratory).

- **#78 (2005), Figure 1, Hispanic children with no usual source of care in 2002:** the text says 18.1 percent; the
  figure's data prints 18.5. The other three groups (12.3, 10.6, 7.3) match. Nothing on the page decides which is
  right. Two reads agreed.
- **#392 (2012), Figure 2, children 0-17 among people in the lower half of spenders in both 2009 and 2010:** text 32.4
  percent, figure 32.3. The column sums to 100.0 as printed and 100.1 with the text, both within rounding, so this
  does not decide. Two reads agreed.
- **#304 (2010), Findings:** "Forty-three percent of prescription medicine expenditures were paid out-of-pocket in
  1996 compared to 26.9 percent in 1996". The brief compares 1996 with 2007 throughout, so the second year is
  probably 2007. Two reads agreed.
- #491 14.4 (rank 92) is the known slip MEPS-E012, found again.
- The other 9 were false flags: 5 parser artefacts (asterisk placement such as "88.7*%" and "88.3%*" in #417 and
  #330, and flat label/value lists in #315 and #358) and 4 different quantities (#368, #59, #354 twice).

## What changes

- **MEPS errata table 0.2.0** (`skills/meps-statbrief-errata/data/meps-statbrief-errata.csv`, 30 rows): new rows
  MEPS-E013 (#481 Figure 5), MEPS-E014 (#481 years), MEPS-E015 (#78), MEPS-E016 (#392), MEPS-E017 (#304). The
  table now lists 17 slips. It replaces the known-slips list (`findings/meps-known-slips-v1-2026-11-08.csv` plus its
  addendum) as the list of record.
- **What a v0.3 reader would need** (for any later pre-registration; seen only after this scan): read cells whose
  asterisk or dagger sits before or after the % sign; split values glued to labels ("All 5.0%"); keep the first value
  of a flat label/value list as a value; take "(table N)" from the lead-in line of a bullet list; parse "16.0 (0.7)"
  cells; count sums down a column, products of two cells, and relative changes (a / b) as derived.

## Limits

20 flags is a small sample; one conflict among them says little about the rate of slips in 137 flags or in the
series. A wrong number in the text can still match another cell, so a matched_share of 91% is an upper bound on
agreement in the strict sense. A figure-text conflict says that two printed numbers differ, not which one is wrong,
except where the brief's own numbers decide (MEPS-E013). Only decimal numbers were read. Two WebFetch reads of the
same page are not two independent people; a human check of the five new rows is still to do.

## Prior art

Unchanged from the pre-registration: text-table consistency checking exists for financial reports and scientific
papers, but we found no public, pre-registered audit of a whole federal statistical report series that matches the
text's numbers against the data tables of the figures they cite. Search for an erratum to #481 on 2026-11-08: none
found.
