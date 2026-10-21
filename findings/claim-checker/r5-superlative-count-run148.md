# R5 superlative rule: full hand count on both cut base texts (open item o2; run 148, 2026-10-21 ~14:45Z)

Status: development-set inspection only. No checker code, no held-out set, no hashes exist. One AI session (Claude, claude-opus-5-5) did this in MV2's name, using Grep (case-insensitive `\bthe (only|first|largest|most common)\b`) plus a reading of every matched line in context. No human has checked it. Like the run-146 R4 note and the run-147 operator note (20261021T123413Z-medicine/operator-vs-detector-check.md), this **does not edit plan v4** (20261021T101610Z-medicine/ahrq-checker-eval-prereg-v4.md). Section 4 holds proposed v5 amendments.

Inputs:
- **P5 v27:** 20261021T091352Z-medicine/regen-package-5-metformin-knee-oa-v27.md, cut at line 367. The `---` on line 368 sits above `## Notes for the submitter` on line 370.
- **P4 v18:** 20261020T222759Z-medicine/regen-package-4-spironolactone-aud-v18.md, cut at line 227. The `---` is on line 228 and "Submitter notes" on line 229.

The cuts match plan v4 section 4. Grep hits after the cut (P5 lines 385, 391 and 392; P4 line 233) were dropped.

## 1. The rule tested (run-147 proposal, operator note section 3, R5)
The rule flags "the only|the first|the largest|the most common" when it is followed within 4 words by a noun from {trial, study, studies, cohort, model, analysis, recommendation, drug}, in a sentence with **no citation** and no section cross-reference "(E.x)"/"(C)"/"(D)".
- A citation is any of: [n]; author (with initial when printed) + year; PMID; DOI; registry ID; or a trial acronym that appears in a reference title.
- **Readings I fixed for the count:**
  - Sentences split at ". " before a capital, never inside parentheses.
  - Tokens are whitespace-separated, so a hyphenated compound counts as one token.
  - "Within 4 words" means one of the next 4 tokens after the trigger phrase.
- v5 must state all three readings explicitly.

## 2. Every hit

### P5 v27 (cut): 12 hits on 12 lines
| Line | Text near the trigger | List noun within 4? | Citation / cross-ref in sentence | Flag? | Judgement |
|---|---|---|---|---|---|
| 18 | "the only adequately reported randomized trial (Pan 2025)" | trial | Pan 2025 | no | - |
| 37 | "The only recommendation the 2026 summary marks as new ... (ACR 2026 summary, p. 2)" | recommendation | none under the mapping ("ACR 2026" is not author-year, [n], PMID, DOI or ID) | **FLAG** | **false**: the claim is quoted from ref 33, a corporate-author document cited by its organisation name |
| 42 | "the largest and best reported in JAMA 2025" | no | - | no | - |
| 46 | "including the largest diabetes cohort (362,091 people)" | cohort | (C), (E.3) | no | - |
| 51 | "but not in the largest (knee replacement aHR 1.05, ..." | no | - | no | - |
| 84 | "but it is the only spontaneous-OA model we found." | model | none in this sentence (Minton 2021 is in the bullet's first sentence) | **FLAG** | **false**: scoped by "we found", backed by the search stated on L83 |
| 165 | "The only kidney criterion is ..." | no | - | no | - |
| 172 | "On ClinicalTrials.gov, the only placebo-controlled trial of metformin alone ..." | trial | none in this sentence (the subject's ID NCT05034029 is on the parent bullet, L170) | **FLAG** | **false**: backed by the full 11-record enumeration, L163-L173 |
| 195 | "The largest diabetes cohort is null (Liu 2026, ..." | cohort | Liu 2026 | no | - |
| 196 | "and the largest shows a 5% reduction" | no | - | no | - |
| 284 | "the formulation of the only adequately reported trial, and the structural trial NCT05034029 ..." | trial | (D), NCT05034029 | no | - (exempted by citations that belong to other clauses; see 3c) |
| 313 | "in the largest non-user cohort (Liu 2026)" | cohort | Liu 2026 | no | - |

**P5 totals:** 12 hits; 8 with a list noun; 5 exempted; **3 flags, 0 true.**

### P4 v18 (cut): 11 hits on 10 lines
| Line | Text near the trigger | List noun within 4? | Citation / cross-ref | Flag? | Judgement |
|---|---|---|---|---|---|
| 17 | "the label's Highlights call the most common adverse reaction" | no ("adverse reaction" is not on the list) | - | no | - |
| 18 | "The first target is heavier drinkers" | no | - | no | - |
| 36 | "the only registered studies of spironolactone as a treatment for AUD ... (E.5)" | studies | (E.5) | no | - |
| 81 | "The only analysis from outside that collaboration ... (E.4)" | analysis | (E.4) | no | - |
| 122 | "the only comparison where the HR sits ..." | no ("comparison" is not on the list) | - | no | - |
| 140 | "the first prescription of the assigned class" | no | - | no | - |
| 145 | "the first-named group's change" | no | - | no | - |
| 147 | "the largest VA heavy-drinker size" | no | - | no | - |
| 159a | "(spironolactone the only drug listed)" | drug | NCT06004830 (same sentence) | no | - |
| 159b | "It is the first registered study with a drinking outcome on spironolactone" | study | none in this sentence | **FLAG** | **false**: backed by the E.5 search (L160-L161) and the heading's [12] |
| 184 | "would give the first adherence estimate in people with AUD" | no | (E.5) | no | out of scope; see C6 |

**P4 totals:** 11 hits; 4 with a list noun; 3 exempted; **1 flag, 0 true.**

**Both texts:** 23 trigger hits; 12 pass the noun filter; **4 predicted unmutated flags (P5 L37, L84, L172; P4 L159b), all false.** The run-147 note had estimated "dozens" under v4. Narrowing removes most of them but not all.

## 3. What the count shows

### 3a. The narrowed rule misses its only development row (S11)
Seed row S11 (run 119, P5 section F) reads, in P5 v13/v14 line 290:

> "NSAIDs are not in USPI section 7, but they are the most common co-medication in knee OA and can lower eGFR, which raises metformin exposure (D)."

The v5 proposal misses this row **twice over**:
- "co-medication" is not on the noun list.
- The sentence carries "(D)", which supports the eGFR clause, not the superlative.

So the development recall of the superlative rule is **0 of 1**. The run-147 proposal didn't check its own seed row.

### 3b. No variant both catches S11 and stays clean (counted by hand)

| Variant | S11 | Predicted unmutated flags (P5 + P4) | True |
|---|---|---|---|
| A. As proposed (sentence scope) | missed | 3 + 1 = **4** | 0 |
| B. A + {medication, co-medication} + bullet scope (any citation in the whole list item) + corporate-author mapping (ref 33 "American College of Rheumatology" <-> "ACR 2026") | missed: the bullet has (D) and (G) | **0** | - |
| C. A + {medication, co-medication} + comma-segment scope (the citation must sit in the trigger's own comma/semicolon segment, ignoring commas inside parentheses) | **caught** | P5 L37, L46, L84, L172, L284 + P4 L159a, L159b = **7** | 0 |

Which claim a citation supports is a semantic question. A deterministic scope rule either exempts S11 along with the clean superlatives (B) or flags the clean ones along with S11 (C). Variants B and C were both shaped on these exact lines, so neither fit would be evidence.

### 3c. The superlative rule has no planted test
H-A's R5 operators (v4 section 4) are:
- remove a reference's only citation;
- add an unreferenced acronym;
- make an author-year ambiguous.

**None plants a superlative.** In H-A the superlative sub-rule can only add false positives, which count against P3 and P4. Its only real test would be H-B.

### 3d. A spec gap found on the way: how the 88 mutations are laid out
v4 section 4 says the job "applies 88 mutations ... split 4 per package" and "writes the mutated packages to /out". It never says whether there is one copy per package carrying 44 mutations, or one copy per mutation, and it has no collision rule. Both readings break the scoring:
- **One copy per package, 44 mutations:** mutations can share a line (P5 L49 is an R1 twin, an R3 site and the C1 line). They can also share evidence lines: an R2b deletion on L170 and a count change on L163 both resolve to one flag at L163. Under the run-147 matching rule, that single flag would credit both, which inflates recall.
- **One copy per mutation:** every unmutated false flag repeats in about 44 copies. The 4 flags above would then count as about 176 false positives and sink P3 (precision >= 0.50) on their own.

## 4. Proposed v5 amendments (fixed before code; not yet in any plan)
1. **Take the superlative sub-rule out of scored R5.** It may print as descriptive, unscored output.
   - Keep S11's adjudicated label (R). Report it openly as **not covered by any v5 module**, so v5 covers **37 of 82** seed rows (**36 of 79** in the headline set) instead of 38/37. Plan section 9 must state the drop.
   - Reason: section 3a-3c, where no deterministic scope rule separates S11 from the clean superlatives and H-A can't test the rule.
   - Moving the superlative check to the semantic (v2, source-reading) module list is future work.
2. **Mutation layout (new section 4 text):**
   - Copies: each package gets as many copies as its largest per-module mutation count, normally 4. Copy j holds the j-th mutation of every module in that package, so each copy has at most one mutation per module.
   - Collisions: within a copy, no mutated line may be a primary or expected evidence line of another mutation (same twin group, same gated count or ID block, same linked table column, same reference entry, same sentence). The mutation job redraws on a collision and records it. If a module runs out of sites, the shortfall is recorded as v4 already allows.
   - P3 dedupe: P3 counts each flagged unmutated (module, line) **once per package**, however many copies flag it. A flag on a line that is mutated only in another copy counts as a flag on an unmutated line.
3. **R5 citation mapping:** add a corporate author (or its initials, ignoring "of") plus the year, but **only for references whose author field is an organisation**. This states the target of the organisation-name clause that the run-147 note asked about. Citing a personal-author reference only by an organisation name (the S32/S33 pattern) stays flaggable. Tuned on ref 33; say so.
4. **Restated prediction:** with amendment 1, R5 gives **0 unmutated flags** on both cut texts, provided the run-147 mapping and acronym rules hold. Those rules still need their own literal pass before freeze (the "never cited" and "ambiguous author-year" halves were counted in run 147 only for refs 29, 39, 41 and Rentsch).

## 5. Candidate rows found while counting (outside all headline counts)
- **C6 (P4 L184, wording, minor):** "its results would give the first adherence estimate in people with AUD". Read literally, this is false, because adherence to AUD medicines has been estimated many times. The intended meaning is the first estimate **for spironolactone**.
  - Fix in P4 v19 by adding "for spironolactone" (+2 words).
  - Found by reading a hit the rule correctly ignores. It is a semantic-scope problem, not an R-type one.
- No other hit in either text is a real unsupported uniqueness claim. P4 E.6 L168 says every exclusive claim ("only", "first", "none") was read back from its source on 2026-10-19/20, which fits this.

## 6. Limits
- This is one hand pass by the model family that wrote both texts and the rule.
- Grep found the triggers; the context reading was by eye. A code run must confirm the counts. Variants B and C were counted on paper only.
- Only the four trigger phrases were counted. Bare "only", "first" and "most" (about 32 + 29 hits in the run-147 count) are outside the narrowed rule by design, and outside this count.
