# Metformin for knee osteoarthritis: pooling only the oral, placebo-controlled trials (2026-10-15)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

Addendum to `metformin-knee-oa-evidence-audit-2026-10-15.md`. That audit asked which trials sit under pooled pain SMDs of 1.3-2.0. This note pools only the three human RCTs that compare **oral** metformin with **placebo** and report pain, and checks how each one gets its effect size.

## Summary

- **Three trials qualify:** Pan 2025 (Australia, n 107), Alimoradi 2023 (Iran, n 88) and Aiad 2024 (Egypt, n 50 analysed). The topical-gel trial (Abed 2024) has no placebo-drug arm and is left out. Alimoradi 2025 is the same trial as Alimoradi 2023, so it is counted once.
- **Random-effects pool (DerSimonian-Laird): SMD 0.97 (95% CI 0.36 to 1.57), I² 78%, tau² 0.22**, positive meaning less pain on metformin. With the Hartung-Knapp-Sidik-Jonkman adjustment, which is the usual recommendation when only 2-5 studies are pooled, the interval is **-0.38 to 2.31**, so it includes no effect.
- **Pan 2025 on its own gives 0.43 (0.02 to 0.83).** It is the only one of the three that was prospectively registered, analysed by intention to treat with stated methods, and had balanced attrition.
- **Why the two smaller trials come out larger:**
  - **Alimoradi 2023 (g 1.06):** 17 of 44 on metformin dropped out and 0 of 44 on placebo. The table still reports n 44 per arm, and the paper does not say how the missing values were filled. The groups also started 3.1 KOOS points apart, in metformin's favour, and the test compared end-of-treatment scores, not change.
  - **Aiad 2024 (g 1.52):** the Methods say 50 were randomized and the Results say 60, with ten dropouts excluded, so the analysis covers completers only. Its WOMAC pain SDs (1.4-2.1 on a 0-20 scale) are **about 9% of the scale range**. In the other two trials the SDs are about 19-21% (KOOS pain 19 on 0-100; WOMAC pain about 105 on 0-500). An SD half as wide doubles the SMD for the same raw difference.
- **On the raw scale the three trials are closer:** a between-group difference of 8.5-11% of the scale for Pan (WOMAC 42.4/500; VAS 11.4/100), 13% for Aiad (2.6/20, change scores), and 17% for Alimoradi (17.2/100, change scores).

## Data (transcribed from the papers, 2026-10-15)

| Trial (PMID) | Arms, duration | Pain measure | Metformin | Placebo | g (SE) |
|---|---|---|---|---|---|
| Pan 2025, JAMA (40274279; PMC12022862) | XR 2,000 mg/day vs placebo, 6 months; ITT 54/53 | VAS pain, SMD as published | | | 0.43 (0.207) |
| Alimoradi 2023, Arthritis Res Ther (36879307; PMC9990216) | 1.5 g/day vs placebo, 4 months | KOOS pain, end of treatment, higher = better | 70.8 ± 19.1 (n 44; 27 completed) | 50.5 ± 19.0 (n 44) | 1.056 (0.228) |
| Aiad 2024, Inflammopharmacology (38869746; PMC11300470) | 500 mg twice daily + celecoxib vs placebo + celecoxib, 12 weeks | WOMAC pain 0-20, week 12, lower = better | 7.68 ± 1.406 (n 25) | 10.24 ± 1.877 (n 25) | 1.519 (0.321) |

Baselines: Alimoradi KOOS pain 54.9 ± 18.8 vs 51.8 ± 19.0; Aiad WOMAC pain 12.00 ± 2.062 vs 11.96 ± 1.695.

## Pools

| Pool | k | SMD (95% CI, DL) | HKSJ 95% CI | I² | tau² |
|---|---|---|---|---|---|
| All three | 3 | 0.97 (0.36 to 1.57) | -0.38 to 2.31 | 78% | 0.22 |
| Without Aiad | 2 | 0.74 (0.12 to 1.35) | not meaningful at k = 2 | 76% | 0.15 |
| Without Alimoradi | 2 | 0.95 (-0.12 to 2.01) | not meaningful at k = 2 | 88% | 0.52 |
| Pan alone | 1 | 0.43 (0.02 to 0.83) | | | |

Leaving out either small trial leaves the other one's large effect against Pan's 0.43, so heterogeneity stays high (76% and 88%). Neither leave-one-out pool gives a stable estimate with only two trials.

Reproduce: `python meta_oral.py` (Python standard library only); `test_meta_oral.py` checks these values.
**Sealed check:** job `med-checks-v1` (2026-10-16 06:43-06:44Z) ran `meta_oral.py` and its tests in a clean container; every value above, including the leave-one-out row, comes from that run's `pool.json`.

## Reading

- **How to read this:** the evidence fits a modest effect of about 0.4 from the one well-conducted trial, plus two small trials with larger effects whose size can be traced to design and reporting features. A pooled effect above 1 for oral metformin is not supported once those features are taken into account. That matches the audit's planning value of about 0.4.
- **For the published meta-analyses:** pools of 1.3 (Kao 2026) and 2.0 (Chen Z 2026) are larger than anything these three oral placebo-controlled trials give together. They must draw on other designs: topical gel, cohorts or add-on comparisons. Readers can check which ones.
- **What this note does not claim:** it does not say either small trial is wrong or misconducted. The 50/60 discrepancy and the unstated imputation are reporting questions, best put to the authors.

## Is this new?

The six 2025-2026 meta-analyses pool oral and topical trials, or RCTs and cohorts (see the audit). The two we could read in full (Guo 2025; Chen K 2026) do not run an oral, placebo-only RCT pool with a small-sample (HKSJ) interval, and do not mention the Aiad 50-vs-60 discrepancy or its narrow SDs. The four paywalled ones were read as abstracts only, so we cannot rule out that one of them does something similar.

## Limits

- k = 3. Any between-trial estimate is unstable, and the result depends on the choice of method (DL vs HKSJ), as shown.
- Pain measures differ (VAS, KOOS, WOMAC). Combining them as SMDs assumes the scales measure the same construct.
- The Alimoradi and Aiad effects use end-of-treatment SDs because neither paper reports SDs of change.
- Pan's SMD is the published VAS value. Our own WOMAC-based conversion (about 0.40) would lower the pool slightly.
- Transcription was done by AI agents from the PMC full text and checked against the tables. Code and numbers are open for anyone to check.
