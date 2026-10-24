# LinkCheck 0.5.0

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research and data-quality software only: it is not medical advice and makes no clinical decisions.

When one person has records in several sources and a linkage index says which records belong together, pooling them is safe only if each person is counted once, the fields are present, and the linked records agree. LinkCheck measures those three things and builds a cohort table that keeps every conflict visible instead of silently picking a value. It can also audit the paged endpoints the records come from (since 0.2.0), so that records lost in transit are found before the analysis starts.

It grew out of MV2's pre-registered census of NCI's Childhood Cancer Data Initiative federation ([ccdi/concordance-v1](../ccdi/concordance-v1/), tag v0.5.5) and its post-hoc diagnostics ([ccdi/diagnostics-v2](../ccdi/diagnostics-v2/), tag v0.5.10; [ccdi/diagnostics-v3](../ccdi/diagnostics-v3/), tag v0.5.12). It uses the same comparison rules, but works on any sources.

## New in 0.5.0: race and ethnicity under both OMB conventions

OMB's 1997 standard asks race (five categories) and Hispanic or Latino origin as two questions. Its 2024 revision of SPD 15 asks one combined question with seven categories, including "Hispanic or Latino" and "Middle Eastern or North African"; federal agencies must comply by March 2029. Under the 2024 standard, a list with categories but without "Hispanic or Latino" means not Hispanic or Latino. Under 1997, a missing ethnicity answer is just missing. Sources that change at different times can therefore serve the same child under different conventions, and a pooled analysis can read "not Hispanic" as "unknown" or the reverse.

0.5.0 adds, without changing anything 0.4.0 reports:
- **Which convention each record follows**, from its own values: `1997` (it answers the separate ethnicity question), `2024` (its race list holds a 2024-only category and it gives no separate answer), `both`, `contradictory` (race list says Hispanic or Latino, ethnicity says not), `undetermined` (only categories both standards share, no ethnicity answer) or `no_value`. The 2024 reading also splits a comma-joined value such as "White, Hispanic or Latino" when every part is a category. No category name contains a comma.
- **Declared conventions:** `--declare SOURCE=2024` (or `=1997`) for a source known to follow one. A declaration fills in `undetermined` records only; a record's own values always come first.
- **Hispanic or Latino origin under that convention:** `H`, `NH`, `NH_implied` (a 2024-style list without Hispanic or Latino) or unknown.
- A **`standards`** report section:
  - per source: conventions, origins, and the 2024-only values served;
  - per source pair, for linked records: origin agreement (with `NH_implied` compared as `NH`), race agreement on the 2024 categories, and the pair of conventions;
  - `implied_nh_vs_stated`: what the other record says when one record's "not Hispanic" is only implied, which tests a declaration against linked data;
  - persons whose records say both Hispanic and not.
- Three **cohort columns**, after the 0.4.0 ones: `hispanic` (`H`, `NH` or `conflict`), `hispanic_conflict` and `race_standard` (the conventions of the person's records).

A pre-registered check on a real CCDI snapshot is [ccdi/linkcheck-050-check-v1](../ccdi/linkcheck-050-check-v1/) (tag v0.9.1). It tests that 0.5.0 gives 0.4.0's result unchanged. It also asks whether linked records in other sources agree with reading CCDI-DCC's unreported ethnicity as "not Hispanic".

## New in 0.4.0: one command for a CCDI snapshot

Until now, every check of LinkCheck on real CCDI data needed job code of its own to turn a saved snapshot into LinkCheck input. `linkcheck/ccdi.py` moves that reading into the package:

```
python -m linkcheck.ccdi --raw <snapshot folder> --out result.json
```

- The snapshot folder is what the census's fetcher (tag v0.5.5) or the robust fetcher (tag v0.8.0) saves: `subject/` (page 1 is the probe named in `chosen.json`), `mapping/` and `fed/subject-summary.json.gz`, each response gzipped as it came.
- `result.json` holds the LinkCheck report (completeness, shared ids, links, conflicts, over-count, cohort summary and, since 0.5.0, standards) and the paging audits of both endpoints (`/subject` and the Participant Index, `/subject-mapping`), with the pages to fetch again. Counts only: no participant ids.
- `--records`, `--links` and `--cohort` also write the records, the link rows and the cohort table. These hold participant ids: keep them as private as the snapshot.
- `--rules`, `--priority`, `--declare` and `--min-cell` work as in `python -m linkcheck`.

How it reads a snapshot:
- **Records:** one per served subject, keyed by source, organization, namespace (study) and name; the first copy is kept. Alternate ids are the names of the subject's other identifiers.
- **Links:** one row per Participant Index association, by the census's rules. A USI association (domain `usi`, a six-letter USI) links the entry to every served subject with that USI as its name or an alternate id. Any other association counts only if its category is `organizational_identifier`. A domain name that is a namespace name becomes that source and namespace; one that is a source name becomes that source. Nothing is resolved in the reader: LinkCheck's own rules do that, and ambiguous ends are counted, never guessed.
- **Page counts:** per source and page, as the paging audit reads them; Participant Index entries are given to the source of the subject they name.

This is the same reading MV2's pre-registered checks used (`adapt()` in [ccdi/linkcheck-repro-v2](../ccdi/linkcheck-repro-v2/), tag v0.8.0, on the census's reader; `ccdi_pages.py` in [ccdi/paging-audit-v1](../ccdi/paging-audit-v1/), tag v0.7.0). A pre-registered check, [ccdi/linkcheck-040-check-v1](../ccdi/linkcheck-040-check-v1/results.md) (tag v0.8.9; results at v0.9.0), found that on a real snapshot the package reader gives exactly the same records, links, page counts, pairs and over-count as that job code (5 of 5 held).

## New in 0.3.1: no entries is not the end

Reading the CCDI aggregation code and probing the live endpoint ([ccdi/aggregator-reading-v1](../ccdi/aggregator-reading-v1/), tag v0.8.4) showed two things. A failed upstream call there comes back as HTTP 200 with a small error object and no entries. And no `link` header tells a client where the last page is. A client that stops at the first page without entries stops early whenever that happens. 0.3.1 added to `linkcheck/paging.py`:

- `last_page(totals, per_page)`: the last page a walk must reach, from the largest source total.
- `refetch_pages(pages, per_page, totals)`: the pages up to that page that were never walked, failed as a whole, or hold no entries from any source. Fetch them again instead of stopping.
- With totals, the audit report also gives `required_last_page` and `refetch_pages`, and the command line prints `refetch_pages`.
- `body_counts(body)`: the per-source counts of one page, from its parsed JSON body (a list of `{"source": ..., "data": [...]}` items; an item without a `data` list counts as an error; an object with an `errors` list is a page that failed as a whole). Other shapes are rejected, never guessed. The key names can be changed.
- `error_messages(body)`: every error the body carries, as `kind: message`.

## New in 0.3.0: namespaces

The first check on real data failed ([ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/results.md)). LinkCheck keyed records by (source, id), but 87 records of one CCDI source share their id with a record in another namespace (study) of the same source, and LinkCheck silently kept only the first. 0.3.0 fixes this:

- A record may name its `namespace`. It is then keyed by (source, id, namespace), so two namespaces of one source can serve the same id.
- A link end may name its namespace (`a_namespace`, `b_namespace`) and then resolves to that record only. A link end without one resolves only if exactly one record of the source has that id. Otherwise it is counted as `unresolved: ambiguous_id` and never guessed.
- The report has a `shared_ids` section: per source, the ids that two or more namespaces serve, and how many records serve them.

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
   - `vital_priority`: the first informative value in a source order you state;
   - (0.5.0) `hispanic`, `hispanic_conflict`, `race_standard`: see "New in 0.5.0".

   An analysis can then report its estimate under each rule, or exclude conflicted persons, and show how much the choice moves the result. Ethnicity is shown as `H` / `NH`.
6. **Paging audit** (`linkcheck/paging.py`). Some endpoints serve several sources side by side: page p of the response holds page p of every source. A source can then lose entries in two ways: its part of a page is an error object, or the page is just shorter than it should be, with no error. The CCDI diagnostics found both on one federation. The audit counts entries per source on every page. It compares each page with what the source's total says it should hold: min(per_page, max(0, T - (p - 1) x per_page)) on page p, for a source with total T. Without a total, every page before the source's last page with entries should be full. It reports:
   - **loss flags**: error pages, short pages and over-full pages where entries were expected;
   - **errors past a source's end**, counted apart (some servers answer an exhausted source with an error object; nothing is lost there);
   - page numbers missing from the walk, and pages that failed as a whole;
   - per source: served, total, entries lost by kind (error pages, short pages, missing pages, **pages not walked**), excess, and what is left **unexplained**. A non-zero unexplained count means the losses are somewhere the flags do not show;
   - with totals (0.3.1): the **last page the walk had to reach** and the **pages to fetch again**.

   "Pages not walked" catches a walk that stopped early. One CCDI snapshot lost 29,435 entries that way. By its byte count, the page that stopped it was most likely the aggregator's fixed "Server Error." object, served with HTTP 200 (see [ccdi/aggregator-reading-v1](../ccdi/aggregator-reading-v1/)).
7. **Standards** (0.5.0): see "New in 0.5.0".

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
- `--declare`: optional, for example `A=2024,B=1997` (0.5.0).

Source names, ids and namespaces are matched exactly (case-sensitive), so normalise them first. Values are normalised case-insensitively:
- Male/M, Female/F;
- Alive/Living, Dead/Deceased;
- Hispanic or Latino / Not Hispanic or Latino;
- the five OMB 1997 race categories; for the 2024 reading also "Hispanic or Latino", "Middle Eastern or North African" and "Native Hawaiian or Pacific Islander".

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
from linkcheck import ccdi, paging
result, rows = ccdi.check("snapshot")        # a saved CCDI snapshot, in one step
result, rows = ccdi.check("snapshot", declared={"CCDI-DCC": "2024"})
pages = {n: paging.body_counts(body) for n, body in parsed_bodies.items()}
report = paging.audit(pages, 100, {"A": 150})
report["refetch_pages"]  # fetch these again before trusting the walk
```

## Tests

```
python -m unittest -v test_linkcheck test_paging test_namespaces test_paging_body test_ccdi test_standards
```

The tests use only made-up data. That is the records in `examples/`, the page counts and bodies in `test_paging.py` and `test_paging_body.py`, the records in `test_namespaces.py` and `test_standards.py`, and the small snapshot `test_ccdi.py` writes to a temporary folder. Every expected number was worked out by hand before the first run. So far:
- `test_linkcheck` (14 tests) passed in the sealed jobs `linkcheck-test-v1`, `ccdi-paging-v1`, `linkcheck-repro-v2`, `linkcheck-031-v2` and `linkcheck-040-v1`;
- `test_paging` (11 tests) passed in `ccdi-paging-v1`, `linkcheck-repro-v2`, `linkcheck-031-v2` and `linkcheck-040-v1`;
- `test_namespaces` (4 tests) passed in `linkcheck-repro-v2`, `linkcheck-031-v2` and `linkcheck-040-v1`;
- `test_paging_body` (12 tests) passed in `linkcheck-031-v1`, `linkcheck-031-v2` and `linkcheck-040-v1`;
- `test_ccdi` (6 tests) passed in `linkcheck-040-v1` (0.5.0 changes only the version it expects);
- `test_standards` (12 tests, new in 0.5.0) first runs in `linkcheck-050-v1`.

## Checks on real data

- [ccdi/linkcheck-repro-v1](../ccdi/linkcheck-repro-v1/results.md) (pre-registered at tag v0.6.0): did LinkCheck 0.1.0 reproduce the CCDI census on the same snapshot? **No: P1-P4 failed**, all because of the (source, id) key that 0.3.0 replaces. The job also found that its fresh snapshot had been cut short.
- [ccdi/paging-audit-v1](../ccdi/paging-audit-v1/results.md) (pre-registered at tag v0.7.0): a paging audit of every saved page of both CCDI endpoints. **All six predictions held.** The audit explained every lost entry, and 1,843 of the 1,845 page errors the census counted lose nothing.
- [ccdi/linkcheck-repro-v2](../ccdi/linkcheck-repro-v2/results.md) (pre-registered at tag v0.8.0; results at tag v0.8.1): **all seven gradable predictions held.** LinkCheck 0.3.0 reproduced the census exactly on the kept snapshot.
- [ccdi/fresh-snapshot-v1](../ccdi/fresh-snapshot-v1/results.md) (pre-registered at tags v0.8.0 and v0.8.2; results at tag v0.8.6): **8 of 8 held.** A fresh snapshot taken by the robust fetcher reached the end of both endpoints, and LinkCheck 0.3.0 reproduced the census on it exactly.
- [ccdi/linkcheck-031-check-v1](../ccdi/linkcheck-031-check-v1/results.md) (pre-registered at tag v0.8.5): not graded; the job ran on a machine without the kept snapshot.
- [ccdi/linkcheck-031-check-v2](../ccdi/linkcheck-031-check-v2/results.md) (pre-registered at tag v0.8.7; results at tag v0.8.8): **4 of 4 held** on a new snapshot. 0.3.1's page reader matched the audit's reader on all 599 pages, and nothing needed refetching.
- [ccdi/linkcheck-040-check-v1](../ccdi/linkcheck-040-check-v1/results.md) (pre-registered at tag v0.8.9; results at tag v0.9.0): **5 of 5 held** on one snapshot (2026-10-24 02:01-05:53 UTC). 0.4.0's CCDI reader gave exactly the job code's records, link rows, page counts, pairs and over-count. Its absolute numbers (153,680 records, 20,496 exact pairs, 135,949 persons), which nobody had counted on that snapshot before, matched the prediction. The kept second snapshot was not graded.
- [ccdi/linkcheck-050-check-v1](../ccdi/linkcheck-050-check-v1/) (pre-registered at tag v0.9.1): 0.5.0 against 0.4.0, and the OMB conventions on real data (S1-S6). Not yet graded.

## Related tools

Record-linkage libraries *make* links: [Splink](https://moj-analytical-services.github.io/splink/index.html), [dedupe](https://github.com/dedupeio/dedupe) and the [Python Record Linkage Toolkit](https://github.com/jpweytjens/recordlinkage). Data-fusion frameworks resolve conflicting values with chosen functions: PyDI ([arXiv 2603.10547](https://arxiv.org/pdf/2603.10547)) and ODCS-FusionTool ([arXiv 1410.7990](https://arxiv.org/pdf/1410.7990)).

LinkCheck does neither. It *audits* links that already exist:
- what each resolution rule adds;
- how complete each source is;
- how often linked records disagree, with unknown values kept apart from conflicts and vital status compared by age;
- how much pooling over-counts.

Its cohort table carries conflicts forward instead of resolving them away. A 2026-10-23 web search found no tool that reports these things for an existing linkage index. The search was short, and generic data-fusion tools overlap with the cohort table.

For paging, generic checkers such as [pagination-integrity-check](https://github.com/chenhz01/pagination-integrity-check) reconcile saved page responses for missing or duplicate pages, overlapping ids and broken cursor chains. LinkCheck's paging audit is narrower. It works per source, for endpoints where one response carries every source's page. It works out what each page should hold from each source's total, and keeps three cases apart: error objects, silent short pages, and errors past a source's end.

For race and ethnicity, the federal Interagency Technical Working Group publishes bridging programs between the 1997 and 2024 standards ([spd15revision.gov data tools](https://spd15revision.gov/content/spd15revision/en/data-tools.html); Python and SAS programs on census.gov). They work on aggregate counts, in either direction, using factors from the 2020 Census. A partial-identification approach to harmonizing the two classifications is in [arXiv 2501.02318](https://arxiv.org/pdf/2501.02318). LinkCheck does something different. It does not bridge or impute. It labels, record by record, which convention each record follows, and it compares linked records across sources, so that a declared convention can be checked against the other sources' own answers. A 2026-10-24 web search found no tool that does this. The search was short.

## Limits

- Version 0.5.0 is a prototype. Its CCDI reader has been checked against the job code on one real snapshot (pre-registered, 5 of 5) and on made-up data. Its OMB reading has been run on made-up data only, until linkcheck-050-v1 is graded.
- The CCDI reader knows one snapshot layout (the census's fetchers). Other ways of saving the federation's pages need their own reader.
- A record's key has no organization. Two records of one source with the same id and the same namespace name, but different organizations, count as a repeat; put the organization into `namespace` if that matters.
- The 1997 race comparison in the conflicts section is unchanged, as the census used it. The 2024 reading is reported separately in `standards`. A declared convention is an assumption the user makes; LinkCheck reports its consequences and the linked evidence against it, but cannot confirm it.
- `NH_implied` follows the 2024 standard's own rule. It is wrong for a source whose records only look 2024-style because the ethnicity question was never asked.
- The alive-versus-dead logic assumes ages at vital status are measured from the same reference point in every source. The CCDI diagnostics found one source where they are not, so check that before trusting `alive_after_death`.
- The paging audit counts entries; it does not compare them. A page can hold the right number of entries but the wrong ones (for example, records repeated from another page because the order changed during the walk), and the audit will not flag it. It also assumes each source's pages are filled in order, so only a source's last page can be partly full.
- `refetch_pages` needs totals. It cannot see a page that holds some entries but lost others with no error; the audit's short-page flags cover that case.
