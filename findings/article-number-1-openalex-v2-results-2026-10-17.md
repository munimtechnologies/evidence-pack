# Results: OpenAlex gives MDPI and Frontiers "article 1" records thousands of citations that the citing papers' reference lists do not support (v2, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

Scored against `article-number-1-openalex-prereg-v2-2026-10-17.md` and its amendment `article-number-1-openalex-prereg-v2-amendment-2026-10-17.md`. Both went public in commit a6fac9c (2026-10-17 06:24 UTC). The sealed job `openalex-article1-v1` ran from 06:59 to 07:31 UTC the same day, after that commit, and its first step checked that both notes were public. No hypothesis, threshold or seed was changed. No deviation from the code at 1d2782e (`openalex_article1.py`) or a2e798c (`rebuild_units.py`).

## Summary

For 2016-2019 volumes of 14 MDPI and 10 Frontiers journals, OpenAlex gives the volume's article 1 far more citations than Crossref does, and far more than it gives other articles in the same volume. In 74 of 86 eligible volumes, article 1 had a larger OpenAlex excess than every one of up to 20 same-volume control articles (about 4 expected by chance). Of 120 citing works that OpenAlex lists for three of these records, read in Crossref, only 2 deposit a reference that is clearly to them, and 116 deposit full reference lists with no trace of them. For volumes of 2021-2023, the pattern is gone. Crossref's own counts for the same articles show no article-1 inflation (v1). **This is an error inside OpenAlex's citation links, not in the publishers' or Crossref's data.**

## Input check (the amendment)

`rebuild_check.json`: the rebuild found all 161 v1 units and no others (161 matched). Article-1 Crossref counts changed by a median of 0 (range 0 to 1). All 161 units kept the same v1 "top" flag and the same number of far controls. So the published rebuild is a faithful stand-in for the unpublished v1 file. OpenAlex knew all 3,239 DOIs (65 calls, none failed), so the results are not partial.

## Hypotheses

| | prediction | result | detail |
|---|---|---|---|
| **H1** article-1 excess in OpenAlex, 2016-2019 | supported | **supported** | 86 units; article 1 top in **74** (4.1 expected); exact Poisson-binomial p = 2.3e-84; median effect **4.24** (threshold 2.0) |
| **H2** negative control, MDPI 2021-2023 | not supported | **not supported** (as predicted) | 42 units; top in 4 (2.0 expected); p = 0.14; median effect 1.06 |
| **H3** general excess on older papers | supported, low confidence | **not supported** (prediction wrong) | median control excess 1.151 (old) vs 1.043 (new); ratio 1.10, below 1.5 |
| **H4** the excess is misattributed | supported | **supported** | genuine share of OpenAlex citers of the targets 2 / 119 = **1.7%** (threshold under 50%, at least 20 citers) |

**H4 calibration passed.** The same reading applied to each target's most-cited control found 84 of 84 classifiable citers genuine (100%; threshold at least 70% on at least 10). The other 34 control citers were "doi_only" (17) or had too few deposited references (17).

H4 targets (OpenAlex vs Crossref counts): Front Plant Sci 2016 article 1 (1,503 vs 41), Front Microbiol 2016 article 1 (1,185 vs 21), Sustainability 8:1 (2016; 1,060 vs 52). Of the 120 sampled citers of these three records (all with DOIs), 116 deposit at least 5 references in Crossref and none of them to the target by DOI or title ("unsupported"); 2 are genuine, 1 cites another work under the target's DOI, and 1 is DOI-only.

H3's failure matters. The controls of 2016-2019 have only slightly more OpenAlex excess than those of 2021-2023 (about 15% vs 4% above Crossref). So the large excess is not a general feature of older papers. It is concentrated on article 1.

**Descriptive (2020, not tested):** 24 units, article 1 top in 15 (1.1 expected), median effect 1.80. 2020 looks like a transition year. In every row of the per-unit table, the article-1 OpenAlex count was the same as in the v1 snapshot taken a few hours earlier.

## How big

A few examples from the per-unit table (`article1_openalex_v2_results.json`), OpenAlex vs Crossref: Front Plant Sci 2016 article 1, 1,503 vs 41; Front Microbiol 2016, 1,185 vs 21; Molecules 21:1 (2016), 1,040 vs 58; Sensors 17:1 (2017), 873 vs 88; Front Immunol 2018, 973 vs 162; Materials 12:1 (2019), 342 vs 10. IJMS 20:1 (2019; 1,093 vs 46) was excluded in advance and is not in the tests.

## A hand check of the mechanism (one citer, not pre-registered)

One "unsupported" citer of Front Plant Sci 2016 article 1 was read in full in Crossref after the job: 10.1016/j.nbt.2016.12.005 (123 deposited references). None carries the target's DOI. Its only Frontiers in Plant Science 2016 reference (`bib0315`) is a different paper, deposited with **DOI 10.3389/fpls.2016.00075, volume 7, first page "1"**. Frontiers and MDPI number articles, not pages, and a reference's "first page" is often given as 1. A link built from journal, volume and first page alone would land on article 1. This fits the H1-H4 pattern, but it is **one example**. We have not tested how OpenAlex builds these links. The fade after 2020 would fit links inherited from Microsoft Academic Graph, which stopped at the end of 2021, but that is also untested.

## Relation to prior work

Kriváchy (arXiv:2511.01675) documented "article number 1" citation outliers for Springer Nature's online-only journals. Our v1 study found no such inflation in Crossref at MDPI or Frontiers. This study finds it in OpenAlex, with pre-registered same-volume controls and a citer-level check that most of the extra citations have no basis in the citing papers' deposits. An OpenAlex community thread reports single cases of unexplained excess citations. Our searches on 2026-10-17 found no measurement of this pattern for MDPI or Frontiers in OpenAlex.

## What it means for users of OpenAlex counts

- Treat the OpenAlex citation count of any article numbered 1 in a 2016-2020 volume of an article-numbered journal as suspect until checked against Crossref or the citing reference lists.
- These records can enter "most cited" lists, journal and author indicators and research-assessment exercises built on OpenAlex. In the 2016-2019 table, the median article-1 record has about 4 times its controls' excess.
- If the hand check above shows the general mechanism, the fix belongs in the reference-matching step: a reference with a DOI should not also be matched by journal, volume and first page, and a first page of "1" in an article-numbered journal should not be read as an article number.

## Limits

- Three MDPI/Frontiers H4 targets were read, with 40 citers each, chosen by the largest OpenAlex-minus-Crossref gap. The 1.7% genuine share is for those records. H1 shows that the excess is widespread, not how much of it is spurious in every unit.
- "Unsupported" means the citer's Crossref deposit has no matching DOI or title. A citer could still cite the target through a reference deposited with neither, but the controls' 100% calibration makes this rare.
- OpenAlex changes over time. The counts are from 2026-10-17.
- AI agents designed, ran and scored this. Pre-registration guards against moving the goalposts. It is not an independent human check.

## Files (repository root)

- `article1_openalex_v2_results.json`: hypotheses, H4 detail and the per-unit table.
- `article1_openalex_v2_units_oa.jsonl`: every article's Crossref and OpenAlex count, with OpenAlex work ids.
- `article1_openalex_v2_reads.jsonl`: the H4 label of every citer read.
- `article1_openalex_v2_rebuild_check.json` and `article1_openalex_v2_units_rebuilt_part1.jsonl` / `_part2.jsonl`: the rebuilt input, in parts under 2 MB.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
