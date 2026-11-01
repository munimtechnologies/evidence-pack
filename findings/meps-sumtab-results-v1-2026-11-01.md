# Results: do AHRQ's MEPS-HC summary tables apply the 60-person rule to persons with an expense? (check S1, v1)

MV2 of Munim, Inc., 2026-11-01. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-sumtab-prereg-v1-2026-10-31.md` (tag v0.9.32). Code: `meps/sumtab_check.py` 0.1.0.
Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied. AHRQ has not been contacted about this; a human will check it first.

## Short answer

The tested line is in AHRQ's file exactly as read, and every published mean and median expenditure row carries
the same sample size as the cell's other rows. All five predictions held as written. **But a premise of the
test holds only in part of the tables (see "Correction after results").** In the cells where it does hold
(both the row and the column are a population subgroup), the 2022 table shows **18 means and 4 medians of
expenditure per person with an expense** whose subgroup very likely had fewer than 60 sample persons with an
expense, which is below AHRQ's published minimum. For one of them that is certain from the published numbers
alone: men aged 65+ without Medicare, sample size 60, with 82.8% having an expense, so at most 59 of them did.

## Run

Job `meps-sumtab-v1`, 2026-11-01 08:07-08:12 UTC, exit 0 (unit tests then the check). HHS-AHRQ/MEPS-summary-tables
at commit `4fbd9b1617a8d73d29a6e016b803b865208a1366`; 27 formatted tables `formatted_tables/hc_use/DY1996.csv` to
`DY2022.csv` (none were Git LFS pointers; SHA-256 of each in `sumtab.json`). `functions_format.R` SHA-256
`43629aee...0ac`; the job found the tested text, at line 124:

    mutate(sample_size = ifelse(value %in% c("meanEXP","medEXP"), n_exp, n)) %>%

followed by `suppress = ifelse(sample_size < 60 | se == 0, TRUE, suppress)` (line 131) and the RSE rules
(lines 126-134). These lines are US government work, quoted for analysis.

## Grades (exactly as pre-registered)

| | prediction | result | grade |
|---|---|---|---|
| P1 | 2022: `meanEXP` sample size = `pctEXP` sample size in >= 99% of comparable cells | 6,291 of 6,291 (100%) | held |
| P2 | same for `medEXP` | 6,291 of 6,291 (100%) | held |
| P3 | P1 share >= 99% in every year with >= 100 comparable cells | 27 of 27 years at 100%; none below | held |
| P4 | control: `totPOP` = `pctEXP` sample size in >= 99% of cells (2022) | 6,581 of 6,581 (100%) | held |
| P5 | >= 1 "low-n published" cell in 2022 | 886 rows | held (but see correction) |

In no year did any expenditure row carry a smaller or larger sample size than `pctEXP`
(`per-year.csv`: `less` = 0 and `greater` = 0 in all 54 year-statistic rows). Ambiguous control cells: 0 to 28 a
year, 0 from 2018 on.

## Correction after results (dated 2026-11-01, written after the grades above)

The pre-registration assumed that in every cell the sample size `n` counts all sample persons in the cell, so
that `pctEXP` < 100% forces the count of persons with an expense below `n`. While checking the results we read
the two scripts that build the event-type and payment-source columns (`code/use1_POP_EXP0.R`,
`code/use2_EXP.R`, same commit). There `n` is computed differently:

- **By event type** (dental, office-based, inpatient, home health, ...): `n` counts persons with any *use* of
  that event type (`sum(x > 0)` over use variables such as `HHTOTD`, `IPDIS`), while `pctEXP` is the share of
  *all* persons in the row group with an expense of that type.
- **By source of payment**: `n` counts persons with an expense paid by that source (`TOTSLF > 0` and so on).
- **Event x source of payment**: the same, per combination.

In those cells `n` is already (close to) the count of persons with an expense, so equality with `pctEXP`'s
sample size proves nothing, and the "n x pctEXP" estimate behind P5 is wrong there. The premise holds only for
cells computed in `run_use.R` itself, where `n` is an unweighted count on the full design and `n_exp` an
unweighted count on the design restricted to `TOTEXP > 0`, that is, cells where neither the row nor the column
variable is `event` or `sop`.

So we restrict the reading, after the fact, to those cells. Grades are not changed. P1-P3 remain 100% in the
restricted set, because no cell in any year differed. The table below says how big the restricted set is.
P5 shrinks from 886 rows to 44, all listed below.

| 2022 low-n rows | rows |
|---|---|
| all (as pre-registered) | 886 |
| row or column is an event type or payment source | 842 |
| **both row and column are population subgroups** | **44** |

The 44 rows show each cell twice (row and column swapped), and several cells are the same people under two
labels (e.g. "Under 18" x "Uninsured" = "Inapplicable (age < 18)" education x "Uninsured"). They are 22
published estimates: 18 means and 4 medians.

## The 22 estimates (2022 table, both variables population subgroups)

`n` = published sample size (all persons in the cell); `pctEXP` = AHRQ's weighted share with an expense;
"est." = n x pctEXP, an approximation to the unweighted count of persons with an expense.

| subgroup A | subgroup B | n | pctEXP | est. | published |
|---|---|---|---|---|---|
| Male | 65+, No Medicare | 60 | 82.8% | 49.7 (**at most 59, certain**) | mean $11,538; median $5,696 |
| Amer. Indian, AK Native, or mult. races | Less than high school | 63 | 66.8% | 42.1 | mean $11,426; median $4,402 |
| Uninsured, all ages | Near-poor | 100 | 30.5% | 30.5 | mean $1,697; median $500 |
| <65, Uninsured | Near-poor | 97 | 30.1% | 29.2 | mean $1,741; median $500 |
| Uninsured, all ages | Under 18 | 105 | 46.0% | 48.3 | mean $3,945 |
| <65, Uninsured | Under 18 | 105 | 46.0% | 48.3 | mean $3,945 |
| Uninsured, all ages | 5-17 | 90 | 38.7% | 34.8 | mean $2,980 |
| <65, Uninsured | 5-17 | 90 | 38.7% | 34.8 | mean $2,980 |
| Uninsured, all ages | Northeast | 91 | 51.3% | 46.7 | mean $2,159 |
| <65, Uninsured | Northeast | 91 | 51.3% | 46.7 | mean $2,159 |
| Uninsured, all ages | Separated | 69 | 52.7% | 36.4 | mean $1,542 |
| <65, Uninsured | Separated | 68 | 51.8% | 35.2 | mean $1,586 |
| Uninsured, all ages | Marital status inapplicable (age < 16) | 79 | 55.0% | 43.5 | mean $4,250 |
| <65, Uninsured | Marital status inapplicable (age < 16) | 79 | 55.0% | 43.5 | mean $4,250 |
| Uninsured, all ages | Education inapplicable (age < 18) | 105 | 46.0% | 48.3 | mean $3,945 |
| <65, Uninsured | Education inapplicable (age < 18) | 105 | 46.0% | 48.3 | mean $3,945 |
| Uninsured, all ages | Employment inapplicable (age < 16) | 80 | 54.0% | 43.2 | mean $4,250 |
| <65, Uninsured | Employment inapplicable (age < 16) | 80 | 54.0% | 43.2 | mean $4,250 |

Dollar values rounded from the file. For the first row the bound needs no approximation: the share is a weighted
mean of a yes/no variable over persons with positive weight, so a share below 100% means at least one sample
person in the cell had no expense, and at most 59 of the 60 did. For the others, reaching 60 persons with an
expense would need an unweighted share far above the weighted one (for example 95% against 66.8%, or 60% against
30.5%), which we think is very unlikely, but only the microdata can settle it (check S2 below).

## What this does and does not show

- It shows that, in AHRQ's archived formatted tables, the sample size attached to mean and median expenditure
  per person with an expense is the count of all persons in the cell, as the code line implies, and that some
  published estimates (22 in 2022) therefore passed a 60-person check that, by the documented standard, they
  very likely fail.
- It does not show that these estimates are wrong. They also passed AHRQ's relative-standard-error rule
  (RSE <= 0.5). The issue is that the published sample-size rule was not applied as written.
- It does not test the live tables on AHRQ's MEPS-HC summary tables site, which may be built differently.
- The 2022 count is small because most small cells involve event types or payers, where the count is right.
  Earlier years were not restricted the same way here; `per-year.csv` gives their unrestricted counts only.

## Next

Check S2 (to be pre-registered before any data is read): recompute `n` and the exact count of persons with an
expense for these 2022 cells from the MEPS 2022 full-year consolidated public-use file (HC-243), with a gate
that every recomputed `n` must equal AHRQ's published `n` before its count is reported.

## Files

`meps-sumtab-v1/per-year.csv` (per year and statistic: comparable cells, equal / less / greater / ambiguous),
`meps-sumtab-v1/sumtab.json` (commit, file hashes, grades), `meps-sumtab-v1/code-lines.txt` (suppression-related
lines of `functions_format.R`, US government work). The full 27-year list of 21,300+ unrestricted low-n rows
(about 3 MB) is not committed; the job rebuilds it.
