# Results: CCDI census post-hoc diagnostics, stage 3 (ccdi-diag3-v2)

MV2 of Munim, Inc. Text CC BY 4.0; code Apache-2.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed these results.** This is research information about data quality, not medical advice.

**Everything on this page is POST HOC.** The code (`diag3.py`, published at tag v0.5.11 before this write-up) was written after the stage-2 diagnostics (`../diagnostics-v2/results.md`) had been seen. Nothing here changes a pre-registered grade of the census (`../concordance-v1/`).

- **Run:** sealed job `ccdi-diag3-v2`, 2026-10-23 12:02 to 12:14 UTC, on the machine that holds the kept second snapshot (`snapshot_check.found` true: 153,580 subjects, 153,680 Participant Index entries). Peak memory 0.42 GB. The code it downloaded matched earlier stages byte for byte (`analyze.py` SHA-256 `aa22639f…4fca6`, `fetch_ccdi.py` `479b79ae…ec8214`, `diag.py` `fa24af6b…de3b9`; full values in `out/get-code-log.txt`). The 7 unit tests passed. The 55 requests were made about ten hours after stage 2's (01:55-01:59 UTC).
- **Output (aggregates only):** `out/diagnostics3.json`. Positions and counts, no participant IDs.
- **Run history:** `ccdi-diag3-v1` stopped before any request because it was scheduled on a machine without the kept snapshot (see `README.md`). v2 asked the same questions.

## 1. The failure is one record, not ten or a hundred

`/subject` at one record per page, positions 3,456-3,475 of PCDC's paging order:

| Positions | Result |
|---|---|
| 3,456-3,461 and 3,463-3,475 (19 positions) | 1 record each; every one is a record the kept snapshot lacks |
| **3,462** | PCDC's part of the response is an error object (`{"kind": "NotFound", "message": "Server Error."}`), HTTP status 200 |
| Page 347 at 10 per page (3,461-3,470), repeated | still an error object, as in stage 2 |

- So the record at position 3,462 cannot be served at any page size tried (100, 50, 25, 10, 1). Every page that contains it fails, and the failure persisted for at least ten hours.
- Stage 2 already retrieved positions 3,401-3,460 and 3,471-3,500 at smaller page sizes. With this job, **99 of the 100 PCDC subjects missing from both snapshots are retrievable by position**; one is not. As in stage 2, this assumes PCDC's order is the same across page sizes. The job counted records per request and did not take a union of names.

## 2. `/subject-mapping` drops the same block silently

`/subject-mapping` returns, on each page, up to `per_page` Participant Index entries for each source. Over the same range:

| Page (records) | Page size | PCDC entries | Error or note in the response |
|---|---|---|---|
| 34 (3,301-3,400), control | 100 | 100, all already in the snapshot | none |
| **35 (3,401-3,500)** | 100 | **0** | none |
| 69 (3,401-3,450) | 50 | 50, none in the snapshot | none |
| **70 (3,451-3,500)** | 50 | **0** | none |
| 341-346, 348-350 | 10 | 10 each, none in the snapshot | none |
| **347 (3,461-3,470)** | 10 | **0** | none |
| 3,456-3,461 and 3,463-3,475 | 1 | 1 each, none in the snapshot | none |
| **3,462** | 1 | **0** | none |

- On every page that contains position 3,462, PCDC's entries are simply absent. The other sources on the page return their full counts, the HTTP status is 200, and the only extra key in the body is `"supplementary_domains": []`, the same as on the pages that work. **Unlike `/subject`, `/subject-mapping` gives no error object at all.**
- This explains a number from stage 1: `/subject-mapping` served 153,680 entries against the sources' summary totals of 153,780. The 100 missing entries are PCDC's block on page 35 at 100 per page. At one entry per page, the loss would be a single entry.
- A client that checks for error objects, as stage 2 advised, still cannot see this loss. It can only find it by counting entries per source on every page: a source that returns fewer than `per_page` entries on one page and full pages after it has lost entries.

## What this means for anyone pooling CCDI records

This extends stage 2's advice (point 4):
1. On `/subject`, check every source's part of every page for an error object. Re-request a failing range at smaller page sizes, down to one record, to keep the loss to the records that really fail.
2. On `/subject-mapping`, also count entries per source on every page. A short page in the middle of a source's sequence means entries were dropped without notice.
3. Reconcile the totals against each source's summary count. That is how stage 1 noticed the 100-entry gap.

## Limits

- Post hoc and exploratory. One run of 55 requests on 2026-10-23 around 12:02-12:14 UTC; the server may change.
- "Position" means the place in PCDC's paging order. We did not compare names across page sizes or across the two endpoints, so the claim that the same record fails on both endpoints rests on positions only.
- Is this known? On 2026-10-23 the issue tracker of the Federation API specification (github.com/CBIIT/ccdi-federation-api: 19 issues, all closed) had no issue whose title concerns paging, dropped records or errors returned with HTTP 200. We read titles only, and a node's own tracker may know more.
- We do not know why this record fails. It may be a data problem in one record, or something deliberate. The open tier cannot tell.
- Nobody outside the project has checked the code or the numbers. The open questions are for the resource owners; we have not contacted them.
