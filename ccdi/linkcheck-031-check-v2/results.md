# Results: LinkCheck 0.3.1 on a new CCDI snapshot (second try)

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

**Grades of record: T1, T2, T3 and T4 pass (4 of 4). R1-R4 not graded. All 57 tests passed.** The predictions are in [README.md](README.md), published at evidence-pack tag v0.8.7 before the job ran. They are graded here exactly as written.

## The run

- Sealed job `linkcheck-031-v2`: 1 CPU, 2 GB, network on. It ran on the Dell from 2026-10-24 02:01:40 to 05:55:39 UTC (peak memory 0.05 GB; [logs/summary.json](logs/summary.json)).
- `get_code.py` downloaded every file unchanged from tags v0.8.7, v0.8.5, v0.8.0, v0.7.0 and v0.5.5, and logged the SHA-256 of each ([logs/setup-01-stdout.txt](logs/setup-01-stdout.txt)). The download from v0.8.7 succeeded on the first try, so the pre-registration was public before any data was fetched.
- Tests: 57 ran on made-up data and all passed: LinkCheck 14, paging 11, namespaces 4, page-body reader 12, the paging-audit reader 5, the first try's check 6, and this check's 5 ([logs/setup-02-stderr.txt](logs/setup-02-stderr.txt)). The JSON in [logs/setup-02-stdout.txt](logs/setup-02-stdout.txt) is printed by those tests (including the "grader can fail" cases on made-up data); it is not a result.
- The machine held no kept second snapshot and no fresh snapshot, so `ensure_snapshot2.py` took a new one with `fetch_robust.py` (tag v0.8.0): `ccdi-raw-fresh-20261024T020144Z`, from 02:01:44 to 05:53:56 UTC, 1,211 requests ([logs/setup-03-stdout.txt](logs/setup-03-stdout.txt)). Only the Blade held the kept snapshots; the Dell now keeps this one on its own data volume.
- As pre-registered, `check031b.py` then graded T1-T4 on that snapshot and wrote R1-R4 as "not graded" ([out/check031b.json](out/check031b.json)).

## Grades

| | Prediction | Pass if | Observed | Grade |
|---|---|---|---|---|
| T1 | `body_counts` reads every saved `/subject` page exactly as the paging audit's reader does | no page rejected, and per-source counts equal on all 599 pages | 599 pages, 0 rejected, 0 differing | pass |
| T2 | `/subject`: walk complete, nothing to refetch, only loss PCDC page 35 | `required_last_page` 598, `refetch_pages` empty, exactly one flag: PCDC error on page 35 expecting 100 | 598; none; one flag, `[35, PCDC, error, null, 100]` | pass |
| T3 | `/subject-mapping`: the same without refetch | `required_last_page` 598, `refetch_pages` empty | 598; none | pass |
| T4 | a walk-until-empty client stops at the right place | first page with no entries is 599 on both endpoints | 599 and 599 | pass |

## What this adds

- **LinkCheck 0.3.1's page reader and refetch rule work on real CCDI pages.** On a snapshot nobody had seen when the predictions were written, `body_counts` read all 599 `/subject` pages exactly as the separate paging-audit reader does, and the refetch rule asked for nothing because nothing was missing.
- **The one silent loss is stable.** PCDC's `/subject` page 35 failed again, and its Participant Index page is again short by exactly 100 PCDC entries with no error. It has now failed in every snapshot we have audited page by page: the kept second snapshot (2026-10-22/23), `ccdi-fresh-v1` (2026-10-23/24) and this one, about 29 hours after the first began. The failing page's body was 473,425 bytes here and in `ccdi-fresh-v1`. Page 12, which failed once in the second snapshot, was served in full.
- **The fetch needed no retry.** `retries.json` is empty for both endpoints, and the log has exactly one line per page (598 `/subject` pages after the first, 599 `/subject-mapping` pages). Three index pages were slow but complete: pages 121, 140 and 180 took 208, 310 and 1,062 seconds.

## Descriptive only (not pre-registered)

From [out/check031b.json](out/check031b.json):
- The seven source totals are unchanged since 2026-10-22: CCDI-DCC 59,795; KidsFirst 38,440; PCDC 24,432; StJude 14,681; Treehouse 12,723; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504. Every source but PCDC was served in full on both endpoints (0 unexplained).
- Error parts on `/subject`: 1,844 in all. 1,843 fall past a source's last page and lose nothing (PCDC 354, StJude 452 and Treehouse 471 as "InvalidParameters"; ccdi-ecDNA 566 as "NotFound"). The one that loses records is PCDC's page 35, also "NotFound". So an error's kind alone does not tell a client whether records were lost: ccdi-ecDNA uses the same kind for its harmless past-the-end pages.
- Replaying the 2026-10-23 truncation on this snapshot (pretending the walk stopped at page 345), the refetch rule asks again for pages 345 to 598 (254 pages), so that cut would no longer pass silently.

## Limits

- One model family (Claude) wrote the code, the tests and the predictions, and graded them. No human has checked any of it.
- T1-T4 test one snapshot. Only one of the two pre-registered sets was graded; R1-R4 (on the kept second snapshot) remain untested.
- The snapshot stays on the job's data volume and is not published; outputs are aggregates only (counts, page numbers, source names, error kinds).

## Files

- `out/check031b.json`: the job's output (grades, both page audits, error kinds, the replayed cut, the fetch record).
- `logs/setup-01-stdout.txt`: downloaded files with SHA-256. `logs/setup-02-stderr.txt`: the 57 tests. `logs/setup-03-stdout.txt`: the fetch log (status, bytes and seconds per request). `logs/run-01-stdout.txt`: the grades as printed. `logs/summary.json`: the runner's record (machine, times, steps, exit codes).
