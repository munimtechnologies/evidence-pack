# Results v1: blinded AI visual triage of KPMP tubules with no TBM thickness (2026-10-30)

MV2 of Munim, Inc. Planned, read and graded by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice. **This is AI triage, not a pathologist's reading.** Nobody on the team is a kidney pathologist. No human has reviewed the readings or this note. Nobody at KPMP, NIDDK or HeroX has been contacted.

Graded as pre-registered in `kpmp-triage-prereg-v1-2026-10-30.md` (tag v0.9.23, fixed before any crop existed). Crops: job `kpmp-triage-v1` (2026-10-30; 12 packages, 48 size-matched pairs, 96 crops plus 8 repeats; median box-area ratio within pairs 0.9999, 43 of 48 within 10%). The 104 blinded readings were committed at tag v0.9.26 (`kpmp-triage-readings-v1.csv`) before the key was opened. Only then was the key's `pairs.csv` (crop ID, block, pair, group, duplicate-of; no package ID or box) opened. It is published here as `kpmp-triage-pairs-v1.csv`.

**How the grades were computed.** By hand, applying the rules of `kidney/kpmp_triage.py` 1.0 `grade()` line by line (originals only for V1-V3, exact one-sided sign test, the discordant-pair floors, V4 over the 8 repeats). The per-group counts below were cross-checked against the category totals of all 104 readings (A 32, B 11, C 32, D 24, E 5, F 0), which they reproduce exactly. A confirming job (`kpmp-triage-grade-v1`) runs the same code on the readings as committed at v0.9.26. If its output differs from this note, the job's output stands and a dated correction will follow.

## Headline

1. **At matched size, this reader could not tell unmeasured tubule rows from measured ones.** Almost every box in both groups looked abnormal or was not a whole tubule: 45 of 48 zero-TBM boxes and 46 of 48 size-matched measured boxes. With only 3 discordant pairs, the main test (V1) is **untestable**, not failed.
2. **Not atrophy, and not artefact, at this sample size.** Zero-TBM boxes were read as atrophic somewhat more often (17 vs 12; discordant pairs 9 vs 4, p 0.13; fail) and as not-a-tubule about equally often (12 vs 11; 8 vs 7, p 0.50; fail).
3. **The small objects themselves are the finding.** In the size range where zero-TBM rows sit, only 5 of 96 boxes looked like an ordinary tubule. About a quarter were not on a tubule at all, and about a third showed only part of one. This held whether or not KPMP's pipeline had measured a TBM thickness for the box.

Plainly: what makes the zero-TBM share track atrophy and eGFR (`kpmp-zs-results-v1-2026-10-29.md`) is not visible as a difference between zero and measured rows of the same size. That fits the earlier finding that a simpler marker, the share of small tubules, carries most of the same signal.

## Gate

48 complete pairs from 12 packages (floors 40 and 10); all 104 images read exactly once; 0 of 96 originals unreadable (cap 10%). **Passed.**

## Table (96 originals)

| Category | Zero-TBM (48) | Measured, size-matched (48) |
|---|---|---|
| A atrophic | 17 | 12 |
| B collapsed | 4 | 6 |
| C tangential or partial | 12 | 17 |
| D not a tubule or artefact | 12 | 11 |
| E normal-looking | 3 | 2 |
| F unreadable | 0 | 0 |

## Grades

| ID | Zero-TBM member more often... | Zero only / measured only | p (one-sided exact) | Floor | Predicted | Grade |
|---|---|---|---|---|---|---|
| V1 | abnormal (A-D) | 1 / 2 | 0.875 | 8 | pass | **untestable** (3 discordant) |
| V2 | atrophic (A) | 9 / 4 | 0.133 | 5 | fail (unsure) | **fail** |
| V3 | not a tubule or artefact (D) | 8 / 7 | 0.500 | 5 | pass (unsure) | **fail** |
| V4 | same category for a repeat and its original (at least 75%) | 8 of 8 agree | - | 6 | pass | **pass (uninformative, see below)** |

Predictions: V2 held; V3 missed; V1 could not be tested; V4 held only by construction.

**V4 is uninformative.** The repeats were byte-identical copies, and the reader recognised all 8 and said so in its notes before the key was opened (`kpmp-triage-readings-v1-note-2026-10-30.md`). The pre-registration listed this risk. So the reader's consistency was **not measured**; V1-V3 are reported with that gap.

**Readings fixed in advance, applied:**
- None of the four fixed readings applies as written. "V1 and V3 pass" and "V2 passes" did not happen. "V1 fails" did not happen either: V1 is untestable because both groups are almost entirely abnormal, so there are too few discordant pairs. We do not substitute a reading.
- What can be said without one: at this sample size, this reader saw no category in which zero-TBM boxes differ from size-matched measured boxes. MV2's Kidney AI entry will **not** describe the zero-TBM share as an image-confirmed atrophy marker (that needed V2 to pass).
- The artifact cautions fixed in advance all apply: one AI reader of one model family; crops come from the package's slide, which may not be the section the segmentation was drawn on; the green outline can hide a thin basement membrane at the box edge; 48 pairs detect only large differences.

## What this means

- **For users of KPMP's open pathomics files:** small objects in the tubule tables are mostly not whole, ordinary tubules, whether or not they have a TBM value. Features built from the smallest tubule rows (counts, shares, thickness averages) mix in boxes that sit on interstitium, capillaries or the edge of a tubule. That is a data-quality caution, from one AI reader on 12 biopsies, not a measured error rate.
- **For the zero-TBM marker:** treat it as a size-linked signal from the pipeline, not as a picture of atrophy. The share of small tubules is the simpler feature and needs no TBM column.
- **For method:** a consistency check needs altered repeats (shifted crop, rotation, re-encoding); identical copies are recognised. A reading at matched size needs a comparator that is not itself mostly abnormal, for example measured rows of median size alongside size-matched ones.

## Prior art

As in the pre-registration (searched 2026-10-30): AI models have been used for kidney slide quality control (arXiv 2606.16658) and glomerulus classification (arXiv 2508.15960), but we found no blinded, size-matched AI triage of the objects a public kidney pathomics release failed to measure. This is a partial, largely negative first attempt at one.

## Limits

- One AI reader, not a pathologist; no human has checked any reading.
- 12 packages from the v2 layout only, 4 pairs each; 48 pairs detect only large differences.
- Consistency of the reader is unmeasured (V4 above).
- Grades computed by hand; confirming job filed (see top).
- Only blinded crop IDs, categories, short notes and the pairing are published. No images, package IDs, boxes, `key.json` or per-participant values are released.

## Files

- Pre-registration: `kpmp-triage-prereg-v1-2026-10-30.md`. Readings: `kpmp-triage-readings-v1.csv` and `kpmp-triage-readings-v1-note-2026-10-30.md`. Pairing: `kpmp-triage-pairs-v1.csv` (this commit).
- Code: `../kidney/kpmp_triage.py` 1.0 with tests `../kidney/test_kpmp_triage.py`; `../kidney/kpmp_patches.py`.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list export of 2026-10-18)
- Vision-Language Models as Zero-Annotation Oracles in Histopathology, arXiv 2606.16658
- Glo-VLMs, arXiv 2508.15960
