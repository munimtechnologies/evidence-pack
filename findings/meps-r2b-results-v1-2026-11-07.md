# Check R2b results: the other six single-file MEPS Statistical Briefs recomputed from the public file each names (v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r2b-prereg-v1-2026-11-06.md` (tag v0.9.42; predictions graded below exactly as
written). Transcription: `findings/meps-r2b-transcription-v1-2026-11-06.md` (v0.9.43). Specification and code:
`findings/meps-r2b-spec-v1-2026-11-06.md`, `meps/r2b.py` 0.1.0 (v0.9.44). Job `meps-r2b-v1` (2026-11-06,
19:59-20:03 UTC) cloned v0.9.44, checked each zip's SHA-256 against the specification and passed every codebook
gate. Outputs: `findings/meps-r2b-v1/`. Text and data CC BY 4.0 (the published numbers are AHRQ's); code
Apache-2.0. Research information about published statistics, not medical advice. No endorsement by AHRQ is
implied; AHRQ has not been contacted.

## Results per brief (the first 40 in-scope published cells of each; #554 has 30)

| Brief | Year, file | Cells | Computable | Close | Exact | Not computable | Share close |
|---|---|---|---|---|---|---|---|
| #493 | 2014, HC-171 | 40 | 40 | 40 | 38 | 0 | 100% |
| #496 | 2014, HC-171 | 40 | 40 | 40 | 40 | 0 | 100% |
| #497 | 2014, HC-171 | 40 | 40 | 37 | 37 | 0 | 92.5% |
| #533 | 2018, HC-209 | 40 | 30 | 30 | 30 | 10 | 100% |
| #554 | 2021, HC-233 | 30 | 28 | 26 | 18 | 2 | 92.9% |
| #558 | 2021, HC-233 | 40 | 40 | 18 | 2 | 0 | 45% |
| **Pooled** | | 230 | 218 | 191 | 165 | 12 | 87.6% |

As in R2, "exact" and "close" are separate tests, so a cell can be exact without being close (a total printed as
"1" billion that we compute as 0.97 rounds to 1 but is 2.6% away).

## Predictions

- **C1 (primary), at least 80% of computable cells close in at least 5 of the 6 briefs: held.** Five briefs reach
  80%; #558 does not (45%).
- **C2, at least 80% of all computable cells exact: failed.** 165 of 218 (75.7%). Without #558 it would be 163 of
  178 (91.6%), but the prediction pooled all six.
- **C3, at most 2 briefs with a cell not computable from the named file: held.** Exactly two, as expected: #533's
  10 treated-condition cells (HC-209 has no condition variable; positive control TOTEXP18 found, negative control
  ICD10CDX absent) and #554's 2 MSA cells (no variable name or description mentions MSA or a metro area; positive
  control REGION31 found).
- **C4, at least 9 of all 11 eligible briefs (R2's five as published plus these six) with at least 80% of
  computable cells close: held.** 10 of 11; only #558 falls short.

**3 of 4 predictions held.**

Over all eleven eligible briefs (R2 + R2b), 347 of 408 computable cells are exact (85.0%) and 374 are close
(91.7%). With #569 (check R1), every MEPS Statistical Brief since 2016 that names a single Full Year Consolidated
file has now been recomputed.

## Brief by brief

- **#496 (spending tiers) and #533 (concentration, 2018):** every computable cell exact.
- **#493 (expenses by type of service):** 38 of 40 exact. The two misses are weighted medians, whose rule the brief
  does not state: all ages, any service, $1,373 against a printed $1,372, and hospital inpatient, $9,845 against
  $9,823 (0.2%). Both are close. The five service groups add up to TOTEXP14 for every person (0 mismatches). 199
  persons with a positive weight had AGE14X = -1 and were aged by AGELAST, as the specification said.
- **#497 (concentration, 2014):** 37 exact. Three dollar totals in billions miss the 1% test because they are
  printed to whole billions (1, 7 and 20 against 0.97, 6.87 and 19.41). The other two misses are the swap below.
- **#554 (e-cigarette use, young adults):** 26 of 28 close. The weight check holds person by person: no one with a
  positive SDOHWT21F lacks the item, and no one with the item has a zero weight, so SDOHWT21F is the
  questionnaire's weight. The two misses are both in Figure 4's general-health panel: "Good" 36.1 against a printed
  34.4 and "Fair/poor" 36.0 against 46.6. The mental-health panel beside it reproduces (three cells exact, one
  close). We cannot tell from the file whether the brief used a different health variable for that panel.
- **#558 (lack of reliable transportation):** 18 of 40 close. Some groups reproduce (any private insurance 3.42
  against 3.4; Medicare 7.74 against 7.9; diabetes, hypertension, stroke, high cholesterol; three of four
  mental-health groups). Others miss by a lot: the total (5.60 against 6.2), every age group (6.46, 5.89, 4.96 and
  4.83 against 11.1, 9.2, 6.1 and 4.3), Medicaid (14.1 against 20.4) and Hispanic adults (6.7 against 9.3). With
  Asian adults added to "Non-Hispanic other", that group is 9.05 against 10.0 (our reading leaves them out; 14.39).
  The specification's readings (weight, universe, age variable) are ours; the brief names no weight. A separate,
  pre-registered addendum (r558x, below) tests five simple alternatives.

## The documentation-consistency log, settled where the file can settle it

1. **#497 Figure 3: the table swaps two numbers, and the text is right.** The file gives ages 18-44 as 35.474% of
   the population and ages 45-64 as 35.948% of spending. The Findings text says 35.5 and 35.9; the table prints
   35.9 and 35.5 in those two places. The table's columns add to 100.5 and 99.6; with the text's values they add
   to 100.1 and 100.0. The two table cells are graded as printed (not exact, but close).
2. **#533 Figure 6's title repeats Figure 5's.** Not a number; outside the graded cells. Unchanged.
3. **#558 Figure 6: "at least two/three/four" (table) or "at least one/two/three" (text)?** Not settled. With the
   nine conditions of Figure 5 (smoking included), the file gives 6.24, 7.06, 8.12 and 9.11 for at least 1, 2, 3
   and 4; with eight (smoking left out), 5.96, 6.63, 7.46 and 8.11. The brief prints 6.6, 7.7 and 9.1. No count
   matches all three, and since #558's overall level does not reproduce, the file cannot decide.

## Found after the recompute (not pre-registered): #558 Figure 1's age rates cannot average to its total

While checking why #558's age groups missed, we read Figure 1 again (two reads, 2026-11-07; both give Total 6.2;
18-34 11.1; 35-49 9.2; 50-64 6.1; 65+ 4.3; the Findings text repeats 11.1, 6.1 and 4.3 and says "Overall, 6.2
percent"). The overall rate is the age rates averaged with the age groups' population shares. Allowing for
rounding (true rates at least 11.05, 9.15, 6.05 and 4.25), any adult population in which at least 25% are aged
18-34 and at least 20% are in each of 35-49 and 50-64 gives an average of at least
0.25 x 11.05 + 0.20 x 9.15 + 0.20 x 6.05 + 0.35 x 4.25 = 7.29%, above the highest value that prints as 6.2 (6.25).
So, unless the brief's age groups cover a very different population, the four age rates and the total cannot all
be right as labelled. Which is wrong is not known. The file gives a flatter age pattern and a total of 5.60, so it
does not side with either. The addendum computes the overall rate implied by the printed age rates using the
file's own weighted age shares.

## Limits

The readings of unstated choices are ours, and a failed cell may be our error, particularly in #558. #554 and #558
share one file and one weight, and #497 and #533 share R2's method with three R2 briefs, so the results are not
independent. Standard errors and significance statements were not checked. No human has reviewed these results.
Any note to AHRQ waits for a human check.

## Files

- `findings/meps-r2b-v1/cells-<N>.csv`: every graded cell with the published text, our value, the raw gap and the
  flags. `findings/meps-r2b-v1/r2b-<N>.json`: file hash, column positions, gates, cells, tally and every estimate
  the job made (including #497's population and spending shares and #558's condition counts).

Only aggregate estimates for published cells left the job; no person-level data is published.
