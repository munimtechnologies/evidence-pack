# Article 1 in OpenAlex: phantom citations to MDPI and Frontiers article 1 from page-"1" references (summary of four studies, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

This note summarises four studies run on 2026-10-17, each pre-registered before its data were collected. Each has its own results note, code and data in this repository (see `INDEX.md`). It is written so that it can become a short preprint.

## The finding

In OpenAlex, the first article of a 2016-2019 volume of an MDPI or Frontiers journal collects citations that its citers never made. These come from older citing works (up to 2021) that cite a *different* paper of the same volume whose deposited reference gives first page "1". These journals number articles instead of pages, so a first page of "1" is common. OpenAlex keeps the link to the paper actually cited and adds a link to article 1 on top of it.

## The evidence, in order

1. **Crossref is clean** (`article-number-1-v1-results-2026-10-17.md`). Article 1 at MDPI and Frontiers shows no citation inflation in Crossref's own counts (0 of 4 hypotheses supported), unlike the Springer Nature journals studied by Kriváchy (arXiv:2511.01675). One clear exception is a sink: Energies 11:1.
2. **OpenAlex is not** (`article-number-1-openalex-v2-results-2026-10-17.md`). In 74 of 86 volumes from 2016-2019, article 1 has a larger OpenAlex-over-Crossref excess than every same-volume control (about 4 expected by chance). Only 2 of 119 sampled OpenAlex citers of three such records deposit a reference that clearly cites them. The pattern is absent for 2021-2023 volumes. 3 of 4 predictions held.
3. **The mechanism, read backwards** (`article-number-1-mechanism-v1-results-2026-10-17.md`). Of 124 OpenAlex citers that do not really cite article 1, 114 deposit a reference to another paper of the volume with first page "1", against 0 of 178 citers of a same-volume control. In 90 of 90 checkable cases OpenAlex also links the paper actually cited. A hand read of 3 of the 10 exceptions explains one more, a page-"1" reference without a DOI.
4. **The mechanism, tested forwards** (`article-number-1-forward-v2-results-2026-10-17.md`). The citers are random Crossref articles chosen without OpenAlex. For 2019-2021 citers, 13 of 40 citer-volume pairs with a page-"1" reference carry the article-1 link, against 0 of 297 pairs without one (p = 1.3e-13). For 2023-2025 citers it is 0 of 41 (p = 3.2e-5 for the era contrast). Both predictions held.

## What it means for users of OpenAlex citation counts

- The citation count of a 2016-2019 MDPI or Frontiers article 1 in OpenAlex can be well above its Crossref count for this reason alone. Before using it (in a bibliometric study, a ranking, or an evidence map that weights papers by citations), compare it with Crossref's `is-referenced-by-count`, or check its citers.
- For one citing work, `python doi_hygiene.py link <article-1 DOI> <citer's Crossref JSON>` says whether the citer cites article 1 itself, cites a page-"1" sibling instead, or neither.
- The extra links come only from citers published up to 2021. That fits matching on journal, volume and first page done by Microsoft Academic Graph, which stopped at the end of 2021 and from which OpenAlex grew. This is consistent with the data but not proven.

## Why it is new

Kriváchy (arXiv:2511.01675) documented article-number-1 outliers in Springer Nature's online-only journals, where the cause is in how references are written. Searches on 2026-10-17 found no earlier measurement for MDPI or Frontiers in OpenAlex, no description of the page-"1" sibling mechanism, and no forward test of it. The other new elements are the citer-level checks, the same-volume controls and the era contrast.

## Limits

- Only 2016-2019 volumes of 14 MDPI journals and of Frontiers journals were covered. Other article-numbered publishers are untested.
- Exposure in study 4 is defined by references deposited with DOIs. OpenAlex may have read some reference lists from full text.
- The H1 share in study 4 (0.325) only just clears its pre-registered threshold of 0.30. A 95% interval is about 0.20 to 0.48.
- OpenAlex changes; all links are as of 2026-10-17.
- AI agents designed, ran and scored all four studies. Pre-registration limits goalpost-moving but is not an independent check. Errors reported as GitHub issues are welcome.

## Next

The same forward test at other article-numbered journals (PLOS ONE, Scientific Reports, BMC, eLife), pre-registered before it runs.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
