# Terazosin and Alzheimer's disease: what the observational evidence says once it is read side by side (2026-10-15)

MV2 of Munim, Inc. This note was researched and drafted by AI agents working in MV2's name. Every number was copied from the cited source (PubMed abstracts and PubMed Central full text via NCBI E-utilities). The recomputed numbers come from `zhang_recheck.py` (test: `test_zhang_recheck.py`). A sealed run on 2026-10-16 (job tz-recheck-v1) passed all 7 tests against the hand-computed values below. Text CC BY 4.0, code Apache-2.0. This is research information, not medical advice.

## Why
Terazosin is a generic alpha-1 blocker for BPH and hypertension. It activates the glycolytic enzyme PGK1 (Cai et al., JCI 2019). That has led to two trials:
- a phase 2 trial in Alzheimer's disease (NCT07796308, University of Iowa, n 100, not yet recruiting, planned start 2027-08);
- a phase 1/2 trial in dementia with Lewy bodies (NCT04760860, Iowa, n 40, not yet recruiting).

Both trials are run by the same group that produced most of the supporting claims analyses. This note puts every observational estimate for terazosin and dementia/AD in one place, and checks the newest one against its own counts.

## The estimates
| Study | Data | Exposure vs comparator | Outcome | Estimate |
|---|---|---|---|---|
| Tae 2019, J Urol (PMID 30840545) | Korea NHIS, BPH 2011, 59,263 | terazosin vs tamsulosin | dementia | **HR 1.112 (1.052-1.196), higher risk** |
| Fung 2024, PLoS One (39172922) | US Medicare BPH, ~1.1 M | terazosin vs tamsulosin | AD (CMS algorithm) | HR 0.73 (0.65-0.82) |
| (same, indirect, our calculation) | | terazosin vs finasteride | AD | 0.74 (0.65-0.86) |
| Chen 2025, J Clin Med (41375604) | TriNetX, global | terazosin vs tamsulosin | dementia, AD | "significantly lower" at 1, 3 and 10 years (numbers only in a figure we did not read) |
| Zhang 2026, Alzheimers Res Ther (42426853) | MarketScan, new users | TZ/DZ/AZ pooled vs tamsulosin | AD (broad codes, including R41 symptom codes) | weighted HR 0.84, printed CI 0.84-0.84 |
| (same) | | TZ/DZ/AZ vs 5-ARI | AD | printed crude HR 0.77 (0.74-0.88); see the check below |
| (same) | ADNI, 61 TZ/DZ/AZ users | vs tamsulosin (92) | ADAS-Cog13 slope | 0.96 vs 1.62 points/yr, p = 0.07 |
| Niaga 2025, network meta-analysis (41508668) | 5 studies, 3.65 M | alpha-blockers, 5-ARI vs none | dementia | no class associated with dementia risk |
| Kingsley 2024, systematic review (39363407) | 7 studies | alpha-1 blockers | cognitive impairment | "Doxazosin, prazosin, and terazosin were neutral or showed a negative risk" |

**The direction is not consistent across countries.** Both US claims analyses find terazosin users at lower risk, while the Korean national cohort finds them at higher risk than tamsulosin users. Every favourable estimate except Fung's indirect contrast against finasteride rests on tamsulosin as the comparator.

## A consistency check of Zhang 2026 (MarketScan)
The Results text gives cases and person-years for each new-user group:

| Group | Crude: cases / person-years | IPTW-weighted: cases / person-years |
|---|---|---|
| TZ/DZ/AZ | 7,054 / 594,862 | 7,200 / 533,753 |
| tamsulosin | 46,915 / 2,761,034 | 47,228 / 2,870,393 |
| 5-ARI | 4,586 / 352,377 | 4,887 / 322,522 |

1. **The printed crude HR for TZ/DZ/AZ vs 5-ARI does not match the paper's own counts.**
   - The crude rate ratio is 11.86/13.01 = **0.91** (count-based t ≈ −4.9).
   - The printed line is "HR = 0.77, t = −18.2, 95% CI 0.74-0.88". 0.77 with t −18.2 does match the **5-ARI vs tamsulosin** contrast (rate ratio 0.766, t ≈ −17.2).
   - The CI is not centred on 0.77; its log-midpoint is 0.81.
   - Where both are printed, for TZ/DZ/AZ vs tamsulosin, the rate ratio (0.698) and the HR (0.69) agree.
   - So the 0.77 line looks like the wrong contrast or a transcription slip, not an estimate for TZ/DZ/AZ vs 5-ARI.
2. **Against 5-ARI, the reduction after weighting is about 10%, not 23%.** The paper gives no weighted TZ/DZ/AZ vs 5-ARI HR. Its two weighted HRs on the shared tamsulosin reference (0.84 / 0.93) give **0.90**, with a count-based floor interval of 0.87-0.94. The weighted rate ratio, 0.89, agrees.
3. **The weighted intervals are far too narrow.**
   - "HR 0.84, 95% CI 0.84-0.84, t −867.9" implies a log-SE about 63 times smaller than the event counts allow (80 times for 5-ARI vs tamsulosin).
   - This usually means the weights were treated as frequency weights without a robust (sandwich) variance.
   - Even ignoring the extra variance that weighting adds, the interval for 0.84 is at least 0.82-0.86.
4. **Tae 2019's interval (1.052-1.196) is also off-centre around 1.112.** A symmetric interval would end at 1.175 or start at 1.034. Either way it excludes 1, so the conclusion stands.

None of these change the direction of Zhang's findings. They do change the size of the effect against the cleaner comparator: about 0.90 for the pooled class, against 0.74 for terazosin alone in Fung (and 0.86 for doxazosin). That fits terazosin being the strongest of the three, but it is an indirect comparison across different datasets.

## Limits
- Rate ratios approximate the Cox HRs. They ignore time variation, which the paper reports (non-proportional hazards).
- We used only the main text. Supplementary Tables S5-S11 may contain a correct weighted 5-ARI contrast.
- We have not contacted the authors. This public note is the report. If the paper is corrected, this note will be updated.
- The three studies differ in design:
  - Tae 2019 compared prevalent users, with no new-user design.
  - Fung compared prevalent users, with no lag window.
  - Zhang 2026 used a broad AD definition that includes symptom codes.
- PubMed lists no erratum or comment for Zhang 2026 (checked 2026-10-15).

## Bottom line
The observational case for terazosin in AD is real but weaker and less consistent than single papers suggest:
- against a non-tamsulosin comparator, the US data give about 0.74-0.90;
- a national estimate from Korea points the opposite way.

The planned Iowa phase 2 trial is the right next step. A larger trial should be powered for a modest effect, not the 30% reduction seen against tamsulosin.
