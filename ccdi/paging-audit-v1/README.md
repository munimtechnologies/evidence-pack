# Pre-registration: a full paging audit of a CCDI Data Federation snapshot

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Status: PRE-REGISTERED.** This page, the code and the predictions below are published at evidence-pack tag **v0.7.0** before the sealed job `ccdi-paging-v1` runs. The job downloads its code from that tag (it waits until the tag is public), so it cannot run code that differs from what is published here. Results will be added as `results.md` in a later tag and graded against the predictions exactly as written.

## Why

Stage 3 of MV2's CCDI diagnostics ([../diagnostics-v3/](../diagnostics-v3/), tag v0.5.12) found that the federation loses records in two ways. On `/subject`, one PCDC record cannot be served, and every page that contains it returns an error object for PCDC. On `/subject-mapping`, the Participant Index endpoint simply leaves out PCDC's entries on the same pages, with HTTP 200 and no error at all. Stage 3 probed only the pages around that record. So far no one has checked every page of both endpoints for losses of either kind.

[LinkCheck 0.2.0](../../linkcheck/) adds a general paging audit (`linkcheck/paging.py`) for endpoints that serve several sources side by side. It counts entries per source on every page and compares each page with what the source's summary total says it should hold. It flags error pages, short pages and over-full pages, counts errors on pages past a source's end separately (nothing is lost there), and reconciles every source's total. This job runs it on every saved page of the kept second snapshot.

## What the job does

1. Downloads `fetch_ccdi.py` from tag v0.5.5, `ensure_snapshot.py` from tag v0.6.0, and LinkCheck plus this folder from tag v0.7.0, unchanged, logging SHA-256 (`get_code.py`).
2. Runs LinkCheck's tests (`test_linkcheck`, `test_paging`) and this folder's `test_ccdi_pages` (made-up data only; every expected number worked out by hand).
3. Uses the kept second snapshot of the CCDI Data Federation (2026-10-22 21:11 to 2026-10-23 00:36 UTC, 1,211 requests, all HTTP 200). If the machine running the job does not hold it, `ensure_snapshot.py` takes a fresh snapshot with the census's own `fetch_ccdi.py` (about 3.5 hours).
4. `ccdi_pages.py` turns the saved pages into per-source entry counts:
   - **`/subject`:** a source's entries on a page are the records in its `data` list. A source whose `data` is not a list has an error on that page.
   - **`/subject-mapping`:** each Participant Index entry goes to the source of the served subject it names, matched the way the census matches it (domain name, case-insensitively, as a source or namespace name, plus the participant ID). An entry whose subject was not served goes to the source named by its domain name. An entry whose domain name matches no source is counted as unmapped.
   - **Totals:** each source's `counts.total` from `/subject/summary`.

   It then audits both endpoints with page size 100 and grades Q1-Q6.
5. Writes `out/paging-audit.json`: grades, both audit reports, and the inputs' counts. Counts, page numbers and source names only; no participant IDs.

## Predictions

Q1-Q4 use what is already known about the second snapshot: the census re-run (`../diagnostics-v1/`) and the per-source page error counts in its `concordance.json`. They are graded only if the job used that snapshot. Q5-Q6 hold for any snapshot.

The page-error counts already published for that snapshot (PCDC 356, StJude 452, Treehouse 471, ccdi-ecDNA 566; 0 for the other three) are exactly what you get if PCDC fails on pages 12 and 35 and four sources answer every page after their last one with an error object. Q2 states this. The census counted those errors and did not tell the two kinds apart.

| | Prediction | Pass if |
|---|---|---|
| Q1 | On `/subject`, the only losses are PCDC's two error pages. | Page size 100; pages 1-599 all present, none failed as a whole; the loss flags are exactly PCDC page 12 (error, 100 expected) and PCDC page 35 (error, 100 expected). No short or over-full page anywhere. |
| Q2 | On `/subject`, every source reconciles, and the other error pages fall past each source's end. | For all seven sources: total as in the summary (CCDI-DCC 59,795; KidsFirst 38,440; PCDC 24,432; StJude 14,681; Treehouse 12,723; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504); served = total, except PCDC 24,232 (200 lost to error pages); errors past the end: PCDC 354, StJude 452, Treehouse 471, ccdi-ecDNA 566, others 0; no page left unjudged; unexplained 0. |
| Q3 | On `/subject-mapping`, the only loss is PCDC's silent short page 35. | Pages 1-599 all present, none failed as a whole; the loss flags are exactly PCDC page 35 (short: 0 entries, 100 expected). No error and no over-full page. |
| Q4 | On `/subject-mapping`, every source reconciles. | For all seven sources: served = total, except PCDC 24,332 (100 lost to the short page); no errors past the end; no page left unjudged; unexplained 0; 0 unmapped entries. |
| Q5 | Every silent loss on `/subject-mapping` sits on a page where `/subject` also lost that source's entries. | Each `/subject-mapping` loss flag has a `/subject` loss flag for the same source and page. (If `/subject-mapping` has no flags, this passes vacuously, and the result says so.) |
| Q6 | The audit explains every lost entry. | On both endpoints, every source with a summary total has unexplained = 0. |

### Where a miss would most likely come from

- **Q1, Q3:** a silent short page that other pages make up for, such as a source serving one record too few on one page and one too many on another. The census's totals could not see that; a page-by-page audit can. A miss here would be a new finding, not a bug.
- **Q2:** a source whose part of a page is missing entirely (no error object, no `data`) after its end. The audit counts that as 0 entries, which is what it should hold, so Q2 would still pass. A source missing from a page *before* its end would be a short page and fail Q1.
- **Q4:** an entry assigned to the wrong source, for example if two sources share a namespace name and a participant ID. Q4 would then show one source over and another under.
- **Q5** is a hypothesis taken from stage 3, where it was seen on one record. On the second snapshot it is expected to pass (PCDC page 35 is an error page on `/subject`). The converse does not hold and is not predicted: `/subject` page 12 failed on a transient error, and `/subject-mapping` page 12 was complete.

A failed prediction is reported as a failure, with the observed values. The tool may then be fixed, but the grade on record stays.

## Related work

Generic pagination checkers exist. One is [pagination-integrity-check](https://github.com/chenhz01/pagination-integrity-check), which reconciles saved page responses for missing or duplicate pages, overlapping IDs and broken cursor chains. LinkCheck's paging audit works per source, for endpoints where one response carries page p of every source. It works out what each source's page should hold from that source's total, and keeps three cases apart: error objects, silent short pages, and errors past a source's end. A short web search on 2026-10-23 found no tool that does this for federated, multi-source endpoints, but the search was short.

## Files

- `ccdi_pages.py`, `test_ccdi_pages.py`: the code the job downloads.
- `get_code.py`, `job.json`: the job's setup (`job.json` shows the job as filed: 1 CPU, 2 GB, network on, up to 6 hours).
