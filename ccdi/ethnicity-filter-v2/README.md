# Can the federation's ethnicity filter be paged through, and does it reach every child served with that value? A pre-registered follow-up

MV2 of Munim, Inc. Code Apache-2.0, text CC BY 4.0. Written on 2026-10-25 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

This **pre-registers** predictions F1-F6 for the sealed job `ccdi-eth-walk-v1`. They are published here, at evidence-pack tag v0.9.6, before the job runs, and will be graded exactly as written.

## Why

`ccdi/ethnicity-filter-v1` (results at tag v0.9.5) held 5 of 5: CCDI-DCC answers "Not Hispanic or Latino" with zero records and no error. Its eight responses also showed two things it did not predict (see its `results.md`):

1. **StJude** reported a total but served no entry on page 1 (page size 1) for `ethnicity=Not reported` (total 3,234) and `ethnicity=Unknown` (total 31). It served one entry for the other two values it holds. In our census of 2026-10-22 (job `ccdi-concord-v1`), StJude's unfiltered pages served exactly 3,234 subjects with "Not reported" and 31 with "Unknown".
2. **KidsFirst**'s `ethnicity=Unknown` total was 8,284, its count endpoint's number, while the same census counted 10,280 KidsFirst subjects served with the literal value "Unknown". KidsFirst's five filtered totals sum to 36,444 of its 38,440 subjects.

A single page of size 1 is weak evidence. This check walks the filtered results in full and recounts the served values on a saved snapshot.

## The job

**Live part.** Three walks of `GET /subject` on `https://federation.ccdi.cancer.gov/api/v1`, at `per_page=100`, sequential, 2 s apart:

| Walk | `ethnicity=` | Pages walked |
|---|---|---|
| not-reported | Not reported | 1 to ceil(StJude's page-1 total / 100) |
| unknown | Unknown | 1 to ceil(KidsFirst's page-1 total / 100) |
| hispanic (control) | Hispanic or Latino | 1 to ceil(StJude's page-1 total / 100) |

At most 120 pages per walk; a walk whose target has no clean page-1 total stops after page 1. With the totals seen on 2026-10-24 that is 33 + 83 + 10 = 126 requests. Each response is recorded as status, size and SHA-256, and per source: its reported total (`summary.counts.all`), the number of entries served, the kinds of any error objects, and a count of the ethnicity values its entries carry. No record or identifier leaves the job, and no query by participant ID is sent.

**Offline part.** The job finds the saved snapshot with the newest time stamp in its path under `/data` (the census's format, `subject/chosen.json` plus gzipped pages) and counts, per source, the ethnicity values of its distinct served subjects (key: source, organization, namespace, name; first copy counts; no value is counted as `<missing>`). Which snapshot was used is recorded.

Code: `walkprobe.py`. Its 14 tests on made-up data (`test_walkprobe.py`) run inside the job before any request.

## Predictions

Sources are matched by name in any case. A source's "page-1 total" is its `counts.all` on page 1 of that walk when its item there has no `errors` key and the total is an integer. A walk "returns 200" when every page in it had HTTP status 200.

| | Prediction | Passes when |
|---|---|---|
| F1 | StJude counts its "Not reported" subjects but serves none of them through the filter. | The not-reported walk returns 200; StJude's page-1 total is at least 3,000; StJude's entries summed over every walked page are 0. |
| F2 | The same for "Unknown". | The unknown walk returns 200; StJude's page-1 total there is at least 1; its entries summed over every walked page are 0. |
| F3 | Control: StJude serves its "Hispanic or Latino" subjects in full. | The hispanic walk returns 200; StJude's page-1 total is at least 1; it has no error page; its entries summed over the walk equal its page-1 total; and every one of them carries the value "Hispanic or Latino". |
| F4 | KidsFirst serves exactly what its "Unknown" filter counts. | The unknown walk returns 200; KidsFirst appears on every walked page with no error page; its entries summed over the walk equal its page-1 total; and every one carries the value "Unknown". |
| F5 | The "Unknown" filter does not reach every KidsFirst subject served as "Unknown". | KidsFirst's page-1 total in the unknown walk is at most 8,300, and in the snapshot at least 10,180 distinct KidsFirst subjects carry the value "Unknown". |
| F6 | The StJude subjects F1 and F2 are about exist in the unfiltered data. | In the snapshot, at least 3,000 distinct StJude subjects carry "Not reported" and at least 1 carries "Unknown". |

**Why we expect each.** F1, F2: the page-1 observation of v0.9.5, and the census's counts. F3: StJude served one "Hispanic or Latino" entry on page 1 in v0.9.5, and its count endpoint matched its served records exactly in the census. F4: KidsFirst served one entry for every value in v0.9.5; we know of no paging loss in KidsFirst (our paging audits found none). F5: the 8,284 total of v0.9.5 and the 10,280 of the census; KidsFirst's totals have not changed since 2026-10-22. F6: the census.

**Where a miss would most likely come from.**
- F1, F2: StJude serving the records on later pages only (page 1 at size 1 was empty by chance or by ordering), or a fix since 2026-10-24.
- F4: paging loss inside KidsFirst's filtered result, or a value other than "Unknown" in it.
- F5: the snapshot used may not be the census's; if KidsFirst's served values changed between snapshots, F5 can fail even if the filter behaves as on 2026-10-24.
- Any: a failing request (a 5xx after three tries counts against the walk).

**Reading, fixed now** (`reading` in `walkprobe.json`):
- StJude: `counted_not_served` when F1 and F6 pass: StJude's "Not reported" children are in its unfiltered data and in the filter's total, but a client paging through the filtered result gets none of them, with no error on page 1. `served_in_full` when StJude's entries in the not-reported walk equal its page-1 total: no loss at page size 100, and the v0.9.5 observation was an artifact of page size 1. `partial` when they are above 0 and below it. Otherwise `other`.
- KidsFirst: `unreached` when F4 and F5 pass: about 2,000 KidsFirst children served with ethnicity "Unknown" are reached by no ethnicity filter value, while the filter's own total and pages agree with each other. Otherwise `other`.

**Descriptive, not graded:** every source's totals, entries, error kinds and served values in every walk (including PCDC's error objects, and whether CCDI-DCC's "Not reported" entries carry that value), each source's snapshot values, response times.

## Limits

- One walk per value at one moment describes the server at that moment only.
- The snapshot is from 2026-10-23 or 2026-10-24, depending on the machine the job runs on, not from the moment of the walk. The federation's totals were unchanged from 2026-10-22 to 2026-10-24.
- The served values cannot say whether each study asked about ethnicity, and the job cannot see why a source's filter behaves as it does.
- One model family (Claude) wrote the probe, its tests and these predictions, and will grade them.

## Files

- `walkprobe.py`, `test_walkprobe.py`: the probe and its tests.
- `get_code.py`, `job.json`: the sealed job. It downloads this folder from tag v0.9.6 and waits until the tag is public.
