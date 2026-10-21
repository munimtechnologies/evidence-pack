# Claim-provenance checker: labelled seed set v1 (run 136, 2026-10-21)

Local file, not published. AI agents (Claude, claude-opus-5-5) compiled it in MV2's name from the check files of runs 115-135. No human has checked it. Licence when published: CC BY 4.0.

**What it is:** every silent problem that the hand checks of runs 115-135 found in MV2's two NCATS ReGen evidence packages (P4 spironolactone-AUD, P5 metformin-knee OA). Each row is one problem as the check file recorded it, with the section, a class, the input a checker would need to catch it, and its v1 module. None of the 79 changed an estimate. All were fixed in the next local version.

**Use:** this is the DEVELOPMENT set for the checker. Recall measured on it is development recall, never an evaluation result (see ahrq-checker-eval-prereg-v1.md).

## Reconciliation with the running tally (rule h3 applied to our own count)
- The playbook says 79 problems. Rebuilt run by run from the check files: 115-118: 6; 119: 5; 120: 1; 121: 2; 122: 1; 123: 3; 124: 1; 125: 3; 126: 5; 127: 4; 128: 6; 129: 7; 130: 11; 131: 3; 132: 10; 133: 2; 134: 4; 135: 5. That sums to **79**.
- **Runs 115-118 are partly inferred.** Those check files list more differences than the tally counted. For example, the package 4 gate-5 file lists 7 label differences, and only the misquote appears to have been counted. The 6 rows below are the reading that matches the run-119 note ("6 earlier"). The uncounted differences are listed separately (U rows) and are not part of the 79.
- **One counted problem was not an error.** S18 (Mohammed year, 2014 vs 2017) was resolved in run 124: the journal page gives Vol. 23 No. 2 (2014), and Crossref's `issued` field holds the 2017 online date. The citation was right. **True problems: 78.** S18 stays in the set, labelled as a false lead of the checking method.
- **The playbook's class breakdown sums to 80, not 79.** 12+9+9+7+6+5+4+4+3+3+3+3+2 = 70, plus 10 singletons, makes 80. The likely cause is one item counted in two classes (run 131 item 1 is both CI-vs-wording and range). This file uses one class per row.
- Item denominators (~771 items checked) are hand estimates and are not rebuilt here.

## Labels
- **Class** (one per row): A quote fidelity / scope lost at a cut; B attribution to the wrong document or report; C exclusive, negative or "first" claim vs search/registry; D registry-field reading; E completeness (missing studies, contrary evidence, records, results, sources); F cross-section number / summary range / N of M / count; G directional wording vs CI; H "checked"/"every" claim vs the tool's real input or computed set; I re-derivation (method, instrument, sign convention, dose basis, threshold-as-observation); J reference hygiene (uncited claim or reference, identifiability, collision, erratum/retraction, deposit gaps); K date-relative claim false at the deadline; L labels (internal, design, pre-registration status, scope wording vs the source).
- **Input** (what a checker needs to see the problem): **R** = a deterministic rule over the package text, its own tables and reference list, the submission deadline and our job input/output files; **S** = a semantic comparison inside the package (LLM-assisted); **X** = something outside the package: the cited source's text or tables (Xs), a registry (Xr), a literature search (Xl) or a bibliographic index (Xb).
- **v1 module** (R rows only): R1 same-quantity digits; R2 range / N-of-M vs table rows; R3 directional wording vs CI; R4 date-relative; R5 citation lint; R6 internal label / pre-registration status; R7 claim vs job I/O; R8 source list and dose basis.

## Rows
| ID | Run | Pkg | Section | Problem (short) | Class | Input | v1 |
|---|---|---|---|---|---|---|---|
| S01 | 115 | P5 | D | "rose about linearly" loosened the label (dose-associated increase; "appeared linear" only after multiple doses) | A | Xs | - |
| S02 | 116 | P4 | Overview | Quoted label sentence dropped "or titration" | A | Xs | - |
| S03 | 117 | P5 | A | "The 2026 update's only new recommendation": true of the summary's labels, false against ACR's press release (two) | C | Xl | - |
| S04 | 117 | P5 | A | Fu 2024 MVMR verification left out (understated a cited source's evidence) | E | Xs | - |
| S05 | 118 | P4 | E.5 | Design-abstract quotes credited to the trial registry record | B | Xs+Xr | - |
| S06 | 118 | P4 | E.3e | Authors' 0.5 threshold written as observed associations "up to about 0.5" (max was 0.31) | I | Xs | - |
| S07 | 119 | P5 | A | "First positive placebo-controlled trial ... (JAMA 2025)": two earlier positive trials | C | Xl | - |
| S08 | 119 | P5 | E.2, B | "First registered independent replication"; "a replication is registered" (two; NCT07065591 earlier) | C | Xr | - |
| S09 | 119 | P5 | E.2 | "Only registered placebo trial with a structural primary": overbroad (PIKASO, NCT06328426) | C | Xr | - |
| S10 | 119 | P5 | D | "No human PK/PD study of metformin for pain exists" (Kialka 2016) | C | Xl | - |
| S11 | 119 | P5 | F | "The most common co-medication in knee OA": superlative with no source | J | R | R5 |
| S12 | 120 | P5 | E.3, E.5 | Jiang 2025 NMA and Chen S 2022 missing (also Hatano 2025, Haj Shehadeh 2025) | E | Xl | - |
| S13 | 121 | P4 | C | Animal section one-sided: four earlier null studies missing | E | Xl | - |
| S14 | 121 | P4 | A | Amygdala mechanism sentence uncited | J | S | - |
| S15 | 122 | P5 | C | Animal section one-sided: Minton 2021 and two retracted supportive studies missing | E | Xl | - |
| S16 | 123 | P5 | ref 47 | Minton 2021 erratum not cited | J | Xb | - |
| S17 | 123 | P5 | C | A cited synthesis (Yao 2026) cites a retracted study; not noted | J | Xb | - |
| S18 | 123 | P5 | ref 23 | Mohammed year 2014 vs 2017 flagged. **Not an error** (Crossref online date; resolved run 124) | J | Xb | - |
| S19 | 124 | P5 | B | Summary kept "two animal studies point the same way" after C was rewritten | F | S | - |
| S20 | 125 | P4 | A | Pince quote cut before "in ASUD" | A | Xs | - |
| S21 | 125 | P4 | A | "66 years on the US market" false from 2027-01-21 | K | R | R4 |
| S22 | 125 | P4 | D | Named trial RALES uncited | J | R | R5 |
| S23 | 126 | P5 | C | Minton quote cut dropped "added to rapamycin" | A | Xs | - |
| S24 | 126 | P5 | E.2 | "Unreported nearly 22 months after completion" false at the deadline | K | R | R4 |
| S25 | 126 | P5 | A | "Full manuscript not yet published" unanchored | K | R | R4 |
| S26 | 126 | P5 | E.5b | "Zhang 2022" collides with package ref 15 (a different Zhang 2022) | J | R | R5 |
| S27 | 126 | P5 | E.5a, E.6 | Internal labels "version 5", "version 18" in submission text | L | R | R6 |
| S28 | 127 | P4 | refs | Ref 12 never cited | J | R | R5 |
| S29 | 127 | P4 | E.5 | "Terminated 2017": last-update date read as end date (ran 1995-2003) | D | Xr | - |
| S30 | 127 | P4 | E.5 | "Are not AUD trials": one lists Alcoholism as a condition | C | Xr | - |
| S31 | 127 | P4 | A | "The only registered clinical studies are ..." too broad | C | Xr | - |
| S32 | 128 | P5 | A | Ref 32 (Kolasinski 2020) cited only by guideline name | J | R | R5 |
| S33 | 128 | P5 | A | Ref 34 (Bannuru 2019) cited only as "OARSI 2019" | J | R | R5 |
| S34 | 128 | P5 | E.2 | NCT06126029 not described as a second unreported placebo trial | E | Xr | - |
| S35 | 128 | P5 | E.2 | METRO given without registry ID or primary completion | E | Xr | - |
| S36 | 128 | P5 | E.2 | 3 of the 11 search records unaccounted for | E | Xr | - |
| S37 | 128 | P5 | E.2 | NCT07065591 joint-replacement-referral criterion missing ("closest in design") | D | Xr | - |
| S38 | 129 | P4 | E.3a | "10.4% in eight comparisons" (10.4% in six; range 9.9-10.4) | F | R | R2 |
| S39 | 129 | P4 | B | "10.4% vs 4.4-7.4%" paired a column maximum with the full comparator range | F | R | R2 |
| S40 | 129 | P4 | B | "HR 0.77-0.81 in seven of nine" (eight in range; CI < 1 in seven) | F | R | R2 |
| S41 | 129 | P4 | E.3a | "Seven of nine below 1" (all nine point estimates below 1) | F | R | R2 |
| S42 | 129 | P4 | E.3c | "All 27 printed estimates" vs the job's actual four Palzes inputs | H | R | R7 |
| S43 | 129 | P4 | Overview | "Two senior authors" (one is first author) | F | Xs | - |
| S44 | 129 | P4 | C | "The doses that worked in [5]" (10 mg/kg did not) | F | S | - |
| S45 | 130 | P5 | B | "About SMD 0.4" vs E.1a 0.40-0.51 | F | R | R1 |
| S46 | 130 | P5 | B | "The exception" when E.3 has several | F | S | - |
| S47 | 130 | P5 | B | "Lower joint-replacement risk in five of six" (CI below 1 in four) | G | R | R3 |
| S48 | 130 | P5 | E.3 | "Two of the five" incident-OA studies (four against non-use) | F | R | R2 |
| S49 | 130 | P5 | E.3 | Case and control counts printed in the Comparison column as exposure groups | L | Xs | - |
| S50 | 130 | P5 | E.5a | Pooled safety estimates listed as job-checked; not in the job | H | R | R7 |
| S51 | 130 | P5 | E.5a | "Every printed estimate" included the spending CI, never checked | H | R | R7 |
| S52 | 130 | P5 | E.2, E.5 | Alimoradi attrition credited to the 2025 report (it is the 2023 report's) | B | Xs | - |
| S53 | 130 | P5 | E.5b | "Five distinct oral randomised reports" (trials, not reports) | F | S | - |
| S54 | 130 | P5 | E.5 | Pan "0.43" unlabelled beside 0.63/0.34/0.40 elsewhere | F | R | R1 |
| S55 | 130 | P5 | A | OAI called a diabetes cohort | L | Xs | - |
| S56 | 131 | P4 | B | Intoxication range unscoped; "less likely" asserted for CIs crossing 1 | G | R | R3 |
| S57 | 131 | P4 | E.1 | "No effect" for a CI spanning 0 | G | R | R3 |
| S58 | 131 | P4 | E.6 | "Three outcome measures" not recomputable (four or five) | F | S | - |
| S59 | 132 | P5 | B | "No difference at 3 months" (CI spans 0) | G | R | R3 |
| S60 | 132 | P5 | G | "No benefit at 3 months" | G | R | R3 |
| S61 | 132 | P5 | B | "No different from SGLT-2 inhibitors" (1.03, 0.89-1.19) | G | R | R3 |
| S62 | 132 | P5 | E.3 | "No differently from SGLT-2 inhibitors" | G | R | R3 |
| S63 | 132 | P5 | C | Effect "absent" in the spontaneous model (non-significant) | G | R | R3 |
| S64 | 132 | P5 | F | "No interaction by sex" from P values | G | R | R3 |
| S65 | 132 | P5 | F | "Effects look stronger with longer treatment" (no CIs printed) | G | R | R3 |
| S66 | 132 | P5 | E.5a | "The four meta-analyses that print CIs" (five print CIs; job has four) | H | R | R7 |
| S67 | 132 | P5 | E.6 | Source list omits Drugs@FDA and PMC full text, both used | E | R | R8 |
| S68 | 132 | P5 | E.5 | "Every leave-one-out pool": only the two keeping Pan were computed | H | R | R7 |
| S69 | 133 | P5 | E.5 | KOOS and VAS pain SDs called "WOMAC pain SDs" | I | Xs | - |
| S70 | 133 | P5 | E.1a | SMDs used one arm's SD; stated method implies both | I | Xs | - |
| S71 | 134 | P4 | E.3e | "About 50-60 patients per arm" (one arm 64) | I | Xs | - |
| S72 | 134 | P4 | E.3e | Signed DiDs from tables with opposite conventions printed side by side | I | Xs | - |
| S73 | 134 | P4 | E.3e | Precise VA heavy-drinker rows of the cited result left out | E | Xs | - |
| S74 | 134 | P4 | E.4 | Follow-up checks called "pre-registered"; plan written after the first result | L | R | R6 |
| S75 | 135 | P5 | E.1a, E.5 | SMD sign convention unstated; Pan's +0.43 beside our -0.58/-0.34 | I | S | - |
| S76 | 135 | P5 | E.1a | 0.43 not credited as the trial's own model-based SMD; -0.34 method unstated | B | Xs | - |
| S77 | 135 | P5 | C | Animal-to-human doses on different body weights (60 vs 70 kg) | I | R | R8 |
| S78 | 135 | P5 | E.5b | Crossref deposits called "complete" despite key gaps | J | Xb | - |
| S79 | 135 | P5 | E.5 | Pool enters Alimoradi with n 44/44; not stated | H | S | - |

## Counts (one class per row; S18 included)
- By class: A 4; B 3; C 7; D 2; E 9; F 13; G 10; H 6; I 7; J 11; K 3; L 4 = **79**.
- By input: **R 35 (44%)**; S 8 (10%); X 36 (46%): Xs 17, Xr 9, Xl 6, Xb 4 (S05, which needs both a source and a registry, is counted under Xs).
- R rows by v1 module: R1 2; R2 5; R3 10; R4 3; R5 6; R6 2; R7 5; R8 2 = 35.
- By package: P4 26, P5 53. The difference reflects P5's longer text and two extra passes (runs 128 and 133); it says nothing about drafting quality.
- **Reading:** under half the problems (35 of 79) could in principle be caught from the package and our own job files alone. 36 needed something the package doesn't contain: a cited table, a registry record, a fresh search or a bibliographic index. A checker that reads only the draft can't reach those, so its X modules matter as much as its rules. Directional wording vs CI (10) and cross-section numbers (13) are the biggest R-detectable groups.

## U rows: differences recorded but not counted in the 79 (for completeness)
- U01-U06 (run 116, P4, label read-back): "most common adverse reaction" placed in 5.4/6 when it is in Highlights; "erectile dysfunction" not the label's term; initial dose 25-100 mg given as the dose range; 13.1 omissions (endometrial stromal polyps; mutagenicity wording "mixed"); tablet sizes said to be absent from the label; "in preparation for surgery" missing.
- U07 (run 118, P4): Pince 2023 paraphrased without its hedge ("may be"); later caught again as S20.
- U08 (run 119, P5): "no disease-modifying drug" vs "no approved disease-modifying drug".
- U09 (run 127, P4): ref 19 middle initials differ from Europe PMC's author string (human check).
- U10 (run 130, P5): "about 40% lower" vs 37.5% (tightened to "nearly 40%").
- The U rows are excluded from development recall. A checker that flags them gets no credit and no penalty on the seed set.

## Known limits
- The problems were found by the same model family that drafted the packages, using rules written after earlier misses. Problems neither the drafts nor the rules anticipated are absent by construction, so the seed set under-represents unknown failure types.
- One annotator (this session) assigned classes and inputs. Agreement hasn't been measured; the pre-registration plans a blinded second labelling.
- Short descriptions summarise the check files. The check file of each run is the record (paths in technical-notes.md, "Package provenance pointers").
