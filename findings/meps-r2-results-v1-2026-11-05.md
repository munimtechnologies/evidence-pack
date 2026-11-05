# Check R2 results: five randomly drawn MEPS Statistical Briefs recomputed from the one public file each names (v1)

MV2 of Munim, Inc., 2026-11-05. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r2-prereg-v1-2026-11-02.md` (predictions graded below exactly as written).
Specifications: `findings/meps-r2-spec-conc-v1-2026-11-03.md` (#506, #521, #540) and
`findings/meps-r2-spec-507-491-v1-2026-11-04.md` (#507, #491). Code: `meps/r2conc.py` 0.1.0 (tag v0.9.39) and
`meps/r2rest.py` 0.1.0 (tag v0.9.40). Text and data CC BY 4.0 (the published numbers are AHRQ's); code
Apache-2.0. Research information about published statistics, not medical advice. No endorsement by AHRQ is
implied; AHRQ has not been contacted.

## Question

When a recent MEPS Household Component Statistical Brief names a single Full Year Consolidated public-use file
as its data source, can an outside analyst recompute its published estimates from that file, the brief's own
text and the codebook? Five briefs were drawn at random (NIST Randomness Beacon seed) from the 11 eligible
briefs: #506, #521, #540, #507 and #491.

## Results per brief (first 40 in-scope published cells of each)

| Brief | Year, file | Cells | Computable | Close | Exact | Not computable | Share close |
|---|---|---|---|---|---|---|---|
| #506 | 2015, HC-181 | 40 | 40 | 40 | 40 | 0 | 100% |
| #521 | 2016, HC-192 | 40 | 40 | 39 | 40 | 0 | 97.5% |
| #540 | 2019, HC-216 | 40 | 30 | 30 | 30 | 10 | 100% |
| #507 | 2015, HC-181 | 40 | 40 | 34 | 32 | 0 | 85% |
| #491 | 2013, HC-163 | 40 | 40 | 40 | 40 | 0 | 100% |
| **Pooled** | | 200 | 190 | 183 | 182 | 10 | 96.3% |

Every codebook gate passed (record counts, positive weights, zero-expense counts and the value tables of every
variable used; for #507 also the 14,522 CPS families of the HC-181 documentation).

## Predictions

- **P1 (primary), at least 80% of computable cells close in at least 4 of the 5 briefs: held.** All 5 briefs
  reach 80% (lowest: #507, 34 of 40 = 85%).
- **P2, at least 70% of all computable cells exact: held.** 182 of 190 (95.8%).
- **P3, at most 1 brief with a cell not computable from its named file: held.** Only #540 (10 cells on treated
  conditions need the Medical Conditions file, which its Data Source does not name).
- **P4, no brief below 50% close: held.** The lowest is 85%.

**4 of 4 predictions held.**

Deviation from the pre-registration, stated in both specifications before any data were read: step 3 said the
Stata file; HC-163, HC-181 and HC-192 have no Stata file, so all five briefs were recomputed from the
fixed-width ASCII zips, read with the codebook's column positions. Each zip was downloaded once in a browser
by MV2's hands; its SHA-256 is recorded in the job output.

## Brief #507: where the 8 non-exact cells come from

#507 (out-of-pocket expenses of non-elderly families, 2015) is the only brief built on families rather than
persons. The brief names no variables; the specification used the CPS family on 12/31/15 (DUID + CPSFAMID),
the reference person's FAMWT15C weight and POVCAT15, adults aged 18+ and children 0-17 by AGELAST.

- **Income figures (Figures 1-2, 20 cells): 19 exact.** The miss is the share of high-income families with
  more than $2,500 out of pocket: 21.454% against a printed 22%, 0.046 points short of rounding up.
- **Family-structure figures (Figures 3-4 without the "All" cells, 16 cells): 9 exact, 11 close.** The
  misses are all four structure medians (1 adult without children $243.69 vs $242; 2+ adults without
  $865.46 vs $869; 1 adult with children $109.97 vs $116; 2+ adults with $735.92 vs $721) and three
  band shares of families with children (46.30 vs 47, 16.46 vs 17, 64.34 vs 65).

The brief's Table 1 (family counts by poverty status and structure; outside the 40-cell cap, used only as a
diagnostic named in the specification) shows why. Two reads of it agree, and its columns add up by hand.

- **The population is right.** Our families with at least one adult sum to 97,196,954.46; the brief prints
  97,196,954. One family in our population has no member aged 18 or older (weight 6,605.61). It is in our
  "All" cells but not in the brief's total, so AHRQ appears to leave it out (it does not change any graded
  cell's rounding).
- **Every poverty row is right.** Poor 19,394,047.91 vs 19,394,048; Low 12,159,195.36 vs 12,159,195; Middle
  27,382,203.58 vs 27,382,204; High 38,261,507.61 vs 38,261,508.
- **Within each row, some families with children move to the no-children column, and their adult count
  stays the same:**

| Poverty | 1 adult: with -> without children | 2+ adults: with -> without children |
|---|---|---|
| Poor | 110,397.6 | 20,374.0 |
| Low | 26,742.6 | 84,827.6 |
| Middle | 23,929.1 | 224,138.6 |
| High | 7,794.7 | 377,400.9 |

  (Each number is our "with children" count minus the brief's. The matching "without children" gap has the same
  size within one weighted family. Total moved: about 875,605 weighted families, 0.90% of the population.)

So AHRQ counted some members whom we count as children as neither children nor adults. The direction of the
median shifts is consistent with that: the moved one-adult families spend less than the remaining ones, and the
moved two-adult families spend more. Which members these are is not stated in the brief. A separate,
pre-registered exploratory addendum (`findings/meps-r507x-prereg-v1-2026-11-05.md`, code `meps/r507x.py`)
tests nine fixed candidate rules against the 16 Table 1 counts. It does not change any grade above.

## Brief #491

All 40 graded cells and all 20 exploratory cells (the rest of Figure 2 and the Figure 3 payer shares) are
exact. The brief's text gives 14.4% for the out-of-pocket share of spending for people under 65, and its
Figure 3 table gives 14.5. We get 14.531, which supports the table. Diagnostics: for 6 of 35,068 persons the
ten service components do not add up to TOTEXP13 within $0.50. For 4,553 persons the payer components we
summed differ from TOTEXP13 by more than $0.50. We have not examined why; every payer share is still exact.

## What R2 shows, and its limits

For five briefs drawn at random from the eligible eleven, an outside analyst who uses only the named public
file, the brief's own definitions and the codebook reproduces 182 of 190 computable published cells to the
printed digit. The gaps are documentation gaps, not wrong numbers we can show. In one brief, 10 cells need a
file that the brief does not name (#540). In another, an unstated rule for counting a family's children moves
about 0.9% of families between structure groups (#507).

Limits: five briefs, three of them from one annual series that shares a method; our readings of unstated
choices (median method, service grouping, family membership) are ours; standard errors and significance
statements were not checked; a failed cell may be our error. No human has reviewed these results.

## Files

- `findings/meps-r2-rest-v1/cells-507.csv`, `cells-491.csv`, `extra-491.csv`: every cell with the published
  text, our value, the raw gap and the flags.
- `findings/meps-r2-rest-v1/r2rest-507.json`, `r2rest-491.json`: gates, column positions, file hashes,
  diagnostics (including #507's Table 1 crosstab) and cells.
- The three concentration briefs: `findings/meps-r2-conc-results-v1-2026-11-04.md` and `findings/meps-r2-conc-v1/`.

Only aggregate estimates for published cells left the jobs; no person-level data is published.
