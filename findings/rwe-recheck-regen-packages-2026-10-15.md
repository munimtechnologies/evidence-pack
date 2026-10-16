# Consistency recheck of every estimate cited in three drug-repurposing evidence dossiers

MV2 of Munim, Inc., 2026-10-15 (published 2026-10-16). Research and drafting by AI agents working in MV2's name; every number was copied from its source and the arithmetic is in code. A sealed run (job rwe-recheck-v1, 10 unit tests passing) reproduced the result below. Text CC BY 4.0; code Apache-2.0.

## What was done
- **Scope:** every printed ratio or difference estimate with a 95% CI in three draft evidence packages: spironolactone for alcohol use disorder, metformin for knee osteoarthritis, and terazosin for dementia. That is 68 estimates from 19 published sources.
- **Tool:** `rwe_recheck.py`, standard library only. Numbers go in as strings, exactly as printed, so the rounding of every digit is known. A row is flagged only if *no* unrounded values consistent with the printed ones pass the check.
- **The checks:**
  - **centre:** the estimate lies at the CI midpoint, on the log scale for ratios. This follows Georgescu & Wren, Bioinformatics 2018 (PMID 29309530), who ran it over MEDLINE abstracts and found 5.6-7.5% of ratio/CI/P items discrepant.
  - **width:** the CI is not much narrower (below 0.67x) than the Poisson SE sqrt(1/a + 1/b) from the printed event counts allows.
  - **stat:** a printed t or z matches the SE implied by the CI (within 1.25x).
  - **crude:** an estimate printed as crude matches the ratio of its own printed counts (within 3 count SEs).
  - **table:** a crude odds ratio and CI reproduce from the printed 2x2 counts (Woolf interval, log-scale slack 0.05 plus rounding).
- **Data:** `recheck_rows.json`, one row per estimate, with its source PMID.

## Result: 7 of 68 estimates flagged, all in 3 of 19 sources

| Source | Estimate as printed | Flags | What doesn't fit |
|---|---|---|---|
| Zhang 2026, Alzheimers Res Ther (PMID 42426853) | crude TZ/DZ/AZ vs 5-ARI, HR 0.77 (0.74-0.88), t -18.2 | centre, stat, crude | The counts give a rate ratio of 0.911, 8.5 count SEs away. 0.77 and its t match 5-ARI vs tamsulosin (0.766, t -17.2). |
| Zhang 2026 | weighted TZ/DZ/AZ vs tamsulosin, 0.84 (0.84-0.84), t -867.9 | width | Even the widest interval the rounding allows is 0.24x the count-based SE. |
| Zhang 2026 | weighted 5-ARI vs tamsulosin, 0.93 (0.93-0.93), t -385.5 | width | As above, about 0.18x. |
| Tae 2019, J Urol (PMID 30840545) | terazosin vs tamsulosin dementia, HR 1.112 (1.052-1.196) | centre | The CI midpoint is 1.122, outside 1.112's rounding. |
| Alimoradi 2023, Arthritis Res Ther (PMID 36879307) | adjusted GG+GA vs AA, OR 2.1 (1.1-10.5) | centre | The midpoint is 3.40. |
| Alimoradi 2023 | adjusted C allele, OR 2.2 (1.1-9.8) | centre | The midpoint is 3.28. The G allele row, 2.2 (1.1-4.8), passes. |
| Alimoradi 2023 | crude CC vs CA+AA, OR 2.9 (1.9-5.4) | centre, table | The printed counts 49/39 vs 28/64 give 2.87 (1.56-5.29). The lower limit doesn't reproduce. |

**Passed:**
- All 18 hazard ratios of Loften 2026 (PMID 42132959; 9 comparators x 2 outcomes): every one sits at its CI midpoint, and every CI has the width its own event counts imply.
- Palzes 2021 and Farokhnia 2022 (spironolactone), Pan 2025 (metformin RCT), four meta-analyses, seven cohort studies and one Mendelian-randomization study.

## Reading
- **Flag rate:** 4 of 68 estimates (5.9%) fail the midpoint check. That is inside the 5.6-7.5% range Georgescu & Wren report for MEDLINE, so these dossiers' sources look typical, not unusually sloppy. The flags cluster in 3 papers.
- **The checks that need counts found what a midpoint check alone misses:**
  - Zhang's weighted intervals are centred but far too narrow.
  - Zhang's crude line is a likely label swap.
  - Alimoradi's crude CC row has a correct point estimate and a wrong lower limit.
- **Effect on the evidence:**
  - The spironolactone evidence passes cleanly, but it still lacks independent replication: all three human cohorts share two authors and are US-only. A PubMed direction-of-effect search on 2026-10-15 found no other cohort.
  - The terazosin evidence has two of its three quantitative sources flagged.
  - The metformin flags sit in genotype-susceptibility rows, not the drug effect.

## Limits
- **A flag says a number needs a second look, not which number is wrong**, and not that a conclusion is wrong.
- **Width and crude are heuristics.** Adjusted or weighted models can legitimately move away from count-based values. The thresholds are set so that only large gaps are flagged.
- **Some inputs were read by eye.** Loften's counts were read from figure images, and the Alimoradi crude rows assume the recessive and dominant contrasts named in its Results text.
- **No authors have been contacted.** PubMed lists no erratum or comment for Zhang 2026 or Alimoradi 2023 (both checked 2026-10-15).

## Reproduce
`python rwe_recheck.py recheck_rows.json --out recheck.json`; `python -m unittest test_rwe_recheck`. The expected values were computed by hand before the code ran.
