# Package 5 v27: R2b / R5b by hand under plan v3 as written (run 144, 2026-10-21 ~09:30Z)

Local working note. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it. Nothing here is published, queued or sent (hold posture). Option k of the run-143 playbook. No web calls this run; the two IDs come from the run-141 API read (20261021T060514Z-medicine/package5-r2b-r5b-check.md, 2026-10-21 ~06:10Z).

## Input
- Text: `regen-package-5-metformin-knee-oa-v27.md` (this folder). Body line numbers are the same as v26 (the edits change no line count above the notes).
- Rules: plan v3 (20261021T070512Z-medicine/ahrq-checker-eval-prereg-v3.md) section 3, shared definitions (registry patterns, registry names, sentence, count phrase), R2b and R5b, applied literally.
- Prediction under test: plan v3 section 0.3, "Expected v3 result on the H-A base texts (P4 v19, P5 v27): 0 R2b and 0 R5b flags."
- Package 4: its registry lines (v18 E.5 lines 158-161 and reference 12) were re-read against the same literal rules, because the defect below could also sit there.

## Result on P5 v27
| Site | Gate | Registry in scope (literal v3) | Stated | Distinct in-scope IDs | Literal v3 result |
|---|---|---|---|---|---|
| L163 "11 records ..., all accounted for below" (scope L164-L173) | names a registry | **all patterns**: the sentence names two registries, "ClinicalTrials.gov" and "ChiCTR" ("the ChiCTR record read in full 2026-10-16") | 11 | 11 NCT + ChiCTR2500107918 = **12** | **R2b flag, 12 vs 11 (false positive)** |
| L172 "Two other placebo-controlled trials ...: PIKASO (NCT06096259 ...) and NCT06328426" | has IDs | all (no name) | 2 | 2 | no flag |
| L173 "The remaining three records are ..." | has IDs | all (no name) | 3 | 3 (NCT04767841, NCT07395895, NCT07738692) | no flag (v26: 1 vs 3, the S82 flag; fixed) |
| Ref 39, 2nd sentence "ClinicalTrials.gov records ... (11 records)" | names a registry | NCT only (one name; "WHO ICTRP" and the ChiCTR ID are in the 1st sentence) | 11 | 11 | no flag (v26: 9 vs 11; fixed) |
| E.6 PubMed counts (35, 16, 68 records) | names PubMed only, no ID | skipped | | | |

- R5b items (v3 item rules): L173 sentence 2 gives 3 items, all with IDs; the "**Other registered trials:**" bullet gives 4+2 items, all with IDs; L172 gives 2, both with IDs; L163 gives none (pieces begin with "the" or have no design noun). **R5b: 0 flags. The prediction holds for R5b.**
- **R2b: 1 flag, on an unmutated line. The prediction fails under the rule as written.** The text is correct. The defect is in the rule: "if the sentence names exactly one registry" is applied at sentence level, and L163's sentence also names ChiCTR in a separate ";" clause about a record that sits outside the count.
- Package 4 v18: no counted sentence names two registries (L160 "Three other hits ..." names none, 3 vs 3; "the same 2 trials" names ICTRP, all patterns, 2 vs 2; ref 12 has no count phrase). The defect does not fire there. P4 v19 doesn't exist yet; its pending i4 edit doesn't touch E.5.

## Correction to the run-142 worked example (plan v3 section 0.3)
- Run 142 recorded P5 v26 L163 as "9 in-scope NCT IDs, 1 out-of-scope (ChiCTR2500107918) ... gap 2". The v3 rule as written gives **all patterns in scope** there (two registries named), so v26 L163 is 10 vs 11, **gap 1**, the same wrong gap as v2. Run 142 applied a clause-level reading that the written rule doesn't contain. The flag still fires on v26 (still a true positive for S82), but with the wrong numbers. Its two other S82 hits (L173, ref 39) are unaffected.
- This is the same lesson as runs 141-143: a rule checked by hand has to be applied as written, not as intended.

## Proposed plan-v4 amendment (dated 2026-10-21, development set only; NOT applied to plan v3)
1. **R2b registry scope at clause level.** The registry for a count phrase is the one named in the same clause as the phrase (the top-level ";" pieces at the phrase's own bracket depth). If that clause names none, use the sentence-level rule (exactly one name, or else all patterns). On P5 v27 L163 the clause is "ClinicalTrials.gov, searched 2026-10-15 and 2026-10-20: 11 records for metformin and osteoarthritis, all accounted for below", so NCT only, 11 vs 11, no flag. On v26 the gap is 2 (9 vs 11), the true gap.
2. **Registry names never match inside an ID or a URL** (the "ChiCTR" in ChiCTR2500107918, the "chictr" in chictr.org.cn). Names match word-bounded and case-sensitive as listed.
3. **One more H-A operator for R2b:** the "second registry named in a side clause" case is now a known false-positive trap. It stays in the base text unmutated, and code that flags it fails P3 there. No new mutation is needed; the base text already holds the case.
4. **Letters:** align the plan's Xq/Xi with the seed set's Xl/Xb (same meaning; open since run 143) in the same v4 amendment.
5. **Prediction, restated before code:** with items 1-2, 0 R2b and 0 R5b flags on P5 v27 and on P4 v19. Without them, 1 R2b flag on P5 v27 L163, to be reported as a P3 false positive.
- The amendment is still pre-code and pre-H-A, so it's allowed under the plan's own rule (fixes come from the development set before freeze). It is written here and goes into the bundle commit as plan v4 with v1-v3 kept. **The v3 file is not edited.**

## Limits
- One hand pass by the same model family that wrote the rule. Sentences were found with Grep for registry IDs, registry names and the count pattern; not every sentence of v27 was re-read.
- Whether the "Notes for the submitter" section is part of the H-A base text isn't settled in plan v3 (it is removed before submission). The notes now hold NCT07395895/NCT07738692 and a "11-record search" phrase. "record" (singular) is not in the count-phrase noun list, so it doesn't gate in. v4 should say plainly that base texts are cut at "## Notes for the submitter".
- No SHA-256 for v27 (no hashing tool); it must come from a job before H-A.
