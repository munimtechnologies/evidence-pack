# Results: pre-registered record-level check of two CCDI federation filter defects (ccdi/filter-reach-v2)

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-26 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

The predictions (S1-S3, D1-D3) were published in `README.md` at evidence-pack tag v0.9.9 before the sealed job `ccdi-cross-v1` ran. They are graded here exactly as written. **4 of 6 held: S1, S2, D1, D2. S3 and D3 failed.**

## The run

- Sealed job `ccdi-cross-v1`, 2026-10-25 22:51-23:00 UTC (the probe finished at 23:00:08 UTC). Setup downloaded the probe from tag v0.9.9 and `reachprobe.py` from tag v0.9.8 and logged their SHA-256 (`logs/setup-stdout.txt`); the 8 tests on made-up data passed before any request (`logs/setup-tests.txt`).
- 92 sequential GET requests to `https://federation.ccdi.cancer.gov/api/v1`, as planned (2 count, 18 totals, 72 walk pages), every one HTTP 200 (`logs/run-stdout.txt`; status, size and SHA-256 of each in `out/crossprobe.json`, key `requests`).
- Snapshot used for served values: `ccdi-raw-fresh-20261024T020144Z` (599 pages, none unreadable).
- Output: `out/crossprobe.json` (aggregates only). Runner summary: `logs/summary.json`.

## Grades

| | Prediction | Result | Grade |
|---|---|---|---|
| S1 | StJude's vital status filter returns StJude's ethnicity records for the two shared values | `vital_status=Unknown`: 1 page, 31 StJude entries; `vital_status=Not reported`: 33 pages, 3,234 entries; every page HTTP 200, no subject twice; every entry has no vital status and ethnicity equal to the value; totals equal StJude's ethnicity totals (31, 3,234) | pass |
| S2 | They are the same subjects | "Unknown": 31 in both walks, 0 in only one; "Not reported": 3,234 in both, 0 in only one | pass |
| S3 | (uncertain) The vital status filter also answers ethnicity-only values | StJude answered `vital_status=Hispanic or Latino` and `vital_status=Not Hispanic or Latino` with an `InvalidParameters` error, not a number | **fail** |
| D1 | CCDI-DCC's `sex=U` filter still serves fewer records than it counts | walk: 4 pages, 396 entries = total (in 390-400), all HTTP 200, every entry sex "U"; count endpoint "U": 432 (in 426-438) | pass |
| D2 | About 36 CCDI-DCC records served as "U" are not reached | 432 served with "U" in the snapshot, 396 walked, **36 unreached** (in 30-42); 0 walked subjects absent from the snapshot | pass |
| D3 | (uncertain) A raw stored value reaches the missed records | CCDI-DCC answered `sex=Not Reported` with 0 (not 396, the `sex=U` total), and each of the other five raw values with 0; 396 + 0 is 36 short of 432 | **fail** |

Readings, as fixed in advance: `stjude_vital_filter` = **matches_ethnicity_on_shared_values**; `dcc_sex_u` = **other**.

## What it shows

**1. StJude: a vital status filter that returns ethnicity records (S1, S2 held).** Record by record, the 31 children StJude returns for `vital_status=Unknown` are exactly the 31 it returns for `ethnicity=Unknown`, and the 3,234 it returns for `vital_status=Not reported` are exactly the 3,234 it returns for `ethnicity=Not reported`. None of them carries a vital status, in the live walks or in the snapshot. A client asking the federation for children whose vital status is unknown or not reported therefore gets 3,265 StJude children selected by ethnicity, whose vital status StJude does not serve at all.

S3 failed: StJude rejects the ethnicity-only values `Hispanic or Latino` and `Not Hispanic or Latino` as vital status values. So StJude checks the value against the vital status list before querying. Whether its filter reads the ethnicity field for every value, or only the two values the fields share, cannot be seen from outside; StJude's node code is not public as far as we found. That is the fixed reading `matches_ethnicity_on_shared_values`.

**2. CCDI-DCC: 36 children no sex filter can reach (D1, D2 held).** The 36 unreached children all carry sex "U" and ethnicity "Not reported" as served (race: 24 "Not Reported", 11 "Unknown", 1 "White"; vital status missing for 32). They sit in six study namespaces, and the split is all or nothing by study: in each of those six (phs002187: 22, phs001437: 8, phs003160: 2, phs002430: 2, phs000471: 1, phs002504: 1), every child served as "U" is unreached, and in each of the other eight namespaces with "U" children (for example phs000464: 324), every one is reached. That fits a per-study difference in the stored value.

D3 failed, and the reason is in CCDI-DCC's public code, which we read after the run (CBIIT/ccdi-dcc-federation-service, main branch, 2026-10-26). This explanation is **post hoc**, not part of the pre-registration:
- the API layer accepts only `M`, `F` and `U` for `sex` (`app/api/v1/deps.py`, `valid_sex_values = ["M", "F", "U"]`). Any other value is marked invalid, and the subjects endpoint then answers HTTP 200 with a total of 0 and no records (`app/api/v1/endpoints/subjects.py`). So no raw value ever reaches the node's pass-through, and the zeros we saw are the API's silent zero, the same behaviour we found for CCDI-DCC's ethnicity filter at v0.9.4/v0.9.5;
- the filter maps `U` to the single stored value `"Not Reported"` and matches it exactly (`app/repositories/subject.py`);
- the count endpoint puts every non-null stored value other than Male, Female and Not Reported into an `ELSE` bucket labelled "U" (`app/repositories/subject_count.py`);
- the serving path turns any non-null stored value that is not Male or Female (after a case-insensitive match) into "U" (`_record_to_subject` in `app/repositories/subject.py`).

Three code paths normalise the same field three ways. Children stored with any value other than exactly "Male", "Female" or "Not Reported" are counted and served as "U", but no value of the sex filter returns them. Which stored value the six studies use is not visible through the API; our pre-registered reading for "no raw value gets a number" (`raw_rejected`) assumed an error, so the API's silent zero falls under `other`.

**3. PCDC, vital status (descriptive).** PCDC's vital status count answered again (Alive 17,134, Dead 4,952, Unknown 2,346, the same as on 2026-10-22), but every vital status filter was still rejected with `InvalidParameters`: reading `count_without_filter`. A client can count PCDC children by vital status but cannot select them by it.

**4. How nodes treat values outside a field's list (descriptive).** For the ethnicity-only vital status values and the raw sex values, StJude and PCDC answered `InvalidParameters`, while CCDI-DCC, KidsFirst, Treehouse, ccdi-ecDNA and ccdi-iusccc-pst answered 0. The same request is an error from some sources and a silent zero from others.

## What this means for a user of the federation

Together with `ccdi/filter-reach-v1` (same repository, tag v0.9.9), both defects are now confirmed at the record level. A cohort built by filtering on vital status includes StJude children chosen by their ethnicity, and a cohort built by filtering on sex "U" misses 36 CCDI-DCC children (8.3% of that source's 432), concentrated in six studies. Neither shows up as an error.

## Limits

- One run at one moment; the snapshot is about 1.9 days older than the live requests.
- Aggregates only: no record identifiers left the job. Stored values are not visible; StJude's cause is inferred, CCDI-DCC's is read from its public main branch, which may differ from what is deployed.
- The CCDI-DCC code reading was done after the grades and is labelled post hoc.
- One model family (Claude) wrote the probe, the predictions and this grading. No human has reviewed it.

## Files

- `README.md`, `crossprobe.py`, `test_crossprobe.py`, `get_code.py`, `job.json`: the pre-registration and job (tag v0.9.9), unchanged.
- `out/crossprobe.json`: the job's output, unchanged.
- `logs/`: the runner's summary and logs, unchanged.
