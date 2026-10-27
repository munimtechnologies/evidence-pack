# Pre-registration v2: the KPMP segmentation census, second pass (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Code: `../kidney/kpmp_census2.py` (reuses `../kidney/kpmp_census.py` 1.0 unchanged), offline tests `../kidney/test_kpmp_census2.py`. Both are committed with this note before the job runs. Pass 1 and its grades: `kpmp-census-results-v1-2026-10-27.md` (this folder).

## 1. Why a second pass

Pass 1 (pre-registration v1, job `kpmp-census-v1`, finished 2026-10-27 01:54 UTC) downloaded 358 of 361 packages but left P2-P5 and P7-P9 untestable, for three reasons found in its own output:

1. **Reader.** The reader was built from a single `_v2` package. The 138 analysed v1 packages use a different layout: 2-4 workbooks named `final_combined_features_<compartment>.xlsx`, each with a `features` sheet (77-78 columns in the headers pass 1 recorded). Pass 1 read no v1 values.
2. **Pixel size.** None of the 358 OME-XML files gave a pixel size in microns, so pass 1 converted nothing.
3. **Scores.** The pathologist score workbook pass 1 named (TIV Descriptor Scores 02.19.2026) answered HTTP 404. The Repository now lists "KPMP TIV Descriptor Scores 10.12.2026.xlsx" (469 kB; seen in a web search result on 2026-10-27, not opened).

Pass 1's v1 headers also hold a column the README does not mention: `Area (pixel^2)` sits next to `Area` in the v1 glomerulus workbooks. If v1 `Area` is in square microns, as the README says, then `Area` / `Area (pixel^2)` equals the pixel size squared on every row. That gives a test of the README from inside the v1 files, with no outside pixel size.

What we already know (from pass 1 and the 2026-10-18 feasibility jobs; no new data read for this note):
- v2 package medians, raw: TBM thickness 5.16, cell thickness 30.07, glomerular area 411,918, luminal fraction 0.121 (220, 220, 211 and 220 packages).
- Two slides opened on 2026-10-18 (both `_v2` packages) gave an Aperio ImageDescription with `MPP = 0.2527` and `AppMag = 40`. Their masks matched the slide's full-resolution level at factor 1.
- The v1 headers of the tubule workbooks are NOT known yet (pass 1 recorded only the first workbook per package).

## 2. Data and procedure (fixed now)

- **Frame and cache:** the same 361 packages and seeded order as pass 1, read from the same data volume. The three packages that failed with HTTP 500 are tried once more (3 tries each). Nothing else is downloaded again for the census itself.
- **v1 workbooks:** `final_combined_features_<c>.xlsx`, sheet `features`, mapped to the v2 sheet names: tubules -> `tubs`, non_globally_sclerotic_gloms -> `gloms`, globally_sclerotic_gloms -> `s_gloms`, muscular_vessels -> `arts`. Any other compartment is kept under its own name and reported.
- **Columns are matched by exact name** (trimmed, lower case, spaces collapsed; brackets kept), so `Area (pixel^2)` never counts as `Area`. Features: `tubs` "Average TBM Thickness", "Average Cell Thickness", "Luminal Fraction"; `gloms` "Area", and in v1 also "Area (pixel^2)".
- **Pixel size from the scanner file:** the first 20 v1 and the first 20 v2 packages in the seeded order are downloaded once more. From the package's `.svs` slide the job reads only the first image directory's ImageDescription (TIFF tag 270) and parses `MPP =` and `AppMag =`. The zip is deleted straight away. **mpp_hat** = median MPP of the sampled v2 packages that give one (at least 5 needed). This replaces pass 1's OME-XML source, which turned out to be empty.
- **Units as the README states them:** v1 values in microns; v2 values times mpp_hat (lengths) or mpp_hat squared (areas); fractions unitless.
- **Scores:** the Repository's file-list export for Experimental Strategy "Pathology Descriptor Scoring" (made by MV2's hands on 2026-10-27, not opened by us). Exactly one open xlsx row is required, otherwise P7-P9 are untestable. The sheet used is "Data Table" if present, otherwise the first sheet with a row starting "Participant ID". Cleaning as in v1: one row per participant, "Consensus Complete" Y.
- **Participants, statistics:** as in v1 (at least 20 tubules per participant; Spearman, one-sided permutation p, 10,000 shuffles, seed 20261026 + test index).

## 3. Predictions and pass rules

Graded only if at least 95% of the 361 packages are analysed. Ratio checks need at least 10 packages per version with the column; otherwise "untestable".

- **S1 scanner pixel size:** at least 10 sampled packages give an MPP, at least 90% of the sampled packages that downloaded give one, their median is in [0.24, 0.26] and max/min <= 1.10. Prediction: pass.
- **U1 v1 area is in square microns:** across v1 `gloms` packages, the median of each package's median row ratio `Area` / `Area (pixel^2)` is in [0.04, 0.10] (pixel size 0.20-0.32 microns). Prediction: pass. A ratio near 1 means v1 `Area` is in pixels and the README is wrong for v1.
- **U2 one pixel scale across versions:** median v2 `gloms` "Area" (pixels, README) over median v1 "Area (pixel^2)" is in [0.5, 2.0]. Prediction: pass.
- **U3 internal and scanner pixel sizes agree:** the square root of U1's median ratio is within 10% of the median MPP of the sampled v1 packages. Prediction: pass.
- **P2-P5 (v1 rules, re-tested):** TBM thickness v2/v1 raw >= 2.0 (P2) and converted in [0.67, 1.5] (P3); glomerular area v2/v1 raw >= 4.0 (P4) and converted in [0.5, 2.0] (P5). Converted = v2 times mpp_hat to the feature's power. If the v1 tubule workbooks have no "Average TBM Thickness" column, P2/P3 are untestable and the v1 tubule columns are reported. Prediction: all pass.
- **P7-P9 (v1 rules, new score release):** luminal fraction vs "Cortex: Abnormal Tubular Luminal Morphology: Abnormal Luminal Morphology: Percent" rho > 0; TBM thickness vs "Cortex: Tubular Atrophy: Common Type: Percent" rho > 0; cell thickness vs "Cortex: Tubular Injury Other: Percent" rho < 0; each with p < 0.05 and at least 30 participants. A score column missing from the new release makes that test untestable. Prediction: pass (P9 with the least confidence).

**Reported, not predicted:** all of the above on raw values and within v1-only and v2-only participants; TBM vs "Cortex: Interstitial Fibrosis: Percent" (D1); every v1 and v2 header by compartment; AppMag values; packages with an IFTA-named mask channel by version; whether the three HTTP 500 packages now download.

P6 (the README's IFTA note) is not re-tested. Pass 1 showed channel names cannot test it: every v2 package names an IFTA channel and no v1 package does, whatever the slide ID. Testing it needs the mask pixels, which this pass does not keep.

## 4. What each outcome changes

- **S1, U1-U3 and P2-P5 pass:** entrants get one conversion (v2 pixels times the scanner MPP) and the size of the error from pooling without it.
- **U1 fails with a ratio near 1:** v1 `Area` is in pixels. Then P4/P5 are read as "both versions in pixels", and the results note says the README's v1 unit claim does not hold for areas.
- **S1 fails (mixed scanners or magnifications):** a single mpp_hat is wrong. P3/P5 are reported but flagged, and entrants are told to read the MPP per slide.
- **P7-P9 fail:** this weakens the case for using these features in a discovery entry, and is published as such.
- Every outcome is published. Only aggregate counts and statistics leave the job, never a KPMP file, image or per-participant value.

## 5. Limits

- Pixel size comes from 40 of 361 slides; a scanner change outside the sample would be missed.
- The unit checks compare populations (mostly earlier v2 biopsies against later v1 biopsies), not the same slides. A real batch difference would shift the ratios, though not by 4x or 16x.
- One model family wrote the code and will grade it; no human has reviewed it.

Acknowledgement (results note): "The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org", followed by the NIDDK grant list on KPMP's citing page.

## Sources

- `kpmp-census-prereg-v1-2026-10-26.md`, `kpmp-census-results-v1-2026-10-27.md`, `kpmp-feasibility-v2-results-2026-10-18.md` (this folder)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list exports of 2026-10-18 and 2026-10-27)
- KPMP available data, https://www.kpmp.org/available-data
