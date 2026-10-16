# DOI stubs, census v2 (PubMed-indexed articles): pre-registration, written before any v2 data (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Follows `doi-stub-census-v1-results-2026-10-16.md`. Code: `stub_census_v2.py`, which reuses `stub_census.py` as published in commit 1e3632b; offline tests: `test_stub_census_v2.py`. Sealed job: `stub-census-v2`. Research information about bibliographic data, not medical advice.

## Why a second census
Census v1 drew its stems from well-cited articles in every field. This one asks the medical question: which stub records sit in the DOI space of PubMed-indexed journals? It also asks where the stub records themselves come from. A hand read of six large stub records after v1 found no PMIDs, MAG ids on five, and repository rather than journal hosting on five. It produces an open **blocklist** (`stub_blocklist.csv`) that literature-search and evidence-synthesis tools can use to drop these records from citation counts.

## Method
- **Sample:** a seeded OpenAlex sample (seed 20261020) of 10,000 works with `indexed_in:pubmed, has_doi:true, type:article, publication_year:2000-2025, cited_by_count:>9`. On 2026-10-16 that filter matched 14,349,660 works.
- **Stems:** the dash and paren stems of each DOI, by the v1 rules (`stubs_of`).
- **Lookup:** every stem, plus the 73 stems known from v1, as an exact OpenAlex DOI, 50 per call. For each record: MAG id present, PMID present, the primary location's source type and name, and citations.
- **Registration:** one Crossref lookup per stem. A 404 is "unregistered". A failed lookup also reads as unregistered, which is a limit.
- **Descriptive only:** the Wiley citer share of the 40 largest new records; the source types of all unregistered records.
- **Budget:** at most 300 keyless OpenAlex calls, with v1's back-off rules.

**Definitions.** A *stub error* is a record whose DOI is a stem that is **not registered** in Crossref; v1 showed that registered stems are mostly journal-level DOIs, a different case. *New* means a stem not among the 73 known before this census.

## Hypotheses and predictions
- **H1 (more medical stubs):** at least 10 unregistered new stems exist as OpenAlex DOIs. *Prediction: supported, with low confidence.* v1 found 25 unregistered new stems from 1,120 stems. This sample is larger and reaches less-cited journals, but the largest stems are already known.
- **H2 (MAG-era origin):** across all unregistered stub records, known and new, at least 60% of the absorbed citations sit on records that carry a MAG id. *Prediction: supported.* **Not blind:** the threshold was set after the six-record hand read, and the known records dominate the citations. To give it a test it has not seen, we will also report H2 on new records alone.
- **H3 (no PubMed footprint):** at most 2 unregistered stub records carry a PMID. *Prediction: supported* (0 of 6 in the hand read). If it holds, tools keyed on PMIDs do not see these counts, and tools keyed on DOIs or OpenAlex ids do.
- **H4 (not hosted by the journal):** among unregistered stub records with at least 50 citations, at least 50% have a primary location that is not a journal source (a missing source counts as not a journal). *Prediction: supported* (5 of 6 in the hand read; same caveat as H2, and also reported for new records alone).

## Outputs
`results.json`, `stub_records_v2.jsonl` and `stub_blocklist.csv`: every stub record found, with its registration, MAG, PMID and hosting fields. The results note (`doi-stub-census-v2-results-<date>.md`) will be published whatever it shows. Any mismatch between this plan and the code, or any change after the data are seen, will be reported there as a deviation. The new-records-only splits for H2 and H4 will be computed from `stub_records_v2.jsonl` and labelled as such.

**Timing.** This plan and the code were written before the job was queued. The plan becomes public when the publish lane commits it at the end of this agent run. If the sealed job finishes before that commit, the results note will say so with both timestamps, as the v1 note does.

No one at OpenAlex, Crossref or any publisher has been contacted.
