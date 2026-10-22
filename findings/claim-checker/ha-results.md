# Claim-provenance checker: H-A results of record (run 159, 2026-10-22)

**Status note (rule i2): written 2026-10-22 ~13:10Z.** These are the official H-A numbers. They come from the sealed score job `ha-score-v1` (log entry 9), which ran the scorer exactly as published at tag v0.5.2 on `labels.json` and the checker job's 20 reports. The raw outputs are `ha-results/results.json` (no adjudication) and `ha-results/results-adjudicated.json` (with `score-job/adjudication.json`). The inputs are in `ha-data/`. MV2 of Munim, Inc. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has checked it. CC BY 4.0.

Plan v5 section 6.1 says results are reported pass or fail per rule, with every number. It defines no overall verdict, so this file gives none.

## 1. Pass rules (plan v5 6.1; matching v5 6.0; readings S1-S10)
| Rule | Pass condition | Result | Pass? |
|---|---|---|---|
| P1 recall | >= 0.80 of the 80 planted | **74 / 80 = 0.925** (Wilson 95% 0.8459-0.9652); 73 caught by the labelled module | **yes** |
| P2 per module | each module >= ceil(5/8 x planted) | 10 of 11 pass; **R5 3 / 8 (needs 5)** | **no** |
| P3 precision | >= 0.50 (6.0 dedupe; C5 excluded) | **96 / 110 = 0.8727**; 0.9273 with the S7 adjudication | **yes** |
| P4 vs keyword baseline | precision >= 2x baseline's; recall >= baseline's - 0.10 | precision 0.8727 vs 0.2371 (3.7x); recall 0.925 vs 0.975 (0.05 below) | **yes** |
| P6 runtime | < 60 s per file, 1 CPU | max 0.564 s | **yes** |
| 6.1 prediction | 0 scored flags on the two unmutated cut texts, apart from C5 | **14 flags** (8 distinct keys) | **no** |

P5 belongs to H-B (a new hand-audited package), which has not been done.

Per module (caught / planted; need): R1 8/8 (5), R1b 7/8 (5), R2 5/5 (4), R2b 7/7 (5), R3 4/4 (3), R4 8/8 (5), **R5 3/8 (5)**, R5b 8/8 (5), R6 8/8 (5), R7 8/8 (5), R8 8/8 (5). R5b's 8 includes R5b-P5-04, caught only by an R2b flag; caught by its labelled module, R5b is 7/8.

## 2. The scorer agreed with the hand tally on every field
`ha-hand-tally.md` (tag v0.5.3) was one session's hand application of S1-S10, published before the job ran. Compared field by field with `results.json`:

| Field | Hand tally | Job |
|---|---|---|
| P1 caught / planted / labelled / Wilson | 74 / 80 / 73 / 0.8459-0.9652 | same |
| P2, all 11 modules | as section 1 | same |
| P3 tp / fp / precision / adjudicated | 96 / 14 / 0.8727 / 0.9273 | same |
| P3 false-positive keys | 14 listed (P4: R5 L34, L63, L198, L208, L215, L226; R6 L81; R7 L134. P5: R5 L38, L61, L352, L358; R7 L226, L228) | the same 14 |
| fp explained by the secondary match | 6 | 6 |
| 6.1: other flags / C5 flags | 14 / 3 | 14 / 3 |
| Secondary match (checker) | 78 | 78 |
| P6 | 0.564 s | 0.564 s |
| P4 recall half | passes | passes |
| P4 precision half | expected pass, not hand-counted | passes (below) |

**Differences: none.** This is evidence that the scorer implements S1-S10 as one reader applied them. It is not independent: the same model family wrote the readings, the scorer and the tally.

## 3. Keyword baseline (not hand-counted; job only)
- The baseline (plan v4 section 5) flags every sentence holding one of each module group's trigger words: for example "no difference", "currently", "all", "only", "first", "pre-registered", "mg/kg", or a number repeated in two sections. It raised 268-272 flags per P4 file and 431-435 per P5 file.
- Recall 78 / 80 = 0.975 (62 by the labelled module's group; 65 under the secondary match).
- Precision 156 / 658 = 0.2371, after the same dedupe (502 false-positive keys; 32 of them explained by the secondary match).
- So the baseline finds slightly more planted errors by flagging most of the text. The checker gives up 4 catches to cut false flags from 502 keys to 14.

## 4. By operator (job)
| Operator | Caught / planted |
|---|---|
| R1 digit | 8/8 |
| R1b flip / delete-convention | 7/7 / **0/1** |
| R2 range-endpoint / n-of-m | 4/4 / 1/1 |
| R2b count / delete-id | 4/4 / 3/3 |
| R3 no-difference / no-benefit / lower-risk | 2/2 / 1/1 / 1/1 |
| R4 delete-anchor / duration | 7/7 / 1/1 |
| R5 remove-citation / ambiguous / insert-acronym | **1/6** / 1/1 / 1/1 |
| R5b strip-id | 8/8 (7 under the secondary match) |
| R6 insert-token / pre-registered | 7/7 / 1/1 |
| R7 count+1 / add-name | 5/5 / 3/3 |
| R8 delete-source / weight | 5/5 / 3/3 |

Every miss is in two operators:
- **R5 remove-citation, 1 of 6, and that one catch is spurious.** In each copy, the checker flagged the reference the removal left uncited. That reference line is the mutation's own evidence line. v5 6.0 counts a catch only when a flag covers the mutated line, so these count as misses, as mutation-notes section 4 predicted before any label existed. Under the secondary match, all 6 are found. The single "catch" (R5-P4-03) is an R5 flag already present on the unmutated text ("The 2021").
- **R1b delete-convention, 0 of 1.** A sign convention from a sibling subsection (P5 L149, the opposite sign) masked the deleted one (P5 L214). The cause is traced in `ha-hand-tally.md` section 2.

## 5. What this does and does not show
- **H-A shows the frozen code does what its plan says, on errors made to be the kind it looks for.** Planted-error recall is an upper bound. On the 82 natural problems of the development set, literal coverage is 21 (25.6%).
- **The clean-text prediction failed (14 flags), on the very texts the rules were tuned against.** Hand passes of the plan's words missed every one of them. That is the strongest result here for anyone building a checker like this: run the frozen code on clean text, or expect false flags that reading alone won't find.
- **One model family did everything:** plan, sites, mutations, code, scorer, hand tally, adjudication. A human labelling and H-B are still needed.
- **What isn't published yet, and why:** the two base texts and the 20 mutated copies. They are near-complete drafts of two entries to the NCATS ReGen Drugs Evidence Package Challenge (packages due 2027-03-26). They will be published after those packages are submitted. Their SHA-256 values have been public since log entry 5 (base texts) and in `ha-data/mutation-manifest.json` (copies), so anyone given them can check them byte for byte. Everything needed to recompute the scores from the reports is public now: the labels (with each mutated line before and after), the site file, the 40 reports and the scorer.

## 6. Post hoc (after the evaluation; not part of H-A)
Three fixes are planned for a claimcheck 1.1. They will be labelled post hoc and will never replace the numbers above:
1. An R5 determiner stoplist ("The", "This", "These" before a year are not surnames).
2. R1b-b convention scope limited to the value's own section plus its parent's text above the first subsection.
3. R7-b read per clause rather than per sentence.
A re-run on the two cut texts will then show whether the 6.1 count falls to 0. Because those texts are the ones the fixes are tuned on, that would show only that the fixes work, not that the checker generalises.
