# Pre-registration: exploratory addendum to check R1 (MEPS Statistical Brief #569), v1

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the job `meps-r569x-v1` reads any MEPS microdata for this addendum. Code: `meps/r569x.py` 0.1.0
(Apache-2.0). Text CC BY 4.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why an addendum, and what it is not

Check R1 v1 (results: `findings/meps-r569-results-v1-2026-11-02.md`, tag v0.9.36) recomputed 24 of #569's 26
percentages from HC-243. 19 rounded to the published value; five did not: F2a (42.7498 vs 42.8, the headline),
F4b (72.469 vs 72.4) and three of the four region cells in Figure 7 (F7a 44.034 vs 44.1, F7b 44.129 vs 43.9, F7c
41.978 vs 42.1). The R1 pre-registration said a miss would be diagnosed only in a dated addendum with the
definitions unchanged. This is that addendum. **It does not regrade R1.** P2 stays failed whatever this shows.
Everything below is exploratory and is reported side by side with the primary definition.

## Variants (each changes one thing relative to R1's primary definition A)

| variant | change | reason it is worth trying |
|---|---|---|
| A | none (control) | must reproduce R1 v1 (gate) |
| REG42 / REG31 / REG53 | Figure 7 region from `REGION42`, `REGION31` or `REGION53` instead of the end-of-year `REGION22` | #569 defines region as "the location of residence" without naming the round; HC-243 carries four region variables (codebook: `REGION53` "CENSUS REGION - R5/3", 1-4, -1 = inapplicable) |
| C2 | the 50+ cells select age by the SAQ's own item `ADAGE42 = 4` ("50 OR OLDER"); the 50-64 and 65+ cells are unchanged | fixes R1's mis-specified variant C (it treated the four-category `ADAGE42` as years, so n = 0) |
| AGE22 | age from `AGE22X` first (then `AGE42X`, `AGE31X`), ignoring `AGELAST` | the brief says "age at the end of the year 2022, or on last date of MEPS eligibility" |
| U3 | scan denominator also keeps women whose osteoporosis answer is -15 "cannot be computed" (`ADOSTP42` in (2, -15)) if they answered the scan item | the brief says women with diagnosed osteoporosis are not asked; it does not say how unknowns are handled |
| PW | weighted by `PERWT22F` (the person weight) among SAQ completers, instead of `SAQWT22F` | **negative control**: the brief says the SAQ weight is used; HC-243 has only one SAQ weight (`SAQWT22F`, codebook checked 2026-11-02: no `PSAQWT22F`) |

The "alternative SAQ weight" idea in our plan is dropped because HC-243 has no second SAQ weight; PW replaces it
as a control.

## Gate

Variant A must give every one of the 24 cells within 0.0005 points of R1 v1's `cells.csv` value, and exactly 19
exact cells. If the gate fails, nothing else in this addendum is read; the code is fixed and re-run under a new
version.

## Fixed readings (written now, applied mechanically by `readings()` and by hand)

- **Region:** a region variant "accounts for" Figure 7 only if, with it, all four region cells are exact
  (within 0.05). If none does, we write that region choice does not explain Figure 7.
- **Candidates:** any variant other than PW with more than 19 exact cells is listed as a candidate explanation.
  For each one we also report which of R1's 19 exact cells it breaks.
- **X1 (the only prediction, a sanity check):** the PW control gives fewer than 19 exact cells.
- For every variant: the exact count (within 0.05), the "rounds to the published decimal" count (half-up), the
  close count (within 0.5) and the raw gap for each of the five missed cells.
- Whatever the outcome, the conclusion is worded as "this definition choice reproduces / does not reproduce
  the published value", never "AHRQ used X".

## Data

`h243dta.zip`, the same file as R1 (5,789,896 bytes; SHA-256 recorded by R1 as `7fc534de...b454` and
re-recorded by this job), copied by MV2's hands into the job folder. The job never downloads it.

## Limits

Exploratory, one brief, eight variants chosen before seeing any variant result. A variant that reproduces a cell
can still be the wrong explanation. Only aggregate percentages for published cells leave the job.

## Outputs

`r569x.json` (file hash, gate, per-variant summaries, readings, per-cell values), `variants.csv`.
