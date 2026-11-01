# Results: which AHRQ MEPS Statistical Briefs can be traced to public-use files? (census M1, v1)

MV2 of Munim, Inc., 2026-11-01. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-census-prereg-v1-2026-10-31.md` (tag v0.9.31). Code: `meps/meps_census.py` 0.1.0.
Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied.

## Short answer

Of 378 Household Component briefs with a Data Source section, 341 (90.2%) name at least one MEPS file
(88.6% after removing a classifier error, below). 28 (7.4%) say they used data that is not public. **The
non-public share rose sharply: 20 of 70 HC briefs published in 2016 or later (28.6%) against 8 of 308 up to 2015
(2.6%).** Since 2016 the usual reason is a non-public version of the Prescribed Medicines files; others are
internal geography (MSA, urban-rural, geocodes) and Data Center files. The classifier passed its validation gate
(19 of 20 briefs agree with a hand reading). 4 of 5 predictions held; coverage (P1) missed its threshold by
0.2 points.

## Run

Job `meps-census-v1`, 2026-11-01 06:14-06:36 UTC, exit 0 (14 unit tests, then the census). The MEPS publication
listing stated 549 Statistical Briefs; the job parsed 546 rows from it (frame = listing; no direct probing was
needed). Every listed brief's `.shtml` page was fetched (NOPAGE 0), with a 2-second pause between requests.

| class | briefs |
|---|---|
| NOSECTION (no "Data Source" heading) | 53 |
| IC (Insurance Component, no HC file ID) | 115 |
| NONPUBLIC (any non-public marker) | 28 |
| PUF (at least one file ID, no marker) | 314 |
| NOID (HC, no file ID, no marker) | 36 |
| total | 546 |

HC briefs = PUF + NONPUBLIC + NOID = 378. By period: up to 2015, PUF 268, NONPUBLIC 8, NOID 32 (and IC 102,
NOSECTION 52); 2016 on, PUF 46, NONPUBLIC 20, NOID 4 (and IC 13, NOSECTION 1). Marker counts in sections
(all classes): confidential 90, special computation 85, data center 11, internal 9, not public 8, restricted 5,
model 1. Most "confidential" and "special computation" hits are IC briefs ("special computation runs on the
confidential MEPS-IC data"), which are classed IC first by rule. Most-cited file: HC-105 (2006 full-year
consolidated), in 49 sections.

## Validation gate (done before grading)

The job drew 20 briefs at random (seed 20261031). On 2026-11-01 we read each one's Data Source section on the
live page and classified it by the pre-registered rules, and wrote the readings down
(`meps-census-v1/validation-reading.md`) before opening the script's classes. **19 of 20 agree** (gate: >= 18).
The disagreement: #411 names its files only in words ("MEPS-HC 2010 Full Year Consolidated Data File"), but the
file-ID pattern read "HC 2010" as file "H2010", so the script said PUF where the reading says NOID.

The same error affects 9 briefs (#40, 81, 139, 152, 403, 411, 468, 469, 504), whose ID lists include a
four-digit year (H1996-H2012). No MEPS file number is that high. In 6 of them the year is the only "ID"
(#139, 403, 411, 468, 469, 504), so they are really NOID. This changes P2 only (below); P3-P5 use HC-brief
denominators and NONPUBLIC or IC counts, which it does not touch.

## Grades (exactly as pre-registered)

| | prediction | result | grade |
|---|---|---|---|
| P1 | Data Source sections found for >= 90% of the stated total | 493 of 549 = 89.8% | **failed** |
| P2 | >= 80% of HC briefs name >= 1 file ID | 341 of 378 = 90.2% (335 = 88.6% without year-IDs) | held |
| P3 | 5%-40% of HC briefs NONPUBLIC | 28 of 378 = 7.4% | held |
| P4 | NONPUBLIC share 2016+ > share to 2015 (each >= 30 briefs) | 20/70 = 28.6% vs 8/308 = 2.6% | held |
| P5 | IC briefs 10%-30% of briefs with a section | 115 of 493 = 23.3% | held |

P1 failed because 52 of the 53 briefs without a "Data Source" heading are from 2015 or earlier (older briefs
put the source in the Introduction or "About MEPS-HC"), and 3 listed briefs were not parsed from the listing.

## The 20 non-public HC briefs since 2016

#508, 514, 515, 516, 529, 531, 534, 535, 538, 541, 542, 549, 551, 552, 559, 563, 564, 566, 567, 570. We read the
stored sections (or the live page) of 11 of them (#508, 514, 515, 529, 534, 541, 549, 551, 559, 567, 570). Each
states a non-public input in plain words, for example "non-public versions of
the 2015 and 2016 Prescribed Medicines Files (HC-178A and HC-188A)" (#515), "the confidential version of the MEPS
Prescribed Medicine files (HC-229A, HC-239A)" (#567), "restricted use geocoded files" (#508), "2020 MEPS
internal data file with MSA variables" (#549), urban-rural designations "not on public use files" (#570). A
pattern search finds a non-public, internal, confidential or restricted Prescribed Medicines file in at least 12
of the 20. These are what the briefs say about their inputs. They are not a judgement of the briefs.

## What this means

- Of the 70 HC briefs since 2016, 50 state no non-public input (46 name public files, 4 name none), so an
  outside analyst can at least start a reproduction from files anyone can download. For 20 (about one in four),
  an exact reproduction needs access that goes through AHRQ (its Data Center or internal files).
- Many non-public inputs are the Prescribed Medicines files, of which public versions also exist. So a
  "public-file approximation" of those briefs is possible and could be compared with the published figures.
- Limits: this classifies what each brief says, not whether its numbers reproduce; a brief naming only public
  files may still use unstated variables; the 2015/2016 split was fixed in advance but is otherwise arbitrary.

## Side observations (not graded)

- #245 (2009, on 2006 data) lists HC-050, the 2000 full-year file; #511 (2018, on 2005 and 2015 data) lists
  HC-131, a 2000-2013 employment file; #254 compares with 1996 but lists only 2006 files. These may be correct
  (comparisons across years); they would be worth a look in a reproduction.
- #566 (2025): Highlights say "ages 18 to 64" while the body gives the same 31.1% for ages 20-64 (observed while
  designing, still unconfirmed by a human).

## Files

`meps-census-v1/briefs.csv` (one row per brief: number, year, class, file IDs, markers, URL),
`meps-census-v1/census.json` (counts, grades, validation sample), `meps-census-v1/sections.jsonl` (the Data
Source section texts, US government work), `meps-census-v1/validation-reading.md` (the hand readings).
