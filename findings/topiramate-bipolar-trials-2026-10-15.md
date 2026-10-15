# Topiramate for alcohol use disorder: the two bipolar trials, read (2026-10-15)

Addendum to [topiramate-aud-registry-pool-2026-10-14.md](topiramate-aud-registry-pool-2026-10-14.md). Research information, not medical advice. Made by MV2 of Munim, Inc. with AI agents (Claude).

The registry pool of 2026-10-14 left two placebo-controlled bipolar trials unread (NCT00550394 and NCT00572117). Both have now been read from the ClinicalTrials.gov API v2 record.

| NCT | Trial | What is posted | Decision |
|---|---|---|---|
| NCT00550394 | Quetiapine plus topiramate or placebo for bipolar mania and alcohol use in adolescents and young adults (randomized, triple-masked, 56 enrolled) | Four primary outcomes, change from baseline to week 12, mean and SD, n 18 (topiramate) and 21 (placebo). Percent heavy drinking days: -14 (SD 25) vs -10 (SD 19). Drinks per day -2.4 (5.1) vs -1.4 (2.3). Drinks per drinking day -7.3 (6.0) vs -7.2 (10.2). Percent days abstinent 14 (23) vs 15 (19). No analysis posted. | Meets the inclusion rule (randomized, placebo-controlled, posted heavy-drinking outcome). Comorbid group (bipolar disorder, young people). Hedges' g on percent heavy drinking days **-0.178** (hand-computed). |
| NCT00572117 | Adjunctive topiramate for alcohol dependence in bipolar disorder (randomized, triple-masked, 12 enrolled) | One drinking outcome: change in drinks per heavy drinking day, mean and 95% CI, n 5 vs 7 (3 and 5 completed). Topiramate -1.38 (-4.93 to 2.17), placebo -0.69 (-1.68 to 0.31). | Excluded by the pool's rule, which needs a heavy-drinking-days outcome. For the record, g on the posted measure would be about -0.32. |

## Effect on the pool

The nine-trial pool was registry-checked before this trial was read, so NCT00550394 is added as **sensitivity-only** (`sensitivity_only` in `studies/topiramate_aud.json`). The checked main pool and its general/comorbid split stay as published. Hand-computed:

- all ten trials: g about **-0.292** (95% CI about -0.48 to -0.10), against -0.301 for the nine;
- comorbid samples with it: about -0.11 (k = 6), against -0.103 (k = 5).

So the bipolar trial changes nothing material. It is one more small comorbid-sample trial with a small effect. The sealed job registry-pool-v4 re-downloads the record and recomputes these numbers. Its output replaces the hand values when it lands.

A registry note: NCT00572117 lists "Drug: Topiramate" as the intervention of its placebo arm. This is the same kind of slip seen in NCT00381043 (acamprosate) and NCT00920829 (naltrexone).
