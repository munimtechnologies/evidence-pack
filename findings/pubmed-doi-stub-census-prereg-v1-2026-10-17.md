# Truncated Elsevier DOIs in PubMed: census pre-registration, written before any census data (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Follows `doi-stub-census-v2-results-2026-10-17.md`, where a failed prediction led to this class of error. Code: `pubmed_doi_stubs.py`, with offline tests in `test_pubmed_doi_stubs.py`. The sealed job `pubmed-doi-stubs-v1` will be queued only after this plan is public. Research information about bibliographic data, not medical advice.

## Question
Some PubMed records store a DOI cut at its first hyphen, such as `10.1016/S0197`, while keeping the full Elsevier PII. How many such records are there, when were they made, can their DOIs be repaired from the PII, and what does OpenAlex do with them?

## What we have already seen (hand pilot, 2026-10-17)
This is listed so readers can judge how blind each test is.
- **PubMed counts.** Seven article-identifier searches: `10.1016/S0197` returned 38 records, `S0091` 5, `S0002` 3 and `S1083` 2. `S0140`, `S0196` and `S0022` returned none. That makes 48 records over 4 stems.
- **Dates.** Every record whose date we saw falls in 2003-2005.
- **Repair.** Two DOIs rebuilt from PIIs were looked up in Crossref. Both are registered and both titles match.
- **OpenAlex.** One work (W1984978909) holds 31 distinct PMIDs among its locations. Of four PMIDs looked up with OpenAlex's `ids.pmid` filter, two were not found.

## Method
1. **Stems.**
   - The confirmatory set is all 20,000 bare Elsevier stems: `10.1016/S0000` to `10.1016/S9999` (PII era) and `10.1016/0000` to `10.1016/9999` (older DOIs).
   - Exploratory only: the non-Elsevier stems in `stub_blocklist_v2.csv`.
2. **Screen.** PubMed esearch over POST, 50 stems per search, each written as `"stem"[aid]` and joined with OR. The stems a search matched are read from PubMed's query translation. If that cannot be read, the group's stems minus the "phrases not found" are used. Each candidate stem then gets its own search, keeping up to 10,000 PMIDs.
3. **Verify.** efetch the PMIDs (200 per call) and parse each record's own `ArticleIdList`, never its reference list. A record is **verified** if its DOI ArticleId, or its DOI ELocationID, equals the stem (ignoring case).
4. **Repair (H3).** Take a seeded sample (seed 20261022) of up to 200 verified Elsevier records that have an S-type PII. Rebuild the DOI from the PII (`S0091674903020116` becomes `10.1016/S0091-6749(03)02011-6`) and look it up in Crossref.
   - **Match:** the DOI is registered and at least half (rounded up, minimum 1) of the PubMed title's content words appear in the Crossref title or subtitle. Content words have 4 or more letters, are not on a short stop list, and at most 10 are used.
   - Records whose title has no content words are left out of the denominator.
5. **OpenAlex (H4).** Look up every verified Elsevier PMID with the `ids.pmid` filter, 50 per call, with at most 400 calls. A PMID is **not found** if no returned work carries it as its PMID.
   - Descriptive only: works whose DOI is the bare stem, with their citations, location counts, and whether their title matches the PubMed title of their PMID.
6. **Pace.** NCBI calls are spaced 0.4 s apart, with no API key. Calls that fail are counted and reported.

## Hypotheses and predictions
- **H1 (scale):** at least 300 PubMed records carry a DOI that is exactly a bare Elsevier stem. *Prediction: supported, low confidence.* The pilot found 48 in 4 of 7 stems tried, but those were stems already known to be broken.
- **H2 (one episode):** at least 80% of verified Elsevier records with a publication year fall in 2003-2005. The test needs at least 30 dated records. *Prediction: supported.*
- **H3 (repairable):** at least 90% of the repair sample are matches. The test needs at least 20 testable records. *Prediction: supported.*
- **H4 (lost in OpenAlex):** at least 30% of verified Elsevier PMIDs are not found as any OpenAlex work's PMID. The test needs at least 50 looked-up PMIDs. *Prediction: supported.*

## Outputs
The job writes:
- `results.json`
- `records.jsonl`: every verified record, with its rebuilt DOI and OpenAlex match
- `repair_checks.jsonl`
- `openalex_stub_works.jsonl`
- `stems.csv`: a per-stem count, journals and years

The results note will be published whatever it shows. It will give both timestamps (this commit and the job's run time). Any change after the data are seen will be reported as a deviation. The `--limit` option exists only for debugging. Any output produced with it will be reported as a deviation.

## Limits known in advance
- `[aid]` searches PubMed's article-identifier index. A truncated DOI stored only in some other field would be missed.
- The screen covers Elsevier-style stems only. Other publishers' truncations are explored, not tested.
- A Crossref 404 and a failed Crossref lookup look the same.

No one at NLM, OpenAlex, Crossref or Elsevier has been contacted.
