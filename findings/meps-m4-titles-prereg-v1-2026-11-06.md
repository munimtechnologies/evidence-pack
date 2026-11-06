# Pre-registration: census M4. Do figures in one MEPS Statistical Brief repeat each other's titles, and when they do, does the title describe the data? (v1)

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the scan runs. Text CC BY 4.0; code `meps/m4titles.py` 0.1.0 (Apache-2.0). Research information about
published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why

While transcribing check R2b (`findings/meps-r2b-transcription-v1-2026-11-06.md`), two reads found that Brief
#533's Figure 6 carries Figure 5's title ("Percentage of persons by race/ethnicity and percentile of spending,
2018") over a table of types of service (prescribed medicines, ambulatory events, inpatient stays, home health,
dental and other). A reader of Figure 6 alone would not know what it shows. Census M3
(`findings/meps-brief-tables-v1/`, 2,999 accessible data tables in 538 brief pages) already holds every table's
title and its row and column labels, so the same kind of slip can be looked for across the whole series at almost
no cost. M3's sum-to-100 check found 6 real inconsistencies in table values; M4 asks the same question of titles.

## What was seen before this was written (disclosed)

- #533 Figures 5 and 6 (above; confirmed by two reads and a hand check during R2b).
- While choosing the key rule, a Grep of M3's titles for figures with letter suffixes (1a, 1b, ...) showed
  #401 Figures 1a and 1b both titled "Payments for hospital inpatient stays, 2010", 1a over types of service
  (prescribed medicines, hospital inpatient, ambulatory care, other) and 1b over sources of payment. Not checked
  against the page yet; it counts only if the hand check below confirms it.
- The M3 title rows of #497, #533 and #558, and the suffix-labelled title rows of #126, #241, #295, #401 and #421.
No other duplicate search has been run.

## Method (machine scan; `meps/m4titles.py`)

1. **Title key:** the M3 title without its leading "Figure N." / "Table N:" label, lower-cased, with spaces
   collapsed. Older pages append the column headers to the caption, so the key is cut where the table's first
   column header (or the part of it after or before ": ") starts, if that is at least 15 characters in. End
   punctuation is removed. Keys shorter than 10 characters are listed separately and not paired.
2. **Candidates:** every pair of tables in one brief with equal keys.
3. **Machine class** of each pair, from M3's cells: *identical data* (same row labels, column labels and printed
   values), *same labels, different values*, or *different labels* (the row or column labels differ; this is the
   #533 pattern).
4. **Hand check of every candidate** (next runs): two separate reads of the brief page (`stat<N>.shtml`) copy both
   titles and both figures' row and column labels exactly. A pair is then one of:
   - **Title error:** a title names a measure, population or breakdown that its own figure's labels (or the
     brief's text about that figure) show it does not have.
   - **Repeated figure:** the same data printed twice.
   - **Legitimate repeat:** for example panels of one figure whose page headings tell them apart, or titles that
     differ on the page but not in M3's text.
   - **Artefact:** M3's title text differs from the page.
   Only cases on which both reads agree are counted. Disagreements get a third read and are logged.

## Predictions (graded exactly as written)

- **D1 (method check):** the scan lists #533 Figures 5 and 6 as a candidate, in the class *different labels*. If it
  does not, the key rule failed and that is reported first.
- **D2 (primary):** apart from #533, between 1 and 5 briefs (inclusive) have at least one confirmed title error.
- **D3:** at most 2 candidate pairs are confirmed repeated figures (identical data printed twice).

## Limits

M3 covers only tables printed as accessible text; figures shown only as images are outside it. The key rule is
crude: titles that differ only in the column headers M3 appended may be missed, and a short first header can cut a
key early. Candidates are hand-checked, so false candidates cost time but are not counted. A title error found
here is a documentation slip, not evidence that any estimate is wrong.

## Why this is new

Searches on 2026-11-02, 2026-11-03 and 2026-11-06 found no errata for these briefs and no systematic check of
figure titles in MEPS Statistical Briefs or, more broadly, in a federal statistical report series. Style guides
(for example NCES's) say a figure title should describe its content; no one appears to have counted how often a
series meets that rule.
