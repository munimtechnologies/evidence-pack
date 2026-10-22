# Claim-provenance checker: evaluation plan and development set

MV2 of Munim, Inc. is building a deterministic checker that flags silent claim-provenance problems in drug-evidence summaries. Examples: a stated record count that doesn't match the registry IDs listed; a date-relative claim that will be false by the deadline; a "no difference" next to a CI that excludes the null; a reference that is never cited. It is planned as one feature of an entry to AHRQ's Clinical Evidence Synthesis Transformation Challenge.

**This folder is the pre-registration. Plan v7, the last amendment, was committed before any checker code existed.** The code is in `claimcheck/` at the repository root. **It is frozen at claimcheck 1.0.0 (tag v0.5.0): the code as committed at de3066f (tag v0.4.47), with only the version number changed. Log entry 6 records the freeze.** The planted-error copies exist (log entry 7: 80 mutations, labels hashed). The scorer was published before the checker ran on any of them (tag v0.5.2). **The checker has now run (log entry 8), and a hand tally of the score is published (`ha-hand-tally.md`) before the sealed scorer runs: planted-error recall 74 of 80, R5 fails its per-module bar, precision 0.873. The clean-text prediction failed, with 14 false flags.** The official result will be the score job's output. AI agents (Claude, claude-opus-5-5) research and draft this work in MV2's name. No human has reviewed any file here yet. Licence: CC BY 4.0 (text and data); code Apache-2.0.

## What is here
| File | What it is |
|---|---|
| `ha-hand-tally.md` | **The H-A hand tally (P1-P6, the 6.1 prediction, every catch and miss, forecast grades), written before the sealed scorer runs.** |
| `eval-plan-v7.md` | **The plan in force, and the last amendment before code.** It defines R2 (tables), R7-a (counts vs lists) and R8 (dose conversions) literally, restates the prediction and sets the order of work. Everything it doesn't replace stands as in v6 and v5. |
| `eval-plan-v6.md` | Amendment: CI-tuple grammar, R1, R1b-b and R5 definitions, literal coverage. |
| `eval-plan-v5.md` | Module definitions, held-out sets, mutation layout, matching and pass rules, limits. |
| `eval-plan-v1.md` ... `eval-plan-v4.md` | Earlier drafts, unedited, kept for the record. |
| `mutation-notes.md`, `mutation-job/` | How the planted-error (H-A) copies are made, published before the job ran, and a matching defect predicted before any label existed. |
| `scoring-notes.md`, `score-job/` | How H-A is scored (readings S1-S10) and our forecasts, published before the checker ran on the copies. `score-job/adjudication.json` is the S7 list (log entry 8). |
| `checker-job/` | The sealed job that ran claimcheck 1.0.0 on the 20 texts. |
| `seed-set-v2.md`, `seed-set-v2.csv` | Development set: 82 naturally occurring problems found while auditing two draft evidence packages (package 4, spironolactone for alcohol use disorder; package 5, metformin for knee osteoarthritis). Each row has two AI labellings and an adjudicated label for the input needed to catch it. |
| `seed-set-v1.md` | The first version of the set (79 rows). |
| `seed-set-second-labels-blind.md` | The blind second labelling (input kappa 0.78, same model family). |
| `seed-set-input-adjudication.md` | The input-label adjudication. |
| `hand-pass-r2b-r5b-run141.md`, `hand-pass-r2b-r5b-run144.md` | Literal hand passes of the registry-count and registry-ID rules. |
| `hand-pass-r4-run146.md` | Literal hand pass of the date rule. |
| `operator-vs-detector-run147.md` | For each module: does the planted-error operator produce text the detector reads? (Its R7-a reading was looser than the rule; see the run-151 note.) |
| `r5-superlative-count-run148.md` | Full hand count of the superlative rule (which led to dropping it). |
| `hand-pass-r1-r5-coverage-run150.md` | Literal passes of the CI-tuple grammar and R5's citation halves on both texts, and the trace of the seed rows against the package versions they were found in. |
| `hand-pass-r2-r7a-r8-run151.md` | Literal passes of the table rule, the count-vs-list rule and the dose rule on both texts. |
| `exposure-and-tuning-log.md` | Append-only log of what the authors saw and tuned, and when. **Entry 5 holds the SHA-256 hashes of the two base texts, entry 6 records the code freeze, entry 7 the mutation job and entry 8 the checker job.** |
| `../../claimcheck/CODING-NOTES.md` | The 59 readings the code takes where the plan's words allowed more than one implementation, fixed before freeze, and the plan files and job manifest the held-out run will use. |

The two evidence packages these files refer to are unpublished drafts for the NCATS ReGen Drugs Evidence Package Challenge.
- Line numbers refer to package 5 v27/v28 (cut at line 367; v28 keeps v27's line numbers) and package 4 v18/v19 (cut at line 227).
- The SHA-256 hashes of the final base texts (package 4 v19, package 5 v28), whole and cut, were recorded by a sealed job on 2026-10-21 and are in log entry 5. The texts, the mutated copies, the site file and the labels stay unpublished until the sealed scorer has run; anyone given them later can check them against the logged hashes.

## Path map
The files cite each other by the local work-folder paths they were drafted under:

| Local path | Here |
|---|---|
| 20261021T002117Z-medicine/ahrq-checker-eval-prereg-v1.md | eval-plan-v1.md |
| 20261021T042443Z-medicine/ahrq-checker-eval-prereg-v2.md | eval-plan-v2.md |
| 20261021T070512Z-medicine/ahrq-checker-eval-prereg-v3.md | eval-plan-v3.md |
| 20261021T101610Z-medicine/ahrq-checker-eval-prereg-v4.md | eval-plan-v4.md |
| 20261021T170928Z-medicine/ahrq-checker-eval-prereg-v5.md | eval-plan-v5.md |
| 20261021T002117Z-medicine/claim-provenance-seed-set-v1.md | seed-set-v1.md |
| 20261021T080721Z-medicine/claim-provenance-seed-set-v2.md / .csv | seed-set-v2.md / .csv |
| 20261021T022123Z-medicine/seed-set-second-labels-blind.md | seed-set-second-labels-blind.md |
| 20261021T032436Z-medicine/seed-set-input-adjudication.md | seed-set-input-adjudication.md |
| 20261021T060514Z-medicine/package5-r2b-r5b-check.md | hand-pass-r2b-r5b-run141.md |
| 20261021T091352Z-medicine/package5-v27-r2b-r5b-hand-pass.md | hand-pass-r2b-r5b-run144.md |
| 20261021T111356Z-medicine/r4-literal-hand-pass.md | hand-pass-r4-run146.md |
| 20261021T123413Z-medicine/operator-vs-detector-check.md | operator-vs-detector-run147.md |
| 20261021T142649Z-medicine/r5-superlative-hand-count.md | r5-superlative-count-run148.md |

Other local paths mentioned in these files (package drafts and their check files) aren't published.

## Honest limits, in one place
- Every label, rule and prediction so far comes from one model family. A human labelling is still wanted.
- The rules were refined by hand against the same two texts that serve as planted-error base texts, so those texts are not a clean false-positive test. Plan v5, v6 and v7 section 9 list which rules were tuned. Even so, the frozen code raised 14 false flags on them (log entry 8).
- **Traced literally against the texts they were found in, the deterministic modules cover only 21 of the 82 development problems (25.6%).** Plan v5 had estimated 26 to 33 from one-line descriptions. Most problems need a semantic judgement or an outside source (a cited paper, a registry or a literature search), and v1 doesn't attempt those. **The high planted-error recall (74 of 80, hand tally) is an upper bound: the planted errors were made to be the kind these modules look for.**
- Every literal hand pass so far has found a defect in the rules it read. Loose readings and one-line descriptions overstated coverage three times. From v7 on, defects found after code freeze are reported, not fixed by new plan versions.
- Coding the plan needed 59 choices the plan doesn't make (for example, how a URL is recognised). They are listed in `claimcheck/CODING-NOTES.md`, fixed before the code runs on any base text. In four of them the code follows the literal text where it and the evident intent diverge.
- The planted errors were placed by hand-listed sites written by the same model family that wrote the checker, so H-A tests the code against its authors' own reading of the plan. Only H-B (a package not yet written) and a human labelling can test it beyond that.
