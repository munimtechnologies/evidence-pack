# Exploratory addendum to check R2, Brief #507: results. No candidate rule reproduces Table 1 (v1)

MV2 of Munim, Inc., 2026-11-06. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r507x-prereg-v1-2026-11-05.md` (tag v0.9.41). Code: `meps/r507x.py` 0.1.0
(Apache-2.0, tag v0.9.41). Text and data CC BY 4.0 (the published numbers are AHRQ's). Research information about
published statistics, not medical advice. No endorsement by AHRQ is implied; AHRQ has not been contacted.
**Exploratory and post hoc. It changes no R2 grade** (R2: 182 of 190 computable cells exact, 4 of 4 predictions
held; `findings/meps-r2-results-v1-2026-11-05.md`).

## What was tested

In R2, Brief #507's Table 1 (non-elderly families with out-of-pocket spending, by poverty status and family
structure, 2015) matched our population and all four poverty rows to within one weighted family. But within
each row, about 875,605 weighted families that we count as having children (a member aged 0-17 by AGELAST) sit
in the brief's no-children columns, and their adult count does not change. The addendum fixed nine rules for
who counts as an adult or a child (R0 is the graded R2 rule), fixed before the job read the extra variables, and
asked whether any of them reproduces all 16 printed counts.

- **E1:** at least one of R1-R8 reproduces all 16 Table 1 counts.
- **E2:** the best rule (most exact cells; ties broken by the smallest summed absolute gap) is one of the
  round-specific age rules R2, R3 or R4.

## Run

Job `meps-r507x-v1`, 2026-11-05 19:46-19:49 UTC, sealed container, code cloned from tag v0.9.41; its unit tests
passed first. Input: the HC-181 ASCII zip, 9,929,884 bytes, SHA-256
`75e50de4bdbd2dcc08c61472c1926395d322d5add57f155b638b23033822e5ee` (the same file as R2). **Every gate passed:**
35,427 records; all of R2's #507 gates (14,522 CPS families); PERWT15F > 0 for 33,893; INSC1231 1 / 2 = 35,067 /
360; the 12 REFRL15X counts; MOPID53X = -1 for 22,791 and DAPID53X = -1 for 26,919; and the four age bins
(-1, 0-17, 18-64, 65-85) of AGE15X, AGE31X, AGE42X and AGE53X, each exactly as the codebook prints them.

## Results (16 Table 1 counts per rule; gaps in weighted families)

| Rule | Child rule (adult: same age variable >= 18) | Exact of 16 | Summed abs. gap | Largest gap | Families with no adult | Structure cells exact / close (of 16) |
|---|---|---|---|---|---|---|
| R0 | AGELAST 0-17 (graded R2 rule) | 0 | 1,751,211 | 377,401 | 1 | 9 / 11 |
| R1 | AGE15X 0-17 (age on 12/31/15) | 0 | 1,751,211 | 377,401 | 1 | 9 / 11 |
| R2 | AGE31X 0-17 (round 3/1) | 0 | 4,511,802 | 1,057,630 | 22 | 8 / 9 |
| R3 | AGE42X 0-17 (round 4/2) | 0 | 2,710,479 | 559,063 | 7 | 10 / 12 |
| R4 | AGE53X 0-17 (round 5/3) | 0 | 1,556,237 | 346,222 | 0 | 10 / 12 |
| R5 | AGELAST 0-17 and PERWT15F > 0 | 0 | 1,591,104 | 216,428 | 1 | 10 / 10 |
| R6 | AGELAST 0-17 and INSC1231 = 1 | 0 | 1,751,211 | 377,401 | 1 | 9 / 11 |
| R7 | AGELAST 0-17 and REFRL15X = 4 | 0 | 3,290,524 | 619,583 | 1 | 6 / 6 |
| R8 | AGELAST 0-17 and a parent (MOPID53X / DAPID53X) in the same family | 0 | 857,896 | 218,041 | 1 | 8 / 9 |

"Structure cells" are the 16 family-structure cells of Figures 3-4 (other than "All") recomputed under each rule.
Under R0 they are R2's graded cells (9 exact, 11 close). The summed gaps of R0, R4, R5 and R8 were re-added by hand
from `table1-rules.csv` and agree with the job's figures.

## Grades (as written)

- **E1: did not hold.** No rule reproduces all 16 counts. No rule reproduces even one: every rule has 0 exact
  cells.
- **E2: did not hold.** All nine rules tie at 0 exact cells. The smallest summed gap, and so the best rule, is
  R8 (parent in the family), which is not a round-age rule.

As pre-registered, the rule AHRQ used stays unidentified, and no further rules are tested in this addendum.

## What the nine rules show

- **The newborn guess is not supported.** We had guessed that babies born during 2015 after an earlier
  interview round were counted as neither adults nor children (age -1 in that round). The round-age rules make
  Table 1 worse (R2, R3) or barely better (R4, 11% smaller summed gap). They also change who counts as an
  adult, which moves families between the one-adult and two-adult columns and takes the population away from
  the printed total (R2 is 169,598 weighted families short and R3 45,047 short). Under AGELAST the population
  matches to within half a family.
- **R1 and R6 change nothing.** Age on 12/31/15 and in-scope status on 12/31/15 put every family in the same
  Table 1 cell as AGELAST does.
- **R8 explains about half of the gap, but not its pattern.** Counting a member aged 0-17 as a child only if
  his or her mother or father is in the same CPS family keeps every family's adult count. It halves the summed
  gap (857,896 against 1,751,211) and brings the high-income one-adult cells to within 247 weighted families
  of the printed counts. But it overshoots, moving more families out of "with children" than the brief does, in
  all four one-adult rows and in the poor two-adult row. In the low-, middle- and high-income two-adult rows it
  falls short (by 38,719, 73,331 and 218,041 weighted families).
- **R5 and R7 also miss in both directions.** Requiring a positive person weight (R5) or that the child be the
  household reference person's child (R7) moves too many families in some rows and too few in others.
- **The structure figures barely move.** No rule makes more than 10 of the 16 structure cells exact (R0: 9).
  The one-adult-with-children median stays between $105.19 and $109.97 against the printed $116 under every
  rule except R2 ($116.93, which rounds to $117), and R2 does worse on Table 1 than any other rule.

## What it means

Brief #507 reproduces exactly at the population and income-group level. How it splits families into "with"
and "without" children follows a rule that neither the brief nor any of nine natural readings of the public
file's variables recovers. This is a documentation gap: the reader cannot tell from the brief which members
count as children. It is not evidence that a published number is wrong. Two of the readings tested (R5, R8) come
closer than plain age, which suggests the rule involves family relationships or analysis weights, not age
timing. Telling them apart would need AHRQ's own definition. A note asking for it waits for a human check, like
every other note to AHRQ.

Limits: nine rules fixed in advance by us; one brief; the unit is the CPS family on 12/31/15, which the brief
does not name either (its population and income rows match under it); no human has reviewed this.

## Files

- `findings/meps-r507x-v1/r507x.json`: gates, column positions, the file hash, and per rule the 16 Table 1
  comparisons, column totals and structure cells.
- `findings/meps-r507x-v1/table1-rules.csv`: one row per rule and Table 1 cell (published, ours, gap, exact).

Only aggregate weighted counts and estimates left the job; no person-level data is published.
