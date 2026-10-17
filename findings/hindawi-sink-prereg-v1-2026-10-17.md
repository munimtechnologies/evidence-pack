# Pre-registration: one record per Hindawi journal-year collects OpenAlex citations meant for its other papers (v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

Code: `hindawi_sink.py` (offline tests in `test_hindawi_sink.py`). It reuses helpers from `article1_check.py`, `openalex_article1.py` and `article1_mechanism.py`. This note and the code are committed before any confirmatory data are collected. The job reads the copy of this note on `main` and stops if it is missing.

## Why

Our four article-1 studies (`article-number-1-openalex-summary-2026-10-17.md`) found this: when a citing work's deposited reference gives journal, volume and first page "1", OpenAlex links it to the volume's article 1 as well as to the paper actually cited. The links come from citers dated up to 2021, which fits matching inherited from Microsoft Academic Graph (MAG).

Hindawi (DOI prefix 10.1155) is an extreme case of the same setup. Its volume is the year, and every article starts at page 1: OpenAlex lists BioMed Research International 2017 articles as volume "2017", first page "1". So "journal + volume + page 1" fits every article of a journal-year, not just one. Our prediction is that the matcher sends those references to **one** record per journal-year, a "sink". Hindawi publishes many medical journals (BioMed Research International, Oxidative Medicine and Cellular Longevity, Mediators of Inflammation and others). An inflated OpenAlex count there can mislead evidence maps, rankings and bibliometric studies that weight papers by citations.

## Pilot, seen before this note (held out of every confirmatory count)

- **BioMed Research International 2017** (OpenAlex source S1010394304). We checked 6 of its 10 most-cited works in OpenAlex against Crossref, and one is a clear outlier: 10.1155/2017/6353510 ("The STARTEC Decision Support Tool ...") has 1,178 OpenAlex citations against 8 in Crossref. The other five we checked have OpenAlex counts 8-43% above Crossref (hand-computed). Its OpenAlex citations by year: 32 (2017), 150, 274, 329, 389 (2021), then 0 in 2022 and 1 a year from 2023 on.
- We read the Crossref deposits of 2 of its 12 seeded-sample OpenAlex citers by hand: Int J Biol Macromol 2021 (10.1016/j.ijbiomac.2021.06.076) and Bull Environ Contam Toxicol 2020 (10.1007/s00128-020-02981-z). Neither cites STARTEC. Each cites a *different* BMRI 2017 paper with volume "2017" and first page "1" (10.1155/2017/2370927 and 10.1155/2017/5801432 respectively), both with DOIs.
- **Oxidative Medicine and Cellular Longevity 2018** (S20935308). We checked the 10 most-cited works in OpenAlex against Crossref. Nine are 10-28% above Crossref (hand-computed). One, 10.1155/2018/5879281 ("A Typical Immune T/B Subset Profile Characterizes Bicuspid Aortic Valve"), has 363 in OpenAlex against 10 in Crossref.
- Prior art (searched 2026-10-17): Kriváchy (arXiv:2511.01675) documents article-number-1 errors in Springer Nature metadata. "Sneaked references" (arXiv:2310.02192) involve one Hindawi paper, but as deliberate manipulation of deposits. We found no report of Hindawi sinks in OpenAlex or MAG.

These two journal-years are listed in `PILOT` and reported separately. They are never scored.

## Design

1. **Population.** For each year 2016-2019 ("old") and 2022-2023 ("new", after MAG ended in 2021), Crossref's ISSN facet lists the ISSNs of Hindawi (prefix 10.1155) journal articles. OpenAlex then groups that year's works by source for those ISSNs. A journal-year is eligible if OpenAlex has at least 100 works for it.
2. **Sample.** A seeded sample (seed 20261031) of up to 160 old and 80 new eligible journal-years, sorted by (year, source) before sampling.
3. **Per journal-year.** We take the 25 works with the most OpenAlex citations, keeping those whose DOI is a 10.1155 DOI of that year and that Crossref returns. Each gets an excess E = (OpenAlex + 1) / (Crossref + 1).
   - The **sink** is the work with the largest E among works with E >= 10 and OpenAlex - Crossref >= 50, if there is one.
   - The **control** is the work with the most OpenAlex citations among those with E < 2.
   - A journal-year is scored only if at least 10 works remain.
4. **Citer reads.** We take a seeded sample of up to 8 old-era sinks. For each sink, and for its control, we read 15 seeded OpenAlex citers in their Crossref deposits.
   - **genuine:** a reference carries the target's DOI, or matches its title (the same title-word rule as our earlier studies).
   - **sibling:** a reference with first page "1" to another paper of the same journal-year. That means either a 10.1155 DOI of that year (with a matching journal title, or none), or no DOI but a matching journal title and volume or year equal to the year.
   - **unsupported:** neither, with at least 5 deposited references. **too_few_references:** neither, with fewer.
   - For sibling citers, OpenAlex is asked whether it links the sink and each sibling's own work.

## Hypotheses and thresholds (alpha = 0.01)

- **H1 (sinks are common in the MAG era).** Among scored old journal-years, the share with a sink is at least 0.40, with n >= 30.
- **H2 (they are absent after MAG).** Among scored new journal-years (n >= 30), the share with a sink is at most 0.05, and lower than the old share (one-sided Fisher p < 0.01).
- **H3 (mechanism).** Among the sink citers labelled sibling or unsupported (n >= 40), at least 70% are sibling.
  - *Calibration:* among control citers labelled genuine, sibling or unsupported (n >= 30), at least 70% must be genuine. Otherwise H3 is "untestable (classifier failed calibration)".
- **H4 (added, not swapped).** Among sibling references with DOIs whose citer is in OpenAlex (n >= 20), OpenAlex links the sibling's own work in at least 80%.
- **H5 (era of the citations).** For old journal-years with both a sink and a control (n >= 10 pairs), take the share of OpenAlex citations dated up to 2021 (from OpenAlex's counts by year). The sink's share must exceed its control's more often than not (sign test p < 0.01), and the sinks' median share must be at least 0.90.

Each verdict is "supported", "not supported" or "untestable", exactly as `hindawi_sink.py` computes it.

## Reported, not tested

- Per year: scored journal-years, sinks, total phantom citations (the sum of OpenAlex - Crossref over sinks), journal-years with more than one work over the sink thresholds, and how often the sink is the most cited work.
- The pilot journal-years.
- Every sink's DOI, counts and title in `journal_years.jsonl`, and every read in `reads.jsonl`.

## Known limits, stated in advance

- Only the 25 most-cited works per journal-year are examined. A sink outside them is missed, which biases H1 downwards.
- OpenAlex counts citations from sources other than Crossref deposits (MAG's own parsing), so every work has some excess. The thresholds (E >= 10 and a gap of 50) are meant to be well above that, but they were chosen after seeing two pilot sinks.
- In 2016 counts by year may miss early citations, because OpenAlex only gives the last ten years.
- Hindawi journals moved to Wiley in 2023-2024. OpenAlex source records may have changed, but ISSNs and DOIs did not.
- The study shows where the extra links are and how they look. It cannot show OpenAlex's or MAG's code.
- AI agents designed this study and will run and score it. Pre-registration limits goalpost-moving but is not an independent check.

## Deviations

Any change after data collection will be published as a dated amendment, with its reason, before re-running under a new job version. No one at Hindawi, Wiley, OpenAlex or OurResearch, and no author, has been contacted.
