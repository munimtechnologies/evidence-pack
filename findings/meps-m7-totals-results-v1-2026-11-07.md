# Results: census M7. Does any MEPS Statistical Brief print a Total outside the range of its own subgroups? (v1)

MV2 of Munim, Inc., 2026-11-07. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0; code `meps/m7totals.py` 0.1.0 (Apache-2.0). Research information about published statistics, not
medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.

Pre-registration: `findings/meps-m7-totals-prereg-v1-2026-11-07.md` (tag v0.9.52). Job `meps-m7-totals-v1` cloned
tag v0.9.52, ran the unit tests (pass) and the scan on 2026-11-07 12:28-12:31 UTC. Its three output files are in
`findings/meps-m7-totals-v1/`, copied unchanged.

## Scan

| | |
|---|---|
| M3 tables read | 2,999 |
| Tables with at least one Total/group pair | 332 |
| Pairs | 1,907 |
| ok / sum_like / excluded_label / above / below | 1,586 / 89 / 183 / 42 / 7 |
| Pairs with the bound applied (ok + above + below) | 1,635 |
| Flags (above + below) | 49 |
| Figures flagged | 11 (6 above, 5 below) |
| #558 Figure 1 control: Age and Race/ethnicity pairs | both ok |

All 11 flagged figures were hand-checked (fewer than 40).

## Hand check (two WebFetch reads of each brief page, 2026-11-07; both reads agreed on every class)

| Rank | Brief | Figure | Total vs groups (M3 = page) | Class |
|---|---|---|---|---|
| 1 | #567 (2025) | Figure 1, combined benzodiazepine-opioid use, adults 65+ | Overall 1.5; Men 1.9, Women 2.0 | **Inconsistent total** |
| 2 | #460 (2014) | Figure 1 | U.S. 10.0; only states above the U.S. average | Not a partition |
| 3 | #460 (2014) | Figure 4 | U.S. 10.0; only states below the U.S. average | Not a partition |
| 4 | #337 (2011) | Figure 5, private insurance share | Total 27.6; Ambulatory 32.2, Prescription 33.9 | Not a partition |
| 5 | #423 (2013) | Figure 3 | Total expenditures in billions against rows of dollars and percentages | Not a mixture statistic |
| 6 | #460 (2014) | Figure 3 | U.S. 10.0; three states above the U.S. average | Not a partition |
| 7 | #297 (2010) | Figure 1 | Overall expenses 84.9; persons with each type of expense (overlapping) | Not a partition |
| 8 | #352 (2011) | Figure 1 | Overall expenses 84.4; same design | Not a partition |
| 9 | #414 (2013) | Figure 1 | Overall 84.6; same design | Not a partition |
| 10 | #460 (2014) | Figure 2 | U.S. 10.0; only states below the U.S. average | Not a partition |
| 11 | #536 (2021) | Figure 13, 2020 column | United States 86.2%; Small 86.5%, Medium 89.0%, Large 89.7% | **Inconsistent total** |

### The two inconsistent totals

**Brief #567** (benzodiazepine use and concurrent benzodiazepine-opioid use among adults aged 65 or older, data
2021-2022). Figure 1 prints combined use as Overall 1.5, Men 1.9, Women 2.0 (both reads, verbatim). The population is
"all individuals aged 65 and older", split by sex, so the overall rate must lie between the two sex rates. The text
says concurrent use "was higher among older women (2.0%) compared to older men (0.9%)" and gives 1.5 percent overall.
With men at 0.9 and women at 2.0, an overall 1.5 needs women to be about 55% of adults 65+, which is about right. The
figure's "1.9" for men is very likely a typo for 0.9. No note or erratum on the page (read 2).

**Brief #536** (enrollment in private-sector employer plans with a deductible, 2008-2020). Figure 13's data table prints
the 2020 United States value as 86.2%, below all three firm-size groups (86.5, 89.0, 89.7). The Highlights and the
Deductibles section both say the overall percentage "increased from 86.6 to 89.2 percent" from 2019 to 2020; the
table's 2019 value (86.6) matches the text. The text also says the overall share rose 18.5 percentage points since
2008; the table's 2008 value is 70.7, and 89.2 - 70.7 = 18.5 (with 86.2 it would be 15.5). The table's 2020 "86.2" is
very likely a typo for 89.2, which lies inside the groups' range. No note or erratum for Figure 13 (read 2).

In both cases the figure disagrees with the brief's own text, and the text's number is the one consistent with the
groups. Both are documentation slips in a figure; the estimates in the text look right.

### The nine false flags

- **Selected groups (5):** #460 Figures 1-4 show only states whose rate differs from the U.S. average ("in states
  with a higher/lower percentage than the U.S. average"), so the U.S. value sits outside them by design.
- **Overlapping groups (3):** #297, #352 and #414 Figure 1 give the share of all people with any expense and with each
  type of expense; one person counts in several types, so "Overall" exceeds every type.
- **Groups that leave part out (1):** #337 Figure 5's Total covers all hypertension spending, but only ambulatory care
  and prescription medicines are shown; inpatient, emergency and home health spending (Figure 2's "Other services")
  are in the Total only.
- **Not a mixture (1):** #423 Figure 3 mixes dollar and percentage rows under a dollar Total.

## Predictions, graded exactly as written

| | Prediction | Result | |
|---|---|---|---|
| G1 (control, negative) | #558 Figure 1 paired with Age and Race/ethnicity, both ok | both ok | **held** |
| G2 (coverage) | at least 300 pairs with the bound applied | 1,635 | **held** |
| G3 (scan size) | 3 to 80 figures flagged | 11 | **held** |
| G4 (false flags) | more than half of hand-checked figures are Not a partition or Not a mixture statistic | 9 of 11 | **held** |
| G5 (primary) | 1 to 5 hand-checked figures are Inconsistent total | 2 (#567 F1, #536 F13) | **held** |

5 of 5 held.

## What this adds up to

- Across 1,635 Total/group comparisons in 332 tables of the MEPS Statistical Brief series, two Totals fall outside
  their own groups' range, and both turn out to be a figure that contradicts the brief's own text (#567, 2025; #536,
  2021). Neither was known to us before the scan.
- With M4 (#533 title, #170 age band), M5 (#227 age band), R2b (#497 swap, #558 labels) and r558x (#558 Figure 1),
  the series audit has now found eight figure-level documentation slips by pre-registered methods.
- The range bound is cheap but weak: #558 Figure 1, whose age rates cannot average to its Total (see
  `findings/meps-r558x-results-v1-2026-11-07.md`), passes it. A v0.2 could skip figures whose titles say "selected" or
  "higher/lower than the U.S. average", and type-of-service figures where one person can have several types.
- Both slips were exposed by the brief's own text. A census that compares every number in the text with the cited
  figure's cells would find this kind of slip directly; that is the natural next census.

## Files

- `findings/meps-m7-totals-v1/m7-summary.json`, `m7-flags.csv` (the 49 flags), `m7-pairs.csv` (all 1,907 pairs).

## Prior art and limits

No errata for #567 or #536 were seen on their pages (2026-11-07). Searches on 2026-11-07 found no public audit
applying the mixture bound across a federal statistical report series (inconclusive, as any search). One scan, one
parser, hand check by two automated page reads, no human review. Image-only figures are outside M3. A Total inside its
groups' range can still be wrong.
