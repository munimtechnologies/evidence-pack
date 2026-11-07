# Pre-registration: MEPS Statistical Brief #558, internal consistency of Figure 1 and five alternative readings (addendum r558x to check R2b, v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the job below reads the file. Exploratory addendum: it changes no grade of check R2b
(`findings/meps-r2b-results-v1-2026-11-07.md`). Code: `meps/r558x.py` 0.1.0 with offline tests
(`meps/test_r558x.py`). Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## What we already know (disclosed)

- R2b reproduced 18 of #558's 40 graded cells within 0.5 points. The total is 5.60 against a printed 6.2, and the
  age pattern is flatter than the brief's (6.46, 5.89, 4.96, 4.83 against 11.1, 9.2, 6.1, 4.3).
- By hand, for any adult population with at least 25% aged 18-34 and at least 20% in each of 35-49 and 50-64, the
  four printed age rates average to at least 7.29%, above the 6.25 that would still print as 6.2. We have not yet
  computed the age shares from the file.

## Questions and method

The job reads HC-233 (the same zip and SHA-256 as R2b) and passes R2b's codebook gates. It adds PERWT21F (full-year
person weight) and AGELAST to R2b's variables (positions from census inventory v1).

1. **Consistency.** Among #558's base as R2b defined it (AGE31X >= 18, SDOHWT21F > 0, SDNOTRANS answered 1 or 2),
   the weighted share of each of the brief's four age groups, with SDOHWT21F and, as a check, PERWT21F. The implied
   overall rate is the sum of share x printed rate.
2. **Readings.** R2b's estimator, unchanged, run on records changed in one way each:
   `perwt` (PERWT21F in place of SDOHWT21F, same respondents); `m15_yes` (the item's -15 code, "cannot be
   computed", counted as yes); `m15_no` (-15 counted as no); `unweighted`; `agelast` (AGELAST in place of AGE31X).
   `spec` is R2b itself and must give R2b's tally (18 close, 2 exact of 40), or the run is not used.

## Predictions (graded exactly as written)

- **F1 (primary):** with the file's SDOHWT21F age shares, the printed age rates imply an overall rate of at least
  7.0%.
- **F2:** none of the five alternative readings brings at least 32 of #558's 40 graded cells (80%) close.
- **F3:** no alternative reading brings the total (printed 6.2) and all four age cells within 0.5 points at once.

F1 rests on the hand bound above, which assumed age shares the file has not yet given us. F2 and F3 say that the
gap is not explained by one simple choice. If a reading does explain it, we report that reading as the likely
documentation gap.

## Limits

Five readings chosen by us; the brief may combine several or use a choice we did not think of. One brief. No human
review. Any note to AHRQ waits for a human check.
