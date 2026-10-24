# Results: LinkCheck 0.3.1 on the saved CCDI pages (first try)

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Grades of record: R1, R2, R3 and R4 not graded. All 52 tests passed.** The predictions are in [README.md](README.md), published at evidence-pack tag v0.8.5 before the job ran.

## The run

- Sealed job `linkcheck-031-v1`: 1 CPU, 2 GB, network on. It ran on 2026-10-24 from 00:52:41 to 00:55:17 UTC on the Dell, which does not hold the kept second snapshot.
- `get_code.py` downloaded every file unchanged from tags v0.8.5 and v0.7.0 (SHA-256 in [logs/stdout.txt](logs/stdout.txt)).
- Tests: 52 ran on made-up data and all passed: LinkCheck 14, paging 11, namespaces 4, the new `test_paging_body` 12 (first run), the paging-audit reader 5, and this check's `test_check031` 6 (first run). See [logs/stderr.txt](logs/stderr.txt).
- `check031.py` found no `/data/ccdi-raw-snapshot2` on that machine, so, as pre-registered, it wrote R1-R4 as "not graded" ([out/check031.json](out/check031.json)).

## What this means

Nothing about the real data was learned. The new code (`body_counts`, `error_messages`, `last_page`, `refetch_pages`) passed its hand-worked tests for the first time outside the machine it was written on, and that is all.

This is our own mistake, and one we had already written down: a conditional prediction should not depend on which machine a job lands on. The second try, [../linkcheck-031-check-v2/](../linkcheck-031-check-v2/) (tag v0.8.7), grades R1-R4 unchanged if it lands on the machine with the kept snapshot, and otherwise grades T1-T4, pre-registered for a fresh snapshot, so one set is graded wherever it runs.

## Files

- `out/check031.json`: the job's output.
- `logs/stdout.txt`, `logs/stderr.txt`, `logs/summary.json`: the job's log and the runner's record (machine, times, steps, exit codes).
