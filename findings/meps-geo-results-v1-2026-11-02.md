# Results: MEPS Statistical Briefs that report metropolitan (MSA) results on data years whose public files no longer carry it (census M2, v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-geo-prereg-v1-2026-11-01.md` (tag v0.9.35, fixed before the job ran). Code:
`meps/meps_geo.py` 0.1.0. Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied. AHRQ has not been contacted about this; a human will check it
first.

## Short answer

Three of four predictions held, and one failed in an informative way.

- **The MSA indicator leaves the public files after 2012.** The online codebooks show the MSA variable with
  values "0 NON-MSA / 1 MSA" for the 2011 and 2012 Full Year Consolidated files and no entry for any year
  2013-2024 (P3 held). AHRQ's own documentation agrees: the HC-196 file notes say an MSA indicator "had been
  provided in the past but is no longer being provided", to protect respondents' confidentiality, and AHRQ's
  Data Center lists it among non-public variables.
- **Briefs kept reporting it anyway, and three of them name only public files.** Of 43 briefs on 2013+ data
  whose Data Source names only public-use files (class PUF), 3 show estimates for metropolitan and
  non-metropolitan (or MSA / non-MSA) groups: #512 (2014-2015), #554 (2021) and #569 (2022) (P1 held, read by
  hand). None of the three says that the geography came from non-public data. A reader cannot reproduce those
  estimates from the files the brief names.
- **The share did not drop (P4 failed).** We predicted that public-file-only briefs would mention MSA less
  often after the variable left the public files. The opposite: 3 of 43 (7.0%) of `post` PUF briefs have an
  MSA hit against 5 of 220 (2.3%) of `pre` PUF briefs.

## Run

Job `meps-geo-v1`, exit 0. Frame: the 378 Household Component briefs in census M1's `briefs.csv` (tag v0.9.33,
SHA-256 `9344182...c6`); all 378 pages fetched from meps.ahrq.gov (allowed by robots.txt, 2 s apart); 62
navigation lines removed (none of them matched MSA). Codebook pages for MSA11 ... MSA24 all loaded.

## Grades (exactly as pre-registered)

| | prediction | result | grade |
|---|---|---|---|
| P1 (primary, by hand) | >= 3 PUF `post` briefs (incl. #569) show an MSA / metro estimate for a 2013+ data year | 3 of 3 candidates confirmed (#512, #554, #569) | held |
| P2 (control) | #569 (PUF) and #549 (NONPUBLIC) both have an MSA hit | both | held |
| P3 | MSA value label found for 2011 and 2012 and none of 2013-2023 | exactly so (2024 also absent) | held |
| P4 | among PUF briefs, MSA-hit share lower for `post` than `pre` | 7.0% (3/43) vs 2.3% (5/220) | **failed** |

P1 readings were written brief by brief before counting: `meps-geo-v1/p1-readings.md`.

## The three briefs

| brief | data year | Data Source names | metro / MSA estimate shown |
|---|---|---|---|
| #512 Insurance and Access to Care in Urban and Rural Areas (May 2018) | 2014-2015 | HC-171, HC-181 | e.g. no usual source of care, under 65: metro 25%, non-metro 19% (county-based Rural-Urban Continuum Codes) |
| #554 Young Adults Who Had Ever Used an Electronic Nicotine Product (Feb 2024) | 2021 | HC-233 + 2021 SAQ supplement | ever used: MSA 29.6%, non-MSA 39.3% |
| #569 Bone Density Scan Utilization Among Women 50+ (Dec 2025) | 2022 | HC-243 | ever had DEXA: MSA 42.7%, non-MSA 43.3% |

#512 groups people by their county's USDA code rather than by the MSA indicator; the page does not say where the
county came from. It counts under the pre-registered rule, which names metropolitan / nonmetropolitan groups.

## Also reported (not graded)

- 11 of the 18 `post` NONPUBLIC briefs have an MSA hit. In the matched lines, #549, #551 and #552 name "MEPS
  internal data files" as the MSA source, and #570's Data Source line begins "Due to confidentiality concerns, urban-rural d..." (the stored line
  is cut off there).
  The other seven were not checked by hand in this run.
- Outside the graded groups, #557 (long COVID; class NOID, so outside P1) reports MSA 12.7% vs non-MSA 19.7% on
  2023 interviews.
- The 5 `pre` PUF briefs with MSA hits (#111, #137, #381, #387, #397) are on 2002-2009 data, when MSA was on the
  public files.

## What this does and does not show

- It shows that some recent briefs that name only public files report MSA or metro results that those files
  cannot produce, so a reader following the Data Source section cannot reproduce them. Together with check R1
  (`findings/meps-r569-results-v1-2026-11-02.md`), #569 is the worked example: 24 of its 26 percentages
  reproduce from HC-243; the 2 MSA ones cannot.
- It does not show that any estimate is wrong. Using internal geography is normal practice for AHRQ; the point is
  only that the brief does not tell the reader.
- An MSA hit is a text match. P4 compares text hits, not confirmed estimates. Briefs that name no file (NOID) are
  outside P1 and P4. Anchors come from census M1's reading of each Data Source section.

## Prior art

Searches on 2026-11-02 (web; GitHub) found no count of MEPS briefs whose reported geography is not on the public
files they name, other than MV2's own pre-registration (tag v0.9.35).

## Files

`meps-geo-v1/geo.json` (codebook statuses, counts, grades, P1 candidates), `meps-geo-v1/geo-briefs.csv` (one row
per brief), `meps-geo-v1/snippets.jsonl` (matching lines from the brief pages, US government work, quoted for
analysis), `meps-geo-v1/p1-readings.md`.
