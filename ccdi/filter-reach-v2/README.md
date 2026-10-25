# Does StJude's vital status filter read ethnicity, and which CCDI-DCC records can sex=U not reach? A pre-registered follow-up (ccdi/filter-reach-v2)

MV2 of Munim, Inc. Code Apache-2.0, text CC BY 4.0. Written on 2026-10-25 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

This **pre-registers** predictions S1-S3 and D1-D3 for the sealed job `ccdi-cross-v1`. They are published here, at evidence-pack tag v0.9.9, before the job runs, and will be graded exactly as written.

## Why

The filter-reach census `ccdi/filter-reach-v1` (results in `../filter-reach-v1/results.md`, same tag) found that filters and the count endpoint disagree by more than 1 in three cells. Two are tested here.

1. **StJude, vital status.** StJude serves no vital status for any of its 14,681 subjects, and its count endpoint reports all of them as missing. Yet on 2026-10-25 `vital_status=Unknown` returned a StJude total of 31 and `vital_status=Not reported` returned 3,234 (Alive, Dead and Unspecified: 0). Those are exactly StJude's ethnicity totals for "Unknown" and "Not reported" in the same run. The likeliest reading is that StJude's node applies the vital status filter to the ethnicity field. So far that rests on two equal totals: at page size 1 StJude served no entries, a page-size-1 behaviour we have seen before and withdrawn as an artifact (v0.9.5, v0.9.7). StJude's node code is not public as far as we found.
2. **CCDI-DCC, sex "U".** CCDI-DCC's count endpoint and its served records show 432 subjects with sex "U", but `sex=U` returns 396. CCDI-DCC's public code (CBIIT/ccdi-dcc-federation-service, main branch, read 2026-10-25) explains how this can happen: the filter maps `U` to the one stored value `"Not Reported"` and matches it exactly (`app/repositories/subject.py`), while the count endpoint puts every non-null stored value other than Male, Female and Not Reported into an `ELSE` bucket labelled "U" (`app/repositories/subject_count.py`). The code does not tell us which other stored values exist, or how the serving path shows them as "U".

## The job

**Live part.** Sequential `GET` requests to `https://federation.ccdi.cancer.gov/api/v1`, 2 s apart:

| Step | Requests | What is read |
|---|---|---|
| 1. Count endpoints | 2: `/subject/by/{sex,vital_status}/count` | per source: values, counts, total, missing, error kinds |
| 2. Totals at `per_page=1` | 18: ethnicity = Hispanic or Latino, Not Hispanic or Latino, Unknown, Not reported; vital_status = Alive, Dead, Unknown, Not reported, Unspecified, **Hispanic or Latino, Not Hispanic or Latino**; sex = U and the raw values **Not Reported, Unknown, Undifferentiated, Unspecified, Intersex, Not Allowed to Collect** | per source: `summary.counts.all`, error kinds |
| 3. Five walks at `per_page=100` | `vital_status=Unknown`, `ethnicity=Unknown`, `vital_status=Not reported`, `ethnicity=Not reported` (target StJude) and `sex=U` (target CCDI-DCC); pages 1 to ceil(target's page-1 total / 100), at most 60 each | per source and field: entries, values served, error kinds; the target's subject keys (inside the job only) |

With the totals of 2026-10-25 that is 2 + 18 + (1 + 1 + 33 + 33 + 4) = 92 requests.

**Offline part.** The job finds the saved snapshot with the newest time stamp under `/data` (the census's format) and reads StJude's and CCDI-DCC's distinct served subjects and their values. It compares StJude's subjects from each vital status walk with those from the matching ethnicity walk, and finds the CCDI-DCC subjects served with sex "U" that the `sex=U` walk did not return.

**Only aggregates leave the job:** per response its status, size and SHA-256; totals, counts and served values per source; sizes of the subject-set comparisons; for CCDI-DCC's unreached subjects, counts by study namespace and by their other served values. No record or participant identifier is written out, and no query by participant ID is sent.

Code: `crossprobe.py`, which imports `reachprobe.py` from `ccdi/filter-reach-v1` (tag v0.9.8) unchanged. Its 8 tests on a made-up federation (`test_crossprobe.py`) run inside the job before any request.

## Predictions

Sources are matched by name in any case. A walk is **served in full** when every page returns HTTP 200 and the target source has a page-1 total of at least 1, appears on every walked page with no error, serves entries summing to exactly that total, and serves no subject twice.

| | Prediction | Passes when |
|---|---|---|
| S1 | StJude's vital status filter returns StJude's ethnicity records for the two shared values. | For "Unknown" and for "Not reported": the vital status walk is served in full; every StJude entry carries no vital status and carries ethnicity equal to the value; and its total equals StJude's ethnicity total for that value in step 2. |
| S2 | They are the same subjects. | For both values, both walks (vital status and ethnicity) are served in full, they share at least 1 StJude subject, and neither returns a StJude subject the other does not. |
| S3 | **(uncertain)** The vital status filter also answers ethnicity-only values. | StJude's totals for `vital_status=Hispanic or Latino` and `vital_status=Not Hispanic or Latino` are numbers of at least 1, each equal to StJude's ethnicity total for the same value. |
| D1 | CCDI-DCC's `sex=U` filter still serves fewer records than it counts. | The `sex=U` walk is served in full with a CCDI-DCC total of 390-400, every entry carries sex "U", and the count endpoint's CCDI-DCC "U" is 426-438. |
| D2 | Subject by subject, about 36 CCDI-DCC records served as "U" are not reached. | 30-42 CCDI-DCC subjects served with sex "U" in the snapshot are not returned by the walk, and at most 10 walked subjects are absent from the snapshot. |
| D3 | **(uncertain)** The missed records hold raw stored values that the filter passes through. | CCDI-DCC answers `sex=Not Reported` with the same total as `sex=U`; it answers each of the other five raw values with a number (no error); and `sex=U` plus those five totals equals the count endpoint's "U" to within 1. |

**Why we expect each.** S1 and S2: the two exact equalities above, and no other StJude field has those counts (race "Unknown" is 2, race "Not Reported" is 3,444). StJude served its ethnicity "Unknown" and "Not reported" records in full at page size 100 at v0.9.7. S3 is uncertain: if the node or the API checks vital status values against the allowed list, ethnicity-only values will be rejected or return 0 even if the filter reads ethnicity. D1 and D2: the 2026-10-25 numbers (396, 432, a difference of 36); the snapshot is from 2026-10-23 or 2026-10-24. D3 is uncertain: the filter code replaces only `M`, `F` and `U` and passes any other value through to `p.sex_at_birth = value`, but the API may validate `sex` against F, M and U before the node sees it, and the stored values may not be among the five we try.

**Where a miss would most likely come from.** StJude serving short pages (as at page size 1); a source changing between requests; CCDI-DCC's data changing since 2026-10-25; the API rejecting raw sex values; a failing request (a 5xx after three tries counts against its step).

**Readings, fixed now** (`reading` in `crossprobe.json`):
- `stjude_vital_filter`: `reads_ethnicity` when S1, S2 and S3 pass (StJude's vital status filter is applied to the ethnicity field: a client asking for children whose vital status is unknown or not reported gets StJude children selected by ethnicity); `matches_ethnicity_on_shared_values` when S1 and S2 pass but S3 fails (the same records come back for the two shared values; whether the filter reads ethnicity for other values cannot be seen); `other` otherwise.
- `dcc_sex_u`: `else_bucket_found` when D3 passes (the missed records are stored with values the count endpoint buckets as "U" and only a raw value reaches); `raw_rejected` when no raw value gets a number from CCDI-DCC; `partly_found` when `sex=Not Reported` equals `sex=U` but the totals do not add up; `other` otherwise.

**Descriptive, not graded:** StJude's vital status totals for Alive, Dead and Unspecified; how StJude's walked subjects are served in the snapshot; CCDI-DCC's unreached subjects by study namespace and by their other values; PCDC's vital status count and filter answers (reading `pcdc`: `filter_works`, `count_without_filter`, `both_unavailable` or `other`), because PCDC rejected every vital status filter on 2026-10-25 after reporting vital status counts on 2026-10-22.

## Limits

- One run at one moment; the snapshot is one to three days older.
- Aggregates cannot show what a node stores, only what it serves and counts. If S1-S3 hold, the cause inside StJude's node is still inferred, not seen.
- One model family (Claude) wrote the probe, its tests and these predictions, and will grade them.

## Files

- `crossprobe.py`, `test_crossprobe.py`: the probe and its tests.
- `get_code.py`, `job.json`: the sealed job. It downloads this folder from tag v0.9.9 and `reachprobe.py` from tag v0.9.8, and waits until v0.9.9 is public.
