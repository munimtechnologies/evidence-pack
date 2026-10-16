# Correction to the gabapentin registry pool (2026-10-16)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0.

This note corrects three things: [gabapentin-aud-registry-pool-2026-10-14.md](gabapentin-aud-registry-pool-2026-10-14.md), the README summary table, and one sentence in [naltrexone-aud-registry-pool-2026-10-15.md](naltrexone-aud-registry-pool-2026-10-15.md). The earlier files are left as they were, so the record stays readable; this note says what was wrong. A check of every row in all seven of MV2's AUD registry lists, done after this was found, is in [registry-pools-treatment-window-audit-2026-10-16.md](registry-pools-treatment-window-audit-2026-10-16.md).

## What was wrong

**1. One pooled trial measured drinking only after the drug had stopped.** The trial is [NCT01014533](https://clinicaltrials.gov/study/NCT01014533?tab=results) ("Pharmacotherapy and Mechanisms of Sleep Disturbance in Alcohol Dependence", University of Michigan, 59 enrolled). We read it on 2026-10-16 from the ClinicalTrials.gov API v2:
- **Dosing lasted about 10 nights**, not weeks. Gabapentin was 600 mg at bedtime on nights 1-2, 1,200 mg on nights 3-10 and 600 mg on night 11, then stopped. Placebo followed the same schedule.
- **Its primary outcomes are sleep measures** (stage 2 sleep and wake after sleep onset), with the time frame "1 week".
- **The drinking outcome we used is a secondary outcome measured after the drug stopped.** "Relapse to Any Drinking" is defined as drinking "from end of sleep laboratory study (night 10) to twelve weeks later" (gabapentin 14/25, placebo 13/24).

So its g of +0.041 measures whether 10 nights of gabapentin carried over into the next 12 weeks. The finding said "Durations run from 8 to 16 weeks", which is wrong for this trial.

**2. A second trial's outcome window runs mostly after gabapentin stopped.** In [NCT00183196](https://clinicaltrials.gov/study/NCT00183196?tab=results) (Anton 2011), the record says "gabapentin (up to 1200 mg/day in divided doses) for the first 6 weeks", added to 16 weeks of naltrexone. The outcome we pooled is time to relapse over "16 weeks". That means 10 of the 16 weeks fall after gabapentin ended. The finding mentioned that the paper's benefit came in the 6 weeks gabapentin was given, but it still pooled the 16-week outcome in the main analysis.

## What changes

The first two rows below are output of the same sealed job ([gabapentin-aud-pool-output-2026-10-14.md](gabapentin-aud-pool-output-2026-10-14.md), leave-one-out section); nothing was re-run. The rows marked *by hand* were computed from that job's per-trial g and SE with regpool.py's method; the next sealed run will confirm them.

| Pool | k | g (95% CI) | HKSJ 95% CI |
|---|---|---|---|
| As published: all generic-gabapentin trials | 6 | -0.360 (-0.659 to -0.062) | -0.757 to +0.037 |
| **Corrected: NCT01014533 removed** (job) | 5 | **-0.437 (-0.754 to -0.119)**, p = 0.007 | **-0.883 to +0.010** |
| Outcome windows fully on treatment (NCT01014533 and NCT00183196 removed), *by hand* | 4 | -0.565 (-0.950 to -0.180) | -1.189 to +0.060 |
| General AUD samples, as published | 4 | -0.511 (-0.836 to -0.186) | -1.015 to -0.006 |
| General AUD samples, on treatment only, *by hand* | 3 | -0.759 (-1.167 to -0.352) | see note |
| Samples with another condition, corrected | 1 | +0.029 (one 30-person pilot, NCT04052139) | n/a |

The draft of this note said the HKSJ interval for the five-trial pool had not been computed. It had: the job's leave-one-out section reports it as -0.883 to +0.010.

**Reading.**
- With the more cautious HKSJ interval, the corrected pool still narrowly crosses zero, exactly as the published six-trial pool did.
- Removing off-drug weeks makes the point estimate larger, not smaller.
- In the three-trial on-treatment general pool, the trials agree almost exactly (Q = 0.007). This makes its HKSJ interval implausibly narrow (-0.813 to -0.706), so read the DerSimonian-Laird interval instead.

**The "comorbid split" for gabapentin no longer has support from more than one trial.** The finding said the effect "vanishes in the two trials of people with another condition". After the correction, only one 30-person pilot is left on that side: people with HIV and chronic pain, with drinking as a secondary outcome. The naltrexone note's cross-drug table gave gabapentin's comorbid-minus-general difference as +0.55 (SE 0.29). Recomputed by hand from the job's subgroup rows, it is about +0.54 (SE about 0.40), and it rests on that single pilot. So "The split is real enough in the two anticonvulsant pools" should read: "the split is clear in the topiramate pool; in the gabapentin pool it rests on one small pilot." The pre-registered tests (naltrexone; acamprosate and varenicline) did not use gabapentin data, so their results are unchanged.

## How it was found

The error came up during a routine reference check of MV2's draft gabapentin evidence package. That draft cited a paper as "likely" reporting NCT01014533: Hoffman et al., J Addict Med 2024, PMID 38828963. It turned out to analyse a different trial, with 90 people with alcohol withdrawal given up to 1,200 mg/day for 16 weeks. That matches Anton et al. 2020 (NCT02349477). Reading NCT01014533's arms to settle the question showed the 10-night schedule. The public finding never cited Hoffman 2024; only the private draft did, and that draft has been corrected too. The Anton 2011 window turned up in the full audit that followed.

## Rule we now follow

Before a registry trial enters a pool, we read its arms' dosing schedule and the time frame of the outcome used. Each row is recorded as on, mixed or after treatment. Main analyses use rows that are on treatment, and mixed rows go to sensitivity analyses. Under this rule, the gabapentin main estimate becomes the four-trial on-treatment pool once a sealed run of `regpool.py` confirms the hand calculation. Until then, the job-computed five-trial pool is the corrected figure.
