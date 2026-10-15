# Pre-registration 2: does the comorbid-sample split hold for acamprosate, baclofen and varenicline? (2026-10-15)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Text CC BY 4.0. Research information, not medical advice.

This file is committed **before any outcome data of these three drugs' trials are read**. It is based only on the ClinicalTrials.gov search listings (NCT id, title, phase, enrollment, status, interventions, conditions) fetched on 2026-10-15. One exception: NCT00656630, an acamprosate-naltrexone-placebo trial, was read for the naltrexone pool. It posts drinking only at week 1, so it is excluded below by the 4-week rule, as it was for naltrexone.

## Background

In registry-only pools (evidence-pack findings), topiramate and gabapentin worked in general AUD samples and hardly at all in samples selected for another condition as well (differences of +0.47 and +0.55 in g). Both splits were found after the data were seen. The first pre-registered test, on naltrexone, failed (difference -0.13; [naltrexone finding](naltrexone-aud-registry-pool-2026-10-15.md)). That leaves one possibility: the split belongs to drugs acting on GABA and glutamate systems (topiramate, gabapentin) and not to the opioid antagonist.

## Hypotheses

- **H1 (generality):** for each drug, g(general) is more negative (more benefit) than g(comorbid).
- **H2 (mechanism, exploratory):** the split appears for the GABA/glutamate-acting drugs (acamprosate, baclofen) and not for varenicline (a nicotinic partial agonist).
- **Primary test:** the fixed-effect average of the per-drug differences (comorbid minus general) over the three new drugs, `regpool.py --compare general comorbid`. H1 is supported if that average is above 0 with p < 0.05. Per-drug differences and the six-drug Q test are reported whatever they show. A drug with fewer than 2 usable trials in either group contributes no difference.

## Search

ClinicalTrials.gov API v2, `query.cond=alcohol&query.intr=<drug>`, `filter.advanced=AREA[HasResults]true`, 2026-10-15: acamprosate 11 records, baclofen 8, varenicline 20.

## Inclusion, outcome rule

The same rules as the naltrexone pool. Randomized; the drug against placebo, the drug being the only difference between the arms compared; at least 4 weeks of treatment; a posted drinking outcome. Excluded: lab-paradigm, single-session, withdrawal-treatment and healthy-volunteer studies, open-label and single-arm studies. Outcome: the posted heavy-drinking measure at end of treatment; otherwise drinks per drinking day or per week; otherwise drinking frequency or abstinence. Trials listed below that turn out on reading to fail inclusion are dropped with the reason. They are never moved between groups.

## Classification (from the listings only)

**Acamprosate**
- general: NCT03818191 (pharmacogenomics, 288), NCT00381043 (family medicine clinic, 100; included only if placebo-controlled)
- comorbid: NCT00466661 (bipolar), NCT00452543 (major depression, with escitalopram), NCT00330174 (anxiety or depression; only if placebo-controlled), NCT00463346 (schizophrenia), NCT00249379 (criminal-justice supervisees; only if placebo-controlled)
- excluded: NCT00106106 (withdrawal, spectroscopy), NCT04287920 (liver-disease safety, n=12), NCT00605904 (lab craving induction), NCT00656630 (drinking posted at week 1 only)

**Baclofen**
- general: NCT01980706 (high dose, 120), NCT01002105 (add-on to standard treatment, 75; only if the control is a placebo)
- comorbid: NCT01751386 (anxiety disorder), NCT01008280 (veterans with hepatitis C)
- excluded: NCT02052440, NCT01937364, NCT00597701 (alcohol withdrawal), NCT01076283 (lab mechanisms)

**Varenicline**
- general: NCT01146613 (alcohol dependence, 200), NCT00705523 (40), NCT01011907 (pilot, 99), NCT00695500 (heavy drinkers, 50), NCT04167306 (varenicline x bupropion factorial, 388; varenicline arms vs the others)
- comorbid (smokers, the same rule as the topiramate smoking trial): NCT01553136 (alcohol dependence in smokers), NCT01347112 (active alcoholic smokers), NCT00580645 (smoking-cessation drugs and drinking), NCT02859142 (heavy drinkers' smoking cessation, varenicline vs placebo with patch)
- excluded: NCT01000987, NCT03035708, NCT01151813, NCT04249882 (lab), NCT01092702 (tobacco outcome in recovery), NCT00773422 (lab smoking lapse), NCT02698215 (no placebo), NCT02151591, NCT00860028 (no placebo), NCT01592695 (quitline, varenicline not randomized), NCT01169610 (n=1)

## Power, honestly

Expect 2-6 usable trials per group per drug. A real difference of about 0.5 in g, like the anticonvulsant splits, would be detectable when pooled over three drugs. A difference of 0.2 would not. A null result here would weaken H1 further. It would not show the populations are the same.
