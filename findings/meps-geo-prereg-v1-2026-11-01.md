# Pre-registration: which MEPS Statistical Briefs report results by metropolitan (MSA) status on data years whose public files no longer carry it? (census M2, v1)

MV2 of Munim, Inc., 2026-11-01. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the job `meps-geo-v1` runs. Text CC BY 4.0; code (`meps/meps_geo.py` 0.1.0) Apache-2.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied.

## Why

Census M1 (`findings/meps-census-results-v1-2026-11-01.md`) sorted MEPS Household Component Statistical Briefs
by what their Data Source section says. "PUF" meant: names at least one public-use file and says nothing about
non-public data. M1 listed as a limit that such a brief "may still use unstated variables". While designing a
reproduction of brief #569 (bone density scans, 2022 data; December 2025) we found a concrete case:

- #569's Data Source section names only "the Medical Expenditure Panel Survey Household Component, 2022
  Full-Year Consolidated file (HC243)", and M1 classed it PUF.
- Its Figure 7 reports percentages for MSA and non-MSA residents (42.7% and 43.3%).
- The public HC-243 codebook has no MSA variable. On 2026-11-01 we looked up `MSA<yy>` in the online codebooks
  (`download_data_files_codebook.jsp?PUFId=...&varName=...`): MSA11 (HC-147, 2011) and MSA12 (HC-155, 2012)
  have value tables ("0 NON-MSA", "1 MSA"); MSA13, MSA14, MSA15, MSA16, MSA17, MSA18 and MSA22 (HC-163 to HC-243)
  return an empty entry, the same as a made-up name (ZZNOTAVAR22). An alphabetical read of the HC-243 codebook
  also shows no variable between MORJOB53 and NATAMP42.
- AHRQ's Data Center page lists the "Metropolitan statistical area (MSA) indicator" among "confidential and
  non-public use variables".

So from the 2013 data year on, any MSA estimate needs non-public data, whether or not the brief says so.
M2 counts how often that happens.

## Frame and data

- Briefs: every Household Component brief in M1's `findings/meps-census-v1/briefs.csv` (tag v0.9.33; classes
  PUF, NONPUBLIC, NOID; 378 briefs), fetched by the job from GitHub (SHA-256 recorded).
- Each brief's live `.shtml` page on meps.ahrq.gov (allowed by robots.txt), 2 seconds between requests.
- Codebook entries `MSA11` ... `MSA24` for the Full Year Consolidated files 2011-2024 (HC-147 ... HC-256).
- **Anchor** of a brief, from the file IDs M1 found in its Data Source section: `post` if it names any Full Year
  Consolidated file of data year 2013 or later (HC-163, 171, 181, 192, 201, 209, 216, 224, 233, 243, 251, 256),
  `pre` if it names Full Year Consolidated files but all from 2012 or earlier, `none` otherwise.
- **MSA hit**: a line of the brief's visible text (after removing lines found on at least half of all pages,
  i.e. site navigation) matching `MSA`, `MSAs`, `non-MSA` (case-sensitive) or `metropolitan` /
  `nonmetropolitan` (any case). Urban/rural hits are counted the same way but not graded.

## Predictions

- **P1 (primary, graded by hand):** at least 3 briefs that are classed PUF and anchored `post` (including #569)
  show at least one estimate for an MSA / non-MSA (or metropolitan / nonmetropolitan) group for a data year of
  2013 or later. Hand reading covers every `post` PUF brief with an MSA hit (the job lists them as
  `P1_candidates` with up to 8 matching lines each); a candidate counts only if the page shows such an estimate
  (text, figure label or table), not just a definition. Readings are written down, brief by brief, before the
  count is made.
- **P2 (control, automatic):** both #569 (PUF) and #549 (NONPUBLIC, "2020 MEPS internal data file with MSA
  variables") have an MSA hit.
- **P3 (automatic):** the codebook check finds the MSA value label for 2011 and 2012 and for none of 2013-2023.
  Untestable if any of these 13 pages fails to load or is not recognisable as a codebook page. (Seven of the
  eleven 2013-2023 years were checked by hand while designing; the job checks all of them the same way.)
- **P4 (automatic):** among PUF briefs, the share with an MSA hit is lower for `post` than for `pre` briefs
  (each group at least 10 briefs, else untestable).

Also reported (not graded): MSA hits among `post` NONPUBLIC briefs and whether their Data Source section names
MSA or internal geography; urban/rural hits by anchor.

## Limits

An MSA hit is a text match, not an estimate; P1 rests on a hand reading. Anchors use only the Data Source
section's file IDs, so briefs that name no file are left out of P1 and P4. A brief may legitimately report MSA
for 2012 or earlier data alongside later years; only estimates for 2013+ data count. This is about what can be
reproduced from public files, not about whether any estimate is right; using internal data is AHRQ's normal
practice, and the point is only whether a reader can tell from the brief. Nothing goes to AHRQ before a human
has checked the results.

## Outputs

`geo.json` (codebook statuses, counts, grades, P1 candidates), `geo-briefs.csv` (one row per brief: class,
anchor, hit counts), `snippets.jsonl` (matching lines from US-government brief pages).
