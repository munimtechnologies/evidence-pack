# Pre-registration 3b, results: the NHANES spironolactone-drinking result is not robust

MV2 of Munim, Inc., 2026-10-16. Made with AI agents (Claude). Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

- **Plan:** `findings/spironolactone-nhanes-followup-prereg-2026-10-15.md`, written 2026-10-15 at about 22:45Z, after the primary result was seen and before any of these checks ran. It is published together with this file, not before it; its status note says so.
- **Code:** `spiro_followup.py`, which reuses the unchanged `nhanes_spiro.py`.
- **Run:** job spiro-followup-v1 ran once, unchanged, in a sealed container on 2026-10-16 between 08:59 and 09:02Z. It downloaded the CDC files fresh and passed 20 of 20 offline tests (10 for each module).
- Every number below is copied from the job's `results.json`.

## Answer

**By the plan's own rule the overall label is "not robust".** Randomization inference does not support the result (p 0.134), and restricting to people on 3 or more antihypertensive drugs shrinks it and loses it. The negative-control drug groups show no sign of a general bias, and no single user drives it, but leaving out either of two survey cycles also loses it.

The primary result of pre-registration 3 (β −0.34 drinks per drinking day, 95% CI −0.62 to −0.06) stands as published. This file only adds the checks that say how much weight it can bear: not much.

## Rebuild

The rebuilt sample reproduces the primary model exactly: n 5,125, 70 spironolactone users, β −0.3404, and 0 mismatches in the other rows.

## Checks

| Check | What it does | Result | Plan's reading |
|---|---|---|---|
| **E1** randomization inference | spironolactone label shuffled within cycle × number of other antihypertensives, 2,000 times (seed 20261015) | 268 of 2,000 shuffles at least as extreme; **p = 269/2,001 = 0.134** | fails (needs p < 0.05) |
| **E2** regimens of 3+ ingredients | resistant-hypertension proxy; n 1,196 (51 users) | **β −0.189 (−0.509 to +0.131)**, p 0.25 | fails (upper bound must be < 0) |
| **E3** negative-control drug groups | each group in place of spironolactone, among non-users | all three near 0 (table below) | no evidence against specificity |
| **E4** leave one cycle out | 7 refits | 5 supported, **2 inconclusive** (without 2007-2008; without 2015-2016) | fragile |
| **E5** leave one user out | 70 refits | **70 of 70 supported**; β −0.410 to −0.296; highest upper bound −0.016 | not fragile |

### E3 in detail

| Group (exposed count) | β | 95% CI | p |
|---|---:|---|---:|
| NC1 central agents and vasodilators (164): clonidine, methyldopa, hydralazine, minoxidil | +0.026 | −0.302 to +0.353 | 0.88 |
| NC2 other potassium-sparing diuretics (221): amiloride, triamterene | +0.004 | −0.204 to +0.212 | 0.97 |
| NC3 loop diuretics (255): furosemide, bumetanide, torsemide | −0.011 | −0.210 to +0.188 | 0.91 |
| A1 alpha-1 blockers (160), not a negative control | −0.101 | −0.385 to +0.183 | 0.49 |

### E4 in detail

| Left out | n (users) | β | 95% CI | Decision |
|---|---|---:|---|---|
| 2005-2006 | 4,660 (67) | −0.367 | −0.655 to −0.078 | supported |
| 2007-2008 | 4,489 (63) | −0.300 | −0.610 to +0.010 | inconclusive |
| 2009-2010 | 4,393 (56) | −0.414 | −0.711 to −0.117 | supported |
| 2011-2012 | 4,489 (64) | −0.331 | −0.627 to −0.034 | supported |
| 2013-2014 | 4,404 (60) | −0.400 | −0.685 to −0.115 | supported |
| 2015-2016 | 4,440 (62) | −0.159 | −0.452 to +0.133 | inconclusive |
| 2017-March 2020 | 3,875 (48) | −0.425 | −0.749 to −0.100 | supported |

## How to read it

- **The cluster-robust p-value was too optimistic, as the primary file warned.** With 70 exposed people spread over at most 70 of 233 clusters, the design-based p of 0.017 becomes 0.134 once the label is shuffled within strata. A difference this size turns up in about 1 in 7 random relabellings.
- **The restriction to 3+ drugs cuts the estimate roughly in half** (−0.19 vs −0.34). That is what confounding by indication would predict if spironolactone users differ from the comparator mainly by having harder-to-treat hypertension. It is also what lower power would give (51 users). The check cannot tell these apart.
- **The negative controls are reassuring, within their limits.** Three drug groups taken by more people than spironolactone (164-255), including one also used as an add-on in resistant hypertension (NC1), show differences of about zero. So there is no sign that "users of any extra antihypertensive drink less". Their intervals still include −0.3, so this does not prove that the association is specific to spironolactone.
- **No single person drives it, but two survey cycles each matter.** Without the 8 users of 2015-2016 the estimate falls to −0.16. Under the plan's rule, either cycle being decisive makes the result fragile.
- **Alpha-1 blockers** (doxazosin, prazosin, terazosin; reported separately because they have their own alcohol hypothesis, pre-registration 4) point the same way but weakly (−0.10, CI −0.39 to +0.18).

## What changes

- In MV2's evidence package on spironolactone for alcohol use disorder, the NHANES analysis is now described by its pre-registered label: **"consistent in direction, not robust"**. It is not counted as independent support.
- The package's main evidence remains the three health-record cohorts (Kaiser Permanente, VA, TriNetX), all from one research collaboration. An independent cohort or a randomized trial is still what the question needs. A phase 1 study is recruiting (NCT05807139).
- Nothing here re-decides pre-registration 3. Both files stay as written.

## Reproduce

```
pip install pandas numpy statsmodels
python spiro_followup.py --data-dir data --out-dir out
python -m unittest -v test_spiro_followup test_nhanes_spiro
```
