# Results v2: KPMP's pathomics features agree between serial sections of the same object (2026-10-30)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-twinrel-prereg-v1-2026-10-28.md` (this folder), unchanged. Earlier attempts: v1 ran without data (`kpmp-twinrel-results-v1-2026-10-28.md`); v2 never started; v3 was stopped by a machine shutdown (exit 143) while filling its cache. Job `kpmp-twinrel-v4`, 2026-10-30 14:34-14:47 UTC, Python 3.12.15, modules from tag v0.9.21 (`kpmp_twins.py`, `kpmp_twinrel.py` 1.0), offline tests passed. 220 of 220 v2 packages read, no errors. Graded by hand from the job's `results.json` against the rules below, then checked against the job's own grades (they agree).

## Gates

- **Detector check T3: pass.** The job re-ran the section-twins census with identical code, data and seed. It matches the census in `kpmp-tbm0-twins-results-v1-2026-10-28.md` to every printed digit: 190 of 219 evaluable slides repeat a section (0.868; T1 pass); slide-median glomerular twin share 0.473 over 174 slides (T2 pass); 5 of 5 positive controls found (errors 10, 83, 257, 449 and 991 px); count inflation 1.262 (glomeruli), 1.260 (sclerotic glomeruli), 1.265 (tubules), 1.238 (arteries).
- Repeat slides: 190 (needed 10). Twin pairs per graded feature: 1,096 glomerular (needed 100); 83,174 to 95,413 tubular (needed 500). R5: 12,239 tubule twin pairs with a zero in either member (needed 50).

## Grades, exactly as written

A feature passes if rho_twin >= 0.30 and the lower 95% bound of rho_twin - rho_null >= 0.10 (200 slide-level bootstrap resamples).

| | Feature (sheet) | Prediction | rho_twin | rho_null | Difference (95% interval) | Grade |
|---|---|---|---|---|---|---|
| R1 | Mesangial fraction (glomeruli) | pass | 0.822 | -0.010 | 0.832 (0.719 to 0.954) | **pass** |
| R2 | Average TBM thickness (tubules) | pass (least sure) | 0.464 | 0.094 | 0.370 (0.350 to 0.388) | **pass** |
| R3 | Luminal fraction (tubules) | pass (most sure) | 0.707 | 0.133 | 0.575 (0.550 to 0.592) | **pass** |
| R4 | Average cell thickness (tubules) | pass | 0.688 | 0.167 | 0.521 (0.494 to 0.542) | **pass** |
| R5 | Zero TBM concordant: OR(twin) >= 2 x OR(null) | pass (low confidence) | OR 85.4 | OR 41.5 | needs >= 83.0 | **pass (narrow)** |

**5 of 5 predictions held.** R5 passed by 3% of its threshold (85.4 against 83.0) and, as pre-registered, has no interval; a small change in pairing would move it either way, so read it as borderline.

Zero-TBM tables (pairs; "zero" means a TBM thickness of zero or less):

| | both zero | first zero only | second zero only | both positive |
|---|---|---|---|---|
| Twin pairs | 7,006 | 2,459 | 2,774 | 83,174 |
| Null pairs | 5,301 | 3,174 | 3,049 | 75,811 |

## Descriptive (not graded)

| Feature (sheet) | Twin pairs | Slides | rho_twin | rho_null | Difference (95% interval) |
|---|---|---|---|---|---|
| Area (glomeruli) | 1,096 | 158 | 0.981 | 0.881 | 0.099 (0.080 to 0.122) |
| Mesangial area (glomeruli) | 1,096 | 158 | 0.943 | 0.652 | 0.291 (0.240 to 0.346) |
| Mesangial fraction (sclerotic glomeruli) | 285 | 93 | 0.619 | -0.013 | 0.632 (0.399 to 0.847) |
| Area (sclerotic glomeruli) | 285 | 93 | 0.960 | 0.835 | 0.125 (0.075 to 0.198) |
| Arterial area (arteries) | 4,647 | 189 | 0.979 | 0.946 | 0.033 (0.027 to 0.039) |

Size features are matched on box size by design, so their high rho_null is expected and they are not graded. Objects on repeat slides: 4,925 glomeruli, 1,267 sclerotic glomeruli, 486,604 tubules, 25,598 arteries.

## Readings fixed in advance, applied

- **R3 pass:** the pairing finds the same tubule (its lumen reproduces), so R2 and R4 can be read as reliability.
- **R2 pass:** per-object TBM thickness is reproducible, so its earlier failures against the pathologists' atrophy scores and baseline eGFR (`kpmp-census-results-v3-2026-10-28.md`, `kpmp-q2-results-v1-2026-10-28.md`) lie in how it is summarised or in what it measures, not in random per-object noise. It is still the least reproducible of the four graded features (0.46, against 0.69 to 0.82).
- **R5 pass:** zero TBM follows the object, so dropping zero rows removes particular tubules and can bias summaries. This agrees with the blinded AI triage (`kpmp-triage-results-v1-2026-10-30.md`): small boxes, zero or measured, are mostly not ordinary whole tubules.

## What the null pairs add (not pre-registered; plain arithmetic on the tables)

Among null pairs, both members are size-matched tubules from the same slide. Given a zero first member, the second is zero in 62.5% of null pairs (5,301 of 8,475), against a 9.6% zero share among all second members of null pairs (8,350 of 87,335). Among twins the same figure is 74.0% (7,006 of 9,465). So most of zero TBM's concordance is shared by any tubule of the same size on the same slide; following the specific object adds only a little on top. Zero TBM is mainly a slide-and-size property, which fits its strong link to tubule size (Z3 in `kpmp-tbm0-twins-results-v1-2026-10-28.md`).

## What this means for MV2's Kidney AI entry

- Mesangial fraction, tubular luminal fraction and tubular cell thickness are reproducible object by object (0.69 to 0.82 between serial sections, a lower bound because the sections are microns apart). They can carry participant-level summaries.
- TBM thickness is reproducible but weaker. It stays out of the main discovery features and is reported as a secondary feature.
- Twin objects must be collapsed (each object counted once) before any count or participant summary, because the census found object counts on repeat slides inflated about 1.26 times by second measurements.
- Zero-TBM rows are a size- and slide-linked data-quality signal, not a random failure. Summaries should be reported with and without them, and with a size floor.

## Limits

- Twins are matched on box size within 15%, which may favour objects that segment consistently; rho_twin may be optimistic for odd shapes and pessimistic for real change between sections.
- Pooling over slides weights slides with many pairs more heavily; the bootstrap accounts for clustering only in the interval.
- Only the dominant offset per slide is used, and only on the 190 slides where the detector finds a repeat.
- One model family wrote, tested, ran and graded this; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.
