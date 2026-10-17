# Findings index (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research information, not medical advice.

This index lists every note in this folder, grouped by study. Each pre-registration was committed before its data were collected or scored, and its results note says how each prediction fared. Corrections are published as new notes, not silent edits.

## Drug-repurposing evidence (NCATS ReGen challenge work)

**Triage**
- `triage-2026-10-14.md`: first triage of 13 drug-condition pairs.

**Alcohol use disorder: pools of results posted on ClinicalTrials.gov**
- Topiramate:
  - `topiramate-aud-registry-pool-2026-10-14.md`
  - `topiramate-aud-pool-output-2026-10-14.md`
  - `topiramate-aud-pool-verify-2026-10-14.md`
- Gabapentin:
  - `gabapentin-aud-registry-pool-2026-10-14.md`
  - `gabapentin-aud-pool-output-2026-10-14.md`
  - `gabapentin-aud-pool-verify-2026-10-14.md`
  - correction: `gabapentin-aud-correction-2026-10-16.md`
- Naltrexone:
  - `naltrexone-prereg-2026-10-15.md`
  - `naltrexone-aud-registry-pool-2026-10-15.md`
- General vs comorbid samples:
  - `aud-comorbidity-prereg-2-2026-10-15.md`
  - `aud-comorbidity-prereg-2-results-2026-10-15.md`
- Prazosin/doxazosin:
  - `alpha1-blocker-aud-prereg-4-2026-10-15.md`
  - `alpha1-blocker-aud-prereg-4-results-2026-10-15.md`
- Treatment windows:
  - `registry-pools-treatment-window-audit-2026-10-16.md`
  - `registry-window-confirmation-2026-10-16.md`

**Spironolactone and drinking (NHANES)**
- `spironolactone-nhanes-prereg-2026-10-15.md`
- `spironolactone-nhanes-results-2026-10-15.md`
- `spironolactone-nhanes-followup-prereg-2026-10-15.md`
- `spironolactone-nhanes-followup-results-2026-10-16.md`

**Real-world-evidence rechecks**
- `rwe-recheck-regen-packages-2026-10-15.md`
- TriNetX:
  - `trinetx-consistency-prereg-6-2026-10-15.md`
  - `trinetx-consistency-selection-log-2026-10-15.md`
  - `trinetx-consistency-prereg-6-results-2026-10-15.md`

**Metformin for knee osteoarthritis**
- `metformin-knee-oa-evidence-audit-2026-10-15.md`
- `metformin-knee-oa-oral-rct-pool-2026-10-15.md`

**Terazosin and Alzheimer's disease**
- `terazosin-ad-rwe-consistency-2026-10-15.md`
- `terazosin-fung2024-vs-finasteride-2026-10-15.md`

**Other**
- `faers-alpha1-falls-75plus-2026-10-15.md`
- `topiramate-bipolar-trials-2026-10-15.md`

**Reference integrity of the packages**
- `integrity-check-v1-2026-10-17.md` (see "Integrity module" below): on 2026-10-17 all 24 reference DOIs of packages 4 and 5 were clear in Crossref (Retraction Watch) and PubMed; 2 small-journal DOIs are not in PubMed.

## Evidence synthesis: screening benchmark (AHRQ challenge work)

- Reproducible screening baseline on CLEF TAR 2018 (30 Cochrane diagnostic-test-accuracy reviews): `clef-tar-2018-bm25-prereg-v1-2026-10-17.md` (code `tar_bench.py`), pre-registered and **not yet run**. It ranks each review's search results by BM25 over PubMed title + abstract and scores them with the formulas of CLEF's own evaluator. H1 asks whether it reproduces a published BM25 baseline (Wang et al. 2023: MAP 0.154, WSS@95 0.361). H2 asks whether adding the review title and expanding truncated query words beats it in at least 20 of 30 reviews. It also counts records that PubMed now marks as retracted (exploratory).
- **Exposure, labor and tuning log:** `benchmark-exposure-and-tuning-log.md`. An append-only record, kept as the work happens, of what benchmark material was looked at, what was changed or tuned, and what human labor went into this benchmark work (none so far). AHRQ's challenge rules ask for contemporaneous logs of this kind.
- **Integrity module:** `integrity-check-v1-2026-10-17.md` (code `integrity_check.py`, offline tests `test_integrity_check.py`). One command over PMIDs and DOIs that reports, as of the day it runs, whether each record is retracted, under an expression of concern or corrected according to PubMed and to Crossref (which carries Retraction Watch notices), which source said so, and the `doi_hygiene` flags of its DOI. `--fail-on` makes it a gate. The note records what both APIs return today, the prior art (several Crossref-based checkers exist; the hygiene flags and the two-source report are the additions), and the hand pilot on the ReGen packages. Not yet run on live data in the sandbox.

## Data integrity: ClinicalTrials.gov results

- Census of impossible statistics:
  - `ctgov-impossible-statistics-census-2026-10-15.md`
  - `ctgov-census-v04-triage-2026-10-16.md`
  - `ctgov-census-v05-2026-10-16.md`
  - `ctgov-census-v06-prediction-2026-10-16.md`
  - `ctgov-census-v06-results-2026-10-16.md`
- Standard errors reported as standard deviations:
  - `ctgov-se-tier-triage-2026-10-16.md`
  - `ctgov-se-tier-case-NCT02037126-2026-10-16.md`

## Data integrity: PubMed comment links

- "Comment in" links that are not comments: `pubmed-commentin-census-prereg-v1-2026-10-17.md` (code `pubmed_commentin.py`). In a pilot of all 76 JAMA randomized trials dated 2025, 14 records carry 30 "Comment in" links that are bare DOIs with no PMID. They point to related JAMA Network articles, 26 of 27 of them published before the record. All 57 links that carry a PMID point to items dated the same day or later. A census of 13 JAMA Network journals against 4 control journals (2016-2026, pilot records held out) is pre-registered and **not yet run**.
  - Operational amendment: `pubmed-commentin-census-prereg-v1-amendment-2026-10-17.md`. The first run stopped on an NCBI "HTTP 400" before any record was counted, so no data were seen. The code now retries such errors, logs any records it still cannot fetch, and voids a run that loses more than 1% of them. The analysis is unchanged.

## Data integrity: references and open citation counts

**Start here:** `open-citation-count-errors-2026-10-17.md` compares the four failure modes below and gives a checklist. `doi_hygiene.py` automates most of that checklist, and `integrity_check.py` runs it together with a retraction check over a whole reference list (see "Integrity module" above). **Correction (2026-10-17):** that note says PMID-keyed tools are immune to stub records. That is wrong for one class: PubMed itself stores some Elsevier DOIs cut at the first hyphen. The census of them is now scored (see below). **Addition (2026-10-17):** article-number-1 inflation also exists inside OpenAlex for MDPI and Frontiers, even though Crossref is clean there (see below). `doi_hygiene.py link` checks a single OpenAlex link of that kind.

- Phantom included studies and references:
  - `phantom-included-studies-prereg-v1-2026-10-16.md`
  - `phantom-included-studies-v1-results-2026-10-16.md`
  - `phantom-refs-manual-read1-2026-10-16.md`
  - `phantom-refs-manual-read2-2026-10-16.md`
- Unicode hyphens in reference DOIs:
  - `phantom-refs-dash-dois-2026-10-16.md`
  - `reference-dash-census-prereg-v1-2026-10-16.md`
  - `reference-dash-census-v1-results-2026-10-16.md`
  - full census, pre-registered and **not yet run**: `reference-dash-full-census-prereg-v2-2026-10-16.md`
- Citation sinks:
  - `citation-sink-prereg-v1-2026-10-16.md`
  - `citation-sink-bunney-v1-results-2026-10-16.md`
  - `citation-sink-prereg-v2-2026-10-16.md`
  - `citation-sink-bunney-v2-results-2026-10-16.md`
  - `citation-sink-census-prereg-v1-2026-10-16.md`
  - `citation-sink-census-v1-results-2026-10-16.md`
- DOI stubs:
  - `doi-stub-census-prereg-v1-2026-10-16.md`
  - `doi-stub-census-v1-results-2026-10-16.md`
  - `doi-stub-census-prereg-v2-2026-10-16.md`
  - `doi-stub-census-v2-results-2026-10-17.md` (with the open blocklist `stub_blocklist_v2.csv`)
- Truncated Elsevier DOIs inside PubMed:
  - `pubmed-doi-stub-census-prereg-v1-2026-10-17.md`
  - `pubmed-doi-stub-census-v1-results-2026-10-17.md`: 69 records over 8 stems, all from 2003-2005. 2 of 4 predictions held. The data are in `pubmed_doi_stubs_v1_*` at the repository root, and `pubmed_doi_stubs_v1_records.jsonl` is the open repair table.
- Article number 1 outside Springer Nature (MDPI, Frontiers):
  - **Summary of the four studies below:** `article-number-1-openalex-summary-2026-10-17.md`
  - `article-number-1-prereg-v1-2026-10-17.md`
  - `article-number-1-v1-results-2026-10-17.md`: no article-1 inflation in Crossref at either publisher (0 of 4 hypotheses supported), but one clear sink (Energies 11:1). The data are in `article1_check_v1_results.json` and `article1_check_v1_reads.jsonl`. The full per-article file is over 2 MB and is rebuilt by `rebuild_units.py`.
  - OpenAlex follow-up: `article-number-1-openalex-prereg-v2-2026-10-17.md`, its amendment `article-number-1-openalex-prereg-v2-amendment-2026-10-17.md`, and **results** `article-number-1-openalex-v2-results-2026-10-17.md`. In 74 of 86 volumes from 2016-2019, article 1 has the largest OpenAlex excess of its volume (about 4 expected), and only 2 of 119 sampled OpenAlex citers of three such records clearly cite them. The pattern is absent for 2021-2023. 3 of 4 predictions held. Data in `article1_openalex_v2_*`.
  - Mechanism: `article-number-1-mechanism-prereg-v1-2026-10-17.md` (code `article1_mechanism.py`) and **results** `article-number-1-mechanism-v1-results-2026-10-17.md`. 114 of 124 OpenAlex citers that do not really cite article 1 deposit a reference to another paper in the volume with first page "1", against 0 of 178 citers of a same-volume control. OpenAlex keeps the correct link in 90 of 90 cases and adds article 1 on top. All 124 were published in 2021 or earlier (post hoc). 2 of 3 hypotheses held; the forward test was untestable. Data in `article1_mechanism_v1_*`.
  - Exceptions, read by hand (post hoc): `article-number-1-mechanism-v1-exceptions-2026-10-17.md`. Of the 10 citers the mechanism did not explain, we read 3. One has the same page-"1" reference without a DOI ("Materials, vol. 10, p. 1"). One has its only DOI-less reference linked to article 1 for no visible reason. In one, OpenAlex lists 6 links that neither Crossref nor Europe PMC has. So 115 of 124 are explained by a page-"1" reference.
  - Forward test: `article-number-1-forward-prereg-v2-2026-10-17.md` (code `article1_forward.py`) and **results** `article-number-1-forward-v2-results-2026-10-17.md`. The citers are random Crossref articles chosen without OpenAlex. For 2019-2021 citers, 13 of 40 citer-volume pairs with a DOI reference of first page "1" into a 2016-2019 MDPI or Frontiers volume carry an OpenAlex link to that volume's article 1, against 0 of 297 pairs without one. For 2023-2025 citers it is 0 of 41. Both hypotheses held (p = 1.3e-13 and 3.2e-5). Data in `article1_forward_v2_*`.
- Hindawi journal-year sinks in OpenAlex (the same page-"1" matching, where every article starts at page 1):
  - `hindawi-sink-prereg-v1-2026-10-17.md` (code `hindawi_sink.py`), pre-registered and **not yet run**. In a pilot, one record per journal-year stood out: BioMed Research International 2017 (10.1155/2017/6353510) has 1,178 OpenAlex citations against 8 in Crossref, almost all dated 2017-2021. Oxidative Medicine and Cellular Longevity 2018 (10.1155/2018/5879281) has 363 against 10. Two hand-read citers of the first each cite a different BMRI 2017 paper with first page "1". The census covers Hindawi journal-years 2016-2019, with 2022-2023 as a negative control; the pilot journal-years are held out.
  - Beyond Hindawi: `page1-sink-prereg-v1-2026-10-17.md` (code `page1_sink.py`), pre-registered and **not yet run**. Many other journals (IEEE, SPIE, ACM, ASCO and others) also give every article pages 1-N in one volume a year. The census asks whether they have sinks too, with the same sink rule, the same 2022-2023 control and the same mechanism reads. No non-Hindawi citation count was looked at first, so there is no pilot.

## Literature retrieval: NLM SPARK Task 1 sample bench

In `../spark/` (see its `README.md`): three dev sets, five pre-registrations and their results. The citation prior is gated on a priority cue (0.838 landmark / 0.809 ordinary MRR@5 on the sample). The MedCPT cross-encoder test (`../spark/ce-rerank-v1-results-2026-10-17.md`) kept that ranking: no candidate passed the rule. A held-out test of an idea found afterwards (`../spark/ce-switch-v1-results-2026-10-17.md`) did **not replicate**: on 28 new ordinary questions the cross-encoder beat the gated ranking by +0.030 MRR@5 (0.958 against 0.929), below the pre-registered +0.05, so the gated ranking stays.

No independent human check has been done on any of these yet. If you find an error, please open an issue.
