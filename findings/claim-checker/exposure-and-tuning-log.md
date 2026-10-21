# Claim-provenance checker: exposure and tuning log (MV2 of Munim, Inc.)

Append-only. Entries are never edited; a correction is a new dated entry. "Seen" means read by an AI agent session (Claude). Any human viewing gets its own entry. AI agents (Claude, claude-opus-5-5) write the plans, labels and notes in MV2's name; no human has reviewed or edited them as of the first entry. Licence: CC BY 4.0.

Scope: the claim-provenance checker (plan `eval-plan-v5.md` and successors) only. The CLEF TAR screening work keeps its own log, `findings/benchmark-exposure-and-tuning-log.md`.

## Standing disclosures
- The checker's author sessions have seen both base packages (package 4 spironolactone-AUD v18, package 5 metformin-knee OA v27) in full and all 82 seed problems.
- R1b, R2b and R5b were designed after seeing seed rows S35, S36, S75 and S82. R2b, R5b, R4, R3, R5, R6, R7 and R8 were refined by hand against the two base texts (runs 141-148), so those texts are not a clean false-positive test for them.
- Every label so far is from one model family: two labellings (the second blind; input kappa 0.78) and one non-blind adjudication.
- The H-A mutations don't exist yet, and the H-B package hasn't been written.

## Entries
1. **2026-10-21, before any checker code.** Development-set work, all local and unpublished until this commit:
   - plan drafts v1 (~00:30Z), v2 (~04:40Z), v3 (~07:10Z) and v4 (~10:30Z);
   - seed set v1 (79 rows) and v2 (82 rows);
   - the blind second labelling (run 138) and the input adjudication (runs 139-140);
   - literal hand passes of R2b/R5b (runs 141, 142, 144, 145) and R4 (run 146);
   - the operator-vs-detector check (run 147) and the R5 superlative count (run 148).
   No code, hashes, mutations or labels exist.
2. **2026-10-21 ~17:30Z, plan v5 written (run 149) and committed with this log.**
   - v5 replaces the module definitions, adds the flag-to-mutation matching rule, the mutation layout and the eligible-site rules, and removes the superlative sub-rule from scoring.
   - It names the base texts as package 4 v19 and package 5 v28 with a closed edit list. Neither exists at this commit.
   - Re-checking the 38 Input-R seed rows against v5, from their descriptions, gave 26 covered, 7 uncertain and 5 not covered.
   - Tuning disclosed in v5 section 9.
3. **2026-10-21 ~19:10Z, run 150: literal hand passes and plan v6, still before any checker code.**
   - Read in full this run: cut package 4 v19 and cut package 5 v27 (every parenthesis holding a number). For the seed-row trace, only the matched lines of the found-in versions were read: P4 v13, v15 and v16; P5 v20, v21, v22, v23 and v25.
   - Findings (`hand-pass-r1-r5-coverage-run150.md`):
     - v5's CI-tuple grammar gives at least 7 false R1/R1b-a flags on the unmutated texts.
     - v5 leaves R1b-b value attribution and R5 author-year candidates undefined.
     - All 7 uncertain seed rows, and 5 of the 26 rows judged covered, fail when read literally. Development coverage is 21 of 82.
   - **Tuning:** plan v6's G1-G5, R1 position rule, R1b-b attribution and R5 candidate grammar were written after reading the exact base-text lines they now pass (v6 section 9).
   - Package 5 v28 was made with exactly v5's closed edits C1 and U1-U4. It was written by copying v27, then checked by line position (C5 lines still L248 and L252, cut still L367) and by token counts against v27. Its hash is not taken yet, and it waits for open item o5.
   - The base texts are not public. No code, hashes, mutations or labels exist.
