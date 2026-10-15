# Pre-registration 3: spironolactone use and drinking in NHANES adults with hypertension

MV2 of Munim, Inc., 2026-10-15. Written with AI agents (Claude). Text CC BY 4.0; code Apache-2.0.

This plan is committed to this repository **before** any NHANES data is downloaded or read. No one working on it has looked at NHANES alcohol or prescription data for spironolactone. The analysis code (`nhanes_spiro.py`, published in this repository) was written at the same time. The results will be published whatever they show.

## Why

Three real-world studies, all from electronic health records, link spironolactone (an aldosterone/mineralocorticoid-receptor antagonist sold as a generic diuretic and antihypertensive) to less drinking:

- Palzes et al. 2021, Kaiser Permanente Northern California (PMID 34341493). 523 treated vs 2,305 matched untreated patients. Treated patients drank 0.76 fewer drinks a week (95% CI -1.43 to -0.11), and 4.18 fewer among those drinking more than 7 a week.
- Farokhnia et al. 2022, US Veterans Affairs (PMID 36123420). 10,726 exposed vs 34,461 matched unexposed patients. AUDIT-C fell by 0.17 points more in exposed patients (95% CI -0.09 to -0.25), by 0.47 at baseline AUDIT-C ≥ 8 and by 0.69 at ≥ 50 mg/day.
- Loften et al. 2026, TriNetX target-trial emulation in adults with AUD and hypertension (PMID 42132959). The hazard ratio for a recorded AUD remission was 1.24 (1.06-1.45) vs loop diuretics and 2.07 (1.73-2.48) vs ARBs.

All three come from health-system records and two of them from the same research group. A fourth source that is independent, nationally representative and uses a different kind of measurement (an interviewer-administered survey, not chart codes or the AUDIT-C screen) would test whether the association holds outside health-system data. As far as we found, no NHANES analysis of spironolactone and alcohol has been published (PubMed search, 2026-10-15: `spironolactone AND alcohol` in titles returns 4 records, none using NHANES).

## Data

NHANES public files from the CDC, cycles 2005-2006 (D) to 2015-2016 (I), plus 2017-March 2020 (P_). The 2021-2023 cycle is not used because its prescription file has no drug names. For each cycle the files are DEMO, ALQ, BPQ, MCQ and RXQ_RX.

## Population (all fixed in advance)

Each participant must meet all of the following:

1. Age 20 or older.
2. Ever told they have high blood pressure (BPQ020 = 1).
3. Took at least one antihypertensive ingredient in the past month (RXQ_RX, RXDUSE = 1): spironolactone or any ingredient on the comparator list in `nhanes_spiro.py`. Combination products count each ingredient.
4. No eplerenone or finerenone, which are other mineralocorticoid-receptor antagonists.
5. Answered "No" both to ever being told of congestive heart failure (MCQ160B = 2) and to ever being told of any liver condition (MCQ160L = 2). This removes the two main indications in which illness itself reduces drinking.
6. A valid ALQ130 (average drinks per drinking day, past 12 months) of 1 to 95, which in practice means a past-year drinker.

## Exposure and outcomes

- **Exposure:** spironolactone in any listed product (alone or combined), versus antihypertensive users without it.
- **Primary outcome:** ALQ130, capped at 15 (the 2017+ public files top-code at 15).
- **Secondary outcome S1:** a heavy-drinking-day level, ALQ130 ≥ 5 for men or ≥ 4 for women (0/1).

## Model

Weighted least squares with interview weights. Each cycle's weight is rescaled by its share of the 15.2 years: 2/15.2 for two-year cycles and 3.2/15.2 for 2017-March 2020. Standard errors are cluster-robust over (cycle, stratum, PSU), with normal-approximation 95% CIs.

Covariates:
- age and age²;
- sex;
- race/ethnicity (RIDRETH1);
- education (DMDEDUC2, with unknown as its own level);
- cycle;
- the number of distinct non-spironolactone antihypertensive ingredients, capped at 4.

## Hypothesis and decision rule

**H1:** after adjustment, spironolactone users report fewer drinks per drinking day than other antihypertensive users (β < 0).

- **Supported:** the upper 95% CI bound of β is below 0.
- **Contradicted:** the lower bound is above 0.
- **Inconclusive:** the CI includes 0. In that case we report whether the CI rules out a reduction of 0.5 drinks per drinking day.

## Sensitivity analyses (reported, not used for the decision)

- **S1:** the heavy-day outcome (linear probability model, same covariates).
- **S2:** spironolactone exposure restricted to users who have taken it for 90 days or more (RXDDAYS ≥ 90). Shorter or unknown-duration users are dropped.
- **S3:** unweighted OLS.
- **S4:** the unadjusted weighted difference in means.

## Known limits, stated in advance

- **Cross-sectional design.** Current use is measured against drinking over the past 12 months, so timing is blurred.
- **Confounding by indication:**
  - resistant hypertension and primary aldosteronism (aldosterone itself tracks drinking, Aoun et al. 2018, PMID 28461696);
  - hormonal uses in women.
- **Selection.** Conditioning on past-year drinking misses anyone spironolactone helped to stop drinking entirely.
- **Power.** Expected spironolactone users after exclusions number in the low hundreds, so a small true effect (such as the 0.76 drinks a week in Palzes 2021) cannot be detected. This is a consistency check, not a definitive test.
- **Self-report and survey weights.** Drinking is self-reported. NHANES weights are not designed for subgroups this small.

Whatever the result, it will be published in `findings/` with the code and the counts, and will be cited as our own analysis (marked *) in our ReGen evidence package on spironolactone for alcohol use disorder.
