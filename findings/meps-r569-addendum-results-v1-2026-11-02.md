# Results: exploratory addendum to check R1 (MEPS Statistical Brief #569), v1

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r569-addendum-prereg-v1-2026-11-02.md` (tag v0.9.37, committed 2026-11-02 06:24
UTC, before the job read any microdata for it). Code: `meps/r569x.py` 0.1.0 (Apache-2.0). Text CC BY 4.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ
has not been contacted.

**This addendum does not regrade check R1.** R1's P2 (the headline exact) stays failed.

## Short answer

- **Figure 7 (region):** if region is taken from `REGION42`, the round-4/2 region (the round in which the
  self-administered questionnaire, the source of the scan question, is fielded), all four region cells
  reproduce to the published decimal. With it, 22 of the 24 cells are exact, and none of R1's 19 exact cells is
  lost. The end-of-year `REGION22` (R1's primary definition) gives 1 of 4. `REGION31` gives 2 of 4 and
  `REGION53` gives the same result as `REGION22`. In the pre-registered wording: **this definition choice
  reproduces the published Figure 7 values.** It does not show which variable AHRQ used.
- **The headline (Figure 2, 50+, 42.8%) and Figure 4's "Medicare and private" (72.4%)** are not reproduced by
  any region or age-variable variant. Selecting the 50+ group by the questionnaire's own age item (`ADAGE42` =
  4) does make the headline exact (42.780), but it loses 6 of R1's 19 exact cells. It is not a candidate under
  the pre-registered rule.
- **X1 (the only prediction) held:** weighting by the person weight instead of the questionnaire weight gives 0
  exact cells and 0 within 0.5 points. The brief's stated weight is clearly the right one.

## Run

Job `meps-r569x-v1`, exit 0: unit tests (`test_r569x`, `test_r569`), then the variants. `h243dta.zip`, 5,789,896
bytes, SHA-256 `7fc534de09eff5fd81facb74d61511d322ebe8bc45af7b75441204fcaf9fb454` (the same as R1; copied into
the job folder by MV2's hands). 22,431 persons. No missing columns.

## Gate

Variant A (R1's primary definition) reproduced R1 v1's 24 cells within 0.0005 points, with 19 exact. Passed.

## Variants (exact = rounds half-up to the published decimal; close = within 0.5 points)

| variant | change | exact | close | Figure 7 exact | R1 misses now exact | R1 exact cells lost |
|---|---|---|---|---|---|---|
| A | none (control) | 19 | 24 | 1 of 4 | - | - |
| REG42 | region from `REGION42` | **22** | 24 | **4 of 4** | F7a, F7b, F7c | none |
| REG31 | region from `REGION31` | 20 | 24 | 2 of 4 | F7c | none |
| REG53 | region from `REGION53` | 19 | 24 | 1 of 4 | none | none |
| C2 | 50+ cells by `ADAGE42` = 4 | 14 | 24 | 1 of 4 | F2a | F5b, F6a, F6b, F8a, F8b, F8c |
| AGE22 | age from `AGE22X` first | 19 | 24 | 1 of 4 | none | none |
| U3 | scan denominator keeps osteoporosis answer -15 | 4 | 20 | 0 of 4 | none | 15 cells |
| PW | person weight (negative control) | 0 | 0 | 0 of 4 | none | all 19 |

Readings, applied as written: **region**: REG42 accounts for Figure 7. **Candidates** (more than 19 exact, PW
excluded): REG42 (22) and REG31 (20). Neither loses any of R1's exact cells. **X1**: held (PW 0 < 19).

## Raw gaps for R1's five missed cells (recomputed minus published, percentage points)

| variant | F2a (42.8) | F4b (72.4) | F7a (44.1) | F7b (43.9) | F7c (42.1) |
|---|---|---|---|---|---|
| A | -0.0502 | +0.0694 | -0.0659 | +0.2292 | -0.1220 |
| REG42 | -0.0502 | +0.0694 | -0.0356 | +0.0350 | +0.0148 |
| REG31 | -0.0502 | +0.0694 | -0.0996 | +0.1740 | -0.0252 |
| REG53 | -0.0502 | +0.0694 | -0.0659 | +0.2292 | -0.1220 |
| C2 | -0.0197 | +0.0694 | -0.0556 | +0.3179 | -0.0863 |
| AGE22 | -0.0502 | +0.0694 | -0.0659 | +0.2292 | -0.1220 |
| U3 | -0.1473 | -0.7816 | +0.5990 | -0.2953 | -0.2121 |
| PW | +3.3243 | +1.5814 | +3.3183 | +3.7290 | +2.9453 |

Under REG42 the Figure 7 group sizes are 440, 560, 998 and 610 women (sum 2,608, the same as the Figure 2
headline group), against 438, 559, 1,003 and 608 with `REGION22`.

## What this does and does not show

- Brief #569 says region is "the location of residence" without naming a round. Read as region at the time of
  the questionnaire, it reproduces Figure 7 exactly from the public file. This is the kind of unstated choice a
  reproduction tool should surface. Here it is a choice the public file supports, not a missing variable.
- The headline still misses by 0.0002 points beyond the exact rule, and F4b by 0.019 points. Neither is
  explained by the variants we fixed in advance. We will not try further variants on #569 without a new dated
  pre-registration.
- After this addendum, the remaining gaps are at most 0.07 points. With the round-4/2 region, 22 of 24
  computable cells are exact; the two MSA cells are still not computable from HC-243.
- One brief, eight variants. A variant that reproduces a cell can still be the wrong explanation.

## Files

`meps-r569x-v1/r569x.json` (file hash, gate, per-variant summaries, readings, per-cell values),
`meps-r569x-v1/variants.csv`.
