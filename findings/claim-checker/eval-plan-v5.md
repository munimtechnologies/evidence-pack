# Claim-provenance checker v1: evaluation plan (v5, run 149, 2026-10-21)

**Status note (rule i2): written 2026-10-21 ~17:30Z. At that time no checker code exists, the H-A base texts (package 4 v19, package 5 v28) do not exist yet, so no hashes, mutations or labels exist, and the H-B package has not been drafted.** This version is the first one committed publicly (evidence-pack `findings/claim-checker/`, together with v1-v4, which are kept unedited). It becomes a pre-registration at its commit time. Further amendments are allowed **only before code freeze**, each as a new dated, committed version. No change of any kind is allowed after H-A labels exist. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has reviewed it. Licence: CC BY 4.0.

Purpose (unchanged): the AHRQ Clinical Evidence Synthesis Transformation Challenge (Phase 1 due 2027-03-12) scores "quality, reproducibility, and provenance" (15 points), which its rules describe as including "error detection" and "independent reproduction". The proposed feature is a deterministic checker that flags silent claim-provenance problems in an evidence document. This plan fixes in advance how its first version will be judged.

Sections 1, 2 and 5 of v4 stand except where this file says otherwise. Sections 3, 4 and 6 are restated here in full, and they replace v4's.

## 0.5 v4 -> v5 amendments (runs 146-149, before any checker code exists)
Sources, all development-set inspections of the cut base texts (P5 v27 lines 1-367, P4 v18 lines 1-227): the R4 literal hand pass (run 146, `hand-pass-r4-run146.md`), the operator-vs-detector check of the other 10 modules (run 147, `operator-vs-detector-run147.md`), and the R5 superlative hand count (run 148, `r5-superlative-count-run148.md`). Run 149 (this file) added the seed-row coverage re-check in section 2.1.
1. **Flag-to-mutation matching rule** (new, section 6.0). Without it, v4 scored a correct flag that lands on an evidence line as one miss plus one false positive.
2. **Mutation layout and collision rule** (new, section 4.2). v4 never said whether 88 mutations share one copy per package or get one copy each. Both readings break scoring.
3. **Every operator now has an eligible-site rule written in terms of its detector's scope**, plus a reported count of out-of-scope claims of that kind in the base texts (section 4.3). Restricting the sites is pre-registered, and the uncovered remainder is reported, not hidden.
4. **Module definitions replaced** (section 3): R1 (CI-tuple twins), R1b (estimate inside its CI + convention per section), R2 (linked column, fixed predicates, range-in-K), R3 (clause binding, narrowed no-CI rule), R4 (R4-a elapsed span, R4-b status claim needing an anchor), R5 (citation mapping, acronym rule, corporate authors; **superlative sub-rule removed from scoring**), R5b (item rule), R6 (token exclusions, plan files required), R7 (R7-a count vs own enumeration, R7-b job manifest), R8 (dose recompute, source vocabulary).
5. **Base texts named:** P4 v19 and P5 v28, with a closed list of edits (section 4.1). The edits fix the candidate problems found while designing (C1, C2, C3, C6, U1-U4) so the base texts should be clean. C5 is pre-registered as known residual flags instead.
6. **Coverage restated** (section 2.1). The run-148 estimate "37 of 82" counted only the superlative drop. Re-checking every R row against the v5 definitions gives **26 covered, 7 uncertain, 5 not covered (of 38 R rows)**.
7. **Integrity log moved** to `findings/claim-checker/exposure-and-tuning-log.md` (section 7). The existing `findings/benchmark-exposure-and-tuning-log.md` covers the CLEF TAR work, and the drafting tools can't append to it without rewriting it.
8. **Tuning disclosure widened** (section 9). These v5 rules were written after seeing the exact base-text lines they now pass: the R1b "signs are as printed" pattern, the R2 range-in-K predicate, the R3 exclusions, the R5 corporate-author mapping, the R6 token exclusions and the R7-a parsing rules.
9. **Unchanged:** the seed (20261021), the planted-mutation target of 8 per module across 11 modules (88, less recorded shortfalls), the pass thresholds, the baselines, and the separation of the mutation job from the checker job.

## 2.1 Development coverage under v5 (run 149; by description, not re-traced)
Each of the 38 adjudicated Input-R rows (82-row set) was judged against the section 3 definitions **from its seed-set description**. The found-in package text was not re-read. "Uncertain" means the description doesn't say whether the text met the rule's scope (for example, whether a CI sat in the same clause).

| Status | Rows | n |
|---|---|---|
| Covered | S21, S24 (R4-a); S25 (R4-b); S26, S28 (R5); S27, S74 (R6; S74 needs the plan file in the manifest); S35 (R5b); S36 (R2b); S38, S40, S41 (R2); S42, S50 (R7-b); S56, S57, S59, S60, S61, S62, S64 (R3); S67, S77 (R8); S75 (R1b-b); S82 (R2b, R5b); S33 (R5 author-year matching none: "OARSI" is neither an author surname of ref 34 nor, under 3.R5, a corporate author) | 26 |
| Uncertain | S22 (RALES: covered only if written as "RALES trial/study" or listed); S32 (depends on how the guideline name was printed); S39 (column max paired with a comparator range: no v5 predicate obviously applies); S51 ("every printed estimate": R7-b only if the estimates are named in job labels); S63 ("absent": needs a CI in the same clause); S66 (R7-a only if the meta-analyses were enumerated); S68 (R7-b only if the pool labels are in the manifest) | 7 |
| Not covered | S11 (superlative rule removed, item 4); S45 ("about X" summaries: v4's R1 half had no bindable set or operator and is dropped); S47 ("lower risk in five of six" with no CI in the clause: v5 R3 keeps the no-CI rule only for "no differen*/no benefit/no interaction"); S54 (an unlabelled value beside others: not a CI-tuple twin); S65 ("effects look stronger" with no CI: narrowed out of R3 to avoid 5 false flags on the base texts) | 5 |

- **Headline development coverage, v5: 26 to 33 of 82 rows (32% to 40%)**, against 38 of 82 under v4. The narrowing that removes false flags from the base texts costs at least 5 true development rows. That trade-off is stated here rather than tuned away.
- Before code freeze, the 7 uncertain rows are traced against their found-in package versions (all on disk) and the result goes into the next plan version. The S and X rows (44) stay out of v1's scope, as in v4.
- Development recall is still never used as evidence (v4 section 2).

## 3. Checker v1 (fixed now so the evaluation can't be tailored)
- One command: `claimcheck <package.md> [--jobs <manifest.json>] [--plans <dir>] --deadline 2027-03-26 --json out.json`. Python 3.11, stdlib only, deterministic, no network. Apache-2.0.
- Output: one flag per finding, with module, sub-rule, **primary line**, **evidence lines** (every other line the finding relies on), the text span, a one-line reason and the evidence used.
- **Shared definitions:** v4's registry ID patterns, registry names, name matching, sentence and count-phrase definitions stand. Added:
  - **Text read:** the cut text (section 4.1) with markdown emphasis removed. Quotation marks: text inside "..." is read for citations and IDs only, never for triggers.
  - **Clause:** v4's definition (innermost enclosing parenthesis pair, split on ";" at its depth).
  - **Word boundary:** as in v4's name matching ("-" and "_" are not boundaries, so "pre-registered", "self-reported" and "cannot" don't match "registered", "reported" and "not").
  - **CI tuple:** an estimate followed within 6 words by "(" or "(95% CI", then two numbers separated by "to", "-" or "," before ")". The estimate is the nearest number before the "(". Values keep their printed sign.
  - **Linked table:** a pipe table is linked to a sentence when both carry the same [n], or when the sentence names a capitalised word from the table's heading line and a word from one column header.
  - **Citation (R5):** [n]; author surname (+ initial when printed) + year; PMID; DOI; registry ID; a named-trial acronym (3.R5) found in a reference title; and, **only for a reference whose author field is an organisation**, the organisation's name or initials (ignoring "of") + year. An author-year directly followed by [n] is resolved by the [n].

### Modules
- **R1 CI-tuple twins.** Flag two CI tuples, anywhere outside one table, that share 2 of their 3 values (compared as absolute values) and differ in the third. Rows of the same table are never compared with each other. The primary line is the later occurrence, and the earlier is an evidence line. Out of scope: repeated plain counts and "about X" summaries.
- **R1b sign.**
  - *R1b-a:* flag a CI tuple whose signed estimate lies outside its own signed interval.
  - *R1b-b:* flag each ### section (or ## section without ### children) that prints both negative and positive values of one effect measure (SMD, MD, DiD, log ratio, risk difference) when neither it nor its parent ## section before it holds a convention sentence. A convention sentence matches, case-insensitively, `(negative|positive)( \w+){0,2} (=|favou?rs?|means?|for benefit)`, "sign convention" or "signs are as printed".
- **R2 tables.**
  - *Ranges* in a sentence linked to a table: flag an endpoint that equals no cell of the linked column (within printed rounding) or lies outside the column's min/max. Subset ranges pass.
  - *N-of-M,* checked only with these predicates on M = the linked table's row count: "CI below 1" (upper < 1), "CI above 1" (lower > 1), "CI includes 1", "below 1" / "above 1" / "all ... below 1" (estimate).
  - *Range-in-K:* a range followed by "in K <noun>" is checked against the number of linked-column cells inside the range.
  - Every other N-of-M is out of scope and only counted.
- **R2b:** v4's definition, unchanged (gate, line scope, clause-level registry choice, flag rule). The primary line is the count line, and the evidence lines are the scope lines.
- **R3 directional wording.** The CI is bound per clause.
  - Flag "no differen\w*", "no benefit", "no interaction", "lower/higher risk", "less/more likely", "stronger", "weaker", "absent" or "no effect" when a CI in the same clause includes the null (1 for ratios, 0 for differences).
  - Also flag "no differen\w*", "no benefit" or "no interaction" in a clause with no CI, unless directly followed by "given", "reported", "printed" or "stated".
- **R4 dates** (the run-146 note's definition, adopted as written there in section 3):
  - *Anchor:* a date (YYYY-MM-DD, YYYY-MM or "D Month YYYY") directly preceded by "as of", "as read", "rechecked", "checked", "searched", "accessed", "unchanged on" or "re-read ... on" (case-insensitive). Its scope is the sentence, plus the bold lead of its own bullet or paragraph, plus the governing block lead (the nearest preceding non-bullet bold-lead paragraph that ends with ":", for bullets directly under it).
  - *R4-a elapsed span:* "N days|weeks|months|years" (digits or one..twenty; optional about, nearly, almost, over, more than), followed immediately by after, since, ago or "on the (US )?market". The start date is bound by event word (completion -> completion; market -> approved|approval|marketed), searched in the sentence, then the bullet block, then the Overview; the first level with exactly one candidate wins, else the span is unbound (info only). The end date is a same-sentence anchor, else the deadline. Flag when the length (calendar months + days/30.44) breaks the qualifier: nearly/almost N needs N-1 <= x < N; about N needs |x-N| <= max(1, 0.1N); over/more than N needs x > N; bare N needs |x-N| < 1.
  - *R4-b status claim:* in one clause, a limiter (no, none, not, not yet, only, exactly <number>, almost no, currently, still) before registered, posted, published, recruiting, exist or exists, or the word "unreported". Flag when no anchor is in scope.
- **R5 citations.**
  - *Never cited:* flag a reference with no citation under the mapping. The primary line is the reference entry.
  - *Ambiguous or unmatched author-year:* flag an author-year (in prose or a table cell) that maps to two references, or to none.
  - *Acronym:* an all-caps token (3+ letters, not on the stoplist frozen in the code before freeze, which must not be edited after) directly followed by "trial" or "study", with no reference whose title contains it.
  - The **superlative sub-rule is removed from scoring.** It may print as unscored "info" output.
- **R5b registry ID on every enumerated trial.** v4's *where* and *flag* rules stand. Items:
  - In form (ii), a bold lead naming trials, studies or records: every top-level piece is an item.
  - In form (i): v4's item rule, except that "not items" are only pieces that are wholly a negation ("no other trial", "none").
  - When a piece's item status depends on a registry ID, the status is judged as if the ID were present. This keeps the strip operator detectable.
- **R6 labels.**
  - *R6-a:* word-bounded `version \d+`, `v\d+`, `run \d+`, `gate \d+`, outside the reference list, not preceded by API, release, "version of" or last, and not followed by `-\d\d-\d\d`.
  - *R6-b:* runs only when `--plans` is given. It flags "pre-registered" when the cited plan file's status note says it was written after results, or when the sentence cites no plan file. Sentences in section H, or containing needed, propose, should, would or will, are skipped.
- **R7 job-bound claims.**
  - *R7-a:* a count phrase followed directly by "(" or by ":" in the same sentence is compared with the number of names listed (split on "," and " and "). A ";" ends the list, unless every ";" piece starts with a name followed by a bare number, in which case the numbers are summed.
  - *R7-b:* only with `--jobs`, a manifest mapping a tool name in the text to a job input/output file. Flag a name in a sentence that names the tool when that name is absent from the file's labels, or a stated count of checked items that differs from the file's count.
- **R8.**
  - *Dose:* recompute every animal-to-human conversion from the stated factor (mouse 3/37, rat 6/37) and body weight. Flag one that is more than 10% off, or two that state different body weights.
  - *Sources:* frozen vocabulary {PubMed, NCBI E-utilities, PMC, Europe PMC, Crossref, ClinicalTrials.gov, WHO ICTRP / ICTRP, ChiCTR, openFDA, DailyMed, Drugs@FDA, Orange Book}. Flag a vocabulary source named in the body or references but missing from section E.6. Study data sources are out of scope.

## 4. Held-out evaluation sets
### 4.1 H-A base texts (closed list of edits)
- **P4 v19 = P4 v18 plus exactly these edits:** (1) the run-137 i4 dose-translation text in section C (20261021T012336Z-medicine/package4-rule-i4-i5-check.md); (2) C3: add "Drugs@FDA, the FDA Orange Book" to E.6's source list; (3) C6: "the first adherence estimate for spironolactone in people with AUD"; (4) C2: add "(negative = fewer drinks among spironolactone users)" to E.4; (5) length trims that delete whole sentences or clauses only and add no claims, each listed in the version's notes.
- **P5 v28 = P5 v27 plus exactly these edits:** (1) C1: "-11.4 mm (95% CI -20.1 to -2.6)"; (2) U1-U4: an "as of 2026-10-20" anchor on the four unanchored status claims (B "the unreported structural trial", C "Almost no null result ... has been published", E.5b "we found no published comparison", H "Publish the unreported structural trial"); (3) length trims as above.
- **C5 is not edited.** "Zhang C 2022" and "Shi S 2018" are reports named secondhand from Jiang 2025's table, not read by us, and adding reference entries would claim more than was read. They are **pre-registered known residual R5 flags** (P5 v27 lines 248 and 252, located in v28 by their text), reported, and excluded from P3 in both directions.
- Any other change to either text means a new plan version before the hash job.
- **Cut rule:** v4's, unchanged. A job records each base file's SHA-256, whole and cut, before the mutation job. A literal re-check of every edited line under section 3 is done, and logged, before the hash job.

### 4.2 Mutation layout (new)
- Each package gets as many copies as its largest per-module mutation count (normally 4). Copy j holds the j-th mutation of every module in that package, so each copy has at most one mutation per module.
- **Collision rule:** within a copy, no mutated line may be a primary or expected evidence line of another mutation (same twin group, same gated count or ID block, same linked table column, same reference entry, same sentence). The job redraws on a collision (seed 20261021, recorded) and logs it.
- The job writes the copies and `labels.json` (copy, module, operator, line, expected evidence lines, original, mutated) and prints the labels' SHA-256. The checker job never sees `labels.json`.

### 4.3 Operators and eligible sites
Operators are v4's, plus the additions below. **A site is eligible only inside its detector's scope as defined in section 3.** The mutation job also counts, and reports, the out-of-scope claims of that kind in each base text.
- R1: change one digit of one member of a CI-tuple twin group.
- R1b: flip the sign of a CI-tuple estimate where -x lies outside the CI (never 0.00); or delete a section's *only* convention sentence.
- R2: N-of-M +/-1 under a fixed predicate; move a linked range endpoint past the column min/max; change a range-in-K count by +/-1.
- R2b: as v4.
- R3: "no clear difference" -> "no difference", "point estimates favour" -> "lower risk", "no clear benefit" -> "no benefit"; only where a CI including the null sits in the same clause, or where no CI does (the "no differen*/benefit" forms).
- R4: delete an anchor whose deletion leaves an R4-b claim or an R4-a span with no anchor in scope; change a bound R4-a duration so it breaks its qualifier.
- R5: remove a reference's only citation; insert "the <ACRONYM> trial" with an acronym from a list frozen with the code and disjoint from both base texts; make a mapped author-year ambiguous.
- R5b: strip the registry ID from one item (v4).
- R6: insert a token; replace "planned in writing after the primary result and before the checks ran" with "pre-registered".
- R7: change an R7-a count by +1; add a name absent from the job file to an R7-b sentence.
- R8: change one conversion's body weight; delete a vocabulary source from E.6 that is also named outside E.6.
- If a module has fewer than 8 eligible sites, the shortfall is recorded and the module is scored on what exists (as in v4). **Expected shortfalls from the hand passes: R3 4 sites; R4 7 sites; R6 (pre-registered operator) 1 site plus token insertions; R2: all in-scope sites are in one P4 table, so R2's H-A result is a test on one table.**

### 4.4 H-B and H-C
As in v4 (hand audit committed before the checker runs; adjudication; Chapman capture-recapture as a lower bound).

## 6. Outcomes and pass rules
### 6.0 Matching (new)
- A mutation is **caught** if any flag's primary or evidence lines include the mutated line. For a deletion, the mutated line is the line the text was deleted from.
- P1 and P2 credit a catch by any module, and the results also report catches by the labelled module.
- A flag whose primary or evidence lines include a mutated line *in the same copy* is not a P3 false positive. A flag on a line mutated only in another copy counts as a flag on an unmutated line.
- **P3 dedupe:** each flagged unmutated (module, line) counts once per package, however many copies flag it.

### 6.1 Pass rules (thresholds unchanged from v4)
1. **P1: H-A recall >= 0.80** of the mutations actually planted (N recorded by the job; 88 if no shortfall), with the Wilson 95% CI.
2. **P2: every module catches >= 5/8 of what was planted in it, rounded up** (5 of 8; 5 of 7; 3 of 4).
3. **P3: H-A precision >= 0.50,** with the 6.0 dedupe; C5's known residual flags are excluded.
4. **P4: beats the keyword baseline** (v4 section 5): precision at least twice the baseline's, recall no more than 0.10 below it.
5. **P5 (H-B): recall of the hand audit's R-type problems >= 0.60, and at most 1 false flag per page.**
6. **P6: under 60 s per package on 1 CPU.**
- **Restated prediction, before code:** on the cut base texts P4 v19 and P5 v28 (unmutated), the frozen code gives **0 scored flags**, apart from C5's known residual flags (2 lines). That rests on hand passes of R2b, R5b, R4, R5 (superlatives) and the run-147 checks of the rest. R5's never-cited, ambiguous-author-year and acronym halves have not had a full literal pass yet. If that pass finds a predicted flag before freeze, it goes into a new plan version. If code finds one after H-A labels exist, it is a P3 false positive and is reported.
- Results are reported pass/fail per rule with every number, whatever they show. Development coverage is reported under v4 and v5 side by side.

## 7. Integrity log
`findings/claim-checker/exposure-and-tuning-log.md`, append-only. Entries: this commit; each further plan version; the base-text hashes (whole and cut); code freeze (commit hash); the mutation job (seed, labels hash, collisions, shortfalls); the checker job; the H-B audit commit; the H-B checker job; the adjudication.

## 8. Order of work (from this commit)
1. Commit this plan with v1-v4, seed sets v1 and v2, the second labelling, the adjudication and the five hand-pass notes (this commit).
2. Trace the 7 uncertain rows (2.1); do the literal pass of R5's other halves. If either changes anything, write a new plan version.
3. Make P4 v19 and P5 v28 (4.1 only); re-check the edited lines literally; run a job that records SHA-256, whole and cut.
4. Write the checker and its unit tests on the seed set only; commit; freeze.
5. Run the mutation job, then the checker job (network false, 1 CPU, 1 GB).
6. Score H-A under section 6 and commit the results file.
7. Run H-B when the next package is drafted.

## 9. Limits (additions to v4's)
- The v5 rules listed in 0.5 item 8 were written after seeing the base-text lines they now pass. Their fit to those texts is not evidence. Only H-A (new text) and H-B (an unwritten package) test them.
- Coverage in 2.1 was judged from one-line descriptions by the model family that wrote the rules. It is the honest range, not a measurement.
- The v5 narrowing trades recall for precision on purpose. At least 5 development rows that v4 covered are no longer covered, and the narrative must say so.
- Everything here is by one model family. No human has checked a rule, a row or a prediction.
