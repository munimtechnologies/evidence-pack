# Check R2, first three of five briefs: the concentration briefs #506, #521, #540 (per-brief results, v1)

MV2 of Munim, Inc., 2026-11-04. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r2-prereg-v1-2026-11-02.md`. Specification (fixed before the files were
downloaded): `findings/meps-r2-spec-conc-v1-2026-11-03.md`. Code: `meps/r2conc.py` 0.1.0 (tag v0.9.39). Text
and data CC BY 4.0 (the published numbers are AHRQ's); code Apache-2.0. Research information about published
statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

**The predictions P1-P4 are graded only after all five drawn briefs are done** (#507 and #491 remain; their
specification is `findings/meps-r2-spec-507-491-v1-2026-11-04.md`). Until then this note gives per-brief tallies
and does not interpret them.

## Files and gates

Each file was downloaded once by MV2's hands in a browser, as the fixed-width ASCII zip from AHRQ's MEPS data
page, and read by a sealed job (no network use for the data, stdlib Python, 1 CPU, 1 GB).

| Brief | File | Bytes | SHA-256 | Records / positive weights / zero expense (codebook = job) | Gate |
|---|---|---|---|---|---|
| #506 (2015) | h181dat.zip | 9,929,884 | 75e50de4...33822e5ee | 35,427 / 33,893 / 6,936 | passed |
| #521 (2016) | h192dat.zip | 11,360,872 | f564ad77...3794329a | 34,655 / 33,259 / 6,933 | passed |
| #540 (2019) | h216dat.zip | 8,984,574 | 53b025b9...1ad4154ebf | 28,512 / 27,648 / 4,292 | passed |

The full hashes are in `r2conc-<brief>.json`. Every AGELAST value is 0-85, and there are no negative expenses.

## Per-brief tallies (first 40 published cells each)

| Brief | Cells | Computable | Close | Exact | Not computable |
|---|---|---|---|---|---|
| #506 | 40 | 40 | 40 | 40 | 0 |
| #521 | 40 | 40 | 39 | 40 | 0 |
| #540 | 40 | 30 | 30 | 30 | 10 |
| **So far** | 120 | 110 | 109 | 110 | 10 |

- **Every computable cell is exact:** rounded to the printed precision, our value equals the printed one in all
  110 cells. That covers the 23 concentration-curve cells per brief (marked "underspecified" because the briefs
  do not say how the curve points are built), the 7 group means and the 10 age shares. The largest raw gaps
  were 0.044 points for a percentage and $0.47 for a mean.
- **#521, curve total at the 20th percentile:** the brief prints $0.9 billion and we get $0.924 billion. That
  rounds to the printed 0.9, so the cell is exact, but it is 2.6% away, outside the pre-registered 1% "close"
  tolerance for totals. A relative tolerance is strict on a number printed with one significant digit. We grade
  the cell as written (exact, not close) and do not change the rule.
- **#540, Figure 3 (10 cells):** the share of each spending group treated for five conditions. This needs
  condition codes (CCSR/ICD-10) from the Medical Conditions file. #540's Data Source names only the 2019 Full
  Year Consolidated file, which has no condition-code variable (the job checked the codebook list, with the
  positive control TOTEXP19 present and the negative control ICD10CDX absent). These cells are **not computable
  from the named file**. Prediction P3 allows at most one such brief among the five, and #540 is already one.

Group sizes behind the means, in persons (Overall / Top 50% / Top 10% / Top 1%): #506 33,893 / 14,684 / 2,882 /
285; #521 33,259 / 14,639 / 2,888 / 308; #540 27,648 / 13,970 / 2,998 / 308.

## What this shows so far (no grades yet)

For these three briefs from one annual series, an outside analyst who uses only the named public file, the
brief's own Definitions section and the codebook reproduces every computable published figure cell to the
printed digit. That includes the briefs' rule for splitting tied people at a percentile cut. The one gap is a
documentation gap: a figure whose stated data source cannot produce it. These three briefs share a method, so
they are not independent evidence.

## Files

- `findings/meps-r2-conc-v1/cells-506.csv`, `cells-521.csv`, `cells-540.csv`: every cell, with the published
  text, our value, the raw gap and the flags.
- `findings/meps-r2-conc-v1/r2conc-506.json`, `r2conc-521.json`, `r2conc-540.json`: the gates, column
  positions, file hashes, group sizes, condition check and cells.

Only aggregate estimates for published cells left the jobs; no person-level data is published.
