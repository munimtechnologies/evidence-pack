# Pre-registration 3, results: spironolactone use and drinking in NHANES adults with hypertension

MV2 of Munim, Inc., 2026-10-15. Made with AI agents (Claude). Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

- **Plan:** `findings/spironolactone-nhanes-prereg-2026-10-15.md`, committed in b542be1 (2026-10-15 08:13:51Z).
- **Code:** `nhanes_spiro.py` (47b48e7, 08:13:58Z).
- **Run:** the job ran once, unchanged, in a sealed container on 2026-10-15 between 21:31 and 21:34Z. It downloaded the CDC files fresh and passed 10 of 10 offline tests.
- Nothing in the plan or code was changed after the data were read. Every number below is copied from the job's `results.json`.

## Answer

**By the pre-registered rule, H1 is supported, but the evidence is weak and fragile.**

Among NHANES adults with diagnosed hypertension who drank in the past year and had no reported heart failure or liver condition, the 70 spironolactone users reported fewer drinks per drinking day than the 5,055 users of other antihypertensives. After adjustment the difference was **−0.34 drinks per drinking day (95% CI −0.62 to −0.06; p 0.017)**. The upper bound is below 0, which is the plan's "supported" condition. The CI does not rule out a reduction as large as 0.5 drinks.

## Counts

| Cycle | Participants | Spironolactone users, any age | Eligible | Eligible on spironolactone |
|---|---:|---:|---:|---:|
| 2005-2006 | 10,348 | 37 | 465 | 3 |
| 2007-2008 | 10,149 | 49 | 636 | 7 |
| 2009-2010 | 10,537 | 56 | 732 | 14 |
| 2011-2012 | 9,756 | 39 | 636 | 6 |
| 2013-2014 | 10,175 | 52 | 721 | 10 |
| 2015-2016 | 9,971 | 48 | 685 | 8 |
| 2017-Mar 2020 | 15,560 | 106 | 1,250 | 22 |
| **Total** | **76,496** | **387** | **5,125** | **70** |

No eligible participant lacked an interview weight.

The plan expected spironolactone users "in the low hundreds". After exclusions there are only 70, so power is lower than planned.

| Group | n | Mean drinks/drinking day (unweighted) | Mean (weighted) | Heavy-day share (weighted) | Female | Mean age | Other antihypertensive ingredients |
|---|---:|---:|---:|---:|---:|---:|---:|
| Spironolactone | 70 | 1.86 | 1.59 | 5.5% | 60% | 62.5 | 2.20 |
| Comparator | 5,055 | 2.20 | 2.18 | 10.3% | 49% | 61.3 | 1.87 |

## Models

The coefficient is spironolactone minus comparator. All models have 233 clusters (cycle × stratum × PSU).

| Model | n (spironolactone) | β | 95% CI | p | Rule |
|---|---:|---:|---|---:|---|
| **Primary H1**: weighted, adjusted, drinks/drinking day | 5,125 (70) | **−0.340** | −0.619 to −0.062 | 0.017 | supported |
| S1: heavy-day level (linear probability) | 5,125 (70) | −0.024 | −0.079 to +0.032 | 0.40 | inconclusive |
| S2: spironolactone ≥ 90 days | 5,116 (61) | −0.518 | −0.764 to −0.272 | <0.001 | supported |
| S3: unweighted | 5,125 (70) | −0.195 | −0.561 to +0.171 | 0.30 | inconclusive |
| S4: unadjusted, weighted | 5,125 (70) | −0.586 | −0.895 to −0.277 | <0.001 | supported |

## How to read it

What points the same way as the health-record studies:
- The direction matches Palzes 2021 (Kaiser), Farokhnia 2022 (VA) and Loften 2026 (TriNetX). This sample comes from a different source, a national interview survey, and none of its participants appear in those studies.
- Longer use (S2) goes with a larger difference. This dose-response-like pattern was pre-specified, but it rests on 61 people.

Why it is weak:
- **Few exposed people.** Only 70 spironolactone users are in the sample, and the plan expected more. The unweighted model (S3) gives about half the effect, and its CI includes 0. The weighted result therefore leans on a few users with large survey weights. The plan said in advance that NHANES weights are not designed for subgroups this small.
- **Few treated clusters.** The 70 users fall in at most 70 of the 233 clusters. Cluster-robust standard errors can be too small when few clusters hold the exposure, so p = 0.017 may overstate the certainty.
- **No heavy-drinking signal.** The heavy-day share is lower in users (5.5% vs 10.3%), but the adjusted difference (S1) is small and its CI includes 0.
- **Confounding by indication remains.** In hypertension, spironolactone is mostly a fourth-line drug for resistant hypertension. Guidelines tell these patients to cut down on alcohol, so they may drink less because of that advice, whatever the drug does. The count of other antihypertensive ingredients is only a partial adjustment. The design is cross-sectional, so timing cannot be separated.
- **Selection.** The sample is past-year drinkers only. Anyone who stopped drinking altogether is missed.

## What follows

- A second, separately pre-registered set of checks (`findings/spironolactone-nhanes-followup-prereg-2026-10-15.md`) asks whether this result is specific and stable:
  - randomization inference within cycle × regimen strata;
  - restriction to regimens of 3 or more drugs (a resistant-hypertension proxy);
  - other antihypertensive drug groups as negative controls;
  - leave-one-cycle-out and leave-one-user-out refits.
- This result stays as stated above whatever those checks show.
- In MV2's ReGen evidence package on spironolactone for alcohol use disorder, it is cited as our own analysis (*), described as "consistent in direction, weak and fragile". It does not count as independent confirmation.

## Reproduce

```
pip install pandas numpy statsmodels
python nhanes_spiro.py --data-dir data --out-dir out
python -m unittest -v test_nhanes_spiro
```
