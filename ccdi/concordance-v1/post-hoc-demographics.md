# Post hoc: field completeness by source, and a race/ethnicity standards mismatch (CCDI census v1)

MV2 of Munim, Inc. Text CC BY 4.0. Written on 2026-10-22 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed this note. Nothing in it was pre-registered.** This is research information about data quality, not medical advice.

- **Part 1** is arithmetic on the aggregates in `out/concordance.json` (the 2026-10-22 snapshot of `ccdi-concord-v1`). The percentages were worked by hand; recheck them against that file.
- **Part 2** adds four aggregate-only filter queries to the CCDI Data Federation API (2026-10-22, about 22:20 UTC) and reads the public CCDI data model and Federation API specification. No record or participant ID was read or kept: only each source's `counts.all`.
- **Part 3** corrects one sentence of `results.md`.
- **Part 4** (added at tag v0.5.8, about 23:45 UTC the same day) splits every CCDI-DCC race value by ethnicity with 12 more aggregate-only filter queries, tightens the part 2 bound, and reports one comparison that turned out not to discriminate.

## 1. How complete are the fields each source serves?

Share of served subject records with an informative value. Vital status counts Alive or Dead. Sex counts M or F. Ethnicity counts Hispanic or Latino, or Not Hispanic or Latino. Everything else (Unknown, Not reported, Unspecified, U, null) counts as not informative.

| Source | Records served | Vital status | Sex | Ethnicity |
|---|---|---|---|---|
| CCDI-DCC | 59,795 | 13,319 (22.3%) | 59,363 (99.3%) | 4,090 (6.8%) |
| KidsFirst | 38,440 | 2,573 (6.7%) | 37,949 (98.7%) | 28,160 (73.3%) |
| PCDC | 24,332 | 0 (0%) | 24,017 (98.7%) | 20,577 (84.6%) |
| StJude | 14,681 | 0 (0%) | 13,356 (91.0%) | 11,414 (77.7%) |
| Treehouse | 12,723 | 0 (0%) | 12,194 (95.8%) | 8,876 (69.8%) |
| ccdi-ecDNA | 3,205 | 2,638 (82.3%) | 3,092 (96.5%) | 0 (0%) |
| ccdi-iusccc-pst | 504 | 54 (10.7%) | 502 (99.6%) | 101 (20.0%) |
| **All seven** | **153,680** | **18,584 (12.1%)** | **150,473 (97.9%)** | **73,218 (47.6%)** |

- **Vital status is the scarce field.** Only 12.1% of served records say Alive or Dead. Three sources serve none. For PCDC, the count endpoint reports 22,086 of 24,432 subjects (90.4%) as Alive or Dead, but the served records carry no vital status (pre-registered H2).
- **ccdi-iusccc-pst serves deaths but no survivors.** Its 504 records hold Dead 54, Unknown 339 and Unspecified 111. No record is served as Alive, so this source alone cannot support a survival estimate. Its count endpoint shows the same values.
- **Race is left out of the table on purpose.** It is multi-valued in the Federation API, and the census kept value counts, not per-record counts. In CCDI-DCC the race values sum to 60,226 for 59,795 records, so a record-level share cannot be derived from these aggregates.
- **CCDI-DCC's 6.8% ethnicity figure is mostly an artifact of standards.** See parts 2 and 4.

## 2. CCDI-DCC's ethnicity: the 2024 race/ethnicity standard meets the 1997 one

**What the census saw.** CCDI-DCC serves 59,795 subjects with ethnicity "Hispanic or Latino" (4,090) or "Not reported" (55,705). It serves **no** "Not Hispanic or Latino" record. Every other source with ethnicity data serves thousands (KidsFirst 23,336; PCDC 17,747; StJude 10,505; Treehouse 8,323). A live recount of the ethnicity count endpoint on 2026-10-22 (about 22:10 UTC) gave the same numbers.

**What the two specifications say.**
- The **CCDI data model** (github.com/CBIIT/ccdi-model, `model-desc/ccdi-model-props.yml`, main branch, read on 2026-10-22) defines `race` as a list. Its description cites the OMB SPD 15 revision, and its allowed values include "Hispanic or Latino" and "Middle Eastern or North African" alongside the other race categories. We found no `ethnicity` property in the file. This follows the 2024 revision of OMB SPD 15, which uses "a combined race/ethnicity question with co-equal categories" (U.S. Census Bureau). Agencies must comply by March 2029.
- The **CCDI Federation API** (github.com/CBIIT/ccdi-federation-api, `swagger.yml`, read on 2026-10-22) keeps the two fields apart, as the 1997 standard did:
  - `race` (caDSR CDE 2192199 v1.00) has no "Hispanic or Latino" value;
  - `ethnicity` (caDSR CDE 2192217 v2.00) is single-valued: Hispanic or Latino, Not Hispanic or Latino, Unknown, Not reported, Not allowed to collect.

**Aggregate filter counts, CCDI-DCC, 2026-10-22 about 22:20 UTC** (`/subject?race=...&ethnicity=...&per_page=1`; only `counts.all` read):

| race | ethnicity | CCDI-DCC subjects |
|---|---|---|
| White | Not reported | 40,780 |
| White | Hispanic or Latino | 2,503 |
| Black or African American | Not reported | 4,382 |
| Unknown | Not reported | 3,939 |

The first two rows sum to 43,283, exactly the snapshot's served count for race "White" in CCDI-DCC. So the filter counts and the census agree.

**Reading (an inference, not confirmed by the data owners).** The pattern fits a translation from the model's combined list into the API's two fields:
- "Hispanic or Latino" in the list becomes ethnicity "Hispanic or Latino";
- any other list becomes ethnicity "Not reported".

Under the combined question, a list without "Hispanic or Latino" is a complete answer. But a served "Not reported" cannot tell that apart from a study that never asked. As a result, at least 40,780 CCDI-DCC subjects (68.2%) are served with a named race and ethnicity "Not reported". This is a lower bound from the White row alone; with the Black row it is at most 45,162 (75.5%), because multi-race records may fall in both rows. **Part 4 splits every race value and tightens the overall figure to 46,650-47,101 subjects (78.0%-78.8%).**

**Why it matters for pooled cohorts.**
- An analysis that treats "Not reported" as missing drops more than three quarters of CCDI-DCC from any ethnicity breakdown. It also makes the Hispanic share of the remaining CCDI-DCC records look like 100%.
- An analysis that treats it as "Not Hispanic" may be wrong for studies that never collected ethnicity.
- Neither choice is documented where the API serves the value.
- The same mismatch will meet every resource that adopts the 2024 standard before the API does.
- It probably explains much of the 17,924 Participant Index pairs whose ethnicity was uninformative in the census. We did not measure how much.

**Prior art.** On 2026-10-22 we searched the web for any description of how the CCDI Federation maps the CCDI model's combined race field to ethnicity. We found none. We have not read the CCDI-DCC node's source code.

## 3. Correction to results.md

`results.md` (tag v0.5.6) says the 24 CCDI-DCC records with race "White, Hispanic or Latino" carry a value that "mixes an ethnicity into race". That wording was wrong. The CCDI data model allows a race list holding both "White" and "Hispanic or Latino" (part 2). These 24 records are served with that list as a single string, which is not a value in the Federation API's race list, and the race endpoint counts them as missing. The census numbers do not change. `results.md` is updated to point here.

## 4. Every CCDI-DCC race value, split by ethnicity (added at v0.5.8)

**Queries.** On 2026-10-22, about 23:40-23:50 UTC, we read the race count endpoint (`/subject/by/race/count`) and the ethnicity count endpoint (`/subject/by/ethnicity/count`), and ran 12 more aggregate-only filter queries (`/subject?race=<value>&ethnicity=<value>&per_page=1`, `counts.all` per source only). The four rows from part 2 were not re-run.

| race (served value) | served count | ethnicity "Not reported" | ethnicity "Hispanic or Latino" | rows sum to count? |
|---|---|---|---|---|
| White | 43,283 | 40,780 (part 2) | 2,503 (part 2) | yes |
| Not Reported | 5,830 | 4,621 | 1,209 | yes |
| Black or African American | 4,481 | 4,382 (part 2) | 99 | yes |
| Unknown | 4,115 | 3,939 (part 2) | 176 | yes |
| Asian | 1,537 | 1,513 | 24 | yes |
| Not allowed to collect | 471 | 471 | 0 | yes |
| American Indian or Alaska Native | 342 | 298 | 44 | yes |
| Native Hawaiian or other Pacific Islander | 143 | 128 | 15 | yes |
| **Sum of rows** | **60,202** | **56,132** | **4,070** | |

The race endpoint also reports 24 CCDI-DCC records with race missing (the 24 "White, Hispanic or Latino" strings of part 3). 60,202 + 24 = 60,226, the census sum in part 1. CCDI-DCC serves only the two ethnicity values, and every race value's two filter counts add up exactly to its served count, so the split is complete.

**The tightened bound.** Call a race value "named" if it is one of the five OMB race categories (White, Black or African American, Asian, American Indian or Alaska Native, Native Hawaiian or other Pacific Islander).
- **Upper bound:** every subject with a named race and ethnicity "Not reported" appears in at least one named-race row, so there are at most 40,780 + 4,382 + 1,513 + 298 + 128 = **47,101** (78.8% of 59,795).
- **Lower bound:** 55,705 subjects are served with ethnicity "Not reported", and at most 24 of them have race missing, so at least 55,681 have a race value. Those without a named race all sit in the Not Reported, Unknown or Not allowed to collect rows, which hold 4,621 + 3,939 + 471 = 9,031. So at least 55,681 - 9,031 = **46,650** (78.0%) have a named race.
- So **78.0%-78.8% of CCDI-DCC subjects are served with a named race and ethnicity "Not reported"**, against 68.2% (at least) in part 2. The width of the range comes from multi-race records: the rows sum to 56,132 for at most 55,705 subjects, so multi-race "Not reported" subjects add at least 427 extra row entries.
- For scale: 93.2% of CCDI-DCC subjects (55,705) are served with an uninformative ethnicity. In the four other sources with ethnicity data, the share served as Unknown or Not reported is 14.2% (PCDC, 3,477 of 24,432), 22.2% (StJude, 3,265 of 14,681), 22.7% (KidsFirst, 8,284 of 36,444) and 24.1% (Treehouse, 3,062 of 12,723), from the ethnicity count endpoint at about 23:45 UTC. Treehouse also has 785 records with ethnicity missing, not included here.

**A check that did not discriminate (reported because it was tried).** If "Hispanic or Latino" alone, with no race category, were translated to race "Not Reported" and ethnicity "Hispanic or Latino", CCDI-DCC might show an unusually large share of Hispanic subjects with no named race. It does not stand out:

| Source | Hispanic or Latino subjects | with race Not Reported or Unknown | share |
|---|---|---|---|
| CCDI-DCC | 4,090 | 1,209 + 176 = 1,385 | 33.9% |
| PCDC | 2,916 | 96 + 901 = 997 | 34.2% |
| StJude | 909 | 271 + 0 = 271 | 29.8% |
| KidsFirst | 4,824 | 0 + 1,889 = 1,889 | 39.2% |
| Treehouse | 553 | 4 + 85 = 89 | 16.1% |

CCDI-DCC sits inside the range of the sources that use the 1997 two-question format. Many Hispanic respondents choose no race category under that format too, so this pattern cannot tell a translation from ordinary reporting. The shares count race-value rows, not subjects, so a multi-race subject could be counted twice. For CCDI-DCC that is at most 4 extra entries (see the next point); for the other sources we did not measure it. The inference in part 2 rests on the zero "Not Hispanic or Latino" count and the two specifications, not on this table.

**One more consistency point.** The Hispanic rows sum to 4,070, but CCDI-DCC serves 4,090 Hispanic subjects. Every Hispanic subject with a race value is in at least one row, so at most 4,070 of them have a race value, and at least 20 of the 24 race-missing records are served as Hispanic. That fits part 3: those 24 records carry "Hispanic or Latino" inside their race list.

## Limits
- Everything here is post hoc. It was found by the same AI agents that wrote the census, and no one else has checked it.
- The filter counts are a later snapshot than the census (same day, about four to eight hours later). Part 4's counts were read over about ten minutes; a source updating in that window would break the exact closures, and none did.
- The translation rule is inferred from counts and two specifications, not from the node's code or its maintainers.
- Part 1 shares are of served records, not of children: a child served by two sources is counted twice.
- PCDC answers some small filtered cohorts with an error instead of a count (it says the cohort is too small to share); those cells are not used in part 4.
- The counts were read through a web-fetch tool that summarises pages; every CCDI-DCC count in part 4 was checked by the exact row closures above.

## Sources
- `out/concordance.json` in this folder (sealed job `ccdi-concord-v1`, 2026-10-22).
- CCDI data model: https://github.com/CBIIT/ccdi-model (`model-desc/ccdi-model-props.yml`, read 2026-10-22).
- CCDI Federation API specification: https://github.com/CBIIT/ccdi-federation-api (`swagger.yml`, read 2026-10-22).
- CCDI Data Federation Resource API v1: https://federation.ccdi.cancer.gov/api/v1 (accessed 2026-10-22).
- U.S. Census Bureau, "Updates to Race/Ethnicity Standards for Our Nation": https://www.census.gov/about/our-research/race-ethnicity/standards-updates.html (OMB published the revised SPD 15 on 2024-03-28; Federal Register document 2024-06469).
