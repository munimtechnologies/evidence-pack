# Pre-registration 4 results: prazosin and doxazosin for alcohol use disorder, pooled only from ClinicalTrials.gov (2026-10-15, confirmed 2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0, code Apache-2.0. Research information, not medical advice.

**Status: final.** A sealed job (`alpha1-pool-v1`, 2026-10-16 05:11Z) re-downloaded all 8 registry records, matched every transcribed number to the posted value (`verify.md`: 8 of 8 match), and recomputed every pooled number. The pre-registered plan was committed before any outcome data were read: `findings/alpha1-blocker-aud-prereg-4-2026-10-15.md`.

## Answer

- **H1, do alpha-1 blockers reduce drinking compared with placebo? Inconclusive.**
  - Pooled over 8 trials (566 analysed): g = -0.078, 95% CI -0.266 to 0.110, p = 0.42.
  - HKSJ interval: -0.310 to 0.153. Prediction interval: -0.431 to 0.275.
  - tau^2 = 0.0116, I^2 = 16%, Q = 8.32 (p = 0.31).
- **H2, is the benefit smaller in samples that required PTSD for entry? Not supported.**
  - PTSD-required trials (3): g = -0.117. General trials (5): g = -0.085 (tau^2 = 0.0016).
  - Difference (comorbid minus general): -0.031, SE 0.236, p = 0.89. With three comorbid trials this test is weak, as the plan said.
- The registry-only estimate (-0.08) is much smaller than the 2021 meta-analysis of published studies (SMD -0.32 for consumption, PMID 32959918). The trial sets and outcomes differ, so the two don't directly contradict each other. Still, the published estimate is not reproduced from registry data.

## Trials and effects (g < 0 favours the drug)

| NCT | trial | outcome used (posted) | window vs treatment | n drug/placebo | g | SE |
|---|---|---|---|---|---|---|
| NCT00762710 | prazosin 16 mg, 12 wk | % heavy drinking days, final medication week | on | 40/40 | -0.382 | 0.226 |
| NCT02989493 | doxazosin, 8 wk | any heavy drinking day (17/29 vs 21/32), 8 wk | on | 29/32 | -0.164 | 0.292 |
| NCT01916941 | prazosin, 6 wk | drinks per week, weeks 4-6 | on | 18/18 | +0.197 | 0.334 |
| NCT00585780 | prazosin by withdrawal stratum, 12 wk | % heavy drinking days, weeks 3-12 (strata combined) | on | 55/45 | +0.144 | 0.201 |
| NCT02322047 | prazosin x naltrexone factorial, veterans, 42 days | change in % heavy drinking days, baseline to visit 8 (LS means) | **mixed** | 14/15 | -0.278 | 0.373 |
| NCT02500602 | doxazosin, PTSD required, 12 wk | % heavy drinking days, 12 wk | on | 74/70 | -0.042 | 0.167 |
| NCT01518972 | prazosin, PTSD required | % heavy drinking days per week, 6 wk (95% CIs) | on | 9/11 | -0.954 | 0.474 |
| NCT00744055 | prazosin, PTSD required, 12 wk | drinking days, 12 wk | on | 50/46 | +0.102 | 0.204 |

## Treatment-window check (added 2026-10-16)

After we found post-treatment and mixed windows in two of our own earlier pools (`findings/registry-pools-treatment-window-audit-2026-10-16.md`), every row here was checked against the posted dosing schedule and outcome time frame.

- **7 rows are on treatment.**
- **NCT02322047 is mixed.** Dosing runs days 1-42. The Form-90 window runs from baseline to visit 8, which the record says "occurred 35 to 76 days after visit 2 with the average of 45 days". For some participants, the window includes up to about 5 weeks off medication. Without this trial, the main pool is k = 7, g = -0.069 (95% CI -0.275 to 0.137; HKSJ -0.337 to 0.199). H1 and H2 are unchanged.
- **A record inconsistency, not a window problem:** NCT01518972's arm text gives a dosing schedule to day 84 (copied word for word from NCT00762710), but its outcomes are posted at 6 weeks. A 6-week outcome is on treatment under either reading.

## Deviations from the plan, all listed

1. **NCT02226367 was dropped on reading.** Its only posted outcome is the Penn Alcohol Craving Scale, not a drinking outcome. The plan said it would be included only if it qualified, so it stays out of every analysis.
   - A side note for the registry audit: its posted SEs (4.1 with n = 46 and 6.4 with n = 56) imply SDs of about 28 and 48 on a 0-30 scale. The second is wider than the scale itself, even for a change score. They are probably SDs labelled as SEs. This led to a new check in the census tool (`ctgov_audit.py` v0.4, se_implies_sd_above_width).
2. **NCT02989493** posts only the number of participants with any heavy drinking day. It is used as a binary heavy-drinking outcome (Chinn 2000 conversion). That is the first rung of the hierarchy, since it is the only drinking outcome posted.
3. **NCT01916941** posts two windows. The later one (weeks 4-6) was used, under the "last on-treatment time point" rule. Weeks 2-4 point the other way (13.65 vs 14.55 drinks).
4. We expected 6-9 trials and 600-750 participants, and got 8 trials and 566 analysed.
5. **The treatment-window check above was not in the plan.** It was added afterwards, for all our registry pools.
6. **One test expectation was wrong.** The plan's test file expected tau^2 = 0 for the general subgroup. The job gave 0.0016, because Q = 4.09 on 4 df, just above its degrees of freedom. A hand recheck agrees (0.0015). The test was corrected; no number in this file changed.

## Pre-registered sensitivity analyses and exploratory checks (all from the job)

- **Second outcome in the hierarchy**, where a trial posts two: k = 8, g = +0.027 (95% CI -0.153 to 0.207). General g = -0.007, comorbid g = +0.065. Every trial that changes moves toward placebo, so H1 stays inconclusive.
- **E1, drug:** doxazosin (2 trials) g = -0.072 (95% CI -0.356 to 0.212); prazosin (6 trials) g = -0.100 (-0.381 to 0.180). There is no sign of a difference.
- **E2, withdrawal strata in NCT00585780 (exploratory):**
  - High withdrawal: prazosin 8.2% vs placebo 27.1% heavy drinking days, g = -0.61.
  - Low withdrawal: prazosin 31.3% vs placebo 7.3%, g = +0.67.
  - The published paper (Sinha 2021, PMID 33207935) reports benefit in the high stratum and "no such benefit" in the low stratum. The posted low-stratum means show heavier drinking on prazosin, which the paper's wording does not say. The paper's high-stratum numbers (7.07% vs 35.58%) also differ from the posted ones, probably because they come from a model. This trial is the largest single source of spread in the general pool.
- **E3, NCT02322047 as prazosin + placebo vs double placebo only:** g = +0.10 (7 vs 8 participants). Main pool g = -0.059 (95% CI -0.246 to 0.129).
- **E4, leave-one-out:** every leave-one-out estimate lies between -0.125 and -0.017, and every 95% CI crosses zero.

## The reporting gap

Five alpha-1 blocker AUD trials listed as completed or ended have **no posted results**: NCT04793685 (Yale, n = 152), NCT01437046 (Brown, n = 41), NCT00167687 (University of Washington, n = 23), NCT04108104 (prazosin-cyproheptadine combination, n = 154) and NCT02193256 (n = 5). Together they enrolled about 375 people, two-thirds of the 566 analysed here. Some may be published in journals, but none can be checked against the registry.

## What this adds to the comorbid-sample question

This was the fourth pre-registered test of whether AUD drugs work less well in samples selected for a second condition. That pattern was first seen *after the fact* for topiramate (+0.47) and gabapentin (+0.55).

- The job's six-list comparison (all six drugs, fixed effect) gives an average difference of +0.168 (SE 0.068, p = 0.014), with Q = 12.63 on 5 df (p = 0.027). That average is driven by the two lists where the pattern was first noticed, so it **cannot count as confirmation**.
- **The four pre-registered tests alone** (naltrexone -0.125, SE 0.131; acamprosate +0.108, SE 0.202; varenicline +0.181, SE 0.144; alpha-1 blockers -0.031, SE 0.236) pool to **+0.02 (SE 0.08, 95% CI -0.14 to +0.18)**. This is a fixed-effect inverse-variance average computed by hand from the job's per-list differences.
- **Plain reading: the comorbid-sample pattern did not replicate in four prospective tests.** The two original signals stay as hypotheses that came from the data. The gabapentin one is also weakened by its own treatment-window correction (`findings/gabapentin-aud-correction-2026-10-16.md`).

## Limits

- The posted outcomes differ between trials (heavy drinking days, drinks per week, drinking days, a binary). Standardizing them assumes they measure the same thing.
- Least-squares and model-based SEs and CIs were converted to SDs as if they came from plain means, which can misstate the SDs.
- Small trials (9-18 per arm) give large, unstable effects. NCT01518972 alone moves the comorbid estimate.
- Registry results are what sponsors posted, and they can differ from the papers.

## Reproduce

`python regpool.py studies/alpha1_aud.json --out-dir out --verify --compare general comorbid` (evidence-pack, Apache-2.0). Tests: `python -m unittest -v test_alpha1` (11 tests; use the 2026-10-16 version of `test_alpha1.py`).
