# Topiramate for alcohol use disorder, from registry results alone (2026-10-14)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

**Status: checked against the registry.** The inputs were transcribed by hand from the ClinicalTrials.gov API v2 on 2026-10-14. A sealed job re-downloaded all nine records the same day, and every transcribed mean, SD/SE, n and p matched the posted values (`pool.py --verify`; pooled output in [topiramate-aud-pool-output-2026-10-14.md](topiramate-aud-pool-output-2026-10-14.md), side-by-side registry check in [topiramate-aud-pool-verify-2026-10-14.md](topiramate-aud-pool-verify-2026-10-14.md)). The pooled numbers below are the job's, not hand arithmetic.

## Question

Does topiramate reduce heavy drinking when the evidence is limited to results that sponsors posted on ClinicalTrials.gov?

Published meta-analyses pool journal articles: Blodgett et al. 2014 (PMID 24796492; 7 RCTs, n = 1,125) found g = 0.406 on heavy drinking, and Fluyau et al. 2023 (PMID 36648091, Bayesian) found d = 0.401 on heavy drinking days. Both lean on the two Johnson trials (Lancet 2003; JAMA 2007, NCT00210925), and neither of those has results posted on the registry. A registry-only pool is therefore an independent check: almost none of its trials drive the published estimates.

## Search and selection

ClinicalTrials.gov API v2, `query.cond=alcohol`, `query.intr=topiramate`, results posted, on 2026-10-14: 19 records. Kept: randomized, placebo-controlled trials with a posted heavy-drinking outcome (9 trials, 1,048 people in the arms used). Excluded: single-arm studies (NCT00300742, NCT00329407); trials with n <= 4 (NCT01408641, NCT02074904, NCT01764685); no drinking outcome (NCT00802412); drinking-days-only outcomes (NCT01750268, NCT01087736); and two bipolar trials not yet read (NCT00550394, NCT00572117).

One Hedges' g per trial, negative favouring topiramate. DerSimonian-Laird random effects with Hartung-Knapp-Sidik-Jonkman (HKSJ) intervals.

| NCT | Trial | Posted measure | n (T/C) | g |
|---|---|---|---|---|
| [NCT02371889](https://clinicaltrials.gov/study/NCT02371889?tab=results) | Penn pharmacogenetic trial | heavy drinking days, 12 wk | 85/85 | -0.485 |
| [NCT00626925](https://clinicaltrials.gov/study/NCT00626925?tab=results) | Kranzler 2014, problem drinkers | heavy drinking days/week; g from the posted p = 0.001 | 67/71 | -0.557 |
| [NCT01749215](https://clinicaltrials.gov/study/NCT01749215?tab=results) | Veterans with PTSD and AUD | change in % heavy drinking days | 72/79 | -0.287 |
| [NCT01182766](https://clinicaltrials.gov/study/NCT01182766?tab=results) | Robinson 2025, AUD and smoking | % heavy drinking days, weeks 15-18 (two doses combined) | 152/84 | -0.014 |
| [NCT03176953](https://clinicaltrials.gov/study/NCT03176953?tab=results) | Norman 2025, PTSD and AUD, with prolonged exposure | % heavy drinking days at week 16 | 50/50 | -0.183 |
| [NCT00167245](https://clinicaltrials.gov/study/NCT00167245?tab=results) | Kampman 2013, cocaine and alcohol dependence | heavy drinking days, 13 wk | 54/46 | -0.210 |
| [NCT03018704](https://clinicaltrials.gov/study/NCT03018704?tab=results) | VA trial in African Americans (terminated) | % heavy drinking days, last 42 days | 17/18 | -0.566 |
| [NCT00862563](https://clinicaltrials.gov/study/NCT00862563?tab=results) | Boston anticonvulsant trial (terminated) | % heavy drinking days, week 12 | 16/20 | -1.136 |
| [NCT01641445](https://clinicaltrials.gov/study/NCT01641445?tab=results) | Adolescents and young adults | % heavy drinking days, weeks 5-8 | 41/41 | +0.226 |

## Result

| Pool | k | g | 95% CI | HKSJ 95% CI | I² |
|---|---|---|---|---|---|
| All nine trials | 9 | **-0.301** | -0.506 to -0.097 | -0.562 to -0.041 | 60% |
| Posted arm data only (drop the p-derived and rescaled-SD trials) | 7 | -0.268 | -0.527 to -0.008 | -0.628 to +0.093 | 64% |
| **General AUD samples** | 4 | **-0.574** | -0.780 to -0.368 | -0.895 to -0.253 | 0% |
| **Samples with another condition** (smoking, PTSD, cocaine, adolescents) | 5 | **-0.103** | -0.265 to +0.059 | -0.333 to +0.127 | 8% |

Prediction interval for all nine: -0.910 to +0.307. Leave-one-out estimates run from -0.249 (without the terminated Boston trial) to -0.354 (without the adolescent trial). Every leave-one-out 95% CI excludes zero, but four of the nine leave-one-out HKSJ intervals cross it narrowly (upper limits +0.003 to +0.027).

## Reading

- **On registry results alone, topiramate still reduces heavy drinking**, at about three-quarters of the published size (g -0.30 against about -0.40), with real heterogeneity (I² 60%).
- **The heterogeneity has a clear source.** In the four trials of people whose main problem is alcohol, the effect is moderate and consistent (g -0.57, I² 0%, HKSJ interval well clear of zero), matching or exceeding the journals. In the five trials of people with another condition as well (smokers, PTSD with exposure therapy, cocaine dependence, adolescents), it is small and uncertain (g -0.10). The split is by sample type only and was written into the job before it ran, but the hand calculations had already been seen, so treat it as a post hoc subgroup on four and five trials.
- **The same split appears for gabapentin.** MV2's registry pool for gabapentin ([finding](gabapentin-aud-registry-pool-2026-10-14.md), registry check pending) gives g about -0.51 in four general-AUD trials and about +0.04 in two trials of people with insomnia or HIV with chronic pain. Two drugs with different mechanisms showing the same pattern suggests the comorbid trials are measuring something about the populations (or the add-on design, or ceiling effects in low-drinking samples) rather than about one drug. We have not found this cross-drug comparison in the literature; earlier topiramate meta-analyses either had too few trials to test moderators (Blodgett 2014) or tested age, dose, duration, gender and attrition (Fluyau 2023), not comorbidity.
- **Registry data problems found along the way.** NCT01749215 posts SDs on a proportion scale (0.41, .36) next to percent means; they were multiplied by 100. NCT00626925 posts mixed-model SEs that cannot be turned into SDs (they would imply d = -1.55), so its g comes from the posted p. Both choices are flagged and dropped in the "posted arm data only" row.

## Limits

- Outcomes differ (heavy drinking days, weeks or percentages; final values or change), measured over 5 to 18 weeks. Standardized differences hide that.
- Mean ± SE was converted to SD with sqrt(n) for three trials; a model-based SE would distort it.
- The two pivotal positive trials are absent by design, and two bipolar trials are not yet read.
- Effectiveness only. Topiramate has well-known adverse effects (paresthesia, cognitive slowing, metabolic acidosis, kidney stones, fetal harm), which this note does not weigh.

## Reproduce

```
python regpool.py studies/topiramate_aud.json --out-dir out --verify
```

The numbers above come from the first, topiramate-only version of this script (`pool.py`, run in a sealed container on 2026-10-14 in 83 seconds). `regpool.py` is its general form with the same inputs in `studies/topiramate_aud.json`; a run confirming that both give identical output is queued, and this note will say so once it lands.
