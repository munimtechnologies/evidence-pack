# Literal hand passes: CI-tuple grammar (R1, R1b), R5 citation halves, and the 7 uncertain seed rows (run 150, 2026-10-21 ~19:00Z)

Plan v5 section 8 step 2, done before any checker code exists. Texts: cut package 4 v19 (lines 1-227) and cut package 5 v27 (lines 1-367; v28 changes only five lines, listed in plan v6 section 4.1). Every rule was applied as written in plan v5 section 3, by hand, by reading every parenthesis that holds a number in both texts. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has checked it. No word counter or parser was used, so "every" means every one found by reading. CC BY 4.0.

## 1. CI-tuple grammar (v5 section 3, "CI tuple"), read literally
v5: "an estimate followed within 6 words by "(" or "(95% CI", then two numbers separated by "to", "-" or "," before ")". The estimate is the nearest number before the "("."

v5 doesn't say what a number is (dates, bracketed citations, "1,000", "24-hour", "NDA021202"), whether the 6-word window may cross a ")" or a sentence end, whether other words may sit inside the parenthesis before the pair, or how R1 compares two tuples ("share 2 of their 3 values": by position or as a set).

### 1.1 Predicted false flags under v5 as written (unmutated text)
**Definite** (any reading of v5 gives the flag):

| Package, line | Text | Tuple v5 reads | Flag |
|---|---|---|---|
| P4 L45 | "about 20% lower in eight of nine comparisons (HR 0.77-0.81; 0.97 vs ARBs)" | (20 or "nine"; 0.77, 0.81) | R1b-a |
| P4 L75 | "USPI 7 (7.1-7.8: potassium-raising drugs, ...)" | (7; 7.1, 7.8) | R1b-a |
| P4 L136 | "39 TriNetX papers (abstracts 2025-2026)" | (39; 2025, 2026) | R1b-a |
| P4 L136 | "(abstracts 2025-2026) failed the same check (Wilson 95% CI 0.5-6.9%)" | (2026; 0.5, 6.9) | R1b-a |
| P4 L147 | "had CIs excluding 0 but stayed near the floor (sizes 0.42-0.52)" | (0; 0.42, 0.52) | R1b-a |
| P5 L46 | "at 6 months on every WOMAC scale (SMD about 0.4-0.5)" | (6; 0.4, 0.5) | R1b-a |
| P5 L195 | "... 0.94-1.18), and so is the active-comparator estimate (Optum: 0.80, 0.50-1.27)" | 1.18 with (0.80, 0.50), or with (0.50, 1.27) | R1b-a, or an R1 twin of the E.3 Baker row 0.80 (0.50-1.27) |
| P5 L353 (ref 36) | "12.1, 12.3 (incl. Tables 3-4)", twice | (12.3; 3, 4) | R1b-a |

That is 7 flagged lines (P4 L45, L75, L136, L147; P5 L46, L195, L353). After the plan's P3 dedupe they are 7 false positives on unmutated lines.

**Likely:** P4 L121 "The spread in HRs (1.24-2.07) comes from the comparator arms (4.4%-7.4%)" reads as (2.07; 4.4, 7.4), an R1b-a flag, if "4.4%-7.4%" counts as two numbers separated by "-".

**Depending on undefined tokenisation:**
- Dates read as numbers: P4 L129 "6 hits (both 2026-10-15)"; P4 L168 "(2026-10-20): every cited PubMed record (refs 1-9, ...)".
- Citation brackets read as numbers: P4 L64 "since 2018 come from three laboratories (Besheer's [5, 21], ...)".
- Thousands separators read as pairs: P5 L92 "24-hour exposure (AUC 26,811 vs ...)"; P5 L100 "1,500 mg/kg/day (each about 3 times ... 2,550 mg ...)".
- Digits inside identifiers: P4 ref 10 "(version 25, LAB-0231-18.0)"; "NDA012151 (products 001, 002)".
- Set-wise R1 comparison: P5 L28 "OR 0.60 (0.43-0.83)" vs P5 L153 "0.43 (95% CI 0.02-0.83)" share the values 0.43 and 0.83, but in different positions.

So v5's restated prediction ("0 scored flags apart from C5") is false for R1/R1b-a under v5's own grammar: at least 7 false flags.

### 1.2 The grammar proposed for v6, and the same pass under it
Plan v6 section 3 adopts these (G1-G5, R1 by position):
- **G1 numbers:**
  - A number is a whole token: an optional sign (-, −, +), digits with optional ",ddd" groups (no space), an optional decimal part (".07" allowed), and an optional leading "$" or trailing "%".
  - Not numbers:
    - tokens glued to letters, "/", "·", ":" or "-letter" (NDA021202, PMC12022862, IL-6, SGLT-2, 24-hour, 1.17-fold, 1:1, 35/54, 100/200/400, "-0.86%/yr");
    - dates (YYYY-MM-DD, YYYY-MM);
    - anything inside citation brackets [..].
  - A "-" between two digits, or between "%" and a digit, separates two numbers. It is not a sign.
- **G2 labels:** "95% CI", "95% CIs", "CI" and "95% confidence interval" are labels, never numbers.
- **G3 estimate before "(":** the estimate is the last number before the "(". At most 6 words may come between them, all in the same sentence and table cell, with no ")" or ";" in between.
- **G4 content:** after an optional G2 label, the parenthesis must open with the pair. The pair is two numbers joined by " to " or "-", or by ", " for the outside-estimate form only. It must then be followed by ")", ";" or ",", or by one digit-free word and ")" (for example "billion)").
- **G5 inner form:** inside one parenthesis, its first number x, then ", ", an optional G2 label, then a pair joined by "-" or " to ", followed by ")", ";" or ",". This covers "(-4.18, 95% CI -5.38 to -2.97)", "(-0.76, CI -1.43 to -0.11)", "(knee replacement aHR 1.05, 0.94-1.18)", "(Optum: 0.80, 0.50-1.27)" and "(OR 1.31, 1.20-1.43; Haj Shehadeh 2025)". G4 is tried first.
- **R1 by position:** estimate with estimate, first bound with first bound, second with second, as absolute values in printed order.

Re-reading every parenthesis under G1-G5:
- Every v5 false flag above disappears, for these reasons:
  - P4 L45, L136 (abstracts), L147, P5 L46 and ref 36: the content doesn't open with the pair.
  - P4 L75: the pair is followed by ":".
  - P4 L121, L136 (Wilson) and P5 L195: a ")" sits between the estimate and the "(".
  - The rest: G1 tokenisation.
- **R1b-a: 0 flags** on either text. Every tuple's signed estimate lies inside its signed interval, provided P5 C1 is fixed. On P5 v27, L49's "11.4 mm ... (95% CI -20.1 to -2.6)" is still a true R1b-a flag; the closed C1 edit removes it in v28.
- **R1: 0 flags.**
- **R1 twin groups (eligible R1 sites) rise from 5 to 9:**
  - P4: E.1 overall -0.76 (L86, L147); E.1 heavy -4.18 (L88, L147); loop diuretics 1.24 (table, L122); other K-sparing 1.82 (table, L124).
  - P5: VAS -11.4 (B L49 after C1, E.1 table); pool 0.97 (B L50, pool table); GI RR 1.97 (B L55, D L111); Liu knee replacement 1.05 (E.3 table, B L51); Baker joint replacement 0.80 (E.3 table, L195).
- **Tuple-like forms left out of scope** (counted, not checked):
  - P5 E.3 Wang "-0.86%/yr (-1.58 to -0.15)" (G1);
  - P5 L195 Liu "(Liu 2026, read from its abstract: knee replacement 1.05, 0.94-1.18)" (G5: the first number is 2026);
  - P4 L135 "(-1.43 to -0.11)" and "(about -1.62 to 0.10)" (no estimate);
  - P4 L136 "2.0% ... (Wilson 95% CI 0.5-6.9%)";
  - every HKSJ interval printed without parentheses.

### 1.3 R1b-b attribution (found during the same pass)
v5 says a section is checked when it "prints both negative and positive values of one effect measure", but it never says when a printed value belongs to a measure.
- Under the loosest reading (any signed number in a section that names the measure), P5 B is flagged. B names SMD and prints "-0.38" (the HKSJ bound) and, after C1, "-11.4 mm", and it has no convention sentence.
- Under the strictest reading (the measure named in the value's own clause), P4 E.1's values are unattributed, because "difference-in-differences" sits in the parent bullet. Deleting E.1's convention sentence then goes undetected.

Proposed for v6: a value of measure M (SMD, MD, DiD/DiDs, difference-in-difference(s), log ratio, risk difference) is either:
- (i) the estimate or a bound of a CI tuple, when M is named in the tuple's clause, in the parent bullet's line (for a sub-bullet), or in the cell or its column header (for a table); or
- (ii) a number directly after M's token, optionally after "about".

Negative means printed with a leading "-" or "−". Zero is ignored. Everything else is positive.

Under that reading:
- The sections that need a convention are P4 E.1 (L85 holds it), P5 E.1a (L149 and L153) and P5 E.5 (L214). **0 flags.**
- P5 B is not flagged: its SMD values are all positive, "-0.38" sits in its own ";" clause, and "-11.4 mm" has no measure token.
- P4 E.3e and E.4 hold no attributed values, so "Signs are as printed" (L145) and the C2 sentence (E.4) are no longer needed by any rule. They stay in the texts.
- Eligible R1b-b deletion sites: P4 L85 and P5 L214. In P5 E.1a, either one of its two convention sentences can be deleted with the other still matching, so E.1a is not a site.
- Seed row S75 (P5 v25) is still covered: v25 E.1a printed "SMD about -0.39" and "SMD 0.4", E.5 printed both signs, and neither section had a convention sentence.

## 2. R5's other halves (open item o3), read literally on both texts
**Never cited:** every reference carries a citation under the v5 mapping.
- P4: [1]-[29] are all bracket-cited.
- P5: refs 1-49 are all cited. Most are cited by first-author surname + year. Refs 21, 29, 30 and 41 are cited by PMID, 36 and 42 by [n], 39 by registry IDs, and 33 as "ACR 2026" (organisation initials).
- **0 flags.**

**Ambiguous or unmatched author-year:** v5 doesn't define which strings are author-year candidates, or which author position the surname must match.
- If any capitalised word before a year is a candidate, unmatched flags fall on:
  - P5: "OARSI 2019" (L36), "JAMA 2025" (L42, L116), "Initiative 2019" (L42), "Rheumatol 2025" (L158), "ACR's 2026" (L36);
  - month-years (P5 "September 2026", "June 2021", "August 2023", "December 2024", "July 2025"; P4 "April 2016", "March 2022", "January 2023", "May 2025").
- If a surname may match any author, "Kang 2026" (P5 E.3) matches refs 14 and 40 (Kang Y is ref 40's fifth author). "Ruan 2022" (P5 L170) matches refs 28 and 44 (Ruan G is ref 44's second author). Both are ambiguous flags.
- Proposed for v6:
  - **Candidate grammar:** Surname [initials] [et al. | and/& Surname2 [initials]] [,] year. The surname starts with a capital letter and has at least one lower-case letter (so all-caps tokens are not candidates), and is not a month name. It is not directly preceded by another capitalised word or a digit. A trailing "'s" is dropped. The year is 19xx or 20xx and is not followed by "-" plus a digit.
  - **Mapping:** by first author, with the full surname. Organisation initials still count as a citation (cite side).
- **Result under v6: only C5's pre-registered residual flags**, P5 L248 "Shi S 2018" and P5 L252 "Zhang C 2022" and "Shi S 2018". Neither text has any other.

**Acronym ("<ALL-CAPS> trial|study", no reference title holding it):** neither text has an all-caps token of 3+ letters directly followed by the word "trial" or "study". The only near miss is P5 L228 "RWE studies" ("studies" is not the listed word). **0 flags.**

## 3. Seed-row coverage, traced against the found-in package versions
This settles v5 section 2.1, which was judged from one-line descriptions.

| Row | Found-in text (version, line) | Literal result under v5 (and v6) |
|---|---|---|
| S22 | P4 v13 L75 "Decades of heart-failure use (RALES and later trials)" | **Not covered.** "RALES" is followed by "and", not "trial"/"study", and no reference existed to be never-cited |
| S32 | P5 v21 L36 "the 2019 ACR/Arthritis Foundation guideline"; E.6 L259 "the Kolasinski 2020 ... errata" | **Not covered.** E.6's "Kolasinski 2020" is a citation under the mapping, so ref 32 is not never-cited |
| S39 | P4 v15 L45 "(TriNetX [8]; 10.4% vs 4.4-7.4%)" | **Not covered.** A single value is not a range, and no fixed predicate applies |
| S51 | P5 v22 L227 "every printed estimate and 95% CI ... was run through `rwe_recheck`" | **Not covered.** R7-b checks names and counts, not "every" |
| S63 | P5 v23 L86 "absent in the one spontaneous-OA model" | **Not covered.** There is no CI in the clause, and the no-CI rule covers only "no differen*/benefit/interaction" |
| S66 | P5 v23 L227 "the four meta-analyses that print CIs, seven RWE studies (...)" | **Not covered.** "meta-analyses" is not a count-phrase noun, and no "(" or ":" follows |
| S68 | P5 v23 L222 "every leave-one-out pool is above Pan alone" | **Not covered.** No name or count is involved |

Re-checking the rows v5 marked covered against their found-in texts turned up five that the literal rules don't catch:
- **S26** (P5 v20 L256 "Zhang 2022 (comparator to liraglutide)"): under the mapping it resolves to exactly one reference (ref 15, Zhang Y 2022), so neither "two" nor "none" applies. The problem is a semantic collision. **Not covered.**
- **S56** (P4 v16 L45 "about 20% less likely (HR 0.77-0.81, with the 95% CI below 1 in seven of nine comparisons)"): the only interval in the clause is 0.77-0.81, which excludes 1. The problem (2 of 9 CIs cross 1) is not in the clause. **Not covered.**
- **S38** (P4 v15 L121 "10.4% in eight comparisons"): a single value, not a range, so range-in-K doesn't apply. The E.3a line also carries no [8], so it is not linked to the table. **Not covered.**
- **S41** (P4 v15 L123 "(seven of nine below 1, ...)"): the predicate fits, but the E.3a sentence carries no [8] and none of the heading's capitalised words, so under v5 it isn't linked to the table. **Not covered.**
- **S40** (P4 v15 L45 "(HR 0.77-0.81 in seven of nine comparisons)"): its sentence carries no [8] (the [8] is in the previous sentence on the same line), and "in seven of nine comparisons" is not the "in K <noun>" form. **Not covered under v5.** Two R2 amendments, linking by line and accepting "in K of M <noun>", would cover it. They are deferred to the literal R2 pass (plan v6, open item o5).

The rows still covered were re-read against the v6 changes in section 1 (S57 uses a standard tuple; S59-S62 and S64 have no CI in the clause; S75 is checked above). None changes.

**Development coverage, literal: 21 of 82 rows (25.6%)**, against v5's 26 to 33. All 7 "uncertain" rows resolved to not covered, and 5 of v5's 26 "covered" rows fail when read literally (19%). Description-level coverage judgments overstated literal coverage here. Development recall is still never used as evidence.

## 4. Limits
- These are hand passes by the model family that wrote the rules, so a missed parenthesis is possible. The code's own run on the unmutated texts is the real test, and any flag it gives that is not listed here is a P3 false positive, reported.
- G1-G5, the R1b-b attribution and the R5 candidate grammar were written after seeing these exact lines. Their fit to these texts is not evidence (plan section 9).
- R2's linking scope and column choice, and the number reading of R2, R4, R7 and R8, have not had a literal pass. They are open item o5.
