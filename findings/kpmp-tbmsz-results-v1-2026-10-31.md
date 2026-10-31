# Results v1: size-adjusted TBM thickness in KPMP's open pathomics vectors still does not track atrophy (2026-10-31)

MV2 of Munim, Inc. Researched, run and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Graded exactly as pre-registered in `kpmp-tbmsz-prereg-v1-2026-10-30.md` (tag v0.9.28, published before the code and before any size-adjusted value existed). Job `kpmp-tbmsz-v1`, run 2026-10-31 00:24-00:31 UTC, Python 3.12.15, modules from tag v0.9.29 (`kidney.kpmp_tbmsz` 1.0, code unchanged). 12 of 12 offline tests passed. Status `ok`. Peak memory 0.31 GB. Graded by hand from the job's `results.json` against the rules below, then checked against the job's own grades and Holm values (they agree).

## Headline

1. **No.** Removing tubule size per tubule does not uncover an atrophy gradient. A participant's median size-adjusted TBM thickness against the KPMP pathologists' tubular atrophy %: version-stratified rho +0.082, one-sided p 0.12, n 222. The primary test fails.
2. **Against baseline eGFR it passes, weakly:** rho -0.124, p 0.026, n 247 (unadjusted on the same participants: -0.100). After Holm adjustment across the three tests, p 0.077, so it is **not confirmed**.
3. **Adjustment hardly reorders participants.** The size line is real but shallow (TBM about 5-6% thicker per doubling of tubule size), and the adjusted feature correlates +0.985 with the plain median it replaces.

One of three predictions held (A2).

## Gate

358 of 361 listed packages read (99.2%; the same 3 v1 packages as in every earlier pass: the job's input check found exactly the 3 expected uncached packages), no read errors. The score file (sheet "Data Table", 426 participants) and the clinical file (973) loaded. 247 participants with packages, 227 with scores, 247 with clinical data, 247 with a `tbm_adj` value. Every test met the 60-participant floor. **Passed.**

Consistency check: the size lines were fitted on 266,897 v1 and 466,752 v2 tubules with both values positive. These equal the tubule totals minus the zero-TBM rows counted in `kpmp-tbm0-twins-results-v1-2026-10-28.md` (316,953 - 50,056 and 518,756 - 52,004) to the row. The plain-median comparator reproduces Z5 and Z6 of that note to the printed digit (+0.062 and -0.100).

## Size line (descriptive)

| | Tubules | Intercept | Slope (ln TBM on ln size) | Per doubling of size |
|---|---|---|---|---|
| v1 (`Area (pixel^2)`) | 266,897 | 1.129 | 0.064 | +4.5% |
| v2 (box area) | 466,752 | 0.831 | 0.083 | +5.9% |

Median TBM thickness (pixels; microns at 0.2527 per pixel) in each quarter of the version's tubule sizes, smallest first:

| | Q1 | Q2 | Q3 | Q4 | Q4 / Q1 |
|---|---|---|---|---|---|
| v1 | 5.37 (1.36) | 5.60 | 6.02 | 6.55 (1.65) | 1.22 |
| v2 | 4.81 (1.22) | 5.33 | 5.71 | 6.09 (1.54) | 1.27 |

Larger tubules carry thicker measured TBM in both layouts. Both slopes are above the pre-registered "nearly flat" bound (|slope| < 0.05), so A1 is graded as a new test, not as a repeat of Z5. They are close to it, though, which fits headline 3.

## Grades

| | Test | rho (n) | v1 / v2 | p (one-sided) | Holm p | Predicted | Grade |
|---|---|---|---|---|---|---|---|
| A1 | `tbm_adj` vs tubular atrophy %, rho > 0 (primary) | +0.082 (222) | +0.104 / +0.058 | 0.116 | 0.116 | pass (low confidence) | **fail** |
| A2 | `tbm_adj` vs baseline eGFR, rho < 0 | -0.124 (247) | -0.090 / -0.165 | 0.026 | 0.077 | pass (low confidence) | **pass, not confirmed** |
| A3 | A1 holding small share fixed, partial rho > 0 | +0.122 (222) | +0.116 / +0.129 | 0.032 | 0.077 | fail (low confidence) | **pass, not confirmed** |

Strata: 117 v1 + 105 v2 participants for atrophy, 136 + 111 for eGFR. Within-layout rho has no p-value (as pre-registered). On A3's rows, the unadjusted rho is +0.082.

## Readings fixed in advance, applied

- **Size line not flat** (0.064 and 0.083): the adjustment is a new test.
- **A1 fail:** the size mix does not explain the earlier null. Together with R2 of `kpmp-twinrel-results-v2-2026-10-30.md` (TBM thickness is reproducible tubule by tubule, rho 0.46 between serial sections), KPMP's TBM thickness, adjusted or not, does not track the pathologists' atrophy scores at participant level in these files. It is dropped from the discovery features of MV2's Kidney AI entry, and the finding goes into the public pitfalls guide (`kpmp-open-pathomics-pitfalls-v2-2026-10-31.md`).
- **A1 and A2 disagree:** A1, the pathologists' own score, is primary. A2's pass is weak and not Holm-confirmed.
- **A3 passed while A1 failed.** The pre-registration fixed readings for A3 only when A1 passes, so none applies and we do not substitute one. Plain arithmetic only: the adjusted feature leans slightly against small share (rho -0.095), which itself tracks atrophy strongly (+0.346). Holding small share fixed removes that pull and lifts the rho from +0.082 to +0.122. It is still weak and not Holm-confirmed.

## Reported, not graded

Two-sided, version-stratified Spearman rho with permutation p (10,000 shuffles). Sixteen lines, with no correction for multiple comparisons.

| Pair | rho | n | p |
|---|---|---|---|
| plain median ln TBM vs atrophy (Z5 repeat) | +0.062 | 222 | 0.35 |
| plain median ln TBM vs eGFR (Z6 repeat) | -0.100 | 247 | 0.12 |
| `tbm_adj`, size floor (tubules >= 25th size percentile) vs atrophy | +0.092 | 222 | 0.17 |
| `tbm_adj`, size floor vs eGFR | -0.135 | 247 | 0.036 |
| plain median, size floor vs atrophy | +0.089 | 222 | 0.19 |
| plain median, size floor vs eGFR | -0.123 | 247 | 0.056 |
| small share vs atrophy | +0.346 | 222 | 0.0001 |
| small share vs eGFR | -0.349 | 247 | 0.0001 |
| `tbm_adj` vs interstitial fibrosis % | +0.012 | 221 | 0.86 |
| `tbm_adj` vs age band | +0.065 | 247 | 0.32 |
| `tbm_adj` vs diabetes history | +0.181 | 246 | 0.004 |
| `tbm_adj` vs albuminuria band | +0.061 | 160 | 0.44 |
| `tbm_adj` vs proteinuria band | +0.215 | 151 | 0.009 |
| `tbm_adj` vs small share | -0.095 | 247 | 0.14 |
| `tbm_adj` vs plain median | +0.985 | 247 | 0.0001 |
| `tbm_adj` vs eGFR, small share held fixed | -0.166 | 247 | 0.009 |

Size-floor cut-offs, as in `kpmp-zs-results-v1-2026-10-29.md`: 8,784.5 pixel^2 (v1) and a box area of 15,660 (v2). The small-share lines repeat that note's figures exactly.

**One pattern worth a later test, not a finding.** The adjusted feature tracks diabetes history (+0.18) and the proteinuria band (+0.22), but not atrophy (+0.08) or fibrosis (+0.01). That is the direction of a classic morphometry result: in 35 people with type 1 diabetes, proximal TBM width was 915 +/- 320 nm against 558 +/- 116 nm in 20 controls (P = 0.0005), and was "only weakly" related to interstitial expansion (r = 0.29, NS) (Brito et al., Kidney Int 1998). That study measured TBM width with the orthogonal intercept method on a different scale and in a different population, so the two cannot be compared directly. Here the diabetes line is one of sixteen uncorrected descriptive lines on participants already used in several earlier studies, and the plain median against diabetes was not computed in this job. In our earlier Q2 split-half screen (58 feature-clinical pairs, unadjusted medians), TBM thickness against proteinuria was carried from exploration but not confirmed (Holm p 0.44), and no TBM pair was confirmed. It is a hypothesis for data we have not used, such as the Kidney AI Discovery Challenge's common image set, not a result.

## What this means

- **For users of KPMP's open pathomics files:** measured TBM thickness rises with tubule size (about 22-27% from the smallest to the largest quarter). Removing that does not make TBM track the pathologists' atrophy scores. If you need an atrophy-linked tubule feature from these files, the share of small tubules is far stronger (+0.35) and needs no TBM column.
- **For MV2's Kidney AI entry:** TBM thickness is out of the discovery features, adjusted or not. It stays as a secondary, reported feature, with the diabetes pattern above as a hypothesis to test on the challenge's own data before anything is claimed.
- **For method:** a significant size line does not mean the adjustment matters at participant level. Report the correlation between the adjusted and the plain feature beside any adjusted result.

## Prior art

As in the pre-registration (searched 2026-10-30): we found no size-adjusted TBM thickness in KPMP's released vectors and no test of it against the KPMP pathologists' atrophy scores. A NEPTUNE study (Kidney International 2025, PMC12302419) measured thicker TBM in pre-atrophic and atrophic tubules in its own segmentation; this result does not contradict it, because it concerns a participant-level summary of a different pipeline's measurement.

## Limits

- One straight line per version on the log scale. The quarter medians rise roughly evenly, so the line is a fair summary, but some size remains in the residuals.
- The v2 size is a bounding box, which depends on orientation. Pixel sizes differ slightly between scanners.
- Zero-TBM rows are left out, and they are not random (`kpmp-twinrel-results-v2-2026-10-30.md`, R5; `kpmp-zs-results-v1-2026-10-29.md`).
- Convenience sample of research biopsies, enriched for diabetic and hypertensive kidney disease and AKI; baseline values only. Same participants as the earlier studies: not an independent replication.
- One model family wrote, tested, ran and graded this; no human has reviewed it. Only aggregate statistics are published. No package IDs, boxes, images or per-participant values are released.

## Files

- Code: `../kidney/kpmp_tbmsz.py` 1.0 with tests `../kidney/test_kpmp_tbmsz.py` (tag v0.9.29); readers `../kidney/kpmp_tbm0.py`, `../kidney/kpmp_zs.py`, `../kidney/kpmp_q2.py`, `../kidney/kpmp_fill.py`.
- Pre-registration: `kpmp-tbmsz-prereg-v1-2026-10-30.md`.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
- Brito PL, Fioretto P, Drummond K, et al. Proximal tubular basement membrane width in insulin-dependent diabetes mellitus. Kidney Int. 1998;53(3):754-761. https://doi.org/10.1046/j.1523-1755.1998.00809.x
- Clinical relevance of computationally derived tubular features ... in MCD/FSGS, Kidney International 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC12302419/
