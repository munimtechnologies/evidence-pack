# Results: how MDPI and Frontiers "article 1" records gain OpenAlex citations their citers never made (mechanism v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

Pre-registration: `article-number-1-mechanism-prereg-v1-2026-10-17.md` (commit 3c7c9e5, release v0.4.19). Code: `article1_mechanism.py` at that commit, run unchanged. Data: `article1_mechanism_v1_results.json`, `article1_mechanism_v1_reads.jsonl` (one row per citer read) and `article1_mechanism_v1_provenance.json` (the exact commit and file sizes the job used).

## Run

- Job `article1-mechanism-v1`, python:3.12, 1 CPU, run 2026-10-17 09:59-10:01 UTC. The job fetched the pre-registration, code, tests and input from main at 3c7c9e5 (pinned helpers: `article1_check.py` @a5a741e, `openalex_article1.py` @1d2782e). The 20 offline tests passed before any data were collected.
- 66 units were eligible. The seeded sample of 8 targets: Molecules 24:1, Materials 10:1, Nutrients 11:1, IJMS 18:1, IJERPH 13:1, Cancers 10:1 (MDPI) and Front Plant Sci 2019:1, Front Neurol 2017:1 (Frontiers).
- 199 OpenAlex citers of the targets were read in Crossref (IJERPH returned 24), and 200 OpenCitations citers of the 8 same-volume controls. 407 Crossref calls, 15 OpenAlex calls, none failed.

## Scoring against the pre-registration

| Hypothesis | Pre-registered rule | Result | Verdict |
|---|---|---|---|
| H1: page-1 references explain the unsupported citers | share >= 0.70, >= 2x controls, Fisher p < 0.01 (n >= 40 / 20) | **114 of 124** unsupported citers (0.92) deposit a reference into the target's volume with first page "1"; **0 of 178** control citers have one (other than to the control). p = 4.0e-72 | **supported** |
| H2: forward test (a page-1 reference creates the link) | >= 15 control citers whose reference to the control has first page "1" | only **1** such citer (Front Oncol 2022), and it is not linked to article 1 | **untestable** |
| H3: the link is added, not swapped | >= 0.80 of page-1 DOI references keep their own OpenAlex link (n >= 20) | **90 of 90** | **supported** |

Two of three hypotheses held; the third could not be tested. As the pre-registration says, untestable is neither a success nor a failure.

**Why H2 was untestable.** Page-1 references are rare among citers chosen without reference to OpenAlex: 1 of 178 control citers cited the control with first page "1", and none had another page-1 reference into the volume. The unsupported citers were chosen because OpenAlex links them to article 1, and 92% of them have such a reference. That contrast is what H1 measures. A forward test needs a far larger frame of independently chosen citers to collect enough page-1 references (see "What comes next").

The baseline that H2 would have compared against is clean. Of the 174 control citers that OpenAlex returned and that have no page-1 reference into the volume, **0** are linked to that volume's article 1.

## Descriptive results (pre-registered as not tested)

- All 124 unsupported citers are in OpenAlex, and all 124 list the target in `referenced_works` (the sampling check).
- 122 of 124 have at least one deposited reference into the target's volume. Their 120 page-1 references are 90 with a DOI and 30 without.
- Median OpenAlex `referenced_works` minus Crossref deposited references, for unsupported citers: **+1.5**.
- **Citer years. All 124 unsupported citers were published in 2021 or earlier; none from 2022 on.** For the control citers, H2's split is empty in the early group (no page-1 references up to 2021) and 0 of 1 from 2022.

## A pattern seen in the data (post hoc, not tested)

The pre-registration asked only for the year split among unsupported citers. Counting every sampled target citer by hand from `article1_mechanism_v1_reads.jsonl`:

| Citer published | read | unsupported | genuine | other work | DOI only | too few refs |
|---|---|---|---|---|---|---|
| up to 2021 | 154 | **124 (81%)** | 13 | 9 | 6 | 2 |
| 2022 on | 45 | **0** | 27 | 9 | 7 | 2 |

OpenAlex's yearly counts tell the same story. Hand-read from the OpenAlex API on 2026-10-17: Molecules 24:1 has 246 citations, 209 dated 2019-2021 and 37 from 2022 on. Front Neurol 2017:1 has 299, with 284 dated 2016-2021 (the 1 in 2016 is before publication), 14 from 2022 on, and 1 more dated 2013.

Microsoft Academic Graph, from which OpenAlex was built, stopped at the end of 2021. If the extra links were made by MAG's reference matching and carried into OpenAlex, only citers from 2021 or earlier would carry them. That fits, but it is an idea read off this data, so it gets its own held-out test (below) before it is claimed.

An independent report fits the same year signature. In the OpenAlex community forum (26 Feb 2025, "Publications with many more citations in OpenAlex than in other databases"), a user describes a 2019 Scientific Reports paper (10.1038/s41598-019-52748-8, article 16885, not article 1). It has about 1,770 OpenAlex citations against about 30-40 elsewhere. Its OpenAlex yearly counts, read on 2026-10-17, are 566 for 2020 and 1,136 for 2021, then 9 to 18 a year from 2022 to 2024. That thread did not identify a cause, and this study does not test that paper.

## Rows that break the H1 pattern

10 of 124 unsupported citers have no deposited page-1 reference into the target's volume:
- 8 deposit a reference into the volume but none with first page "1" (for example 10.1111/geb.13427, 10.1128/mbio.01376-19, 10.1136/jitc-2020-002086, 10.1111/obr.13355).
- 2, both citers of Materials 10:1 (10.1016/j.matdes.2017.02.006, 10.1088/1742-6596/1082/1/012074), deposit no reference into the volume at all.

These could come from references OpenAlex or MAG read from somewhere other than the Crossref deposit (the full text or PubMed), which the pre-registration listed as a limit. They were not read further in this run.

## What this shows, and what it does not

- **Shown (H1, H3).** For these 8 records, nearly every OpenAlex citer that does not really cite article 1 deposits a reference to *another* paper in the same volume with first page "1". OpenAlex keeps the link to that paper and *also* links article 1. A reference that gives volume V and first page "1" in an article-numbered journal marks the misattributed citations, and the extra link is added on top of the correct one.
- **Not shown.** That a page-1 reference *causes* the link in general (H2, untestable here), or that the effect is limited to citers up to 2021 (post hoc).
- **Limits.** 8 records, 6 from MDPI and 2 from Frontiers. Only Crossref deposits were read. OpenAlex changes over time, so these figures stand as of 2026-10-17. AI agents designed, ran and scored the test; no independent human check has been done.

## What comes next

A forward test, pre-registered before any data are collected (`article-number-1-forward-prereg-v2-2026-10-17.md`, code `article1_forward.py`). It draws random Crossref journal articles from 2019-2021 and from 2023-2025, so OpenAlex plays no part in which papers are chosen. For each article, it takes every DOI reference into a 2016-2019 MDPI or Frontiers volume and asks whether OpenAlex links that article to the volume's article 1. It compares references with first page "1" against those without, and the 2019-2021 citers against the 2023-2025 citers.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
