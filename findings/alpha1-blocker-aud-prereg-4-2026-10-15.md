# Pre-registration 4: prazosin and doxazosin for alcohol use disorder, pooled only from ClinicalTrials.gov results (2026-10-15)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Text CC BY 4.0. Research information, not medical advice.

This file is committed **before any outcome data of these trials are read**. It is based only on what ClinicalTrials.gov records say about the design of each trial, fetched on 2026-10-15:
- the search listing (NCT id, title, status, phase, enrollment, sponsor, conditions, masking, has-results flag);
- the eligibility criteria and arm descriptions of the trials classified below.

No results section, publication or abstract of these trials was opened.

## Why

Prazosin and doxazosin are generic alpha-1 adrenergic antagonists labeled for hypertension (and, for doxazosin, benign prostatic hyperplasia). Noradrenergic signalling through alpha-1 receptors is linked to stress-driven drinking and alcohol withdrawal.

Prior art:
- The only pooled estimate we found is a 2021 meta-analysis of published studies (Addiction 2021; PMID 32959918). It reported that prazosin and doxazosin reduced alcohol consumption (SMD -0.32, 95% CI -0.56 to -0.07) but not abstinence or heavy drinking days.
- PubMed, 2026-10-15: 7 records for alpha-1 blockers + alcohol + systematic review/meta-analysis, none registry-only and none testing PTSD comorbidity.

What is new here:
1. Registry-only pooling. Unpublished and later-posted trials count, and the input numbers can be re-checked by anyone against the registry.
2. A pre-registered test of whether the benefit differs between samples that required PTSD for entry and samples that did not. This is the fourth test of the comorbid-sample split MV2 found post hoc for topiramate and gabapentin. It failed the pre-registered test on naltrexone, and the acamprosate/varenicline test is pending.
3. A count of completed alpha-1 blocker AUD trials that never posted results.

This is also the own-analysis section (*) of a planned NCATS ReGen Drugs evidence package.

## Search

ClinicalTrials.gov API v2, `query.cond=alcohol&query.intr=prazosin OR doxazosin`, 2026-10-15: 21 records, 11 with posted results.

## Inclusion and outcome rules (the same as the naltrexone, acamprosate and varenicline pools)

- **Include:** randomized, parallel-group trials of prazosin or doxazosin against placebo, the alpha-1 blocker being the only difference between the arms compared, with at least 4 weeks of treatment and a posted drinking outcome.
- **Exclude:** crossover, lab-paradigm, single-dose, withdrawal-treatment, healthy-volunteer, open-label and single-arm studies.
- **Outcome**, first available in this order, at the last on-treatment time point:
  1. heavy drinking days (percent or count);
  2. drinks per drinking day, or drinks per week or per day;
  3. drinking days (percent or count);
  4. abstinence (binary, "good" event).

  Change from baseline is used when only change is posted. Median/IQR is converted as in regpool.py (Wan 2014). SE and 95% CI are converted to SD.
- **Effect:** Hedges' g, signed so that negative favours the drug; DerSimonian-Laird random effects (regpool.py, evidence-pack v0.4.0).
- A trial listed below that fails inclusion on reading is dropped with the reason. It is never moved between groups.

## Classification (from eligibility criteria only)

"Comorbid" means the eligibility criteria require a condition other than an alcohol diagnosis.

**General** (no other condition required; NCT00762710 and NCT01916941 exclude PTSD):
- NCT00762710: prazosin 16 mg/day, 12 weeks, n = 92.
- NCT02989493: doxazosin, target 8 mg, 8 weeks, n = 61.
- NCT01916941: prazosin 16 mg/day, 6 weeks, n = 36.
- NCT00585780: prazosin 16 mg/day, 12 weeks, n = 100, randomized within high and low withdrawal strata. Main pool: both prazosin arms vs both placebo arms.
- NCT02322047: veterans; prazosin x naltrexone factorial, 6 weeks, n = 31. Main pool: the two prazosin arms vs the two non-prazosin arms (`groups`).
- NCT02226367: active-duty soldiers in the Army Substance Abuse Program, with or without PTSD; prazosin up to 20 mg/day, n = 158. Included only if treatment lasted at least 4 weeks.

**Comorbid** (current PTSD required for entry):
- NCT02500602: doxazosin up to 16 mg/day, about 12 weeks, n = 144 (VA).
- NCT01518972: prazosin, 12-week medication phase, n = 30.
- NCT00744055: prazosin 16 mg/day, n = 96.

**Excluded, with the reason:**
- NCT02966340: single 2 mg dose, crossover, screening purpose.
- NCT00240227: crossover; alcohol or cocaine dependence; abstinent at entry; terminated at n = 8.
- NCT02655354: pragmatic trauma-care trial, not an alpha-1 blocker comparison.

**Completed or ended without posted results** (reported as a reporting gap, not pooled):
- NCT04793685 (Yale, prazosin for AUD with withdrawal symptoms, phase 2, n = 152, listed completed);
- NCT01437046 (Brown, doxazosin, n = 41);
- NCT00167687 (University of Washington, prazosin, n = 23);
- NCT04108104 (KT-110, a prazosin-cyproheptadine combination, n = 154; not a single-drug comparison in any case);
- NCT02193256 (n = 5, lab).

Also not pooled: NCT04135846 (Brown, active, not recruiting), NCT06147622 (pharmacokinetics), NCT03398252 (withdrawn) and NCT02616094 (imaging, non-randomized).

## Hypotheses and decision rules

**H1 (primary): alpha-1 blockers reduce drinking against placebo.** Main pool = all included general and comorbid trials.
- **supported** if the DL 95% CI lies wholly below 0;
- **contradicted** if it lies wholly above 0;
- **inconclusive** otherwise.

The HKSJ interval and prediction interval are reported. If DL excludes 0 and HKSJ does not, the label is "supported, not robust to HKSJ".

**H2 (comorbid split, fourth test):** g(comorbid, PTSD required) minus g(general) is above 0, meaning less benefit in PTSD samples. `regpool.py --compare general comorbid`, two-sided p < 0.05 = replicates; otherwise not supported. With 3 comorbid trials this test is weak, and a null does not show the populations respond alike. The difference also joins the cross-drug Q test with the earlier lists.

**Exploratory, labelled as such:**
- E1: prazosin vs doxazosin;
- E2: in NCT00585780 only, high vs low withdrawal strata, if posted separately;
- E3: sensitivity for NCT02322047 using prazosin + placebo vs placebo + placebo only;
- E4: leave-one-out.

## Sensitivity analyses fixed now

- Main pool without NCT02226367 (a military sample; PTSD neither required nor excluded).
- Main pool using the second outcome in the hierarchy when a trial posts both.

## Power, honestly

Expect 6-9 usable trials and about 600-750 participants in total. A true g of -0.3 would give a pooled 95% CI of about ±0.15 (SE ≈ √(4/650)) with low heterogeneity, so "supported" is reachable. With moderate heterogeneity it may not be. Posted registry results often use different outcomes than the papers, so our estimate can differ from the 2021 meta-analysis for reasons other than the trials added.

## What happens next

1. Next run: transcribe each included trial's posted outcome into `studies/alpha1_aud.json`.
2. Run `regpool.py --verify` against the registry.
3. Publish the result under `findings/` whatever it shows, with every deviation from this file listed as a deviation.
