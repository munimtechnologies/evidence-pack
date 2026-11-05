# Exploratory addendum to check R2, Brief #507: which child-counting rule reproduces Table 1? (pre-registration, v1)

MV2 of Munim, Inc., 2026-11-05. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before any job reads the extra variables listed below. Code: `meps/r507x.py` 0.1.0 (Apache-2.0). Text CC BY
4.0. Research information about published statistics, not medical advice. No endorsement by AHRQ is implied;
AHRQ has not been contacted. **This is exploratory and post hoc: it was written after seeing the R2 result for
#507, it explains a gap, and it changes no R2 grade.**

## What prompts it

In check R2 (`findings/meps-r2-results-v1-2026-11-05.md`), Brief #507's Table 1 matched our population and all four
poverty rows to within one weighted family. Within each row, however, about 875,605 weighted families that we
count as having children (members aged 0-17 by AGELAST) sit in the brief's no-children columns, and their adult
count is unchanged. So AHRQ counted some members as neither adults nor children. Our working guess is babies born
during 2015 after an interview round whose age variable AHRQ used: such babies have age -1 ("inapplicable") in
that round.

## Fixed (unchanged from the graded specification)

CPS families on 12/31/15 (DUID + CPSFAMID; members FCRP1231 >= 0 and FAMWT15C > 0); the reference person's
FAMWT15C and POVCAT15; non-elderly = no member with AGELAST >= 65; family TOTEXP15 > 0; families with no adult
are left out of Table 1. Only the adult and child counts change.

## The nine rules (fixed now; no other rule is added after the job runs)

| Rule | Adult | Child |
|---|---|---|
| R0 | AGELAST >= 18 | AGELAST <= 17 (the graded specification) |
| R1 | AGE15X >= 18 | 0 <= AGE15X <= 17 (age as of 12/31/15; -1 counts as neither) |
| R2 | AGE31X >= 18 | 0 <= AGE31X <= 17 (round 3/1; -1 = neither) |
| R3 | AGE42X >= 18 | 0 <= AGE42X <= 17 (round 4/2; -1 = neither) |
| R4 | AGE53X >= 18 | 0 <= AGE53X <= 17 (round 5/3; -1 = neither) |
| R5 | AGELAST >= 18 | AGELAST <= 17 and PERWT15F > 0 |
| R6 | AGELAST >= 18 | AGELAST <= 17 and INSC1231 = 1 (in scope on 12/31/15) |
| R7 | AGELAST >= 18 | AGELAST <= 17 and REFRL15X = 4 (child of the household reference person) |
| R8 | AGELAST >= 18 | AGELAST <= 17 and the person's mother or father (MOPID53X / DAPID53X) is a member of the same family |

## Gates (HC-181 online codebooks, read 2026-11-05; each table checked by hand to add up to 35,427)

All of R2's #507 gates, plus: PERWT15F > 0 for 33,893; INSC1231 1 / 2 = 35,067 / 360; REFRL15X 1-11 and 91 =
14,177 / 5,578 / 977 / 11,736 / 154 / 752 / 897 / 621 / 37 / 51 / 193 / 254; MOPID53X = -1 for 22,791 and
DAPID53X = -1 for 26,919 (all others 101-402); and for (-1, 0-17, 18-64, 65-85): AGE15X 235 / 9,615 / 21,210 /
4,367; AGE31X 997 / 9,541 / 20,735 / 4,154; AGE42X 504 / 9,608 / 21,009 / 4,306; AGE53X 235 / 9,563 / 21,232 /
4,397. If any gate fails, nothing is reported but the gate.

## Measure and predictions

A rule **reproduces** Table 1 if each of its 16 weighted counts, rounded half-up to a whole family, equals the
printed count. Also reported per rule: the number of exact cells, the largest and summed absolute gaps, the four
column totals, families with no adult, and the 16 structure cells of Figures 3-4 (other than "All") recomputed
under the rule. The best rule has the most exact cells, with ties broken by the smallest summed gap.

- **E1:** at least one of R1-R8 reproduces all 16 Table 1 counts.
- **E2:** the best rule is one of the round-specific age rules R2, R3 or R4.

Both are graded as written. If no rule reproduces Table 1, the rule stays unidentified; we report the closest one
and do not add rules to this run.

## Data and outputs

HC-181 ASCII zip (SHA-256 75e50de4...33822e5ee, as in R2), copied into the job folder by MV2's hands. Outputs:
`r507x.json` (gates, per-rule tallies, Table 1 comparisons, structure cells) and `table1-rules.csv`. Only aggregate
weighted counts and estimates leave the job.
