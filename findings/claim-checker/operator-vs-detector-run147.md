# Operator-vs-detector check for the other 10 checker modules (run 147, 2026-10-21 ~12:45Z)

Status: development-set inspection only. No checker code, no held-out set, no hashes exist. Done by reading both cut texts in full (P5 v27 lines 1-367, P4 v18 lines 1-227) plus Grep for the trigger words, by one AI session (Claude, claude-opus-5-5) working in MV2's name. No human has checked it. This note does NOT edit plan v4 (20261021T101610Z-medicine/ahrq-checker-eval-prereg-v4.md). Everything in section 3 is a **proposed v5 amendment** (plan section 8 step 3), like the run-146 R4 note (20261021T111356Z-medicine/r4-literal-hand-pass.md).

Method: for each module, take its H-A operator as written in v4 section 4, apply it by hand to one or more real sites in a cut base text, and ask whether the module **as written in v4 section 3** would fire on the mutated line. Also count, where cheap, what the module would flag on the unmutated cut texts (P3 false-flag load).

## 1. Summary table

| Module | v4 operator detectable as written? | Unmutated false flags predicted under v4 (P5 + P4) | Main defect |
|---|---|---|---|
| R1 | No: "labelled quantity" can't be bound | n/a (not implementable) | label matching fails on the actual strings |
| R1b | Flip: **0 sites detectable**; delete: 1-2 of 3-5 | P5 flagged as a whole if matching is case-sensitive | both signs already present in both texts; the regex misses 2 of P5's 3 convention statements |
| R2 | Only where a predicate is computable (P4 E.3 only) | 2 (subset ranges P4 L45, L121) | row selection and predicates undefined; subset ranges |
| R2b | Yes (worked in runs 141-145) | 0 | flag line is the count line, not the deleted-ID line (scoring, section 2) |
| R3 | 2 of 3 literal sites | **9** (P5 L62, L86, L196, L211, L269; P4 L21, L54, L57, L58) | CI bound per sentence, not clause; the no-CI half fires on any "weaker/stronger/no effect" |
| R5 | Yes, but swamped | **dozens** (superlatives: 32 trigger hits on 29 P5 body lines, 29 on 24 P4 lines; all-caps tokens; 3 Rentsch hits in P4) | trigger lists far too wide; citation mapping undefined |
| R5b | Strip: missed whenever the item has no trial noun | 0 | item test is circular for the strip operator |
| R6 | Insert: yes. "planned ... before they ran": **0 sites** | 3 token hits (P5 L256 "API v2", P5 L259 "last run 2026-10-18", P4 L167 "API v2") + up to 5 "pre-registered" | H-A job gets no plan files, so every "pre-registered" fires |
| R7 | **No: 0 sites match its trigger patterns** | 0 | patterns written from older package wording; job files never named |
| R8 | Source drop: yes if the vocabulary is fixed; weight change: P5 yes, P4 no | 2 likely-real (P4) | no source vocabulary; no recompute of the dose |

Together with run 146 (R4 fails P2 by construction), **at least four modules (R1, R1b, R4, R7) can't pass P2 as written, and two more (R3, R5, R6) would sink P3 on the unmutated text alone.** Only R2b and R5b, the two modules already worked by hand in runs 141-145, are close to consistent. That confirms the run-145 limit note: modules not worked by hand have the same kind of defects.

## 2. A defect shared by every module: how a flag is matched to a mutation

v4 section 4 says the mutation job writes (module, line, original, mutated) and P3 scores "a flag on an unmutated line". It never says when a flag **counts as catching** a mutation. Many correct flags land on a different line from the mutation:
- R2b: deleting an ID on P5 L170 is flagged at the count sentence, L163.
- R5: removing a reference's only citation is flagged on the reference entry (e.g. P5 L358), not at the sentence edited.
- R1: a changed digit is flagged at the pair of places; the code may report either one.
- R1b and R4-b: a deleted convention sentence or anchor leaves a flag on the claim it covered.
- R8: dropping a source from E.6 is flagged where the source is used (Overview, references).
- R2b vs R5b: stripping an ID at P4 L160 is caught by R2b (count 3 vs 2), not by R5b (section 3, R5b).

Under v4 as written, each of these would score as **one missed mutation plus one false positive**. Proposed v5 rule (fixed before code):
1. Every flag reports a primary line and its **evidence lines** (the other occurrence, the count line, the reference entry, the list line).
2. A mutation is **caught** if any flag's primary or evidence lines include the mutated line. For a deletion, the "mutated line" is the line the text was deleted from.
3. P1 and P2 credit a catch by **any** module. The table also reports catches by the labelled module, so readers can see cross-module rescues.
4. A flag whose primary or evidence lines include a mutated line is not a P3 false positive.

## 3. Module by module (v4 text, the hand test, proposed v5)

### R1 same-quantity digits
- **v4:** "the same labelled quantity (estimate label + study) printed with different digits in two sections". Operator: change one digit of a repeated labelled number.
- **Hand test:** P5 pooled SMD "0.97 (0.36-1.57)" appears at L50 (label "Pooled oral, placebo-controlled RCTs") and L218 (table row "All three" under "Oral, placebo-controlled pool"). P4 "-4.18 (-5.38 to -2.97)" appears at L88 ("More than 7 a week") and L147 ("the heavier-drinker estimate"). In neither pair do the labels share a word that names the quantity, and the "study" of the E.1 table rows comes only from the heading ("Pan F et al."), not "Pan 2025". **No deterministic label rule finds these pairs, so a changed digit can't be detected.** "In two sections" is also undefined (is E.3a a different section from E.3?).
- **Proposed v5 (R1-a, CI tuples):** extract each (estimate, lower, upper) tuple. The estimate is the nearest number at most 6 words before "(" or "(95% CI". Compare absolute values (so "fell 11.4" matches "-11.4"). Flag when two tuples **anywhere outside one table** share 2 of the 3 values and differ in the third. Report both lines.
  - Rows of the same table are never compared with each other: P4 E.3's β-blocker and loop-diuretic intoxication rows (0.77 (0.64-0.92) vs 0.77 (0.64-0.93)) share 2 of 3 and would otherwise false-flag.
  - **Twin groups in the cut texts:** P5 4 (VAS -11.4 L49/L138; SMD 0.97 L50/L218; aHR 1.05 L51/L190/L195; RR 1.97 L55/L111). P4 3 (-0.76 L86/L147; -4.18 L88/L147; HR 1.24 L110/L122). That gives 15 occurrences to mutate (P5 9, P4 6), enough for 8.
  - **Predicted unmutated flags: 0** (by reading every CI tuple in both texts; code must confirm).
  - **Operator restricted to numbers inside a twin tuple.** Repeated plain counts ("107 people") are outside R1-a, reported as a coverage limit, not mutated.
  - The v4 "about X summary" half has no operator, so H-A never tests it. Say so.

### R1b sign convention
- **v4:** both signs present and no sentence matching `negative (values )?(=|favou?r|mean)`, `positive (values )?(=|favou?r|mean)` or "sign convention". Operators: flip one signed value, or delete "the package's sign-convention sentence".
- **Hand test, flip:**
  - Both texts already print both signs: P5 E.1a and E.5 have negative SMDs and positive SMDs (0.97, 0.43); P4 E.1 has DiDs -0.76 and +0.12, and E.3e mixes signs.
  - Both texts also have a convention sentence.
  - So flipping any value changes nothing R1b looks at: **0 flips detectable, in either package.**
- **Hand test, delete:** P5 states its conventions three times: L149 "Negative = less pain ...", L153 "positive for benefit", L214 "Here a positive SMD means less pain on metformin".
  - Only L149 can match the v4 regex, and only if matching is case-insensitive (v4 doesn't say). L153 ("positive for") and L214 ("positive SMD means") don't match.
  - Case-sensitive: unmutated P5 is flagged as a whole. Case-insensitive: deleting L214 (the convention for E.5, where the sign is the *opposite* of E.1a's) is missed, because L149 still matches.
  - P4: deleting L85 ("so negative favours spironolactone") is caught, since L145 ("Signs are as printed") doesn't match.
  - So 1-2 of 3-5 deletion sites are caught, and R1b fails P2 by construction under v4.
- **Proposed v5:**
  - **R1b-a (estimate inside its own CI):** flag a CI tuple whose signed estimate lies outside its signed interval. A flipped estimate is caught whenever -x lies outside the CI.
    - Flip sites are restricted to those tuples. Flips of values with no CI (E.1a's -0.39/-0.49/-0.47) or whose CI contains -x (P4 E.3e "-0.04 (-0.17 to 0.09)") are a stated coverage limit.
    - "0.00" is a no-op flip; the mutation job must reject it.
  - **R1b-b (convention per section):** case-insensitive patterns `(negative|positive)( \w+){0,2} (=|favou?rs?|means?|for benefit)` plus "sign convention" / "signs are as printed". Each ###-section that prints both signs of one measure needs a match in that section, or in its parent ## section before it.
    - Deleting L214 is then caught; deleting L149 is caught only if L153's clause is also gone (L153 sits in E.1a). That makes L149 an ineligible deletion site unless both go: write the rule as "a deletion site is a section's *only* matching sentence".
- **Unmutated predictions under v5:**
  - **C1 (candidate, P5 L49):** "VAS pain fell 11.4 mm more than with placebo (95% CI -20.1 to -2.6)". The unsigned estimate sits outside its own signed CI. Readable, but inconsistent as printed. Fix in P5 v28: "-11.4 mm (95% CI -20.1 to -2.6)" or "11.4 mm (95% CI 2.6 to 20.1)".
  - **C2 (debatable, P4 E.4):** L153-L154 print -0.34, -0.52, -0.20, -2.4 and +0.03/+0.00 with no convention sentence in E.4. The means "1.59 vs 2.18" make the direction clear, so it's likely a false flag under R1b-b.
  - Decide before code: add "(negative = fewer drinks among spironolactone users)" to P4 v19 E.4 (about +7 words), or pre-register it as an expected flag.
  - P4 E.3e is covered by "Signs are as printed" (L145) only because that phrase was added to the pattern after seeing it. **That is tuning on the development text, and the narrative must say so.**

### R2 range / N-of-M
- **v4:** every "N of M", "in all/every K" or numeric range attached to a table's rows is recomputed from the table's cells. Operators: N-of-M +/-1, or a range endpoint moved past the column min/max.
- **Hand test:**
  - **P5 L51 / L195** "five of six (estimates) against non-users ... CI below 1 in four" and **L196** "two of the four studies against non-use are null". Recomputing them needs semantic row selection: which E.3 rows are "against non-users", and which outcomes count as "joint replacement" (TKR or THR / TKA / TKR / joint arthroplasty / total knee replacement / joint replacement). No column holds that, so **these can't be recomputed, and a +/-1 change there is undetectable.** P5 has no computable R2 site.
  - **P4 L45** "CI below 1 in seven of nine" recomputes from the E.3 Intoxication column (upper bound < 1: 7 of 9 rows) if the sentence links to the table: it cites [8], as does the E.3 heading.
  - **P4 L123** "all nine HRs below 1": recomputable. "eight of nine ... about 20% lower" (L45): "about 20% lower" is not a computable predicate.
  - **Subset ranges false-flag:** L45 "HR 0.77-0.81" covers 8 of 9 rows (ARBs 0.97 excluded and named). L121 "9.9-10.4% in eight comparisons" excludes the 8.0% row. A full min/max recompute gives 0.77-0.97 and 8.0-10.4, so **2 false flags** on unmutated P4.
- **Proposed v5:**
  - **Ranges:** linked to one table column by a shared [n], or by a capitalised name in the table's heading plus a column-header keyword in the sentence. Flag an endpoint that equals no cell in that column (within printed rounding) or lies outside the column's min/max.
    - Subset ranges pass, and the v4 operator is caught. Unlinked ranges (E-values, L116; no E-value column) are skipped.
  - **N-of-M:** checked only with a fixed predicate list ("CI below/above 1" = upper < 1 / lower > 1; "below/above 1" or "all ... below 1" = estimate; "CI includes 1"), on M = the linked table's row count. Everything else is reported as out of scope.
  - **Operator sites = in-scope claims only.** Report the count of out-of-scope N-of-M claims in the base texts (P5: L51 x2, L195 x2, L196) as a coverage limit, so the restriction is visible rather than hidden.
  - In-scope sites: all in P4 (L45 x5: one N-of-M and four ranges; L121 x3; L123 x1): 9, enough for 8, all from one table. **Say plainly that R2's H-A result is a test on one table.**

### R2b (stated record count vs listed IDs)
- Consistent: deleting an in-scope ID (P5 L164-L173, P4 L160) or changing a gated count (P5 L163, L172, L173, ref 39; P4 L160 x2) is detected as written in v4 (runs 141-145).
- **Only problem:** the scoring rule of section 2. A deletion on L170 is flagged at L163.

### R3 directional wording vs CI
- **v4:** trigger words "within the same sentence or table row as a CI"; flag when the CI includes the null, "or when a comparative claim has no CI at all". Operator: "no clear difference" -> "no difference", "point estimates favour" -> "lower risk".
- **Literal operator sites:** 3 (shortfall). "no clear difference" at P5 L49 and P4 L87; "point estimates favour" at P5 L51.
  - **P5 L49:** the sentence's only CI is the 6-month one (-20.1 to -2.6, excluding 0). The 3-month CI is in the E.1 table. Under "same sentence", the mutated "no difference at 3 months" binds to the wrong CI, and **the mutation is missed**. (Under the no-CI half it isn't "no CI at all" either, because the sentence has a CI.)
  - **P4 L87:** "no difference, 0.12 (-0.56 to 0.81)" is caught.
  - **P5 L51:** "lower risk ... (knee replacement aHR 1.05, 0.94-1.18)" is caught, because that CI includes 1.
- **Unmutated false flags under v4 (no-CI half), by Grep:**
  - P5: L62 "not a weaker GLP-1 RA", L86 "weaker than its count", L196 "stronger for replacement", L211 table cell "no difference given", L269 "point estimates are stronger".
  - P4: L21, L54, L57, L58 "no effect" (animal findings as reported).
  - **9 flags, none a real problem.**
- **Proposed v5:**
  - Bind the CI per **clause** (split on top-level ";"), not per sentence.
  - Keep the no-CI rule only for "no difference|no benefit|no interaction", and never when followed by "given|reported|printed|stated".
  - "stronger/weaker/absent/no effect" fire only with a CI in the same clause that includes the null.
  - Add the operator "no clear benefit" -> "no benefit" (P5 L298), which gives 4 sites, all detectable.
  - **Predicted unmutated flags: 0.**
  - **Caveat:** the exclusions were written after seeing these 9 lines, which is tuning on development text. Say so.

### R5 citation lint
- **Hand test, operators:**
  - Removing a reference's only citation (e.g. P5 ref 41, cited only as "PMID 42875857" on L259) is caught, but on the reference line (section 2).
  - Making an author-year ambiguous ("Chen Z 2026" -> "Chen 2026", which matches refs 4 and 7) is caught.
  - Adding an unreferenced acronym is caught, but see below.
- **Hand test, unmutated text (the real problem):**
  - **Superlatives:** "only/first/largest/most common" occur 32 times on 29 P5 body lines and 29 times on 24 P4 body lines. Reading the first 11 matched P5 lines, 9 sit in a sentence with no author-year or [n] citation (L17, L37, L42, L46, L51, L80, L81, L84, L111). Of the first 10 P4 lines, 8 do (L9, L10, L17, L18, L36, L42, L81, L100). None of those 17 is a real unsupported uniqueness claim: "first approved", "Hypertension = I10 only", "only 200 mg/kg differed", summaries pointing to E.
  - **All-caps tokens:** dozens in each text with no reference (WOMAC, VAS, MCID, OARSI, AMPK, HKSJ, NHIRD, AUDIT-C, NHANES ...).
  - **Author-year matching two references:** P4 L130, L131 and L143 "Rentsch et al. 2026" match refs 20 and 28. The [20]/[28] that follows each one disambiguates, so these are 3 false flags.
  - **Never cited, if the mapping is author-year only:** P5 refs 29 (cited by PMID 40609734 only), 39 (by registry ID) and 41 (by PMID): 3 false flags.
  - **"Cited only by an organisation name":** P5 ref 33 ("ACR 2026 summary") is cited correctly. The plan doesn't say what problem this clause targets.
  - **Unreferenced author-years:** "Zhang C 2022" and "Shi S 2018" (P5 L248, L252) name trials that Jiang 2025 included and have no entry in our reference list. A strict flag here is arguable either way: candidate C5, decide before code.
- **Proposed v5:**
  - **Citation mapping:** [n]; author (+ initial when printed) + year; PMID; DOI; registry ID; and a trial acronym that appears in a reference title. An author-year directly followed by [n] is resolved by the [n].
  - **Superlatives:** only "the only|the first|the largest|the most common" followed within 4 words by a noun from {trial, study, studies, cohort, model, analysis, recommendation, drug}, in a sentence with no citation and no section cross-reference "(E.x)"/"(C)"/"(D)". A full hand count of what this still flags is needed before freeze: **open item o2**.
  - **Acronyms:** only tokens on a frozen named-trial list, or an all-caps token (3+ letters, not on a frozen stoplist) directly followed by "trial" or "study". The inserting operator draws from a list disjoint from the base texts.
  - Drop the organisation-name clause, or state its target.

### R5b registry ID on every enumerated trial
- **Hand test, strip operator:** an item counts only if it holds a trial noun or a registry ID, so **stripping the ID removes the item itself** unless it has a noun.
  - In P5 L173 ("**Other registered trials:**"), stripping the ID from NCT05638893, NCT06231758 or NCT06367283 leaves "(Aiad 2024; completed 2022; ...)" etc.: no noun, so not an item, so missed.
  - NCT06126029's piece contains "no results: a second unreported ... trial", where "no" comes before the noun. It becomes a "not item" once its ID is stripped, so it's missed too.
  - At P4 L160, stripping NCT05014087 is missed by R5b but caught by R2b (3 vs 2).
  - Only pieces like "a topical iontophoresis trial (NCT07395895)" survive the strip.
- **Proposed v5:**
  - In the (ii) form (a bold lead naming trials/studies/records), every top-level piece is an item.
  - "Not items" applies only to pieces that are wholly a negation ("no other trial", "none").
  - In the (i) form, a piece is an item if its unmutated form would be one. Equivalently: a piece that begins with "(" directly after a removed token is still an item.
  - Re-run the run-144 hand pass on L173 and L160 before freeze. Expected unmutated flags stay 0, since every piece there has an ID.

### R6 labels
- **Hand test:**
  - **Tokens:** `v\d+` matches "API v2" (P5 L256, P4 L167), and `run \d+` matches "last run 2026-10-18" (P5 L259). That's 3 false flags; these are product and search-date strings, not internal labels.
  - **Inserting a token:** caught.
  - **"planned in writing before they ran" -> "pre-registered":** the literal string occurs **nowhere** in either cut text (P4 L154 reads "planned in writing after the primary result and before the checks ran"). **0 operator sites.**
  - **"pre-registered":** the H-A checker job gets "only the mutated packages and the job files", with no plan files. So every "pre-registered" hits the "no plan file is given" branch: P5 L68 and L314 (proposals for future work), P4 L81 and L136, plus L150-L151 if matching is case-insensitive or stems "Pre-registration". **That's 4-6 false flags per run.**
- **Proposed v5:**
  - Tokens are word-bounded and not preceded by "API|release|version of|last" or followed by "-\d\d-\d\d" (a date).
  - R6-b runs only when `--plans` is given. H-A passes the public plan files the base texts cite (P4 ref 13 and ref 17 findings files). Sentences in section H, or with needed|propose|should|would|will, are proposals and are skipped.
  - Operator: "pre-registered" replaces the phrase "planned in writing after the primary result and before the checks ran" (P4 L154), and replaces "planned" in any sentence whose cited plan file's status note shows it was written after results. If fewer than 8 sites exist, record the shortfall.

### R7 claim vs job I/O
- **v4 triggers:** "all/every K estimates checked", "N meta-analyses checked", "every leave-one-out pool". **None of these strings occurs in either cut text.** The R7 seed rows came from older package wording that has since been fixed.
  - The real job-bound claims read differently: P4 L134 "**Checked:** 27 estimates ... with the open tool `rwe_recheck`", P4 L135 "All 28 are consistent", P4 L154 "70 of 70 leave-one-out refits", P5 L228 "four meta-analyses (Chenchula, Guo, Kao, Chen Z), seven RWE studies (...) ... are consistent (`rwe_recheck`)", and P5 L214 "reproduced in a sealed run".
  - "All 28" -> "All 29" and "naming a target absent from the job file" both produce text R7 doesn't read. **0 of 8 detectable under v4.**
  - v4 also never says which job files H-A passes to the checker.
- **Proposed v5:**
  - **R7-a (count vs its own enumeration, no job files needed):** a count phrase followed directly by a parenthesis, or by ":" in the same sentence, is compared with the number of names listed. Split on "," and " and ". A ";" ends the list, unless every ";"-piece starts with a name followed by a bare number, in which case the numbers are summed.
    - Checked by hand: P5 L228 4 = 4 and 7 = 7; P5 L234 "four ... : Chenchula (55 references), Chen Z (31), Kao (34) and Yao (38)" 4 = 4; P5 L250 "five ... (Pan, Alimoradi, Aiad, Mohammed, Varshini; Alimoradi also ...)" 5 = 5; P4 L134 9 + 9 + 4 + 5 = 27.
    - "All K" -> K+1 on a count with a list, and adding an absent name, are both caught.
    - **These three parsing rules were written after seeing these five sentences; they are tuned, and the narrative must say so.**
  - **R7-b (names vs job labels):** only with job files listed in an H-A input manifest (tool name -> file). Fix the manifest before code: the `rwe_recheck` outputs for P4 E.3c and P5 E.5a, and the E.5 pool job.
  - "All 28 are consistent" (27 by tool + 1 by hand, P4 L134-L135) stays **out of scope**: no deterministic rule can tell the by-hand item apart. It is not an operator site.

### R8 source list and dose basis
- **Hand test, dose:**
  - P5 L75 (mouse 200 mg/kg -> "about 1.1 g/day for 70 kg"; 200 x 3/37 x 70 = 1.14 g) and L82 (rat 200 mg/kg -> "about 2.3 g/day for 70 kg"; 200 x 6/37 x 70 = 2.27 g) both use 70 kg. Changing either to 60 kg gives different weights, which is caught.
  - P4 has one conversion (L65: 50 mg/kg x 3/37 = 4.05 mg/kg; "roughly 240 mg for a 60 kg adult" = 243 mg). Changing its weight leaves no second weight to compare, so it's **missed under v4**.
  - **Proposed:** recompute every conversion from the stated factor (mouse 3/37, rat 6/37) and weight; flag more than 10% off. That catches P4. Unmutated: all three within 3%.
- **Hand test, sources:** v4 names no source vocabulary and doesn't say whether "the package's own data-source list" is one sentence or all of E.6.
  - **Proposed:** a frozen vocabulary {PubMed, NCBI E-utilities, PMC, Europe PMC, Crossref, ClinicalTrials.gov, WHO ICTRP/ICTRP, ChiCTR, openFDA, DailyMed, Drugs@FDA, Orange Book}. The list is all of E.6. A source is "used" if named in the body or the references outside E.6.
  - Drop operator sites: sources named once in E.6 and at least once outside it.
  - Study data sources (TriNetX, NHANES, UK Biobank, Optum ...) are out of scope.
  - **Unmutated, under that rule:** P5 0 flags (its E.6 L256 names every vocabulary source it uses).
  - **P4: 2 flags, both likely real (candidate C3).** P4's E.6 never names **Drugs@FDA** (used L9, ref 10) or the **FDA Orange Book** (used L10, ref 10), although P5's E.6 lists both. This is a rule-(b)-type gap in judge-facing text: E.6 is where the challenge asks for the AI tool and how it was used.
  - **Fix in P4 v19:** add "Drugs@FDA, the FDA Orange Book" to L167's list (about +5 words).

## 4. Candidate rows found while designing (not natural-error rows; excluded from all headline counts)
- **C1** P5 L49: unsigned estimate "11.4" printed with a signed CI "(-20.1 to -2.6)". Fix in P5 v28.
- **C2** P4 E.4: both signs, no convention sentence. Debatable; fix (about +7 words) or pre-register as an expected flag.
- **C3** P4 E.6 L167: Drugs@FDA and the Orange Book were used but not listed. Fix in P4 v19.
- **C5** P5 L248/L252: "Zhang C 2022" and "Shi S 2018" have no reference entry (named secondhand from Jiang 2025's table). Decide: add a parenthetical "(as listed in Jiang 2025)" or pre-register.
- (C4 not used.) With run 146's U1-U4 (P5 L68, L86, L253, L312), that makes 8 candidate rows. Recommended treatment, same as run 146 option (A): fix C1, C3 and U1-U4 in the next package versions so the base texts have none, and log all of them as "found while designing R1b/R8/R4", outside the 79/82-row counts and outside any natural-error claim.

## 5. What this means for plan v5 (to be written once, as a new file)
1. Add the section 2 matching rule. Without it, P1-P3 can't be scored for R1, R1b, R2b, R4, R5 or R8.
2. Replace the R1, R1b, R2, R3, R5, R5b, R6, R7 and R8 definitions as in section 3, and R4 as in the run-146 note.
3. Every operator gets an **eligible-site rule written in terms of the detector's scope**, plus a stated count of out-of-scope claims of that kind in the base texts. This is the honest version of "only plant what the module claims to cover": the restriction is pre-registered and the uncovered remainder is reported, not hidden.
4. Restate every unmutated-flag prediction. Under the section 3 proposals with C1-C3 and U1-U4 fixed: **0 flags expected on both cut base texts**, except the R5 superlative remainder (open item o2) and C2/C5 if they are pre-registered instead of fixed.
5. Several v5 rules were written after seeing these exact lines: the R1b "signs are as printed" pattern, the R3 exclusions, the R7-a parsing rules and the R6 token exclusions. **Their development fit is not evidence**; only H-A (new text) and H-B (an unwritten package) test them. Add this to plan section 9.
6. Remaining before v5: open item o2 (a full hand count of the narrowed R5 superlative rule on both texts), and the literal R1 and R6 passes (playbook option o). After this note, those passes are mostly the re-checks of the v5 rules above.
