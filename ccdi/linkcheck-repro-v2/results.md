# Results: does LinkCheck 0.3.0 reproduce the CCDI census, and does a fresh snapshot reach the end?

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Grades of record: P1, P2, P3, P4, P5, P6 and S1 pass; F1 not graded.** The predictions are in [README.md](README.md), published at evidence-pack tag v0.8.0 before the job ran, and graded here exactly as written. The job ran on the kept second snapshot. So the absolute counts (P5, P6, S1) were graded, and F1, the test of the new fetcher, was not. F1 is now pre-registered again in a job that must take a fresh snapshot ([../fresh-snapshot-v1/](../fresh-snapshot-v1/), tag v0.8.2).

## 1. The run

- Sealed job `linkcheck-repro-v2`: 1 CPU, 2 GB, network on. It ran on the Blade from 2026-10-23 20:23:41 to 20:35:56 UTC.
- `get_code.py` waited for tag v0.8.0: the first two tries got 404, and the third, about 10 minutes in, succeeded. It then downloaded 16 files unchanged: `analyze.py` and `fetch_ccdi.py` from tag v0.5.5, `ccdi_pages.py` from v0.7.0, and LinkCheck 0.3.0 plus this folder from v0.8.0. Their SHA-256 sums are in [logs/stdout.txt](logs/stdout.txt).
- Tests: 42 ran on made-up data (LinkCheck's 14, paging 11, namespaces 4, `test_repro2` 13), and all passed.
- `ensure_snapshot2.py` found the kept second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC) on the Blade's data volume, so nothing was fetched. That makes P5, P6 and S1 gradeable, and F1 not.
- Full output: [out/repro2.json](out/repro2.json) (counts, page numbers, source names; no participant IDs).

## 2. Grades

| | Prediction | Observed | Grade |
|---|---|---|---|
| P1 | Every served subject becomes exactly one LinkCheck record. | Census 153,580 subjects; LinkCheck 153,580 records; 0 repeated (source, id, namespace) keys | **pass** |
| P2 | LinkCheck's exact links make exactly the census's pairs. | 20,496 pairs each; 0 pairs only in the census, 0 only in LinkCheck | **pass** |
| P3 | Same over-count with exact links. | Both: 135,849 persons, naive over-count 17,731, 14,847 linked persons, 32,578 records in links | **pass** |
| P4 | Same agreement tables with exact links. | Overall tables equal; 0 of 12 source pairs differ | **pass** |
| P5 | Looser rules reproduce stage 2's Treehouse finding and add nothing else. | Added `{"alt_id": 1094}` only; 21,590 pairs; 135,044 persons, over-count 18,536, 15,403 linked persons, 33,939 records in links; extra disagreements sex +3, ethnicity +2, race +0 | **pass** |
| P6 | Snapshot 2's absolute exact-link counts. | 153,580 records; 20,496 pairs; 135,849 persons; over-count 17,731; 14,847 linked persons; 32,578 records in links | **pass** |
| S1 | Snapshot 2 has the same shared CCDI-DCC names as snapshot 3. | 87 groups, 87 extra records, all CCDI-DCC | **pass** |
| F1 | A fresh snapshot taken by `fetch_robust.py` reaches the end of both endpoints. | not graded (the kept snapshot was used) | not graded |

**What this shows.** LinkCheck is a general record-linkage checker that knows nothing about CCDI. With namespace-aware keys it now reproduces the census pipeline exactly on 153,580 real records: every pair, every over-count figure and every agreement table, for all 12 source pairs. That also confirms the diagnosis of the failed first reproduction (../linkcheck-repro-v1/, grade of record still **fail**). Its only cause was the 87 shared ids, and keying by namespace removes it. P5 is the first graded check of the stage-2 Treehouse finding by code other than the stage-2 script. It holds: the looser rules add exactly the 1,094 alternate-id pairs, nothing else, and the same small number of disagreements.

No link was counted as `ambiguous_id`. As the pre-registration expected, every Participant Index link into CCDI-DCC names a study namespace, so the 87 shared ids never made a link end ambiguous.

## 3. Descriptive only: the 87 shared CCDI-DCC names

Not pre-registered beyond S1. On the kept second snapshot:

- 87 names are each served by exactly two CCDI-DCC records (174 records). The two records are always in different study namespaces (8 namespaces in all), never in the same one (`same_namespace_name` 0). 41 of the 87 names are USI-shaped (P + five capital letters).
- The two records of each pair compare, by the census's own rules, as follows:

| Field | Agree | Disagree | Not comparable (one or both missing) |
|---|---|---|---|
| Sex | 87 | 0 | 0 |
| Race | 55 | 0 (no partial overlaps either) | 32 |
| Ethnicity | 20 | 0 | 67 |
| Vital status | 31 (7 both alive, 24 both dead) | 0 | 56 |
| Age at death (both dead) | 24 within 1 day | 0 | n/a |

For comparison, pairs matched by chance disagree on sex about half the time (diagnostics-v2). Zero disagreements in 87 pairs, with 24 of 24 ages at death matching within a day, **suggests** that most or all of these pairs are one child enrolled in two CCDI studies, served once per study. It does not prove it: we cannot see, in aggregate, whether the 46 names that are not USI-shaped behave like the 41 that are. The census counts each pair as two subjects unless its cross-source links happen to join them. If they are one child each, its de-duplicated count is too high by up to 87 (0.06% of 135,849). That is small, but anyone counting CCDI-DCC participants by served record inherits it. The follow-up job splits the agreement by name shape and counts how many pairs the census's links already join. Neither the data owners nor anyone else has been contacted.

## 4. Descriptive only: other numbers from the same run

- **Adapter:** 150,161 link rows from 153,680 Participant Index entries: 134,265 organizational-identifier associations and 21,567 USI associations, 6,589 of which name a USI no subject serves. 87,988 associations of other categories were skipped, by the census's rule.
- **LinkCheck link resolution (exact rule first):**
  - 20,496 new cross-source pairs;
  - 4,826 links to pairs already made;
  - 10,062 self-references;
  - 384 links within one source;
  - 1,094 new pairs by `alt_id` (and 3 more within one source);
  - 3,728 links by `suffix`, all to pairs already made;
  - 109,568 unresolved. Most of these name domains the federation does not serve, such as dbGaP subject ids (74,120 in the census's own count), cBioPortal and GDC.
- **Within-source multiplicity:** 404 de-duplicated persons hold two or more records of one source with exact links (410 with the looser rules). LinkCheck reports the 87 shared ids as `shared_ids: CCDI-DCC 87 ids, 174 records`.
- **Paging audits on snapshot 2:** identical to the graded paging audit ([../paging-audit-v1/results.md](../paging-audit-v1/results.md)). On `/subject`, PCDC's error pages 12 and 35 lose 200 records. On `/subject-mapping`, PCDC's page 35 is silently short by 100. Nothing is unexplained.

## 5. Limits

- One snapshot (the kept second one), one job, one model family (Claude) wrote and graded it, and no human has checked it.
- P1-P4 show that two pieces of code agree on the same data. They do not show that either one models the federation correctly. The earlier census grades and diagnostics speak to that.
- F1 was not tested. Until it is, the robust fetcher's behaviour on live data is unknown beyond its made-up-data tests.
- Section 3 is descriptive and post hoc. Agreement does not prove identity.

## Files

- `out/repro2.json`: the job's output.
- `logs/stdout.txt`, `logs/stderr.txt`: the job's full log (SHA-256 of the downloaded code, test output).
- `logs/summary.json`: the runner's record of the job (machine, times, steps, exit codes).
