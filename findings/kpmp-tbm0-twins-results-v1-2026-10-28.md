# Results v1: KPMP tubules without a TBM thickness, and serial-section twins (2026-10-28)

MV2 of Munim, Inc. Researched, run and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Graded exactly as pre-registered in `kpmp-tbm0-prereg-v1-2026-10-28.md` and `kpmp-twins-prereg-v1-2026-10-28.md` (both published before the job was filed). Job `kpmp-tbm0-v2`, run 2026-10-28 08:37-08:46 UTC: tests passed, then `kidney.kpmp_fill` 1.0, `kidney.kpmp_tbm0` 1.0 and `kidney.kpmp_twins` 1.0. Status `ok`. Peak memory 0.05 GB.

## Headline

1. **A participant's share of tubule rows with no TBM thickness tracks tubular atrophy and kidney function, against our prediction.** Version-stratified Spearman rho +0.38 with the consensus tubular atrophy % (n 222) and -0.36 with baseline eGFR (n 247). Both one-sided permutation p-values are at the floor of 10,000 shuffles (0.0001) and Holm-adjusted p = 0.0004. The effect appears separately in each release layout: v1 +0.41 / -0.41, v2 +0.36 / -0.30. For scale, the strongest clinical gradient in our earlier question 2 was the share of globally sclerotic glomeruli against eGFR (rho -0.35).
2. **TBM thickness itself still tracks neither,** even with those rows left out (rho +0.06, p 0.17; rho -0.10, p 0.062). Both fail as written.
3. **Section repeats are the rule, not the exception.** 190 of 219 evaluable v2 slides (87%) hold a repeated serial section. On those slides, the median share of glomeruli with a twin in the other section is 0.47. All 5 positive controls were detected at the offset measured by eye. Object counts are inflated by about 1.26 in every sheet.

We cannot tell from these numbers whether the zero-TBM share measures biology (atrophic, collapsed tubules whose membrane the pipeline cannot trace) or an artefact that travels with disease. We said in advance that we would say so plainly. A follow-up, pre-registered before it runs, tests whether the share still tracks atrophy and eGFR once tubule size, collapsed lumens or age are held fixed (`kpmp-zs-prereg-v1-2026-10-28.md`).

## Gate

358 of 361 listed packages read (99.2%; the same 3 v1 packages return HTTP 500 as in every earlier pass), no read errors, and the TIV score release (426 participants) and clinical file (973 participants) loaded. The 95% gate passed, so every test was graded. `kpmp_fill` found all 358 readable packages already cached on this host and downloaded nothing.

## Zero-TBM study (Z1-Z8)

| | Check | Pass if | Observed | Predicted | Grade |
|---|---|---|---|---|---|
| Z1 | Zero rows exist in v1 too | v1 share >= 0.01 | 50,056 of 316,953 (0.158) | pass | **pass** |
| Z2 | v2 zero rows concentrated in some slides | chi-square / df > 2 | 114.1 (220 slides) | pass | **pass** |
| Z3 | v2 zero rows are smaller tubules | size ratio < 0.8 | 0.150 | pass (low confidence) | **pass** |
| Z4 | v1 zero rows commoner in the medulla | odds ratio >= 2 | 1.19 | pass (low confidence) | **fail** |
| Z5 | `tbm_pos` vs tubular atrophy % | rho > 0, p < 0.05 | +0.062, p 0.17, n 222 | fail | **fail** |
| Z6 | `tbm_pos` vs baseline eGFR | rho < 0, p < 0.05 | -0.100, p 0.062, n 247 | fail | **fail** |
| Z7 | `zero_share` vs tubular atrophy % | rho > 0, p < 0.05 | +0.384, p 0.0001, n 222 | fail | **pass** |
| Z8 | `zero_share` vs baseline eGFR | rho < 0, p < 0.05 | -0.360, p 0.0001, n 247 | fail | **pass** |

Holm-adjusted p over Z5-Z8: 0.17, 0.12, 0.0004, 0.0004. Five of eight predictions held. The two we got most wrong were the two we cared most about.

**Readings fixed in advance, applied:**
- *Z5 and Z6 fail:* TBM thickness as released does not track atrophy or kidney function in this cohort, even cleaned. Our Kidney AI entry leaves it out as a feature. Z6 came close (p 0.062; v2 alone rho -0.14), and we report it as a fail.
- *Z7 and Z8 pass:* the share of tubules the pipeline could not measure tracks disease. It may be biology or an artefact that travels with disease, and we cannot tell which. It is a new, cheap marker to check by eye.
- *Z2 and Z3 pass:* zero rows look like a measurement failure that clusters by slide and in small tubules.
- *Z4 fails:* in v1, medullary tubules are not the main source (odds ratio 1.19; 9,809 of 55,208 medulla tubules against 40,247 of 261,745 cortex tubules).

### Reported, not graded

- Every zero row is exactly 0.000. None is negative, in either version.
- Per-slide zero share: v1 0.027 to 0.438 (median 0.115); v2 0.007 to 0.381 (median 0.082). Every slide has some zero rows. No slide is over half zero.
- **Zero rows look like collapsed tubules.** Median luminal fraction is 0.019 against 0.125 for the other rows in v1, and 0.018 against 0.146 in v2. Median cell thickness hardly differs (v1 27.8 vs 27.8; v2 28.4 vs 29.3, in pixels). Median size is 5,298 vs 23,209 pixel^2 in v1 (ratio 0.23) and a box area of 5,963 vs 39,676 in v2 (ratio 0.15).
- Leaving zero rows out moves a slide's median TBM by more than 5% on 57 of 138 v1 slides and 54 of 220 v2 slides. The median shift is 4.0% (v1) and 2.6% (v2).
- `In Medulla` raw values are only "0" (261,745 rows) and "1" (55,208), all coded.
- Within version: Z5 v1 +0.087 / v2 +0.035; Z6 v1 -0.068 / v2 -0.140; Z7 v1 +0.407 / v2 +0.359; Z8 v1 -0.407 / v2 -0.302.

## Section-twins census (T1-T3)

| | Check | Pass if | Observed | Predicted | Grade |
|---|---|---|---|---|---|
| T1 | Share of evaluable v2 slides with a repeated section | >= 0.50 (>= 150 evaluable) | 190 / 219 = 0.868 | pass (least sure) | **pass** |
| T2 | Median share of glomeruli with a twin (repeat slides, >= 5 glomeruli) | >= 0.30 (>= 10 slides) | 0.473 over 174 slides | pass | **pass** |
| T3 | Positive controls detected at the eye-measured offset (within 1,000 px) | at least 4 of 5 | 5 of 5 (errors 10, 83, 257, 449, 991 px) | pass | **pass** |

All three held. Since T3 passed, T1 can be read as a repeat rate. It is a lower bound, because only the dominant offset is used.

**Descriptive:** the median mode count is 22 on repeat slides and 4 on the others. The median offset length is about 47,700 px (about 12 mm at 0.2527 microns per pixel). Twin shares are 0.47 for sclerotic glomeruli, 0.50 for tubules and 0.35 for arteries (slide medians). The count-inflation factor n / (n - twins / 2) is 1.262 for glomeruli, 1.260 for sclerotic glomeruli, 1.265 for tubules and 1.238 for arteries.

**What this means for users of these files:** per-slide object counts in v2 overstate the number of distinct structures by about a quarter, and per-object statistics treat about half of all objects as two samples. Shares and medians are much less affected, because both sections come from the same core. That includes the zero-TBM share above. Our pre-registered `kpmp-twinrel` study, gated on T3 (now passed), uses the twins as free test-retest replicates.

## Prior art (searched 2026-10-28)

We found no published report of tubules with no TBM measurement in KPMP's pathomics vectors, of their share, or of its relation to atrophy or eGFR. The closest work is a NEPTUNE/CureGN study of computed tubular features in MCD/FSGS (Kidney International 2025). It reports TBM thickening as tubules become atrophic, and an outcome association for the spread of TBM thickness, but says nothing on unmeasured tubules. HistoWAS (arXiv 2512.19954) and KPMP's own segmentation papers do not mention it either. The AJKD Atlas of Renal Pathology describes atrophic tubules as contracted, and some atrophy patterns as having little TBM thickening. That fits the collapsed, small profile of the zero rows, but it is not evidence that they are atrophic.

## Limits

- These are associations in a convenience sample of research biopsies. Scores and segmentations may come from different sections of one biopsy.
- Atrophy and low eGFR both rise with age and with smaller, collapsed tubules. The follow-up tests those confounders; until it runs, Z7 and Z8 are associations only.
- Z2 shows strong slide-to-slide variation. A slide-level factor such as staining or scanning could drive both the zero share and, by chance of case mix, the scores.
- One model family wrote, ran and graded this. No human has reviewed it. Only aggregate statistics are published. No package IDs, boxes, images or per-participant values are released.

## Files

- Code: `../kidney/kpmp_tbm0.py` 1.0, `../kidney/kpmp_twins.py` 1.0, `../kidney/kpmp_fill.py` 1.0 (tags v0.9.17-v0.9.19).
- Pre-registrations: `kpmp-tbm0-prereg-v1-2026-10-28.md`, `kpmp-twins-prereg-v1-2026-10-28.md`.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18, 2026-10-26 and 2026-10-27)
- Clinical relevance of computationally derived tubular features ... in MCD/FSGS, Kidney International 2025, https://www.kidney-international.org/article/S0085-2538(25)00409-0/fulltext
- AJKD Atlas of Renal Pathology: Tubular Atrophy, https://www.ajkd.org/article/S0272-6386(16)30033-6/fulltext
- HistoWAS, https://arxiv.org/abs/2512.19954
