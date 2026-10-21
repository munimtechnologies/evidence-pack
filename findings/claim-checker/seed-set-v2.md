# Claim-provenance checker: labelled seed set v2 (run 143, 2026-10-21)

Local file, not published. AI agents (Claude, claude-opus-5-5) compiled it in MV2's name. No human has labelled or checked a row. Licence when published: CC BY 4.0. Machine-readable copy: `claim-provenance-seed-set-v2.csv` (same rows, same columns).

**What changed from v1** (20261021T002117Z-medicine/claim-provenance-seed-set-v1.md):
1. Rows S80-S81 (run 137, 20261021T012336Z-medicine/package4-rule-i4-i5-check.md) and S82 (run 141, 20261021T060514Z-medicine/package5-r2b-r5b-check.md; plan v3 section 0.2 item 6) merged in. 82 rows.
2. Both labellings shown side by side: the first labels (v1 file; S80-S81 from the run-137 file) and the blind second labels (20261021T022123Z-medicine/seed-set-second-labels-blind.md). S82 was labelled once, not blind.
3. **Adjudicated Input** column (runs 139-140: 20261021T032436Z-medicine/seed-set-input-adjudication.md and plan v2 section 2) under the two-field rule: Input is judged from the package version the problem was found in; coverage is a separate column.
4. The v1-module column is replaced by **coverage under plan v3's 11 modules** (R1-R8 plus R1b, R2b, R5b; 20261021T070512Z-medicine/ahrq-checker-eval-prereg-v3.md section 3).
5. A found-in column, filled only where the adjudication recorded the version. Elsewhere the general rule applies (run N checked the version made by run N-1) and the version number was not re-traced.

**Class is not adjudicated.** The reference class is the first label. The second label is shown; the 8 class disagreements (S30, S35, S43, S44, S71, S76, S79, S80) are kept open. The second labeller's proposed tie-break (take the class naming the check that would have caught it) was never adopted, so it is not applied here. No figure in the plan depends on class.

**Input subtypes:** Xs cited source, Xr registry, Xl literature search, Xb bibliographic index (plan v2/v3 wrote these as Xs/Xr/Xq/Xi; same meaning; v1's letters kept here so rows match v1). The X subtype is not adjudicated: where the two labellings differ (S03, S05, S43), the first label stands.

## Rows
Columns: ID; run that found it; package; section; problem (short, from v1 or the source file); class 1st / 2nd; input 1st / 2nd / **adjudicated**; v3 coverage (module, or - if outside v1's R scope); found-in version where recorded.

| ID | Run | Pkg | Section | Problem (short) | Class 1/2 | Input 1/2/adj | v3 cov | Found in |
|---|---|---|---|---|---|---|---|---|
| S01 | 115 | P5 | D | "rose about linearly" loosened the label | A/A | Xs/Xs/**Xs** | - | |
| S02 | 116 | P4 | Overview | Quoted label sentence dropped "or titration" | A/A | Xs/Xs/**Xs** | - | |
| S03 | 117 | P5 | A | "The 2026 update's only new recommendation" false against ACR's press release | C/C | Xl/Xs/**Xl** | - | |
| S04 | 117 | P5 | A | Fu 2024 MVMR verification left out | E/E | Xs/Xs/**Xs** | - | |
| S05 | 118 | P4 | E.5 | Design-abstract quotes credited to the registry record | B/B | Xs+Xr/Xr/**Xs+Xr** | - | |
| S06 | 118 | P4 | E.3e | Authors' 0.5 threshold written as observed "up to about 0.5" (max 0.31) | I/I | Xs/Xs/**Xs** | - | |
| S07 | 119 | P5 | A | "First positive placebo-controlled trial": two earlier positive trials | C/C | Xl/Xl/**Xl** | - | |
| S08 | 119 | P5 | E.2, B | "First registered independent replication" (NCT07065591 earlier) | C/C | Xr/Xr/**Xr** | - | |
| S09 | 119 | P5 | E.2 | "Only registered placebo trial with a structural primary": overbroad | C/C | Xr/Xr/**Xr** | - | |
| S10 | 119 | P5 | D | "No human PK/PD study of metformin for pain exists" (Kialka 2016) | C/C | Xl/Xl/**Xl** | - | |
| S11 | 119 | P5 | F | Superlative co-medication claim with no source | J/J | R/R/**R** | R5 | |
| S12 | 120 | P5 | E.3, E.5 | Jiang 2025 NMA and Chen S 2022 missing | E/E | Xl/Xl/**Xl** | - | |
| S13 | 121 | P4 | C | Animal section one-sided: four null studies missing | E/E | Xl/Xl/**Xl** | - | |
| S14 | 121 | P4 | A | Amygdala mechanism sentence uncited | J/J | S/S/**S** | - | |
| S15 | 122 | P5 | C | Animal section one-sided: Minton 2021 and two retracted studies missing | E/E | Xl/Xl/**Xl** | - | |
| S16 | 123 | P5 | ref 47 | Minton 2021 erratum not cited | J/J | Xb/Xb/**Xb** | - | |
| S17 | 123 | P5 | C | Cited synthesis (Yao 2026) cites a retracted study; not noted | J/J | Xb/Xb/**Xb** | - | |
| S18 | 123 | P5 | ref 23 | Mohammed year flagged. **Not an error** (false lead) | J/J | Xb/Xb/**Xb** | - | |
| S19 | 124 | P5 | B | Summary kept "two animal studies point the same way" after C changed | F/F | S/S/**S** | - | |
| S20 | 125 | P4 | A | Pince quote cut before "in ASUD" | A/A | Xs/Xs/**Xs** | - | |
| S21 | 125 | P4 | A | "66 years on the US market" false from 2027-01-21 | K/K | R/R/**R** | R4 | |
| S22 | 125 | P4 | D | Named trial RALES uncited | J/J | R/R/**R** | R5 | |
| S23 | 126 | P5 | C | Minton quote cut dropped "added to rapamycin" | A/A | Xs/Xs/**Xs** | - | |
| S24 | 126 | P5 | E.2 | "Unreported nearly 22 months after completion" false at the deadline | K/K | R/R/**R** | R4 | |
| S25 | 126 | P5 | A | "Full manuscript not yet published" unanchored | K/K | R/R/**R** | R4 | |
| S26 | 126 | P5 | E.5b | "Zhang 2022" collides with ref 15 | J/J | R/R/**R** | R5 | |
| S27 | 126 | P5 | E.5a, E.6 | Internal labels "version 5", "version 18" | L/L | R/R/**R** | R6 | |
| S28 | 127 | P4 | refs | Ref 12 never cited | J/J | R/R/**R** | R5 | |
| S29 | 127 | P4 | E.5 | "Terminated 2017": last-update date read as end date | D/D | Xr/Xr/**Xr** | - | |
| S30 | 127 | P4 | E.5 | "Are not AUD trials": one lists Alcoholism | C/D | Xr/Xr/**Xr** | - | |
| S31 | 127 | P4 | A | "The only registered clinical studies are ..." too broad | C/C | Xr/Xr/**Xr** | - | |
| S32 | 128 | P5 | A | Ref 32 cited only by guideline name | J/J | R/R/**R** | R5 | |
| S33 | 128 | P5 | A | Ref 34 cited only as "OARSI 2019" | J/J | R/R/**R** | R5 | |
| S34 | 128 | P5 | E.2 | NCT06126029 not described as a second unreported placebo trial | E/E | Xr/Xr/**Xr** | - | |
| S35 | 128 | P5 | E.2 | METRO listed with no registry ID | E/J | Xr/R/**R** | R5b | P5 v21 E.2 |
| S36 | 128 | P5 | E.2 | 3 of the 11 search records unaccounted for | E/E | Xr/R/**R** | R2b | P5 v21 E.2 |
| S37 | 128 | P5 | E.2 | NCT07065591 referral criterion missing | D/D | Xr/Xr/**Xr** | - | |
| S38 | 129 | P4 | E.3a | "10.4% in eight comparisons" (six) | F/F | R/Xs/**R** | R2 | P4 v18 (table printed) |
| S39 | 129 | P4 | B | Column maximum paired with the full comparator range | F/F | R/Xs/**R** | R2 | P4 v18 (table printed) |
| S40 | 129 | P4 | B | "HR 0.77-0.81 in seven of nine" (eight) | F/F | R/R/**R** | R2 | |
| S41 | 129 | P4 | E.3a | "Seven of nine below 1" (all nine) | F/F | R/R/**R** | R2 | |
| S42 | 129 | P4 | E.3c | "All 27 printed estimates" vs the job's four inputs | H/H | R/R/**R** | R7 | |
| S43 | 129 | P4 | Overview | "Two senior authors" (one is first author) | F/B | Xs/Xb/**Xs** | - | |
| S44 | 129 | P4 | C | "The doses that worked in [5]" (10 mg/kg did not) | F/A | S/Xs/**S** | - | P4 v15 C |
| S45 | 130 | P5 | B | "About SMD 0.4" vs E.1a 0.40-0.51 | F/F | R/R/**R** | R1 | |
| S46 | 130 | P5 | B | "The exception" when E.3 has several | F/F | S/S/**S** | - | |
| S47 | 130 | P5 | B | "Lower risk in five of six" (CI below 1 in four) | G/G | R/R/**R** | R3 | |
| S48 | 130 | P5 | E.3 | "Two of the five" incident-OA studies (row set needs judgement) | F/F | R/S/**S** | - | P5 v22 E.3 |
| S49 | 130 | P5 | E.3 | Case/control counts printed as exposure groups | L/L | Xs/Xs/**Xs** | - | |
| S50 | 130 | P5 | E.5a | Pooled safety estimates listed as job-checked | H/H | R/R/**R** | R7 | |
| S51 | 130 | P5 | E.5a | "Every printed estimate" included an unchecked CI | H/H | R/R/**R** | R7 | |
| S52 | 130 | P5 | E.2, E.5 | Alimoradi attrition credited to the wrong report | B/B | Xs/Xs/**Xs** | - | |
| S53 | 130 | P5 | E.5b | "Five distinct oral randomised reports" (trials) | F/F | S/S/**S** | - | |
| S54 | 130 | P5 | E.5 | Pan "0.43" unlabelled beside other values | F/F | R/R/**R** | R1 | |
| S55 | 130 | P5 | A | OAI called a diabetes cohort | L/L | Xs/Xs/**Xs** | - | |
| S56 | 131 | P4 | B | "Less likely" asserted for CIs crossing 1 | G/G | R/R/**R** | R3 | |
| S57 | 131 | P4 | E.1 | "No effect" for a CI spanning 0 | G/G | R/R/**R** | R3 | |
| S58 | 131 | P4 | E.6 | "Three outcome measures" not recomputable | F/F | S/S/**S** | - | |
| S59 | 132 | P5 | B | "No difference at 3 months" (CI spans 0) | G/G | R/R/**R** | R3 | |
| S60 | 132 | P5 | G | "No benefit at 3 months" | G/G | R/R/**R** | R3 | |
| S61 | 132 | P5 | B | "No different from SGLT-2 inhibitors" | G/G | R/R/**R** | R3 | |
| S62 | 132 | P5 | E.3 | "No differently from SGLT-2 inhibitors" | G/G | R/R/**R** | R3 | |
| S63 | 132 | P5 | C | Effect "absent" (non-significant) | G/G | R/R/**R** | R3 | |
| S64 | 132 | P5 | F | "No interaction by sex" from P values | G/G | R/R/**R** | R3 | |
| S65 | 132 | P5 | F | "Effects look stronger" with no CIs printed | G/G | R/S/**R** | R3 | P5 v23 F |
| S66 | 132 | P5 | E.5a | "The four meta-analyses that print CIs" (five) | H/H | R/R/**R** | R7 | |
| S67 | 132 | P5 | E.6 | Source list omits Drugs@FDA and PMC | E/E | R/R/**R** | R8 | |
| S68 | 132 | P5 | E.5 | "Every leave-one-out pool": two computed | H/H | R/R/**R** | R7 | |
| S69 | 133 | P5 | E.5 | KOOS and VAS SDs called "WOMAC pain SDs" | I/I | Xs/Xs/**Xs** | - | |
| S70 | 133 | P5 | E.1a | SMDs used one arm's SD | I/I | Xs/R/**Xs** | - | P5 v24 E.1a |
| S71 | 134 | P4 | E.3e | "About 50-60 patients per arm" (one arm 64) | I/F | Xs/Xs/**Xs** | - | |
| S72 | 134 | P4 | E.3e | Signed DiDs with opposite conventions side by side | I/I | Xs/Xs/**Xs** | - | |
| S73 | 134 | P4 | E.3e | VA heavy-drinker rows left out | E/E | Xs/Xs/**Xs** | - | |
| S74 | 134 | P4 | E.4 | Follow-up checks called "pre-registered" | L/L | R/R/**R** | R6 | |
| S75 | 135 | P5 | E.1a, E.5 | SMD sign convention unstated; both signs printed | I/I | S/R/**R** | R1b | P5 v25 E.1a |
| S76 | 135 | P5 | E.1a | 0.43 not credited as the trial's own SMD | B/I | Xs/Xs/**Xs** | - | |
| S77 | 135 | P5 | C | Animal-to-human doses on different body weights | I/I | R/R/**R** | R8 | |
| S78 | 135 | P5 | E.5b | Crossref deposits called "complete" | J/J | Xb/Xb/**Xb** | - | |
| S79 | 135 | P5 | E.5 | Pool's n 44/44 not stated beside the attrition | H/I | S/R/**S** | - | P5 v25 E.5 |
| S80 | 137 | P4 | C | Only the mouse dose translated; female-rat dose ~490 mg/day, above the 400 mg maximum | E/I | S/Xs/**Xs** | - | P4 v18 C |
| S81 | 137 | P4 | C | Single injected rodent dose translated to a daily oral dose unsaid | I/I | Xs/Xs/**Xs** | - | |
| S82 | 141 | P5 | E.2, ref 39 | Two of the 11 search records described without IDs (NCT07395895, NCT07738692) | J/- | R/-/**R** | R2b, R5b | P5 v26 E.2 |

## Counts
Recomputed from the table above (82 rows; S18 included as a false lead).

| Set | Input R | S | X | v3 coverage |
|---|---|---|---|---|
| 79 rows (plan headline; first labels) | 35 | 8 | 36 | - |
| 79 rows, **adjudicated** | **37** | 8 | 34 | 37 |
| 81 rows (+S80, S81), adjudicated | 37 | 8 | 36 | 37 |
| 82 rows (+S82), adjudicated | 38 | 8 | 36 | 38 |

- Adjudicated X subtypes, 82 rows: Xs 19 (S05 counted here), Xr 7, Xl 6, Xb 4 = 36.
- Coverage by module (82 rows): R1 2 (S45, S54); R2 4 (S38-S41); R3 10 (S47, S56, S57, S59-S65); R4 3 (S21, S24, S25); R5 6 (S11, S22, S26, S28, S32, S33); R6 2 (S27, S74); R7 5 (S42, S50, S51, S66, S68); R8 2 (S67, S77); R1b 1 (S75); R2b 2 (S36, S82); R5b 2 (S35, S82). 39 module hits on 38 rows (S82 is caught by two modules).
- Reference class (first label), 82 rows: A 4; B 3; C 7; D 2; E 10; F 13; G 10; H 6; I 8; J 12; K 3; L 4 = 82.
- These match plan v3 section 2 (79: R 37, S 8, X 34; 81: R 37, S 8, X 36; 82: R 38, S 8, X 36; coverage 38) and the second-labelling file's first-label class marginals for 81 rows (E 10, I 8). No figure in the plan needs changing.
- **Thin modules:** R1b has one development row and R2b/R5b two each, and those rows are the ones the rules were designed from. Development recall on them is close to 1 by construction and says nothing. Only H-A (8 planted mutations per module) and H-B test them.

## U rows (differences recorded but not counted)
U01-U10 as in v1. U11 (run 137, P4): BSA factors used without naming their source. Excluded from development recall; a checker that flags them gets no credit and no penalty.

## Known limits
- All labels come from one model family: two labellings and one non-blind adjudication. S82 was labelled once. A human labelling is still wanted before any agreement figure goes in a submission.
- The problem descriptions were written by the first labeller and carry hints, so the second labelling's agreement (input kappa 0.78) is an upper bound.
- Found-in versions were traced only for the 12 rows above; for the rest the Input label was not re-checked against the found-in version.
- The seed set holds only problems found by checks the same model family designed, so unknown failure types are missing by construction.
