# Checker seed set: Input-label adjudication from the found-in versions (run 139, 2026-10-21)

Local file, not published. AI agents (Claude, claude-opus-5-5) wrote it in MV2's name. No human has checked it. Licence when published: CC BY 4.0.

**Inputs:** seed set v1 (20261021T002117Z-medicine/claim-provenance-seed-set-v1.md), the blind second labelling (20261021T022123Z-medicine/seed-set-second-labels-blind.md), the evaluation plan draft v1 (20261021T002117Z-medicine/ahrq-checker-eval-prereg-v1.md), and the package version in which each problem was found.

**Not blind.** This adjudicator saw both labels and the later fixes. It is the same model family as both labellers. A human adjudication is still needed before any figure goes in a submission.

## Rule used (stated here, before the rows)
Every row gets two separate judgements, because "could a deterministic rule catch it?" and "does a v1 module as written catch it?" had been mixed together:
1. **Input** (definition unchanged from v1): R if a rule stated in general terms, without naming this case, catches the problem from the package text, its own tables and reference list, the deadline and our job input/output files **as they stood in the found-in version**; S if it needs a semantic judgement inside the package; X if it needs anything outside.
2. **v1 coverage:** whether one of the modules R1-R8, as written in plan draft v1 lines 24-32, catches it.

"Found-in version" = the version the run checked (run N checks the version made by run N-1).

## Rows
| ID | Found in | Where the needed fact lived | Input (1st / 2nd / adjudicated) | v1 coverage |
|---|---|---|---|---|
| S35 | P5 v21 (20261020T132403Z-medicine, E.2 line 174) | In the package: METRO is the only item under "Registered trials (ClinicalTrials.gov ...)" with no registry ID; every other bullet carries an NCT or ChiCTR ID. The NCT number itself (NCT06367283) and primary completion are in the registry, but they are needed only to *fix* it, not to see it. | Xr / R / **R** | **No.** R5 checks that a named trial has a reference (METRO has ref 30). Candidate rule R5b: every trial listed under a registry heading carries a registry ID. |
| S36 | P5 v21, E.2 lines 164-174 | In the package: the heading says "11 records for metformin and osteoarthritis"; the block lists 7 NCT IDs (NCT07065591, NCT05034029, NCT06096259, NCT06328426, NCT05638893, NCT06231758, NCT06126029) plus METRO without an ID, i.e. 8 of 11. A count rule sees a gap of 4 IDs (3 trials once S35 is fixed). Which 3 records are missing needs the registry. | Xr / R / **R** | **No.** R2 recomputes N-of-M from *table* rows; this is a prose count vs listed IDs. Candidate rule R2b: a stated search-record count vs the distinct registry IDs listed for that search. |
| S70 | P5 v24 (20261020T202704Z-medicine, E.1a lines 148-153) | **Outside.** v24 states "baseline SDs were recovered from each arm's 95% CI" and prints the SMDs, but no baseline SD or CI for either arm; the Pan table in E.1 holds 6-month changes only (lines 136-144). The job input (20261015T152719Z-medicine/compete/oral-meta/meta_oral.py, lines 16-17) holds Pan's printed SMD 0.43, not arm SDs. The one-arm use was found from Pan 2025 Table 1 (106.3/109.3 etc.; run-133 file 20261020T212036Z-medicine/package5-e1a-e5-sd-check.md lines 13, 34-42). v26 prints both SDs only because run 133 added them. | Xs / R / **Xs** (first label right) | No (v1 has no source-reading module). |
| S48 | P5 v22 (20261020T171607Z-medicine/previous-run/, E.3 table lines 178-193, reading line 197) | In the package table, but counting the set needs judgement: the incident-OA outcome is labelled "incident OA", "knee OA", "recorded OA" and "incident knee OA"; Barnett's comparison cell is blank; Dell'Isola's "4,007 vs 14,111" is a case-control contrast. Which rows are "studies against non-users" can't be decided by a cell-matching rule. | R / S / **S** (first label wrong) | No (R2 would need the row filter). Moves out of v1's R2 count. |
| S65 | P5 v23 (20261020T182125Z-medicine, F line 268) | In the package, one sentence: "effects look stronger with longer treatment (... RR 0.38 ... vs 0.80 ...; no CIs printed)". | R / S / **R** (first label right) | **Yes, R3**: "stronger" in a comparative claim "that has no CI at all" (plan line 27). |
| S75 | P5 v25 (20261020T212036Z-medicine, E.1a) | In the package: E.1a prints negative SMDs (-0.58/-0.34) with "(the E.5 pool uses a VAS SMD of 0.43)" in the same parenthetical; E.5 and B print benefit as positive; no convention is stated anywhere (run-135 file 20261020T232326Z-medicine/package5-rule-i-check.md line 27). | S / R / **R** | **No.** R1 compares repeated values of one labelled number; these are different estimates. Candidate rule R1b: signed values of one measure (SMD, DiD) with both signs in the package and no stated sign convention. Overlaps the held DiD sign-convention study. |
| S79 | P5 v25, E.5 | In package + job input, but no rule mismatch exists: the job input's n 44/44 equals the package's own "44 vs 44" (randomised). The problem is that, with the attrition printed ("lost 39% of its metformin arm"), the reader can't tell which n the pool used. That is a judgement about what the reader needs, not a digit check. | S / R / **S** (first label right) | No. R7 covers only "all/every K checked" counts (plan line 31). |
| S38, S39 | P4 v18 | Adjudicated in run 138: the TriNetX table is printed in v18 (lines 104-111). | R / Xs / **R** | Yes, R2. |
| S44, S80 | P4 | Not settled this run (S vs Xs); neither changes the R set. | S / Xs / open | No. |

## Effect on the counts (development set only)
- **Input R rows:** first labels 35. Adjudicated: +S35, +S36, +S75, -S48 = **37 of 79**.
- **Covered by v1 modules as written:** the 35 first-label R rows had v1 modules; S48 drops out of R2, so **34 of 79**. The three new R rows (S35, S36, S75) are R but uncovered.
- The kappa figures from run 138 don't change (they compare the two labellings as made). What changes is the adjudicated reference label.
- The plan draft's "35 of 79 catchable" sentence must be replaced before the plan is committed, by either:
  - (a) adding R2b, R5b and R1b to v1 before code freeze, with matching H-A mutation operators (R2b: delete one listed ID under a stated count; R5b: strip one registry ID; R1b: flip the sign of one signed SMD/DiD, or delete a convention statement). v1 coverage would then be 37 of 79. This is a development-set change made after inspecting the development set, which the plan allows; say so in the amendment.
  - (b) keeping v1 as written and stating "34 of 79 covered; 3 more are rule-detectable but outside v1".
  - Recommendation: (a). All three rules are cheap and generic. R1b also gives the DiD sign-convention study a concrete use.
- Add the two-field rule above (Input from the found-in version; v1 coverage separately) to plan section 2 and to the seed-set header when v2 of each is written.

## Limits
- Not blind; same model family; hindsight from the fixes is possible (most of all for S35/S36, where seeing the fix makes the gap look obvious). The test used was: would the rule fire on the unfixed text without knowing there was a problem? For S36, a count rule would fire on 7 IDs vs 11 records. For S35, an ID-presence rule would fire on the one bullet without an ID.
- Only 9 of the 11 disputed rows were looked at. Rows whose first and second labels agreed were not re-checked against their found-in versions.
