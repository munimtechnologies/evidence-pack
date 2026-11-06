# Results: census M4, repeated figure titles inside one MEPS Statistical Brief (v1)

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code `meps/m4titles.py` 0.1.0 (Apache-2.0). Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

Pre-registration: `findings/meps-m4-titles-prereg-v1-2026-11-06.md` (tag v0.9.45, published before the scan ran).
Scan output: `findings/meps-m4-titles-v1/` (m4-summary.json, m4-candidates.csv, m4-short-keys.csv). Hand check:
`findings/meps-m4-titles-v1/handcheck.csv`.

## Grades (exactly as written)

| Prediction | Result | Grade |
|---|---|---|
| D1 (method check): #533 Figures 5 and 6 listed, class *different labels* | Listed, class different_labels | **Held** |
| D2 (primary): apart from #533, 1 to 5 briefs with a confirmed title error | 1 brief (#257, Figure 2), on a 2-of-3 read | **Held, narrowly** |
| D3: at most 2 candidate pairs confirmed as repeated figures | 5 pairs, all in #549 | **Failed** |

## The scan

The job (`meps-m4-titles-v1`, Dell, 2026-11-06 16:29-16:32 UTC, clone of tag v0.9.45, unit tests passed first)
read 2,999 tables carrying 540 distinct brief numbers in census M3's tables.csv (the pre-registration quoted M3's
"538 brief pages"; the difference of 2 is reported here, not resolved). 10 titles gave keys under 10 characters and
were set aside. It listed **109 candidate pairs in 34 briefs**: 89 *different labels*, 15 *same labels, different
values*, 5 *identical data*.

## Hand check

Every candidate was read on its brief page (`meps.ahrq.gov/data_files/publications/st<N>/stat<N>.shtml`) twice,
with different prompts, on 2026-11-06. Two disagreements got a third read (both logged in handcheck.csv).

| Verdict | Pairs | Briefs |
|---|---|---|
| Title error | 4 | 2 (#533, #257) |
| Repeated figure (same data printed twice) | 5 | 1 (#549) |
| Legitimate repeat | 98 | 31 |
| Not a repeat: the key rule cut two different titles too early | 2 | 2 (#201, #345) |
| Artefact (M3 title text differs from the page) | 0 | 0 |

Most legitimate repeats (90 of 98 pairs, counting #401's Figures 1a/1b) are panels of one figure: older briefs print the full figure title above
each panel's text table, and the panels are told apart by a heading, a row label or the insurance categories. The other 8 are the three
identical-title pairs below and the five #549 pairs where a figure repeats one column of its table. The
machine class predicted the hand verdict well at both ends: all 5 *identical data* pairs were repeated figures and
all 15 *same labels, different values* pairs were legitimate panels.

### The title errors

- **#533 (2021), Figure 6** (positive control, found during R2b and excluded from D2). Figure 6 carries Figure 5's
  title, "Percentage of persons by race/ethnicity and percentile of spending, 2018", over a table of types of
  service (prescribed medicines, ambulatory events, inpatient stays, home health, dental and other). The text
  heading for it is "Type of service (figure 6)".
- **#257 (2009), Figure 2.** Title: "Percentage of full year uninsured working adults ages 19-64, by race/ethnicity,
  sex, and education, 2006". Read literally it describes how the uninsured are spread across groups; the values
  (Hispanic 37.1%, Black non-Hispanic 17.9%, White/other non-Hispanic 12.1%; male 19.6%, female 12.6%) are the
  share of each group that was uninsured all year, and the groups do not sum to 100. Figure 1 of the same brief
  words the same kind of measure correctly ("Percentage of working adults ages 19-64, who were uninsured all
  year ..."). **This is a wording judgment, weaker than #533:** the first read called it not an error, the second
  and third called it an error. Graded by the 2-of-3 rule; a reader who judges it an acceptable shorthand would
  grade D2 as failed (0 briefs).

### The repeated figures (why D3 failed)

In **#549 (2023)**, the text table under each of Figures 2b, 4b, 5b, 6b and 7b repeats Table 2b, 4b, 5b, 6b or 7b cell
for cell, including the flags for relative standard errors over 30%. Example (Table 2b and Figure 2b, by age):
$310 / 91.8% / 7.4%*; $964 / 92.1% / 12.4%; $4,273 / 89.4% / 21.2%; $4,603 / 71.1% / 38.2%. The page does not say
why. This looks like a deliberate layout (each chart image followed by its data in text form), not a slip; D3
assumed repeated figures would be rare accidents, and that assumption was wrong for this brief's layout.

### Identical titles on different figures (not errors under the rule)

Three briefs give two separately numbered figures exactly the same title, so the title alone does not say which
is which. None names something its figure lacks, so none counts as a title error:
- **#24 (2003)** Figures 3 and 4, "MEPS, 1996-2001, All-Year Insurance Status, Children Under 18": percent vs
  millions of children (only Figure 4's row labels give the unit).
- **#100 (2005)** Figures 1 and 2, "Trends in children's eligibility for public insurance for families with
  children, 1996-2002": percent vs millions of families.
- **#570 (2025)** Figures 1 and 2, "Percent of Medical Visits Via Telehealth, 2021-2023": by provider type and
  metropolitan status vs by rurality.

### Other slips seen during the hand check (outside M4's definition; not counted)

These were seen after the pre-registration, while reading candidate pages. Each was read twice.
- **#170 (2007), Figure 5:** the first panel is labelled "Age 40-65" next to a panel labelled "Age 65+", so age 65
  sits in both. The brief's text says "Women age 40 to 64" and "women under age 65".
- **#217 (2008), Definitions:** "Low income: Persons in families with income from 100-99 percent of the poverty
  line." (presumably 100-199; "Middle income" starts at 200).
- **#91 (2005), Figure 1:** titled "... for the elderly and near elderly", but its first panel is "Dollars in billions
  for the 18 and older adult population"; neither the title nor the text mentions that panel.

The #170 label slip led to a new pre-registered census (M5: age bands that overlap or leave a one-year gap inside
one figure), published separately.

## Deviations

- The pre-registration did not say how a third read settles a disagreement. It was used as a tie-break (2 of 3).
  Both cases are listed with all three reads.
- A fifth verdict, "not a repeat: the key rule cut two different titles too early", was added for #201 and #345.
  Neither affects any grade.
- The reads were made with an AI page reader (two prompts per page), not by a person. Quotes were requested
  verbatim and checked across the reads.

## Limits

M4 sees only tables printed as accessible text; image-only figures are outside it. The key rule found the known
case but also produced 2 false candidates, and it cannot find a wrong title that is not repeated. One title error in
a repeated-title candidate set of 34 briefs says nothing about the rate in the rest of the series. A title error is a
documentation slip, not evidence that any estimate is wrong.
