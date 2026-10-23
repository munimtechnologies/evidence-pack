# Results: does LinkCheck reproduce the CCDI census on real data?

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Grades of record: P1 fail, P2 fail, P3 fail, P4 fail; P5 and P6 not graded.** The predictions are in [README.md](README.md), published at evidence-pack tag v0.6.0 before the job ran. They are graded here exactly as written. All four failures have one cause, and it was the first one the pre-registration named as a likely miss: LinkCheck 0.1.0 keys records by (source, id), and 87 CCDI-DCC records share their id with another CCDI-DCC record. Separately, the fresh snapshot this job took is incomplete, for a reason no pre-registered check covered (section 3).

## 1. The run

- Sealed job `linkcheck-repro-v1`: 1 CPU, 2 GB, network on. It ran on the Dell from 2026-10-23 15:59 to 19:04 UTC, with a peak memory of 0.06 GB.
- `get_code.py` downloaded `analyze.py` and `fetch_ccdi.py` from tag v0.5.5, and LinkCheck 0.1.0 plus this folder from tag v0.6.0. All eight files were unchanged, and their SHA-256 sums are in [logs/stdout.txt](logs/stdout.txt).
- `test_repro.py` ran 7 tests on made-up data: OK.
- The Dell does not hold the kept second snapshot (its data volume is on the Blade). So `ensure_snapshot.py` took a fresh snapshot with the census's own `fetch_ccdi.py`, from about 15:59 to 19:02 UTC. We call it **snapshot 3**. All 957 logged requests returned HTTP 200: 8 federation summaries and counts, 2 GDC pages, 4 page-size probes, `/subject` pages 2-599 and `/subject-mapping` pages 1-345.
- Because the job used a fresh snapshot, P1-P4 compare LinkCheck with the census code on snapshot 3. P5 and P6 hold numbers that belong to snapshot 2, so the job did not grade them, as pre-registered.
- Full output: [out/repro.json](out/repro.json) (counts only, no participant IDs).

## 2. Grades

| | Prediction | Observed | Grade |
|---|---|---|---|
| P1 | Every served subject becomes exactly one LinkCheck record. | Census 153,580 subjects; LinkCheck 153,493 records; 87 repeated (source, id) keys, all CCDI-DCC | **fail** |
| P2 | LinkCheck's exact links make exactly the census's pairs. | Census 5,738 pairs, LinkCheck 5,695. As sets of (source, name) pairs they are identical (0 pairs only on one side) | **fail** (the counts differ) |
| P3 | Same over-count with exact links. | Persons 148,143 vs 148,094; naive over-count 5,437 vs 5,399; records in links 10,538 vs 10,500; linked persons 5,101 vs 5,101 | **fail** |
| P4 | Same agreement tables. | 4 of 11 source pairs differ, all involving CCDI-DCC (with KidsFirst, PCDC, StJude, Treehouse) | **fail** |
| P5 | Looser rules reproduce stage 2's Treehouse finding. | not graded (fresh snapshot) | not graded |
| P6 | Snapshot 2's absolute counts. | not graded (fresh snapshot) | not graded |

### Why P1-P4 failed: one cause

The census keys a subject by (source, namespace organization, namespace name, name). LinkCheck 0.1.0 keys a record by (source, id) and keeps the first copy. In snapshot 3, **87 CCDI-DCC records have the same name as another CCDI-DCC record in a different namespace** (the census kept all 153,580 keys apart, so each of the 87 differs from its twin in the namespace name or organization). LinkCheck folded them, and every other difference follows from that:

- P1: 153,580 - 87 = 153,493 records.
- P2: 43 of the census's pairs differ from another census pair only in which of two same-named CCDI-DCC records one end is. Written as (source, name) the two lists are the same set, but the census counts those 43 pairs separately and LinkCheck cannot.
- P3: the 87 folded records split into 49 that sat outside any link, which lowers persons by 49, and 38 that sat in links, which lowers the over-count and records-in-links by 38 (49 + 38 = 87). Linked persons do not change.
- P4: the 43 pairs fall in the four CCDI-DCC source pairs that differ.

The pre-registration named this risk first under "where a miss would most likely come from". The grade of record stays **fail**. The fix is LinkCheck 0.3.0, which keys a record by namespace when it has one and reports an id that two namespaces share as ambiguous instead of guessing. A new pre-registered reproduction tests it ([../linkcheck-repro-v2/](../linkcheck-repro-v2/), tag v0.8.0).

We do not yet know whether the 87 shared names are the same child enrolled in two CCDI studies or two different children whose study-specific IDs happen to match. The census counts them as two subjects. If they are one child, CCDI-DCC's own count is 87 too high. The v2 job measures this with aggregates only.

## 3. Not pre-registered: the fresh snapshot is incomplete

**Post hoc. No pre-registered check covered this; it was found while reading the job's log.**

`fetch_ccdi.py` has no counts for `/subject-mapping`, so it walks pages until one comes back empty. In snapshot 3, **page 345 came back with HTTP 200 and a 100-byte body with no Participant Index entries, so the walk stopped there.** In snapshot 2 the same walk went on to page 599. Read again on 2026-10-23 at about 20:30 UTC, page 345 serves 200 entries (100 KidsFirst, 100 CCDI-DCC), and page 598 serves 95 CCDI-DCC entries, which is what CCDI-DCC's 59,795 subjects predict. **So the empty page was transient, and a transient empty page with HTTP 200 silently cut the walk short.**

The entry count closes exactly on that reading. Snapshot 3 holds 124,245 Participant Index entries. That is 344 full pages for the two largest sources (CCDI-DCC 34,400; KidsFirst 34,400) plus every entry of the other five (PCDC 24,332, with its usual short page; StJude 14,681; Treehouse 12,723; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504). So **29,435 entries were never fetched** (CCDI-DCC 25,395; KidsFirst 4,040). The census code reads whatever pages exist and raised nothing.

The cost is large. With the same census code, snapshot 3 gives **5,738 cross-source pairs, against 20,496 on snapshot 2 (72% fewer)**, and 148,143 de-duplicated persons against 135,849. A de-duplicated count built on this snapshot would be about 12,300 children too high (148,143 - 135,849 = 12,294), with no error shown anywhere. (The body of page 345 was not kept. That it held no entries follows from the fetcher's stopping rule: it stops only on an HTTP 200 page without entries.)

LinkCheck 0.2.0's paging audit would have flagged it. By its formula (expected entries on page p = min(100, max(0, T - (p - 1) x 100))), page 345 is short by 100 for both sources. The pages not walked hold 25,295 CCDI-DCC and 3,940 KidsFirst entries, so the audit would have explained all 29,435 lost entries. **This is worked out by hand from the counts above. The audit was not run on snapshot 3**, because the job kept the snapshot only inside its container. The v2 job keeps its snapshot, and it does not stop at an empty page before the expected last one.

`/subject` was also slightly different in snapshot 3. PCDC lost 100 records (one error page; in snapshots 1 and 2 it lost 200 on pages 12 and 35), and ccdi-ecDNA lost 100 (one error page; none before). By coincidence, the federation total, 153,580 unique subjects, is the same as in snapshot 2. These per-source losses are inferred from LinkCheck's per-source record counts and the census's per-source error counts in `out/repro.json`. The pages themselves were not kept, so the page numbers are unknown.

## 4. Descriptive only (snapshot 3; affected by the truncated walk)

LinkCheck's report is in `out/repro.json` under `linkcheck_report`. With the looser rules, `alt_id` adds 957 pairs (Treehouse links), and `suffix` resolves 1,075 links, all to pairs already made. Of the link rows, 1,263 are self-references, 24 exact plus 3 `alt_id` links stay within one source, and 58,786 stay unresolved. Because 29,435 Participant Index entries are missing, none of these is a federation-level number. Use snapshot 2's published numbers instead (../diagnostics-v1/, ../diagnostics-v2/).

## 5. Limits

- One snapshot, one job, one model family (Claude) wrote and graded it, and no human has checked it.
- Section 3 is post hoc. The decomposition of 124,245 entries is the one that closes exactly with full pages to 344 and the known totals; per-page counts for snapshot 3 were not kept.
- The two live re-reads of pages 345 and 598 were single requests on 2026-10-23, and nothing was sent by participant ID.
- We have not told the data owners and have not contacted anyone. The cause of the empty page (server load, a deployment, a timeout inside the federation) is unknown.

## Files

- `out/repro.json`: the job's output.
- `logs/stdout.txt`, `logs/stderr.txt`: the job's full log (SHA-256 of the downloaded code, test output, every request of snapshot 3 with status and size).
- `logs/summary.json`: the runner's record of the job (machine, times, steps, exit codes).
