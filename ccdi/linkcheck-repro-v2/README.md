# Pre-registration: does LinkCheck 0.3.0 reproduce the CCDI census, and does a fresh snapshot reach the end?

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Status: PRE-REGISTERED.** This page, the code and the predictions below are published at evidence-pack tag **v0.8.0** before the sealed job `linkcheck-repro-v2` runs. The job downloads its code from that tag and waits until the tag is public, so it cannot run code that differs from what is published here. Results will be added as `results.md` in a later tag and graded against the predictions exactly as written.

## Why

The first reproduction ([../linkcheck-repro-v1/results.md](../linkcheck-repro-v1/results.md)) failed P1-P4, all for one reason. LinkCheck 0.1.0 keyed records by (source, id), and 87 CCDI-DCC records share their id with a record in another namespace. [LinkCheck 0.3.0](../../linkcheck/) keys a record by (source, id, namespace) when the record names one. A link end that names a namespace resolves to that record only. A link end without one resolves only if exactly one record of the source has the id; otherwise it is counted as `ambiguous_id`, not guessed.

The same job also showed a second problem: a fresh snapshot can be cut short without any error. Page 345 of `/subject-mapping` came back empty with HTTP 200 for a moment, and the census's fetcher, which walks until a page is empty, stopped there. 29,435 Participant Index entries were never fetched, and the census code on that snapshot found 72% fewer cross-source pairs. That snapshot was also lost when the job ended. This job fixes both: `fetch_robust.py` walks every page the largest source's total needs and fetches an empty page again, and the snapshot is kept on the machine's data volume.

## What the job does

1. Downloads, unchanged, and logs SHA-256 (`get_code.py`): `analyze.py` and `fetch_ccdi.py` from tag v0.5.5; `ccdi_pages.py` (the paging-audit reader) from tag v0.7.0; LinkCheck 0.3.0 and this folder from tag v0.8.0.
2. Runs LinkCheck's tests (`test_linkcheck`, `test_paging`, the new `test_namespaces`) and this folder's `test_repro2`. All use made-up data only, and every expected number was worked out by hand.
3. `ensure_snapshot2.py` picks the snapshot to read:
   - the kept second snapshot (2026-10-22 21:11 to 2026-10-23 00:36 UTC), if the machine holds it;
   - else the newest complete fresh snapshot an earlier job kept under `/data/ccdi-raw-fresh-<UTC time>`;
   - else it takes one now with `fetch_robust.py`, which keeps it there (about 3.5 hours).

   `fetch_robust.py` runs the census fetcher's own code with two changes. Both walks go on to the page after the last one the largest source's total needs. A page before that which comes back empty with HTTP 200 is fetched again, up to 3 times, after waits of 1, 2 and 3 minutes. Every attempt is logged. A page where only some sources return an error object is not retried, because that is what the audit measures.
4. `repro2.py`:
   - **`adapt()`** turns the snapshot into LinkCheck input. Each served subject becomes one record with its namespace. Each Participant Index association becomes one link row, kept by the census's rules (a USI association becomes one row per subject serving that USI; any other association counts only if its category is `organizational_identifier`). A domain name that is a namespace name becomes that source and namespace. A source name becomes that source with no namespace. `adapt()` resolves nothing; LinkCheck does.
   - Runs the census code (`fed_indexes`, `mapping_links`, `section_c`, `section_d`) and LinkCheck (rules exact, alt_id, suffix) on the same data.
   - Runs LinkCheck's paging audit on both endpoints of the snapshot used.
   - Describes the subjects of one source that share a name: groups, group sizes, how many differ only by organization, how many names are USIs, how many namespaces are involved, and how their sex, ethnicity, race and vital status compare.
5. Writes `out/repro2.json`: grades, adapter counts, census link counts, the shared-name summary, both paging audits and the full LinkCheck report. Counts, page numbers and source names only; no participant IDs.

## Predictions

P1-P4 compare LinkCheck with the census code **on the same snapshot**, so they are graded whichever snapshot is used. P5, P6 and S1 use numbers of the second snapshot and are graded only on it. F1 is graded only on a fresh snapshot taken by `fetch_robust.py`.

| | Prediction | Pass if |
|---|---|---|
| P1 | Every served subject becomes exactly one LinkCheck record. | LinkCheck's record count equals the census's subject count, and no (source, id, namespace) repeats. |
| P2 | LinkCheck's exact links make exactly the census's cross-source pairs. | The two pair sets are identical (pairs written as LinkCheck record keys), and the counts match. |
| P3 | Same over-count with exact links. | De-duplicated persons, naive over-count, linked persons and records in links all equal the census's section D. |
| P4 | Same agreement tables with exact links. | LinkCheck's sex, race, ethnicity, vital-status and age-at-death tallies equal the census's section C, overall and for every source pair. |
| P5 | The looser rules reproduce stage 2's Treehouse finding and add nothing else (unchanged from v1, never graded). | Pairs added: `{"alt_id": 1094}` only; 21,590 pairs in all; with the rules, 135,044 persons, over-count 18,536, 15,403 linked persons, 33,939 records in links; the added pairs raise sex disagreements by exactly 3, ethnicity by 2 and race by 0. |
| P6 | The absolute exact-link counts of the second snapshot (unchanged from v1, never graded). | 153,580 records; 20,496 pairs; 135,849 persons; over-count 17,731; 14,847 linked persons; 32,578 records in links. |
| S1 | The second snapshot has the same shared CCDI-DCC names as the third. | Subjects that share a name with another subject of the same source: exactly 87 extra records (group size minus one, summed), all in CCDI-DCC, none in any other source. |
| F1 | A fresh snapshot taken by `fetch_robust.py` reaches the end of both endpoints. | On both `/subject` and `/subject-mapping`: no missing page numbers, and for every source with a summary total, 0 entries on pages not walked and 0 unexplained. |

### Where a miss would most likely come from

- **P1:** two subjects of one source with the same name and the same namespace name but different organizations. The census keeps both, while LinkCheck's key has no organization. The shared-name summary counts such groups (`same_namespace_name`), so a miss would show its cause.
- **P2-P4:** a link whose domain is a source name, not a namespace, and whose id is one of the shared names. The census takes the first such subject; LinkCheck counts the link as ambiguous. In snapshot 3, CCDI-DCC's Participant Index entries used study namespaces as domain names, so we expect no such links. A domain name that is both a source name and a namespace name could also differ.
- **P5:** as in v1. LinkCheck applies the looser rules to both ends of a link and to every source, while stage 2 applied them to the linked-to side only.
- **S1:** CCDI-DCC changing between the two snapshots (about 15 hours apart). Both served all 59,795 of its subjects.
- **F1:** an outage longer than the retries (about 6 minutes) would leave a page empty. The audit would then flag it as short, with nothing unexplained, and F1 could still pass; the result will say so.

A failed prediction is reported as a failure, with the observed values; the grade on record stays.

## Not pre-registered (reported as descriptive only)

The shared-name summary (beyond S1), both paging audits on the second snapshot (already graded in ../paging-audit-v1/), the fetcher's retries, LinkCheck's completeness table, its link-resolution counts and its cohort summary.

Whether the shared names are one child in two studies is a question the data can only hint at: same USI-shaped name, and agreement of sex, race and ethnicity. Agreement does not prove identity, and the result will not claim it.

## Files

- `repro2.py`, `test_repro2.py`, `ensure_snapshot2.py`, `fetch_robust.py`: the code the job downloads.
- `get_code.py`, `job.json`: the job's setup (`job.json` shows the job as filed: 1 CPU, 2 GB, network on, up to 6 hours).
