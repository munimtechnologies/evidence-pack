# Naltrexone registry pool: classification fixed before reading any outcome data

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Text CC BY 4.0. Research information, not medical advice.

Written 2026-10-15 ~00:30 UTC, after reading only the ClinicalTrials.gov search listing (NCT id, title, phase, enrollment, status, interventions, conditions) and BEFORE fetching any posted outcome measure of any naltrexone trial.

## Hypothesis under test
From topiramate (general AUD g -0.57, k=4; comorbid -0.10, k=5) and gabapentin (general -0.51, k=4; comorbid +0.04, k=2): in registry-posted placebo-controlled trials, the drug effect on drinking is smaller in samples selected for something besides AUD than in general AUD samples.

Prediction for naltrexone: pooled g(general) is more negative than pooled g(comorbid). Test: difference of the two random-effects means, z test on the subgroup difference (Q-between). Reported whatever the direction.

## Search
ClinicalTrials.gov API v2, query.cond=alcohol, query.intr=naltrexone, AREA[HasResults]true, 2026-10-15: 60 records.

## Inclusion
Randomized; naltrexone (oral or extended-release) vs placebo, naltrexone being the only difference between the arms compared; at least 4 weeks of treatment; a posted drinking outcome. Lab-paradigm, single-session and healthy-volunteer studies, active-comparator trials, open-label/single-arm studies and smoking-cessation trials are excluded.

## Outcome rule (same as topiramate/gabapentin)
The posted heavy-drinking outcome (percent heavy drinking days, heavy drinking days, any heavy drinking / no heavy drinking) at end of treatment where posted; otherwise drinks per drinking day or drinks per week; otherwise abstinence/relapse. If several heavy-drinking measures exist, the one named primary.

## Classification (from the listing only)
General AUD sample (selected for AUD/heavy drinking alone):
NCT01218958 (ALK21-003), NCT00501631 (ALK21-014), NCT00831272 (pharmacogenetic), NCT01296646 (sweet preference), NCT02026011 (East Asian descent), NCT00366626 (craving + genetics), NCT00920829 (genetic and brain mechanisms), NCT00656630 (acamprosate vs naltrexone vs placebo: naltrexone and placebo arms), NCT00511836 (ALK21-018, craving), NCT00817089 (white alcoholics), NCT01211769 (omegas: naltrexone vs placebo arms), NCT00667875 (naltrexone vs placebo arms)

Samples selected for something else as well (another disorder, HIV, a second substance, housing/incarceration, or age group):
NCT00302133 (bipolar), NCT00006489 (PTSD), NCT00338962 (depression/PTSD), NCT00777062 (cocaine, XR-NTX), NCT00142818 (cocaine), NCT01723384 (methamphetamine polysubstance), NCT01625091 (women with HIV), NCT01245647 (HIV), NCT01227044 (HIV), NCT01077310 (HIV+ prisoners), NCT02330419 (MSM, binge drinking, HIV risk), NCT01932801 (homeless, harm reduction, XR-NTX), NCT00568958 (young adults)

Sensitivity: the age-group (NCT00568958) and housing (NCT01932801) trials moved to "general" (in the topiramate pool the adolescent trial was in the comorbid group, so the main rule keeps age groups there).

Excluded from the listing: NCT02842073 (open label), NCT01519063 / NCT04249882 / NCT00256451 / NCT04854551 / NCT01625611 (lab or imaging), NCT00773422 / NCT02698215 (smoking), NCT00183196 / NCT01214083 (naltrexone in both arms), NCT03852628 / NCT02461927 (combination or ketamine), NCT02478489 / NCT01893827 / NCT01218997 / NCT01856712 / NCT01155869 / NCT01342549 (active comparators), NCT00620750 / NCT02445339 / NCT04094584 / NCT04817410 / NCT04562779 / NCT00537745 / NCT02885311 / NCT01908062 (no placebo arm), NCT00156923 / NCT01218971 / NCT00156936 (extensions, no placebo), NCT00115037 (non-responder strategy), NCT01032135 (adaptive behavioural), NCT05458609 (n=8, lemborexant), NCT03278886 (n=11, no placebo), NCT04052139 (low-dose naltrexone pain pilot, used in the gabapentin pool).

Trials in the include lists that turn out on reading to fail inclusion (e.g. no placebo-vs-naltrexone contrast posted, no drinking outcome) are dropped with the reason stated; they are not moved between groups.
