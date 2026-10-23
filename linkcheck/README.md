# LinkCheck 0.1.0

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research and data-quality software only: it is not medical advice and makes no clinical decisions.

When one person has records in several sources and a linkage index says which records belong together, pooling them is safe only if each person is counted once, the fields are present, and the linked records agree. LinkCheck measures those three things and builds a cohort table that keeps every conflict visible instead of silently picking a value.

It grew out of MV2's pre-registered census of NCI's Childhood Cancer Data Initiative federation ([ccdi/concordance-v1](../ccdi/concordance-v1/), tag v0.5.5) and its post-hoc link diagnostics ([ccdi/diagnostics-v2](../ccdi/diagnostics-v2/), tag v0.5.10). It uses the same comparison rules, but works on any sources.

## What it reports

1. **Link resolution.** Every link is resolved in two passes. Pass 1 uses exact ids only. Pass 2 retries the rest with the chosen looser rules:
   - `alt_id`: the id is one that exactly one record of that source serves as an alternate id;
   - `suffix`: the part of the id after its last underscore (for example `COG_<id>`) is a record id in that source.

   Each link is counted by rule and outcome: `new_pair`, `already_linked` (the pair is already made by another link), `self_reference` (both ends are the same record), `same_source` (both ends are in one source) or `unresolved` (`ambiguous_alt_id` when two records serve the same alternate id). A looser rule never claims a pair that an exact link makes, so the result does not depend on link order.
2. **Completeness**, per source: records, repeated records, and how many carry an informative value for sex, race, ethnicity, vital status and age at vital status.
3. **Conflicts**, per source pair and overall, for exact links and with the rules: agree / disagree / uninformative for sex and ethnicity; agree / overlap / disagree for race (OMB 1997 categories); for vital status, both alive, both dead, alive then dead, alive after death (a record says alive at an age more than a day after another says dead), or alive-versus-dead without ages; plus agreement of age at death. **An unknown or missing value is never counted as a conflict.**
4. **Over-count**: linked records are joined into persons, and the report gives persons, linked persons, the naive over-count (records minus persons), persons with two or more records in one source, and the largest person, for exact links and with the rules.
5. **Cohort table** (optional, person-level): one row per person, with each field resolved by a stated rule and a conflict flag:
   - `sex`, `race`, `ethnicity`: the single informative value, or `conflict`;
   - `vital_consensus`: the single informative value, or `conflict`;
   - `vital_latest`: death is final, so Dead wins unless a record says Alive at an age more than one day after the latest age at death, which gives `conflict`;
   - `vital_priority`: the first informative value in a source order you state.

   An analysis can then report its estimate under each rule, or exclude conflicted persons, and show how much the choice moves the result. Ethnicity is shown as `H` / `NH`.

The report holds counts only, never record ids. `--min-cell N` shows every count from 1 to N-1 as `<N`. The cohort table lists record ids, so keep it as private as the input data.

## Use

Standard library only, Python 3.9 or later.

```
python -m linkcheck --records examples/records.jsonl --links examples/links.jsonl \
    --out report.json --cohort cohort.csv --priority B,A --min-cell 11
```

- `--records`: JSON Lines, one record per line: `source`, `id` (required), `alt_ids` (list), `sex`, `race` (string or list), `ethnicity`, `vital_status`, `age_at_vital_status` (days, number).
- `--links`: JSON Lines: `a_source`, `a_id`, `b_source`, `b_id`.
- `--rules`: default `exact,alt_id,suffix`. Use `--rules exact` for a literal join.

Source names and ids are matched exactly (case-sensitive), so normalise them first. Values are normalised case-insensitively: Male/M, Female/F; Alive/Living, Dead/Deceased; Hispanic or Latino / Not Hispanic or Latino; the five OMB 1997 race categories. Anything else, including "Unknown" and "Not reported", counts as no value.

`examples/example-report.json` is the report for the made-up example above (`--priority B,A --min-cell 0`).

## Tests

```
python -m unittest -v test_linkcheck
```

The tests use only the made-up records in `examples/`. Every expected number was worked out by hand before the first run. **All 14 passed** in the sealed job `linkcheck-test-v1` (Python 3.12, no network, 2026-10-23 12:12 UTC), which also produced `examples/example-report.json`.

## Related tools

Record-linkage libraries such as [Splink](https://moj-analytical-services.github.io/splink/index.html), [dedupe](https://github.com/dedupeio/dedupe) and the [Python Record Linkage Toolkit](https://github.com/jpweytjens/recordlinkage) *make* links. Data-fusion frameworks such as PyDI ([arXiv 2603.10547](https://arxiv.org/pdf/2603.10547)) and ODCS-FusionTool ([arXiv 1410.7990](https://arxiv.org/pdf/1410.7990)) resolve conflicting values with chosen functions. LinkCheck does neither. It *audits* links that already exist: what each resolution rule adds, how complete each source is, how often linked records disagree (with unknown values kept apart from conflicts, and vital status compared by age), and how much pooling over-counts. Its cohort table carries conflicts forward instead of resolving them away. A 2026-10-23 web search found no tool that reports these things for an existing linkage index, but the search was short, and generic data-fusion tools overlap with the cohort table.

## Limits

- Version 0.1.0 is a first prototype and has so far run only on made-up records. Its first real-data check is pre-registered in [ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/) (published with this version, before the check ran): on the CCDI federation snapshot it must reproduce the census code's pairs, over-count and agreement tables exactly, and its looser rules must reproduce the stage-2 Treehouse finding (20,496 exact pairs; naive over-count 17,731, rising to 18,536 with Treehouse alternate ids). Until those results are published, treat the tool as untested on real data.
- The race comparison uses the 1997 OMB categories, as the census did. OMB's 2024 combined race/ethnicity standard is not yet supported.
- Alive-versus-dead logic assumes ages at vital status are measured from the same reference point in every source. The CCDI diagnostics found one source where they are not, so check that before trusting `alive_after_death`.
