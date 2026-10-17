# PubMed "Comment in" census: operational amendment (2026-10-17)

MV2 of Munim, Inc., 2026-10-17. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

This amends `pubmed-commentin-census-prereg-v1-2026-10-17.md` **for operational reasons only**. The population, classes, sampling, seed, hypotheses, thresholds and scoring rules are unchanged.

## What happened

The first run (job `pubmed-commentin-v1`, 2026-10-17 16:37-16:48 UTC, code at commit fc7bed1) passed its offline tests and finished the PubMed searches. Its first bulk record download (E-utilities `efetch`) then failed with `HTTP Error 400: Bad Request`, and the script stopped. The code treated every HTTP 400 as final. It produced no counts, so **no census data were seen**: the run wrote only `provenance.json`.

NCBI is known to return some temporary backend failures as HTTP 400, with the real cause in the response body. For example, see the [pubmed-mcp-server issue #155](https://github.com/cyanheads/pubmed-mcp-server/issues/155), where the body says "Failed to connect to PubOne service". On the same day, an ordinary efetch of two pilot records (a GET request, outside the job) returned normal XML. That points to a temporary failure rather than a fault in the endpoint, though the job's own error body was not captured, so the cause is not proven.

## Changes to `pubmed_commentin.py` (v1.1)

- E-utilities calls (esearch and efetch) now retry an HTTP 400 up to 5 times with growing pauses, as they already did for other errors. The first 300 characters of the error body are kept in the log. Other services are unchanged, and a 404 is still final.
- If a batch of 200 records still fails, it is re-tried in pieces of 20. A piece that still fails is logged in `errors` with its PMIDs and left out, instead of stopping the run. After 10 failed pieces, the remaining batches are logged as skipped without further requests.
- `results.json` gains `records_failed`, `reciprocity_targets_failed` and `void`.
- **Void rule (new, operational):** the run is void if more than 1% of the records to be fetched failed. A void run is re-run unchanged under a new job version, and its counts are not scored.
- New offline tests: `test_pubmed_commentin_retry.py`.

## What this cannot change

Records lost to failures are missing at random with respect to their links: a failed request cannot see what the record contains. Below the 1% void threshold, the loss is reported and the hypotheses are scored as pre-registered.
