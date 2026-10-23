# LinkCheck 0.2.0

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research and data-quality software only: it is not medical advice and makes no clinical decisions.

When one person has records in several sources and a linkage index says which records belong together, pooling them is safe only if each person is counted once, the fields are present, and the linked records agree. LinkCheck measures those three things and builds a cohort table that keeps every conflict visible instead of silently picking a value. Since 0.2.0 it can also audit the paged endpoints the records come from, so that records lost in transit are found before the analysis starts.

It grew out of MV2's pre-registered census of NCI's Childhood Cancer Data Initiative federation ([ccdi/concordance-v1](../ccdi/concordance-v1/), tag v0.5.5) and its post-hoc diagnostics ([ccdi/diagnostics-v2](../ccdi/diagnostics-v2/), tag v0.5.10; [ccdi/diagnostics-v3](../ccdi/diagnostics-v3/), tag v0.5.12). It uses the same comparison rules, but works on any sources.

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
6. **Paging audit** (new in 0.2.0, `linkcheck/paging.py`). Some endpoints serve several sources side by side: page p of the response holds page p of every source. A source can then lose entries in two ways: its part of a page is an error object, or the page is just shorter than it should be, with no error. The CCDI diagnostics found both on one federation; a client that checks only for errors misses the second. The audit counts entries per source on every page, and compares each page with what the source's total says it should hold: min(per_page, max(0, T - (p - 1) x per_page)) on page p for a source with total T. Without a total, every page before the source's last page with entries should be full. It reports:
   - **loss flags**: error pages, short pages and over-full pages where entries were expected;
   - **errors past a source's end**, counted apart (some servers answer an exhausted source with an error object; nothing is lost there);
   - page numbers missing from the walk, and pages that failed as a whole;
   - per source: served, total, entries lost by kind (error pages, short pages, missing pages, pages not walked), excess, and what is left **unexplained**. A non-zero unexplained count means the losses are somewhere the flags do not show.

The reports hold counts only, never record ids. `--min-cell N` shows every count in the linkage report from 1 to N-1 as `<N`. The cohort table lists record ids, so keep it as private as the input data.

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

The paging audit:

```
python -m linkcheck.paging --pages pages.jsonl --per-page 100 --totals totals.json --out paging.json
```

- `--pages`: JSON Lines, one line per page walked: `{"page": 35, "counts": {"A": 100, "B": 0, "C": null}}`. A count is the number of entries the source had on that page; `null` means the source's part of the page was an error object; a source left out has 0 entries; `"counts": null` means the whole page failed.
- `--totals` (optional): a JSON object `{"A": 24432, ...}`, for example from a summary endpoint.
- `--per-page`: the page size the walk asked for.

From Python: `from linkcheck import paging; paging.audit({1: {"A": 100}, 2: {"A": None}}, 100, {"A": 150})`.

## Tests

```
python -m unittest -v test_linkcheck test_paging
```

The tests use only made-up data: the records in `examples/` and the page counts in `test_paging.py`. Every expected number was worked out by hand before the first run. The 14 tests of `test_linkcheck` passed in a sealed job for 0.1.0 (`linkcheck-test-v1`); `test_paging` first runs in the sealed job `ccdi-paging-v1`.

## Checks on real data

- [ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/) (pre-registered at tag v0.6.0): does LinkCheck 0.1.0 reproduce the CCDI census on the same snapshot? Pending.
- [ccdi/paging-audit-v1](../ccdi/paging-audit-v1/) (pre-registered at tag v0.7.0): a paging audit of every saved page of both CCDI endpoints, with six predictions. Pending.

## Related tools

Record-linkage libraries such as [Splink](https://moj-analytical-services.github.io/splink/index.html), [dedupe](https://github.com/dedupeio/dedupe) and the [Python Record Linkage Toolkit](https://github.com/jpweytjens/recordlinkage) *make* links. Data-fusion frameworks such as PyDI ([arXiv 2603.10547](https://arxiv.org/pdf/2603.10547)) and ODCS-FusionTool ([arXiv 1410.7990](https://arxiv.org/pdf/1410.7990)) resolve conflicting values with chosen functions. LinkCheck does neither. It *audits* links that already exist: what each resolution rule adds, how complete each source is, how often linked records disagree (with unknown values kept apart from conflicts, and vital status compared by age), and how much pooling over-counts. Its cohort table carries conflicts forward instead of resolving them away. A 2026-10-23 web search found no tool that reports these things for an existing linkage index, but the search was short, and generic data-fusion tools overlap with the cohort table.

For paging, generic checkers such as [pagination-integrity-check](https://github.com/chenhz01/pagination-integrity-check) reconcile saved page responses for missing or duplicate pages, overlapping ids and broken cursor chains. LinkCheck's paging audit is narrower. It works per source, for endpoints where one response carries every source's page. It works out what each page should hold from each source's total, and it keeps three cases apart: error objects, silent short pages, and errors past a source's end.

## Limits

- Version 0.2.0 is a prototype. The linkage report has not yet been checked on real CCDI data, and the paging audit has run only on made-up pages (see "Checks on real data").
- The race comparison uses the 1997 OMB categories, as the census did. OMB's 2024 combined race/ethnicity standard is not yet supported.
- Alive-versus-dead logic assumes ages at vital status are measured from the same reference point in every source. The CCDI diagnostics found one source where they are not, so check that before trusting `alive_after_death`.
- The paging audit counts entries; it does not compare them. A page that holds the right number of entries but the wrong ones (for example, records repeated from another page because the order changed during the walk) is not flagged. It also assumes each source's pages are filled in order, so only a source's last page can be partly full.
