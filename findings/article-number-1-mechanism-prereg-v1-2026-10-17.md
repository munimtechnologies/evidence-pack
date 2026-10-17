# Pre-registration: how do MDPI and Frontiers "article 1" records gain OpenAlex citations their citers never made? (mechanism v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

Written and committed before any data for this test were collected. Code: `article1_mechanism.py` with offline tests `test_article1_mechanism.py`, committed with this note. Input: `article1_openalex_v2_units_oa.jsonl` (public since commit 39db945). Seed 20261025.

## Background

The v2 study (`article-number-1-openalex-v2-results-2026-10-17.md`) found that OpenAlex gives article 1 of 2016-2019 volumes of 14 MDPI and 10 Frontiers journals far more citations than Crossref does. Of 119 readable OpenAlex citers of three such records, only 2 clearly cite them in their Crossref deposits. That study did not test how the extra links arise.

## Pilot (before this note; not part of the test)

All pilot data come from records already read and published in v2 (`article1_openalex_v2_reads.jsonl`). All are citers of Front Plant Sci 2016 article 1 (10.3389/fpls.2016.00001), which this test excludes. Read by hand on 2026-10-17 through the public Crossref and OpenAlex APIs.

| "unsupported" citer | Crossref refs | Front Plant Sci references with first page "1" | in OpenAlex |
|---|---|---|---|
| 10.1016/j.nbt.2016.12.005 | 123 | vol 7: 10.3389/fpls.2016.00075 | not checked |
| 10.1007/s12298-021-01053-8 | 59 | vol 6: 10.3389/fpls.2015.00008; vol 7: 10.3389/fpls.2016.01758 | 67 links. Both real papers linked, **plus** both article 1s: fpls.2015.00001 (1,940 OpenAlex citations) and fpls.2016.00001 |
| 10.1111/aab.12561 | 89 | vol 7, no DOI (article number 1930 deposited as the issue); also vols 5, 6, 9, all first page "1" | not checked |
| 10.1093/jxb/ery240 | 90 | vol 7: 10.3389/fpls.2016.01849 | 92 links. The real paper linked, **plus** fpls.2016.00001 |

What the pilot suggests: when a reference to an article-numbered journal gives volume V and first page "1", OpenAlex links the citer to article 1 of volume V **as well as** to the paper actually cited, even when the reference carries the right DOI. That is 4 citers of one record, so this test uses fresh records and adds a forward test (H2) on citers chosen independently of OpenAlex.

## Design

**Targets.** From `article1_openalex_v2_units_oa.jsonl`, take units that are confirmatory, MDPI or Frontiers, volume year 2016-2019, with at least 10 far controls and article 1 "top" (a larger OpenAlex excess than every far control, as in v2's H1). Keep those with an OpenAlex-minus-Crossref gap of 50 or more, and drop v2's three H4 targets (fpls.2016.00001, fmicb.2016.00001, su8010001). Sort by DOI and take a seeded sample of 8 (`random.Random(20261025)`). The **control** of each unit is its far control (article 41-60 of the same volume) with the most Crossref citations.

**Target citers.** A seeded OpenAlex sample of 25 works listed as citing each target (seed 20261025 + i). Each is read in Crossref and labelled as in v2 (`openalex_article1.classify_citer`). For each **unsupported** citer, record every deposited reference into the target's volume with first page "1" (a **page-1 reference**), excluding the target itself. "Into the volume" means the reference's DOI fits the volume's DOI pattern (MDPI `10.3390/<code><volume>` plus 6 digits; Frontiers `10.3389/<code>.<year>.` plus 5 digits). For a reference without a DOI, its journal-title must match the journal's Crossref full or short name (the same words, or each word a prefix: "Front Plant Sci") and its volume must match.

**Control citers.** Up to 25 citers of each control, sampled with seed 20261025 + 100 + i from OpenCitations (citations drawn from Crossref deposits, so chosen independently of OpenAlex). If OpenCitations lists fewer than 5, OpenAlex's citers are used instead, and the source is recorded. A control citer counts ("found") if its Crossref deposit has a reference carrying the control's DOI and does not cite article 1 by DOI or title. For each, record whether that reference's first page is "1" and whether it has other page-1 references into the volume.

**OpenAlex links.** For every unsupported target citer and found control citer, read OpenAlex `referenced_works` (batches of 25 DOIs). Look up the OpenAlex ids of the page-1 references' DOIs.

## Hypotheses (fixed thresholds, alpha 0.01)

- **H1 (page-1 references explain the unsupported citers).** Among unsupported target citers (at least 40), the share with at least one page-1 reference into the target's volume is **at least 0.70**. It must also be at least twice the share of found control citers (at least 20) with a page-1 reference into the volume other than the control, and a one-sided Fisher exact test must give p < 0.01. *Prediction: supported.*
- **H2 (forward test: a page-1 reference creates the link).** Among found control citers that have no other page-1 reference into the volume and are in OpenAlex, compare those whose reference to the control has first page "1" with those whose reference has another or no first page (at least 15 in each group). Supported if the share whose OpenAlex `referenced_works` includes article 1 is **at least 0.30** in the page-1 group and at least 3 times the share in the other group, with one-sided Fisher p < 0.01. *Prediction: supported (moderate confidence: the effect may be limited to older citers, see below).*
- **H3 (added, not swapped).** Among page-1 references with a DOI in unsupported citers found in OpenAlex, where the reference's own work is in OpenAlex (at least 20), the share whose own work is still in the citer's `referenced_works` is **at least 0.80**. *Prediction: supported.*

Any of these with too few records is reported as "untestable", not as a failure or a success.

## Descriptive (not tested)

- Citer publication years, up to 2021 and from 2022, for unsupported citers; and H2's two rates split the same way. The v2 pattern faded for 2021-2023 volumes, and Microsoft Academic Graph, which OpenAlex grew from, stopped at the end of 2021. If the extra links were inherited from it, H2 should hold mainly for citers up to 2021. This split is reported, not tested.
- How many unsupported citers have any reference into the volume; how many page-1 references carry a DOI; the median of (OpenAlex links minus Crossref deposited references) for unsupported citers.
- A check: the share of unsupported citers whose OpenAlex `referenced_works` includes the target (should be nearly all, since they were sampled as its citers).

## Limits stated in advance

- Only Crossref deposits are read. Where OpenAlex took a citer's references from somewhere else (PDF parsing, PubMed), the deposit may differ from what OpenAlex matched.
- "First page" is read as deposited. Some deposits put the article number in the issue or first-page field. The test counts only first page "1" exactly.
- A batch of OpenAlex DOI lookups can fail on an unusual DOI. Failed calls are counted, and citers OpenAlex does not return drop out of H2 and H3.
- OpenAlex changes. Counts and links are as of the day the job runs.
- AI agents designed this test and will run and score it. Pre-registration guards against moving the goalposts; it is not an independent human check.

## What would follow

If H1-H3 hold, the extra links come from matching references by journal, volume and first page, and a reference's first page of "1" in an article-numbered journal is read as article 1, even when the DOI is right and already linked. That would explain why article 1 is singled out and where a fix belongs. If H2 fails while H1 holds, the page-1 pattern marks the affected citers but does not by itself create the link, and another cause must be looked for.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
