# Pre-registration, second try: LinkCheck 0.3.1 on saved CCDI pages, on whichever snapshot the machine holds

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

**Status: PRE-REGISTERED.** This page, `check031b.py` and predictions T1-T4 are published at evidence-pack tag **v0.8.7** before the sealed job `linkcheck-031-v2` runs. Predictions R1-R4 are the ones published at tag v0.8.5 ([../linkcheck-031-check-v1/README.md](../linkcheck-031-check-v1/README.md)) and are not changed. The job downloads its code from tags v0.8.7, v0.8.5, v0.8.0, v0.7.0 and v0.5.5 and waits until v0.8.7 is public, so it cannot run code that differs from what is published. Results will be added as `results.md` in a later tag and graded exactly as written.

## Why a second try

The first try, `linkcheck-031-v1`, ran on 2026-10-24 from 00:52 to 00:55 UTC on a machine that does not hold the kept second snapshot. All 52 tests passed, but R1-R4 were **not graded** ([../linkcheck-031-check-v1/results.md](../linkcheck-031-check-v1/results.md)). A job cannot choose its machine, and each machine has its own data volume. We had already learned that lesson once (a conditional prediction should not depend on where the job lands) and did not apply it. This try does.

## What the job does

1. `get_code.py` downloads every file unchanged and logs SHA-256.
2. It runs all the tests from the first try plus this folder's `test_check031b` (5 tests, made-up data only, every expected value worked out by hand).
3. `ensure_snapshot2.py /data/ccdi-raw-snapshot2 /data/ccdi-fresh-v1` (tag v0.8.0, unchanged) does nothing if the machine holds the kept second snapshot or a complete fresh snapshot under `/data/ccdi-fresh-v1`. Otherwise it takes a fresh snapshot there with `fetch_robust.py` (about 1,200 sequential requests over 3.5 hours, the same as `ccdi-fresh-v1`).
4. `check031b.py` grades one set:
   - **kept second snapshot present:** R1-R4, by `check031.py` from tag v0.8.5, unchanged, exactly as pre-registered there; T1-T4 are not graded;
   - **otherwise, the newest complete fresh snapshot:** T1-T4 below, by the same code with the fresh values; R1-R4 are not graded.

Only the Blade holds the second snapshot and the fresh snapshot `ccdi-fresh-v1` kept on 2026-10-24. On any other machine the job takes a new snapshot, so T1-T4 are then tested on data fetched about a day after the last one.

## Predictions T1-T4 (fresh snapshot only)

| | Prediction | Pass if |
|---|---|---|
| T1 | `body_counts` reads every saved `/subject` page exactly as the paging audit's own reader does. | It rejects no page, and on all 599 pages its per-source counts (an error part as null) equal those of `ccdi_pages.subject_walk` (tag v0.7.0). |
| T2 | On `/subject`, the walk is complete, nothing needs to be fetched again, and the only loss is PCDC's page 35. | `required_last_page` is 598, `refetch_pages` is empty, and the flags are exactly one: a PCDC error on page 35 expecting 100 entries. |
| T3 | On `/subject-mapping`, the same holds without any refetch. | `required_last_page` is 598 and `refetch_pages` is empty. |
| T4 | A walk-until-empty client would stop at exactly the right place. | The first page with no entries from any source (or failed as a whole) is page 599 on both endpoints. |

**Why we expect each.** In the fresh snapshot of `ccdi-fresh-v1` (2026-10-23 21:47 to 2026-10-24 01:22 UTC; [../fresh-snapshot-v1/results.md](../fresh-snapshot-v1/results.md)) the seven source totals were unchanged, so CCDI-DCC's 59,795 subjects still end on page 598. Its paging audit (LinkCheck 0.3.0) flagged exactly one PCDC error, on `/subject` page 35. Page 12, which failed in the second snapshot with a connection error that a single retry already cleared ([../diagnostics-v1/results.md](../diagnostics-v1/results.md)), was served in full. Our earlier diagnostics traced page 35 to one PCDC record that fails at every page size, so we expect it to keep failing and page 12 to keep working.

**What is and is not new.** If the job reads the kept `ccdi-fresh-v1` snapshot (on the Blade, when the second snapshot is missing), the flags in T2 are already known from that published audit, so T1-T4 then test only the new code. If the job takes a new snapshot, T2 is also a real test of whether page 35 still fails and page 12 still works a day later.

**Where a miss would most likely come from.** T2-T4: a source releasing data (the last page moves), a new failing page, or page 35 recovering. T1: a page body shape that `body_counts` rejects. A transient outage longer than the fetcher's retries would show up as a refetch page in T2 or T3, and in `retries.json`.

## Not pre-registered (descriptive only)

The same descriptive outputs as the first try (error kinds per source with no messages, the replay of a cut at page 345), plus `complete.json` and `retries.json` of a fresh snapshot (times, request count, retried page numbers).

## Limits

- One model family (Claude) wrote the code, the tests and these predictions, and will grade them. No human has checked any of it.
- Only one of the two sets is graded, depending on the machine.

## Files

- `check031b.py`, `test_check031b.py`: the check and its tests (they reuse the made-up snapshot of `../linkcheck-031-check-v1/test_check031.py`).
- `get_code.py`, `job.json`: the job as filed (1 CPU, 2 GB, network on, up to 6 hours, data volume `ccdi-raw`).
