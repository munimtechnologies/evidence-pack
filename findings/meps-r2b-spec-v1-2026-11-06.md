# Check R2b specification: six single-file MEPS Statistical Briefs (#493, #496, #497, #533, #554, #558), v1

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before any job reads a variable of the three data files below. Pre-registration:
`findings/meps-r2b-prereg-v1-2026-11-06.md` (predictions unchanged). Transcription:
`findings/meps-r2b-transcription-v1-2026-11-06.md` + `findings/meps-r2b-transcription-v1/cells.csv`. Code:
`meps/r2b.py` 0.1.0 (Apache-2.0), which reuses `meps/r2conc.py` (R2) for the percentile ranking, the ASCII reader
and matching. Text CC BY 4.0. Research information about published statistics, not medical advice. No endorsement
by AHRQ is implied; AHRQ has not been contacted.

## Order of steps (as the pre-registration requires)

1. Transcription published (tag v0.9.43).
2. File-hash job `meps-r2b-hash-v1` (2026-11-06, 08:37-08:40 UTC): size, SHA-256, zip members and record counts
   of the three zips MV2's hands downloaded from meps.ahrq.gov. It read no variables.
3. This specification, with `meps/r2b.py` and its offline tests, published together (tag v0.9.44). The code was
   written while the hash job waited and was run only on synthetic test records (job `meps-r2b-unit-v1`: 24 tests
   pass, and the transcription gives each brief exactly as many graded cells as the code has keys: 40, 40, 40,
   40, 30, 40). No MEPS file was opened by any code before this commit.
4. The recompute job clones this tag, so it cannot read a file before this specification is public.

## Files (from the hash job)

| File | Zip | Bytes | SHA-256 | Member | Records x length |
|---|---|---|---|---|---|
| HC-171 (2014) | h171dat.zip | 9,755,087 | 3b9aecd7723f3f8427b222532b969a89e854bdea6363346668b621ef5bce75d0 | h171.dat | 34,875 x 5,398 |
| HC-209 (2018) | h209dat.zip | 9,759,504 | 6b031e8c316fcf9285b9e841c63472a0fbdebf8b04e6e9dfad94ef92373b9dee | h209.dat | 30,461 x 4,398 |
| HC-233 (2021) | h233dat.zip | 8,354,598 | 07cb5aa2ae0caf06475901b7364ef6bd1dc23c6624bf2bcd6837096afaaa05ba | h233.dat | 28,336 x 4,287 |

Each record count equals the codebook's, and each record length equals the last column of the last variable
(VARPSU) in census inventory v1 (`findings/meps-inventory-v1/inventory/H171.csv`, `H209.csv`, `H233.csv`). The
HC-209 download page lists its ASCII zip as about 11 MB; the file is 9.76 MB, but its member name, record count
and record length are HC-209's, so it is the 2018 file. The recompute job hashes each zip again and stops if the
hash differs.

## Gates (codebook value tables, read 2026-11-06; nothing is graded for a file unless all match)

- HC-233: 28,336 records; SDOHWT21F positive 18,400; SDENICPROD -15/-1/1/2 = 216/9,936/2,419/15,765; SDNOTRANS
  204/9,936/1,187/17,009; RACETHX 1-5 = 6,798/15,023/4,071/1,385/1,059; AGE31X -1 = 511; INSCOV21 1-3 =
  16,128/10,136/2,072; OFTSMK53 1-3 = 1,913/939/19,379.
- HC-171: 34,875 records; PERWT14F positive 33,162; TOTEXP14 zero 7,225; INSCOV14 1-3 = 17,829/12,078/4,968; AGE14X
  -1 = 209.
- HC-209: 30,461 records; PERWT18F positive 29,415; TOTEXP18 zero 4,620.
Every value table quoted here adds to its file's record count (checked by hand).

## Common rules

Weighted percentages and means use the named weight over persons with a positive weight. Codes below 0 (DK,
refused, inapplicable, cannot be computed) never count as "yes". A group with no weight gives "no estimate"
(graded as not close). Matching, the cap and the grades are the pre-registration's. **Underspecified** marks a
cell whose value depends on a choice the brief does not state. Such cells stay in the denominator.

## #554 and #558 (HC-233, 2021; questionnaire items)

- **Weight (our reading; every cell of both briefs is marked underspecified):** SDOHWT21F, the questionnaire's own
  weight. Its 18,400 positive values match the 18,400 records whose SDENICPROD is not -1 (by count only, not yet
  person by person; the job reports both mismatch counts). Neither brief names a weight.
- **Universe:** AGE31X >= 18, SDOHWT21F > 0, item answered 1 (yes) or 2 (no). Answers of -15 are left out.
- **Outcome:** #554 SDENICPROD = 1; #558 SDNOTRANS = 1.
- **Age:** AGE31X ("age around the time the supplement was initiated (AGE31X)", both briefs). #554 bands 18-24,
  25-34, 35-44, 45-64, 65+; young adults 18-24. #558 bands 18-34, 35-49, 50-64, 65+.
- **Race and ethnicity:** RACETHX 1 Hispanic, 2 non-Hispanic White, 3 non-Hispanic Black. "Non-Hispanic other" is
  RACETHX 4 or 5 in #554 (its definition includes Asian and Pacific Islander) and RACETHX 5 only in #558 (its
  definition lists Asian separately, and Figure 1 has no Asian row). The job also reports #558 with 4 or 5.
- **#554 other groups (young adults):** SEX 1 and 2; REGION31 1-4; RTHLTH31 and MNHLTH31 codes 1, 2, 3 and 4-5
  (fair/poor); currently smoke = OFTSMK53 1 or 2 (every day or some days), not = 3; ASTHDX 1 and 2. Figure 3 MSA
  cells are not computable (no MSA variable on HC-233; positive control REGION31). The text cell is all adults.
- **#558 insurance (our reading of the brief's definitions):** any private = INSCOV21 1 (people with public and
  private coverage count as private); among public-only (INSCOV21 2), Medicare = MCREV21 1 (people with Medicaid
  and Medicare count as Medicare), then Medicaid/CHIP = MCDEV21 1; uninsured = INSCOV21 3. Figure 4 crosses these
  with RTHLTH31 1-3 ("good or better") and 4-5.
- **#558 conditions (ever told):** diabetes DIABDX_M18 = 1; emphysema EMPHDX = 1; cancer CANCERDX = 1; heart
  disease = any of CHDDX, ANGIDX, MIDX, OHRTDX = 1; current smoker OFTSMK53 1 or 2; asthma ASTHDX = 1;
  hypertension BPMLDX = 1 (told on two or more visits); stroke STRKDX = 1; high cholesterol CHOLDX = 1.
  "None" = none of these nine. **Number of conditions (our reading):** the count over the same nine items (Figure 5
  lists current smoking among the conditions). Graded with the table's labels (at least 2 and at least 3). The job
  also reports at least 1-4 and the eight-item count without smoking, to settle the label conflict in the
  transcription note.

## #493 (HC-171, 2014): expenses by type of service

- **Weight:** PERWT14F > 0. **Age (our reading; marked underspecified):** AGE14X (age at 31 Dec 2014). For the persons
  with AGE14X = -1, who left the survey's scope during the year, AGELAST is used. Columns are all ages, under 65 and
  65+.
- **Types of service (our reading; marked underspecified):** any = TOTEXP14; hospital inpatient = IPTEXP14
  (facility plus doctor, including zero-night stays); ambulatory = OBVEXP14 + OPTEXP14 + ERTEXP14 (the Findings
  describe "office-based visits, hospital outpatient care, and emergency room services"); prescribed medicines =
  RXEXP14; dental = DVTEXP14; home health and other = HHAEXP14 + HHNEXP14 + VISEXP14 + OTHEXP14. These five add up
  to TOTEXP14, and the job counts any person for whom they don't (by more than $1).
- **Figure 1:** % of persons with an expense > 0. **Figure 2:** mean among persons with an expense. **Figure 3:**
  weighted median among persons with an expense: the smallest value whose cumulative weight reaches half
  (underspecified). Only "any service, all ages" in Figures 1-2 is not marked underspecified.

## #496 (HC-171, 2014): spending tiers

- Ranking as in R2 (the brief's own rule, the same as #506/#521/#540): high = top 10%, middle = the rest of the top
  50%, and within the bottom 50%, none = TOTEXP14 = 0 and low = the rest. Age is AGE14X ("age at the end of the
  year 2014"), or AGELAST for persons out of scope by then. Bands are 0-17, 18-44, 45-64 and 65+.
- Figure 1 is the age distribution within each tier. Figures 2a and 2b are the INSCOV14 distribution (1 any private,
  2 public only, 3 uninsured all year) within each tier, among ages 0-17 and 18-64.

## #497 (HC-171, 2014) and #533 (HC-209, 2018): concentration

- Ranking, curve and means exactly as R2's specification (`findings/meps-r2-spec-conc-v1-2026-11-03.md`). Curve
  cells are underspecified (as in R2). #497 has no 100% row. #533's Figure 2 includes "Overall".
- #497 Figure 3: each age band's share of persons and of total spending (age as for #496). The job reports both
  shares, which settles the 35.5/35.9 conflict in the transcription note.
- #497 Figure 4 (our reading; marked underspecified): ranking within each age group. The text supports this: "the
  top 5% ... accounted for 32.6 percent of the total expenditures for this age group".
- #533 Figure 3 treated conditions: not computable from HC-209 (r2conc.condition_check, as for #540).

## Deviations from the draft

None in method. The draft (written before the hash job) differs from this text only in the filled file table, the
order-of-steps section and "by more than $1" in #493, which states the tolerance the code already used.
`meps/r2b.py` names this file as `findings/meps-r2b-spec-v1-*.md`; it is unchanged from the unit-tested version.

## Limits

The readings are ours. #554 and #558 share one file and one weight, and #497 and #533 share R2's method, so their
results are not independent. A failed cell may be our error.
