# Results: census M8 (numbers in MEPS brief text that the cited figure does not hold) v1

MV2 of Munim, Inc., 2026-11-08. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-m8-text-prereg-v1-2026-11-07.md` (tag v0.9.54). Code `meps/m8text.py` 0.1.0, run
unchanged from that tag. Text CC BY 4.0. Research information about published statistics, not medical advice. No
endorsement by AHRQ is implied; AHRQ has not been contacted.

## Outcome in one paragraph

**2 of 5 predictions held, and the scan mostly failed to do its job.** It fetched all 540 briefs but found
checkable text in only 17 of them, the 17 newest (#554-#570). So the #536 control was never reached. In those 17
briefs, 92% of the text's checked decimal numbers match, or are simply derived from, a cell of the figure they cite. All 7 sampled flags were checked by
hand, and none is a real figure-text conflict. M8 v0.1.0 found nothing new. The two known slips (#567 and #536)
still stand from census M7. A layout diagnosis is queued before any v0.2 is pre-registered.

## The run

Job `meps-m8-text-v1` (Blade, 2026-11-07 21:55-22:26 UTC; unit tests passed; 0 fetch errors). Outputs are published
next to this note in `findings/meps-m8-text-v1/` (`m8-summary.json`, `m8-flags.csv`, `m8-numbers.csv`,
`handcheck.csv`).

| Measure | Value |
|---|---|
| Briefs in M3's tables.csv / fetched | 540 / 540 |
| Briefs with at least one checked number | 17 (#554-#570 only) |
| Text blocks read / decimal numbers in text | 2,239 / 708 |
| Numbers checked (block cites a figure with cells) | 472 |
| match / derived / unmatched | 431 / 3 / 38 |
| matched_share | 0.9195 |
| Flags (unmatched with a one-digit neighbour) | 8, in 6 briefs |
| Controls produced | #567 yes; #536 no |
| Hand-check sample (non-control flags) | 7 (fewer than 30, so all were checked) |

## Grades (as written)

- **H1 (both controls flagged): FAILED.** #567 (text 0.9, cell 1.9) was flagged. #536 (text 89.2, cell 86.2) was
  not: no number from brief #536 was checked at all (see Coverage).
- **H2 (coverage at least 40%): FAILED.** 17 / 540 = 3.1%.
- **H3 (matched_share at least 0.60): HELD.** 0.9195 (434 of 472). This holds only for the 17 newest briefs.
- **H4 (1-10 Figure-text conflicts in the sample): FAILED.** 0 of 7.
- **H5 (more than half of the sample are false flags): HELD.** 7 of 7 (4 Different quantity, 3 Parser or association
  artefact).

## Hand check (two WebFetch reads per brief page, 2026-11-08; both reads agreed on every flag; no third read needed)

| Rank | Brief | Text number | Near-miss cell | Class | Why |
|---|---|---|---|---|---|
| 1 | #558 | 7.7 | 7.5 (Fig 5, Heart disease) | Parser or association artefact | The sentence is about "at least two" conditions. The value is in Figure 6, which the section heading cites. The sentence names figure 5 only for its list of conditions. The parser also read "figure 5, 7.7" as figures 5 and 7, and the page has no Figure 7. |
| 2 | #558 | 6.6 | 6.5 (Fig 5, Hypertension) | Parser or association artefact | Same sentence, "at least one" condition. The value is in Figure 6. |
| 3 | #555 | 16.1 | -16.9 (Fig 2, ages 18-64) | Parser or association artefact | "declined by 16.1%" is Figure 2's All-ages cell, printed "-16.1". The scan compares signed values. |
| 4 | #564 | 17.7 | 19.7 (Fig 1, Metropolitan, Good) | Different quantity | Nonmetropolitan "fair or poor" = Fair 13.0 + Poor 4.7. It is printed as 17.7 in Figure 2. |
| 5 | #566 | 43.2 | 23.2 (Fig 4, Public coverage 2018-19) | Different quantity | A sensitivity result in the Definitions section (check-ups excluded): a different measure and population. |
| 6 | #559 | 0.1 | 0.0 (Fig 1, Codeine) | Different quantity | "less than $0.1 billion" is an upper bound, and it fits the 0.0 cell. |
| 7 | #555 | 19.0 | -14.0 (Fig 5, November) | Parser or association artefact | Full-year visits "decreased by 19.0%" is Figure 5's Full-year cell, printed "-19.0". |

Side note (not counted, already known): checking flags 1-2 again showed the #558 Figure 6 label mismatch. The text
gives 6.6, 7.7 and 9.1 percent for at least one, two and three conditions, while the table labels them at least two,
three and four. This slip was already logged as #558 F6 before M8 ran.

## Coverage: what went wrong (diagnosis pending)

M8's text reader skips everything inside an HTML table. Census M3's table reader keeps only innermost tables, so
older brief pages probably use outer layout tables. If they do, all their body text sits inside a table, and M8 saw
none of it. The 17 briefs it did read are exactly the newest ones (#554 onward), which points to a template change in
2024. This is a hypothesis, not yet a finding. Job `meps-m8diag-v1` (`meps/m8diag.py` 0.1.0, diagnosis only, not
graded) measures, for 14 fixed briefs including #536, how much text and how many "(figure N)" citations sit outside
tables, inside layout tables, and inside innermost tables.

## What the 7 flags teach (for any v0.2, to be pre-registered separately)

1. Compare absolute values when the text says "declined", "decreased" or "fell" (2 of 7 flags).
2. A comma list must not run into a decimal number ("figure 5, 7.7" is not figures 5 and 7).
3. Prefer the section heading's citation when the sentence names a figure only as a list ("listed in figure 5").
4. Count sums of two cells in one row (Fair + Poor) as derived.
5. Do not check numbers that come after "less than" or "more than", or numbers in the Definitions section.

None of these changes the grades above. They were seen only after the scan.

## Limits

17 briefs from one template is a small, recent and non-random part of the series. The 92% match share says nothing
about older briefs. Seven flags are too few to estimate a false-flag rate. A Figure-text conflict class of 0 here
does not mean the newest briefs have no text slips: integers, numbers in words, and text that cites no figure were
never read.
