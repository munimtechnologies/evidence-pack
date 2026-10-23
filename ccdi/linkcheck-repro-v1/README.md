# Pre-registration: does LinkCheck reproduce the CCDI census on real data?

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Status: PRE-REGISTERED.** This page, the code and the predictions below are published at evidence-pack tag **v0.6.0** before the sealed job `linkcheck-repro-v1` runs. The job downloads its code from that tag (it waits until the tag is public), so it cannot run code that differs from what is published here. Results will be added as `results.md` in a later tag, graded against the predictions exactly as written.

## Why

[LinkCheck 0.1.0](../../linkcheck/) is a general tool: given records from several sources and a linkage index, it reports link resolution, per-source completeness, conflicts between linked records, and how much pooling over-counts. It was built from MV2's pre-registered CCDI census ([../concordance-v1/](../concordance-v1/), tag v0.5.5) and its post-hoc link diagnostics ([../diagnostics-v2/](../diagnostics-v2/), tag v0.5.10). So far it has run only on 10 made-up records. Before anyone relies on it, it should reproduce the census on the real data, independently: the census resolves links in its own code, and LinkCheck must get the same answer from a plain list of records and links.

## What the job does

1. Downloads `analyze.py` and `fetch_ccdi.py` from tag v0.5.5, and LinkCheck plus this folder from tag v0.6.0, unchanged, logging SHA-256 (`get_code.py`).
2. Runs `test_repro.py` (7 tests on a made-up snapshot; every expected number worked out by hand).
3. Uses the kept second snapshot of the CCDI Data Federation (2026-10-22 21:11 to 2026-10-23 00:36 UTC). If the machine running the job does not hold it, `ensure_snapshot.py` takes a fresh snapshot with the census's own `fetch_ccdi.py` (about 3.5 hours).
4. `repro.py`:
   - **`adapt()`** turns the snapshot into LinkCheck input. Each served subject becomes one record (source, name, alternate ids, and the raw sex, race, ethnicity, vital status and age values). Each Participant Index association becomes one link row, following the census's rules: a USI association becomes one row per subject that serves that USI; any other association counts only if its category is `organizational_identifier`. Domain names map to sources as in the census: case-insensitively, by source or namespace name. `adapt()` resolves nothing; LinkCheck does.
   - Runs the census code (`fed_indexes`, `mapping_links`, `section_c`, `section_d`) and LinkCheck (all three rules: exact, alt_id, suffix) on the same data, and grades the predictions.
5. Writes `out/repro.json`: grades, the adapter's counts, the census's link counts and the full LinkCheck report. Counts only, no participant IDs.

## Predictions

P1-P4 compare LinkCheck with the census code **run on the same snapshot**, so they hold whichever snapshot is used. P5-P6 use the numbers already published for the second snapshot, and are graded only if the job used it.

| | Prediction | Pass if |
|---|---|---|
| P1 | Every served subject becomes exactly one LinkCheck record. | LinkCheck's record count equals the census's subject count, and no (source, name) repeats. |
| P2 | LinkCheck's exact links make exactly the census's cross-source pairs. | The two pair sets are identical (pairs written as (source, name)), and the counts match. |
| P3 | Same over-count with exact links. | De-duplicated persons, naive over-count, linked persons and records in links all equal the census's section D. |
| P4 | Same agreement tables with exact links. | LinkCheck's sex, race, ethnicity, vital-status and age-at-death tallies equal the census's section C, overall and for every source pair. |
| P5 | The looser rules reproduce stage 2's Treehouse finding and add nothing else. | Pairs added: `{"alt_id": 1094}` only; 21,590 pairs in all; with the rules, 135,044 persons, over-count 18,536, 15,403 linked persons, 33,939 records in links; the added pairs raise sex disagreements by exactly 3, ethnicity by 2 and race by 0. |
| P6 | The absolute exact-link counts of the second snapshot. | 153,580 records; 20,496 pairs; 135,849 persons; over-count 17,731; 14,847 linked persons; 32,578 records in links. |

### Where a miss would most likely come from

- **P1:** two subjects of one source with the same name in different namespaces. The census keeps both; LinkCheck keys records by (source, id) and keeps the first.
- **P5:** LinkCheck also applies the looser rules to the *linking* side of an association, and to every source; stage 2 applied them to the linked-to side only. Any pair this adds, for example from the 100 Index entries whose own subject was not served, fails P5. The PCDC `COG_<USI>` links should resolve by the suffix rule only to pairs already made (stage 2: all 3,728), and the 148 ccdi-ecDNA self-references and 1,364 KidsFirst links should stay unresolved, because LinkCheck has no rule that looks a name up in a different source.

A failed prediction is reported as a failure, with the observed values; the tool may then be fixed, but the grade of record stays.

## Not pre-registered (reported as descriptive only)

The report also holds LinkCheck's completeness table, its link-resolution counts by rule and outcome, and its cohort summary (vital status by consensus, latest and source priority CCDI-DCC then KidsFirst). These are descriptive. The `vital_latest` rule compares ages across sources, and ccdi-ecDNA's ages refer to an earlier time point (diagnostics stage 1), so its counts involving ccdi-ecDNA should not be read as contradictions.

## Files

- `repro.py`, `test_repro.py`, `ensure_snapshot.py`: the code the job downloads.
- `get_code.py`, `job.json`: the job's setup (`job.json` shows the job as filed: 1 CPU, 2 GB, network on, up to 6 hours).
