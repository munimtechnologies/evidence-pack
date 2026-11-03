# Results: census M3, the published numbers in every MEPS Statistical Brief's accessible data tables (v1)

MV2 of Munim, Inc., 2026-11-03. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-brief-tables-prereg-v1-2026-11-02.md` (tag v0.9.37). Code: `meps/brief_tables.py`
0.1.0 (tag v0.9.38). Job `meps-brief-tables-v1`, 2026-11-02 12:20-12:52 UTC, exit 0. Data and text CC BY 4.0.
The numbers themselves are AHRQ's (U.S. government work), transcribed from AHRQ's pages. Research information
about published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## The dataset

`findings/meps-brief-tables-v1/`: **41,342 published numbers from 2,999 accessible data tables in 538 of the
546 MEPS Statistical Briefs** in census M1 (all 546 pages fetched, none failed). Each number has its brief, table,
figure or table label, row and column labels, printed text, value and printed decimals (`cells/stNNN-NNN.csv`).
Each table has its title, shape and sum-check result (`tables.csv`). Each page's SHA-256, per-brief counts and
the sum-check flags are in `brief-tables.json`. We found no earlier open, machine-readable collection of the
estimates printed in MEPS Statistical Briefs. Web searches on 2026-11-02 and 2026-11-03 found AHRQ's own MEPS-HC
and MEPS-IC data tools and the IC state tables, which are separate products and are not linked to briefs.

## Gate and predictions (graded as written)

- **Gate passed.** G1: Brief #569's labelled tables are Figures 1-8 with the 26 values typed in by hand for check
  R1, in order. G2: Brief #491's tables are Figures 1-3 with 15, 30 and 15 numbers.
- **P1 held.** 80 of the 84 briefs from 2016 on (95.2%) have at least one labelled data table (needed: 90%).
- **P2 held.** All 11 briefs eligible for check R2 have one.

## Exploratory: do "distribution" tables add up to 100?

380 tables have "distribution" in their title. For each, the job checked whether the columns (within a section)
or the rows sum to 100, within the rounding the printed decimals allow (half a unit in the last place per
number). **71 tables were flagged.** The pre-registration requires a hand check of every flag before anything is
said about it. Results:

**64 flags are our parser or the table's design, not errors.** We classified them from the parsed cells,
checking at least one table in each family, and from their titles:
- 40 are not shares of one whole. They are percentile tables (8: #111, 164, 318 x2, 401, 532 x3) or tables of
  the cumulative share held by the top 5/10/25/50% beside mean dollars (32: #421, 423, 448, 450, 480).
- 10 mix shares that do sum with counts, dollar or N columns (#197, 240, 539 x2, 545, 547 x5).
- 12 have structure the parser does not model: nested subtotals, "100%" header rows, payer lists without an
  "other" column, one-row tables whose first value became a label, difference-in-differences tables (#94, 106,
  151, 192, 348, 357, 358, 396, 494 x2, 502, 504).
- 2 are not distributions, or have empty (suppressed) cells (#225, 227).

**6 tables on 5 brief pages add up to more or less than rounding allows, and each was confirmed on the live page
by two reads** (census M3's machine read and a WebFetch "copy every cell exactly" read, 2026-11-03). Where the
brief's own text gives the same numbers, the text points to the likely error:

| Brief (data year) | Table | What does not add up | What the brief's text says |
|---|---|---|---|
| [#497](https://meps.ahrq.gov/data_files/publications/st497/stat497.shtml) (2014) | Figure 3, population and spending by age | Population column 100.5, spending column 99.6 (allowed: 100 +/- 0.2) | Ages 18-44 are "35.5 percent of the population"; ages 45-64 have "35.9 percent of total health care spending". The table has 35.9 and 35.5: the two cells look swapped. With the text's values, the columns sum to 100.1 and 100.0. |
| [#529](https://meps.ahrq.gov/data_files/publications/st529/stat529.shtml) (2017) | Figure 4, payer shares for top opioid products | Tramadol row: 31.1 + 29.1 + 12.6 + 8.2 + 2.1 = 83.1 (the other three rows: 100.1, 100.0, 100.0) | Medicare paid the largest share for all four products (34.6 to 54.3 percent), but the table gives tramadol's Medicare share as 29.1, below its private share. A Medicare value of 46.0 would close the row and fall inside that range. That is our inference; the page does not confirm it. |
| [#481](https://meps.ahrq.gov/data_files/publications/st481/stat481.shtml) (2012-13) | Figure 5, health status by spending persistence | "Top decile both years" column 102.0; "total population" column 99.6 | "17.9 percent were in poor health" (table: 19.9). With 17.9 the column sums to 100.0. |
| #481 (2012-13) | Figure 7, poverty status by spending persistence | "Total population 2013" column 100.6 | (text figures for this column match the table) |
| [#495](https://meps.ahrq.gov/data_files/publications/st495/stat495.shtml) (2014) | Figure 2, people by annual out-of-pocket amount and age | The "$501-1,000" row (68.8, 61.5, 73.3, 63.3%) makes the columns sum to 156.1, 155.3, 159.9 and 144.6 | "18.5 percent of people had out-of-pocket expenses greater than $1,000", "from 7.0 percent for children" "to 35.4 percent for the elderly". The table's two top rows give 19.3, 6.4 and 37.0. So at least two rows of this table disagree with the text. |
| [#359](https://meps.ahrq.gov/data_files/publications/st359/stat359.shtml) (2009) | Figure 5.2, payer shares for costly conditions | COPD/asthma, top 5%: 102.9; COPD/asthma, overall: 99.6 (allowed: +/- 0.25) | (only the out-of-pocket values are in the text, and they match) |

One more flag is marginal. In #449 Figure 2, one column sums to 100.3 against an allowed 100 +/- 0.25. Its cells
were confirmed on the page, and the brief's text gives no numbers to compare.

**What this does and does not show.** These are inconsistencies inside AHRQ's published pages, between an
accessible table and arithmetic or between a table and the same brief's text. We did not read the figure images,
so we do not know whether the charts show the same numbers. We did not recompute the estimates from microdata, so
we cannot say which printed value is right. #497 is one of the 11 briefs eligible for check R2 (not drawn). We
found no errata notices for these briefs (web search, 2026-11-03). The sum check finds only errors that break a
total. A wrong number in a table that still adds up, or in a table that is not a distribution, is invisible to it.

## Limits

Only HTML tables are read. Numbers that appear only in images, PDFs or running text are not captured. Rowspans
are not expanded, and labels are text matches. Older briefs often have tables without figure labels. A page can
change after we read it, so each page's SHA-256 is recorded. The 64 non-errors are classified from parsed cells
and titles, not re-read on the page.

## Use

The cells are read 1 of the double transcription that check R2 requires. For the three R2 briefs specified so far
(#506, #521, #540), read 1 and an independent read 2 agreed on all 120 cells
(`findings/meps-r2-spec-conc-v1-2026-11-03.md`). For MV2's planned entry to AHRQ's SI Tech Sprint, this is the
"published-number layer": every number a brief prints, in one place, with the page it came from.
