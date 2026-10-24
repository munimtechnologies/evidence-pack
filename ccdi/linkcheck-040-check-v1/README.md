# ccdi/linkcheck-040-check-v1: does LinkCheck 0.4.0 read a CCDI snapshot exactly as the job code did? (PRE-REGISTERED)

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name on 2026-10-24; no human has reviewed it. Research software and data-quality work only; not medical advice.

**Status: pre-registered.** These predictions and the code that grades them are published at evidence-pack tag v0.8.9, before the sealed job `linkcheck-040-v1` runs. The job's setup waits until this tag is public. Results will be published at a later tag, whatever they are.

## Why

Every earlier check of LinkCheck on NCI's CCDI Data Federation read the saved snapshot with job code: `adapt()` in [ccdi/linkcheck-repro-v2](../linkcheck-repro-v2/) (tag v0.8.0), on top of the census's reader `analyze.py` ([ccdi/concordance-v1](../concordance-v1/), tag v0.5.5), and `ccdi_pages.py` ([ccdi/paging-audit-v1](../paging-audit-v1/), tag v0.7.0). LinkCheck 0.4.0 moves that reading into the package (`linkcheck/ccdi.py`), so that one command, `python -m linkcheck.ccdi --raw <snapshot> --out result.json`, gives the LinkCheck report and both paging audits. A rewrite can drift. This check tests that it did not.

## What the job does

The job `linkcheck-040-v1` downloads, unchanged, LinkCheck 0.4.0 and this folder from tag v0.8.9, `analyze.py` from tag v0.5.5, `ccdi_pages.py` from tag v0.7.0, and `repro2.py` and `ensure_snapshot2.py` from tag v0.8.0, and logs each file's SHA-256. It runs every test (LinkCheck's five test files and this folder's), then `check040.py` on every snapshot the machine keeps:
- the kept second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC), if this machine holds it;
- the newest complete fresh snapshot under the job's data folder (taken by `fetch_robust.py`: one machine holds one from 2026-10-23 21:47 to 2026-10-24 01:22 UTC, the other one from 2026-10-24 02:01 to 05:53 UTC).

It sends no request to the federation. A machine that kept no snapshot grades nothing. Every machine the job can land on holds at least one fresh snapshot.

## Predictions

On every snapshot graded:

- **C1. Records.** `ccdi.read_snapshot()` gives exactly the records `adapt()` gives (same values, same order).
- **C2. Links.** It gives exactly the same link rows (same order) and the same association counts.
- **C3. Pages.** It gives the same page size, the same per-page, per-source entry counts on `/subject` and on the Participant Index (`/subject-mapping`), the same number of unmapped Participant Index entries, and the same source totals as `ccdi_pages.py`.
- **C4. The census.** The exact pairs LinkCheck finds from the package's own reading are exactly the census code's pairs (none only in one of them, and the same count), and LinkCheck's exact over-count (persons, naive over-count, linked persons, records in links) equals the census's section D.
- **C5. Absolute numbers** from the package alone (`ccdi.check()`):

| Snapshot | Records | Exact pairs | Persons | Naive over-count | Shared ids |
|---|---|---|---|---|---|
| kept second snapshot | 153,580 | 20,496 | 135,849 | 17,731 | CCDI-DCC: 87 ids, 174 records |
| newest fresh snapshot | 153,680 | 20,496 | 135,949 | 17,731 | CCDI-DCC: 87 ids, 174 records |

A prediction holds if it passes on every snapshot graded.

How strong each prediction is:
- C1-C4 compare two readings of the same files. The package code was written from the job code, so they test faithful transcription, not a new claim about the federation.
- C5's numbers for the kept second snapshot and for the 2026-10-23/24 fresh snapshot were already measured (tags v0.8.1 and v0.8.6), so there C5 only re-checks known numbers. **For the 2026-10-24 02:01-05:53 UTC fresh snapshot, C5 is a real prediction**: only its pages have been audited so far (tag v0.8.8: the same seven source totals and the same single failing page, PCDC's `/subject` page 35), and nobody has counted its records, pairs or persons. A changed record inside an unchanged total, or a changed Participant Index, would make it fail.

## Output

`check040.json`: the grades, per snapshot and overall, and per snapshot the package's aggregate result (the LinkCheck report and both paging audits). Aggregates only: counts, page numbers and source names, never participant ids. The script refuses to write anything that holds a string shaped like a COG USI.

## Files

- `check040.py`: the check; `test_check040.py`: its tests, on the made-up snapshot of LinkCheck's `test_ccdi.py` (C1-C4 pass and C5 fails there by design, because the made-up numbers are not the real ones).
- The job's setup script (`get_code.py`) and job file (`job.json`).

## Limits

- One model family (Claude) wrote the package code, the job code it is compared with, and this check. Agreement between them shows the move into the package was faithful, not that the reading is right; the census's own pre-registered checks and the paging audit are the evidence for that.
- The kept second snapshot is graded only if the job lands on the machine that holds it.
