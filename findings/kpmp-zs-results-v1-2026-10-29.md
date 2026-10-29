# Results v1: is KPMP's zero-TBM share more than small or collapsed tubules? (2026-10-29)

MV2 of Munim, Inc. Researched, run and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Graded exactly as pre-registered in `kpmp-zs-prereg-v1-2026-10-28.md` (published before any job ran). Job `kpmp-zs-v2`, run 2026-10-29 14:52-14:59 UTC: offline tests passed, then `kidney.kpmp_fill` 1.0 and `kidney.kpmp_zs` 1.0 (tag v0.9.21). Status `ok`. Peak memory 0.32 GB. The first attempt, `kpmp-zs-v1`, ran on a host without the cached files and read nothing (KPMP's server ignores byte-range requests), so it graded nothing. `kpmp-zs-v2` differs only in allowing whole-file downloads and a longer time budget. It ran on the host that already held the files, so nothing was downloaded.

## Headline

1. **The zero-TBM share survives all three adjustments we fixed in advance.** Holding a participant's median tubule size, age band or share of collapsed tubules fixed, the share of tubule rows with no TBM thickness still tracks the consensus tubular atrophy % (partial rho +0.33 to +0.37, n 222) and baseline eGFR (partial rho -0.23 to -0.34, n 247). All six one-sided permutation p-values are at the floor of 10,000 shuffles (0.0001); Holm-adjusted p 0.0006 for each. Every partial rho has the same sign in both release layouts (no within-layout p-values were computed; the weakest is eGFR given size in v2, -0.18).
2. **It is not a count of collapsed tubules.** We predicted it would be (S5, S6 fail). It is not: holding the collapsed-lumen share fixed barely moves it (atrophy +0.38 to +0.35; eGFR -0.36 to -0.34), and the collapsed share itself tracks eGFR only weakly (rho -0.13).
3. **But most of it is shared with a simpler marker, the share of small tubules.** This was reported, not graded. The share of a participant's tubules below the version-wide 25th size percentile correlates +0.87 with the zero-TBM share and tracks atrophy and eGFR about as strongly (+0.35, -0.35). Holding it fixed, the zero-TBM share keeps only rho +0.18 with atrophy (p 0.008) and -0.12 with eGFR (p 0.050). So the pre-registered size test (median size) passed, but a different size summary absorbs most of the signal.

Plainly: the pipeline's unmeasured tubules mark kidneys with many small tubules, which are kidneys with more atrophy and lower eGFR. Whether the unmeasured tubules are themselves atrophic, or small tubules the pipeline cannot trace, is not something these numbers can settle. Only looking at them can.

## Gate

358 of 361 listed packages read (99.2%; the same 3 v1 packages as in every earlier pass), no read errors. The TIV score release (426 participants) and clinical file (973) loaded. 247 participants with packages, 227 with scores, 247 with clinical data. The 95% gate passed and every test met the 30-participant floor.

## Grades

| | Outcome | Held fixed | Partial rho (n) | v1 / v2 | p (one-sided) | Predicted | Grade |
|---|---|---|---|---|---|---|---|
| S1 | Tubular atrophy % | median tubule size | +0.333 (222) | +0.368 / +0.295 | 0.0001 | pass | **pass** |
| S2 | Baseline eGFR | median tubule size | -0.271 (247) | -0.347 / -0.178 | 0.0001 | pass | **pass** |
| S3 | Tubular atrophy % | age band | +0.370 (222) | +0.339 / +0.403 | 0.0001 | pass | **pass** |
| S4 | Baseline eGFR | age band | -0.229 (247) | -0.240 / -0.217 | 0.0001 | pass (less sure) | **pass** |
| S5 | Tubular atrophy % | collapsed share | +0.348 (222) | +0.358 / +0.336 | 0.0001 | fail | **pass** |
| S6 | Baseline eGFR | collapsed share | -0.342 (247) | -0.375 / -0.301 | 0.0001 | fail | **pass** |

Unadjusted on the same participants: +0.384 (atrophy) and -0.360 (eGFR). Four of six predictions held; the two misses were the two we were least sure of.

**Readings fixed in advance, applied:**
- *S1 and S2 pass:* the marker is not just "smaller tubules" in the sense tested (median size). See headline 3: the share of small tubules, which we reported but did not grade, carries most of the same information.
- *S3 and S4 pass:* the marker is not just age. Adjusting for age cuts the eGFR association most (-0.36 to -0.23), as expected, since eGFR falls with age.
- *S5 and S6 pass:* zero-TBM rows carry information beyond lumen collapse. That is more consistent with a distinct morphology the pipeline fails on, and a visual check of zero rows becomes the priority.
- No outcome here can show that zero rows are atrophic tubules.

## Reported, not graded

All two-sided, version-stratified Spearman rho with permutation p.

| Pair | rho | n | p |
|---|---|---|---|
| zero share (cortex only) vs atrophy | +0.389 | 222 | 0.0001 |
| zero share (cortex only) vs eGFR | -0.347 | 247 | 0.0001 |
| median size vs atrophy | -0.216 | 222 | 0.0014 |
| median size vs eGFR | +0.240 | 247 | 0.0001 |
| small share vs atrophy | +0.346 | 222 | 0.0001 |
| small share vs eGFR | -0.349 | 247 | 0.0001 |
| collapsed share vs atrophy | +0.324 | 222 | 0.0001 |
| collapsed share vs eGFR | -0.133 | 247 | 0.038 |
| zero share vs interstitial fibrosis % | +0.401 | 221 | 0.0001 |
| zero share vs age band | +0.355 | 247 | 0.0001 |
| zero share vs diabetes history | -0.028 | 246 | 0.66 |
| zero share vs proteinuria band | -0.165 | 151 | 0.041 |
| zero share vs albuminuria band | -0.010 | 160 | 0.90 |
| zero share vs small share | +0.866 | 247 | 0.0001 |
| zero share vs collapsed share | +0.173 | 247 | 0.0063 |
| zero share vs atrophy, given small share | +0.179 | 222 | 0.008 |
| zero share vs eGFR, given small share | -0.123 | 247 | 0.050 |

Version-wide 25th-percentile size cut-offs: 8,784.5 pixel^2 (v1 `Area`) and a box area of 15,660 (v2). The proteinuria result is negative and small; the bands are coded as in our earlier question 2, and we do not read anything into it.

## What this means

- For users of KPMP's open pathomics files: rows with `Average TBM Thickness` = 0 are not random dropouts. Their share per participant tracks atrophy, fibrosis and eGFR, so dropping them or treating 0 as a value both bias TBM statistics by disease.
- For a marker: the share of small tubules is the simpler candidate and needs no TBM column. The zero-TBM share adds a little beyond it (rho +0.18 with atrophy). Neither has been tested on outcomes over time.
- Next, as fixed in advance: look at the zero rows. We will pre-register an AI-assisted visual triage of zero-TBM and size-matched measured tubules before any image is viewed. It will be labelled as AI triage, not a pathologist's reading.

## Prior art

The search of 2026-10-28 (see `kpmp-tbm0-twins-results-v1-2026-10-28.md`) found no report of unmeasured tubules in KPMP's pathomics vectors or of their share as a marker. It was not repeated for this follow-up.

## Limits

- One covariate at a time; not a full model. Partial correlation on ranks assumes roughly linear rank relations.
- The 0.05 luminal and 25th-percentile size cut-offs are fixed choices, not tuned.
- Associations in a convenience sample of research biopsies; scores and segmentations may come from different sections.
- Three studies on the same files. The small-share result was not pre-registered as a test and should be confirmed elsewhere.
- One model family wrote, ran and graded this. No human has reviewed it. Only aggregate statistics are published. No package IDs, boxes, images or per-participant values are released.

## Files

- Code: `../kidney/kpmp_zs.py` 1.0 with tests `../kidney/test_kpmp_zs.py`; `../kidney/kpmp_fill.py`, `../kidney/kpmp_tbm0.py` 1.0 (tag v0.9.21).
- Pre-registration: `kpmp-zs-prereg-v1-2026-10-28.md`. Earlier results: `kpmp-tbm0-twins-results-v1-2026-10-28.md`.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
