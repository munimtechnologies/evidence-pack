# Check R2 specification: the three "concentration" briefs drawn (#506, #521, #540), v1

MV2 of Munim, Inc., 2026-11-03. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before any job reads these briefs' data files (the files were not yet downloaded when this was written).
Pre-registration: `findings/meps-r2-prereg-v1-2026-11-02.md` (its predictions and rules are unchanged). Code:
`meps/r2conc.py` 0.1.0 (Apache-2.0). Text CC BY 4.0. Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## The draw

The draw job (`findings/meps-r2-draw-v1/r2-draw.json`) recomputed exactly the 11 eligible briefs, read NIST beacon
pulse 2009978 (chain 2, 2026-11-02T10:00:00.000Z), and drew, in order: **#506** (HC-181, 2015), **#540** (HC-216,
2019), **#521** (HC-192, 2016), **#507** (HC-181, 2015), **#491** (HC-163, 2013). Three of the five belong to one
annual series ("Concentration of Health Care Expenditures and Selected Characteristics of Persons with High
Expenses"). This file specifies those three. #507 (family out-of-pocket burden) and #491 (spending by service and
payer) get their own specifications later, also before any job reads their files.

## Transcription (procedure step 1)

Read 1 = census M3's machine read of each page's accessible data tables (`findings/meps-brief-tables-v1/`). Read 2
= a separate WebFetch read on 2026-11-03 asking for every cell "exactly, character for character". **The two reads
agree on every in-scope cell of all three briefs**, so no third read was needed. The published text of each cell
is in `meps/r2conc.py` (`BRIEFS`).

## Which 40 cells (the pre-registered cap, in page order)

Each brief has more than 40 in-scope estimates, so the first 40 in page order are used. Page order inside an
accessible table is row by row, left to right. Two readings are fixed here:

- **Anchors are not estimates.** Figure 1 (the concentration curve) starts at "0% of people, 0% of spending,
  $0" and ends at "100% of people, 100% of spending". Those three printed numbers are true by construction and are
  left out. The total at 100% (all spending, in billions) is an estimate and is kept.
- **Code lists are not estimates.** #506's page has a small table of CCS codes ("98, 99 / 201-204") that census
  M3 picked up; it is not an estimate.

That gives, for each brief:

| Brief | Figure 1 (curve) | Figure 2 (mean per person) | Next 10 cells | Total |
|---|---|---|---|---|
| #506 (2015) | 23: cumulative % and total ($ billions) at 10, 20, ..., 90, 95, 99%; total at 100% | 7: overall, bottom 50%, top 50%, 30%, 10%, 5%, 1% | Figure 3, ages 0-17 and 18-44, in five groups | 40 |
| #521 (2016) | 23 (same layout) | 7 | Figure 3, ages 0-17 and 18-44 | 40 |
| #540 (2019) | 23 (same layout) | 7 | Figure 3, first five conditions (overall and top 5%) | 40 |

## Definitions (from each brief's own text, read twice)

- **Population and weight:** persons with a positive final person weight (PERWT15F / PERWT16F / PERWT19F).
  Codebook value tables: HC-181 33,893 positive of 35,427; HC-192 33,259 of 34,655; HC-216 27,648 of 28,512.
- **Expenditure:** total health care expenditure, TOTEXP15 / TOTEXP16 / TOTEXP19 ("the sum of payments from all
  sources"). Codebook zero counts: 6,936 (HC-181), 6,933 (HC-192), 4,292 (HC-216). No negative values.
- **Age:** "age at the end of the year", or the last date of MEPS eligibility for people who left the survey
  before then. That is AGELAST ("PERSON'S AGE LAST TIME ELIGIBLE"), 0-85 in all three codebooks, with no
  negative codes. Age groups 0-17 and 18-44 as printed.
- **Percentile groups:** persons are ordered by total expenditure from highest to lowest and assigned by weighted
  share of the population. At a cut point a person joins the higher group only if their weight does not take the
  group past the threshold, and when tied people straddle a cut, the lower-weight person goes to the higher group
  (the briefs' Definitions section, read twice). Our implementation: sort by expenditure (high to low), then by
  weight (low to high), then by person ID (for determinism, our addition); the top q% is the longest run from the
  top whose cumulative weight is at most q% of the total weight. "Bottom 50%" is everyone not in the top 50%.
- **Concentration curve (Figure 1), our reading, marked underspecified:** the briefs define the groups but not
  how the curve points are built. We take the bottom p% as everyone not in the top (100 - p)% under the rule
  above; cumulative % = their share of all spending; total = their spending in billions of dollars. The 23 curve
  cells carry the label "underspecified" in the results and stay in the denominator, as the pre-registration
  requires.
- **Means (Figure 2):** weighted mean of total expenditure within each group.
- **Age shares (Figure 3 of #506 and #521):** weighted share of the group in each age band.

## #540 Figure 3: not computable from the named file

#540's Data Source names only the "MEPS 2019 Full Year Consolidated File (HC-216)". Its Figure 3 gives the
percentage of persons *treated* for each condition, defined in its Definitions as having one or more health care
events where the condition was reported, with household-reported conditions coded to ICD-10 and grouped into
CCSR categories. HC-216's codebook (all variables, `findings/meps-inventory-v1/inventory/H216.csv`) has no
condition code, CCS/CCSR or ICD variable. The positive control TOTEXP19 is there, and the negative control
ICD10CDX, a Medical Conditions file variable, is not. HC-216 does carry "ever diagnosed" items such as DIABDX_M18
and HIBPDX, but those measure a different thing (ever told, adults only) from "treated in 2019". So these 10
cells count as **not computable** from the named file. The job repeats this check against the codebook list.
Under prediction P3 ("at most 1 of the 5 briefs has a cell that is not computable"), #540 is therefore already
one such brief. #506's own treated-conditions figure (Figure 4) falls outside its first 40 cells.

## Matching (unchanged from the pre-registration)

Percentages are close within 0.5 points; means and totals within 1% of the published value (a published 0 is
close only if ours rounds to 0). A cell is exact if our value, rounded half-up to the printed precision, equals
the printed number. The raw gap is always reported.

## Data files and gates

The briefs' files are downloaded once each by MV2's hands, in a browser, as the fixed-width **ASCII** zip
(h181dat.zip, h192dat.zip, h216dat.zip), because HC-181 and HC-192 are offered only as ASCII or SAS transport.
Jobs never download them. Column positions come from the published codebook inventory. Before anything is
computed, the job checks that the record count, the number of positive weights and the number of zero
expenditures equal the codebook counts above, and that every AGELAST is between 0 and 85. If any check fails,
nothing is graded and the failure is reported. Each file's SHA-256 is recorded.

## Limits

These three briefs share one method, so their results are not independent: a misreading of the percentile rule
would affect all three. Standard errors and significance statements are out of scope. A failed cell may be our
error, not AHRQ's.
