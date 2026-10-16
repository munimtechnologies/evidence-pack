# One registry record, two labelling problems: a worked case from the census SE tier (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

This is a hand-checked case from the SE tier of `findings/ctgov-census-v04-triage-2026-10-16.md` (still present in v0.5: `findings/ctgov-census-v05-2026-10-16.md`). It is about how a posted record is labelled, not about the trial's conclusions. The trial's published primary result is not affected (see "What is not affected").

## The record

[NCT02037126](https://clinicaltrials.gov/study/NCT02037126?tab=results), "Psilocybin-facilitated Treatment for Cocaine Use" (University of Alabama at Birmingham), 20 vs 20 randomized. Paper: Hendricks PS et al., JAMA Netw Open 2026;9(5):e2611029, PMID 42096204, PMC13153991. Live API record read 2026-10-16.

## Problem 1: the secondary "Standard Error" cells are SDs

Outcomes 14-17 (percentage of alcohol, heavy-alcohol, tobacco and cannabis "abstinent" days; three periods; two arms) post 24 mean cells, each labelled **Standard Error**, with n = 20 per arm.

- For a percentage, the largest possible SD for n values with a given mean is sqrt(m(100-m) n/(n-1)) (the Bhatia-Davis bound).
- **All 24 cells are impossible as SEs.** SE x sqrt(20) exceeds that bound in every cell. The closest case is heavy-alcohol, psilocybin, period 1: mean 1.8, "SE" 4.88, implied SD 21.8, maximum 13.6.
- **All 24 are possible as SDs.** The tightest is tobacco, psilocybin, period 1: mean 55.07, spread 46.01, maximum 51.0.
- **The primary outcome in the same record is labelled correctly.** Cocaine-abstinent days, period 1: 97.43 (SE 1.01) vs 71.63 (SE 5.25). Read as SEs, these give SDs of 4.5 and 23.5, a Hedges g of about 1.50. The paper reports g 1.40 for that period from its mixed model. Read as SDs, they would give g about 6.7. So the submitter used the SE label correctly for the primary outcome and wrongly for the secondaries.

## Problem 2 (likely, not proven): "abstinent days" look like use days

| Measure, period 1 | Psilocybin | Placebo |
|---|---|---|
| Alcohol "abstinent" days, % | 5.7 | 27.68 |
| Heavy-alcohol "abstinent" days, % | 1.8 | 13.29 |
| Tobacco "abstinent" days, % | 55.07 | 63.52 |
| Cannabis "abstinent" days, % | 14.31 | 28.57 |

- A mean of 1.8% heavy-drinking-**abstinent** days means that, on average, people drank heavily on 98% of days. The paper's baseline table says only 13/20 (psilocybin) reported any heavy drinking in the past 90 days, with a median of 16.7% heavy days among them. Reading these values as **use** days fits the baseline; reading them as abstinent days does not.
- Tobacco fits too: the placebo arm had more daily smokers at baseline (11/20 vs 7/20) and posts the higher number.
- This is an inference from plausibility, not a bound violation, so it stays **unresolved**. Only the investigators can confirm it. The paper says these outcomes "will be reported in a separate publication", so **for now the registry is the only public source of them.**

## Why it matters to anyone pooling these numbers

Alcohol days, period 1 (placebo minus psilocybin; positive favours psilocybin if the values are use days):

| Reading | Hedges g |
|---|---|
| Spreads are SDs, values are use days (most likely) | **+0.90** |
| Spreads taken literally as SEs and converted to SDs (SD = SE x sqrt(n)) | +0.20 |
| As above, and "abstinent" taken literally | **-0.20** (favours placebo) |

A literal reading shrinks the effect by a factor of sqrt(20) = 4.5 and flips its sign. Either problem alone would mislead a meta-analysis of psychedelics and secondary substance use, and both errors are invisible unless someone checks the bounds.

## What is not affected

- The published primary result (cocaine-abstinent days) rests on the paper's mixed model and agrees with the registry's correctly labelled primary cells.
- No claim is made about how the trial was run or analysed.

## Reproduce

`se_case.py` and `test_se_case.py` (standard library). The tests encode the hand values above: 24/24 impossible as SE, 24/24 possible as SD, g 0.895 vs 0.200.

**Verified in a sealed job** (`se-case-v1`, 2026-10-16 10:41 UTC): all 6 tests passed, and the script reproduced every hand value. With `--live`, it re-read the record from the ClinicalTrials.gov API. That record holds 120 SE-labelled cells, and **all 24 hand-transcribed cells were found unchanged** (`hand_cells_missing_from_live: []`).

## Prior art (each citation checked against PubMed or Crossref on 2026-10-16)

The SE/SD mix-up made by **meta-analysts** during data extraction is well documented:
- Gøtzsche PC, Hróbjartsson A, Maric K, et al. Data extraction errors in meta-analyses that use standardized mean differences. *JAMA* 2007;298(4):430-437. doi:10.1001/jama.298.4.430. PMID 17652297.
- Kadlec D, Sainani KL, Nimphius S. With great power comes great responsibility: common errors in meta-analyses and meta-regressions in strength & conditioning research. *Sports Med* 2023;53(2):313-325. doi:10.1007/s40279-022-01766-0. PMID 36208412. Of the 20 most-cited meta-analyses in that field, 45% "contained at least one effect size that was mistakenly calculated using standard error rather than standard deviation".
- Sandercock G. The standard error/standard deviation mix-up: potential impacts on meta-analyses in sports medicine. *Sports Med* 2024;54(6):1723-1732. doi:10.1007/s40279-023-01989-9.
- Kanukula R, Page MJ, Turner SL, McKenzie JE. Identification of application and interpretation errors that can occur in pairwise meta-analyses in systematic reviews of interventions: a systematic review. *J Clin Epidemiol* 2024;170:111331. doi:10.1016/j.jclinepi.2024.111331.

**What this adds:** here the error sits upstream, in the **registry record itself**. It also shrinks the effect, whereas the documented extraction error (treating an SE as an SD) inflates it. A PubMed search on 2026-10-16 for ClinicalTrials.gov results-data errors (11 hits; titles read) and a web search found no audit that tests posted SE labels against scale bounds.
