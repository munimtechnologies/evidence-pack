# Pre-registration: census M8 v0.2. Numbers in MEPS brief text that the cited figure does not hold, now read on older page layouts too (v2)

MV2 of Munim, Inc., 2026-11-08. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the v0.2 scan runs. Text CC BY 4.0; code `meps/m8text2.py` 0.2.0 (Apache-2.0) with offline tests
(`meps/test_m8text2.py`). Research information about published statistics, not medical advice. No endorsement by
AHRQ is implied; AHRQ has not been contacted.

## Why a v0.2

Census M8 v0.1 (`findings/meps-m8-text-results-v1-2026-11-08.md`, tag v0.9.55) read text only outside HTML tables. It
reached the 17 newest briefs (#554-#570) and nothing older, so 2 of 5 predictions held and the #536 control was never
reached. The cause was suspected to be layout tables. The diagnosis below confirms it.

## Diagnosis result (job `meps-m8diag-v1`, `meps/m8diag.py` 0.1.0, Blade, 2026-11-08 08:28-08:32 UTC)

Diagnosis only, not graded. For 14 fixed briefs, characters of text and "(figure N)" citations by where they sit on
the page: outside every table, inside a layout table (a table that contains another table), or inside an innermost
table. Output: `findings/meps-m8diag-v1/m8-diag.json`.

| Brief | Tables (layout) | Outside: chars / cites | Layout: chars / cites | Innermost: chars / cites |
|---|---|---|---|---|
| #536 | 23 (2) | 82 / 0 | 16,309 / 20 | 8,987 / 0 |
| #533 | 16 (2) | 176 / 0 | 16,517 / 8 | 2,955 / 0 |
| #497 | 15 (3) | 119 / 0 | 12,619 / 6 | 3,133 / 0 |
| #460 | 13 (3) | 119 / 0 | 11,509 / 0 | 2,823 / 0 |
| #423 | 18 (3) | 154 / 0 | 20,140 / 7 | 5,761 / 0 |
| #352 | 12 (3) | 93 / 0 | 11,490 / 0 | 2,432 / 0 |
| #297 | 12 (3) | 93 / 0 | 9,708 / 3 | 2,091 / 0 |
| #257 | 17 (3) | 150 / 0 | 15,749 / 5 | 2,432 / 0 |
| #217 | 19 (3) | 115 / 0 | 14,264 / 8 | 2,425 / 0 |
| #170 | 16 (4) | 132 / 0 | 13,074 / 6 | 2,117 / 0 |
| #100 | 14 (3) | 128 / 0 | 14,326 / 7 | 2,743 / 0 |
| #10 | 12 (3) | 91 / 0 | 6,453 / 5 | 1,905 / 0 |
| #554 | 12 (1) | 13,026 / 5 | 0 / 0 | 1,564 / 0 |
| #567 | 15 (1) | 17,970 / 8 | 0 / 0 | 1,841 / 0 |

In all 12 briefs from #10 (2003) to #536 (2021), the body text and every parenthesised figure citation sit inside
layout tables; fewer than 180 characters sit outside any table. In #554 and #567 the body sits outside tables. No
innermost table holds a citation, so innermost tables can be treated as data tables. #460 and #352 have no
parenthesised citation at all (they may cite figures in headings or not at all), which is why the gate below asks for
9 of 12, not 12 of 12.

## What was seen before this was written (disclosed)

- Everything listed in the v1 pre-registration, the v1 run outputs (`findings/meps-m8-text-v1/`) and its hand check
  of 7 flags in #555, #558, #559, #564 and #566 (the source of fixes 2-6 below).
- The diagnosis output above (counts only, no numbers from the text).
- One WebFetch read of brief #170's page asking only for its section headings and menu labels (no numbers): body
  sections are Highlights, Introduction, Findings, Data Source, Definitions, About MEPS-HC, References, Suggested
  Citation, and none of those names appears in the menu above the body.

## Method (`meps/m8text2.py` 0.2.0)

Everything in v1's method holds (pages, M3's table parser, verdicts, flags, two-read hand check), with these changes:

1. **Text reader.** Text outside tables and inside layout tables is read; text inside innermost tables is skipped.
   Layout-table cells (`td`, `th`, `tr`) and two `<br>` in a row also end a block.
2. **Signs.** A text number is compared with each cell's absolute value (match, 100 minus a cell, near-miss).
3. **Figure lists.** A cited figure number cannot be followed by a decimal point and digit ("figure 5, 7.7" cites
   figure 5 only).
4. **Citations.** A block is checked against the figures it names plus those named in the nearest heading-like block
   above it (v1 used the block's own if it had any, else the heading's).
5. **Derived.** Besides 100 minus a cell and the difference of two cells in one row or column, the sum of two cells in
   one row counts as derived.
6. **Skipped numbers.** A number right after "less than", "more than", "fewer than" or "greater than" (optionally
   "about"/"approximately" and "$") is not checked (counted as `bounds_skipped`). Blocks are not checked from a
   heading-like block reading exactly "Definitions", "Data source(s)", "About MEPS(-HC)", "References" or
   "Suggested citation" until the next h1-h6 heading with another name.
7. **Coverage gate (new).** The 14 diagnosis briefs are scanned first. The other briefs in M3's `tables.csv` are
   scanned only if at least 9 of the 12 older-template ones (#10-#536) have at least one checked number. If the gate
   fails, the census stops and is graded as failed.
8. **Hand-check sample.** Flags ordered by SHA-256 of `m8v2|<brief>|<block>|<number as printed>`; the two control
   flags set aside; the first **20** others (`check_rank` 1-20) are hand-checked, two WebFetch reads each, a third on
   disagreement (2 of 3 decides). Classes as in v1 (Figure-text conflict, Different quantity, Parser or association
   artefact) plus **Known slip**: a flag at one of the 11 slips listed, before this scan, in
   `findings/meps-known-slips-v1-2026-11-08.csv` (published with this note; each row points to the results note
   that first logged it). Known slips are reported but left out of H4 and H5.

## Predictions (graded exactly as written)

- **G (gate):** at least 9 of the 12 older-template development briefs have at least one checked number.
- **H1 (controls):** both control flags are produced: #567 text 0.9 with near-miss 1.9, and #536 text 89.2 with
  near-miss 86.2.
- **H2 (coverage):** at least 50% of fetched briefs have at least one checked number (`coverage` >= 0.50).
- **H3 (agreement):** `matched_share` >= 0.70 over all checked numbers.
- **H4 (primary):** between 1 and 10 (inclusive) of the hand-checked sample, Known slips left out, are Figure-text
  conflicts.
- **H5 (false flags):** more than half of the hand-checked sample, Known slips left out, are Different quantity or
  Parser or association artefact.

If the gate fails, H1-H5 are graded as failed (not run). If fewer than 20 non-control flags exist, all are checked.
`matched_share_old` and `matched_share_new` (briefs before #554 and from #554) are reported, not graded.

## Limits

As in v1: decimal numbers only; only figures with an accessible data table; a wrong number can still match another
cell; a near-miss can arise by chance; the heading rule can tie a paragraph to the wrong figure, and the union rule
(change 4) gives each block more cells to match, which can hide a slip. A Figure-text conflict says one of two printed
numbers is wrong, not which. The fixes come from 7 flags in 6 recent briefs; older pages may break the reader in new
ways, which is what the gate and the per-era shares are for.

## Prior art

Unchanged from v1 (see `findings/meps-m8-text-prereg-v1-2026-11-07.md`): text-table consistency checking exists for
financial reports and scientific papers, and statistical producers are told to cross-check publication figures
against tables. We found no public, pre-registered audit of a whole federal statistical report series that matches
the text's numbers against the data tables of the figures they cite (searches 2026-11-02 to 11-08, inconclusive as any
search).
