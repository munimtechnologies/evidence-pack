# Results: open variable inventory of the MEPS Full Year Consolidated public-use files, 2011-2024 (v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-inventory-prereg-v1-2026-11-02.md` (tag v0.9.37, committed 2026-11-02 06:24 UTC,
before the job fetched any page). Code: `meps/inventory.py` 0.1.0 (Apache-2.0). Text and data CC BY 4.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ
has not been contacted.

## Short answer

The gate passed and both predictions held. AHRQ's codebook lists exactly 1,420 variables for the 2022 file
(HC-243), the same number as the Stata file that check R1 read. None of the 12 FYC files for 2013-2024 has a
variable whose name or description mentions MSA or a metro area. The 2011 and 2012 files each have four. The
inventory (23,195 variables in 14 files) is published here as CSV, so anyone can check in one lookup whether
the file a publication names carries the variables a figure needs.

## Run

Job `meps-inventory-v1`, exit 0: offline unit tests, then 14 codebook pages fetched 10 seconds apart after a
robots.txt check in code. No fetch errors. No data file was fetched.

## Gate and grades (exactly as pre-registered)

| | rule | result | grade |
|---|---|---|---|
| Gate | HC-243 lists exactly 1,420 variables; has SAQWT22F, ADOSTP42, REGION53, PERWT22F; has neither PSAQWT22F nor MSA22 | 1,420; all four present; neither absent variable present | passed |
| P1 | no MSA-rule variable in any of the 12 FYC files for 2013-2024, all 12 read | 12 read, none flagged | held |
| P2 (positive control) | HC-147 (2011) and HC-155 (2012) each have one | both have four: MSAyy ("MSA AS OF 12/31/yy"), MSA31, MSA42, MSA53 ("MSA STATUS - Rn/m") | held |

Positive controls `PERWTyyF`, `REGIONyy`, `VARSTR` and `VARPSU` are present in all 14 files.

## Variables per file

| file | year | variables | file | year | variables |
|---|---|---|---|---|---|
| HC-147 | 2011 | 2,052 | HC-201 | 2017 | 1,564 |
| HC-155 | 2012 | 1,883 | HC-209 | 2018 | 1,501 |
| HC-163 | 2013 | 1,790 | HC-216 | 2019 | 1,447 |
| HC-171 | 2014 | 1,838 | HC-224 | 2020 | 1,451 |
| HC-181 | 2015 | 1,831 | HC-233 | 2021 | 1,488 |
| HC-192 | 2016 | 1,941 | HC-243 | 2022 | 1,420 |
| | | | HC-251 | 2023 | 1,374 |
| | | | HC-256 | 2024 | 1,615 |

## What this adds to census M2

Census M2 (`findings/meps-geo-results-v1-2026-11-02.md`) found MSA missing from the public files after 2012 by
looking up named variables one at a time. P1 checks every variable name and description in every FYC file for
2013-2024, so a renamed or differently labelled MSA variable would have been caught. None was found. The wider
"geography" text match (reported, not graded; 130 hits) finds no description containing COUNTY, FIPS, ZIP,
CBSA, URBAN or RURAL in any of the 14 files. Apart from the eight MSA variables of 2011-2012, every hit is a
state insurance-programme variable (for example `STAPR13`, "COV BY STATE-SPEC PROG"), a text match on STATE and
not geography. The monthly state-programme variables appear through 2016, and the last hit is `CINSHP31` in
2017. This is a fact about the codebook text; we have not looked into why those variables end.

## Limits

The inventory is AHRQ's codebook description of each file, not the file itself. The gate ties it to one real
file (HC-243, 1,420 = 1,420); the other 13 files were not opened. A text match on a description is not a
judgement about what a variable measures. The pages were read on 2026-11-02 and may change.

## Files

`meps-inventory-v1/inventory/H147.csv` ... `H256.csv` (file, data year, name, start, end, description),
`meps-inventory-v1/geo-candidates.csv`, `meps-inventory-v1/inventory.json` (counts, controls, gate, grades).
