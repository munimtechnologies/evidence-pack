# Impossible summary statistics in ClinicalTrials.gov posted results: a census of all 80,504 records (2026-10-15)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

## What was done

A sealed job (`ctgov_audit.py` v0.2, stdlib Python, public ClinicalTrials.gov API v2) read the outcome-measure results of **every study with posted results** on 2026-10-15 (80,504 studies, 670,344 outcome measures, 4,982,064 numeric cells). It applied checks that no real data can fail, allowing for the rounding of the posted numbers:

| Check | What cannot be true | Cells it applies to |
|---|---|---|
| negative_dispersion | a standard deviation or standard error below zero | 1,656,350 |
| inverted_interval | a lower limit above its upper limit (IQR, full range, 95% CI) | 825,676 |
| center_outside_interval | a median outside its own IQR or range, a mean outside its full range, an estimate outside its own CI | 841,191 |
| sd_above_width | an SD of a percent-of-day/time measure larger than the full 0-100 width (times sqrt(n/(n-1))), which even a change score cannot reach | (bounded measures) |

## Result

**45 of 80,504 studies (about 1 in 1,800) post at least one summary statistic that is impossible as written: 86 cells in all. 14 of the 45 studies have the error in a primary outcome.**

| Check | Studies | Cells | Studies with it in a primary outcome |
|---|---|---|---|
| center_outside_interval | 16 | 30 | 7 |
| inverted_interval | 18 | 38 | 2 |
| negative_dispersion | 8 | 15 | 3 |
| sd_above_width | 3 | 3 | 2 |

None of the 45 studies appears under two checks. Six records were re-read through the live API on 2026-10-15 (marked "live" below), and all six still show the values listed.

### One pattern explains every inverted interval

In **all 38 inverted-interval cells (18 studies), one of the two limits equals the point estimate exactly**: in 12 studies the lower limit equals the estimate, in 6 the upper limit does. The other limit then lies on the wrong side. Examples: geometric mean 422, range "422 to 337" (NCT00392015); 2.11%, CI "2.11 to 1.30" (NCT03278067); median 0 months, range "15 to 0" (NCT00324987). This points to one data-entry mechanism: the estimate typed into a limit field, with the single real limit in the other. It is not a mix of random typos. A validation rule that rejects lower > upper would have caught all 38 cells.

### Negative standard deviations: the sign of the change score carried over

In 7 of the 8 studies, the negative SD belongs to a change-from-baseline measure or sits next to a negative mean. The exception is NCT00821236, where the SD of 0.08 logMAR is simply the mean with a minus sign. In NCT01284114, 5 of its 6 posted SDs are negative (live). In NCT00329160, 3 of its 4 SDs are negative, including a primary outcome (live).

### Estimates outside their own interval

These cells are more varied. Several are structural: a count of participants posted with a 95% CI that looks like an odds ratio's (NCT00810641, primary, 38 participants, "CI 2.48 to 13.78", live), a one-sided lower bound typed into the upper-limit field (NCT00777556, 90.1% with "upper" 86.4), and an area under the curve next to a per-month interval (NCT00533949). Others look like plain typos (NCT01468597, primary: median blood loss 1,996 mL with IQR 937 to 1,572 mL, live).

### The full list

| NCT | Check | Outcome type | As posted (example cell) |
|---|---|---|---|
| [NCT01468597](https://clinicaltrials.gov/study/NCT01468597?tab=results) | center | PRIMARY | median 1996 mL, IQR 937-1572 (live) |
| [NCT03029689](https://clinicaltrials.gov/study/NCT03029689?tab=results) | center | SECONDARY | 664 cells/mm3, interval 430-658 |
| [NCT03878160](https://clinicaltrials.gov/study/NCT03878160?tab=results) | center | SECONDARY | 18, interval 13-13 |
| [NCT01384539](https://clinicaltrials.gov/study/NCT01384539?tab=results) | center | SECONDARY | 3.9 mg/dL, interval 0.3-2.1 |
| [NCT00574119](https://clinicaltrials.gov/study/NCT00574119?tab=results) | center | PRIMARY | 7.4, interval 2.2-3.9 |
| [NCT00810641](https://clinicaltrials.gov/study/NCT00810641?tab=results) | center | PRIMARY | 38 participants, 95% CI 2.48-13.78 (live) |
| [NCT01262976](https://clinicaltrials.gov/study/NCT01262976?tab=results) | center | SECONDARY | 180, interval 316-1545 (3 cells) |
| [NCT05648565](https://clinicaltrials.gov/study/NCT05648565?tab=results) | center | SECONDARY | 7, interval 2.9-5.1 |
| [NCT00533949](https://clinicaltrials.gov/study/NCT00533949?tab=results) | center | SECONDARY | 265.4 (AUC), interval 55.9-76.9 |
| [NCT02721979](https://clinicaltrials.gov/study/NCT02721979?tab=results) | center | SECONDARY | median change -17.65, interval 0.50-50 |
| [NCT00777556](https://clinicaltrials.gov/study/NCT00777556?tab=results) | center | PRIMARY | 90.1%, upper limit 86.4, lower NA (2 cells) |
| [NCT02582775](https://clinicaltrials.gov/study/NCT02582775?tab=results) | center | SECONDARY | change -30, range 10-100 (3 cells) |
| [NCT04684836](https://clinicaltrials.gov/study/NCT04684836?tab=results) | center | PRIMARY | 0.047, interval 0.00-0.0153 |
| [NCT05221749](https://clinicaltrials.gov/study/NCT05221749?tab=results) | center | PRIMARY | 70000 CFU/mL, interval 1-7 (4 cells) |
| [NCT04026711](https://clinicaltrials.gov/study/NCT04026711?tab=results) | center | SECONDARY | FEV1 change -0.01 L, interval 0.18-0.24 |
| [NCT01826851](https://clinicaltrials.gov/study/NCT01826851?tab=results) | center | PRIMARY | median 2.5, IQR 0-1.25 (5 cells) |
| [NCT00392015](https://clinicaltrials.gov/study/NCT00392015?tab=results) | inverted | SECONDARY | 422, range 422 to 337 (3 cells) |
| [NCT05093049](https://clinicaltrials.gov/study/NCT05093049?tab=results) | inverted | SECONDARY | -0.3 cm, -0.3 to -1.0 |
| [NCT01967134](https://clinicaltrials.gov/study/NCT01967134?tab=results) | inverted | SECONDARY | 0.0000, 0.0000 to -0.0003 |
| [NCT02433483](https://clinicaltrials.gov/study/NCT02433483?tab=results) | inverted | OTHER | 99.5%, 99.8 to 99.5 |
| [NCT04827732](https://clinicaltrials.gov/study/NCT04827732?tab=results) | inverted | SECONDARY | 0, 0 to -3.33 |
| [NCT04415632](https://clinicaltrials.gov/study/NCT04415632?tab=results) | inverted | SECONDARY | -0.1 mmol/L, -0.1 to -2.8 |
| [NCT01877187](https://clinicaltrials.gov/study/NCT01877187?tab=results) | inverted | SECONDARY | 95.1%, 95.1 to 9.51 |
| [NCT03278067](https://clinicaltrials.gov/study/NCT03278067?tab=results) | inverted | SECONDARY | 2.11%, 2.11 to 1.30 |
| [NCT03688620](https://clinicaltrials.gov/study/NCT03688620?tab=results) | inverted | PRIMARY | 0.11%, 0.11 to 0.00 (16 cells) |
| [NCT01875250](https://clinicaltrials.gov/study/NCT01875250?tab=results) | inverted | SECONDARY | -99%, -84 to -99 (2 cells) |
| [NCT04037436](https://clinicaltrials.gov/study/NCT04037436?tab=results) | inverted | SECONDARY | 69.46 g/day, 69.46 to 22.29 |
| [NCT02689063](https://clinicaltrials.gov/study/NCT02689063?tab=results) | inverted | SECONDARY | 0 min, 9.9 to 0 |
| [NCT05764239](https://clinicaltrials.gov/study/NCT05764239?tab=results) | inverted | PRIMARY | -3.85%, 0 to -3.85 (2 cells) |
| [NCT02320175](https://clinicaltrials.gov/study/NCT02320175?tab=results) | inverted | SECONDARY | 26.5%, 26.5 to 12.7 |
| [NCT04460183](https://clinicaltrials.gov/study/NCT04460183?tab=results) | inverted | SECONDARY | 5.00 days, 5.00 to 3.00 |
| [NCT04294641](https://clinicaltrials.gov/study/NCT04294641?tab=results) | inverted | SECONDARY | 0, 0.00 to -0.459 |
| [NCT00324987](https://clinicaltrials.gov/study/NCT00324987?tab=results) | inverted | SECONDARY | 0 months, 15 to 0 |
| [NCT04216329](https://clinicaltrials.gov/study/NCT04216329?tab=results) | inverted | OTHER | -0.875, -0.11 to -0.875 (2 cells) |
| [NCT00770692](https://clinicaltrials.gov/study/NCT00770692?tab=results) | negative SD | SECONDARY | -35.1 min, SD -25.0 (live) |
| [NCT00821236](https://clinicaltrials.gov/study/NCT00821236?tab=results) | negative SD | PRIMARY | 0.08 logMAR, SD -0.08 |
| [NCT00568685](https://clinicaltrials.gov/study/NCT00568685?tab=results) | negative SD | SECONDARY | -0.30, SD -.036 |
| [NCT00329160](https://clinicaltrials.gov/study/NCT00329160?tab=results) | negative SD | PRIMARY | 14.1%, SD -5.066 (3 cells, live) |
| [NCT00496470](https://clinicaltrials.gov/study/NCT00496470?tab=results) | negative SD | SECONDARY | -0.404, SD -0.526 (2 cells) |
| [NCT01284114](https://clinicaltrials.gov/study/NCT01284114?tab=results) | negative SD | PRIMARY | -337.5 mg/g, SD -484.6 (5 cells, live) |
| [NCT00803361](https://clinicaltrials.gov/study/NCT00803361?tab=results) | negative SD | SECONDARY | 26.84, SD -28.48 |
| [NCT01020123](https://clinicaltrials.gov/study/NCT01020123?tab=results) | negative SD | SECONDARY | -1.8 IU/L, SD -1.8 |
| [NCT02240186](https://clinicaltrials.gov/study/NCT02240186?tab=results) | SD above width | PRIMARY | 15.64 % of day, SD 8362, n 46 (live) |
| [NCT06380179](https://clinicaltrials.gov/study/NCT06380179?tab=results) | SD above width | PRIMARY | sleep efficiency 78.26%, SD 147.19, n 13 |
| [NCT03859401](https://clinicaltrials.gov/study/NCT03859401?tab=results) | SD above width | SECONDARY | 16.6% of time, SD 112.6, n 15 |

## What this is not

- **Not a judgement on any trial's conclusions.** Each flag shows that a posted number, or the posted label on it, is wrong. It doesn't say which one, and it doesn't say whether the trial's analysis was affected. Most look like data-entry slips.
- **A floor, not a count of all errors.** The checks are deliberately narrow: rounding slack is allowed on both sides, and only definitional rules are used. A wrong number that is still possible passes.
- **The bounded-measure checks of v0.2 are not used here.** v0.2 also flagged means and SDs against 0-100 bounds for percent-of-days/time measures (41 + 26 studies). Hand triage showed that many of these were false positives. The time word sat in the title ("Y-balance at Week 12", unit "% of limb length"), the unit was an area under the curve ("%*h"), or the value was an unlabelled change score (negative "percent of time"). v0.3 fixes this: the time word must be in the unit, and negative means become a "suspect" tier. v0.3 also adds sd_above_width, which holds even for change scores. The three sd_above_width studies above were checked by hand against that rule. The v0.3 census is queued and will replace this paragraph.
- Free-text score ranges ("scale" tier, 221 studies) and the "suspect" tier (188 studies) are left out of every number above.

## Why it is new

ClinicalTrials.gov runs automated validation and manual review before posting (Zarin et al., NEJM 2011; NEJM 2019 ten-year update). Studies of posted results have compared them with publications in samples (Hartung et al., Ann Intern Med 2014: 110 trials). Consistency tests such as GRIM and SPRITE, and Carlisle's baseline checks, are applied to journal articles. We found no published census that runs internal-consistency checks over every posted result, and no report of the single-mechanism pattern behind inverted intervals. If one exists, we would like to cite it.

## Reproduce

- Code: `ctgov_audit.py` and `test_ctgov_audit.py` (v0.2 for this census; 13 tests pass in the job). The tool needs only the Python standard library and reads only the public API.
- Run: `python ctgov_audit.py --out-dir out --page-size 100` (about 11 minutes, 806 API pages).
- Data snapshot: ClinicalTrials.gov API v2, all studies with `HasResults=true`, read 2026-10-15 11:02-11:13 UTC. Sponsors can correct records at any time, so a later run may differ.
