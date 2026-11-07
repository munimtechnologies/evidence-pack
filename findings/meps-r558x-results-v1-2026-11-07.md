# Results: MEPS Statistical Brief #558, internal consistency of Figure 1 and five alternative readings (addendum r558x to check R2b, v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code `meps/r558x.py` 0.1.0 (Apache-2.0). Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

Pre-registration: `findings/meps-r558x-prereg-v1-2026-11-07.md` (tag v0.9.49). Job `meps-r558x-v1` cloned tag
v0.9.49, ran the unit tests (`meps.test_r558x`, `meps.test_r2b`: pass), checked the SHA-256 of HC-233
(`h233dat.zip`, 8,354,598 bytes, `07cb5aa2...05ba`, the same file as R2b), passed all 22 codebook gates and ran on
2026-11-07 09:08-09:12 UTC. Its output is `findings/meps-r558x-v1/r558x.json`, copied unchanged.

## Gate

R2b's estimator, unchanged (`spec`), gave R2b's tally again: 18 of 40 graded cells within 0.5 points, 2 exact
(`spec_matches_r2b`: true). The run is used.

## 1. Consistency of Figure 1

Base as in R2b: adults (AGE31X >= 18) with SDOHWT21F > 0 who answered the transportation item (18,196 records).

| Age group | Share, SDOHWT21F (%) | Share, PERWT21F (%) | Printed rate (%) |
|---|---|---|---|
| 18-34 | 29.39 | 27.56 | 11.1 |
| 35-49 | 24.05 | 24.18 | 9.2 |
| 50-64 | 24.69 | 25.57 | 6.1 |
| 65+ | 21.87 | 22.70 | 4.3 |
| Implied overall rate | **7.92** | 7.82 | printed Total **6.2** |

Hand check of the SDOHWT21F row: 0.2939 x 11.1 + 0.2405 x 9.2 + 0.2469 x 6.1 + 0.2187 x 4.3 = 3.263 + 2.212 +
1.506 + 0.940 = 7.92.

With the file's own age mix, the four printed age rates average to 7.9%, not 6.2%. Even with all four rates at the
bottom of their rounding (11.05, 9.15, 6.05, 4.25) the average is 7.87. The printed Total and the printed age rates
cannot both describe the same adults.

## 2. Five alternative readings

| Reading | Close (of 40) | Exact | Total | 18-34 | 35-49 | 50-64 | 65+ |
|---|---|---|---|---|---|---|---|
| Printed | | | 6.2 | 11.1 | 9.2 | 6.1 | 4.3 |
| `spec` (R2b) | 18 | 2 | 5.60 | 6.46 | 5.89 | 4.96 | 4.83 |
| `perwt` | 18 | 3 | 5.60 | 6.59 | 5.86 | 5.12 | 4.65 |
| `m15_yes` | 6 | 1 | 6.49 | 6.82 | 6.60 | 6.11 | 6.37 |
| `m15_no` | 21 | 3 | 5.54 | 6.44 | 5.84 | 4.90 | 4.75 |
| `unweighted` | 9 | 1 | 6.52 | 7.29 | 7.01 | 7.15 | 5.06 |
| `agelast` | 18 | 2 | 5.60 | 6.58 | 5.70 | 4.99 | 4.94 |

No reading comes near the printed age gradient (11.1 for ages 18-34 against at most 7.3 here).

## Predictions, graded exactly as written

| | Prediction | Result | |
|---|---|---|---|
| F1 (primary) | with SDOHWT21F age shares, the printed age rates imply an overall rate of at least 7.0% | 7.92% | **held** |
| F2 | no alternative reading brings at least 32 of 40 cells close | best: `m15_no`, 21 | **held** |
| F3 | no alternative reading brings the Total and all four age cells within 0.5 at once | none (closest on the Total: `m15_yes` 6.49 and `unweighted` 6.52, both far off on 18-34) | **held** |

3 of 3 held.

## What this adds up to

- Brief #558 (transportation barriers, 2021) Figure 1 is inconsistent with itself: its age rates imply an overall
  rate near 7.9% for the population the brief describes, against a printed Total of 6.2%. Which numbers are wrong
  cannot be told from the page or the file. Our recompute agrees with neither the printed Total (5.60 against 6.2) nor
  the printed age rates, so the brief probably used a definition or population we have not identified.
- The gap is not one simple choice of weight, age variable or missing-data code (F2, F3).
- Census M7 (`findings/meps-m7-totals-results-v1-2026-11-07.md`) showed why a share-free check misses this: the
  printed Total 6.2 lies inside the age range 4.3-11.1, so only the file's age shares reveal the problem.

## Limits

One brief. Five readings chosen by us; the brief may combine several choices or use one we did not think of. The
consistency argument uses the base as R2b defined it; a different universe would give different shares, but every
plausible adult age mix gives an average of at least 7.29 (hand bound in the pre-registration). No human review.
Any note to AHRQ waits for a human check.
