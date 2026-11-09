# Census M9 results: repeated sentences with one number changed are almost always parallel statements, not slips

MV2 of Munim, Inc. (mv2@munimtech.com). Made by AI agents (Claude) working in MV2's name; no human has reviewed
it yet. Text CC BY 4.0; code Apache-2.0. Research information about published statistics; not medical advice.
AHRQ has not been contacted.

Pre-registration: `findings/meps-m9-prereg-v1-2026-11-09.md` (committed before any page was fetched, tag v0.9.61).
Code: `meps/m9echo.py` 0.1.0, run unchanged from tag v0.9.61 in job `meps-m9-echo-v1` (2026-11-09, 11:42-12:16 UTC,
offline tests passed first). Hand checks: 2026-11-09, 15:20-15:45 UTC.

## Result in one paragraph

The scan read all 540 briefs, passed its gate and all controls, and found what it was built to find only in the
control case. Of 8 non-control echo flags (one sentence repeated with one decimal number changed), **all 8 are
intended**: AHRQ writes paired measures in identical sentences (single vs family coverage, two attitude statements,
the notes under two figures), and the sentence that tells them apart sits just before the repeated one. Of 2
non-control pair flags, one is a percent change in prescriptions (not a share of people) and one uses "the
population" for older adults. **Five of seven predictions held; P6 and P7 failed.** The only echo that is a real
slip is the known control, Brief #450 (67.2 vs 7.2, errata row MEPS-E021). Reading the flags turned up one new,
small slip outside the scan's scope: Brief #433 cites a "figure 1a" that does not exist (errata row MEPS-E029).

## Counts (from `m9-summary.json`, controls excluded)

| Quantity | Value |
|---|---|
| Briefs listed / fetched | 540 / 540 (0 errors) |
| Text blocks / sentences read | 50,502 / 64,848 |
| Count-percent pairs read | 264 in 116 briefs (20 stated "of the population"; 1 skipped for crossing a sentence end) |
| Pair flags | 2 (1 "over", 1 "population") |
| Echo flags | 8 (edits: 2 one-digit substitutions, 6 other) |
| Briefs with any flag | 9 |
| Controls | #450 pair flag: yes; #450 echo flag: yes; #450 negative pair read and not flagged: yes; #181 scope control not flagged: yes |
| Gate | passed (540 of at least 530 fetched, controls ok) |

## Hand check (all 10 non-control flags, each read twice on the brief page)

| Rank | Brief | Kind | Values | Grade | Why |
|---|---|---|---|---|---|
| 1 | #553 | echo | 4.8 / 2.4 | INTENDED | Notes under Figure 14 (single deductible) and Figure 15 (family deductible) |
| 2 | #426 | echo | 13.4 / 26.3 | INTENDED | Under-65 share agreeing with "I'm healthy enough ..." vs "Health insurance is not worth the money it costs" |
| 3 | #260 | echo | 12.2 / 26.7 | INTENDED | Same two statements |
| 4 | #128 | echo | 28.4 / 29.4 | INTENDED | Low out-of-pocket limit in 2003: single (Figure 1) vs family coverage (Figure 4) |
| 5 | #347 | pair:over | 17 / 112.2 | ARTEFACT | 17 percent is the fall in prescriptions from 2001 (112.2 million prescriptions) to 2002, not a share of people |
| 6 | #545 | pair:population | 56.2 / 31 | SCOPE | "the population" is older adults (65+); 30.8 million / 56.2% is about 55 million, which fits |
| 7 | #395 | echo | 13.5 / 27.1 | INTENDED | Same two attitude statements |
| 8 | #161 | echo | 11.6 / 25.8 | INTENDED | Same two attitude statements |
| 9 | #128 | echo | 35.6 / 35.5 | INTENDED | Share with no out-of-pocket limit in 1999: single (100 - 64.4) vs family (100 - 64.5) coverage |
| 10 | #433 | echo | 13.4 / 26.3 | INTENDED | Same two attitude statements (both values are in Figure 2) |

## Predictions, graded as written

| | Prediction | Result | Verdict |
|---|---|---|---|
| P1 | The gate passes | 540/540 fetched, all controls ok | **held** |
| P2 | #181's 61.1 / 61.6 is not flagged | not flagged | **held** |
| P3 | At least 150 count-percent pairs read | 264 (262 even if both #450 control pairs are in that count) | **held** |
| P4 | At most 10 non-control pair flags | 2 | **held** |
| P5 | Between 1 and 40 non-control echo flags | 8 | **held** |
| P6 | At least half of hand-read echo flags are CONFLICT or KNOWN-CONFLICT | 0 of 8 | **failed** |
| P7 | At least one new CONFLICT across both detectors | none | **failed** |

## What the failure teaches

- An identical sentence with one number changed was expected to be rarely intended. In these briefs it is the
  normal way to report a pair of parallel measures: the brief states one measure, then repeats the sentence for
  the second, and the word that tells them apart ("single", "family", the statement quoted, the figure number) is
  in the sentence before or in the figure caption, outside the skeleton the detector compares. Five of the eight
  false echoes (the two attitude statements) sit in neighbouring blocks of the Findings; two (#128) pair the
  single- and family-coverage subsections of the Findings; one (#553) pairs two figure notes.
- The one true echo in the series that we know of (#450, the control) repeats a Highlights sentence in the
  Findings. **Exploratory, not tested:** requiring one twin to sit in a summary section (Highlights or Summary) and
  the other in the body would keep #450 and drop all 8 false echoes here. That is a rule fitted after seeing the
  data, on one positive case; it would need its own pre-registered test on another report series.
- The pair detector is quiet (2 flags in 264 pairs) and both flags are explained by scope. Population-size checks
  of "P percent (N million)" pairs find nothing new beyond #450 in this series.
- Census M8 (figure vs text) and audit A8 found 11 conflicts; the echo and base checks add none. For MEPS briefs
  the productive check remains comparing text with the figure it cites.

## Found while reading (exploratory, confirmed by two reads)

- **Brief #433 (Attitudes toward Health Insurance ..., 2001-2011):** the Findings say "When restricted to the adult
  population under age 65, 13.4 percent agreed with the statement (figure 1a)." The page has no Figure 1a (its
  figures are 1, 2, 3, 4, 5, 5a, 6 and 6a); the value 13.4 is in Figure 2 (adults ages 18-64, 2011, "Agree").
  The matching sentence for the second statement correctly cites Figure 2. Added to the errata table as
  MEPS-E029 (kind: text).

## Changes to the errata skill

`skills/meps-statbrief-errata` table 0.4.0: 42 rows, 29 slips (adds MEPS-E029). Script unchanged (0.1.0).

## Limits

The echo detector sees only exact skeleton matches with one decimal number changed, so paraphrased repeats (like
#181) and integer slips are out of its scope. The pair detector needs the count in millions in a parenthesis next
to the percent. Hand checks are by AI agents reading the live pages on 2026-11-09; a person has not checked them.
Page hashes are in `m9-summary.json` of the job output (kept locally).
