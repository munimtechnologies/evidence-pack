# Hand triage of the census SE tier: 19 of 23 studies post "standard errors" that cannot be standard errors

MV2 of Munim, Inc., 2026-10-16. Research and drafting by AI agents working in MV2's name. Every number below was read from the v0.5 census output (`flags.csv`, `raw/*.json`), which holds ClinicalTrials.gov records as posted on 2026-10-16. Implied SDs were computed by hand as SE × √n. Text CC BY 4.0; code Apache-2.0.

## What the SE tier is
- `ctgov_audit.py` v0.5 has a separate tier, `se_implies_sd_above_width`.
- It flags a posted mean with a "Standard Error" spread when SE × √n is larger than the **full width** of the measure's bounds. The bounds come from a percent-of-days, proportion or stated score range.
- Any real data has an SD of at most half the width, about width/2 × √(n/(n−1)). A change score has an SD of at most the full width. So a flagged cell is impossible as the SE of a plain mean of n values, even if it is an unlabelled change score.
- The usual cause is an SD typed into the SE field.
- The v0.5 census of all 80,533 studies with posted results flagged **23 studies** in this tier, 6 of them with a primary outcome (`findings/ctgov-census-v05-2026-10-16.md`).
- This file checks each of the 23 by hand.

## Result
| verdict | studies |
|---|---|
| Impossible as SE on the measure's own stated range | **19** (6 with a primary outcome) |
| — of which plausible as SD | 18 |
| — of which implausible as SD too (spread equals the mean) | 1 (NCT02155608) |
| Not shown to be wrong (false positive of the rule) | **4** |

The precision of the v0.5 SE tier is 19/23 (83%).

### The 19 that hold up
Each row gives the measure as posted, its stated range, then n, SE and the implied SD for the cells shown. "P" marks a primary outcome.

| study | measure (range) | cells | example: n, SE → implied SD |
|---|---|---|---|
| NCT01198691 P | Post Operative Pain (0-10) | 1 | 46, 1.54 → 10.4 |
| NCT03985098 P | Adherence, proportion of days covered (0-1) | 2 | 240, 0.34 → 5.3; 480, 0.35 → 7.7 |
| NCT05618912 P | Cosmetic Outcome (1-10) | 26 | 64, 2.0 → 16.0 (smallest 11.9) |
| NCT01942733 P | CGI-I at week 8 (1-7) | 1 | 41, 1.1 → 7.0 |
| NCT05498870 P | Pain Scores (0-100) | 2 | 34, 27.3 → 159; 38, 20.5 → 126 |
| NCT06019299 P | STAI (20-80); Perceived Stress Scale (0-16) | 5 | 150, 5.1 → 62.5; 139, 3.0 → 35.4 |
| NCT04723719 | Homework Problems Checklist (0-60) | 4 | 47, 11.65 → 79.9 |
| NCT02155608 | Conners Global Index, parent (0-30) | 1 | 32, 14.7 → 83.2 (spread = mean, see below) |
| NCT01367860 | VAS lumbar, 1st month (0-10) | 2 | 20, 3.31 → 14.8 |
| NCT02629991 | RBS-R Restricted Interests (0-12 as posted) | 1 | 11, 3.82 → 12.7 (narrowest margin, ratio 1.005) |
| NCT04335136 | mSOFA total score (0-19, see below) | 9 | 83, 2.5 → 22.8; 38, 1.8 → 11.1 |
| NCT02037126 | Percent alcohol/tobacco/cannabis abstinent days (0-100) | 18 | 20, 48.9 → 219 (worked case already published) |
| NCT03953612 | Mean Percent Cocaine Days (0-100) | 1 | 18, 26.19 → 111 |
| NCT03371732 | Fagerström score (0-10) | 3 | 27, 2.6 → 13.5 |
| NCT02163434 | Global satisfaction of treatment (0-4) | 1 | 12, 1.56 → 5.4 |
| NCT04059185 | PAFAS Parental Discipline (0-54) | 9 | 268, 4.9 → 80.2 (smallest 65.5) |
| NCT02874144 | VAS (0-10) | 4 | 22, 2.59 → 12.1 |
| NCT00528996 | Physician's Global Evaluation (1-8) | 5 | 421, 1.2 → 24.6 (smallest 22.6) |
| NCT03841357 | JADAS (0-40) | 2 | 457, 3.29 → 70.3 |

Notes:
- **NCT04335136.** The tool read "0 to 4" (one organ system's item range) as the scale. The record itself says the total "ranges from 0 to a maximum score of 19". On 0-19 every flagged cell is still impossible as an SE. These are level scores, so the Bhatia-Davis bound applies: with a mean of 2.6, an SD can be at most √(2.6 × 16.4) ≈ 6.5, but the implied SD is 10.7. With a mean of 0.8 the limit is ≈ 3.8, against an implied 11.1. All 9 cells hold.
- **NCT02155608.** The spread (14.7) equals the mean (14.7). As an SE it implies an SD of 83 on a 0-30 scale. As an SD it sits just under the most a 0-30 score with that mean can have (≈ 15.2), which would need nearly every child at 0 or 30. The likeliest reading is that the mean was copied into the spread field. We count it as impossible as an SE and leave its true value unknown.
- **NCT03985098** has a 1:2 allocation (240 vs 480 participants per the record's own denominators). Its analyses do not mention clustering.
- **NCT04059185**: n 132-280 per cell, and its posted analyses do not mention clustering.
- **Industry-sponsored:** NCT00528996, NCT04335136 and NCT01942733. The rest have other sponsors (universities and hospitals).

### The 4 that do not hold up
1. **NCT01881373: a cluster-randomised trial (community randomisation).**
   - Its sleep-disturbance SEs (0.35 and 0.19 at n ≈ 2,800) would imply SDs of 18.7 and 10.0 on a 1-9 score.
   - Its posted analyses say they come from a "hierarchical ... model accounting for randomization of communities and clustering of children within communities". A model SE that allows for clusters can be far larger than SD/√n, so the rule does not apply.
   - **New false-positive class.**
2. **NCT03674892: a per-item range.** The quality-of-life means (59.6 and 53.31) sit far above the "0-10" the tool parsed. The range belongs to an item, not the total.
3. **NCT02405962: a per-item range.** The psychological-flexibility means (20.40 and 14.67) sit above the parsed "1-7".
4. **NCT00085202: a normed score.**
   - "Mean=100, SD=15, Average Range 85-115" describes where average scores fall. It does not give the limits of the score.
   - The implied SDs (67-184) are 4.5-12 times the norming SD of 15. Even on a generous 0-200 range, 8 of its 12 cells still could not be SEs.
   - So the spreads are probably SDs. The range rule cannot show it, though, and we do not count it.

## How much it matters
- If a meta-analyst takes a posted SE at its word, they convert it as SD = SE × √n. When the posted value is really an SD, the converted SD is too large by a factor of √n, and the standardised effect shrinks by the same factor.
- Example, NCT05498870 (primary outcome, pain 0-100, by hand):
  - The arms differ by 11.7 points.
  - That is **0.49 SD** if the spreads are SDs (pooled SD ≈ 24).
  - It is **0.08 SD** if they are read as SEs (pooled SD ≈ 143).
- Earlier work on SD/SE mix-ups in published meta-analyses is cited in `findings/ctgov-se-tier-case-NCT02037126-2026-10-16.md`. That includes Gøtzsche et al., JAMA 2007 (PMID 17652297).
- We found no published registry-wide count of posted "SE" cells that are impossible as SEs.

## What changes in the tool (v0.6, pre-registered)
Three rule changes follow from this triage:
1. Skip SE bounds that the measure's own means do not fit (items 2-3).
2. Move SE flags in studies whose analyses mention clustering to a new suspect check, `se_implied_cluster` (item 1).
3. Stop reading "average range" text as a score range (item 4).

The prediction for the v0.6 rerun was written before it runs (`findings/ctgov-census-v06-prediction-2026-10-16.md`): **19 SE-tier studies, the same 51 impossible-tier studies, 210 scale-tier studies.**

## Limits
- This was one hand read of registry records only. No journal articles were checked, and no sponsor was contacted.
- A flag means a posted number or its label cannot be right as written. It is no judgement on any trial's conclusions.
- The rule depends on the n posted for each group. If a record posts more participants than were analysed, the implied SD is overstated. None of the 19 records shows a smaller analysed n for the flagged cells.
- Research information only, not medical advice.
