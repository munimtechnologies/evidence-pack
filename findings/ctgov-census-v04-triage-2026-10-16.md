# ClinicalTrials.gov impossible-statistics census: v0.4 rerun and hand triage (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

This updates `findings/ctgov-impossible-statistics-census-2026-10-15.md` (v0.2 census, 45 studies).

## What ran

`ctgov_audit.py` v0.4 ran in a sealed job (`ctgov-sd-audit-v4`, 2026-10-16 05:12-05:24Z). It read every ClinicalTrials.gov study with posted results (about 80,500; progress lines stop at 80,000) and passed all 19 of its tests. v0.4 runs the v0.2 checks unchanged, plus the bounded-measure checks that v0.2 had left out (`mean_outside_bounds`, `sd_above_max`) and a new SE-based tier.

## Result 1: the v0.2 numbers reproduce exactly

| Check | v0.2 studies (10-15) | v0.4 studies (10-16) |
|---|---|---|
| center_outside_interval | 16 | 16 |
| inverted_interval | 18 | 18 |
| negative_dispersion | 8 | 8 |
| sd_above_width | 3 | 3 |

**The 45-study headline stands.** A day later, a second, independent run of the full registry found the same counts.

## Result 2: half of the new Bhatia-Davis flags were false positives

v0.4 flagged 12 more studies under `mean_outside_bounds` or `sd_above_max` (NCT06380179 was already among the 45). Every one was checked by hand against its live record on 2026-10-16:

| NCT | Check | As posted | Verdict |
|---|---|---|---|
| [NCT02967367](https://clinicaltrials.gov/study/NCT02967367?tab=results) | mean outside + SD | deep and light sleep as "a percentage of total sleep time": 243, 192, 190, 163, 239 | **impossible as written** (the values look like minutes) |
| [NCT02899962](https://clinicaltrials.gov/study/NCT02899962?tab=results) | mean outside | "Proportion of days" in remission: 70.2 and 60.8 | **impossible as written** (percentages labelled as a proportion) |
| [NCT05135676](https://clinicaltrials.gov/study/NCT05135676?tab=results) | SD | % daytime above 250 mg/dL: mean 1.1, SD 12.3, n 60 (largest possible SD about 10.5) | **impossible as written** (a level, not a change) |
| [NCT03808909](https://clinicaltrials.gov/study/NCT03808909?tab=results) | SD | % days with drinking or substance use: mean 19.85, SD 44.509, n 9 (largest possible about 42.3) | **impossible as written** |
| [NCT03806491](https://clinicaltrials.gov/study/NCT03806491?tab=results) | SD | % days alcohol used for sleep, week 6: mean 4.76, SD 21.82, n 35 (largest possible 21.6) | **impossible as written, but only by 1%**. The record mentions multiple imputation, and imputed values outside 0-100 could explain it. |
| [NCT03833245](https://clinicaltrials.gov/study/NCT03833245?tab=results) | SD (primary) | % days of attendance: mean 40.4, SD 53.6, n 52 | **unresolved**. The record says it is a level, but a sibling primary outcome posts negative means, so it may be a change score. |
| NCT06033521 | SD (primary) | adherence "Percentage of days": the description defines it as a medication possession ratio | **false positive**: an MPR can exceed 100% |
| NCT05785832 | SD | class titled "Change from Baseline" | **false positive**: change score |
| NCT02365064 | SD | description: "Change from baseline to 4 months in sleep efficiency" | **false positive**: change score |
| NCT04623086 | SD | description: "Change in nocturnal ... time in range" | **false positive**: change score |
| NCT03477838 | SD | a sibling class in the same measure posts -3.17 | **false positive**: change score |
| NCT01687400 | SD | "Rate of Mutation Clearance", proportion per day | **false positive**: a rate, not bounded |

**Five of the 12 are impossible as written** (one of them only marginally), one is unresolved and six are false positives. The cause matches the v0.2 triage: a percent unit does not mean the posted number is a level. Sponsors post change scores, possession ratios and rates under percent units, and the title often doesn't say so.

## Fix, and a prediction stated before the rerun

`ctgov_audit.py` v0.5 (tests added for every case above):
- An `sd_above_max` hit becomes the suspect check `sd_above_max_if_level` when the measure's description or a class/category title says "change" or "differ", or when another mean in the same measure is below the floor.
- Rates, possession ratios and areas under the curve get no bounds.
- `sd_above_width` is unaffected: an SD wider than the whole scale is impossible even for a change score.

v0.5 is queued (`ctgov-sd-audit-v5`). **Prediction, written before it runs:** the impossible tier will hold about 51 studies, the 45 above plus the six remaining non-false-positive rows (NCT03833245 stays in until a human reads its paper). If the description of NCT02967367 mentions a difference, its SD flag will drop, but its mean flags keep it in. The registry is live, so a record corrected since 10-16 can change the count by one or two.

## The SE tier (reported separately; not triaged in full)

`se_implies_sd_above_width` flagged 135 cells in 26 studies (7 with a primary outcome). Here a posted SE, multiplied by the square root of n, exceeds the whole width of the scale. Read as an SE of a plain mean, that is impossible, so the posted number is almost certainly an SD labelled as an SE. Clear examples:
- **NCT03985098** (primary outcome): adherence as a proportion of days covered, 0.63 with "SE" 0.34 and n = 240. That implies an SD of 5.3 on a 0-1 scale.
- **NCT02037126** (psilocybin trial, results posted 2026): percentage of abstinent days with "SE" 32-49 and n = 20. That implies SDs of 143-219 on a 0-100 scale.


Some of the 26 are false positives of known kinds:
- Three are areas under a curve (NCT05298111, NCT00162266, NCT00868140), where the scale's range does not bound the area. v0.5 excludes these.
- At least one range was probably parsed from a per-item score rather than the total: NCT04335136 (mSOFA, "0-4"), where the total score can be higher. Why this tier matters for evidence synthesis: a meta-analyst who reads such an "SE" as an SE and converts it to an SD gets an SD inflated by a factor of sqrt(n), which shrinks the trial's standardized effect toward zero. The v0.5 rerun will give the cleaned count. Until it is triaged by hand, the count is a screening result, not a finding.

## Limits

- Each flag shows that a posted number, or its label, is wrong as written. It doesn't say which one, and it is no judgement on a trial's conclusions.
- The census is a floor. Wrong numbers that are still possible pass every check.
- Hand triage used the live API records only, not the papers.
