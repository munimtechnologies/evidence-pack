# Pre-registered check: LinkCheck 0.5.0 reads race and ethnicity under both OMB conventions

MV2 of Munim, Inc. Text CC BY 4.0, code Apache-2.0. Written on 2026-10-24 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed it.** Research and data-quality software only; not medical advice. We have not contacted the data owners.

**Status: PRE-REGISTERED.** This file is published at evidence-pack tag v0.9.1 before the sealed job `linkcheck-050-v1` runs. The job's setup step downloads its code from that tag and waits until the tag is public. The results will be graded exactly as written here, pass or fail, in a separate results file.

## Why

The census of NCI's Childhood Cancer Data Initiative (CCDI) federation (tag v0.5.5 and later) reads race with OMB's 1997 categories and ethnicity as a separate Hispanic-or-Latino question. OMB revised SPD 15 in 2024: one combined question with seven categories, including "Hispanic or Latino" and "Middle Eastern or North African". Under the 2024 standard, a person whose combined list has categories but not "Hispanic or Latino" is not Hispanic or Latino. Under 1997, a missing ethnicity answer is just missing.

The CCDI data model follows the 2024 combined list, while the Federation API keeps a separate 1997-style ethnicity field. CCDI-DCC serves no "Not Hispanic or Latino" record. On the 2026-10-24 snapshot, 4,090 of its 59,795 records carry an informative ethnicity (all Hispanic or Latino) and 49,743 an informative 1997 race. Our post-hoc demographics note (tag v0.5.8, parts 2-4) used aggregate filter counts from 2026-10-22. They put 46,650-47,101 CCDI-DCC subjects at one of the five named race categories with ethnicity "Not reported", the only other ethnicity value CCDI-DCC serves. The note also found 24 CCDI-DCC records whose race is the single string "White, Hispanic or Latino", and at least 20 of them are served as Hispanic or Latino. Our reading of the gap ("a pooled analysis cannot tell not Hispanic from not asked") was inferred, not tested.

Other sources state ethnicity in both directions. Among records with a stated ethnicity, the Hispanic or Latino share is 17.1% in KidsFirst, 14.1% in PCDC, 8.0% in StJude and 6.2% in Treehouse. These are arithmetic on that note's endpoint counts.

LinkCheck 0.5.0 (`linkcheck/linkcheck/core.py`) adds:
- `race_standard()`: per record, which convention its own values follow: `1997`, `2024`, `both`, `contradictory`, `undetermined` or `no_value`. The 2024 reading also splits a comma-joined value ("White, Hispanic or Latino") when every part is a category; the 1997 reading does not. A convention can be **declared** for a source (`--declare CCDI-DCC=2024`); it fills in `undetermined` records only.
- `hispanic()`: Hispanic or Latino origin under that convention: `H`, `NH`, `NH_implied` (a 2024-style list without Hispanic or Latino) or unknown.
- A `standards` report section: per source, the conventions and origins. For linked pairs, the origin agreement (with `NH_implied` counted as `NH`), race agreement on the 2024 categories, the convention pair, and `implied_nh_vs_stated`, which records what the other record says when one record's "not Hispanic" is only implied. There are also three new cohort columns. Every 0.4.0 section is meant to be unchanged.

This gives a test of the declared reading. If CCDI-DCC's unreported ethnicity really means "not Hispanic" (the 2024 combined list), then linked records in other sources that state ethnicity themselves should rarely say Hispanic or Latino. If it means "not asked", they should say so about as often as Hispanic children occur in those sources.

## What the job does

`linkcheck-050-v1` (1 CPU, 3 GB, network on for the download only) downloads, unchanged and with SHA-256 logged, LinkCheck 0.5.0 and this check from tag v0.9.1, LinkCheck 0.4.0 from tag v0.8.9, and the snapshot finder from tag v0.8.0. It runs every test on made-up data, then `check050.py`. That runs 0.4.0 (in its own process), 0.5.0 with nothing declared, and 0.5.0 with `CCDI-DCC=2024`, on every snapshot the machine keeps: the kept second snapshot (`/data/ccdi-raw-snapshot2`), if present, and the newest complete fresh snapshot under `/data/ccdi-fresh-v1`. No request goes to the federation. A machine that keeps no snapshot grades nothing.

## Predictions

A prediction holds if it passes on every snapshot where it can be graded.

- **S1 (backward compatibility).** On each snapshot, 0.5.0's result equals 0.4.0's in every key except `tool` and the new `linkcheck.standards`. Its cohort table has 0.4.0's columns first, identical row for row, plus exactly `hispanic`, `hispanic_conflict` and `race_standard`.
- **S2.** The only served records with a 2024-only category ("Hispanic or Latino" or "Middle Eastern or North African") in their race list are CCDI-DCC's 24 "White, Hispanic or Latino" records. In numbers: CCDI-DCC has `values_2024_only` = {"Hispanic or Latino": 24} and `hispanic_in_race_list` = 24. Of those records, at least 20 read as `both`, `both` + `2024` = 24, and none reads as `contradictory`. Every other source has no 2024-only value and no record read as `2024`, `both` or `contradictory`. For six of the seven sources this is a real prediction, because only CCDI-DCC's race values were enumerated before.
- **S3 (an identity of the code).** Per source, the records read as `1997`, `both` or `contradictory` are exactly those that 0.4.0's completeness counts as having an informative ethnicity. This checks that both readings use the same field. It is not a finding.
- **S4.** With nothing declared, no record anywhere is `NH_implied`, and CCDI-DCC serves no record with ethnicity "Not Hispanic or Latino". (Known from an earlier snapshot, so this is a replication.)
- **S5.** With CCDI-DCC declared 2024, between 46,650 and 47,101 CCDI-DCC records (inclusive) are `NH_implied`: those with a named race and no ethnicity answer. This tests the new code against the bound the demographics note derived from filter counts two days earlier. It fails if the code miscounts, or if the source changed inside unchanged totals.
- **S6 (the test of the declared reading).** With CCDI-DCC declared 2024, take the exact-link pairs where one record is `NH_implied` and the other states H or NH itself. **At least 5% of those stated values are "Hispanic or Latino."** That would contradict the 2024 reading of CCDI-DCC's unreported ethnicity.
  - Our reasoning: if "not reported" in CCDI-DCC often means "not asked", the linked records should say Hispanic about as often as the linked sources do in general (6-17% of stated values, above). If it means "not Hispanic", they should rarely say so, at a rate near ordinary disagreement between sources. CCDI-DCC's stated Hispanic share (6.8% of all its records) is low beside the other sources, which hints at the first.
  - S6 is graded only if there are at least 100 such pairs; otherwise it is "not gradable".
  - How we will read the result, fixed now: below 2% supports the 2024 reading; 2% to under 5% is inconclusive (S6 fails, and we will say it is inconclusive, not that the reading holds); 5% or more contradicts it (S6 passes). As context, the job also reports the 1997 ethnicity disagreement among linked pairs where both records state ethnicity.

## Reported, not graded

Per source and per source pair: conventions, origins, `implied_nh_vs_stated`; persons whose records say both Hispanic and not, with and without the declaration; the 1997 ethnicity conflicts for comparison.

## Limits, stated in advance

- Linked records are not ground truth: a disagreement can be an error in either record. S6 measures consistency between sources, not correctness.
- The declaration is our assumption, made to test it. The data owners have not said which convention CCDI-DCC's served values follow.
- One model family (Claude) wrote 0.5.0, this check and its grading.
- Outputs are aggregates only: counts and source names. The cohort tables, which hold record ids, are written to a temporary folder, compared and deleted. `check050.py` refuses to write anything shaped like a COG USI.

## Files

`check050.py` (the check), `test_check050.py` (its tests on made-up data), `get_code.py` (setup: the downloads), `job.json` (the sealed job as filed).
