# Pre-registration: the rest of the eligible set. Can the other six single-file MEPS Statistical Briefs be recomputed from the public file they name? (check R2b, v1)

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before any published estimate of these six briefs is transcribed and before any of their data files is
read. Text CC BY 4.0. Research information about published statistics, not medical advice. No endorsement by
AHRQ is implied; AHRQ has not been contacted.

## Why

Check R2 (`findings/meps-r2-prereg-v1-2026-11-02.md`; results `findings/meps-r2-results-v1-2026-11-05.md`)
drew 5 of the 11 eligible briefs at random and recomputed 182 of 190 computable published cells to the printed
digit (4 of 4 predictions held). A random five out of eleven leaves the other six unknown. **R2b recomputes all six,
so that together with R2 every eligible brief has been checked.** Brief #569 (R1, 2022) also names a single FYC
file, so R1, R2 and R2b together cover all 12 briefs from 2016 onwards that census M1 found naming one Full Year
Consolidated file.

## The six briefs (fixed now; the eligible set of R2 minus its draw)

| Brief | Data year, named file | Topic (title words) |
|---|---|---|
| #493 | 2014, HC-171 | Health care expenses per person |
| #496 | 2014, HC-171 | Characteristics of persons with high health care expenditures |
| #497 | 2014, HC-171 | Concentration of health expenditures |
| #533 | 2018, HC-209 | Concentration of healthcare expenditures and characteristics of persons with high expenses |
| #554 | 2021, HC-233 | Young adults aged 18-24 who had ever used an electronic nicotine product |
| #558 | 2021, HC-233 | Lack of reliable transportation for daily living among adults |

A scoping read of each brief's page on 2026-11-06 listed its figures, definitions and approximate number of
printed estimates (about 70, 90, 84, 144, 29 and 41). No cell was transcribed and no data file was read. Each
brief's Data Source section names only its FYC file. #554 and #558 add that the
question came from the 2021 Social and Health Experiences Self-Administered Questionnaire. Whether those items
(and any special weight) are on HC-233 is a codebook question for the specification.

## Procedure (as in R2, with two stated changes)

1. Two independent reads of each brief's page (`stat<N>.shtml`) transcribe every in-scope published estimate.
   Disagreements are settled by a third read and logged.
2. A per-brief specification (definitions from the brief's text; every variable's codebook value table read
   before use; universe, weight, recodes) is published **before any job reads that brief's file**. Where the brief
   is silent, the specification states our reading and marks the affected cells "underspecified". They stay in
   the denominator.
3. MV2's hands download each named file once in a browser (meps.ahrq.gov's robots.txt disallows automated
   fetches of public-use files). Jobs never download it. **Change 1:** the fixed-width ASCII zip is used for all
   three files, as in R2's deviation (HC-171 has no Stata file; using ASCII for all keeps one reader). A job
   records each zip's size and SHA-256 before any specification is written. That job reads no variables.
4. A sealed job recomputes every computable cell. A cell that needs a variable the named file does not carry
   (codebook check with one positive and one negative control variable) is "not computable".

**In scope, out of scope, the 40-cell cap and matching are exactly R2's:** point estimates for the data year
(percentages, means, medians, totals) in figures, tables and text. Standard errors, significance statements,
sample counts and numbers attributed to other files, years or sources are out of scope. At most the first 40
in page order are graded (figures, then tables, then text that does not repeat them). A percentage is *close*
within 0.5 points, and a mean, median or total within 1% (relative). *Exact* means our value, rounded half-up
to the published precision, equals the published value. The raw gap is always reported. **Change 2:** dollar
cut points of percentile groups (for example a tier's spending range) are quantiles, not means or medians, so
they are out of scope here as they were in R2's concentration briefs. Shares of the population that define the
tiers (for example "top 10%") are definitions, not estimates.

## Predictions (graded exactly as written)

- **C1 (primary):** in at least 5 of the 6 briefs, at least 80% of the computable cells are close.
- **C2:** pooled over all computable cells of the 6 briefs, at least 80% are exact.
- **C3:** at most 2 of the 6 briefs have a cell that is not computable from the named file.
- **C4:** over all 11 eligible briefs (R2's five, graded as published, plus these six), at least 9 have at least
  80% of their computable cells close.

C3 is informed by what the brief pages show. #554 has a figure by MSA status, and census inventory v1 found no
MSA variable in any FYC file after 2012. #533 has a figure of treated conditions, which in #540 needed the
Medical Conditions file. Our own errors are graded as they fall; corrections only by dated addendum, with the
grades kept.

## Documentation consistency (descriptive; no prediction)

While transcribing, every case where a brief's text and its own figure data disagree, or a figure's title or
labels do not describe its data, is logged with exact quotes from two reads. Each is counted only after a hand
check against the numbers. Where the file can decide between the text and the table, the recomputed value is
reported (as for #491's 14.4 vs 14.5). Three candidates were noticed while scoping and are **not yet
confirmed**: #497 Figure 3 (text and table may swap two age groups), #533 Figure 6 (its title repeats Figure 5's
title), and #558 Figure 6 (labels "at least two/three/four" against text describing at least one/two/three).

## Limits

Two of the six (#497, #533) are concentration briefs, and #496 uses spending percentiles too. They share
their method with three R2 briefs (#506, #521, #540), so their results are not independent of R2. The readings of unstated choices are ours, and a failed cell may be our
error. No human has reviewed this. Any note to AHRQ waits for a human check.

## Why this is new

Searches on 2026-11-01/02, repeated on 2026-11-06, found no systematic reproduction of MEPS Statistical Briefs
from their named public files. IPUMS MEPS harmonises the files. AHRQ's own example-code repository
(github.com/HHS-AHRQ/MEPS, SAS README read 2026-11-06) re-creates two briefs on 2005 data (#193 and #188, older
exercises E6 and E7) and selected MEPS-HC Data Tools statistics, but it does not check a defined set of briefs.
With R2b, every brief in a defined frame (all briefs since 2016 that name one FYC file) will have been
recomputed, not a sample.
