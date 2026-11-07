# Pre-registration: census M7. Does any MEPS Statistical Brief print a Total outside the range of its own subgroups? (v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the scan runs. Text CC BY 4.0; code `meps/m7totals.py` 0.1.0 (Apache-2.0). Research information about
published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why

A percentage, mean or median for everyone is a mixture of the same statistic over any split of those people into
groups that do not overlap and leave no one out (age bands, sexes, insurance groups). So it cannot be smaller than the
smallest group value or larger than the largest, beyond rounding. A printed Total outside that range means that the
Total, a group value or a group label is wrong, or that the groups are not such a split.

Check R2b's results (`findings/meps-r2b-results-v1-2026-11-07.md`) found, after the recompute, that Brief #558's
Figure 1 age rates (11.1, 9.2, 6.1, 4.3) cannot average to its printed Total (6.2) for any plausible age mix. That
argument needed population shares from the data file. This census asks the cheaper, share-free question of every
table in census M3 (`findings/meps-brief-tables-v1/`, 2,999 accessible data tables): is the Total even inside the
range of its own groups?

## What was seen before this was written (disclosed)

- #558 Figure 1 in M3: Total 6.2; Age 11.1, 9.2, 6.1, 4.3; Race/ethnicity 4.6, 8.8, 9.3, 10.0. The Total lies inside
  both ranges, so this census cannot catch the #558 problem (prediction G1 below says so in advance).
- To learn M3's file layout, parts of `cells/st500-599.csv` (briefs 500 and 538-570) were read through a summarising
  web reader; one table seen in detail was #549 Table 3a (counts and percentages by age and insurance). No Total was
  compared with its groups, and no scan has been run.
- M4 and M5 hand checks (34 + 4 briefs) looked at labels, not at whether Totals fit their groups.

## Method (machine scan; `meps/m7totals.py` 0.1.0)

1. **Pairs.** For every table and every column, each row whose label reads as a total ("Total", "Total population",
   "Overall", "All persons/people/adults/...", "All", "United States", "U.S.") is paired with the other rows of its
   own M3 section if there are at least two; otherwise with every other section that has at least two rows. A section
   is the run of rows under one heading row (M3's `section` field). Total rows are never group rows.
2. **Verdicts** (rounding tolerance = half a unit in the last printed digit of each of the two numbers compared):
   - `excluded_label`: the title, column label, total label or section names a quantity the bound does not hold for
     (standard error, SE, change, difference, ratio, "number of", millions, thousands, count);
   - `excluded_negative`: a negative Total or group value;
   - `below` (flag): Total < smallest group value - tolerance;
   - `ok`: Total within [smallest, largest] +/- tolerance;
   - `sum_like`: Total > largest and Total >= 98% of the groups' sum - tolerance (a count or a share table);
   - `above` (flag): largest < Total < 98% of the groups' sum.
   Only row Totals are read; a Total printed as a column is not (stated limit).
3. **Hand-check sample.** Flagged figures (one brief + one label) are ordered by SHA-256 of `m7|<brief>|<label>`; if
   more than 40 are flagged, only the first 40 in that order are hand-checked (`check_rank`, `in_sample`). The order
   is fixed by the code, not chosen.
4. **Hand check.** For each sampled figure, two separate reads of the brief page (`stat<N>.shtml`) copy the Total and
   the group values of the flagged column exactly, and every sentence of the text, notes or definitions that says who
   the groups and the Total cover and what the statistic is. Classes:
   - **Inconsistent total:** the page matches M3; the groups are stated as, or plainly are, groups that do not
     overlap and leave no one out of the Total's population; the statistic is a percentage, mean or quantile of those
     people; the Total is outside the groups' range beyond rounding; and nothing on the page explains it.
   - **Not a partition:** the groups overlap (conditions, "any" categories), leave people out (selected groups), or
     the Total covers a different population, year or denominator.
   - **Not a mixture statistic:** counts, sums, shares of a total, standard errors, differences, ratios or similar that
     the label screen missed.
   - **Parser or artefact:** M3 put a value in the wrong row, section or column, or the page differs from M3.
   Only classes both reads agree on are counted; a disagreement gets a third read, which decides (2 of 3), and is
   logged.

## Predictions (graded exactly as written)

- **G1 (control, negative):** #558 Figure 1's Total is paired with both its Age and its Race/ethnicity sections and
  both pairs are `ok` (`control_558_f1.all_ok` true).
- **G2 (coverage):** at least 300 pairs get the bound applied (`pairs_bound_applied` = ok + below + above).
- **G3 (scan size):** between 3 and 80 figures (inclusive) are flagged.
- **G4 (false flags):** of the hand-checked figures, more than half are classed Not a partition or Not a mixture
  statistic.
- **G5 (primary):** between 1 and 5 hand-checked figures (inclusive) are classed Inconsistent total.

G4 and G5 are graded on the hand-checked figures only (all flagged figures if 40 or fewer). Per-figure classes are
reported alongside the pooled counts.

## Limits

M3 covers accessible data tables only; image-only figures are outside it. The bound is weak: a Total can be wrong and
still lie inside its groups' range (as in #558). Section boundaries come from M3's parser and may group rows that are
not one split. Row Totals only. The label screen is a fixed word list and will both miss and over-exclude. An
Inconsistent total is a documentation or transcription error somewhere in the figure; it does not say which number
is wrong, and the estimates in the data files may be right.

## Why this is new

Official statistics agencies run macro-editing checks before release, and tools such as statcheck and GRIM test
reported statistics in papers, but a web search on 2026-11-07 found no public audit that applies the mixture bound
(Total within its groups' range) across a federal statistical report series (inconclusive, as any search). No errata
for MEPS Statistical Briefs on this point were found in searches of 2026-11-02 to 11-07.
