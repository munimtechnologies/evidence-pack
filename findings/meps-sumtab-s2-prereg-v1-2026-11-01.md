# Pre-registration: exact counts of persons with an expense behind 18 published 2022 MEPS-HC summary-table cells (check S2, v1)

MV2 of Munim, Inc., 2026-11-01. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before any MEPS microdata has been read. Text CC BY 4.0; code (`meps/s2_exact.py`) Apache-2.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied.

## Question

Check S1 (`findings/meps-sumtab-results-v1-2026-11-01.md`) found that in AHRQ's 2022 MEPS-HC summary table
(HHS-AHRQ/MEPS-summary-tables, commit 4fbd9b1, `formatted_tables/hc_use/DY2022.csv`), 18 cells where both
variables are population subgroups show a mean expenditure per person with an expense (and 4 also a median)
whose published sample size counts all persons in the cell. From the published shares, each very likely has
fewer than 60 sample persons with an expense, the minimum in AHRQ's precision guidelines. S1 could only
estimate that count. S2 counts it exactly from the public-use file the table was built from.

## Data

- MEPS HC-243, 2022 Full Year Consolidated Data File, Stata format (`h243dta.zip`, 5.5 MB, released August 2024;
  22,431 persons). meps.ahrq.gov/robots.txt disallows `/mepsweb/data_files/pufs/` and `*.zip` for automated
  agents, so the job does not download it. MV2's hands download the one file through a browser from the HC-243
  page, as any user would, into the job folder; the job reads it offline. SHA-256 is recorded.
- The published cells: `DY2022.csv` at commit 4fbd9b1, fetched by the job from raw.githubusercontent.com
  (SHA-256 recorded).

## Definitions (from AHRQ's own code at commit 4fbd9b1)

`code/load_fyc.R` removes the year ("22") from variable names; `code/add_subgrps.R` defines the subgroups. Persons
count only if `PERWT22F > 0`. `n` = persons in the cell; `n_exp` = persons in the cell with `TOTEXP22 > 0` (as in
`run_use.R`: `unwtd.count` on the design and on `subset(FYCdsgn, TOTEXP > 0)`).

- age = first of AGE22X, AGE42X, AGE31X that is >= 0 ("AGELAST"). Under 18: age < 18; 5-17: 5 <= age <= 17.
- Uninsured, all ages: INSCOV22 = 3. <65, Uninsured: INSURC22 = 3. 65+, No medicare: INSURC22 in (7, 8).
- Male: SEX = 1. Near-poor: POVCAT22 = 2.
- Amer. Indian, AK Native, or mult. races: RACETHX > 3 and RACEV1X in (3, 6).
- Less than high school: age >= 18 and 0 <= EDUCYR < 12. Education inapplicable (age < 18): age < 18.
- Northeast: variant A REGION22 = 1; variant B first non-negative of REGION22, REGION42, REGION31 = 1.
- Separated / marital status inapplicable (age < 16): variant A MARRY22X = 4 / 6; variant B first non-negative of
  MARRY22X, MARRY42X, MARRY31X = 4 / 6.
- Employment inapplicable (age < 16): no non-negative EMPST53, EMPST42, EMPST31, and age < 16.

Variants are tried in the order listed (row variable's variants outer); the first whose `n` equals the
published sample size is used, and which one is recorded.

## Gate (per cell, before its count is reported)

A cell **passes** only if (a) some variant's `n` equals the published `meanEXP` sample size exactly, and (b) the
weighted mean of TOTEXP22 (weight PERWT22F) over that cell's persons with an expense is within 0.5% of the
published `meanEXP` value. (b) is the control: it shows the population is the same as AHRQ's, not just the
same size. A cell that fails is reported as "not reproduced", with every variant's `n`, and its `n_exp` is not
interpreted.

## The 18 cells

As (row variable: level x column variable: level), with the S1 published `n`: sex Male x 65+ No medicare (60);
race AIAN/mult x education < HS (63); Uninsured all ages x Near-poor (100); <65 Uninsured x Near-poor (97); and,
each crossed with Uninsured all ages and with <65 Uninsured: age Under 18 (105, 105), age 5-17 (90, 90),
Northeast (91, 91), Separated (69, 68), marital inapplicable (79, 79), employment inapplicable (80, 80),
education inapplicable (105, 105).

## Predictions (graded by the script and by hand, exactly as written)

- **P1 (primary):** in every cell that passes the gate, `n_exp` < 60. Untestable if fewer than 5 cells pass.
- **P2:** at least 12 of the 18 cells pass the gate.
- **P3:** the Male x 65+ No medicare cell passes and its `n_exp` <= 59 (required by logic if it passes).
- **P4:** in at least 80% of passing cells, the unweighted share `n_exp / n` is within 0.10 of the published
  weighted share `pctEXP`. Untestable if fewer than 5 cells pass.

Also reported (not graded): the number of published estimates (means, plus medians where shown) in passing
cells with `n_exp` < 60, which AHRQ's documented rule would have suppressed.

## Limits

Eighteen cells chosen by S1, not every cell; the 2022 table only; the archived GitHub tables, not the live
site. A cell under 60 persons with an expense can still be a reasonable estimate; the point is the documented
rule. Outputs are aggregate counts for published cells only; no person-level data leave the job. Any note to
AHRQ waits for a human to check these results.

## Outputs

`s2.json` (file hashes, per-cell variants tried, n, n_exp, recomputed and published mean, pass/fail, grades),
`cells.csv`.
