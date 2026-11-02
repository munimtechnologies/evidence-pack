# Results: can MEPS Statistical Brief #569 be recomputed from the public-use file it names? (check R1, v1)

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r569-prereg-v1-2026-11-01.md` (tag v0.9.35, fixed before the job read any
microdata). Code: `meps/r569.py` 0.1.0. Text CC BY 4.0; code Apache-2.0. Research information about published
statistics, not medical advice. No endorsement by AHRQ is implied. AHRQ has not been contacted about this; a
human will check it first.

## Short answer

Mostly yes. All 24 non-MSA percentages in the brief's eight figures were recomputed from HC-243 to within 0.23
percentage points, and 19 of them round to the published value. Three of four predictions held. The headline
(Figure 2, women 50+ without diagnosed osteoporosis who ever had a bone density scan) came out at 42.750%
against a published 42.8%: it misses our "exact" rule by 0.0002 points, so P2 **failed** as written. The two
MSA percentages cannot be recomputed: HC-243 has no MSA variable (P3 held), which is what census M2 is about.

## Run

Job `meps-r569-v1`, exit 0 (unit tests, then the check). `h243dta.zip`, 5,789,896 bytes, SHA-256
`7fc534de09eff5fd81facb74d61511d322ebe8bc45af7b75441204fcaf9fb454` (the same browser download as check S2,
copied into the job folder by MV2's hands). 22,431 persons, 1,420 variables; 11,299 with a positive SAQ weight.
All needed columns were present (`missing_columns` empty).

## Grades (exactly as pre-registered)

| | prediction | result | grade |
|---|---|---|---|
| P1 (primary) | >= 20 of 24 cells close (within 0.5 points) | 24 of 24; largest gap 0.229 | held |
| P2 | headline (Figure 2, 50+, 42.8%) exact (within 0.05) | 42.7498, gap 0.0502 | **failed** |
| P3 | no MSA variable in HC-243 | none by name (MSA*, *METRO*) or by label | held |
| P4 | >= 18 of 24 cells exact | 19 of 24 | held |

## The 24 cells

| figure | group | published | recomputed | n | exact |
|---|---|---|---|---|---|
| 1 osteoporosis | 50+ / 50-64 / 65+ | 21.5 / 9.2 / 33.8 | 21.46 / 9.17 / 33.77 | 3,501 / 1,505 / 1,996 | yes / yes / yes |
| 2 ever DEXA | 50+ / 50-64 / 65+ | 42.8 / 24.8 / 67.6 | **42.75** / 24.80 / 67.57 | 2,608 / 1,318 / 1,290 | **no** / yes / yes |
| 3 (50-64) | any private / public only | 27.9 / 17.4 | 27.88 / 17.42 | 930 / 294 | yes / yes |
| 4 (65+) | Medicare only / + private / + other public | 69.4 / 72.4 / 45.8 | 69.45 / **72.47** / 45.85 | 515 / 569 / 191 | yes / **no** / yes |
| 5 | no usual source / usual source | 30.7 / 45.3 | 30.65 / 45.33 | 358 / 2,208 | yes / yes |
| 6 | Hispanic / NH White / NH Black / NH Asian | 25.4 / 47.7 / 37.1 / 30.4 | 25.39 / 47.69 / 37.14 / 30.42 | 308 / 1,719 / 411 / 110 | all yes |
| 7 | Northeast / Midwest / South / West | 44.1 / 43.9 / 42.1 / 41.7 | **44.03 / 44.13 / 41.98** / 41.74 | 438 / 559 / 1,003 / 608 | **no / no / no** / yes |
| 8 | low / middle / high income | 37.5 / 38.9 / 47.6 | 37.46 / 38.87 / 47.60 | 900 / 652 / 1,056 | all yes |

Standard errors (Taylor linearisation, VARSTR / VARPSU) are in `meps-r569-v1/r569.json`; they were reported, not
graded.

## What the misses look like (observations, not a diagnosis)

The pre-registration says a P2 failure is diagnosed only in a dated addendum, with the definitions unchanged.
No diagnosis is attempted here; two observations for that addendum:

- Three of the five non-exact cells are in **Figure 7**, the figure that also reports MSA, and they are the
  largest gaps (0.07 to 0.23 points). Every cell in Figures 1, 3, 5, 6 and 8 is exact. One possible explanation
  is that Figure 7 was built from a file version that carries MSA (and perhaps a different region measure),
  but we have not tested this and it may be wrong.
- The headline misses by 0.0002 points beyond the threshold (42.7498 rounds to 42.7); the two age bands that
  make it up are both exact.

## Sensitivity variants (reported, not graded)

- **B** (sex from the SAQ item `ADSEX42`): identical to the primary results in all 24 cells.
- **"A, DEXA universe B"** (dropping "no diagnosed osteoporosis" from the scan denominator): only 4 of 24 exact,
  so the brief's stated universe is the one that reproduces.
- **C** (SAQ age `ADAGE42`): our variant was mis-specified. In the HC-243 codebook, `ADAGE42` ("SAQ: SURVEY
  AGE") is a four-category item (4 = "50 OR OLDER", 6,671 persons), not an age in years, so our rule "age >= 50"
  selected nobody (n = 0 in every cell). This is our error, recorded as it ran; it does not touch P1-P4.

## What this does and does not show

- An outside analyst with only the public file the brief names, plus the brief's own text and the codebook,
  can reproduce 24 of its 26 published percentages within 0.23 points, 19 of them to the published decimal.
- The two MSA percentages need a variable that the public 2022 file does not have; the brief does not say where
  it came from (see census M2, `findings/meps-geo-results-v1-2026-11-02.md`).
- One brief only. Statistical-significance statements in the brief were not tested. Only aggregate percentages
  for published cells leave the job.

## Prior art

Searches on 2026-11-02 found no published reproduction of MEPS Statistical Brief #569, and no systematic
reproduction of MEPS Statistical Briefs from their named public-use files. IPUMS MEPS harmonises the files and
AHRQ publishes the code behind its summary tables, but neither recomputes the briefs. The search was a short web
and GitHub search, not a full literature review.

## Files

`meps-r569-v1/r569.json` (file hash, variables found, per-cell estimates, SEs, n, sensitivity variants, grades),
`meps-r569-v1/cells.csv`.
