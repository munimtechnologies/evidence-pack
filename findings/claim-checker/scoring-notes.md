# Claim-provenance checker: how H-A is scored (run 157, 2026-10-22)

**Status note (rule i2): written 2026-10-22 ~09:45Z, after the mutation job ran (log entry 7) and before the checker job has run. No checker or baseline output exists. `labels.json` has not been opened; the scorer was written from the label format in `mutation-job/mutate.py`.** These are readings of plan v5 section 6 (with v4's P3 and P4 text, and v7 6.1), not plan amendments. MV2 of Munim, Inc. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has checked it. Text CC BY 4.0; the code (`score-job/score.py`, `score-job/test_score.py`) is Apache-2.0.

## 1. What the scorer reads
- `labels.json` from the mutation job (SHA-256 `2b6948969e8145ddfc8494dec4b76a665b122151f9036711475c951ec08f091b`, log entry 7). It refuses any other file.
- The checker job's `out/`: `summary.json`, `checker/<file>.json` (claimcheck 1.0.0) and `baseline/<file>.json` (the keyword baseline), for the 18 mutated copies and the 2 unmutated cut texts. It refuses to score if the checker job reported a problem, if a report doesn't print "claimcheck 1.0.0", or if any report's SHA-256 differs from the one the checker job printed.
- Optionally, an adjudication file (section 2, S7).
- It shares no code with `claimcheck` or the mutation job, and it needs no base text.

## 2. Readings (S1-S10)
- **S1, info flags.** Only flags marked scored count. Unscored info output (the dropped superlative rule, unbound R4-a spans) counts for neither recall nor precision.
- **S2, a flag's lines.** The primary line plus the evidence lines. Baseline flags have no evidence lines, so only their sentence's line counts.
- **S3, catch (P1, P2).** A mutation is caught when any scored flag in the same copy has the mutated line among its lines (v5 6.0). Catches by the labelled module are also reported. A baseline flag belongs to every module its group names ("R2/R2b" is both).
- **S4, secondary match (descriptive, fixed in mutation-notes section 4).** A flag of the labelled module whose lines include the mutated line or one of that mutation's expected evidence lines. Reported per module and per operator. It is not a pass rule. The number of false positives it would explain is reported too.
- **S5, C5.** R5 flags at P5 L248 and L252 (the two pre-registered residual flags, v5 4.1) count for neither recall nor precision, on every copy. The same goes for baseline flags of a group that includes R5.
- **S6, precision (P3).**
  - P3 is computed on the mutated copies only; the cut texts are the 6.1 prediction.
  - **True positive:** a distinct (copy, module, primary line) whose lines include a line mutated in that copy.
  - **False positive:** a distinct (package, module, primary line) of every other flag (v5 6.0 dedupe). A flag on a line mutated only in another copy is a false positive.
  - Precision = true / (true + false).
- **S7, adjudication (v4 P3).** A false positive judged a real but unlisted problem counts as a true positive. The judgement is made by hand after scoring, listed one by one with reasons, and committed. P3 is reported before and after it. **P4 compares the checker and the baseline before adjudication**, since the baseline's sentence-level flags won't be adjudicated.
- **S8, P2 threshold:** ceil(5/8 x planted) catches per labelled module: R2 4 of 5, R2b 5 of 7, R3 3 of 4, R7 5 of 8, the rest 5 of 8.
- **S9, arithmetic.** Pass rules are compared in exact fractions (P1 recall >= 4/5, P3 >= 1/2, P4 checker precision >= 2 x baseline's and checker recall >= baseline recall - 1/10). Printed values are rounded to 4 places. P1's Wilson 95% interval uses z = 1.96.
- **S10, P6.** The largest checker runtime the checker job printed, over all 20 files, must be under 60 s (1 CPU).

## 3. Forecasts recorded before the checker runs (one model's guesses, not pass rules)
- **6.1 prediction (v7: 0 scored flags on the cut texts apart from C5):** we expect it to **fail**, with 1-5 other flags. Every literal hand pass so far found something the previous one missed. The likeliest sources are R7-b on P5 L228 (coding reading 57: named studies that may be absent from `recheck.json` labels) and R6-b (reading 53).
- **P2:** we expect **R5 to fail** (mutation-notes section 4: citation removals can't be matched). Whether R1b fails depends on how many of its 8 draws were convention deletions (2 of its 15 sites).
- **P1:** we expect overall recall between 0.70 and 0.85, so P1 (>= 0.80, at least 64 of 80) could go either way.
- **P4:** the baseline flags most sentences that hold a trigger word or a repeated number, so its recall may be high. We expect the precision half of P4 to pass and the recall half (checker recall no more than 0.10 below the baseline's) to be at risk.
- **P6:** pass. The checker makes regular-expression passes over about 50 KB of text per file, with no network.

## 4. Order from here
1. `ha-score-test-v1`: the scorer's unit tests (synthetic labels and flags only) in a sealed job.
2. Checker job `ha-check-v1`: the agent that works MV2's desktop copies the 20 texts, `manifest.json` and `recheck.json` (never `labels.json` or `report.json`) into the job's inputs and switches it on.
3. Score job: `score.py` on `labels.json` plus the checker job's `out/`. Results are committed whatever they show, with log entry 8, then the adjudication list.
