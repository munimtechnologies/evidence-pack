# Results: census M5. Age bands that overlap or leave an age out inside one MEPS Statistical Brief figure (v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code `meps/m5ages.py` 0.1.0 (Apache-2.0). Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

Pre-registration: `findings/meps-m5-agebands-prereg-v1-2026-11-06.md` (tag v0.9.47). Job `meps-m5-agebands-v1`
cloned tag v0.9.47, ran the unit tests (pass) and the scan on 2026-11-07 03:06-03:09 UTC. Its three output files are
in `findings/meps-m5-agebands-v1/`.

## Scan

| | |
|---|---|
| M3 tables read | 2,999 |
| Figures (tables sharing one label in one brief) | 2,873 |
| Figures with at least one age band | 393 |
| Flags | 5 (4 overlap, 1 gap1) |
| Figures flagged | 4 |
| #170 Figure 5 flagged as overlap 40-65 / 65+ | yes |

## Hand check (every flagged figure, two WebFetch reads of the brief page each, 2026-11-07)

| Brief | Figure | Flag | Read 1 | Read 2 | Class |
|---|---|---|---|---|---|
| #165 (2007) | Figure 3 | overlap "BMI <25" / "18-44" | "BMI <25" is a row (healthy weight); ages are the columns "18-44", "45-64", "65+" | same | Parser false flag |
| #227 (2008) | Figure 4 | gap1 "< 18" / "19-25" | labels "< 18", "19-25", "26-35", "36-45", "46-55", "56-60", "61-64"; no label covers 18 | same | **Label slip** |
| #509 (2018) | Figure 2 (2 flags) | overlap "Large (11-50)" with "Children (0-17)" and "Adults (18-64)" | "Large (11-50)" is a practice-size row (number of doctors); ages are "Children (0-17)", "Adults (18-64)", "Elderly (65+)" | same | Parser false flag |
| #170 (2007) | Figure 5 | overlap "Age 40-65" / "Age 65+" | checked in census M4 (two reads); text says "Women age 40 to 64" | | Label slip (control, not counted in E2) |

Brief #227 ("Length of Coverage in the Individual Health Insurance Market for the Non-Elderly U.S. Population,
2006"): both reads agree that Figure 4 and its data table label the age groups "< 18", "19-25", "26-35", "36-45",
"46-55", "56-60" and "61-64", so no label includes age 18. The brief's population is ages 1-64 (Table 1 and Figures 1
and 2 say "Ages 1-64"; "Age is defined as age at the end of 2006"), the words "children", "under 18" and the number 17
appear nowhere, and nothing explains a missing age. Each of the figure's two distributions adds to about 100 percent
(read 2: 99.9 and 100.1), so 18-year-olds were very likely counted in one of the groups and the label, not the
estimate, is what is off. Which group holds them cannot be told from the page.

## Predictions, graded exactly as written

| | Prediction | Result | |
|---|---|---|---|
| E1 | #170 Figure 5 flagged as overlap 40-65 / 65+ | flagged | **held** |
| E2 | apart from #170 Figure 5, 1 to 8 figures with a confirmed label slip | 1 (#227 Figure 4) | **held** |
| E3 | 2 to 60 figures flagged, #170 Figure 5 included | 4 | **held** |

3 of 3 held. E2 held at its lower bound, on one figure.

## What this adds up to

- Across 393 figures that print age bands, the scan finds two documentation slips in total: #170 Figure 5 (age 65 in
  two groups; found by hand in M4) and #227 Figure 4 (age 18 in no group; new here). Both are labels, not estimates.
- The other two flagged figures are scan false flags of one kind: a non-age range ("BMI <25", "Large (11-50)") in a
  figure whose title says "by age". A v0.2 would read only the label dimension that carries the ages.
- Not covered: image-only figures (outside M3), bands that agree with each other but not with the text, and ages
  written in words.

## Files

- `findings/meps-m5-agebands-v1/m5-summary.json`, `m5-flags.csv` (the 5 flags), `m5-bands.csv` (the age bands of
  all 393 figures), copied unchanged from the job's output.

## Prior art and limits

No errata for #165, #170, #227 or #509 were found (searches 2026-11-02 to 11-06; inconclusive, as any search). One
scan, one parser, hand check by two automated page reads, no human review. A label slip is a documentation error and
says nothing about whether any estimate is wrong.
