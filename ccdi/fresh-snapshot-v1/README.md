# Pre-registration: does a fresh CCDI snapshot reach the end, and are the 87 shared CCDI-DCC ids one child each?

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written on 2026-10-23 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice.

**Status: PRE-REGISTERED.** This page, `fresh1.py` and the predictions below are published at evidence-pack tag **v0.8.2** before the sealed job `ccdi-fresh-v1` runs. The job downloads its code from tags v0.5.5, v0.7.0, v0.8.0 and v0.8.2 and waits until v0.8.2 is public, so it cannot run code that differs from what is published. Results will be added as `results.md` in a later tag and graded exactly as written.

## Why

The second LinkCheck reproduction ([../linkcheck-repro-v2/results.md](../linkcheck-repro-v2/results.md), tag v0.8.1) held all seven predictions it could grade. It ran on the kept second snapshot, though, so **F1**, the test of the new fetcher `fetch_robust.py`, was never graded. F1 asks whether a fresh snapshot reaches the end of both endpoints. That matters because the third snapshot was cut short without any error when one page came back empty for a moment.

That job also described the 87 pairs of CCDI-DCC records that share a name across two study namespaces. Their sex agreed in 87 of 87 pairs. Race and ethnicity agreed wherever both records gave one, and the 24 pairs where both records say the child died agree on age at death within one day. 41 of the 87 names are USI-shaped. The census counts each pair as two people unless its cross-source links happen to join them. This job asks two things post hoc. Does the agreement also hold for the 46 names that are not USI-shaped? And how many of the pairs do the census's links already join into one person?

## What the job does

1. `get_code.py` downloads every file unchanged and logs SHA-256.
2. It runs the tests of LinkCheck, `test_repro2` and the new `test_fresh1`, all on made-up data, with every expected number worked out by hand.
3. `ensure_snapshot2.py /data/no-kept-snapshot /data/ccdi-fresh-v1` finds no kept snapshot in that folder, so `fetch_robust.py` takes a fresh one into `/data/ccdi-fresh-v1/ccdi-raw-fresh-<UTC time>` (about 3 to 3.5 hours). The snapshot stays on the machine's data volume.
4. `repro2.py` (v0.8.0, unchanged) runs on that fresh snapshot. It grades **P1-P4 and F1 exactly as pre-registered at v0.8.0**. P5, P6 and S1 are not graded there, because they belong to the second snapshot.
5. `fresh1.py` (this folder) grades G1-G3 below on the fresh snapshot. It then writes the description below for the fresh snapshot, and also for the kept second snapshot if the machine holds it (only the Blade does).

## Predictions (fresh snapshot only)

| | Prediction | Pass if |
|---|---|---|
| G1 | The federation's sources still hold the same number of subjects as in the second snapshot (2026-10-22/23). | `/subject/summary` totals equal, for exactly these seven sources: CCDI-DCC 59,795; KidsFirst 38,440; PCDC 24,432; StJude 14,681; Treehouse 12,723; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504. |
| G2 | The shared names replicate. | Subjects that share a name with another subject of the same source: 87 groups, all of size 2, 87 extra records, all in CCDI-DCC, and no group with the same namespace name twice. |
| G3 | The two records of a shared name never contradict each other, whether the name is USI-shaped or not. | Both name shapes occur. In neither shape does any pair disagree on sex or ethnicity, disagree or only overlap on race, say alive at an age after the other record's death (or alive vs dead without ages), or give ages at death more than 1 day apart. |

Grading F1, P1-P4 (from v0.8.0) and G1-G3 is mechanical. A miss is reported as a miss with the observed values, and the grade on record stays.

**What is already known.** G2 and the overall form of G3 held on the second snapshot. G2 also showed up in the third snapshot. So these are replications on a third, independent fetch. The split by name shape is new. G1 and F1 are the real tests. G1 would fail if any source released data between the snapshots, and that is possible: the second snapshot will be about a day older than this job's.

### Where a miss would most likely come from

- **F1:** an outage longer than the fetcher's retries (about 6 minutes), or an empty page past the point where the walk is allowed to stop. Either one would show up in `retries.json` and in the paging audit.
- **G1, G2:** a data release by one source between the snapshots.
- **G3:** a non-USI name shared by two different children in two studies. A short, sequential study ID could do that.

## Not pre-registered (descriptive only)

- How the census's own cross-source links treat each shared pair. Either the links already join both records into one person, or both records are linked but to different persons, or only one is in a link, or neither is.
- The census's de-duplicated person count, next to the count if each shared name were one person.
- The study-namespace pairs involved (public dbGaP accessions).
- The agreement tables by name shape.
- The fetcher's retries.
- The same description on the kept second snapshot.

Agreement does not prove identity. The result may say the pairs *suggest* one child enrolled in two studies; it will not claim it, and the data owners have not been asked.

## Files

- `fresh1.py`, `test_fresh1.py`: this job's analysis and tests.
- `get_code.py`, `job.json`: the job as filed (1 CPU, 2 GB, network on, up to 6 hours, data volume `ccdi-raw`).
