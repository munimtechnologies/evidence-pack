# Results: CCDI census post-hoc diagnostics v1 (ccdi-diag-v1)

MV2 of Munim, Inc. Text CC BY 4.0; code Apache-2.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed these results.** This is research information about data quality, not medical advice.

**Everything on this page is POST HOC.** The diagnostic code was written after the pre-registered census results (`../concordance-v1/results.md`, tag v0.5.6) had been seen. Nothing here changes a pre-registered grade.

- **Run:** sealed job `ccdi-diag-v1`, 2026-10-22 21:11 to 2026-10-23 00:36 UTC.
  - Census code downloaded unchanged from tag v0.5.5: `analyze.py` (20,808 bytes, SHA-256 `aa22639f75436c099c339191d5b92ee2b3e2f3a79a8ed6273b6693044ba4fca6`) and `fetch_ccdi.py` (7,364 bytes, SHA-256 `479b79aecbeaa9481e1fb16bed26b8fde47edcde671ecdd0dca8bdc075ec8214`).
  - The 5 diagnostic unit tests passed.
  - Second snapshot: 1,211 requests, all HTTP 200, the same request plan as the census. The first snapshot was taken 14:29-18:03 UTC the same day.
- **Outputs (aggregates only):**
  - `out/diagnostics.json`
  - `out/snapshot2/concordance.json`: the census analysis re-run unchanged on the second snapshot
  - `out/snapshot2/fetch-log.json`: URL, status, size and SHA-256 of every response

## 1. The second snapshot reproduces the census

All seven grades are the same as in the census (H1-H4, H6 and H7 pass; H5 fails), with the same counts. Section C of `concordance.json` is identical apart from one new line (see 2). That covers all 20,496 Participant Index pairs, every source-pair table and every link-resolution count.

| | Census | Snapshot 2 |
|---|---|---|
| Records served | 153,680 | 153,580 |
| PCDC records served (summary total 24,432) | 24,332 | 24,232 |
| Every other source | same | same (59,795 / 38,440 / 14,681 / 12,723 / 3,205 / 504) |
| Linked persons; naive over-count | 14,847; 17,731 | 14,847; 17,731 |
| De-duplicated total | 135,949 | 135,849 |
| GDC TARGET: cases / distinct USIs / USIs linked | 6,543 / 5,876 / 5,731 | same |

The only difference is 100 more PCDC records lost to a failed page (next section).

## 2. One PCDC page fails every time

On `/subject?page=35&per_page=100`, the PCDC part of the response is an error object, not a record list. The whole response is **byte-identical in both snapshots** (473,425 bytes, SHA-256 `2c32015b…a395cd`), taken about seven hours apart. A retry in snapshot 2 failed again with `{"kind": "NotFound", "message": "Server Error."}`. Every other source on that page returned its records.

Page 12 also failed in snapshot 2 (`ServerConnection`, "We are having issue connecting to the main server"). One retry returned all 100 records, so that failure was transient. In the census, page 12 was fine (679,407 bytes) and page 35 was the failed page.

`/subject-mapping` served 153,680 entries in both snapshots: 100 fewer than the sources' summary totals (153,780). Its page 35 is also byte-identical across snapshots. In snapshot 2, exactly 100 mapping entries point to a subject that was not served: page 12's PCDC records. **Our inference, not yet tested:** the same 100 PCDC subjects (records 3,401-3,500 in PCDC's paging order) are missing from both endpoints in both snapshots. Follow-up job `ccdi-diag2-v1` re-requests that range at smaller page sizes.

## 3. ccdi-ecDNA ages run earlier than both other sources

Age differences in days between linked records. The sign is ecDNA (or KidsFirst) minus CCDI-DCC.

| Pair, vital status (first / second) | n | Median | Second source younger by more than 1 day | Within 1 day |
|---|---|---|---|---|
| CCDI-DCC / ccdi-ecDNA, all | 1,117 | −780 | 1,059 | 1 |
| … Alive / Alive | 934 | −1,048 | 920 | 0 |
| … Alive / Dead | 145 | −160 | 106 | 1 |
| … Dead / Dead | 10 | −334 (range −770 to −37) | 10 | 0 |
| KidsFirst / ccdi-ecDNA, all | 15 | −489 | 14 | 1 |
| CCDI-DCC / KidsFirst, Dead / Dead | 195 | 0 | 2 | 190 |

- **CCDI-DCC and KidsFirst agree with each other** on age at death: 190 of 195 pairs fall within a day.
- **ccdi-ecDNA reports a smaller age for the same children** against both of them. That includes every one of the 10 deaths it shares with CCDI-DCC.
- So ccdi-ecDNA's `age_at_vital_status` seems to refer to a different, earlier time point. We cannot tell which one from the open tier.
- **Consequence for the census:** its 106 "alive after death" labels, all in this pair, compare ages with different reference points. They should not be read as contradictions.
- **The Alive-versus-Dead disagreement itself does not depend on ages, and it runs one way.** In all 145 pairs, CCDI-DCC says Alive and ccdi-ecDNA says Dead. In the 4 CCDI-DCC / KidsFirst conflicts, CCDI-DCC says Dead and KidsFirst says Alive.

## 4. Sex disagreements center on one study

The same 7 linked pairs disagree on sex as in the census.
- **6 of the 7 involve one study**, namespace `sd-fycr78w0`. The federation's `/namespace` endpoint names it "INCLUDE: (Lupo) Genomic Analysis of Congenital Heart Defects and Acute Lymphoblastic Leukemia in Children with Down Syndrome". Its short title is DS-COG-ALL, and its organization is include-dcc, hosted on the Kids First FHIR server.
  - 4 of the 6 are against St. Jude PanALL;
  - 2 are against TARGET ALL Expansion Phase 2 (dbGaP phs000464, served by CCDI-DCC).
- **The seventh** is TARGET Wilms tumor (phs000471, CCDI-DCC) against Treehouse.
- **Both directions occur** (M versus F and F versus M), so it is not one value coded the wrong way.
- From open-tier data we cannot tell whether the link, a record, or the way sex was determined is at fault.
- **Correction of emphasis:** the census attributed 4 of these to the "KidsFirst" source. The records come from an INCLUDE study that the KidsFirst federation node serves.

## 5. Participant Index links that do not resolve

| Target source | Unresolved links | Shape of the linked IDs | Shape of served names | A looser match resolves |
|---|---|---|---|---|
| PCDC | 3,734 | `A{3}_A{6}` 2,614; `A{3}_A{4}9{4}_A{6}` 960; `A{3}_A{4}9{2}A9_A{6}` 160 | `A{6}` (all 24,232) | none of the four tests |
| KidsFirst | 1,364 | the same shapes as served names | 15+ shapes like `a{2}-a{8}` | none |
| Treehouse | 1,206 | `A{3}9{2}_9{4}` (all) | other shapes | 1,097 (91.0%) equal a served subject's alternate identifier |
| ccdi-ecDNA | 148 | `A{2}9{6}` (all) | `A{2}9{6}` and others | none served by ccdi-ecDNA; all 148 are names that some other source serves |

Shapes reduce each character to `A` (capital letter), `a` (lower case) or `9` (digit), with run lengths.

The four tests were: case-insensitive name, alphanumeric-only name, an alternate identifier in the target source, and the name in any source.

- **PCDC:** every unresolved link is an underscore-joined ID that ends in six capital letters, which is the shape of the COG USI. PCDC serves bare six-letter names.
  - The `/namespace` endpoint lists 30+ PCDC namespaces named after COG protocols (for example ACCL1633). One more is named "COG" and has null metadata.
  - Every served PCDC subject sits in the "COG" namespace.
  - The likely reading, untested: the Index stores PCDC IDs as program and protocol prefixes plus the USI, and the federation serves the USI alone. `ccdi-diag2-v1` tests matching on the part after the last underscore.
- **Treehouse:** most unresolved links use an identifier that Treehouse serves as an alternate identifier, not as the subject name.
- **ccdi-ecDNA:** the 148 links name records served by another source. `ccdi-diag2-v1` reports which source, and whether the "link" points back to the linking record itself.

These looser matches are diagnostics, not corrections. A loose rule can also join the wrong records, so `ccdi-diag2-v1` reports sex agreement for every pair a loose rule creates.

## 6. Missing sex and vital status by study namespace

- **StJude:** 1,325 of 14,681 served records have no sex, all in three namespaces: SJLIFE 500 of 4,675, PCGP 421 of 1,901, ClinicalGenomics 404 of 3,576. None of the seven StJude namespaces serves a vital status.
- **PCDC:** 315 of 24,232 have no sex (one namespace, "COG"), and none has a vital status.
- **KidsFirst:** one record has no sex. Vital status is missing in most namespaces: for example 7,633 of 7,706 in the largest.
- **CCDI-DCC** (40 namespaces): no record lacks sex. Vital status is complete in the largest namespace (phs001327, 30,717 records) but missing for 5,382 of 7,023 in phs002790 and for all 1,287 in phs001228.

## Limits
- Everything here is post hoc and exploratory. Shapes and loose-match counts describe identifiers; they do not show which records are the same person.
- Open tier only. Some gaps may be deliberate access-tier or modelling choices.
- The study names come from the federation's `/namespace` endpoint (read 2026-10-23). The dbGaP study names for phs000464 and phs000471 come from the dbGaP TARGET data use certification.
- Nobody outside the project has checked the code or the numbers yet. The open questions (PCDC link format, ecDNA age reference, the failing page) are for the resource owners; we have not contacted them.
