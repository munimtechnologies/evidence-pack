# Claim-provenance checker v1: evaluation plan (v7, run 151, 2026-10-21)

**Status note (rule i2): written 2026-10-21 ~21:00Z. At that time no checker code exists. Package 4 v19 and package 5 v28 exist (local, unpublished) and are not yet hashed. No mutations or labels exist, and the H-B package has not been drafted.** v7 is a dated amendment made before code freeze, as v5 section 0 allows. v1-v6 stay unedited in this folder. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has reviewed it. Licence: CC BY 4.0.

**v7 is the last amendment before code.** After it, the definitions are frozen, the base texts are hashed, and the code is written to v5 + v6 + v7. A defect found later is not fixed by a new plan version. It is reported as a P3 false positive or a P2/P1 miss, with its cause.

**Everything in v5 and v6 stands except what this file replaces.** Replaced: the v5 "Linked table" definition; the R2 module; the R7-a count phrase and list rule; the R8 dose rule; the 2.1 coverage line for S40 and S77; the R2 and R7 rows of v5 4.3; the 6.1 prediction; and the order of work.

## 0.7 v6 -> v7 amendments
Source: `hand-pass-r2-r7a-r8-run151.md` (open item o5).
1. **R2 linking, ranges, cell values, column choice and predicate binding defined.** Under v5/v6 readings, 1 to 4 false R2 flags on the unmutated texts (P4 L45, L136; P5 L195, L223). Under v7: 0.
2. **R7-a uses v4's count phrase literally,** and gets a name rule and three list readings. Read literally, v5 gives 2 to 6 false flags (P4 L129, L160, L172; P5 L27/L86/L163, L209, L223). Under v7: 0. The run-147 check had read the rule more loosely, so its R7-a sites (P4 L134, P5 L228 "four meta-analyses", L234) are not sites.
3. **R8 dose pairing defined.** v5 said nothing about species, pairing or weight, and P4 v19 L65 now holds three conversions in one bullet. Under v7: 0 flags.
4. **G1 governs every number read by R2, R4-a, R7-a and R8.** For R4-a this changes nothing on the base texts.
5. **Coverage:** S40 is now covered (R2) and S77 is not (R8: no stated weight). The total is still **21 of 82 (25.6%)**.
6. **The hash job's input path** is defined (section 8).
7. **Unchanged:** the seed (20261021); the base texts and their closed edit lists; the mutation target, layout, collision rule and matching rule; the pass thresholds; the baselines; the job separation.

## 2.1 Development coverage (v7)
- Covered: as v6, **minus S77, plus S40** (R2 range-in-K, "in K of M <noun>").
- Not covered: as v6, minus S40, plus S77.
- **21 of 82 rows (25.6%).**

## 3. Changed definitions
### Linked table (replaces v5's)
- A pipe table **carries** the [n] citations printed in its governing heading (the nearest markdown heading line above it) or in any of its cells.
- A **line** of the cut text outside any table (one physical line: a bullet item or a paragraph) is **linked** to the table when it carries one of those [n]. Citation lists and ranges count each number, so "[6-8]" carries 8.
- Nothing else links. v5's capitalised-heading-word half is dropped.

### R2 tables (replaces v5's)
- **Claims** are read sentence by sentence in linked lines. The claim's own sentence chooses its candidate columns and its predicate.
- **Range:** two G1 numbers joined by "-" or " to ". If either end has "%", both are percentages. Interval pairs are not ranges:
  - the interval of a CI tuple (v6 G3-G5);
  - a pair directly after a G2 label;
  - a pair directly after "<number>, ".
- **Cell values:** for a cell holding a CI tuple, its estimate. Otherwise every G1 number in the cell, typed as a percentage or plain.
- **Candidate columns:** every column whose header shares a word with the claim's sentence. Matching is case-insensitive, whole word, with v4 boundaries. G2 labels and the words vs, per, of, and, or, the and n are ignored. A claim with no candidate column is out of scope and counted.
- **Lenient rule:** a claim is flagged only if it fails in every candidate column.
- **Range check:** fails in a column unless both endpoints equal values of the same type in that column. Values are compared within printed rounding (the cell value rounded to the endpoint's decimals equals the endpoint).
- **N-of-M:**
  - N and M are digits or one..twenty; "N of the M" is included.
  - The predicate is the nearest fixed predicate before it in the same clause, at most 8 words before, with no other N-of-M in between. Longest match wins, so "CI below 1" beats "below 1".
  - The fixed predicates are v5's. An N-of-M with no predicate is out of scope and counted.
  - It fails in a column when M differs from the table's row count or N differs from the predicate count in that column. CI predicates use columns holding CI tuples only.
- **Range-in-K:** a range directly followed by "in K <noun>" or "in K of M <noun>". It fails in a column when the number of that column's values inside the range differs from K, or when M (if printed) differs from the row count.
- R2b is unchanged.

### R7-a count vs its own list (replaces v5's)
- Prose only: not table cells and not the reference list.
- **Count phrase:** v4's: a number followed by records|trials|hits|studies|registrations with at most 3 words in between. The number is a G1 integer with no sign, "%" or "$", or a number word one..twenty (any case).
- **List:** the content of the parenthesis directly after the phrase. Otherwise, the rest of the sentence after the first ":" that follows the phrase in the same sentence.
- **Pieces and names:** pieces are split at top level only, never inside deeper parentheses or quotation marks. A piece is a name when its first character (after markdown and opening quotes are removed) is an upper-case letter, or it starts with a registry ID. A list with no name is not checked.
- **Readings:**
  - (A) the names before the first top-level ";", split on "," and " and ";
  - (B) the number of top-level ";" pieces that start with a name;
  - (C) the v5 sum: when every ";" piece starts with a name followed by a bare number, the sum of those numbers.
- **Flag** when the stated count equals none of the readings that apply.
- A count preceded by "no", "none", "0" or "zero" is never flagged.

### R8 dose (replaces v5's dose half; the sources half stands)
- **Scope:** only lines containing "body-surface-area" or "body surface area".
- **Animal dose D:** a G1 number followed by "mg/kg" (optionally "/day"), not preceded by "about".
- **Species of D:** taken from the first of mouse, mice, rat or rats found:
  1. after D in the same clause;
  2. else before D in the same sentence;
  3. else in the line's bold lead;
  4. else in the nearest earlier line of the same section that names one.
  The factor is 3/37 for mice and 6/37 for rats.
- **HED:** "about X mg/kg". It is checked against every D since the previous HED or human total: |D x factor - X| / X <= 10%.
- **Human total T:** a G1 number followed by "mg" or "g" (optionally "/day"), not followed by "/kg", and directly preceded by "about" or "to a human".
- **Pairing:** T is paired with every D since the previous T in the same sentence. If there is none, it is paired with the D's of the previous T.
- **Weight W:** "for W kg" within the 4 words after T; else "W kg" in the line's bold lead; else T is not checked.
- **Flag:**
  - a paired |D x factor x W - T| / T over 10% (g converted to mg);
  - two checked conversions in one package with different W.

### Numbers
G1 (v6) governs every number read by R1, R1b, R2, R4-a, R7-a and R8.

## 4.3 Eligible sites (R2 and R7 rows replace v5's)
- **R2: 5 sites, all on P4 L45:**
  - 4 ranges: 1.24-2.07, 8.0-10.4%, 4.4-7.4% and 0.77-0.81. One endpoint is moved to a value matching no candidate column.
  - 1 N-of-M: "seven of nine", changed by +/-1.
  - Range-in-K: 0 sites. P5: 0 sites. **Shortfall 3 of 8.** All 5 are planted in P4, so P4 gets 5 copies. P2 for R2 is 4 of 5 (5/8 of 5, rounded up).
- **R7:**
  - R7-a has 5 sites: P4 L160; P5 L172, L223, L228 ("seven RWE studies") and L250. Each takes count +1.
  - R7-b is as v5.
- **Redraw rule:** the mutation job redraws any R2 or R7-a mutation that still passes under the section 3 rules (logged as a collision).

## 6.1 Restated prediction (replaces v6's)
- On cut P4 v19 and cut P5 v28 (unmutated), the frozen code gives **0 scored flags**, apart from C5's known residual R5 flags (P5 L248, L252).
- The basis is literal hand passes for R1, R1b and R5 (run 150), R2, R7-a and R8 dose (run 151), R2b/R5b (runs 141-145) and R4 (run 146). For R3, R6, R7-b and R8 sources it is the run-147 operator check.
- Any other flag is a P3 false positive and is reported as such.

## 8. Order of work (replaces v6's)
1. Commit v7, the run-151 note and log entry 4.
2. **Hash job** (`basetext-hash-v1`: Python stdlib, network off, 1 CPU, 1 GB).
   - Its workdir holds exact byte copies of the two base files: `regen-package-4-spironolactone-aud-v19.md` (from 20261021T170928Z-medicine) and `regen-package-5-metformin-knee-oa-v28.md` (from 20261021T183738Z-medicine), copied with File Explorer.
   - It computes SHA-256 for each file, whole and cut (v4 cut rule, computed in code and asserted: P4 lines 1-227, P5 lines 1-367).
   - **The copies in that job folder are the H-A base texts of record.** The mutation job reads the same bytes.
   - The hashes go into log entry 5.
3. Code `claimcheck` to v5 + v6 + v7 (Python 3.11, stdlib, Apache-2.0), with unit tests on seed rows and synthetic strings only. Commit with tests run first, then freeze (log the commit).
4. Mutation job, then checker job, then score: v5 sections 4-6.

## 9. Limits (additions)
- The v7 R2, R7-a and R8 rules were written after reading the exact base-text lines they now pass. **Their fit to those texts is not evidence.**
- R2 is now narrow:
  - it reads only lines that share an [n] with a table, so P5 (author-year citations) has no R2 claims at all;
  - development coverage gains only S40.
- R2's H-A result is a test of 5 mutations on one line of one table. Read it as a feasibility check, not a recall estimate.
- The run-147 check over-read R7-a, and v5/v6 credited S77 from its description. **Descriptions and loose readings overstated coverage three times** (v5 2.1, run 147, S77). Only literal passes are trusted from here.
