# Naltrexone for alcohol use disorder, from registry results alone, and a pre-registered test that failed (2026-10-15, preliminary)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

**Status: preliminary.** The 17 trials' numbers were transcribed by hand from the ClinicalTrials.gov API v2 on 2026-10-15, and the pooled numbers below were computed by hand. A sealed job (`regpool.py --verify --compare general comorbid`, queued) recomputes everything from `studies/naltrexone_aud.json` and re-downloads every record so that each transcribed number can be checked against the registry. This note will be replaced by the job's numbers. Small differences are possible. A change in the conclusion is unlikely, but it would be reported here.

## Why naltrexone

MV2's registry-only pools found the same pattern for two drugs. Topiramate worked in general AUD samples (g -0.57, k = 4) and barely at all in samples selected for another condition as well (g -0.10, k = 5). Gabapentin showed the same: -0.51 (k = 4) against +0.04 (k = 2). Both splits were found after the data had been seen. Before claiming a general pattern, it had to survive a test fixed in advance on a third drug with a different mechanism. Naltrexone, an opioid antagonist with many registry-posted trials, is that test.

## The pre-registration

[naltrexone-prereg-2026-10-15.md](naltrexone-prereg-2026-10-15.md) fixed the hypothesis, inclusion rule, outcome rule and the general/comorbid label of every trial. It was written from the search listing alone (NCT id, title, phase, enrollment, conditions), before any naltrexone outcome data were opened. It is committed in this repository next to this note. Both were committed in the same session, so the claim that it came first rests on our word, not on a timestamp. The next pre-registration will be committed before any data are read. The prediction: g(general) more negative than g(comorbid).

## Search and selection

ClinicalTrials.gov API v2, `query.cond=alcohol&query.intr=naltrexone`, results posted: 60 records. The pre-registration kept 25 randomized naltrexone-vs-placebo trials. Reading the posted results then dropped 8, each for a reason fixed in advance: lab-only or very short outcomes (NCT02026011, NCT00366626, NCT00656630, NCT00817089), no posted drinking outcome (NCT00511836, NCT00338962, NCT01723384), and results posted only within strata without per-arm counts (NCT01296646). No trial moved between groups.

17 trials remain (2,499 participants in the arms used): 6 in general AUD samples and 11 in samples selected for something else as well (bipolar disorder, PTSD, cocaine dependence, HIV, prisoners with HIV, men who have sex with men who binge drink, homelessness, young adults).

| NCT | Trial | Group | Posted outcome used | n (NTX/placebo) | g |
|---|---|---|---|---|---|
| [NCT01218958](https://clinicaltrials.gov/study/NCT01218958?tab=results) | ALK21-003, XR-NTX 190 + 380 mg | general | % heavy drinking days, 24 wk (median/IQR) | 407/204 | -0.25 |
| [NCT00501631](https://clinicaltrials.gov/study/NCT00501631?tab=results) | ALK21-014, XR-NTX after enforced abstinence | general | no heavy drinking days, 12 wk | 152/148 | +0.15 |
| [NCT00831272](https://clinicaltrials.gov/study/NCT00831272?tab=results) | OPRM1 pharmacogenetic trial | general | % heavy drinking days, 12 wk | 111/110 | -0.19 |
| [NCT00920829](https://clinicaltrials.gov/study/NCT00920829?tab=results) | A118G genotype trial | general | % heavy drinking days, month 4 | 73/73 | -0.29 |
| [NCT01211769](https://clinicaltrials.gov/study/NCT01211769?tab=results) | omega-3/6 factorial | general | drinking days, month 3 | 20/20 | +0.11 |
| [NCT00667875](https://clinicaltrials.gov/study/NCT00667875?tab=results) | naltrexone + aripiprazole trial | general | % heavy drinking days, 16 wk | 21/20 | +0.30 |
| [NCT00302133](https://clinicaltrials.gov/study/NCT00302133?tab=results) | bipolar disorder | comorbid | drinks per drinking day | 8/8 | -0.94 |
| [NCT00006489](https://clinicaltrials.gov/study/NCT00006489?tab=results) | PTSD, x prolonged exposure | comorbid | % drinking days, week 24 | 82/83 | -0.43 |
| [NCT00777062](https://clinicaltrials.gov/study/NCT00777062?tab=results) | cocaine + alcohol, XR-NTX | comorbid | abstinent, 8 wk | 39/41 | +0.32 |
| [NCT00142818](https://clinicaltrials.gov/study/NCT00142818?tab=results) | cocaine + alcohol, x modafinil | comorbid | % heavy drinking days | 85/79 | +0.04 |
| [NCT01625091](https://clinicaltrials.gov/study/NCT01625091?tab=results) | women with HIV | comorbid | quit hazardous drinking, month 4 | 85/87 | -0.15 |
| [NCT01245647](https://clinicaltrials.gov/study/NCT01245647?tab=results) | HIV pilot | comorbid | drinks per week, month 4 | 8/7 | -0.11 |
| [NCT01227044](https://clinicaltrials.gov/study/NCT01227044?tab=results) | heavy drinkers with HIV | comorbid | heavy drinking days, week 12 | 19/21 | -1.11 |
| [NCT01077310](https://clinicaltrials.gov/study/NCT01077310?tab=results) | prisoners with HIV, XR-NTX | comorbid | change in % heavy drinking days | 67/33 | +0.10 |
| [NCT02330419](https://clinicaltrials.gov/study/NCT02330419?tab=results) | MSM, binge drinking | comorbid | binge days per week, 12 wk | 54/54 | -0.41 |
| [NCT01932801](https://clinicaltrials.gov/study/NCT01932801?tab=results) | homeless, XR-NTX (HaRP) | comorbid | drinks on peak occasion, week 12 | 74/78 | -0.26 |
| [NCT00568958](https://clinicaltrials.gov/study/NCT00568958?tab=results) | young adults | comorbid | % heavy drinking days, 8 wk | 61/67 | -0.09 |

## Result (hand-computed, pending the job)

| Pool | k | g | 95% CI | I² |
|---|---|---|---|---|
| All 17 trials | 17 | **-0.16** | -0.29 to -0.04 | 47% |
| General AUD samples | 6 | **-0.10** | -0.28 to +0.08 | 51% |
| Samples selected for something else as well | 11 | **-0.22** | -0.41 to -0.04 | 49% |
| Difference (comorbid minus general) | | -0.13 | z = -0.95, p = 0.34 | |

**The prediction failed.** In naltrexone trials the effect is not smaller in comorbid samples. If anything it is larger, mainly because of three trials in people with HIV or at HIV risk (-1.11, -0.41, -0.15) and the PTSD trial (-0.43). The difference is not significant either way.

Across the three drugs (difference = comorbid minus general; positive = weaker in comorbid samples):

| Drug | Difference | SE |
|---|---|---|
| Topiramate | +0.47 | 0.13 |
| Gabapentin | +0.55 | 0.29 |
| Naltrexone | -0.13 | 0.13 |

The fixed-effect average, about +0.20, means little, because the three differences disagree (Q ≈ 11.7 on 2 df, p ≈ 0.003). The split is real enough in the two anticonvulsant pools, but it does not carry over to naltrexone.

## Reading

- **Naltrexone on registry results alone: a small benefit, g about -0.16.** That fits the modest effects reported in the journals (for example Maisel et al., Addiction 2013, PMID 23075288, 64 placebo-controlled trials). Maisel found larger naltrexone effects in trials that required abstinence before treatment. Here the one such registry trial, ALK21-014, is the least favourable of the large ones. The two largest trials, the extended-release pivotal trial ALK21-003 (-0.25) and ALK21-014 (+0.15 on the share with no heavy drinking days), point in different directions.
- **The cross-drug comorbidity pattern is not general.** Our earlier topiramate and gabapentin notes said the comorbid split "suggests the comorbid trials are measuring something about the populations". The pre-registered test does not support that reading. The pattern is drug-specific: it holds for the two anticonvulsants and not for naltrexone. Or the anticonvulsant splits are partly chance, since they rest on 2-5 trials per side and were found after the fact. We have changed the wording in both notes.
- **A negative result worth keeping.** We found no published test of comorbid vs general samples as a moderator across AUD drugs. The moderator analyses we found tested things like dose, duration, age, gender, attrition, pre-treatment abstinence, lab paradigm and added psychotherapy, not this. Had we stopped at two drugs, the claim would have looked general.

## Registry data problems found along the way

- **NCT01932801 (HaRP)**: the posted "standard deviations" for drinks on the peak occasion (1.70 at a baseline mean of 32.0 drinks, n = 74) can only be standard errors. They are read as SEs here. The trial's posted drinking-frequency outcome, whose SDs look right, gives a similar g (about -0.31).
- **NCT01245647**: the posted lower and upper limits next to the SDs are inconsistent (the naltrexone upper limit, 5.3, is below its own mean, 12.0).
- **NCT00920829**: one placebo group's description says it was given 50 mg naltrexone.
- **NCT01077310**: results are posted split by how many injections people received, which is a post-randomization split. The strata are recombined here.

## Limits

- Hand transcription and hand arithmetic; the registry check job is queued.
- Outcomes differ across trials (heavy drinking days, drinking days, drinks per day, abstinence), as do formulations (oral, extended-release) and durations (8 to 24 weeks). Medians and IQRs (ALK21-003) were converted to means and SDs (Wan 2014). SDs from 95% CIs use the t quantile. SEs were turned into SDs with sqrt(n).
- "Comorbid" lumps very different samples together. HIV trials drive the comorbid estimate. With 6 and 11 trials, a subgroup test has little power.
- Naltrexone is contraindicated with opioid use and needs liver monitoring. This note looks at efficacy only.

## Reproduce

```
python regpool.py studies/topiramate_aud.json studies/gabapentin_aud.json studies/naltrexone_aud.json --out-dir out --verify --compare general comorbid
```
