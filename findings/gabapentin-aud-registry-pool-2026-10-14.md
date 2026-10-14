# Gabapentin for alcohol use disorder, from registry results alone (2026-10-14, preliminary)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

**Status: preliminary.** The inputs below were transcribed by hand from the ClinicalTrials.gov API v2 on 2026-10-14 and the pooled numbers were computed by hand. `regpool.py` recomputes them from `studies/gabapentin_aud.json` and, with `--verify`, re-downloads every record so each transcribed number can be checked against the registry. This note will be updated with that output.

## Question

Does gabapentin reduce drinking in alcohol use disorder (AUD) when the evidence is limited to results posted on ClinicalTrials.gov, the public registry that also holds trials never published in journals?

Published meta-analyses pool journal articles. The most recent one for this question (Kranzler et al., Addiction 2019, PMID 31077485; seven RCTs) found clear benefit only on percent heavy drinking days, g = -0.64 (95% CI -1.22 to -0.06). A registry-only pool is a different check: it uses the numbers sponsors posted, including trials that were small, negative or never written up.

## Search and selection

ClinicalTrials.gov API v2, results posted (`filter.advanced=AREA[HasResults]true`), on 2026-10-14:
- `query.cond=alcohol&query.intr=gabapentin`: 12 records;
- `query.term=gabapentin AND (drinking OR alcohol OR AUD)`: 21 records (no new AUD trials).

Kept: controlled trials of gabapentin in AUD with a posted drinking outcome (6 trials, 456 participants in the arms used), plus 1 trial of gabapentin enacarbil as a sensitivity analysis only, because it is a branded prodrug rather than generic gabapentin.
Excluded: withdrawal trials against active drugs (NCT01573052, NCT03012815), an imaging crossover with no drinking outcome (NCT03220776), a single-arm study (NCT03205423), and a flumazenil-plus-gabapentin combination (NCT00262639).

Each trial contributes one standardized mean difference, negative favouring gabapentin. Heavy-drinking outcomes are used where posted. Otherwise the trial's abstinence or relapse outcome is used, converted from a log odds ratio with sqrt(3)/pi (Chinn 2000). DerSimonian-Laird random effects, with Hartung-Knapp-Sidik-Jonkman (HKSJ) intervals.

| NCT | Trial | Posted outcome used | n (gabapentin/control) | g |
|---|---|---|---|---|
| [NCT00391716](https://clinicaltrials.gov/study/NCT00391716?tab=results) | Mason 2014, 900 + 1800 mg/day | complete abstinence, 14/101 vs 2/49 | 101/49 | -0.733 |
| [NCT02349477](https://clinicaltrials.gov/study/NCT02349477?tab=results) | Anton 2020, withdrawal history | no heavy drinking days, 12/44 vs 4/46 | 44/46 | -0.756 |
| [NCT01141049](https://clinicaltrials.gov/study/NCT01141049?tab=results) | Mariani 2021, 3,600 mg/day pilot | % heavy drinking days at week 8, 22.5 (SD 34.0) vs 53.9 (SD 44.0) | 19/21 | -0.778 |
| [NCT01014533](https://clinicaltrials.gov/study/NCT01014533?tab=results) | AUD with insomnia | relapse to any drinking, 14/25 vs 13/24 | 25/24 | +0.041 |
| [NCT04052139](https://clinicaltrials.gov/study/NCT04052139?tab=results) | St PETER pilot, HIV with chronic pain | change in % heavy drinking days, -4.22 (SE 2.07) vs -4.63 (SE 4.64) | 15/15 | +0.029 |
| [NCT00183196](https://clinicaltrials.gov/study/NCT00183196?tab=results) | Anton 2011, added to naltrexone | days to relapse, 69.9 (SE 6.5) vs 59.6 (SE 7.6) | 48/49 | -0.207 |
| [NCT02252536](https://clinicaltrials.gov/study/NCT02252536?tab=results) | Falk 2019, gabapentin **enacarbil** (sensitivity only) | no heavy drinking days, 24.1% vs 17.3% (41/170 vs 29/168) | 170/168 | -0.232 |

## Result (hand-computed, pending the registry check)

| Pool | k | g | 95% CI | HKSJ 95% CI | I² |
|---|---|---|---|---|---|
| All generic-gabapentin trials | 6 | **-0.36** | -0.66 to -0.06 | -0.76 to +0.04 | 28% |
| Gabapentin alone vs placebo | 5 | -0.42 | -0.81 to -0.04 | -0.97 to +0.12 | 37% |
| Heavy-drinking outcomes only | 3 | -0.52 | -1.02 to -0.01 | -1.64 to +0.60 | 40% |
| General AUD samples | 4 | -0.51 | -0.84 to -0.19 | -1.02 to -0.01 | 17% |
| Samples with another condition (insomnia; HIV with pain) | 2 | +0.04 | -0.43 to +0.51 | not informative at k=2 | 0% |
| Adding gabapentin enacarbil | 7 | -0.31 | -0.53 to -0.09 | in the job output | 18% |

The prediction interval for the 6-trial pool is about -1.05 to +0.33.

## Reading

- **The signal is there, but it is smaller and less certain than in the journals.** On registry results, gabapentin favours less drinking (g about -0.36), but the HKSJ interval, which is more honest with few trials, just crosses zero. The published estimate of -0.64 rests on percent heavy drinking days alone. Here every outcome type is pooled.
- **It holds in general AUD samples (g about -0.51, four trials) and vanishes in the two trials of people with another condition** (insomnia, and HIV with chronic pain; both small, about 0). The same split appeared in MV2's registry pool for topiramate, where comorbid groups carried the smallest effects.
- **Gaps in the registry go the other way from the usual worry.** Three small placebo-controlled trials reported as positive in journals have no results on ClinicalTrials.gov: Furieri 2007 (n=60, PMID 18052562), Brower 2008 (n=21, PMID 18540923) and Chompookham 2018 (n=112, PMID 30243130). A registry-only pool leaves out positive evidence here. It is not hiding negative trials.
- **What a sponsor posts is not always the headline.** Mason 2014 posted only complete-abstinence counts, though its paper's co-primary outcome was no heavy drinking (published 22.5%, 29.6% and 44.7% for placebo, 900 mg and 1,800 mg). Anton 2011 posted days to any relapse over 16 weeks, but its paper reports its benefit on heavy drinking over the 6 weeks gabapentin was given.

## Limits

- Hand transcription through an API summary; the registry check (`regpool.py --verify`) is pending.
- Outcomes differ across trials (abstinence, no heavy drinking, % heavy drinking days, days to relapse). Converting odds ratios to SMDs assumes a logistic distribution.
- Mean ± SE was converted to SD with sqrt(n). If a posted SE comes from a model rather than raw data, the SD can be wrong.
- Six small-to-mid trials. One trial is an add-on to naltrexone. Durations run from 8 to 16 weeks.
- Gabapentin can be misused, especially with opioids, and FDA warned in 2019 of serious breathing problems when gabapentinoids are taken with other CNS depressants or by people with respiratory risk factors. This note looks at efficacy only.

## Reproduce

```
python regpool.py studies/gabapentin_aud.json --out-dir out --verify
```
