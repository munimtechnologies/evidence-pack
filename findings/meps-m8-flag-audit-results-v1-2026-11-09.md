# Results: hand audit of every remaining M8 v0.2 flag (A8)

MV2 of Munim, Inc., 2026-11-09. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0. Research information about published statistics, not medical advice. No endorsement by AHRQ is
implied; AHRQ has not been contacted. Pre-registration: `findings/meps-m8-flag-audit-prereg-v1-2026-11-08.md`
(tag v0.9.59), fixed before any flag in the frame was read.

## In one paragraph

Census M8 v0.2 flagged 134 numbers in the text of AHRQ's MEPS Statistical Briefs that differ by one digit from a
cell of the figure or table the text cites. Before this audit, 33 of them had been read (a graded sample of 20 and
13 picked by eye). This audit read the other 101, every one, in the pre-registered order. **Three are real
figure-text conflicts** (Briefs #192, #481 and #434), **75 compare different quantities** (mostly counts in millions
set beside percentage cells, percent changes, ratios and products that the figures do not print) and **23 are
parser or association artefacts** (the text's number is printed, but the scan missed the cell or tied the sentence
to the wrong figure). P1 and P2 held; **P3 failed** (22.8% artefacts against a prediction of at least 30%). With
the earlier reads, all 134 ranked M8 flags have now been read by hand. While reading, we also found eight slips
that the scan was not built to catch; each was confirmed by a second read and is reported below as exploratory.
All 11 are added to MV2's MEPS errata table (0.3.0, 41 rows).

## Grades (exactly as pre-registered)

| Prediction | Result | Grade |
|---|---|---|
| P1 (primary): between 1 and 10 (inclusive) of the 101 are Figure-text conflicts | 3 | **HELD** |
| P2: more than 70% are Different quantity or Parser or association artefact | 98 of 101 = 97.0% | **HELD** |
| P3: at least 30% are Parser or association artefact | 23 of 101 = 22.8% | **FAILED** |

No flag in the frame matched a row of the errata table 0.2.0 (the known-slip class was empty). All three conflicts
were confirmed by a second read with a different prompt (2 of 2 each); no third read was needed. The other 98
flags had one read each, as the pre-registration allows.

Why P3 failed: we expected the parser problems seen in the sample (9 of 20) to recur. They did recur, but they
cluster in a few briefs (#250 alone gives 8 of the 23, all from bullets that sit under "From table 4:" and were
tied to Table 3). The tail of the ranking is dominated instead by counts in millions printed next to a percentage
the figure does show (for example "12.4 percent ... 12.2 million persons"), which M8 cannot tell apart from a cell.

Two classifications go beyond what the single read said. For ranks 116 (#93) and 117 (#264), the read compared the
text with the figure the scan used and said Different quantity, but it also reported that the same number is
printed, for the same quantity, in another figure of the brief (Figure 2 and Figure 3). By the class definitions
these are association artefacts, and we count them so. With both counted as Different quantity instead, P3 fails
by more (21 of 101) and P1 and P2 do not change.

## The three conflicts

| Rank | Brief (data year) | Place | Text | Figure/table | Do the brief's own numbers decide? |
|---|---|---|---|---|---|
| 40 | #192 (2005) | Table 3, United States, out-of-pocket share of expenses | "about one-fifth (19.0 percent)" | 18.6 (bold) | No: the table's sources of payment do not total 100 by design |
| 70 | #481 (2012-2013) | Figure 7, high-income share of people in the lower half of spenders both years | 27.3 percent | 27.36% (its only two-decimal cell; rounds to 27.4) | No: the column sums to 100.16 as printed, 100.1 with 27.3 |
| 88 | #434 (2011) | Figure 5, prescription share of children's mental disorder spending | "About 41.5 percent" | 41.4% | No: the column sums to 100.0 as printed, 100.1 with 41.5 (within rounding) |

For #192 the offline cells parsed in census M3 (`compete-results/meps-brief-tables-v1`) also hold 18.6 in the United
States row. A conflict says that two printed numbers differ, not which one is wrong. #481 is the brief whose
Figure 5 conflict was found in the M8 v0.2 sample (MEPS-E013), so it now carries two figure-text conflicts.

## Exploratory finds (not part of the graded frame)

Found while reading flags; each was then confirmed by a second, targeted read. They are leads, not a rate:
nobody searched the series for this kind of slip.

| Row | Brief | Place | What the page prints |
|---|---|---|---|
| MEPS-E021 | #450 (2012) | Findings | "67.2 percent of the population (22.5 million individuals)" had out-of-pocket spending of $2,000 or more; the Highlights and Figure 2 say 7.2 percent, and 22.5 million fits 7.2 percent |
| MEPS-E022 | #481 | Figure 7 | The row-header column is labelled "Health status", but the rows are poverty categories |
| MEPS-E023 | #481 | Findings | 36.5 percent with high incomes "in 2012 (figure 7)"; Figure 7's column is "Total population 2013" and poverty status uses 2013 income |
| MEPS-E024 | #192 | Table 3 | Florida's Medicare share is printed "26." with no decimal digit (every other cell has one) |
| MEPS-E025 | #181 (2005) | Introduction vs Findings | Enrollees: "approximately 61.1 million" vs "61.6 million"; same population and year |
| MEPS-E026 | #99 (1996) | Figure 2 | All families with an insured child, 1996: 83.6%; Figure 1 and the text give 83.7 |
| MEPS-E027 | #99 | Figure 2 | Rows labelled "Federal policy level" instead of Federal poverty level |
| MEPS-E028 | #430 | Figure 2 | Percentages labelled "(persons in millions)", the row labels of Figure 1 |

E021 is the clearest single slip found so far in the series: the brief's own Highlights, figure and population
count all side with 7.2. M8 could not have flagged it, because 67.2 and 7.2 have different numbers of digits; a
next scan should treat an inserted or dropped digit as a near miss.

## What this says about M8

Across all 134 ranked flags, 6 are new figure-text conflicts (1 in the sample, 2 in the exploratory set, 3 here)
and 1 is a slip already known from check R2 (#491). That is 7 conflicts, about 1 per 19 flags; a reader of M8's
output still has to read every flag by hand. M8 is a floor on this kind of slip: it only sees decimal numbers, only
blocks that cite a figure with parsed cells, and only one-digit near misses. Parser lessons for any v0.3, in
addition to those in the v2 results note: pair "N million (P percent)" so that the count is not compared with
percentage cells; recognise percent changes, ratios and products stated next to their inputs; read the US or
National Average column/bar as a cell; follow "From table N:" lead-ins; allow an inserted or dropped digit.

## Files

- `findings/meps-m8-flag-audit-v1/a8-tally.csv`: one row per flag in the frame (rank, brief, text number, near-miss
  cells, class, number of reads, reason).
- `skills/meps-statbrief-errata/data/meps-statbrief-errata.csv`, table 0.3.0: rows MEPS-E018 to MEPS-E028.

## Limits

Reads were made with an AI page reader (WebFetch), one per non-conflict flag; reads by the same tool are not
independent people, and a one-read class can be wrong. Every conflict and every exploratory find had two reads.
We did not check the PDF versions of the briefs or any later revision of the pages, and we did not recompute any of
these numbers from the public-use files, so none of the conflicts says which value is right. No human has checked
these results.
