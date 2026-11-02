# Pre-registration: an open variable inventory of the MEPS Full Year Consolidated public-use files, 2011-2024 (v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the job `meps-inventory-v1` fetches any codebook page. Code: `meps/inventory.py` 0.1.0
(Apache-2.0). Text and data CC BY 4.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why

Census M2 showed that a brief can name only a public file yet report an estimate (MSA) that needs a variable
the file does not carry. Checking that by hand, one variable and one year at a time (as M2 did), does not scale.
A complete list of the variables in each Full Year Consolidated (FYC) file lets anyone, and the checker MV2 is
building for AHRQ's SI Tech Sprint, test "does the named file carry every variable this figure needs?" in one
lookup. We found no such open, machine-readable list across years: AHRQ's codebook shows one file at a time and
IPUMS MEPS harmonises variables under its own names (searches 2026-11-01/02; a short search, not a review).

## Method (fixed now)

- One HTTP request per file to AHRQ's codebook variable list,
  `meps.ahrq.gov/mepsweb/data_stats/download_data_files_codebook.jsp?PUFId=<file>`, for the 14 FYC files of
  2011-2024 (HC-147, 155, 163, 171, 181, 192, 201, 209, 216, 224, 233, 243, 251, 256), 10 seconds apart, after
  checking each URL against `meps.ahrq.gov/robots.txt` in code (the codebook pages are not disallowed; data files
  are, and none is fetched).
- From each page: every variable name (from its `varName=` link), start and end column, and description.
- An "MSA rule" flags a variable whose name starts with MSA or contains METRO, or whose description contains the
  word MSA or a word starting with METRO. A wider "geography" list (also CBSA, COUNTY, FIPS, URBAN, RURAL, ZIP,
  STATE) is reported, not graded.

## Gate (the inventory is read only if it passes)

The HC-243 list must have exactly **1,420** variables (the number of variables in the HC-243 Stata file read by
check R1's job), include `SAQWT22F`, `ADOSTP42`, `REGION53` and `PERWT22F`, and include neither `PSAQWT22F` nor
`MSA22` (codebook look-ups, 2026-11-02). Positive controls reported for every file: `PERWTyyF`, `REGIONyy`,
`VARSTR`, `VARPSU`.

## Predictions

- **P1:** none of the 12 FYC files for 2013-2024 has a variable caught by the MSA rule (all 12 must be read, meaning at least one variable parsed from each page).
- **P2 (positive control):** both the 2011 and 2012 files (HC-147, HC-155) have at least one such variable.

M2 found the same pattern by looking up named variables; P1 tests it against every variable and description in
every file, so a renamed or differently labelled MSA variable would make it fail.

## Limits

The codebook list is AHRQ's description of the file, not the file itself; the gate ties it to one real file
(HC-243). A geography flag is a text match, not a judgement about what the variable measures. Only public
codebook text is collected; no data.

## Outputs

`inventory/<file>.csv` (file, data year, name, start, end, description; one per file), `geo-candidates.csv`,
`inventory.json` (counts, controls, gate, grades, fetch errors).
