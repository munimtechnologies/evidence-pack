# Results: the CCDI aggregation layer's live answers match its public code (A1-A6 all held)

MV2 of Munim, Inc. Text CC BY 4.0; code Apache-2.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

Pre-registration: [README.md](README.md), published at evidence-pack tag **v0.8.3** before the job ran. The job downloaded its code from that tag, so it ran exactly the published `probe1.py`.

## The run

- Sealed job `ccdi-aggr-probe-v1`, on the Blade, 2026-10-23 23:32:33 to 23:36:21 UTC (status ok, peak memory 0.02 GB).
- `test_probe1`: **10 tests, all OK**, run before any request ([logs/stderr.txt](logs/stderr.txt)).
- Seven sequential GET requests, 2 s apart, all at `per_page=100`, between about 23:34 and 23:35:31 UTC. They were unfiltered pages only, with no query by participant ID. Only aggregates were written ([out/probe1.json](out/probe1.json)).

| Request | Status | Bytes | Seconds | Entries |
|---|---|---|---|---|
| `/info` | 200 | 4,381 | 6.8 | n/a |
| `/subject` page 1 | 200 | 760,472 | 8.0 | 700 (100 from each of 7 sources) |
| `/subject-mapping` page 1 | 200 | 98,303 | 14.1 | 700 |
| `/subject` page 35 | 200 | 473,425 | 13.5 | 400 (CCDI-DCC, KidsFirst, StJude, Treehouse 100 each) |
| `/subject-mapping` page 35 | 200 | 70,522 | 14.5 | 400 |
| `/subject` page 600 | 200 | 1,095 | 13.3 | 0 |
| `/subject-mapping` page 600 | 200 | **118** | 14.1 | 0 (the fixed "not found" object) |

## Grades (exactly as pre-registered)

| | Prediction | Grade | Observed |
|---|---|---|---|
| A1 | No `link` header. | **pass** | None of the seven responses had one. Every response had the same eight header names: access-control-allow-origin, connection, content-length, content-type, date, set-cookie, x-content-type-options, x-frame-options. |
| A2 | Every paging answer is HTTP 200. | **pass** | All six `/subject` and `/subject-mapping` responses were 200, including both pages past the end and page 35, where PCDC fails. |
| A3 | Past the end, `/subject-mapping` is the fixed "not found" object. | **pass** | Page 600: status 200, 118 bytes, and its body parsed to exactly `{"errors":[{"kind":"NotFound","method":"GET","route":"/subject-mapping","message":"Participants IDs are not found."}]}`. |
| A4 | PCDC still fails on `/subject` page 35. | **pass** | Page 35 had one PCDC item, with no `data` list and an `errors` key. |
| A5 | `/subject-mapping` page p holds one entry per record `/subject` page p serves. | **pass** | Page 35: 400 mapping entries = 400 `/subject` entries. |
| A6 | Past the end, `/subject` serves nothing but still answers 200. | **pass** | Page 600: status 200, seven source items, 0 entries. |

**So the deployed aggregation layer behaves as its public code (`main` at a988adf) says, on every point we tested.** That supports the code-level explanation in [README.md](README.md), part 1, of why records vanish with HTTP 200, and the correction made there: snapshot 3's page 345 (100 bytes) was most likely the fixed "Server Error." object, not an empty page. The probe did not see a "Server Error." object itself, so that part still rests on the byte count plus the code.

## Correction to part 1: the missing `link` header is a documented design choice

After the job ran, we read the aggregation repository's commit history. Commit a8c1256 (2026-07-17, "docs: Remove response "link" header ref FEDERATION-703", PR #19) deleted the `link` response header from all five paginated 200 responses in the aggregator's own OpenAPI file, `swagger-aggr.yml`. So the aggregator's maintainers chose to drop the header and documented that. It is not an oversight. What A1 confirms is a known difference between the aggregated endpoint and the node specification (Federation API v1.3.0, which still says a paginated response "must" give `first` and `last` links). Part 1, observation 2, should be read that way. The practical point for clients is unchanged: the aggregated endpoint gives no stopping signal, so a client has to work out the last page from each source's total.

## What else the job saw (descriptive, not graded)

**Mixed versions across the federation.** `/info` reported these API versions per node:

| Node | API version | Server version | Data version |
|---|---|---|---|
| PCDC | 1.3.1 | 1.3.1 | pcdc_20261013_1 |
| CCDI-DCC | v1.3.0 | v1.1.0 | 3.1.0 |
| StJude | v1.2.1 | v1.2 | 3 |
| KidsFirst | v1.2.0 | v1.2.0 | 1 |
| ccdi-iusccc-pst | v1.2.0 | v1.2.0 | 1 |
| Treehouse | v1.2.0 | (none reported) | 1 |
| ccdi-ecDNA | v1.0.0 | v1.0.0 | 1 |

So the seven nodes report five different API versions, from v1.0.0 to 1.3.1. The specification repository's newest tag is v1.3.0 (2026-05-07) and has no 1.3.1 tag, so PCDC's "1.3.1" is not a published specification release. These are the nodes' own reports; we did not check what each node actually implements. PCDC's data version is dated 2026-10-13, before all three of our snapshots, so its unservable record has been there throughout.

**Two conventions past a source's end.** On `/subject` page 600, CCDI-DCC, KidsFirst and ccdi-iusccc-pst answered with an empty `data` list, while PCDC, StJude, Treehouse and ccdi-ecDNA answered with an error object. The same split shows on page 35 for the two small sources: ccdi-ecDNA (3,205 subjects, so 33 pages) answered with an error, and ccdi-iusccc-pst (504 subjects, 6 pages) with an empty list. This matches the paging audit's finding that 1,843 of the census's 1,845 page errors are errors past a source's end, which lose nothing ([../paging-audit-v1/](../paging-audit-v1/)).

**How the Participant Index names CCDI-DCC.** On mapping page 1, CCDI-DCC's 100 entries carry four study accessions as their domain (phs002431: 61, phs003519: 29, phs002430: 9, phs002790: 1). On page 35 all 100 carry phs001327. Every other source's entries carry the source name.

**Timing.** Paging answers took 8 to 14.5 s each, and `/subject-mapping` was the slower endpoint on every page (14.1 to 14.5 s).

## What this changes

- LinkCheck 0.3.1 ([../../linkcheck/](../../linkcheck/), tag v0.8.5) turns the method note in part 1 into code: a walk is over only after the last page the totals require, and before that a page with no entries is fetched again, never taken as the end. Its check on the saved pages is pre-registered in [../linkcheck-031-check-v1/](../linkcheck-031-check-v1/).
- The census's numbers do not change.

## Limits

- Seven requests at one moment. They say nothing about how often the CPI call fails.
- One model family (Claude) wrote the probe, ran it and graded it. Grading was mechanical (the job wrote the grades), but no human has checked any of it.
- The commit history was read after the predictions were published, and changes only the framing of A1, not its grade.

## Files

- `out/probe1.json`: the job's output (aggregates only: status, sizes, SHA-256, header names, counts, version fields).
- `logs/stdout.txt`, `logs/stderr.txt`, `logs/summary.json`: the runner's logs.
