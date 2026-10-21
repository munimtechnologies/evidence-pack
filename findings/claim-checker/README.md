# Claim-provenance checker: evaluation plan and development set

MV2 of Munim, Inc. is building a deterministic checker that flags silent claim-provenance problems in drug-evidence summaries: a stated record count that doesn't match the registry IDs listed, a date-relative claim that will be false by the deadline, a "no difference" next to a CI that excludes the null, a reference that is never cited, and similar. It is planned as one feature of an entry to AHRQ's Clinical Evidence Synthesis Transformation Challenge.

**This folder is the pre-registration. It is committed before any checker code exists.** AI agents (Claude, claude-opus-5-5) research and draft this work in MV2's name. No human has reviewed any file here yet. Licence: CC BY 4.0 (text and data).

## What is here
| File | What it is |
|---|---|
| `eval-plan-v5.md` | **The plan in force.** Module definitions, held-out sets, mutation layout, matching and pass rules, restated predictions, limits. |
| `eval-plan-v1.md` ... `eval-plan-v4.md` | Earlier drafts, unedited, kept for the record. v5 says what changed and why. |
| `seed-set-v2.md`, `seed-set-v2.csv` | Development set: 82 naturally occurring problems found while auditing two draft evidence packages (package 4, spironolactone for alcohol use disorder; package 5, metformin for knee osteoarthritis). Each row has two AI labellings and an adjudicated label for the input needed to catch it. |
| `seed-set-v1.md` | The first version of the set (79 rows). |
| `seed-set-second-labels-blind.md` | The blind second labelling (input kappa 0.78, same model family). |
| `seed-set-input-adjudication.md` | The input-label adjudication. |
| `hand-pass-r2b-r5b-run141.md`, `hand-pass-r2b-r5b-run144.md` | Literal hand passes of the registry-count and registry-ID rules. |
| `hand-pass-r4-run146.md` | Literal hand pass of the date rule. |
| `operator-vs-detector-run147.md` | For each module: does the planted-error operator produce text the detector reads? |
| `r5-superlative-count-run148.md` | Full hand count of the superlative rule (which led to dropping it). |
| `exposure-and-tuning-log.md` | Append-only log of what the authors saw and tuned, and when. |

The two evidence packages these files refer to are unpublished drafts for the NCATS ReGen Drugs Evidence Package Challenge. Line numbers refer to package 5 v27 (cut at line 367) and package 4 v18 (cut at line 227). Their SHA-256 hashes, and those of the final base texts (package 4 v19, package 5 v28), will be logged before any planted-error job runs.

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
- The rules were refined by hand against the same two texts that serve as planted-error base texts, so those texts are not a clean false-positive test. Plan v5 section 9 lists which rules were tuned.
- Under v5, the deterministic modules cover only **26 to 33 of the 82** development problems. Most problems need a semantic judgement or an outside source (a cited paper, a registry or a literature search), and v1 doesn't attempt those.
