# Results: KPMP segmentation census, pass 1 (2026-10-27)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Pre-registration: `kpmp-census-prereg-v1-2026-10-26.md` (tag v0.9.11). Code: `../kidney/kpmp_census.py` 1.0, unchanged since that tag. Job `kpmp-census-v1`: python:3.12 container, 2 CPUs, 1 GB memory cap (peak 0.48 GB), network on. It started 2026-10-26 23:33 UTC and finished 2026-10-27 01:54 UTC. The 17 offline tests passed in the container first. The census took 138.7 minutes and downloaded 93,727,901,655 bytes (about 11 MB/s; AI arithmetic).

## Grades, exactly as pre-registered

| | Prediction | Grade | Why |
|---|---|---|---|
| P1 access | pass | **pass** | 358 of 361 packages downloaded within 2% of their listed size and opened. The other 3 (all v1) answered HTTP 500 three times. |
| P2-P5 units (TBM thickness, glomerular area; raw and converted) | pass | **untestable** | 0 v1 packages gave a value, and no package gave a pixel size (reasons 1 and 2 below) |
| P6 IFTA note | pass | **fail** | 77 of the 212 packages whose slide sorts after S-2006-005094 have an IFTA-named mask channel. 143 of the 146 at or before it do. |
| P7-P9 agreement with pathologist scores | pass | **untestable** | The score workbook named in the pre-registration answered HTTP 404 (reason 3) |

All of these grades are recorded unchanged. None of the untestable predictions is counted as passed.

## Why most predictions were untestable: our errors and the data's

1. **Our reader (our error).** We wrote the reader from the one package we had opened, a `_v2` package. The 138 analysed v1 packages are laid out differently. Each holds 2-4 workbooks named `final_combined_features_<compartment>.xlsx` (2 workbooks: 5 packages; 3: 27; 4: 106), one per compartment (tubules, non-globally and globally sclerotic glomeruli, muscular vessels), and each has a `features` sheet. The v1 headers we saw have 78 columns (glomeruli) and 77 (vessels): texture, colour, distance-transform and nuclear features, then the compartment's own columns. Every v2 package holds one workbook with sheets `gloms`, `s_gloms`, `tubs`, `arts` of 5-7 columns. Pass 1 looked for sheets named `tubs` and `gloms` only, so it read no v1 value.
2. **No pixel size in the OME-XML (a fact about the data).** Not one of the 358 OME-XML files gave a pixel size in microns (PhysicalSizeX missing or not in microns; pass 1 did not record which). A v2 workbook, whose README gives its values in pixels, therefore cannot be converted from inside its own package.
3. **The score workbook moved (a fact about the data).** "KPMP TIV Descriptor Scores 02.19.2026.xlsx", listed in the Repository's export of 2026-10-18, answered HTTP 404 at its listed address. The Repository now lists "KPMP TIV Descriptor Scores 10.12.2026.xlsx" (469 kB), which we have not opened.

## What pass 1 did measure (descriptive; nothing here was predicted)

- **Two layouts, split by version.** v2: 220 packages, one README (the same hash in every package), 7 mask channels including "IFTA" and "cortex", 1 workbook. v1: 138 packages, a different README (one hash) that contains neither the v2 pixel sentence nor the IFTA note, 5 mask channels and no IFTA channel.
- **The IFTA channel follows the version, not the slide ID.** All 220 v2 packages name an IFTA channel and none of the 138 v1 packages do. The README's note says masks of slides after S-2006-005094 "do NOT contain annotations" for IFTA. 77 v2 packages after that ID still name the channel, which may be empty. Channel names cannot settle this, so P6's "fail" says that our test did not fit the note, not that the note is wrong. Checking it needs the mask pixels.
- **v1 workbooks carry pixel columns.** Every v1 header we saw has `Area (pixel^2)` and `Radius (pixel)` next to the compartment's own `Area`. If v1 `Area` is in square microns, as the v2 README's wording implies for non-v2 files, the two differ by the pixel size squared on every row. Pass 2 tests this.
- **v2 raw values (package medians, pixels per the README):** TBM thickness 5.16 (220 packages), cell thickness 30.07 (220), glomerular area 411,918 (211), luminal fraction 0.121 (220). 9 of the 220 v2 `gloms` sheets and 64 of the 220 `s_gloms` sheets are empty.
- **No participant has both versions.** 247 participants have at least one analysed package. Every package belongs to one participant, and no participant's packages mix v1 and v2.
- Two slides opened on 2026-10-18 report `MPP = 0.2527` (40x Aperio) in their scanner metadata. **If** every v2 slide shares that pixel size, which pass 2 checks on 40 slides, the v2 medians above are about 1.30 microns (TBM), 7.60 microns (cell thickness) and 26,300 square microns (glomerular area) (AI arithmetic). Until then these are not results.

## What this changes

- **For anyone pooling KPMP's released pathomics:** v1 and v2 differ in more than units. They have different files, sheets, column sets and mask layers, and the package says nothing about pixel size. A reader built from one version silently drops the other. That happened to us.
- **Pass 2** (`kpmp-census-prereg-v2-2026-10-27.md`, published with this note before it runs) reads the v1 workbooks and takes the pixel size from the scanner metadata of 40 slides. It tests the README's units from inside the v1 files (`Area` / `Area (pixel^2)`) and re-runs P2-P5 and P7-P9 against the 10.12.2026 score release.
- **Lesson recorded:** before pre-registering a census, open at least one package of every version in the frame.

## Limits

- One release (the file list of 2026-10-18). The Repository changes; one file has already moved.
- Our reader's error is ours. The descriptive facts come from the same job and the same reader; header facts for v1 tubule workbooks are not yet known.
- `results.json` stays local because it holds per-slide feature medians, which are KPMP data. Only the aggregates above are published.
- One model family wrote the code and graded it; no human has reviewed it.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-census-prereg-v1-2026-10-26.md`, `kpmp-feasibility-v2-results-2026-10-18.md` and `../kidney/kpmp_census.py` (this repository)
- Job output `compete-results/kpmp-census-v1/` (local; aggregates quoted above)
- KPMP Atlas Repository, https://atlas.kpmp.org/repository/ (file-list export of 2026-10-18; Pathology Descriptor Scoring listing seen 2026-10-27)
