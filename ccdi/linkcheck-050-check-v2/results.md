# Results: ccdi/linkcheck-050-check-v2: 5 of 6 held; S6, the test of the 2024 reading, failed in the direction that supports it

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

Graded exactly as written in `ccdi/linkcheck-050-check-v1/README.md` (predictions S1-S6, tag v0.9.1), with the corrected grader of `ccdi/linkcheck-050-check-v2` (tag v0.9.2). Nothing in the predictions, thresholds or grader was changed after the job ran.

## The job

- Sealed job `linkcheck-050-v2` ran on the Blade, 2026-10-24 20:14:58-20:18:50 UTC (232 s, peak memory 0.54 GB). No request went to the federation.
- **Setup:** `get_code.py` downloaded the corrected grader from v0.9.2 and every other file from v0.9.1, v0.8.9 and v0.8.0. Every reused file had the SHA-256 that the first job (`linkcheck-050-v1`) logged (`logs/stdout.txt`, "as in v1").
- **Tests:** 66 ran, 66 passed (`logs/stderr.txt`): LinkCheck 0.5.0's 59 and the grader's 7, including the three new `Stamps` tests and `test_grade_one`, which failed in the first filing.
- **Snapshots graded:** two, both on the Blade: the kept second snapshot (`/data/ccdi-raw-snapshot2`, 153,580 records) and the fresh snapshot `ccdi-raw-fresh-20261023T214658Z` (153,680 records). The Dell's snapshot of 2026-10-24 is not on the Blade and was not graded.
- Output: `out/check050.json` (aggregates only: counts and source names).

## Grades

A prediction holds if it passes on every snapshot where it can be graded. Every prediction got the same grade on both snapshots.

| | Prediction (short form) | Grade | Observed (both snapshots unless stated) |
|---|---|---|---|
| S1 | 0.5.0 = 0.4.0 except version stamps and the new standards section; cohort table adds exactly 3 columns | **pass** | `differing_keys` empty; cohort rows 135,044 (kept) and 135,144 (fresh), old columns identical; added `hispanic`, `hispanic_conflict`, `race_standard` |
| S2 | Only CCDI-DCC's 24 "White, Hispanic or Latino" records carry a 2024-only category; at least 20 read `both`; none `contradictory` | **pass** | CCDI-DCC: `{"Hispanic or Latino": 24}`, all 24 `both`, 0 `2024`, 0 `contradictory`; the other six sources: none |
| S3 | `1997` + `both` + `contradictory` = 0.4.0's informative-ethnicity count, per source | **pass** | e.g. CCDI-DCC 4,090 = 4,090; KidsFirst 28,160; PCDC 20,488 (kept) and 20,577 (fresh) |
| S4 | Nothing declared: no `NH_implied`; CCDI-DCC serves no "Not Hispanic or Latino" | **pass** | `NH_implied` 0 in every source; CCDI-DCC H 4,090, unknown 55,705 |
| S5 | CCDI-DCC declared 2024: 46,650-47,101 records `NH_implied` | **pass** | 47,062 |
| S6 | CCDI-DCC declared 2024: in exact-link pairs where one record is `NH_implied` and the other states its ethnicity, **at least 5%** of the stated values are Hispanic or Latino | **fail** | 4 of 7,389 (0.05%) |

**Overall: 5 of 6 held.** What the five passes mean, plainly:
- **S1** is a regression check: LinkCheck 0.5.0 changes nothing that 0.4.0 reported. It skipped exactly the four version stamps the v2 README said it would (`tool`, `linkcheck.tool`, `paging.subject.tool`, `paging.mapping.tool`; listed under `stamps_skipped`).
- **S2** was a real prediction for six of the seven sources, whose race values had not been enumerated before.
- **S3 is an identity of the code**, as the pre-registration said: both readings use the same field. It is not a finding.
- **S4** replicates an earlier snapshot.
- **S5 mostly tests the new code against a bound we derived two days earlier** from aggregate filter counts. 47,062 is inside it, 39 below the upper end.

## S6: the prediction failed, and the result supports the reading we doubted

The README fixed the reading in advance: below 2% supports the 2024 reading of CCDI-DCC's unreported ethnicity; 2% to under 5% is inconclusive; 5% or more contradicts it. **The observed share is 0.05% (4 of 7,389 pairs), far below 2%, so by our own rule the result supports the 2024 reading.** The README leaned the other way ("which hints at the first", i.e. "not asked"). That hint was wrong.

| Source pair (exact links) | Pairs | Linked record says Hispanic | Says not Hispanic |
|---|---|---|---|
| CCDI-DCC with KidsFirst | 4,387 | 2 | 4,385 |
| CCDI-DCC with PCDC | 2,020 | 2 | 2,018 |
| CCDI-DCC with Treehouse | 982 | 0 | 982 |
| **All** | **7,389** | **4 (0.05%)** | **7,385** |

The pairs total is 7,389 on both snapshots (above the 100 needed to grade). For context, as pre-registered: among linked pairs where both records state a 1997 ethnicity, 2 of 2,572 disagree (0.08%). So the 4 stated-Hispanic values are about as rare as ordinary disagreement between sources.

**Post hoc arithmetic (not pre-registered):** if the linked records said Hispanic at each source's own stated rate in this snapshot (KidsFirst 4,824 of 28,160, 17.1%; PCDC 2,813 of 20,488, 13.7%; Treehouse 553 of 8,876, 6.2%), we would expect about 1,090 of the 7,389 pairs to say Hispanic. We observed 4. The linked children may not be a random sample of each source, so this is a rough scale, not a test.

**What it means.** When CCDI-DCC serves a named race with ethnicity "Not reported", and another source holds the same child, that source almost always says "Not Hispanic or Latino". In the linked records, CCDI-DCC's "Not reported" behaves as "not Hispanic", the reading OMB's 2024 combined question gives. A pooled analysis that reads the Federation API's 1997-style ethnicity field literally treats those children as having unknown ethnicity. Declaring CCDI-DCC as 2024 adds 4 persons whose records say both Hispanic and not (exact links: 2 persons without the declaration, 6 with it; with the resolution rules, 4 and 8).

## Limits

- **Only linked children are tested.** 7,389 of the 47,062 `NH_implied` CCDI-DCC records (15.7%) have an exact link to a record that states ethnicity. Whether the other 84% follow the same reading cannot be checked from open data.
- **The sources may not be independent.** If CCDI-DCC's records and the linked records come from the same submission, their agreement shows a consistent mapping ("Not Hispanic or Latino" served as "Not reported"), not two independent observations. Either way, the practical reading is the same: in these records, "Not reported" stands for "not Hispanic".
- Linked records are not ground truth; a disagreement can be an error in either record.
- The data owners have not said which convention CCDI-DCC's served values follow, and we have not asked them.
- PCDC served 24,232 records in the kept snapshot and 24,332 in the fresh one. Every grade and every S6 count is the same on both. This check does not explain the difference. Earlier paging audits in this repository report a PCDC `/subject` page that fails inside an HTTP 200 answer; how each snapshot's walk handled that page may account for it, but nothing here tests that.
- One model family (Claude) wrote LinkCheck 0.5.0, the check, the grader and this grading.

## Files

`out/check050.json` (the job's full output); `logs/summary.json`, `logs/stdout.txt`, `logs/stderr.txt` (the runner's record, unchanged).
