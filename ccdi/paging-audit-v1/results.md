# Results: a full paging audit of a CCDI Data Federation snapshot

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Grades of record: all six predictions held (Q1-Q6 pass).** The predictions are in [README.md](README.md), published at evidence-pack tag v0.7.0 before the job ran, and are graded here exactly as written.

## The run

- Sealed job `ccdi-paging-v1`: 1 CPU, 2 GB, network on. It ran on the Blade, 2026-10-23 18:48-18:50 UTC.
- `get_code.py` downloaded `fetch_ccdi.py` (tag v0.5.5), `ensure_snapshot.py` (tag v0.6.0), and LinkCheck 0.2.0 plus this folder (tag v0.7.0). All 12 files were unchanged, and their SHA-256 sums are in [logs/stdout.txt](logs/stdout.txt).
- Tests: `test_linkcheck`, `test_paging` and `test_ccdi_pages` ran 30 tests on made-up data: OK. This was the first run of the paging tests.
- The Blade holds the kept second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC), so nothing was fetched and Q1-Q4 were graded.
- Full output: [out/paging-audit.json](out/paging-audit.json) (counts, page numbers and source names only).

## Grades

| | Prediction | Observed | Grade |
|---|---|---|---|
| Q1 | On `/subject`, the only losses are PCDC's two error pages. | Page size 100. Pages 1-599 all present, and none failed as a whole. The only loss flags: PCDC page 12 (error, 100 expected) and PCDC page 35 (error, 100 expected). No short or over-full page. | **pass** |
| Q2 | On `/subject`, every source reconciles. | All seven: served = total, except PCDC 24,232 of 24,432 (200 lost to error pages). Errors past the end: PCDC 354, StJude 452, Treehouse 471, ccdi-ecDNA 566, others 0. Not judged 0. Unexplained 0. | **pass** |
| Q3 | On `/subject-mapping`, the only loss is PCDC's silent short page 35. | Pages 1-599 all present, and none failed as a whole. The only loss flag: PCDC page 35 (short, 0 of 100 expected). No error and no over-full page. | **pass** |
| Q4 | On `/subject-mapping`, every source reconciles. | All seven: served = total, except PCDC 24,332 (100 lost to the short page). No errors past the end. Not judged 0. Unexplained 0. Unmapped entries 0. | **pass** |
| Q5 | Every silent loss on `/subject-mapping` sits on a page where `/subject` also lost that source. | 1 mapping flag (PCDC 35), and `/subject` flags PCDC 35 too. Not vacuous. | **pass** |
| Q6 | The audit explains every lost entry. | Unexplained = 0 for every source on both endpoints. | **pass** |

## What this establishes

- **On this snapshot, the losses are exactly the known ones and nothing else.** Every one of the 599 pages of both endpoints was checked, against each of the seven sources' totals. There is no silent short page that other pages make up for, and no over-full page. The census's totals alone could not have shown that.
- **1,843 of the census's 1,845 "page errors" lose nothing.** Four sources answer every page after their last one with an error object. Only PCDC's errors on pages 12 and 35 lose records (200). The census counted the two kinds together.
- **The Participant Index endpoint drops data with no signal.** `/subject-mapping` page 35 has no PCDC entries, with HTTP 200 and no error. It is the page where `/subject` returns an error for PCDC, because one PCDC record cannot be served (diagnostics stage 3, ../diagnostics-v3/).

## Since then

A later job (`linkcheck-repro-v1`, [../linkcheck-repro-v1/results.md](../linkcheck-repro-v1/results.md)) took a fresh snapshot on another machine, and that snapshot shows a third kind of loss. Page 345 of `/subject-mapping` came back empty with HTTP 200 for a moment, and the fetcher's "walk until a page is empty" rule stopped there, so 29,435 entries were never fetched. This audit's per-source expected counts would flag that page and count the pages that were not walked. The fix to the fetcher and a pre-registered audit of a kept fresh snapshot are in [../linkcheck-repro-v2/](../linkcheck-repro-v2/) (tag v0.8.0).

## Limits

- One snapshot. One model family (Claude) wrote and graded it, and no human has checked it.
- The audit counts entries; it does not compare them. Records repeated across pages, or the right number of the wrong records, would not be flagged.
- We have not contacted the data owners. The cause of the unservable PCDC record is not confirmed.

## Files

- `out/paging-audit.json`: the job's output.
- `logs/stdout.txt`, `logs/stderr.txt`, `logs/summary.json`: the job's log, test output and the runner's record.
