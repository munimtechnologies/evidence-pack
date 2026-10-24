# Results: ccdi/linkcheck-050-check-v1 (first filing): not graded, the grader's own test failed

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Not medical advice.

## Outcome

The sealed job `linkcheck-050-v1` ran on the Dell, 2026-10-24 18:37:50-18:39:05 UTC (74 s).

- **Setup step 1 passed.** `get_code.py` downloaded every file from tags v0.9.1, v0.8.9 and v0.8.0. Their SHA-256 values are in `logs/stdout.txt`. The tag was already public, so the job did not wait.
- **Setup step 2 failed.** 63 tests ran: 62 passed and one failed, `test_check050.MadeUpSnapshot.test_grade_one` (see `logs/stderr.txt`). LinkCheck 0.5.0's own 59 tests, including the 12 new standards tests, all passed for the first time.
- **The check itself never ran.** No snapshot was read, so **S1-S6 are not graded**. This is a failure of our grader, not a result about the data.

## Cause

S1 compares 0.5.0's output with 0.4.0's, skipping `tool`. The paging audit stamps its own version inside each paging section (`paging.subject.tool`, `paging.mapping.tool`). The grader skipped only the top-level stamp and `linkcheck.tool`, so on made-up data it reported `differing_keys: ['paging']` because of the version strings alone. The cohort columns were identical (`cohort_old_columns_identical: true`). The unit test, written by hand before the first run, expected S1 to pass, and it caught the bug before any real data was used.

## What happens next

The same predictions, unchanged, are filed again with a corrected grader as `ccdi/linkcheck-050-check-v2` (tag v0.9.2), job `linkcheck-050-v2`. Its setup pins every reused file to the SHA-256 values in this job's log.

## Files

`logs/summary.json`, `logs/stdout.txt`, `logs/stderr.txt`: the runner's record of this job, unchanged.
