# Results: does an open biomedical cross-encoder help the SPARK Task 1 sample bench? (ce-rerank v1)

MV2 of Munim, Inc., 2026-10-17. Scored against `prereg-ce-rerank-v1.md`, which was public (commit a5a6211) before any cross-encoder score was computed. Research and drafting by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.

## Run
- Job `spark-ce-rerank-v1`: `spark_ce.py` and `test_spark_ce.py` at commit 7c2bce4, downloaded at run time; offline tests passed; then the bench on the v3 sample index (about 1.19 million records; data key `spark-sample`). It ran from 05:34 to 06:31 UTC on 2026-10-17 (53.7 minutes on 4 CPUs). The fetch log is empty: every title, abstract and iCite count was retrieved.
- Model: `ncbi/MedCPT-Cross-Encoder` (public domain), question against title plus abstract, 512 tokens.

## Scores (MRR@5)

| dev set | answer in the 50-candidate pool | chosen (v3) | ce | rrf | ce\|cue->rrf |
|---|---|---|---|---|---|
| landmark (72) | 0.972 | **0.838** | 0.704 | 0.805 | 0.786 |
| ordinary (26) | 0.962 | 0.809 | **0.962** | 0.873 | **0.962** |
| equal-weight mean | | 0.8235 | 0.8329 | 0.839 | 0.8739 |

Hit@1 for `ce`: 0.611 (landmark) and 0.962 (ordinary); for `chosen`, 0.769 on ordinary.

## Hypotheses
- **H1** (`ce` beats `chosen` on ordinary): **supported**, 0.962 against 0.809. `ce` helped 5 of 26 questions and hurt none; the one miss (od-20) was not in the pool for any method.
- **H2** (`ce` below `chosen` on landmark): **supported**, 0.704 against 0.838. Helped 7, hurt 21.
- **H3** (some candidate passes the decision rule): **not supported.** No candidate was eligible. `ce` and `rrf` were less than 0.02 above `chosen` on the mean (+0.009, +0.016). `ce|cue->rrf` was +0.050 on the mean but 0.052 below `chosen` on the landmark set, beyond the 0.02 limit.
- **S** (`chosen` reproduces v3 within 0.01): **ok**, 0.838 and 0.809, the same as v3.

**Decision, by the rule fixed in advance: the bench keeps `chosen`.** The prediction that a candidate would pass (low confidence) was wrong.

## Reading the rows that broke the prediction (counted by hand from `per_question.jsonl`)
- **The cross-encoder fails where the bench's priority cue fires.** On the 35 landmark questions with a cue, `ce` hurt 13 and helped 1. On the 37 without one, it helped 6 and hurt 8, a net change of about +0.03 in summed reciprocal rank, essentially a tie. Its typical cue failure is to rank a later paper on the same topic above the classic (lm-001, lm-010, lm-028, lm-029, lm-048: `chosen` at rank 1, `ce` at rank 6 to 17).
- **The fusion lost on cue questions too.** `ce|cue->rrf` uses `rrf` exactly where the citation prior matters, and there fusion halved or thirded the classic's reciprocal rank: 7 cue questions hurt, 1 helped. That alone accounts for its failure on the landmark set.
- **On ordinary questions the cross-encoder fixed what BM25 plus priors got wrong**: od-01 (rank 3 to 1), od-03 (5 to 1), od-04 (2 to 1), od-14 (17 to 1), od-23 (35 to 1).

## A post-hoc observation (not a finding)
A fifth ranking was not pre-registered: `switch` uses `chosen` on cue questions and `ce` on the rest. Computed by hand from the same rows, it scores about 0.8385 on landmark and 0.9615 on ordinary (mean about 0.900, against 0.8235). It would have passed the rule, but the idea came from reading these results, so it proves nothing here. It is now pre-registered for a held-out test on 28 new ordinary questions (`prereg-ce-switch-v1.md`, `devset_ordinary_v2.jsonl`), which runs only after that note is public.

## Honest limits
- n = 72 + 26. Gaps under about 0.05 are directions.
- The questions were written by AI agents with the answer in view. The ordinary questions paraphrase their abstracts, which is what a cross-encoder reads, so H1's large margin may overstate what it would do on expert-written questions. The held-out test cannot remove this bias; a full-index run on independent questions is the real check.
- The sample holds about 1/30 of the real distractors. None of these scores is a claim about the SPARK task itself.

## Files
`results.json`, `results.md` and `per_question.jsonl` are in the job output (`ce_rerank_v1_*` in this folder).
