# Results: a reference with first page "1" makes OpenAlex link older citers to article 1 of that volume (forward test v2, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

Pre-registration: `article-number-1-forward-prereg-v2-2026-10-17.md`, committed (release v0.4.20) before any data were collected. The job ran the frozen code from main at 0db8338 on 2026-10-17, 12:51-12:56 UTC, and its offline tests passed first (13 of 13). Code `article1_forward.py`. Data in this repository:
- `article1_forward_v2_results.json`: the job's own scoring;
- `article1_forward_v2_pairs.jsonl`: every pair looked up, with its page-1 references and the OpenAlex outcome;
- `article1_forward_v2_provenance.json`: the commit of each file the job ran.

The job is named article1-forward-v1 in the compute queue; the study is forward test v2.

## Result: both hypotheses supported

| | Pairs with a page-1 reference ("exposed") | linked to article 1 | Pairs without one ("unexposed", seeded sample) | linked to article 1 |
|---|---|---|---|---|
| Citers 2019-2021 | 40 | **13 (0.325)** | 297 | **0 (0.000)** |
| Citers 2023-2025 | 41 | **0 (0.000)** | 291 | 0 (0.000) |

- **H1 (forward, old era): supported.** 13 of 40 exposed pairs are linked to the volume's article 1, against 0 of 297 unexposed pairs. The pre-registered rule needed a share of at least 0.30, at least 3 times the unexposed share, and a one-sided Fisher p < 0.01. The share is 0.325 and p = 1.3e-13. *Predicted: supported (moderate confidence).*
- **H2 (era): supported.** For 2023-2025 citers, 0 of 41 exposed pairs are linked (rule: at most 0.10), against 13 of 40 for 2019-2021 citers (one-sided Fisher p = 3.2e-5; rule p < 0.01). *Predicted: supported.*

Both p values were checked by hand: a hypergeometric tail with all 13 linked pairs in the exposed group, giving 1.31e-13 and 3.2e-5.

**The H1 margin is narrow.** The pre-registered threshold was 0.30. 12 of 40 would still have passed, but 11 of 40 would not. A Wilson 95% interval for 13 of 40 runs from about 0.20 to 0.48 (computed by hand). The safe reading: for older citers, roughly one in three citer-volume pairs with a DOI reference of first page "1" into a 2016-2019 MDPI or Frontiers volume also carries an OpenAlex link to that volume's article 1. Pairs without such a reference never did (0 of 297).

## Sampling (descriptive, as pre-registered)

| | Crossref calls | Works read | Duplicates | Citers with a covered pair | Pairs | Exposed | Unexposed dropped (page-1 ref without DOI) |
|---|---|---|---|---|---|---|---|
| 2019-2021 | 50 (0 failed) | 4,998 | 2 | 670 | 1,070 | 40 | 352 |
| 2023-2025 | 82 (0 failed) | 8,199 | 1 | 1,159 | 1,730 | 42 | 474 |

Each era stopped on the exposure count (40), as pre-registered, never on the outcome. OpenAlex lookups: 592 of 593 citers and 159 of 161 article-1 records were found, with 28 calls and 0 failures. Article 1 of Sustainability volume 10 (10.3390/su10010001) and of Frontiers in Cardiovascular Medicine 2016 (10.3389/fcvm.2016.00001) were not found in OpenAlex by DOI. Their pairs drop out: 3 unexposed pairs in the old era, and 1 exposed plus 7 unexposed in the new era. Two more new-era unexposed pairs drop out because their citers are marked as not found (10.12688/wellcomeopenres.18767.2 and 10.15789/1563-0625-aip-3222). The summary counts only one missing citer (592 of 593 found), and that small mismatch is unexplained. It touches only these two unexposed pairs, so neither hypothesis depends on it.

By publisher (descriptive):

| | Old exposed linked | Old unexposed linked | New exposed linked | New unexposed linked |
|---|---|---|---|---|
| MDPI | 5 / 15 | 0 / 140 | 0 / 19 | 0 / 165 |
| Frontiers | 8 / 25 | 0 / 157 | 0 / 22 | 0 / 126 |

## Every old-era exposed pair, read (post hoc, not tested)

All 40 old-era exposed pairs are in `article1_forward_v2_pairs.jsonl`, and all were read.
- **By citing work.** They come from 34 distinct citing works, and 12 of the 34 have at least one linked pair. So the citer-level share (0.35) is close to the pair-level share. Clustering does not drive H1.
- **Within one citer, the link fires for some page-1 references and not others.** *Remote Sensing of Environment* 2021 (10.1016/j.rse.2021.112299) carries three exposed pairs. The pairs into Remote Sensing volumes 8 and 11 are linked to their article 1; the pair into Frontiers in Plant Science 2019 is not. A BMC citer (10.1186/s40643-019-0276-2) is linked for Sustainability 8 but not for Frontiers in Microbiology 2018. So whatever decides the link works per reference, not per citer. This fits the limit stated in advance that the matching "fires only for some page-1 references".
- **Unexposed pairs never linked** (0 of 588 across both eras). So a citer that cites a 2016-2019 MDPI or Frontiers volume without page "1" did not acquire an article-1 link in this sample.

## What this adds to the earlier article-1 studies

- **OpenAlex v2 results:** in 74 of 86 volumes from 2016-2019, article 1 had the largest OpenAlex-over-Crossref excess of its volume.
- **Mechanism v1:** 114 of 124 OpenAlex citers that do not really cite article 1 deposit a reference with first page "1" into its volume. That study chose citers *because* OpenAlex linked them.
- **This test** runs in the other direction, on citers chosen at random from Crossref without OpenAlex: a page-1 reference goes with the extra link, and a reference without one does not. The era contrast confirms the observation made after the mechanism data came in, which was not claimed then: the extra links belong to citers published up to 2021 and are absent for 2023-2025 citers.

Taken together: OpenAlex adds a link to article 1 on top of the correct one when an older citing work's reference to another paper in the same volume has first page "1". MDPI and Frontiers papers are article-numbered, so their Crossref deposits often give first page "1". The pattern fits matching on journal, volume and first page done by Microsoft Academic Graph (MAG), which stopped at the end of 2021 and from which OpenAlex grew. This study does not prove where the links came from.

## Limits

- Exposure is defined only by references deposited with DOIs. MAG or OpenAlex may have read a citer's reference list from the full text, where the page can differ.
- Pairs that share a citer are not independent; the Fisher tests treat them as if they were. The citer-level reading above (12 of 34) suggests this does not matter here.
- Only 2016-2019 volumes of 14 MDPI journals and all Frontiers journals were covered. Other article-numbered journals are untested.
- OpenAlex changes. These links are as of 2026-10-17.
- AI agents designed, ran and scored this test. Pre-registration guards against moving the goalposts; it is not an independent human check.

## What follows (from the pre-registration)

- **A check anyone can run:** `doi_hygiene.py link <article-1 DOI> <citing work's Crossref JSON>`, added with this release. It says whether a citing work cites an MDPI or Frontiers article 1 itself, cites a page-"1" sibling in the same volume instead (the pattern found here), or neither.
- The same forward test at other article-numbered journals (PLOS ONE, Scientific Reports, BMC, eLife), pre-registered before it runs.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
