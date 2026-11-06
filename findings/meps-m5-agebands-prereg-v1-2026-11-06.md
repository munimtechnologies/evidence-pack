# Pre-registration: census M5. Do the age bands inside one MEPS Statistical Brief figure overlap or leave an age out? (v1)

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the scan runs. Text CC BY 4.0; code `meps/m5ages.py` 0.1.0 (Apache-2.0). Research information about
published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

## Why

During census M4's hand check (`findings/meps-m4-titles-results-v1-2026-11-06.md`), two reads of Brief #170 (2007)
found Figure 5's first panel labelled "Age 40-65" next to a panel labelled "Age 65+", so age 65 falls in both
groups, while the brief's text says "Women age 40 to 64" and "women under age 65". Census M3
(`findings/meps-brief-tables-v1/`, 2,999 accessible data tables) holds every table's row and column labels, so the
same kind of slip can be looked for across the whole series at almost no cost.

## What was seen before this was written (disclosed)

- #170 Figure 5 (above) and the #170 text quoted above.
- The row labels of the 109 M4 candidate pairs (34 briefs) in `findings/meps-m4-titles-v1/m4-candidates.csv`, and
  those briefs' figure labels while hand-checking M4. No other age-band slip was noticed there, but that was not a
  systematic look.
- No age-band scan of M3 has been run. M3's cells for #170 tables 5 and 6 were read to confirm the labels are in
  M3 ("Age 40-65 / Breast exams", "Age 65+ / Breast exams").

## Method (machine scan; `meps/m5ages.py` 0.1.0)

1. **Figure:** all M3 tables in one brief with the same label (older pages print one figure as several panels)
   form one figure.
2. **Age bands:** every row label and every " / "-separated part of every column label is read, unless it names
   another unit (%, $, percent, poverty, FPL, income, hour, visit, day, week, month, dollar, condition). It must say
   "age"/"ages"/"aged", or the figure's title must. Forms: "40-65" (also en or em dash, "to", "through"), "65+",
   "65 and older/over", "65 years and older", "65 or older", "under 18", "less than 18", "younger than 18",
   "below 18", "<65". Ages 0 to 110 only.
3. **Flags:** for each pair of distinct bands in one figure where neither contains the other (a total band such as
   "40 and over" and its parts are not flagged): *overlap* if they share an age; *gap1* if exactly one age lies
   between them and no band of the figure covers it.
4. **Hand check of every flagged figure** (next runs): two separate reads of the brief page
   (`stat<N>.shtml`) copy the figure's band labels exactly and every sentence of the text, definitions, notes or
   other tables that states those groups' age limits. Each flagged figure is then one of:
   - **Label slip:** a band label conflicts with how the brief itself states that group's ages, or two bands that
     the brief treats as separate groups share an age or leave one out, with no explanation.
   - **By design:** the brief states the same bands (for example deliberately overlapping groups), or explains the
     omitted age.
   - **Parser false flag:** the numbers are not ages, or the scan misread a label.
   - **Artefact:** M3's label text differs from the page.
   Only cases on which both reads agree are counted; a disagreement gets a third read, which decides (2 of 3), and is
   logged.

## Predictions (graded exactly as written)

- **E1 (method check):** the scan flags #170 Figure 5 as *overlap*, bands 40-65 and 65+. If it does not, the parser
  failed and that is reported first.
- **E2 (primary):** apart from #170 Figure 5, between 1 and 8 figures (inclusive) have a confirmed label slip.
- **E3 (scan size):** the scan flags between 2 and 60 figures (inclusive), #170 Figure 5 included.

## Limits

M3 covers only tables printed as accessible text; image-only figures are outside it. Only bands inside one figure
are compared; a figure whose bands are consistent with each other but not with the text is found only if the hand
check of some other flag happens to show it. The unit filter may drop real age labels that also name a unit, and
the title rule may read non-age ranges in a figure whose title mentions age (those become parser false flags). A
label slip is a documentation error, not evidence that any estimate is wrong: the underlying estimate may use the
right ages.

## Why this is new

Searches on 2026-11-02, 11-03 and 11-06 found no errata for these briefs; a web search on 2026-11-06 for audits of
overlapping age categories in MEPS briefs or federal statistical reports found none (inconclusive, as any search). Overlapping class limits ("40-65" and "65+") are a known textbook error in frequency
tables; no one appears to have counted them across a federal statistical report series.
