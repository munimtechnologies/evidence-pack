# Literal hand passes: R2 tables, R7-a counts, R8 doses and the number reading of R4-a (run 151, 2026-10-21 ~21:00Z)

Plan v6 open item o5, done before any checker code exists. Texts: cut package 4 v19 (lines 1-227) and cut package 5 v28 (lines 1-367). Each rule was applied by hand as written in plan v5 section 3 and v6 section 3. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has checked it. No parser was used, so "every" means every one found by reading and by pattern search (Grep) over both texts. CC BY 4.0.

## 1. R2 (tables), read literally
### 1.1 What v5/v6 leave undefined
- **"The table's heading line"** is not defined. It could be the nearest markdown heading or the table's own header row. Table cells carry no [n] in either text, so under the header-row reading the [n] half of the linking rule can never fire.
- **"A word from one column header"** has no stoplist and no case rule. P4's E.3 headers contain "vs", "n", "per", "CI" and "HR", and P5's E.5 header contains "Pain".
- **Linking scope** (sentence or line), **column choice** when a sentence word is in several headers, **what counts as a range**, **what a cell's value is**, and **which predicate an N-of-M takes** are all undefined.

### 1.2 Predicted false flags under v5/v6 readings (unmutated text)
| Line | Text | Why it flags |
|---|---|---|
| P4 L136 | "39 TriNetX papers (abstracts 2025-2026) failed the same check (Wilson 95% CI 0.5-6.9%)" | "TriNetX" (E.3 heading) plus "CI" (two E.3 headers) link the sentence. "2025-2026" and "0.5-6.9%" equal no cell |
| P5 L223 | "WOMAC pain SDs (0-20 scale) are 7-10% of the scale range, against 18.5-21% ..." | Case-insensitive, "pain" matches T3's "Pain estimate"; "The" (E.5 heading) links it. All four ranges equal no cell |
| P4 L45, sentence 1 | "1.24-2.07 times as likely ... (TriNetX [8]; 8.0-10.4% vs 4.4-7.4%)" | If one column is chosen by most shared words ("remission", "vs"), the counts column wins and 1.24-2.07 equals no cell there. If "remission" is matched case-sensitively, only "vs" matches, and again no candidate holds 1.24 and 2.07 |
| P5 L195 | "(Liu 2026, read from its abstract: knee replacement 1.05, 0.94-1.18)" | With case-insensitive "estimate" linking to the E.3 Estimate column, and a cell's value taken as its estimate, 0.94 equals no cell |

So depending on the reading, v6 gives 1 to 4 false R2 flags. Every one of them comes from the heading-word half of the linking rule, from an undefined range, or from single-column choice.

### 1.3 The rules adopted in plan v7, and the same pass under them
- **Linking:** [n] only. A table carries the [n] citations printed in its governing heading (the nearest markdown heading above it) or in any of its cells. A **line** of the cut text (one physical line: a bullet or a paragraph) outside any table is linked when it carries one of them, with lists and ranges expanded ([6-8] carries 8). The heading-word half of v5's rule is dropped.
- **Ranges:** a pair of G1 numbers joined by "-" or " to ". If either end has "%", both are percentages. Interval pairs are not ranges: the pair of a CI tuple (G3-G5), a pair directly after a G2 label, and a pair directly after "<number>, ".
- **Cell values:** for a cell holding a CI tuple, its estimate; otherwise every G1 number in the cell, each typed as a percentage or plain.
- **Candidate columns:** every column whose header shares a word with the claim's own sentence. Matching is case-insensitive and whole-word (v4 boundaries). G2 labels and "vs", "per", "of", "and", "or", "the", "n" are ignored.
- **Lenient check:** a claim is flagged only if it fails in **every** candidate column. A claim with no candidate column is out of scope and counted.
- **Ranges** pass when both endpoints equal values of the same type in one candidate column (within printed rounding).
- **N-of-M:** the predicate is the nearest fixed predicate (longest match, so "CI below 1" before "below 1") before "N of M" in the same clause, at most 8 words before it, with no other N-of-M in between. N-of-M without one is out of scope. M must equal the row count, and N is evaluated in each candidate column (columns holding CI tuples only, for CI predicates).
- **Range-in-K:** "in K <noun>" and "in K of M <noun>" (M is then checked against the row count) directly after a range.

**Linked lines:** P4 L45 (carries [8], the E.3 heading's citation) and P4 L131 (carries [6-8]). No P5 table carries an [n] (P5 cites by author-year), so **no P5 line is linked.**

| Claim (P4 L45) | Candidate columns | Result |
|---|---|---|
| "1.24-2.07" (sentence 1: "remission") | Remission counts; Remission HR | Remission HR estimates hold 1.24 (loop) and 2.07 (ARBs): pass |
| "8.0-10.4%" | same | Remission counts percentages hold 8.0 and 10.4: pass |
| "4.4-7.4%" | same | holds 4.4 and 7.4: pass |
| "0.77-0.81" (sentence 2: "intoxication", "HR"; "(HR 0.77-0.81; ...)" is not a CI tuple, since "HR" is not a G2 label) | Remission HR; Intoxication counts; Intoxication HR | Intoxication HR estimates hold 0.77 and 0.81: pass |
| "the 95% CI below 1 in seven of nine" | Remission HR (0 of 9); Intoxication HR (7 of 9) | pass in Intoxication HR |
| "about 20% lower in eight of nine comparisons" | no fixed predicate | out of scope, counted |

P4 L131 holds no range and no N-of-M. **R2: 0 flags on either text.**

**Eligible R2 sites under v7: 5, all on P4 L45.** They are the 4 ranges (move one endpoint past the column's values) and the one N-of-M (7 -> 6 or 8). Each mutation fails in every candidate column; for example 0.77-0.81 -> 0.76-0.81 matches no estimate in any candidate. Range-in-K has 0 sites. P5 has 0 sites. Shortfall: 3 of 8.

### 1.4 Seed rows
- **S40** (P4 v15 L45 "Alcohol intoxication diagnoses were about 20% less likely (HR 0.77-0.81 in seven of nine comparisons)"): the line carries [8]; the range-in-K form "in K of M <noun>" applies; the candidates hold 8 (Intoxication HR) and 0 (Remission HR, Intoxication counts) estimates in 0.77-0.81, never 7. **Covered under v7.**
- **S38** (P4 v15 L121, E.3a) and **S41** (L123, E.3a): the E.3a lines carry no [8]. **Still not covered.**
- **S39** (P4 v15 L45 "10.4% vs 4.4-7.4%"): a single value is not a range. **Still not covered.**

## 2. R7-a (count vs its own list), read literally
v5 says "a count phrase" and v4 defines one: a number (digits or one..twenty) followed within 3 words by records|trials|hits|studies|registrations. **The run-147 operator check read R7-a more loosely than that.** Its sites "27 estimates", "four meta-analyses" and "four paywalled meta-analyses" are not count phrases, and its P4 L134 sum (9 + 9 + 4 + 5 = 27) is not what the rule computes: the phrase directly before "(" there is "the three papers", and summing the ";" pieces gives 9 + 4 + 5 = 18 against 3.

Read with v4's count phrase, the v5 rule ("names listed, split on ',' and ' and '; a ';' ends the list unless ...") gives:
| Line | Count phrase and list | v5 literal | Problem |
|---|---|---|---|
| P4 L160 | "Three other hits have no drinking outcome: NCT05014087 (...); NCT00188045 (...); NCT00226109 (...)" | 1 name before the first ";" vs 3 | **false flag** |
| P5 L223 | "the other two trials (Pan's VAS pain at baseline; Alimoradi's KOOS pain, 0-100)" | 1 vs 2 | **false flag** |
| P5 L209 (table cell) | "10 studies: RCTs and cohorts" | 2 vs 10 | **false flag** if cells are read |
| P4 L129 | "6 hits (both 2026-10-15)" | 1 vs 6 | **false flag** if a non-name counts |
| P4 L172 | "0 records (2026-10-15)" | 1 vs 0 | false flag if a non-name counts |
| P5 L27, L86, L163 | ":" with nothing, or no names, after it | 0 vs 2 / 2 / 11 | false flag if an empty list is checked |

**Adopted in v7:** R7-a reads prose only (not tables, not the reference list).
- **Count phrase:** v4's, with "within 3 words" meaning at most 3 words in between. The number is a G1 integer with no sign, "%" or "$", or a number word (any case).
- **List:** the content of the parenthesis directly after the phrase, or the rest of the sentence after a later ":".
- **Pieces:** top-level, never inside deeper parentheses or quotation marks. A piece is a **name** if it starts with an upper-case letter or a registry ID. A list with no name is not checked.
- **Three readings, flagged only when the count matches none:**
  - (A) names before the first top-level ";", split on "," and " and ";
  - (B) the number of top-level ";" pieces that start with a name;
  - (C) the v5 sum, when every ";" piece starts with a name followed by a bare number.

Result: **0 flags. Sites: 5.** P4 L160 (3: reading B); P5 L172 (2: A), L223 (2: B), L228 "seven RWE studies" (7: A), L250 "five distinct oral randomised trials" (5: A). Each +1 mutation matches no reading. Seed row S66 ("four meta-analyses") stays not covered.

## 3. R8 dose, read literally
v5 says "recompute every animal-to-human conversion from the stated factor and body weight" but never says how a dose is paired with its species, its human dose and its weight. P4 v19 L65 now holds three conversions in one bullet, two of them sharing one human dose ("50 mg/kg in mice and 25 mg/kg in male rats, are each about 4 mg/kg (about 240 mg)"). P5 L100 names rats and then mice in one clause.

**Adopted in v7 (section 3 there):** lines containing "body-surface-area" or "body surface area" only; species, HED, human-total, pairing and weight rules.
- P4 L65: 50 mg/kg mouse -> 4.05 mg/kg -> 243 mg (printed 4 and 240); 25 mg/kg rat -> 4.05 -> 243 (4 and 240); 50 mg/kg rat -> 8.11 -> 486 (8 and 490). The weight is 60 kg, from the bold lead. All are within 2%.
- P5 L75: "to a human 1,000 mg/day" has no stated weight, so it is not checked. "about 1.1 g/day for 70 kg" is paired back to 200 mg/kg (mouse, from L74): 1,135 mg, 3.1% off.
- P5 L82: 200 mg/kg (rat, from L79), 2,270 mg against 2.3 g for 70 kg, 1.3% off.
- P5 L100: no human total (the "about 3 times" form), so nothing is checked.

**0 flags.** Changing any one weight is caught: P4 60 -> 70 kg gives 18% off; P5 L75 or L82 70 -> 60 kg gives 11.5% or 15% off, plus two different weights in one package.

**Seed row S77** (P5 v25 L75 "scaled by body surface area to a human 1,000 mg/day" against L82's 70 kg): the 1,000 mg/day states no weight, so no literal rule checks it, and checking unweighted doses at the package's other weight would also flag v28's correctly hedged L75. **Not covered.** v5 and v6 had counted it covered from its description.

## 4. R4-a number reading
The only R4-a spans in the cut texts are P4 L38 "more than 65 years on the US market" and P5 L172 "nearly 22 months after". Both use plain integer tokens, so adopting G1 changes nothing. "6-month-old" and "29-week" are glued tokens under G1 and were never spans.

## 5. Net effect
- Development coverage, literal: **21 of 82 (25.6%)**, unchanged in number. S40 is gained and S77 lost.
- Predicted unmutated flags for R2, R7-a and R8: **0**. Without the v7 rules there would be 1-4 (R2), 2-6 (R7-a) and an undefined number (R8).
- These rules were written after reading these exact lines. Their fit to these texts is not evidence.
- This note has the same limits as the run-150 note: the hand passes are by the model family that wrote the rules, and the frozen code's own run on the unmutated texts is the real test.
