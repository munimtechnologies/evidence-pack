# Claim-provenance checker: H-A hand tally, written before the sealed scorer runs (run 158, 2026-10-22)

**Status note (rule i2): written 2026-10-22 ~11:00Z.** The checker job `ha-check-v1` has run (log entry 8). The sealed score job `ha-score-v1`, which runs the scorer exactly as published at tag v0.5.2, has **not** run yet. This file is one AI session's hand application of that scorer's readings (S1-S10, `scoring-notes.md`) to `labels.json` and the checker's 20 reports. It is published first so that the sealed job also checks the scorer: if the two differ, the difference is reported, not hidden. **The official H-A result is the job's `results.json`, not this file.** MV2 of Munim, Inc. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has checked it. CC BY 4.0.

## 1. Headline (hand tally; the job confirms or corrects it)
| Rule | Pre-registered pass condition | Hand tally | Pass? |
|---|---|---|---|
| P1 recall | at least 64 of 80 planted errors caught (v5 6.0 matching) | **74 / 80 = 0.925** (Wilson 95% 0.846-0.965) | yes |
| P2 per module | at least ceil(5/8 x planted) per module | 10 of 11 modules pass; **R5 3 / 8 (needs 5)** | **no** |
| P3 precision | at least 1/2 (S6 dedupe) | **96 / 110 = 0.873** before adjudication; 102 / 110 = 0.927 after (section 4) | yes |
| P4 vs keyword baseline | precision at least 2x baseline's, recall no more than 0.10 below | recall half passes arithmetically (0.925 >= any baseline recall - 0.10); precision half expected to pass (the baseline flags 268-435 sentences per file) but **not hand-counted** | expected yes |
| P6 runtime | under 60 s per file, 1 CPU | max 0.564 s | yes |
| 6.1 prediction | 0 scored flags on the two unmutated cut texts, apart from C5 | **14 flags** (8 distinct package/module/line keys) | **no** |

## 2. What the numbers mean, honestly
- **High planted-error recall is an upper bound, not a field result.** The mutation operators were written to produce exactly the errors these modules look for, by the same model family that wrote the modules. On the 82 natural problems of the development set, literal coverage is 21 of 82 (25.6%). H-A shows the code does what its plan says. It doesn't show the plan catches most real errors.
- **One of the 74 catches is spurious.** R5-P4-03 (citation [11] removed from P4 L34) is "caught" by an R5 author-year flag on "The 2021" that is already on the unmutated text. A post hoc differential reading (count a catch only if some catching flag isn't on the cut text in the same module, rule and line) gives 73 / 80 = 0.9125. This reading wasn't pre-registered. It is reported for robustness only.
- **R5's P2 failure is the matching rule, as mutation-notes section 4 predicted before any label existed.** All 5 missed citation removals (R5-P4-01, -05, -06, R5-P5-01, -04) **were found at the other end**: in each copy the checker flagged the reference the removal left uncited, and that reference line is exactly the mutation's evidence line (198, 215, 226, 358, 352; R5-P4-03's is 208, also flagged). v5 6.0 counts a catch only when a flag covers the mutated line, so these count as misses and their six flags as false positives. Under the descriptive secondary match (S4), R5 finds 8 of 8.
- **The one non-R5 miss** is R1b-P5-01 (P5 L214, where the sentence stating E.5's SMD sign convention was deleted). No R1b flag appears anywhere in that copy. **Traced cause:** for a ### section, the frozen code's `_has_convention` searches every line of the parent ## section above the ### heading, sibling subsections included. So P5 L149, in an earlier E subsection ("Negative = less pain or better function on metformin"), still counts as E.5's convention once L214 is gone. That inherited convention is the *opposite* of the deleted one ("a positive SMD means less pain"). A reader of the mutated copy would be told the wrong sign, and the checker stays silent. Even if R1b-b had fired, its flag sits on the section heading (L202) with the value lines as evidence, and none of those is L214, so v5 6.0 would still count a miss (secondary match only). The hand-listed site file didn't check this site's detectability against the scope reading.
- **R5b-P5-04** (copy 5) is caught only by R2b's count flag on L163, whose evidence lines include L173. R5b itself raised nothing there. It counts as caught under v5 6.0 but not as caught by its labelled module.

## 3. The 6.1 prediction failed: 14 flags on the unmutated texts
Our forecast (scoring-notes section 3) was "fails, with 1-5 other flags; likeliest R7-b on P5 L228 and R6-b". The direction and two of the three sources were right; the size was wrong.

| Text, line | Module, rule | Flags | Cause | Real problem? |
|---|---|---|---|---|
| P4 L34, L63; P5 L38, L61 | R5 author-year-none ("The 2021", "The 2023", "The ACR 2026" x2) | 4 | **Not foreseen.** The v6 candidate grammar accepts any capitalised word with a lower-case letter as a surname, so a sentence-initial "The" before a year becomes an author-year citation. "ACR" is then read as initials. | No. Each sentence carries its numbered citation or names the ACR summary. |
| P4 L81 | R6-b b-no-plan | 1 | Reading 53 (forecast): "our own pre-registered national survey check (E.4)" cites no plan file in that sentence. | No. The plans are cited in E.4. |
| P4 L134 | R7-b b-count "5", b-name "Georgescu" | 2 | "Farokhnia 5 AUDIT-C estimates" is a true sub-count of the 27 rows; Georgescu and Wren is the method's source, not a checked study. | No. `recheck.json` holds exactly 5 Farokhnia rows. |
| P5 L226 | R7-b b-name "Georgescu" | 1 | Method's source, as above. | No. |
| P5 L228 | R7-b b-name x6 (Chen, Chenchula, Guo, Haj Shehadeh, Hatano, Jiang) | 6 | Reading 57 (forecast). The sentence names studies checked by the tool and studies checked by hand. The rule reads the whole sentence. Also, `recheck.json` labels three of the four meta-analyses by journal, not by first author. | No error in the claim. There is a labelling gap in our own job file: a reader can't tell by name which meta-analysis row is Chenchula's or Guo's. Judged not real, conservatively. |

All 14 are on the two texts the rules were hand-tuned against (log entries 3-4), and no hand pass caught the "The <year>" pattern. This is the sixth method lesson: hand passes that trace the plan's words don't replace running the frozen code on the clean text. Running it would have shown these flags, but it would also have exposed the code to the base texts before H-A, which plan v7 ruled out.

## 4. Adjudication (S7), made after this hand tally and before the sealed scorer
S7 says the adjudication is made by hand after scoring. It was made after this hand tally, before the job output exists, and it is fixed in `score-job/adjudication.json`. The job scores both with and without it.
- **Judged real (6):** P4 R5 L198, L208, L215, L226; P5 R5 L352, L358. Each is a "reference never cited" flag on the reference whose only citation the planted removal deleted in that copy. It is that mutation's own evidence line.
- **Judged not real (8):** the 8 base-text keys in section 3. That includes P5 R7 L228, where we chose the conservative reading.
- P3 passes either way. The pre-adjudication value (0.873) is the headline.

## 5. Per-copy tally (catching flag: module, line; "ev" = the mutated line is one of the flag's evidence lines)
- **P4-copy01 (8/9):** R1-P4-03 L88 (R1 L147 ev); R1b-P4-02 L94; R2-P4-04 L45; R2b-P4-03 L160; R3-P4-01 L87; R4-P4-03 L161; **R5-P4-05 L35 miss** (R5 never-cited L215); R6-P4-04 L164; R7-P4-02 L134 (R7-b, R5).
- **P4-copy02 (7/8):** R1-P4-06 L122; R1b-P4-03 L94; R2-P4-02 L45; R2b-P4-02 L160 (R2b, R7-a); R4-P4-04 L38 (R4-a); **R5-P4-01 L31 miss** (L198); R6-P4-05 L154 (R6-b-after); R8-P4-03 L167 (R8 L9 ev).
- **P4-copy03 (8/8):** R1-P4-02 L147; R1b-P4-06 L153; R2-P4-03 L45; R2b-P4-01 L160; R4-P4-01 L36; R5-P4-03 L34 (spurious, section 2); R6-P4-02 L114; R8-P4-01 L65 (R8 total).
- **P4-copy04 (7/8):** R1-P4-08 L124; R1b-P4-05 L153; R2-P4-05 L45 (R2 N-of-M); R4-P4-02 L131; **R5-P4-06 L76 miss** (L226); R5b-P4-02 L160; R6-P4-03 L155; R8-P4-02 L167 (R8 L10 ev).
- **P4-copy05-08 (5/5):** R2-P4-01 L45; R5b-P4-01 L160; R5b-P4-03 L160; R7-P4-01 L160 (R7-a); R8-P4-06 L167 (R8 L158 ev).
- **P5-copy01 (9/9):** R1-P5-06 L111; R1b-P5-04 L141; R2b-P5-04 L173; R3-P5-03 L298; R4-P5-02 L68; R5-P5-11 L280 (acronym); R6-P5-02 L197; R7-P5-04 L250; R8-P5-04 L256 (R8 L353 ev).
- **P5-copy02 (9/9):** R1-P5-04 L218; R1b-P5-03 L140; R2b-P5-02 L172; R3-P5-01 L49; R4-P5-06 L253; R5-P5-08 L111 (ambiguous); R6-P5-01 L30; R7-P5-06 L226 (R7-b, R5); R8-P5-01 L75.
- **P5-copy03 (6/8):** R1-P5-03 L50 (R1 L218 ev); **R1b-P5-01 L214 miss**; R2b-P5-03 L173; R3-P5-02 L51; R4-P5-03 L86; **R5-P5-04 L112 miss** (L352); R6-P5-04 L154; R8-P5-07 L256 (R8 L356 ev).
- **P5-copy04 (7/8):** R1-P5-05 L55 (R1 L111 ev); R1b-P5-08 L210; R2b-P5-01 L163; R4-P5-01 L36; **R5-P5-01 L259 miss** (L358); R6-P5-03 L223; R7-P5-05 L228 (R7-b, R5); R8-P5-02 L82.
- **P5-copy05-10 (8/8):** R5b-P5-04 L173 (R2b L163 ev only); R7-P5-02 L223; R5b-P5-01 L173; R7-P5-03 L228 (R7-a); R5b-P5-02 L173; R5b-P5-07 L172; R5b-P5-03 L173; R7-P5-01 L172.

Per module (caught / planted): R1 8/8, R1b 7/8, R2 5/5, R2b 7/7, R3 4/4, R4 8/8, **R5 3/8**, R5b 8/8, R6 8/8, R7 8/8, R8 8/8.

True-positive keys: P4 44, P5 52 (96). False-positive keys: P4 8 (R5 L34, L63, L198, L208, L215, L226; R6 L81; R7 L134); P5 6 (R5 L38, L61, L352, L358; R7 L226, L228). C5's flags (P5 R5 L248, L252) are excluded both ways.

## 6. Forecast grades (scoring-notes section 3)
| Forecast | Outcome |
|---|---|
| 6.1 fails with 1-5 flags; R7-b P5 L228 and R6-b likeliest | Failed, as forecast, but with 14 flags. Both named sources appeared; R5 "The <year>" (4 flags) was not foreseen. |
| R5 fails P2 | Right: 3/8. |
| R1b P2 depends on convention deletions | R1b passes, 7/8; the one convention deletion in its draw was missed. |
| P1 recall 0.70-0.85 | Wrong: 0.925, above the range. |
| P4's recall half at risk | Wrong. With checker recall at 0.925 it cannot fail. |
| P6 passes | Right. |
