# Pre-registration: do AHRQ's MEPS-HC summary tables apply the 60-person rule to persons with an expense? (check S1, v1)

MV2 of Munim, Inc., 2026-10-31. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the check job has read a single table. Text CC BY 4.0; code (`meps/sumtab_check.py`) Apache-2.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied.

## Question

AHRQ's precision standard for MEPS-HC tables says published means "should be based on an unweighted sample of
at least 60 persons for the subgroup of interest", and that estimates with a relative standard error above 0.50
are not shown (meps.ahrq.gov/survey_comp/precision_guidelines.shtml, read 2026-10-31). For "mean expenditure per
person with an expense" (`meanEXP`) and the median (`medEXP`), the subgroup of interest is the persons in the
cell who had an expense.

AHRQ's public code for the MEPS-HC summary tables (github.com/HHS-AHRQ/MEPS-summary-tables, archived 2026-06-09,
newest commit 4fbd9b1) computes that count separately: `run_use.R` saves `n` (all sample persons in the cell)
and `n_exp` (sample persons with `TOTEXP > 0`). The formatting step in `functions_format.R` then picks the
sample size used for suppression with this line (read twice through a page summariser on 2026-10-31; the job
records the line from the file itself):

    mutate(sample_size = ifelse(value %in% c("meanEXP","medEXP"), n_exp, n)) %>%

At that point `value` holds the numeric estimate (it was renamed from the stat column earlier, while the stat
name is kept in `stat_var`), so the test can never be true and every row would get `n`. If so, the published
mean and median expenditure rows carry the count of all persons in the cell, and the 60-person rule is applied
to the wrong count.

The formatted tables in the same repository (`formatted_tables/hc_use/DY1996.csv` to `DY2022.csv`, "the final
version of the formatted data tables that are used in the MEPS-HC summary tables web page", per its README)
keep a `sample_size` column, so this can be tested from AHRQ's published files alone, with no microdata.

## Prior art (searched 2026-10-31)

The repository has no open issues (it is archived and read-only). Web searches for an error in the MEPS summary
tables' sample sizes or suppression found nothing. We found no published check of these tables' suppression
inputs.

## Method (fixed)

1. Resolve `main` of HHS-AHRQ/MEPS-summary-tables to a commit SHA (GitHub API), list `formatted_tables/hc_use`
   at that SHA, and download every `DY<year>.csv` and `functions_format.R` from raw.githubusercontent.com at
   that SHA (Git LFS pointers are followed to media.githubusercontent.com). SHA-256 of every file is recorded.
2. Cell = (row_group, row_var, rowLevels, col_group, col_var, colLevels). For each cell, read the
   `sample_size` and `value` of the rows with stat_var `totPOP`, `pctEXP`, `meanEXP`, `medEXP`. A row set with
   more than one distinct sample size is "ambiguous" and is counted, not compared.
3. Logic of the test: `pctEXP` is the weighted share of the cell with an expense. If it is below 100%, at least
   one sample person in the cell had no expense, so a correct count of persons with an expense is strictly
   smaller than the cell's `n`. Comparable cells: `pctEXP` has one sample size and one value, and its value is
   below 99.9% (percent or fraction scale detected per file). In those cells, compare the `meanEXP` (and
   `medEXP`) sample size with the `pctEXP` sample size (`n`): equal, less or greater.
4. Control: in every cell with both rows, the `totPOP` sample size should equal the `pctEXP` one (both `n`).
5. Primary table: the newest year in the folder (expected DY2022).
6. P5 estimate: persons with an expense ~ `n` x `pctEXP` share (a weighted share standing in for an unweighted
   one, so approximate). A "low-n published" cell is a `meanEXP` or `medEXP` row with a value shown, a
   sample size of at least 60, and an estimated count of persons with an expense below 50.

## Predictions (graded by the script and by hand, exactly as written)

- **P1 (primary):** in the primary table, the `meanEXP` sample size equals the `pctEXP` sample size in at least
  99% of comparable cells (untestable if fewer than 100). If the code worked as intended, it would be 0%.
- **P2:** the same holds for `medEXP` in the primary table.
- **P3:** the P1 share is at least 99% in every year's table with at least 100 comparable cells (untestable if
  fewer than 20 tables qualify).
- **P4 (control):** in the primary table, `totPOP` and `pctEXP` sample sizes are equal in at least 99% of cells
  with both (untestable if fewer than 100). If P4 fails, P1-P3 are reported but not interpreted.
- **P5 (consequence):** only if P1 holds, at least one low-n published cell exists in the primary table.

If P1 fails (the tables carry a smaller count), our reading of the code is wrong for the published files and we
will say so.

## Limits

This tests the formatted files in AHRQ's archived GitHub repository, not the live tables on AHRQ's data tools
site, which may have been rebuilt differently. P5 is an approximation; an exact count of affected cells needs the
MEPS full-year consolidated public-use file and would be a separate, pre-registered check. A cell that slipped
past the 60-person rule may still be a reasonable estimate; the issue is that the published rule was not applied
as written. Any report to AHRQ waits for a human to check these results.

## Outputs

`sumtab.json` (commit SHA, file hashes and sizes, stat names per file, per-year comparisons, grades, whether the
tested code line was found), `per-year.csv`, `low-n-published.csv` (aggregate published cells only),
`code-lines.txt` (the suppression-related lines of `functions_format.R`, US government work).
