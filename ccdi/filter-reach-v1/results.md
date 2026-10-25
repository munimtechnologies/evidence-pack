# Results: pre-registered filter-reach census of NCI's CCDI Data Federation (ccdi/filter-reach-v1)

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-25 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

The predictions (R1-R3, K1-K3) were published in `README.md` at evidence-pack tag v0.9.8 before the sealed job `ccdi-reach-v1` ran. They are graded here exactly as written. **3 of 6 held: K1, K2, K3. R1, R2 and R3 failed.**

## The run

- Sealed job `ccdi-reach-v1`, 2026-10-25 14:45-15:03 UTC (the job's requests finished at 15:02:38 UTC). Setup downloaded the probe from tag v0.9.8 and logged its SHA-256 (`logs/setup-stdout.txt`); the 14 tests on made-up data passed before any request (`logs/setup-tests.txt`).
- 195 sequential GET requests to `https://federation.ccdi.cancer.gov/api/v1`, every one HTTP 200 (`logs/run-stdout.txt`; status, size and SHA-256 of each in `out/reachprobe.json`, key `requests`).
- Snapshot used for served values: `ccdi-raw-fresh-20261024T020144Z` (599 pages, none unreadable).
- Output: `out/reachprobe.json` (aggregates only). Runner summary: `logs/summary.json`.

## Grades

| | Prediction | Result | Grade |
|---|---|---|---|
| R1 | Filters follow the count endpoint (at least 100 comparable cells, all within 1) | 130 comparable cells; 125 equal, 2 differ by 1 (Treehouse race Asian and White, where one record is served as "White,Asian"); **3 differ by more than 1** (below) | **fail** |
| R2 | The only gaps above 10 are KidsFirst "Unknown" in ethnicity (1,900-2,100) and race (2,550-2,750) | KidsFirst ethnicity 1,996 and race 2,659, as predicted, **plus CCDI-DCC sex "U": 36** | **fail** |
| R3 | PCDC's vital status filter returns over 22,000 records that carry no vital status | PCDC answered all five vital status filters with an `InvalidParameters` error, and the vital status count endpoint answered for PCDC with a `ServerConnection` error | **fail** |
| K1 | Both KidsFirst walks serve exactly their totals | ethnicity=Unknown: 83 pages, 8,284 entries = total; race=Unknown: 87 pages, 8,607 entries = total; all HTTP 200, every entry carries "Unknown" | pass |
| K2 | Subject by subject, the unreached sets have the sizes of R2 | 1,996 ethnicity-unreached, 2,659 race-unreached; 0 walked subjects absent from the snapshot | pass |
| K3 | At least 80% of ethnicity-unreached subjects are also race-unreached | 1,632 of 1,996 = **81.8%** | pass (close to the threshold) |

Readings, as fixed in advance: `count_and_filter` = **disagree**; `under_reach` = **other**; `pcdc_vital_status` = **other**; `kidsfirst_overlap` = **shared**.

## What failed, and what it shows

**1. CCDI-DCC, sex "U": the filter misses 36 records (R1, R2).** The count endpoint says 432 CCDI-DCC subjects have sex "U", and 432 are served with "U" in the snapshot, but `sex=U` returns 396. We read the node's public code (CBIIT/ccdi-dcc-federation-service, main branch, read 2026-10-25):
- the filter translates `U` to the single stored value `"Not Reported"` and matches it exactly (`app/repositories/subject.py`, `sex_mapping = {"M": "Male", "F": "Female", "U": "Not Reported"}`, then `p.sex_at_birth = $param`);
- the count endpoint builds a `CASE` expression in which every non-null stored value other than Male, Female and Not Reported falls into an `ELSE` bucket labelled "U" (`app/repositories/subject_count.py`, `_build_sex_normalization_case`).

So any stored sex value outside those three is counted as "U" but cannot be reached by `sex=U`. This explains the count/filter disagreement from the code. It does not yet show which stored values the 36 records hold, or how the serving path turns them into "U"; the follow-up `ccdi/filter-reach-v2` tests that.

**2. StJude, vital status: the filter returns records from another field (R1).** StJude serves no vital status for any of its 14,681 subjects, and its count endpoint reports all 14,681 as missing. Yet `vital_status=Unknown` returns a StJude total of **31** and `vital_status=Not reported` returns **3,234**, while Alive, Dead and Unspecified return 0. Those two numbers are exactly StJude's ethnicity totals for "Unknown" (31) and "Not reported" (3,234) in the same run. No other StJude field has those counts (race "Unknown" is 2 and race "Not Reported" is 3,444). The likeliest reading is that StJude's node applies the vital status filter to the ethnicity field. That reading rests on two equal totals, not yet on records: at page size 1 StJude served no entry for either filter, the same page-size-1 behaviour we saw for its ethnicity filter at v0.9.5 and withdrew at v0.9.7 as an artifact. StJude's node code is not public as far as we found. The follow-up walks both filters at page size 100 and compares the subjects.

**3. PCDC, vital status (R3).** We predicted from the 2026-10-22 census, when PCDC's count endpoint reported Alive 17,134, Dead 4,952 and Unknown 2,346. On 2026-10-25 PCDC rejected every vital status filter (`InvalidParameters`) and its vital status count failed (`ServerConnection`). PCDC also answered the race filters "Black or African American" and "Native Hawaiian or other Pacific Islander" with `ServerConnection` errors in this run, so some of this may be transient. What can be said: on 2026-10-25 a client could not ask PCDC for children by vital status, and the R3 situation (a filter returning records without the value) was not observed.

**4. KidsFirst, what held (K1-K3).** Both KidsFirst "Unknown" filters serve exactly their own totals, and those totals leave out 1,996 (ethnicity) and 2,659 (race) records that are served as "Unknown"; 3,023 KidsFirst records are unreached in at least one field and 1,632 in both. The unreached records are concentrated by study: in one study namespace (`sd-dypmehhf`) 1,120 of 1,681 subjects are ethnicity-unreached and 1,109 race-unreached; in another (`sd-jws3v24d`) all 1,777 subjects are served with ethnicity "Unknown" and all are reached, while 324 of its 376 race-"Unknown" subjects are not. So "Unknown" is reachable in some studies and not in others, field by field, which fits a per-study difference between an explicit stored "Unknown" and no stored value served as "Unknown". This check sees only served values and cannot show the stored ones. Of the ethnicity-unreached records, 1,888 of 1,996 also have no vital status. Counts per study namespace and by other values are in `out/reachprobe.json`, key `kidsfirst`.

## What this means for a user of the federation

Across 7 sources, 4 fields and 20 values (140 cells), 130 cells could be compared, and in 127 of them the filter agrees with the count endpoint to within 1 (the other 10 are PCDC cells where the filter or the count answered with an error). Beyond that, the federation falls short in three ways: some records counted under a value cannot be reached by filtering on it (KidsFirst "Unknown" in two fields; CCDI-DCC sex "U"); one source's vital status filter returns records that, as served, carry no vital status, and their number matches its ethnicity field; and one source rejects a filter whose values its count endpoint reported three days earlier. A cohort built by filtering will differ from one built from counts or from served records, by source and by field.

## Limits

- One run at one moment; the snapshot is about 1.5 days older than the live requests.
- Aggregates only: no record identifiers left the job, and the reasons are inferred from served values and, for CCDI-DCC, from its public code.
- The StJude reading rests on two equal totals until the follow-up walk confirms or refutes it.
- K3 passed at 81.8% against an 80% threshold.
- One model family (Claude) wrote the probe, the predictions and this grading. No human has reviewed it.

## Files

- `README.md`, `reachprobe.py`, `test_reachprobe.py`, `get_code.py`, `job.json`: the pre-registration and job (tag v0.9.8), unchanged.
- `out/reachprobe.json`: the job's output, unchanged.
- `logs/`: the runner's summary and logs, unchanged.
- Follow-up pre-registration: `../filter-reach-v2/README.md`.
