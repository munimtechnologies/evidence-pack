# Results: exact counts of persons with an expense behind 18 published 2022 MEPS-HC summary-table cells (check S2, v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-sumtab-s2-prereg-v1-2026-11-01.md` (fixed before any microdata was read). Code:
`meps/s2_exact.py` 0.1.0. Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied. AHRQ has not been contacted about this; a human will check it
first.

## Short answer

All four predictions held. Every one of the 18 cells passed the gate: the recomputed number of persons equals
AHRQ's published sample size exactly, and the recomputed weighted mean expenditure matches AHRQ's published
mean to the cent. In **every** cell, the number of sample persons with an expense is **below 60**, between 34
and 51. So the 22 estimates that check S1 flagged (18 means and 4 medians of expenditure per person with an
expense, 2022 table) rest on fewer persons than the 60 that AHRQ's precision guidelines name as the minimum for
a continuous estimate. In AHRQ's code, the count that the 60-person rule is tested against is the count of all
persons in the cell (S1). These estimates are not shown to be wrong; only the documented sample-size rule was
not applied as written.

## Run

Job `meps-s2-v1`, 2026-11-01 15:26-15:29 UTC, exit 0 (unit tests, then the check). Inputs:

- `h243dta.zip` (MEPS HC-243, 2022 Full Year Consolidated, Stata), 5,789,896 bytes, SHA-256
  `7fc534de09eff5fd81facb74d61511d322ebe8bc45af7b75441204fcaf9fb454`, downloaded once through a browser by MV2's
  hands from the HC-243 page (meps.ahrq.gov/robots.txt asks automated agents not to fetch public-use files).
  22,431 persons, 21,747 with a positive weight.
- `formatted_tables/hc_use/DY2022.csv` from HHS-AHRQ/MEPS-summary-tables at commit `4fbd9b1`, 18,981,260 bytes,
  SHA-256 `4250ef87...5bce` (full hash in `meps-s2-v1/s2.json`).

## Grades (exactly as pre-registered)

| | prediction | result | grade |
|---|---|---|---|
| P1 (primary) | in every cell that passes the gate, `n_exp` < 60 | 18 of 18 passing cells; largest `n_exp` 51 | held |
| P2 | at least 12 of 18 cells pass the gate | 18 of 18 (first variant tried, `AA`, in every cell) | held |
| P3 | Male x 65+ No Medicare passes and its `n_exp` <= 59 | passes; `n_exp` = 47 | held |
| P4 | in >= 80% of passing cells, `n_exp / n` is within 0.10 of the published `pctEXP` | 17 of 18 (94%) | held |

The one P4 miss is <65 Uninsured x Near-poor: 39 / 97 = 0.402 against a published weighted share of 0.301, a
gap of 0.101. Every mean matched within 0.000001% (gate b allowed 0.5%).

## The 18 cells

`n` = all sample persons in the cell (= AHRQ's published sample size); `n_exp` = sample persons with any 2022
expense (TOTEXP22 > 0); mean = weighted mean expenditure per person with an expense, recomputed (= published).

| cell | n | n_exp | mean |
|---|---|---|---|
| Male x 65+, No Medicare | 60 | **47** | $11,538 |
| Amer. Indian, AK Native, or mult. races x Less than high school | 63 | **46** | $11,426 |
| Uninsured, all ages x Near-poor | 100 | **40** | $1,697 |
| <65, Uninsured x Near-poor | 97 | **39** | $1,741 |
| Under 18 x Uninsured, all ages | 105 | **51** | $3,945 |
| Under 18 x <65, Uninsured | 105 | **51** | $3,945 |
| 5-17 x Uninsured, all ages | 90 | **38** | $2,980 |
| 5-17 x <65, Uninsured | 90 | **38** | $2,980 |
| Northeast x Uninsured, all ages | 91 | **49** | $2,159 |
| Northeast x <65, Uninsured | 91 | **49** | $2,159 |
| Separated x Uninsured, all ages | 69 | **35** | $1,542 |
| Separated x <65, Uninsured | 68 | **34** | $1,586 |
| Marital status inapplicable (age < 16) x Uninsured, all ages | 79 | **44** | $4,250 |
| Marital status inapplicable (age < 16) x <65, Uninsured | 79 | **44** | $4,250 |
| Employment inapplicable (age < 16) x Uninsured, all ages | 80 | **44** | $4,250 |
| Employment inapplicable (age < 16) x <65, Uninsured | 80 | **44** | $4,250 |
| Education inapplicable (age < 18) x Uninsured, all ages | 105 | **51** | $3,945 |
| Education inapplicable (age < 18) x <65, Uninsured | 105 | **51** | $3,945 |

Several cells are the same people under two labels (for example "Under 18" and "Education inapplicable
(age < 18)", crossed with either uninsured definition). Counted as distinct groups of people, the 18 cells are
11 groups; every one of them has fewer than 60 persons with an expense. The first four cells also carry a
published median, so 22 published estimates are affected (not graded, reported as pre-registered).

## What this does and does not show

- It shows, from AHRQ's own public-use file and with a gate that reproduces AHRQ's published sample size and
  mean exactly, that 22 published 2022 estimates of expenditure per person with an expense rest on 34 to 51
  sample persons with an expense, below the 60-person minimum in AHRQ's precision guidelines
  (meps.ahrq.gov/mepsweb/survey_comp/precision_guidelines.shtml).
- It does not show that the estimates are wrong or misleading; they passed AHRQ's relative-standard-error rule.
- It covers 18 cells from the 2022 archived GitHub tables only, chosen by S1, not the live MEPS-HC summary-table
  site, and not other years or cells that involve event types or payers (where S1 found the count is right).
- Only aggregate counts and means for already published cells leave the job; no person-level data.

## Prior art

Searches on 2026-11-02 (web; GitHub) found no published audit of the sample sizes behind suppression in AHRQ's
MEPS-HC summary tables other than MV2's own S1 (tags v0.9.32, v0.9.33).

## Files

`meps-s2-v1/s2.json` (file hashes, per-cell variants tried, n, n_exp, recomputed and published means, grades),
`meps-s2-v1/cells.csv`.
