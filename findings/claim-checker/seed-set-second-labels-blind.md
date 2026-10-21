# Seed set: blinded second labelling (run 138, 2026-10-21 ~02:30Z)

Local file, not published. AI agents (Claude, claude-opus-5-5) made these labels in MV2's name. No human has checked them.

**Procedure (plan section 2, as written in the run-137 playbook):** the first step of this run was a Grep `-o` of `^\| S\d+ \| \d+ \| P\d \| [^|]+ \| [^|]+ \|` over claim-provenance-seed-set-v1.md (S01-S79) and package4-rule-i4-i5-check.md (S80-S81). The output showed only ID, run, package, section and problem text. The only other parts read were the seed-set header (lines 1-23: the label definitions and the reconciliation note, with no per-row labels). These labels were written and saved before the original Class/Input/v1 columns were opened.

**Limit:** the second labeller is the same model family that wrote the problem text and the first labels, so this measures how stable the labels are, not agreement between independent people. A human labeller is still needed for a real kappa.

| ID | Class | Input |
|---|---|---|
| S01 | A | Xs |
| S02 | A | Xs |
| S03 | C | Xs |
| S04 | E | Xs |
| S05 | B | Xr |
| S06 | I | Xs |
| S07 | C | Xl |
| S08 | C | Xr |
| S09 | C | Xr |
| S10 | C | Xl |
| S11 | J | R |
| S12 | E | Xl |
| S13 | E | Xl |
| S14 | J | S |
| S15 | E | Xl |
| S16 | J | Xb |
| S17 | J | Xb |
| S18 | J | Xb |
| S19 | F | S |
| S20 | A | Xs |
| S21 | K | R |
| S22 | J | R |
| S23 | A | Xs |
| S24 | K | R |
| S25 | K | R |
| S26 | J | R |
| S27 | L | R |
| S28 | J | R |
| S29 | D | Xr |
| S30 | D | Xr |
| S31 | C | Xr |
| S32 | J | R |
| S33 | J | R |
| S34 | E | Xr |
| S35 | J | R |
| S36 | E | R |
| S37 | D | Xr |
| S38 | F | Xs |
| S39 | F | Xs |
| S40 | F | R |
| S41 | F | R |
| S42 | H | R |
| S43 | B | Xb |
| S44 | A | Xs |
| S45 | F | R |
| S46 | F | S |
| S47 | G | R |
| S48 | F | S |
| S49 | L | Xs |
| S50 | H | R |
| S51 | H | R |
| S52 | B | Xs |
| S53 | F | S |
| S54 | F | R |
| S55 | L | Xs |
| S56 | G | R |
| S57 | G | R |
| S58 | F | S |
| S59 | G | R |
| S60 | G | R |
| S61 | G | R |
| S62 | G | R |
| S63 | G | R |
| S64 | G | R |
| S65 | G | S |
| S66 | H | R |
| S67 | E | R |
| S68 | H | R |
| S69 | I | Xs |
| S70 | I | R |
| S71 | F | Xs |
| S72 | I | Xs |
| S73 | E | Xs |
| S74 | L | R |
| S75 | I | R |
| S76 | I | Xs |
| S77 | I | R |
| S78 | J | Xb |
| S79 | I | R |
| S80 | I | Xs |
| S81 | I | Xs |

---

## Comparison with the first labels (written after the table above was saved)

First labels: claim-provenance-seed-set-v1.md (S01-S79) and package4-rule-i4-i5-check.md (S80 E/S, S81 I/Xs).

### Agreement
| Set | Class agreement | Class kappa (12 classes) | Input agreement (R/S/X) | Input kappa (R/S/X) |
|---|---|---|---|---|
| 79 rows (the plan's set) | 72/79 = 91.1% | 0.90 | 69/79 = 87.3% | **0.78** |
| 81 rows (+ S80, S81) | 73/81 = 90.1% | 0.89 | 70/81 = 86.4% | 0.77 |

- Marginals, 81 rows. First labels: R 35, S 9, X 37. Second labels: R 36, S 7, X 38. Class, first: A4 B3 C7 D2 E10 F13 G10 H6 I8 J11 K3 L4. Class, second: A5 B3 C6 D3 E8 F12 G10 H5 I10 J12 K3 L4.
- Kappa = (po - pe)/(1 - pe), with pe from the two labellers' marginals. 79-row input: po 0.8734, pe 2612/6241 = 0.4185, so kappa 0.782. 79-row class: po 0.9114, pe 648/6241 = 0.1038, so kappa 0.901.
- **The plan's gate (section 2: revise the R/S/X definitions if input kappa < 0.6) is passed (0.78).** By the plan's rule, the definitions stay as they are.
- R vs not-R (what v1's scope rests on): 9 rows swap and 31 are R in both. The size of the R set is stable (35 vs 36), but its membership isn't fully.
- Rows that are X in both labellings: 34. The X subtype matches in 31 (S03 Xl/Xs, S05 Xs+Xr/Xr, S43 Xs/Xb differ).

### Disagreements (first / second)
Class (8): S30 C/D; S35 E/J; S43 F/B; S44 F/A; S71 I/F; S76 B/I; S79 H/I; S80 E/I.
Input (11): S35 Xr/R; S36 Xr/R; S38 R/Xs; S39 R/Xs; S44 S/Xs; S48 R/S; S65 R/S; S70 Xs/R; S75 S/R; S79 S/R; S80 S/Xs.

### What the disagreements show
1. **The input label depends on the package version, and the short description doesn't carry it.** S38/S39: the second labeller assumed the 10.4% figures had to come from the cited source. Package 4 v18 prints the TriNetX table itself (lines 104-111), so **the first labels (R) are right**. S70: v26 now prints both arms' baseline SDs (line 149), but only because run 133 added them. Whether the version that had the problem printed them, or held them in a job file, can't be told from the row, so it's unresolved, leaning to the first label (Xs). S35/S36 are the same kind of question (is the registry ID or record count in the package or job files, or only in the registry?).
2. **Class boundaries that blur:** registry reading vs an exclusive claim (S30 D/C); identifiability vs completeness (S35 J/E); method/dose re-derivation (I) vs count (S71), attribution (S76), "checked" claims (S79) and completeness (S80). Most are rows where two classes truly apply. One class per row forces a choice.
3. **"Uncited claim" rows are stable** (S11, S14, S22 agree on both columns). So are the CI-wording rows (S56-S64 G/R, except S65's input) and the date rows (K/R).

### Proposed clarification (record only; the gate doesn't require it)
- Add one field per row: **where the needed fact lived in the version where the problem was found** (package section/table, job file, or outside source), and judge Input from that field. This would have settled S38/S39 and probably S35/S36/S70 without judgement.
- Tie-break for class: when two classes apply, take the one naming the check that would have caught it (e.g. S80: the dose re-derivation, I), and list the second class in a note.
- Neither change alters the 35-row v1 scope unless a re-check of S35/S36/S70 against their original versions moves them to R. That re-check is open.

### Limits
- Same model family as the first labeller and the author of the descriptions. The descriptions carry hints written by the first labeller (e.g. "(CI below 1 in four)"), so this agreement is an upper bound on what two independent people would reach. A human second labelling is still needed before any agreement figure goes in a submission.
- The plan's order puts the second labelling AFTER the plan is committed (section 8, step 2). The plan isn't committed yet because of the hold. Blinding is unaffected. When the plan is committed, this file should be committed with it, and the commit message should say it predates the plan commit.
- S80 and S81 were added after the plan was written. The plan's figure is the 79-row one.
