# Pre-registration: census M3, the published numbers in every MEPS Statistical Brief's accessible data tables (v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the job `meps-brief-tables-v1` fetches any brief page. Code: `meps/brief_tables.py` 0.1.0
(Apache-2.0). Text and data CC BY 4.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why

Recent MEPS Statistical Briefs show each figure as an image followed by an "accessible table" holding the same
numbers as HTML text. Census M1 read every brief's Data Source section; check R1 recomputed one brief's 26
figure numbers, typed in by hand. To reproduce briefs at scale, and for the checker MV2 is building for AHRQ's SI
Tech Sprint, the published numbers have to be machine-readable. We found no open, machine-readable collection
of the estimates printed in MEPS Statistical Briefs. AHRQ publishes them as HTML and PDF pages; MEPS-IC data
tools and MEPS summary tables are separate products (web search 2026-11-02, a short search and not a review).
M3 builds that collection and measures how much of the series it covers.

## Method (fixed now)

- Frame: every brief with `status` = ok in census M1 (`findings/meps-census-v1/briefs.csv`), fetched once each
  from `meps.ahrq.gov/data_files/publications/st<N>/stat<N>.shtml`, 3 seconds apart, after checking each URL
  against `meps.ahrq.gov/robots.txt` in code (one retry after 30 s). No data file is fetched.
- A **data table** is an innermost HTML table (one that contains no other table) with at least one cell, outside
  the first column, that is a single number (`42.8`, `$1,234`, `12 %`, `45.3*`). Leading rows with no number are
  header rows; colspans are expanded; a later row with no number is a section label. Its **label** is the first
  "Figure/Table/Exhibit/Chart N" in its caption, or else the last one in the page text before it.
- Output: one row per published number (brief, table, label, row and column labels, printed text, value,
  decimals), the page's SHA-256, and per-brief counts.

## Gate (nothing else is read unless both pass)

- **G1:** Brief #569's labelled data tables are exactly Figures 1-8 in order, and their numbers in page order are
  the 26 values check R1 typed in by hand (21.5, 9.2, 33.8, 42.8, 24.8, 67.6, 27.9, 17.4, 69.4, 72.4, 45.8,
  30.7, 45.3, 25.4, 47.7, 37.1, 30.4, 44.1, 43.9, 42.1, 41.7, 43.3, 42.7, 37.5, 38.9, 47.6).
- **G2:** Brief #491's labelled data tables are exactly Figures 1-3, with 15, 30 and 15 numbers (5 x 3,
  5 x 6 and 5 x 3, read with WebFetch on 2026-11-02).

## Predictions (graded exactly as written)

- **P1:** of the briefs fetched whose census year is 2016 or later, at least 90% have at least one labelled data
  table.
- **P2:** all 11 briefs eligible for check R2 (#491, 493, 496, 497, 506, 507, 521, 533, 540, 554, 558) have at
  least one labelled data table.

## Exploratory (reported, not graded)

- **Sum check:** in tables whose title contains "distribution", do all columns (within a section) or all rows
  sum to 100 within the rounding their printed decimals allow (half a unit in the last place per number;
  numbers printed as exactly 100 are left out)? Every flagged table is checked by hand against the page before
  anything is said about it. A flag can be a parsing artefact: a two-way table, a "total" row we did not
  recognise, or a table that is not a distribution.
- Counts by brief year; numbers per brief; the share of labelled tables.

## Role in check R2

For each brief drawn in check R2, this job's rows are **read 1** of the two independent transcriptions R2's
pre-registration requires. Read 2 is a WebFetch "copy every cell exactly" read of the same page. Disagreements
are settled by a third read and logged. Numbers printed only in the text (not in a table) are read twice with
WebFetch. R2's predictions and rules are unchanged.

## Limits

Only HTML tables are read. Numbers that appear only inside figure images, PDFs or the running text are not
captured. Rowspans are not expanded, and a label is a text match, not a judgement. Older briefs may print tables
without figure labels or as images. A page can change after we read it, so its SHA-256 is recorded.

## Outputs

`brief-tables.json` (gate, grades, per-brief counts and hashes, sum-check flags, errors), `tables.csv`, and
`cells/stNNN-NNN.csv` (one file per hundred brief numbers).
