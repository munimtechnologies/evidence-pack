# Results: a fresh CCDI snapshot reaches the end, and the 87 shared CCDI-DCC names

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

**Grades of record: F1, P1, P2, P3, P4, G1, G2 and G3 pass (8 of 8).** F1 and P1-P4 are graded exactly as pre-registered at evidence-pack tag v0.8.0 ([../linkcheck-repro-v2/README.md](../linkcheck-repro-v2/README.md)). G1-G3 are graded exactly as pre-registered at tag v0.8.2 ([README.md](README.md)). Both tags were public before the job ran. P5, P6 and S1 belong to the second snapshot and were not graded, as planned.

## 1. The run

- Sealed job `ccdi-fresh-v1`: 1 CPU, 2 GB (peak 0.06 GB), network on. It ran on the Blade from 2026-10-23 21:41:54 to 2026-10-24 01:25:02 UTC.
- `get_code.py` got a 404 once while tag v0.8.2 was not yet public, then downloaded 19 files unchanged (SHA-256 in [logs/stdout.txt](logs/stdout.txt)).
- Tests: 51 ran on made-up data and all passed: LinkCheck 14, paging 11, namespaces 4, `test_repro2` 13, `test_fresh1` 9 ([logs/stderr.txt](logs/stderr.txt)).
- `ensure_snapshot2.py` was pointed at an empty folder on purpose, so `fetch_robust.py` took a fresh snapshot: 2026-10-23 21:46:58 to 2026-10-24 01:22:28 UTC, 1,211 sequential requests, every one answered with HTTP 200. **No page had to be fetched again** (`retries.json` is empty for both endpoints). The snapshot is kept on the Blade's data volume.
- Outputs: [out/repro2.json](out/repro2.json) and [out/fresh1.json](out/fresh1.json): counts, page numbers, source names and public study accessions only, no participant IDs.

## 2. Grades

| | Prediction | Observed | Grade |
|---|---|---|---|
| F1 | A fresh snapshot taken by `fetch_robust.py` reaches the end of both endpoints. | Both endpoints walked to page 599; no missing pages; for every source, 0 entries on pages not walked and 0 unexplained | **pass** |
| P1 | Every served subject becomes exactly one LinkCheck record. | Census 153,680 subjects; LinkCheck 153,680 records; 0 repeated keys | **pass** |
| P2 | LinkCheck's exact links make exactly the census's pairs. | 20,496 pairs each; 0 only in the census, 0 only in LinkCheck | **pass** |
| P3 | Same over-count with exact links. | Both: 135,949 persons, naive over-count 17,731, 14,847 linked persons, 32,578 records in links | **pass** |
| P4 | Same agreement tables with exact links. | Overall tables equal; 0 of 12 source pairs differ | **pass** |
| G1 | Source totals unchanged since the second snapshot. | `/subject/summary`: CCDI-DCC 59,795; KidsFirst 38,440; PCDC 24,432; StJude 14,681; Treehouse 12,723; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504; none differ | **pass** |
| G2 | The shared names replicate. | 87 groups, all of size 2; 87 extra records, all CCDI-DCC; no group with the same namespace name twice | **pass** |
| G3 | No contradiction within a shared name, for either name shape. | Both shapes occur (41 USI-shaped, 46 other); 0 disagreements on sex, race, ethnicity, vital status or age at death in either | **pass** |

**What this shows.** LinkCheck reproduces the census exactly on a third, independent fetch: every pair, every over-count figure and every agreement table. The robust fetcher walked both endpoints to the end. It did not have to retry anything this time, so its retry path is still tested only by its made-up-data tests. The federation's sources held the same totals about a day apart, and the 87 shared CCDI-DCC names came back unchanged.

## 3. Descriptive only (not pre-registered)

### PCDC page 35 fails again; page 12 does not

- On `/subject`, PCDC's part of page 35 is again an error object. The response is 473,425 bytes, the same size as in the census snapshot and the second snapshot, where it was byte-identical ([../diagnostics-v1/results.md](../diagnostics-v1/results.md); this job logs sizes only). On `/subject-mapping`, page 35 is again silently short by PCDC's 100 entries, with no error. So 100 PCDC records are missing from both endpoints, as in every snapshot so far.
- Page 12, which failed in the second snapshot with a connection error that one retry cleared, was served in full (679,407 bytes, the same size as in the census snapshot).
- That is why this snapshot serves 153,680 subjects, 100 more than the second (153,580). Its census numbers equal those of the original census snapshot (de-duplicated 135,949, linked persons 14,847, over-count 17,731). The 100 extra records add 100 persons and no cross-source pair.
- Error objects on `/subject`: 1,844 per-source error parts. One is the real loss (PCDC page 35). The other 1,843 come after a source's last page: PCDC 354, StJude 452, Treehouse 471, ccdi-ecDNA 566, exactly as in the second snapshot.

### The 87 shared CCDI-DCC names

- **The census's own links already join 51 of the 87 pairs into one person. For the other 36, neither record is in any cross-source link**, so the census counts them as two persons. No pair has its two records linked to different persons, and no pair has only one record linked. The split is the same, 51 and 36, on the kept second snapshot.
- If each shared name is one child, the de-duplicated count would be 135,913, not 135,949. **The census is too high by at most 36 (0.03%), not "up to 87" as our v0.8.1 results put it.** That bound was correct but loose.
- The pairs come from four pairs of study namespaces (public dbGaP accessions): phs002276 / phs003432 (39), phs002620 / phs003111 (28), phs000463 / phs000464 (18), phs000720 / phs002883 (2).
- Agreement by name shape (fresh snapshot; the kept second snapshot gives the same tables):

| Field | USI-shaped (41): agree / not comparable | Other (46): agree / not comparable |
|---|---|---|
| Sex | 41 / 0 | 46 / 0 |
| Race | 39 / 2 | 16 / 30 |
| Ethnicity | 7 / 34 | 13 / 33 |
| Vital status | 14 both dead / 27 | 7 both alive, 10 both dead / 29 |
| Age at death (both dead) | 14 within 1 day | 10 within 1 day |

No field disagrees in any of the 87 pairs. That **suggests** each pair is one child enrolled in two studies of the same program. It does not prove it, and the data owners have not been asked.

### LinkCheck's looser rules

The `alt_id` rule again adds exactly 1,094 Treehouse pairs (21,590 pairs in all; 135,144 persons with the rules, 100 more than in the second snapshot, from the same 100 page-12 records).

## 4. Limits

- One fresh snapshot, one job. One model family (Claude) wrote the code and the predictions and graded them, and no human has checked any of it.
- P1-P4 show that two pieces of code agree on the same data. They do not show that either models the federation correctly.
- F1 passed without a single retry, so it does not show that the retries work on live data.
- Section 3 is post hoc. Agreement does not prove identity. Byte sizes match earlier snapshots, but content was not compared in this job.

## Files

- `out/repro2.json`, `out/fresh1.json`: the job's outputs.
- `logs/stdout.txt`, `logs/stderr.txt`, `logs/summary.json`: the job's full log (request log with sizes, SHA-256 of the code, test output) and the runner's record (machine, times, steps, exit codes).
