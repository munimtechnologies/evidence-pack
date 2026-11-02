# Pre-registration: can randomly chosen MEPS Statistical Briefs be recomputed from the one public file they name? (check R2, v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the draw. Code for the draw: `meps/r2_draw.py` 0.1.0 (Apache-2.0). Text CC BY 4.0. Research
information about published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not
been contacted.

## Question

Check R1 recomputed one brief (#569) from HC-243: 24 of 26 percentages within 0.23 points, 19 to the published
decimal, and two MSA cells not computable from the public file. One brief chosen by us says little about the
series. R2 asks the same question of five briefs chosen at random: **when a recent MEPS Household Component
Statistical Brief names a single Full Year Consolidated (FYC) public-use file as its data source, can an outside
analyst recompute its published estimates from that file, the brief's text and the codebook?**

## Eligible set (fixed now)

From census M1 (`findings/meps-census-v1/briefs.csv`, tag v0.9.33 and later), every brief with `status` = ok,
`cls` = PUF, `n_ids` = 1, `year` >= 2016, whose one named file is an FYC file for 2013-2024 (HC-163, 171, 181,
192, 201, 209, 216, 224, 233, 243, 251, 256; MEPS data-file search read 2026-11-02), excluding #569 (already
done). Read by hand from the published CSV, that is **11 briefs**: #491 (HC-163), #493, #496, #497 (HC-171), #506,
#507 (HC-181), #521 (HC-192), #533 (HC-209), #540 (HC-216), #554, #558 (HC-233). Three single-file PUF briefs are
outside the rule because their file is not an FYC file (#502 HC-175, #509 HC-182, #504 "H2010", a census parsing
artefact). The job recomputes the set; if it does not get these 11, the draw is void and the cause is reported
before any redraw.

## Draw (fixed now)

- Seed: the first 16 hex digits, read as an integer, of the `outputValue` of the **NIST Randomness Beacon
  (version 2.0, chain 2) pulse stamped 2026-11-02T10:00:00.000Z**
  (`https://beacon.nist.gov/beacon/2.0/pulse/time/1793613600000`). This value did not exist when this file was
  committed; the commit time on GitHub is the evidence. The job accepts the pulse only if its `timeStamp` matches
  exactly.
- Sample: Python 3.12 `random.Random(seed).sample(sorted(eligible numbers), 5)`. All 5 are reproduced; there is
  no replacement for a brief that turns out to be hard.

## Procedure after the draw (fixed now)

1. For each drawn brief, two independent reads of its web page (`stat<N>.shtml`) transcribe every in-scope
   published estimate; disagreements are settled by a third read and logged.
2. A per-brief specification (definitions from the brief's own text; every variable's codebook value table read
   before use; universe, weight and any recodes) is published **before any job reads that brief's file**. Where
   the brief is silent, the spec states our reading and marks the cells it affects "underspecified"; they stay in
   the denominator, because that is part of the reproducibility question.
3. MV2's hands download the named FYC Stata file once per file through a browser (meps.ahrq.gov's robots.txt
   disallows automated fetches of public-use files); jobs never download it and record its SHA-256.
4. A sealed job recomputes every computable cell; a cell needing a variable that the named file does not carry
   (codebook check with one positive and one negative control variable) is "not computable".

**In scope:** point estimates for the data year of the named file printed in the brief's figures, tables and
text: percentages, means, medians and totals. **Out of scope:** standard errors, significance statements,
sample counts, and numbers the brief attributes to other files, years or sources. If a brief has more than 40
in-scope estimates, the first 40 in page order are used (figures, then tables, then text not repeating them).

**Matching:** percentages are *close* within 0.5 points; means, medians and totals within 1% (relative). A cell
is *exact* if our value, rounded half-up to the published precision, equals the published value. The raw gap is
always reported (R1 missed "exact" by 0.0002 points; a reader should see that).

## Predictions (graded exactly as written)

- **P1 (primary):** in at least 4 of the 5 briefs, at least 80% of the computable cells are close.
- **P2:** pooled over all computable cells of the 5 briefs, at least 70% are exact.
- **P3:** at most 1 of the 5 briefs has a cell that is not computable from its named file.
- **P4:** no brief has fewer than 50% of its computable cells close.

Our own errors are graded as they fall; corrections only by dated addendum, with the grades kept.

## Limits

Five briefs from an eligible set of 11; the eligible set itself depends on census M1's parsing of each brief's
Data Source section (validated by hand on 20 briefs in M1). A failed cell may be our error, not the brief's.
Statistical tests in the briefs are not graded. Only aggregate estimates for published cells leave the jobs.
Any note to AHRQ waits for a human check.

## Why this is new

Searches on 2026-11-01/02 found no systematic reproduction of MEPS Statistical Briefs from their named public
files (IPUMS MEPS harmonises files; AHRQ publishes summary-table code; neither recomputes briefs). The test
feeds MV2's planned entry to AHRQ's SI Tech Sprint, which asks for tools that reproduce AHRQ results and say
when the public data cannot support an answer.

## Outputs of the draw job

`r2-draw.json`: the eligible list as recomputed, the beacon pulse (uri, index, timeStamp, outputValue), the seed
and the 5 sampled briefs in draw order with their file and URL.
