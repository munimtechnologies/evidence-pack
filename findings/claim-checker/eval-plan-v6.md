# Claim-provenance checker v1: evaluation plan (v6, run 150, 2026-10-21)

**Status note (rule i2): written 2026-10-21 ~19:10Z. At that time no checker code exists. Package 5 v28 has just been made (local, unpublished), and package 4 v19 exists. No hashes, mutations or labels exist, and the H-B package has not been drafted.** v6 is a dated amendment made before code freeze, as v5 section 0 allows. v1-v5 stay unedited in this folder. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has reviewed it. Licence: CC BY 4.0.

**Everything in v5 stands except what this file replaces.** Replaced: the 2.1 coverage table; the shared "CI tuple" definition; the R1, R1b-b and R5 module text; and the 6.1 restated prediction. Added: the open items in section 8.

## 0.6 v5 -> v6 amendments
Source: the literal hand passes in `hand-pass-r1-r5-coverage-run150.md` (plan v5 section 8 step 2).
1. **CI-tuple grammar (R1, R1b-a).** As written, v5's definition gives at least 7 false flags on the unmutated base texts: P4 L45, L75, L136, L147 and P5 L46, L195, L353. Replaced by G1-G5 below. Under G1-G5 the same texts give 0 flags, and R1's eligible twin groups rise from 5 to 9.
2. **R1 compares by position** (estimate, first bound, second bound), not as sets.
3. **R1b-b value attribution** defined. v5 never said when a printed value belongs to an effect measure.
4. **R5 author-year candidates** defined, and the mapping fixed to the **first author**. Without this, any reading that accepts a capitalised word before a year flags "OARSI 2019", "JAMA 2025", "Initiative 2019", "Rheumatol 2025" and month-years, and an any-author reading makes "Kang 2026" and "Ruan 2022" ambiguous.
5. **Coverage restated from the found-in texts:** 21 of 82 (25.6%), against v5's 26-33 (section 2.1).
6. **Unchanged:** the seed (20261021); the base texts and their closed edit lists (v5 4.1); the mutation target, layout, collision rule and matching rule; the pass thresholds; the baselines; the job separation.

## 2.1 Development coverage (v6; traced against found-in versions)
| Status | Rows | n |
|---|---|---|
| Covered | S21, S24, S25 (R4); S28, S33 (R5 never-cited: in P5 v21 ref 34 had no citation in the mapping); S27, S74 (R6); S35 (R5b); S36 (R2b); S42, S50 (R7-b); S57, S59, S60, S61, S62, S64 (R3); S67, S77 (R8); S75 (R1b-b); S82 (R2b, R5b) | 21 |
| Not covered, was "uncertain" in v5 | S22, S32, S39, S51, S63, S66, S68 | 7 |
| Not covered, was "covered" in v5 | S26 (semantic collision: resolves to one reference); S56 (the clause's interval excludes 1); S38 (single value, not a range; line not linked); S41 (sentence not linked to the table); S40 (not linked, not the "in K <noun>" form; see o5) | 5 |
| Not covered (v5) | S11, S45, S47, S54, S65 | 5 |

- **Headline development coverage: 21 of 82 rows (25.6%).** The reasons for each row are in the run-150 note, section 3.
- One lesson for the narrative: **coverage judged from one-line descriptions overstated literal coverage.** All 7 uncertain rows failed when traced, and so did 5 of the 26 rows judged covered.

## 3. Changed definitions
### Shared: CI tuple (replaces v5's)
- **G1 numbers:**
  - A number is a whole token: an optional sign (-, −, +), digits with optional ",ddd" groups (no space), an optional decimal part (".07" allowed), and an optional leading "$" or trailing "%".
  - Not numbers:
    - tokens glued to letters, "/", "·", ":" or "-letter";
    - dates (YYYY-MM-DD, YYYY-MM);
    - anything inside citation brackets [..].
  - A "-" between two digits, or between "%" and a digit, separates two numbers.
  - In v1, G1 governs R1 and R1b. Other modules' number reading is open item o5.
- **G2 labels:** "95% CI", "95% CIs", "CI" and "95% confidence interval" are labels, never numbers.
- **G3 (estimate before):** the estimate is the last number before the "(". At most 6 words may come between them, all in one sentence and one table cell, with no ")" or ";" in between.
- **G4 (content):** after an optional G2 label, the parenthesis opens with the pair. The pair is two numbers joined by " to " or "-", or by ", ". It is then followed by ")", ";" or ",", or by one digit-free word and ")".
- **G5 (inner form, tried if G4 fails):** inside one parenthesis, its first number x, then ", ", an optional G2 label, then a pair joined by "-" or " to ", followed by ")", ";" or ",".
- A tuple keeps every printed sign.

### R1 CI-tuple twins (replaces v5's)
- Flag two tuples outside one table that share two of their three values and differ in the third.
- Values are compared **position by position** (estimate with estimate, first bound with first, second with second), as absolute values.
- Rows of one table are never compared with each other. The later occurrence is the primary line.

### R1b-b sign convention (the attribution sentence is new; the rest is as v5)
- A value of measure M (SMD, MD, DiD/DiDs, difference-in-difference(s), log ratio, risk difference; word-bounded, case-sensitive for abbreviations) is one of:
  - (i) the estimate or a bound of a CI tuple, when M is named in the tuple's clause (v4 clause), in the parent bullet's line (for a sub-bullet), or in the cell or its column header (for a table);
  - (ii) a number directly after M's token, optionally after "about".
- Negative means printed with a leading "-" or "−". Zero is ignored. All else is positive.
- A section needs a convention sentence when it holds both negative and positive values of one M. The pattern list is as in v5.
- R1b-b deletion sites are only the sole matching sentence of a section that needs one (v5 4.3).

### R5 citations (replaces v5's mapping and candidate text; the never-cited and acronym halves stand)
- **Mapping (cite side):** [n]; PMID; DOI; registry ID; the **first author's** full surname (+ initial when printed, + "et al." or a second author optional) directly before the reference's year; a named-trial acronym found in a reference title; and, only for an organisation author, its name or initials (ignoring "of") + year. An author-year directly followed by [n] is resolved by the [n].
- **Author-year candidate (flag side):** Surname [initials] [et al. | and/& Surname2 [initials]] [,] year.
  - The surname starts with a capital letter and has at least one lower-case letter; it is not a month name.
  - It is not directly preceded by another capitalised word or a digit.
  - A trailing "'s" is dropped.
  - The year is 19xx or 20xx, not followed by "-" plus a digit.
- Flag a candidate that maps to two references or to none.
- **Acronym:** "trial" and "study" are matched as whole words (not "trials" or "studies"). The stoplist frozen with the code includes RWE, RCT and every all-caps registry or database name.

## 4. Held-out sets: additions
- **4.1:** P5 v28 is made (run 150) with exactly the v5 closed edits C1 and U1-U4, and no trims. The literal re-check of its five touched lines is in v28's submitter notes. P4 v19 is unchanged. **The hash job waits for open item o5**, so that the base texts are hashed once.
- **4.3 eligible sites under v6:**
  - R1: 9 twin groups (P4 4, P5 5).
  - R1b: deletion sites P4 L85 and P5 L214, plus flip sites where -x lies outside the tuple's CI.
  - R5 never-cited removal: any reference with exactly one citation under the mapping.

## 6.1 Restated prediction (replaces v5's)
- On cut P4 v19 and cut P5 v28 (unmutated), the frozen code gives **0 scored flags from R1, R1b, R5, R2b, R5b and R4**, apart from C5's known residual R5 flags (P5 L248, L252).
  - These rest on literal hand passes: R1/R1b/R5 in run 150, R2b/R5b in runs 141-145, R4 in run 146.
- For R2, R3, R6, R7 and R8 the basis is still the run-147 operator check, not a full literal pass. R2 needs o5 first.

## 8. Order of work (replaces v5's steps 2-3)
- **o5 (before the hash job): a literal R2 pass.**
  - Settle the linking scope (sentence or line) and the column choice when a sentence names a word found in two column headers (P4 E.3: "Remission" and "HR" each appear in two headers).
  - Settle whether "in K of M <noun>" is a range-in-K form.
  - Settle the number reading (G1 or not) for R2, R4-a, R7-a and R8.
  - Any change goes into plan v7.
- Then:
  - the hash job (SHA-256, whole and cut, for P4 v19 and P5 v28);
  - code and unit tests on the seed set only;
  - freeze;
  - the mutation job;
  - the checker job.
- The rest is as v5.

## 9. Limits (additions)
- G1-G5, the R1b-b attribution and the R5 candidate grammar were written after reading the exact base-text lines they now pass. **Their fit to those texts is not evidence.**
- They narrow, as well as fix. Out of scope now:
  - tuples printed as "x%/yr (a to b)";
  - an interval with no estimate before it;
  - author-years after another capitalised word (e.g. "Haj Shehadeh 2025" is a citation but is never checked as a candidate);
  - sign problems in sections where no measure token sits near the values (e.g. P4 E.3e's VA/KPNC tables).
- Every hand pass so far found a defect in the rules it read. Expect o5 to find one too.
