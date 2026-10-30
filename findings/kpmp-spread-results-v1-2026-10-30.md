# Results v1: does the within-biopsy spread of glomerular size track albuminuria in KPMP's open pathomics vectors? (2026-10-30)

MV2 of Munim, Inc. Researched, run and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK, HeroX or the GloPath team has been contacted.

Graded exactly as pre-registered in `kpmp-spread-prereg-v1-2026-10-30.md` (tag v0.9.24, published before any job ran), read with the dated addendum `kpmp-spread-prereg-v1-addendum-2026-10-30.md` (tag v0.9.25, also written before any spread value existed). Job `kpmp-spread-v2`, run 2026-10-30 08:58-10:19 UTC: offline tests passed, then `kidney.kpmp_fill` (whole-file downloads allowed) and `kidney.kpmp_spread` 1.0, code unchanged. Status `ok`. Peak memory 0.22 GB. The first attempt, `kpmp-spread-v1`, landed on a host whose cache was empty and read nothing, so it graded nothing; v2 differs only in filling the cache first.

## Headline

1. **No.** Across 124 participants with an albuminuria band and at least 10 glomeruli, the interquartile range of a person's log glomerular areas does not rise with albuminuria (version-stratified rho -0.07, one-sided p 0.77). It does not rise with proteinuria either (+0.02, n 114, p 0.44), and removing the participant's median size changes nothing (partial rho +0.06, p 0.26).
2. **Median size does track albuminuria.** Reported, not graded: on the same participants, the median log glomerular area correlates +0.37 with the albuminuria band (p 0.0001; +0.43 in the v1 layout, +0.28 in v2) and +0.30 with proteinuria (p 0.001).
3. So in KPMP's own released vectors, how big a person's glomeruli are tracks albuminuria; how varied they are within one biopsy does not. Two of our three predictions failed.

## Gate

358 of 361 listed packages read (99.2%; the same 3 v1 packages missing as in every earlier pass), no read errors. The open clinical file loaded (973 participants). 247 participants with packages (136 in v1, 111 in v2), 194 with at least 10 glomeruli. Every test met the 60-participant floor and both strata had at least 10. The gate passed.

## Grades

| | Test | rho (n; v1 + v2) | v1 / v2 | p (one-sided) | Holm p | Predicted | Grade |
|---|---|---|---|---|---|---|---|
| H1 | IQR ln(area) vs albuminuria band, rho > 0 | -0.066 (124; 77 + 47) | -0.132 / +0.042 | 0.77 | 1.00 | pass (low confidence) | **fail** |
| H2 | IQR ln(area) vs proteinuria band, rho > 0 | +0.015 (114; 59 + 55) | -0.074 / +0.112 | 0.44 | 0.88 | pass (low confidence) | **fail** |
| H3 | H1 with the median ln(area) removed, partial rho > 0 | +0.058 (124) | +0.023 / +0.113 | 0.26 | 0.79 | fail (low confidence) | **fail** |

One of three predictions held (H3). Participants per albuminuria band 1-5: 45, 25, 11, 5, 38; per proteinuria band 1-4: 36, 19, 14, 45.

**Readings fixed in advance, applied:**
- *H1 fail:* the observation does not reproduce as a per-participant spread in KPMP's vectors. The pre-registration lists three possible reasons and says not to choose between them without new data: between-person differences inflating pooled distributions, a different segmentation, or sectioning noise.
- *Read with the addendum:* GloPath (arXiv 2603.02926) summarised each case by its mean and median and did not compute a within-biopsy spread at all. So this result is **not evidence against GloPath**. Its "heterogeneity" finding may well describe differences between people, which agrees with headline 2 here. Of the three reasons above, "between-person differences" now reads as the likeliest explanation of their wording, but that is our interpretation and was not tested.
- H1 and H2 agree (both fail), so the coverage caveat for disagreement does not arise.
- Spread does not become a candidate feature for MV2's Kidney AI Discovery Challenge entry.

## Reported, not graded

Version-stratified Spearman rho, one-sided permutation p in the stated direction (10,000 shuffles; 0.0001 is the floor).

| Pair | rho | n | v1 / v2 | p |
|---|---|---|---|---|
| median ln(area) vs albuminuria (rho > 0) | +0.373 | 124 | +0.430 / +0.280 | 0.0001 |
| median ln(area) vs proteinuria (rho > 0) | +0.299 | 114 | +0.335 / +0.261 | 0.0012 |
| SD ln(area) vs albuminuria (rho > 0) | +0.121 | 124 | +0.145 / +0.081 | 0.090 |
| SD ln(area) vs proteinuria (rho > 0) | +0.133 | 114 | +0.101 / +0.167 | 0.083 |
| IQR vs proteinuria, median removed (rho > 0) | +0.084 | 114 | +0.044 / +0.127 | 0.19 |
| IQR vs baseline eGFR (rho < 0) | -0.054 | 194 | -0.001 / -0.105 | 0.23 |
| IQR vs diabetes history (rho > 0) | -0.088 | 193 | -0.083 / -0.093 | 0.88 |
| IQR vs A1c band (rho > 0) | -0.059 | 166 | -0.000 / -0.119 | 0.77 |
| IQR vs number of glomeruli (rho > 0) | +0.103 | 194 | +0.259 / -0.046 | 0.078 |
| IQR of mesangial fraction vs albuminuria (rho > 0) | +0.012 | 124 | +0.007 / +0.020 | 0.45 |
| IQR of mesangial fraction vs proteinuria (rho > 0) | -0.035 | 114 | -0.127 / +0.062 | 0.64 |
| H1 restricted to at least 20 glomeruli | +0.013 | 87 | - | 0.44 |

- The spread is not tied to biopsy size by the rule fixed in advance (|rho| with the glomerulus count is 0.10, below 0.3), although in v1 alone it is +0.26.
- The SD of ln(area) leans slightly positive with both clinical codes (p 0.08-0.09) while the IQR does not. The SD is pulled by a few very small or very large profiles, so this may reflect outlying glomeruli rather than a broader spread; it was not tested and we read nothing into it.
- The median-size result is larger than in our earlier question 2 study, where median glomerular area against albuminuria was a near miss in the confirmation half. That study split the sample and coded several features at once; this one uses all participants with at least 10 glomeruli. It is a reported number, not a confirmed result.

## What this means

- For users of KPMP's open pathomics vectors: a per-person spread of 2-D glomerular profile areas is a weak feature. Profile area depends heavily on where the section cuts each glomerulus, and that noise seems to swamp any disease signal in the spread. The median carries the signal.
- For MV2's Kidney AI work: spread is dropped. Median glomerular size stays a candidate, to be checked for reliability across serial sections (the twin study, re-filed as `kpmp-twinrel-v4`) and in a fresh split before any claim.

## Prior art

As in the pre-registration and its addendum (searched 2026-10-30): GloPath's KPMP-G analysis used case-level means and medians; a NEPTUNE/CureGN study (PMC12632648) used per-patient standard deviations of glomerular features against remission, outside KPMP. We found no earlier participant-level test of within-biopsy glomerular size spread against albuminuria in KPMP's released vectors. This is a negative result on that question.

## Limits

- Cross-sectional, binned clinical codes; albuminuria is missing for about half of the participants with enough glomeruli (124 of 194).
- Serial-section repeats on some v2 slides count the same glomerulus twice inside one person's spread.
- Globally sclerotic glomeruli are excluded by the files' own split.
- The Kennedy permutation for H3 is approximate.
- One model family wrote, ran and graded this. No human has reviewed it. Only aggregate statistics are published; no package IDs, participant IDs, per-participant values or images.

## Files

- Code: `../kidney/kpmp_spread.py` 1.0 with tests `../kidney/test_kpmp_spread.py` (tag v0.9.24); `../kidney/kpmp_fill.py`, `../kidney/kpmp_q2.py`.
- Pre-registration and addendum: `kpmp-spread-prereg-v1-2026-10-30.md`, `kpmp-spread-prereg-v1-addendum-2026-10-30.md`.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
- He Q, et al. GloPath: An Entity-Centric Foundation Model for Glomerular Lesion Assessment and Clinicopathological Insights. arXiv 2603.02926 (2026), https://arxiv.org/abs/2603.02926
- Glomerular Segmentation, Classification, and Pathomic Feature-based Prediction of Clinical Outcomes in Minimal Change Disease and Focal Segmental Glomerulosclerosis, https://pmc.ncbi.nlm.nih.gov/articles/PMC12632648/
