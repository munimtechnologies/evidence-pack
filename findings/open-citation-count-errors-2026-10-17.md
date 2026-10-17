# Where open citation counts go wrong: journal swaps, article number 1, DOI stubs and Unicode hyphens (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

This note brings together six studies published in this repository on 2026-10-16. Each one has its own pre-registration (or says plainly that it had none), code, sealed-job outputs and limits. Nothing here is new data. The numbers are copied from those notes, and each section names the note it comes from. What is new is the comparison: four separate ways that the open citation graph (Crossref deposits, OpenCitations, OpenAlex) credits citations to the wrong work or drops them, how big each one is, and how a user of citation counts can guard against each.

**Why it matters for medicine.** Systematic reviewers chase citations forwards and backwards. Evidence maps, "most-cited" lists and literature-ranking tools use citation counts as priors. Several of the largest errors below sit on The Lancet's and BMJ's DOIs.

## The four failure modes at a glance

| | What happens | Size found (snapshot 2026-10-16) | Where it starts | Visible from one record? |
|---|---|---|---|---|
| **1. Unicode hyphens** | Reference DOIs deposited with U+2010 in place of "-" do not resolve, so those citations are lost | 134 of 300 sampled 2026 Wiley articles (44.7%); none at the 8 other publishers that could be tested. Hand extrapolation (not pre-registered): ~103,000 articles and on the order of a million reference DOIs in Jan-Sep 2026 | Publisher deposits (Wiley) | Yes: the DOI contains a non-ASCII dash |
| **2. DOI stubs** | An OpenAlex record whose own DOI is a bare journal stem (`10.1016/s0140`, `10.1136/bmjopen`) collects every reference truncated the same way | 73 stems on 74 records hold 63,194 citations; 33 unregistered stems hold 56,438 | Truncated DOIs: U+2010 cut-offs, stems deposited by publishers, repository/MAG records | Yes: the DOI ends where a journal's DOIs continue |
| **3. Article number 1** | References written "Sci Rep 9:1-17" are matched to the volume's article 1 | Sci Rep 9:1 has 8,494 OpenAlex citations, 0 genuine of 18 judged; Nat Commun 9:1 has 7,417, 0 of 10 | Matching by volume and first page | Partly: article 1 with no page range |
| **4. Journal swaps (citation sinks)** | Another work's reference carries the sink's journal, volume and page, or its DOI | Bunney 2017: 2,067 OpenAlex citers, 83.2% off-topic; 24 of 174 readable deposited references genuine (13.8%) | Deposited metadata (publisher 119 and Crossref 42 of 213 DOI assertions) plus a smaller OpenAlex layer | No: needs the citers' reference lists |

## 1. Unicode hyphens in deposited reference DOIs

Sources: `phantom-refs-dash-dois-2026-10-16.md`, `reference-dash-census-v1-results-2026-10-16.md` (pre-registered; commit 450258f before any census data).
- First seen in 11 meta-analyses (10 published by Wiley): 131 publisher-deposited DOIs with U+2010, none resolving as deposited, and 129 resolving once the one character is fixed.
- Random census of 2026 articles: Wiley 134 of 263 eligible (51.0%, Wilson 44.9-56.9%) had at least one U+2010 DOI. Springer Nature, Taylor & Francis, SAGE, OUP, Wolters Kluwer, Frontiers, BMJ and Cambridge had none. Elsevier and MDPI could not be tested because Crossref, not the publisher, supplies their reference DOIs.
- As deposited, 0 of 150 resolve; normalised, 148 of 150. OpenAlex links 1 of 134 such citations it could check, against 212 of 214 ASCII controls.
- Within Wiley the share rose through 2026 (Q1 35.5%, Q3 75.0%; exploratory, not pre-specified).

## 2. DOI stubs

Sources: `citation-sink-census-v1-results-2026-10-16.md` (where the first one turned up), `doi-stub-census-v1-results-2026-10-16.md` (pre-registered; H1 and H2 supported, H3 not supported).
- **Two kinds.** 33 stems are not registered DOIs at all: these are errors, a real item (often an unrelated one) carrying a truncated DOI. 27 are registered journal-level DOIs (many of Emerald's, `10.1530/eje`, three BMJ stems). OpenAlex holds these as journal-title "paratext" records, and most citations to them are meant for one of the journal's articles.
- **Medicine is hit hardest through The Lancet.** Its five stub records hold 36,359 citations. The largest, `10.1016/s0140` (W3120106258), is titled as a 2008 "Authors' reply" and has 22,520 citations. BMJ's six hold 3,921, including `10.1136/bmjopen` with 2,230, 1,940 of them from 2024-25.
- **Three routes in.** (a) A DOI pattern stops at Wiley's U+2010: 165 of 190 readable Wiley citers of dash stubs carry the cited DOI with U+2010 (86.8%). (b) Publishers deposit the stem itself: in 79 reads, the citer's own deposit already held the bare stem, 34 of them from Springer Nature-family deposits. In one hand-checked Springer deposit, the reference text gives `10.1016/S1470-2045(19)30456-5`, but the DOI field holds `10.1016/S1470-2045`, cut at "(". (c) Crossref's own matcher, rarely: 4 reads, all to registered journal-level DOIs.
- **Where the records come from (inference from six hand-checked records, not a test).** None carries a PMID, five of six carry a Microsoft Academic Graph id, and five of six sit in an institutional repository rather than at the journal. Census v2, pre-registered over PubMed-indexed articles, tests this. It has not returned yet.
- **PMID-keyed tools are immune.** These records have no PMID, so tools that count citations by PubMed ID do not see the inflated counts. Tools that rank by OpenAlex record or by DOI do.

## 3. Article number 1

Source: `citation-sink-census-v1-results-2026-10-16.md` (pre-registered screen).
- The screen found two sinks it was not designed for: Scientific Reports 9:1 and Nature Communications 9:1. In both, deposited references such as `Sci Rep 9:1-17` were given the article-1 DOI by the publisher or by Crossref.
- **This is a rediscovery.** T. Kriváchy described the mechanism for Springer Nature's online-only journals (arXiv:2511.01675, November 2025). We found that paper only after our job ran. What we add: the same sinks are inflated in OpenAlex by about as much as in Crossref, and Int J Mol Sci 20(1):1 (MDPI, 1,093 citations), a near miss outside Kriváchy's publisher family, is an open lead. It has not been tested.

## 4. Journal swaps: the Bunney sink

Sources: `citation-sink-bunney-v1-results-2026-10-16.md`, `citation-sink-bunney-v2-results-2026-10-16.md` (pre-registered; H1, H2 and H5 supported).
- Bunney et al., Physiol Behav 2017;176:139-148 (a mouse study of orexin and activity thermogenesis): Crossref 1,191, OpenCitations 1,525 and OpenAlex 2,067 citations. Of a same-lab control paper's 70 OpenAlex citers, 7.1% are off-topic. Of Bunney's, 83.2% are.
- Of 150 misdirected deposited references, 95 are journal swaps ("Physiol Behav 176:139" on another work's reference) and 55 carry Bunney's DOI on otherwise different metadata.
- A screen over 4,000 random well-cited works found 1 more sink (0.025%, Wilson 0.004-0.14%), and that one was the `10.1136/bmjopen` stub. Sinks of the Bunney kind look rare. When one exists, it is large.

## What a user of open citation counts can do today

1. **Normalise dashes before matching DOIs.** Map U+2010-U+2015, U+2212, U+FE63 and U+FF0D to "-", and drop the soft hyphen. Use a DOI pattern that runs to whitespace, not one that stops at the first non-ASCII character.
2. **Reject DOIs that stop where a journal's DOIs continue**: before "-" or "(", or at shapes such as `j.NNNN`, `sNNNN`, `sNNNN-NNNN`, `sNNNNN`, `NNNN-NNNN` and `978`.
3. **Drop the known stub records.** `stub_blocklist_v1.csv` lists all 74, with OpenAlex ids, citation counts and Crossref registration.
4. **Distrust journal-title ("paratext") records and article-1 records with large counts.**
5. **For a single paper whose count matters, read the citers.** No single record shows a journal-swap sink. `sink_check_v2.py` reads the citers' deposited references.

`doi_hygiene.py` (Apache-2.0, standard library) does steps 1-4. It runs on a list of DOIs (`check`), on free text such as reference lists (`scan`), or on OpenAlex work records (`records`, one JSON object per line). Its flags are heuristics, meaning "check this before counting it". Its offline tests (`test_doi_hygiene.py`) include the cases above.

## Limits

- Every number is from one snapshot (2026-10-16). Publishers re-deposit references and OpenAlex rebuilds, so counts will change.
- Mechanism 1's million-link scale is a hand extrapolation, not a measurement. The pre-registered full census (prereg v2 in this repo) has not run yet.
- The stub census samples by article, so 73 stems is a floor. The record-origin picture rests on six records.
- The stub shapes in `doi_hygiene.py` came from the stems we found. A real DOI can, rarely, have one of those shapes, and stubs of other shapes (`10.1007/jhep03`) are caught only by the blocklist.
- AI agents designed, ran and scored all of this. Pre-registration guards against moving the goalposts. It does not replace independent human checking, and none has been done yet.

## Prior art

Cioffi et al. 2022 (Scientometrics 127:3593; arXiv:2111.11263) classify invalid DOIs in Crossref reference deposits and how to clean them. Their rules have no case for Unicode dashes. Besançon et al. 2024 (JASIST, doi 10.1002/asi.24896) document sneaked and lost references in deposited metadata. Kriváchy 2025 (arXiv:2511.01675) covers article number 1. A 2025 review of OpenAlex (arXiv:2512.16434) reports inflated counts from duplicate versions, a different cause. Searches on 2026-10-16 found no earlier report of U+2010 in deposited reference DOIs, of OpenAlex records whose DOI is a journal stem, or of a single-paper journal-swap sink at Bunney's scale. If you know of one, please open an issue and we will cite it.

No one at a publisher, Crossref, OpenAlex or OpenCitations, and no author, has been contacted. This public note is the report.
