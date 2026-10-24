# LinkCheck 0.3.1

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research and data-quality software only: it is not medical advice and makes no clinical decisions.

When one person has records in several sources and a linkage index says which records belong together, pooling them is safe only if each person is counted once, the fields are present, and the linked records agree. LinkCheck measures those three things and builds a cohort table that keeps every conflict visible instead of silently picking a value. It can also audit the paged endpoints the records come from (since 0.2.0), so that records lost in transit are found before the analysis starts.

It grew out of MV2's pre-registered census of NCI's Childhood Cancer Data Initiative federation ([ccdi/concordance-v1](../ccdi/concordance-v1/), tag v0.5.5) and its post-hoc diagnostics ([ccdi/diagnostics-v2](../ccdi/diagnostics-v2/), tag v0.5.10; [ccdi/diagnostics-v3](../ccdi/diagnostics-v3/), tag v0.5.12). It uses the same comparison rules, but works on any sources.

## New in 0.3.1: no entries is not the end

Reading the CCDI aggregation code and probing the live endpoint ([ccdi/aggregator-reading-v1](../ccdi/aggregator-reading-v1/), tag v0.8.4) showed that a failed upstream call there comes back as HTTP 200 with a small error object and no entries, and that no `link` header tells a client where the last page is. A client that stops at the first page without entries stops early whenever that happens. 0.3.1 adds to `linkcheck/paging.py`:

- `last_page(totals, per_page)`: the last page a walk must reach, from the largest source total.
- `refetch_pages(pages, per_page, totals)`: the pages up to that page that were never walked, failed as a whole, or hold no entries from any source. Fetch them again instead of stopping.
- With totals, the audit report now also gives `required_last_page` and `refetch_pages`, and the command line prints `refetch_pages`.
- `body_counts(body)`: the per-source counts of one page, from its parsed JSON body (a list of `{"source": ..., "data": [...]}` items; an item without a `data` list counts as an error; an object with an `errors` list is a page that failed as a whole). Other shapes are rejected, never guessed. The key names can be changed.
- `error_messages(body)`: every error the body carries, as `kind: message`.

Nothing else changed. The 0.3.0 report keys and every earlier test are kept unchanged. The new tests (`test_paging_body.py`, 12 tests) and a pre-registered check on the saved CCDI pages ([ccdi/linkcheck-031-check-v1](../ccdi/linkcheck-031-check-v1/), tag v0.8.5) run for the first time in the sealed job `linkcheck-031-v1`.

## New in 0.3.0: namespaces

The first check on real data failed ([ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/results.md)). LinkCheck keyed records by (source, id), but 87 records of one CCDI source share their id with a record in another namespace (study) of the same source, and LinkCheck silently kept only the first. 0.3.0 fixes this:

- A record may name its `namespace`. It is then keyed by (source, id, namespace), so two namespaces of one source can serve the same id.
- A link end may name its namespace (`a_namespace`, `b_namespace`) and then resolves to that record only. A link end without one resolves only if exactly one record of the source has that id. Otherwise it is counted as `unresolved: ambiguous_id` and never guessed.
- The report has a new `shared_ids` section: per source, the ids that two or more namespaces serve, and how many records serve them.
- Input without namespaces gives the same report as 0.2.0, apart from the version and the new (empty) `shared_ids` section.

## What it reports

1. **Link resolution.** Every link is resolved in two passes. Pass 1 uses exact ids only. Pass 2 retries the rest with the chosen looser rules:
   - `alt_id`: the id is one that exactly one record of that source serves as an alternate id;
   - `suffix`: the part of the id after its last underscore (for example `COG_<id>`) is the id of exactly one record in that source.

   Each link is counted by rule and outcome: `new_pair`, `already_linked` (another link already makes the pair), `self_reference` (both ends are the same record), `same_source` (both ends are in one source) or `unresolved`. Unresolved links are split into `ambiguous_id` (two namespaces serve the id and the link names neither), `ambiguous_alt_id` (two records serve the same alternate id) and plain `unresolved`. A looser rule never claims a pair that an exact link makes, so the result does not depend on link order.
2. **Completeness**, per source: records, repeated records, and how many carry an informative value for sex, race, ethnicity, vital status and age at vital status. Also **shared ids**, per source.
3. **Conflicts**, per source pair and overall, for exact links and with the rules:
   - sex and ethnicity: agree / disagree / uninformative;
   - race (OMB 1997 categories): agree / overlap / disagree;
   - vital status: both alive, both dead, alive then dead, alive after death (a record says alive at an age more than a day after another says dead), or alive-versus-dead without ages;
   - agreement of age at death.

   **An unknown or missing value is never counted as a conflict.**
4. **Over-count**: linked records are joined into persons. For exact links and with the rules, the report gives persons, linked persons, the naive over-count (records minus persons), persons with two or more records in one source, and the largest person.
5. **Cohort table** (optional, person-level): one row per person, with each field resolved by a stated rule and a conflict flag:
   - `sex`, `race`, `ethnicity`: the single informative value, or `conflict`;
   - `vital_consensus`: the single informative value, or `conflict`;
   - `vital_latest`: death is final, so Dead wins, unless a record says Alive at an age more than one day after the latest age at death, which gives `conflict`;
   - `vital_priority`: the first informative value in a source order you state.

   An analysis can then report its estimate under each rule, or exclude conflicted persons, and show how much the choice moves the result. Ethnicity is shown as `H` / `NH`.
6. **Paging audit** (`linkcheck/paging.py`). Some endpoints serve several sources side by side: page p of the response holds page p of every source. A source can then lose entries in two ways: its part of a page is an error object, or the page is just shorter than it should be, with no error. The CCDI diagnostics found both on one federation. The audit counts entries per source on every page, and compares each page with what the source's total says it should hold: min(per_page, max(0, T - (p - 1) x per_page)) on page p, for a source with total T. Without a total, every page before the source's last page with entries should be full. It reports:
   - **loss flags**: error pages, short pages and over-full pages where entries were expected;
   - **errors past a source's end**, counted apart (some servers answer an exhausted source with an error object; nothing is lost there);
   - page numbers missing from the walk, and pages that failed as a whole;
   - per source: served, total, entries lost by kind (error pages, short pages, missing pages, **pages not walked**), excess, and what is left **unexplained**. A non-zero unexplained count means the losses are somewhere the flags do not show;
   - with totals (0.3.1): the **last page the walk had to reach** and the **pages to fetch again**.

   "Pages not walked" catches a walk that stopped early. One CCDI snapshot lost 29,435 entries that way. By its byte count, the page that stopped it was most likely the aggregator's fixed "Server Error." object, served with HTTP 200 (see [ccdi/aggregator-reading-v1](../ccdi/aggregator-reading-v1/)).

The reports hold counts only, never record ids. `--min-cell N` shows every count in the linkage report from 1 to N-1 as `<N`. The cohort table lists record ids, so keep it as private as the input data.

## Use

Standard library only, Python 3.9 or later.

```
python -m linkcheck --records examples/records.jsonl --links examples/links.jsonl \
    --out report.json --cohort cohort.csv --priority B,A --min-cell 11
```

- `--records`: JSON Lines, one record per line: `source`, `id` (required), `namespace` (optional), `alt_ids` (list), `sex`, `race` (string or list), `ethnicity`, `vital_status`, `age_at_vital_status` (days, number).
- `--links`: JSON Lines: `a_source`, `a_id`, `b_source`, `b_id`, and optionally `a_namespace`, `b_namespace`.
- `--rules`: default `exact,alt_id,suffix`. Use `--rules exact` for a literal join.

Source names, ids and namespaces are matched exactly (case-sensitive), so normalise them first. Values are normalised case-insensitively:
- Male/M, Female/F;
- Alive/Living, Dead/Deceased;
- Hispanic or Latino / Not Hispanic or Latino;
- the five OMB 1997 race categories.

Anything else, including "Unknown" and "Not reported", counts as no value.

The paging audit:

```
python -m linkcheck.paging --pages pages.jsonl --per-page 100 --totals totals.json --out paging.json
```

- `--pages`: JSON Lines, one line per page walked: `{"page": 35, "counts": {"A": 100, "B": 0, "C": null}}`. A count is the number of entries the source had on that page. `null` means the source's part of the page was an error object; a source left out has 0 entries; `"counts": null` means the whole page failed.
- `--totals` (optional): a JSON object `{"A": 24432, ...}`, for example from a summary endpoint.
- `--per-page`: the page size the walk asked for.

From Python:

```
from linkcheck import paging
pages = {n: paging.body_counts(body) for n, body in parsed_bodies.items()}
report = paging.audit(pages, 100, {"A": 150})
report["refetch_pages"]  # fetch these again before trusting the walk
```

## Tests

```
python -m unittest -v test_linkcheck test_paging test_namespaces test_paging_body
```

The tests use only made-up data: the records in `examples/`, the page counts and bodies in `test_paging.py` and `test_paging_body.py`, and the records in `test_namespaces.py`. Every expected number was worked out by hand before the first run. So far:
- `test_linkcheck` (14 tests) passed in the sealed jobs `linkcheck-test-v1`, `ccdi-paging-v1` and `linkcheck-repro-v2`;
- `test_paging` (11 tests) passed in `ccdi-paging-v1` and `linkcheck-repro-v2`;
- `test_namespaces` passed in `linkcheck-repro-v2`;
- `test_paging_body` (12 tests) first runs in `linkcheck-031-v1`.

## Checks on real data

- [ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/results.md) (pre-registered at tag v0.6.0): did LinkCheck 0.1.0 reproduce the CCDI census on the same snapshot? **No: P1-P4 failed**, all because of the (source, id) key that 0.3.0 replaces. The job also found that its fresh snapshot had been cut short.
- [ccdi/paging-audit-v1](../ccdi/paging-audit-v1/results.md) (pre-registered at tag v0.7.0): a paging audit of every saved page of both CCDI endpoints. **All six predictions held.** The audit explained every lost entry, and 1,843 of the 1,845 page errors the census counted lose nothing.
- [ccdi/linkcheck-repro-v2](../ccdi/linkcheck-repro-v2/results.md) (pre-registered at tag v0.8.0; results at tag v0.8.1): **all seven gradable predictions held.** LinkCheck 0.3.0 reproduced the census exactly on the kept snapshot. The test of the robust fresh fetcher (F1) could not be graded there and was re-filed as [ccdi/fresh-snapshot-v1](../ccdi/fresh-snapshot-v1/) (tag v0.8.2; pending).
- [ccdi/linkcheck-031-check-v1](../ccdi/linkcheck-031-check-v1/) (pre-registered at tag v0.8.5): does 0.3.1 read the saved CCDI pages exactly, and does its refetch rule find nothing to refetch on a complete walk? Pending.

## Related tools

Record-linkage libraries *make* links: [Splink](https://moj-analytical-services.github.io/splink/index.html), [dedupe](https://github.com/dedupeio/dedupe) and the [Python Record Linkage Toolkit](https://github.com/jpweytjens/recordlinkage). Data-fusion frameworks resolve conflicting values with chosen functions: PyDI ([arXiv 2603.10547](https://arxiv.org/pdf/2603.10547)) and ODCS-FusionTool ([arXiv 1410.7990](https://arxiv.org/pdf/1410.7990)).

LinkCheck does neither. It *audits* links that already exist:
- what each resolution rule adds;
- how complete each source is;
- how often linked records disagree, with unknown values kept apart from conflicts and vital status compared by age;
- how much pooling over-counts.

Its cohort table carries conflicts forward instead of resolving them away. A 2026-10-23 web search found no tool that reports these things for an existing linkage index. The search was short, and generic data-fusion tools overlap with the cohort table.

For paging, generic checkers such as [pagination-integrity-check](https://github.com/chenhz01/pagination-integrity-check) reconcile saved page responses for missing or duplicate pages, overlapping ids and broken cursor chains. LinkCheck's paging audit is narrower. It works per source, for endpoints where one response carries every source's page. It works out what each page should hold from each source's total, and keeps three cases apart: error objects, silent short pages, and errors past a source's end.

## Limits

- Version 0.3.1 is a prototype. Its namespace handling and its new paging functions have been tested only on made-up data so far.
- A record's key has no organization. Two records of one source with the same id and the same namespace name, but different organizations, count as a repeat; put the organization into `namespace` if that matters.
- The race comparison uses the 1997 OMB categories, as the census did. OMB's 2024 combined race/ethnicity standard is not yet supported.
- The alive-versus-dead logic assumes ages at vital status are measured from the same reference point in every source. The CCDI diagnostics found one source where they are not, so check that before trusting `alive_after_death`.
- The paging audit counts entries; it does not compare them. A page that holds the right number of entries but the wrong ones (for example, records repeated from another page because the order changed during the walk) is not flagged. It also assumes each source's pages are filled in order, so only a source's last page can be partly full.
- `refetch_pages` needs totals. It cannot see a page that holds some entries but lost others with no error; the audit's short-page flags cover that case.
