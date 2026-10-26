# Pre-registration: do KPMP's open segmentation packages match their own README, and do their tubule features agree with KPMP's pathologist scores? (v1, 2026-10-26)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Code: `../kidney/kpmp_census.py`, offline tests `../kidney/test_kpmp_census.py`. Both are committed with this note, before the job runs. As of this note, the only KPMP segmentation package we have opened is the smallest one (feasibility check, `kpmp-feasibility-prereg-v1-2026-10-18.md`). Its facts are used below and are marked as such.

## 1. Why

The NIDDK Kidney AI Discovery Challenge (herox.com/KidneyAI; submissions 2026-11-05 to 2027-04-29) allows only open data from the Kidney Precision Medicine Project (KPMP). Entrants who use KPMP's ready-made pathomics features will pool the 361 "Segmentation Masks & Pathomics Vectors" packages. Each package's own README says:

- "In v2 Measurements represented as either unitless, pixels, pixels squared". The same README describes the feature file as "microns, microns squared" otherwise. Of the 361 packages in the Repository's file list (exported 2026-10-18), 220 are named `_v2` and 141 are not.
- "ome.tif file past S-2006-005094 (alphanumerically) do NOT contain annotations for interstitial fibrosis and tubular atrophy (IFTA)".

KPMP's segmentation help page (kpmp.org/help-docs/technologies, imaging tab, read 2026-10-26) does not mention units, file versions or IFTA layers. The README inside each zip is the only place these facts appear. If they hold, anyone who pools v1 and v2 values without converting units mixes microns with pixels (about 4x for lengths and 16x for areas at 0.25 microns per pixel). If they do not hold, the README misleads. Either way, a full census is worth publishing for every entrant.

The second question is whether KPMP's own released tubule features track KPMP's own pathologist descriptor scores (TIV workbook, 02.19.2026 release; 341 rows, 340 distinct participant IDs, measured 2026-10-18). If they don't, the released features are a weak base for "discovery" claims.

## 2. Prior art (searched 2026-10-26: web, arXiv; KPMP help pages)

- HistoWAS (Yang et al., arXiv 2512.19954, Dec 2025): 385 PAS slides from 206 KPMP participants; 72 "conventional object-level features provided by the KPMP" plus 30 spatial ones; pathologist interstitial fibrosis as the endpoint. Its abstract and HTML text (read 2026-10-26) do not mention feature-file versions, pixels or microns, or missing tables.
- Next-Generation Morphometry (Nat Commun 2023, s41467-023-36173-0): its own segmentation, validated on KPMP; tubular diameters fall with report-based IFTA grade.
- NEPTUNE/CureGN tubular pathomics (PMC11275675): features against descriptor scores, but in NEPTUNE/CureGN, not KPMP.

We found no published check of the KPMP segmentation release against its own README, and no published test of KPMP's released tubule features (luminal fraction, TBM thickness, cell thickness) against KPMP's TIV descriptor scores that handles units explicitly. This search was not systematic. Anything we missed will be cited in the results note.

## 3. Data and procedure (fixed now)

- **Frame:** every open package in the Repository's CSV export of 2026-10-18 whose Experimental Strategy is "Segmentation Masks & Pathomics Vectors" (361). The export is not re-hosted. MV2's hands copy it into the job's input folder without opening it.
- **Order:** sort by package ID, then shuffle with seed 20261026. If the job's 200-minute download budget runs out, a later job with the same code and data volume resumes, so a partial census is always a seeded random subset.
- **Per package:** download the zip (KPMP's download URL; the server does not honour Range requests, so the whole zip is fetched) and log its SHA-256. Keep only the `xlsx`, `xml` and `md` members of at most 50 MB in the job's data volume, and delete the zip, slide and masks at once. Then read:
  - **README:** hash, the v2-pixels sentence, the IFTA note.
  - **OME-XML:** PhysicalSizeX (microns per pixel; a unit other than microns counts as missing) and the channel (layer) names.
  - **Feature workbook:** for each sheet (names normalised: lower case, bracketed text dropped), the header, the row count, and the median of every non-coordinate column.
- **Units, as the README states them:** v1 values are taken as microns. v2 values are multiplied by mpp for lengths (column name has thickness, length, diameter, perimeter, distance or width) and by mpp squared for areas ("area"). Fractions and ratios are unitless. A v2 package without an mpp has no converted values.
- **Participants:** packages listed for exactly one participant. All of a participant's packages are pooled, and the participant value is the median over all their structures. A participant needs at least 20 tubules (`tubs` rows).
- **TIV scores:** sheet "Data Table", header row starting "Participant ID". Kept: participants with exactly one row and "Consensus Complete" Y or y. "n/a" and non-numbers are missing.
- **Statistics:** Spearman rho with average ranks; one-sided permutation p in the predicted direction (10,000 shuffles, seed 20261026 + test index).

## 4. Predictions and pass rules

P1 is graded once every listed package has been attempted. P2-P9 are graded only when at least 95% of the 361 packages are analysed; until then they read "pending". Ratio checks need at least 10 packages per version with the column.

- **P1 access:** at least 95% of packages download within 2% of their listed size and open as zips. Prediction: pass.
- **P2 TBM units, raw:** median of package medians of `tubs` "Average TBM Thickness", v2 over v1, is at least 2.0. That is what the README implies at about 0.25 microns per pixel (expected about 4). Prediction: pass.
- **P3 TBM units, converted:** the same ratio after converting v2 to microns lies in [0.67, 1.5]. Prediction: pass.
- **P4 glomerular area, raw:** the same v2/v1 ratio for `gloms` "Area" is at least 4.0 (expected about 16). Prediction: pass.
- **P5 glomerular area, converted:** in [0.5, 2.0]. Prediction: pass.
- **P6 IFTA note:** no package whose slide ID sorts after S-2006-005094 has an OME channel named like IFTA (ifta, fibros or atroph), and at least 90% of those at or before it do. "Untestable" if no channel anywhere has such a name. Prediction: pass.
- **P7 luminal fraction:** participant median `tubs` "Luminal Fraction" against "Cortex: Abnormal Tubular Luminal Morphology: Abnormal Luminal Morphology: Percent": rho > 0, p < 0.05. Prediction: pass.
- **P8 TBM thickness (microns):** against "Cortex: Tubular Atrophy: Common Type: Percent": rho > 0, p < 0.05. Prediction: pass.
- **P9 cell thickness (microns):** against "Cortex: Tubular Injury Other: Percent": rho < 0, p < 0.05. Prediction: pass, with the least confidence. That score bundles simplification with other injury types.
- P7-P9 need at least 30 participants, otherwise "untestable".

**Reported, not predicted:**
- The same correlations on raw (unconverted) values, and within v1-only and v2-only participants.
- TBM thickness against "Cortex: Interstitial Fibrosis: Percent" (D1).
- Empty sheets by version (the smallest package, S-1904-008128, has 238 tubule rows and 0 glomerulus rows).
- Distinct READMEs; header variants by version.
- The mpp range; channel names and counts.
- How many participants have packages in both versions.

## 5. What each outcome changes

- **P2-P5 pass:** the README's units hold. The results note gives entrants the conversion and the size of the error from pooling without it (raw vs converted rho).
- **P2/P4 fail:** the README's units sentence is wrong for this release, and v1 and v2 values can be pooled as they are. Report that plainly.
- **P3/P5 fail while P2/P4 pass:** units differ, but simple mpp conversion does not reconcile them (another pipeline difference). Report it as a caution, without guessing the cause.
- **P6 fail:** report which slides break the note.
- **P7-P9:** a failed agreement prediction weakens the case for using these features in a discovery entry, and it is published as such. Passing does not show that the features measure what pathologists see, only that they move together.
- Every outcome is published, including failures. No KPMP file, image or per-participant value is published, only aggregate counts and statistics.

## 6. Limits

- One release (file list of 2026-10-18; TIV workbook of 02.19.2026). The Repository may change.
- The unit check compares populations (earlier v2 biopsies against later v1 biopsies), not the same slides. A real batch difference in tubule size would shift the ratios, though not by 4x.
- TIV scores are per participant. Features are pooled over all slides, which may sample different tissue.
- Median pooling hides within-biopsy structure, and the tests are correlations, not diagnoses.
- One model family did all the work, and no human has reviewed it.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- KPMP Atlas Repository file-list export, 2026-10-18 (https://atlas.kpmp.org/repository/); README inside package S-1904-008128 (read by the feasibility job, 2026-10-18)
- https://www.kpmp.org/help-docs/technologies?tabname=imaging (read 2026-10-26)
- HistoWAS, https://arxiv.org/abs/2512.19954
- Next-Generation Morphometry, https://www.nature.com/articles/s41467-023-36173-0
- NEPTUNE/CureGN tubular features, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11275675/
- `kpmp-feasibility-prereg-v1-2026-10-18.md` (this folder) and its job's measurements (kpmp-feasibility-v2, 2026-10-18)
