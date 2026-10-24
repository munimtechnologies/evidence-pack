# Results: does LinkCheck 0.4.0 read a CCDI snapshot exactly as the job code did?

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

**Grades of record: C1, C2, C3, C4 and C5 pass (5 of 5), on one snapshot. All 52 tests passed.** The predictions are in [README.md](README.md), published at evidence-pack tag v0.8.9 before the job ran. They are graded here exactly as written: "A prediction holds if it passes on every snapshot graded."

## The run

- Sealed job `linkcheck-040-v1`: 1 CPU, 3 GB, network on. It ran on the Dell from 2026-10-24 11:39:58 to 11:42:42 UTC (163 seconds; [logs/summary.json](logs/summary.json)). It sent no request to the federation.
- `get_code.py` downloaded every file unchanged from tags v0.8.9, v0.8.0, v0.7.0 and v0.5.5 and logged the SHA-256 of each ([logs/setup-01-stdout.txt](logs/setup-01-stdout.txt)). The download from v0.8.9 succeeded on the first try (the step took 3 seconds), so the pre-registration was public before anything was graded.
- Tests: 52 ran on made-up data and all passed: LinkCheck 14, paging 11, namespaces 4, page-body reader 12, the new CCDI reader 6 (their first run) and this check's 5 ([logs/setup-02-stderr.txt](logs/setup-02-stderr.txt)). The JSON in [logs/setup-02-stdout.txt](logs/setup-02-stdout.txt) is printed by those tests, including the made-up cases where C5 fails by design; it is not a result.
- **Which snapshots were graded.** The Dell keeps one snapshot: `ccdi-raw-fresh-20261024T020144Z`, taken by `fetch_robust.py` (tag v0.8.0) from 2026-10-24 02:01 to 05:53 UTC. The kept second snapshot and the 2026-10-23/24 fresh snapshot are on the Blade, so the first row of the C5 table (kept second snapshot) was not graded. The snapshot that was graded is the one where, as the pre-registration says, C5 is a real prediction.

## Grades

| | Prediction | Observed on `ccdi-raw-fresh-20261024T020144Z` | Grade |
|---|---|---|---|
| C1 | the package's records equal `adapt()`'s, same values and order | 153,680 records each; no first difference | pass |
| C2 | the same link rows, same order, and the same association counts | 150,161 link rows each; USI associations 21,567, organizational associations 134,265, other categories skipped 87,988, USIs served by no subject 6,589, in both | pass |
| C3 | the same page size, per-page per-source counts on both endpoints, unmapped entries and source totals as `ccdi_pages.py` | 100 per page; 599 `/subject` and 599 Participant Index pages, no page differing; 0 unmapped entries in both; totals equal | pass |
| C4 | LinkCheck's exact pairs from the package's reading are the census code's pairs, and its exact over-count equals the census's section D | 20,496 pairs in both, none only in one; persons 135,949, naive over-count 17,731, linked persons 14,847, records in links 32,578 in both | pass |
| C5 | from the package alone: 153,680 records, 20,496 exact pairs, 135,949 persons, naive over-count 17,731, CCDI-DCC 87 shared ids in 174 records | 153,680; 20,496; 135,949; 17,731; CCDI-DCC 87 ids, 174 records | pass |

## What this adds

- **LinkCheck 0.4.0's CCDI reader is a faithful move of the job code.** On a real snapshot, `python -m linkcheck.ccdi` gives the same records, link rows, page counts, pairs and over-count as the three pieces of job code it replaces (C1-C4). These compare two readings of the same files, both written by the same model family, so they show the transcription was faithful, not that the reading is right; the census's own checks are the evidence for that.
- **C5 was a real prediction, and it held.** Nobody had counted this snapshot's records, pairs or persons before. The record count was close to implied by its page audit (tag v0.8.8: the same seven source totals and the same single failing page, so 153,780 - 100 = 153,680 records served); the pair, person and over-count numbers were not. A changed record inside an unchanged total, or a changed Participant Index, would have changed them.

## Descriptive only (not pre-registered)

From [out/check040.json](out/check040.json), on this snapshot (taken about two days after the census's snapshot of 2026-10-22):
- **Table 1 of the census holds unchanged on a fourth complete snapshot** (after the census's, the second snapshot and the 2026-10-23/24 fresh snapshot; the 2026-10-23 walk that was cut short is not counted). Sex disagreement 7 of 19,702 linked pairs with both values; race 5 of 11,019; vital status missing on one or both sides in 19,081 of 20,496 pairs; Alive against Dead in 149 of 1,415 pairs with both values, 145 of them (of 1,089) in CCDI-DCC with ccdi-ecDNA. These are the census's numbers (tag v0.5.6).
- With LinkCheck's looser rules: alternate identifiers add 1,094 pairs (21,590 in all), as on the second snapshot; persons 135,144, naive over-count 18,536.
- Paging: only PCDC's `/subject` page 35 failed, and its Participant Index page is short by exactly the same 100 PCDC entries. This is the same snapshot as tag v0.8.8, so it is not a new observation.

## Limits

- One model family (Claude) wrote the package code, the job code it is compared with, this check and this grading. No human has checked any of it.
- One snapshot was graded. The kept second snapshot (the first row of the C5 table) stays ungraded because the job ran on the machine that does not hold it.
- The snapshot stays on the job's data volume and is not published; outputs are aggregates only (counts, page numbers, source names). `check040.py` refuses to write any string shaped like a COG USI.

## Files

- `out/check040.json`: grades per snapshot and overall, and the package's aggregate result (LinkCheck report and both paging audits).
- `logs/setup-01-stdout.txt`: downloaded files with SHA-256. `logs/setup-02-stderr.txt`: the 52 tests. `logs/setup-02-stdout.txt`: output printed by the tests. `logs/run-01-stdout.txt`: the grades as printed. `logs/summary.json`: the runner's record (machine, times, steps, exit codes).
