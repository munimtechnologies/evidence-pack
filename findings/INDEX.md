# Findings index (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research information, not medical advice.

Every note in this folder, grouped by study. Where a study was pre-registered, the pre-registration was committed before its data were collected or scored, and its results note says how each prediction fared. Corrections are published as new notes rather than silent edits.

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

## Data integrity: references and open citation counts

**Start here:** `open-citation-count-errors-2026-10-17.md` compares the four failure modes below and gives a checklist. `doi_hygiene.py` automates most of that checklist. **Correction (2026-10-17):** that note says PMID-keyed tools are immune to stub records. That is wrong for one class: PubMed itself stores some Elsevier DOIs cut at the first hyphen (see `doi-stub-census-v2-results-2026-10-17.md`).

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
- Truncated Elsevier DOIs inside PubMed, pre-registered, **job queued** (code `pubmed_doi_stubs.py`, tests passed): `pubmed-doi-stub-census-prereg-v1-2026-10-17.md`
- Article number 1 outside Springer Nature (MDPI, Frontiers), pre-registered, **job queued**: `article-number-1-prereg-v1-2026-10-17.md`

## Literature retrieval: NLM SPARK Task 1 sample bench

In `../spark/` (see its `README.md`): two dev sets, three pre-registrations and the v3 decision. The citation prior is now gated on a priority cue (0.838 landmark / 0.809 ordinary MRR@5 on the sample). A cross-encoder reranker is pre-registered and **not yet run**: `../spark/prereg-ce-rerank-v1.md`.

No independent human check has been done on any of these yet. If you find an error, please open an issue.
