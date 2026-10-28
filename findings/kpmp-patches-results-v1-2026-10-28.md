# Results: a visual check of KPMP's most extreme segmented objects (2026-10-28)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.
Research information, not medical advice. **The visual triage below is AI visual triage, not a pathologist's reading.** No independent human check yet. Nobody on the team is a kidney pathologist. Nobody at KPMP, NIDDK or HeroX has been contacted.

Code: `../kidney/kpmp_patches.py` 1.0 (tag v0.9.16). Job `kpmp-patches-v1`: python:3.12 container, 2 CPUs, 2 GB memory cap, network on. It ran on 2026-10-28 from 01:35 to 01:41 UTC; its 9 offline tests passed first. It downloaded the 14 open segmentation packages that hold the 30 most extreme within-slide outliers from the object audit (`kpmp-objects-results-v1-2026-10-28.md`): the top 10 glomeruli, top 10 tubules and top 10 arteries. From each package's PAS slide it cut a crop around every target box, then deleted the package. The crops are KPMP image data. They stay private and are not published here, and neither are package IDs or box positions. This note gives counts only.

This was a look, not a pre-registered test. Nothing below was predicted in advance, and nothing is graded.

## 1. KPMP's `x` columns are image rows

The v2 workbooks give each object's box as `x1 | x2 | y1 | y2`. The job could not decide from the workbooks which image axis `x` runs along. The workbooks were missing on the machine that ran it (see section 4). So it cut every target both ways:

- **Reading `x` as the image column** (the usual meaning): 14 of the 30 boxes fall partly or wholly outside their slide. All 14 slides are much wider than tall, and these boxes have a `y` larger than the slide's height. Of the 16 boxes that do fit, we looked at 4 crops (two glomeruli, one tubule, one artery). None shows its object. Two are blank glass (one beside the tissue edge), one is a field of ordinary tubules, and one is plain interstitium.
- **Reading `x` as the image row:** all 30 boxes fit inside their slide. Each crop frames a structure of the right size and place: a round tuft for glomerulus boxes, a lumen for tubule boxes, a muscular wall for artery boxes. The exceptions are listed in section 2.

So in the released v2 boxes, `x` indexes rows (top to bottom) and `y` indexes columns (left to right), as in a numpy array. The packages' README names the columns but not the axes. Anyone who cuts image patches by reading `x` as horizontal gets the wrong tissue or blank glass, without any error message whenever the box happens to fit. We checked 14 v2 slides; v1 boxes were not checked.

## 2. What the 30 most extreme objects are (AI visual triage, not a pathologist)

| Compartment (screen feature) | Targets | Plausible object of the labelled kind | Not of the labelled kind | Artefact | Cannot tell |
|---|---|---|---|---|---|
| Glomeruli: smallest area (8), highest or lowest mesangial fraction (1 each) | 10 | 4 | 2 | 2 | 2 |
| Tubules: highest luminal fraction | 10 | 9 | 0 | 1 | 0 |
| Arteries: largest area (9), smallest (1) | 10 | 9 | 1 | 0 | 0 |
| **All** | **30** | **22** | **3** | **3** | **2** |

- **Glomeruli.** 3 of the 8 "smallest" glomeruli look like real small tufts in a Bowman's capsule, one with a shrunken tuft and a wide Bowman's space. 2 look like a small vessel or an atrophic tubule in cross-section rather than a glomerulus. One is a detached tuft fragment lying free on the glass, and 2 are unclear. The high-mesangial-fraction outlier looks like a real hypercellular tuft. The low-mesangial-fraction outlier is a glomerulus torn open at the tissue edge.
- **Tubules.** All 10 come from one slide with diffuse tubular dilation and thickened basement membranes. 9 are real dilated tubules with flattened lining cells. One is a tubule torn open at the tissue edge, so its "lumen" is the empty space outside the tissue. The object audit's high-lumen dominance therefore reflects real dilated tubules, amplified by our own robust z-score on a zero-heavy fraction (see the audit's lesson). It is not mostly segmentation failure.
- **Arteries.** The 9 "largest" are real arteries: thick muscular walls, several cut obliquely, one broken across a tissue tear with the box spanning both pieces. The "smallest artery" covers 4 pixels on loose tissue at the edge of a section. It is a speck, not a vessel.

## 3. The same object appears more than once: serial sections on one slide

12 of the 30 targets are 6 pairs of the **same object seen twice**: 2 tubule pairs and 4 artery pairs. In each pair the two crops show the same structure with the same neighbours. The slides carry two or more serial sections of the same biopsy core side by side; the overview images show this. KPMP's segmentation measured every section, and the workbook has no column saying which section a row comes from.

- The two tubule pairs sit on the same slide, and both are shifted by the same amount: about 4,470 pixels along one axis and 41,250 along the other. That is what one copy of a section placed beside another would produce.
- The 30 targets are therefore 24 distinct objects.

Why it matters for anyone using the per-object vectors:

1. **Counts.** The number of glomeruli, tubules or arteries per slide or per participant counts each structure once per section. A slide with two sections reports about twice as many.
2. **Independence.** Per-object statistics, outlier screens and object-level training sets count repeats as separate samples. A within-slide outlier list can name the same object twice. That happened in 6 of 30 cases here, and in 8 of the 10 artery targets.
3. **Rarity.** An object that looks rare (1 of 1,000) may be one structure shown twice.

Prior art (searched 2026-10-28): non-independence of glomeruli across serial sections is known in general. A deep-learning study of deceased-donor kidney sections (Marsh et al., JAMA Network Open 2021) notes that "glomeruli sampled in subsequent sections may not be independent", and NEPTUNE's digital-pathology protocol aligns biopsy levels to annotate glomeruli across sections. Registration methods such as Map3D match glomeruli across serial slides. We found no report that KPMP's released per-object pathomics vectors repeat objects across the sections on one slide without a section label.

**Next, pre-registered in `kpmp-twins-prereg-v1-2026-10-28.md` (same release):** a census, over all 220 v2 workbooks, of how many slides carry repeated sections and what share of objects have a twin. It will detect each slide's section shift as a dominant displacement between objects of matching size, using workbook boxes only, with a shuffled-position control. No images are involved.

## 4. Why both of this round's jobs ran without the cached workbooks

The compute pool keeps one copy of each data volume per machine. The KPMP workbook cache was filled on one machine (census passes 1-3 and the object audit ran there). Both new jobs landed on the other machine, where that volume was empty. So:

- `kpmp-patches-v1` found no workbook for any of its 14 packages. It still cut every target crop, which is how section 1 was found, but it could not confirm boxes against the workbook or crop "typical" comparison objects.
- `kpmp-tbm0-v1` (the zero-TBM study, pre-registration `kpmp-tbm0-prereg-v1-2026-10-28.md`, tag v0.9.17) found 0 of 361 packages cached. It graded nothing; all eight predictions stay **pending**, unchanged.

The fix is `../kidney/kpmp_fill.py` 1.0, committed alongside this note once its offline tests pass. Before an analysis, it fills the cache on whichever machine the job lands on. It reads only the small members the census keeps (feature workbooks, OME-XML, README) straight out of each remote zip with HTTP range requests, and skips the multi-hundred-megabyte slides and masks. If the server does not honour range requests, it stops and says so rather than downloading every whole zip. The zero-TBM study re-runs as `kpmp-tbm0-v2` with this step first; its analysis code and predictions are unchanged.

## Limits

- **One AI reader, no pathologist.** Categories such as "vessel rather than glomerulus" are judgement calls from a single 1024-pixel crop of a PAS stain. They may be wrong, and a kidney pathologist could disagree with any of them.
- 30 targets from 14 slides were chosen as extremes, not at random. Shares here say nothing about the typical object.
- The duplicate pairs were spotted by eye among the targets. Their prevalence across KPMP is unknown until the census in section 3 runs.
- The orientation finding rests on 14 v2 slides: geometry for all 30 boxes and a visual check of 4 crops. v1 was not checked.

## Acknowledgement

The results here are in whole or part based upon data generated by the Kidney Precision Medicine Project. Accessed October 2026. https://www.kpmp.org. KPMP is supported by the National Institute of Diabetes and Digestive and Kidney Diseases through grants U01DK133081, U01DK133091, U01DK133092, U01DK133093, U01DK133095, U01DK133097, U01DK114866, U01DK114908, U01DK133090, U01DK133113, U01DK133766, U01DK133768, U01DK114907, U01DK114920, U01DK114923, U01DK114933, U24DK114886, UH3DK114926, UH3DK114861, UH3DK114915, UH3DK114937, 1U01DK144965-01 and 1U01DK144994-01 (list copied from KPMP's citing page, https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata, on 2026-10-18). We thank the KPMP participants and US taxpayers whose support made the data possible.

## Sources

- `kpmp-objects-results-v1-2026-10-28.md`, `kpmp-tbm0-prereg-v1-2026-10-28.md` (this folder)
- Job outputs `compete-results/kpmp-patches-v1/` and `compete-results/kpmp-tbm0-v1/` (local; crops never published)
- Development and Validation of a Deep Learning Model to Quantify Glomerulosclerosis in Kidney Biopsy Specimens, JAMA Network Open (PMC7818108), https://pmc.ncbi.nlm.nih.gov/articles/PMC7818108
- The Application of Digital Pathology to Improve Accuracy in Glomerular Enumeration in Renal Biopsies (NEPTUNE), PLOS ONE 2016, https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0156441
- Map3D: Registration Based Multi-Object Tracking on 3D Serial Whole Slide Images, arXiv 2006.06038
