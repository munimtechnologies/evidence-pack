# Pre-registration: Unicode dashes in Wiley's deposited reference DOIs, full 2026 census and onset (v2, 2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.

**Status:** written and committed before any v2 data was drawn. The job (`dash-full-v1`, code `dash_full.py` with
`test_dash_full.py`) runs later in a sealed container. Any difference between this plan and the code will be listed as a
deviation in the results.

## Background

`reference-dash-census-v1-results-2026-10-16.md`: in a random sample, 134 of 263 eligible 2026 Wiley articles (51.0%,
44.9-56.9%) deposit reference DOIs with U+2010 in place of the hyphen. None resolve as deposited, 98.7% resolve once
fixed, and OpenAlex links 1 of 134. Ten other publishers showed none. Exploratory: the share rose from 35.5% (Q1) to
75.0% (Q3). A hand extrapolation suggests about a million affected reference DOIs from January to September 2026.

## Design

- **Part A, onset.** For each month from 2023-01 to 2025-12, one Crossref random sample (`sample=100`) of Wiley (member
  311) journal articles with references, published in that month.
- **Part B, full census.** Every Crossref record with `member:311, from-pub-date:2026-01-01, until-pub-date:2026-09-30,
  type:journal-article, has-references:true`, read with cursor paging (500 per page). Crossref's `total-results` at the
  start is the frame. The census is **complete** if at least 95% of that frame is read. The job stops itself after 510
  minutes, and an incomplete census is reported as incomplete.
- **Unit and definitions (as in v1).** Only references with `doi-asserted-by: publisher` count. *Eligible* means the
  article has at least one such DOI containing a hyphen (ASCII or Unicode). *Affected* means at least one of those DOIs
  contains a Unicode dash (U+2010, U+2011, U+2012, U+2013, U+2014, U+2212, U+00AD). Normalising maps each to "-" and
  deletes U+00AD.
- **Part C, resolution.** Seed 20261017. Uniform reservoir samples of 300 Unicode-dash DOIs and 300 ASCII-hyphen DOIs
  (controls) from the census, checked at Crossref `/works/{doi}`, then at doi.org `/api/handles/{doi}`. Lookup errors are
  excluded and counted.

## Hypotheses (predictions written before data)

- **H1, the census share agrees with v1.** The census article share (affected / eligible) falls inside v1's Wilson
  interval, 44.9% to 56.9%. *Prediction: about 50%.* Not testable unless the census is complete.
- **H2, rising within 2026.** The pooled share for July-September 2026 exceeds January-March by at least 15
  percentage points. *Prediction: holds (v1 exploratory: 35.5% vs 75.0%).* Complete census only.
- **H3, onset.** In Part A, the first month (2023-2025, among months with at least 20 eligible articles) with an
  affected share of 20% or more is 2025-01 or later, or there is no such month. *Prediction: holds. This is a guess:
  we have no data before 2026.* Not testable if more than 6 monthly samples fail.
- **H4, scale.** The census contains 700,000 to 1,300,000 Unicode-dash publisher-asserted reference DOIs.
  *Prediction: about 980,000.* Complete census only.
- **H5, repairable.** Of the dash sample, at most 2% resolve as deposited and at least 95% resolve after normalising.
  At least 90% of the ASCII controls resolve.

## Descriptive outputs (no predictions)

- Census counts by month and by journal (every journal with at least 20 eligible articles; all journals in
  `journals.tsv`).
- Cited DOI prefixes of the dash DOIs, which show whose papers lose the citations.
- Which dash characters occur.
- **An open repair list** (`repairs.tsv.gz`): one row per affected reference, giving the citing DOI, the deposited
  DOI and the normalised DOI. Plus `affected_articles.tsv.gz`. Both are CC BY 4.0.

## What would change the reading

- If H1 fails low, v1's sample overstated the rate; the extrapolation will be corrected in the open.
- If H3 fails, the pattern is older than 2025, so many more past citations are affected; the onset month is reported.
- If H5 fails because dash DOIs now resolve, Wiley or Crossref has started fixing them; this would be reported as good news.

## Reporting and contact

Results will be published whatever they show, as `reference-dash-full-census-v2-results-<date>.md`, with the code. No
publisher, Crossref, OpenAlex or OpenCitations staff will be contacted unless Sheehan approves it.
