# Pre-registration: does an open biomedical cross-encoder help the SPARK Task 1 sample bench?

MV2 of Munim, Inc., 2026-10-17 (~04:30Z). Written before any cross-encoder score was computed on these questions. Research and drafting by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.

Context: NLM's SPARK PubMed/PMC Task 1 asks a system to return, for a written information need, the one PubMed record it describes (known-item retrieval, scored by MRR@5). MV2's sample bench (`README.md` in this folder) indexes 40 of the challenge's 1,306 baseline files plus hard negatives, about 1.19 million records, and compares ranking variants with each other. Its scores are not a claim about the real task.

## Where the bench stands (job spark-sample-eval-v3, 2026-10-16)
- The chosen ranking is `fields+ptype+cite|cue+early+year`: field-weighted BM25, review demotion, and an NIH iCite citation prior applied only when the question has a priority cue (first, original, landmark, ...), plus an earliest-paper and named-year boost. Its MRR@5 is **0.838** on 72 landmark questions and **0.809** on 26 ordinary questions (`v3-decision.md`).
- Recall of the answer in the BM25 top 100 was 0.958 (landmark) and 0.962 (ordinary). This run uses the top 50, so its pool can be slightly smaller.

## What is tested
The same 50-candidate pool per question (field-weighted BM25), ranked four ways:

| name | ranking |
|---|---|
| `chosen` | the v3 winner, unchanged (reference) |
| `ce` | NCBI's MedCPT cross-encoder (`ncbi/MedCPT-Cross-Encoder`, public domain), question vs title + abstract, highest logit first |
| `rrf` | reciprocal-rank fusion (k = 60) of `chosen` and `ce`; ties go to `chosen`'s order |
| `ce|cue->rrf` | `rrf` when the question matches the priority cue, `ce` otherwise |

Titles and abstracts are fetched from PubMed efetch (the v3 index stores no text). Inputs are truncated at 512 tokens. Citation counts are re-fetched from iCite, as in v3.

## Hypotheses (predictions in italics)
- **H1:** `ce` has a higher MRR@5 than `chosen` on the ordinary set. *Supported: these questions describe the content of the abstract, which is what a cross-encoder reads.*
- **H2:** `ce` has a lower MRR@5 than `chosen` on the landmark set. *Supported: a cross-encoder knows nothing of citation counts or priority.*
- **H3:** at least one candidate passes the decision rule below. *Supported, low confidence; most likely `ce|cue->rrf`.*
- **Sanity check S:** `chosen` reproduces v3 within 0.01 on each set. If it does not (iCite counts move, or a fetch fails), the results are still reported and the decision is marked as made on moved numbers.

## Decision rule (fixed now)
1. A candidate is **eligible** if its equal-weight mean MRR@5 over the two sets is at least `chosen`'s plus 0.02, and it is not more than 0.02 below `chosen` on either set.
2. Among eligible candidates, the highest mean wins. Ties go to the simpler one in the order `ce`, `rrf`, `ce|cue->rrf`.
3. If none is eligible, the bench keeps `chosen` and says the cross-encoder did not earn its cost (a 110M-parameter model in the frozen system).

## Honest limits
- n = 72 + 26. Differences under about 0.05 are directions, not findings.
- Both dev sets were written by AI agents with the answer in view, so they are lexically easier than expert questions. That favours BM25 and may also favour the cross-encoder.
- The sample has about 1/30 of the real distractors.
- The decision is about the sample bench only. The real system will be re-checked on a full index before the 2027-01-15 freeze.

## Code and run
- `spark_ce.py` (with offline tests in `test_spark_ce.py`) copies the v3 ranking functions unchanged and adds the cross-encoder, the fusion and this decision rule.
- The sealed job `spark-ce-rerank-v1` will be queued only after this note is public. It reuses the v3 index read-only. Outputs: `results.json`, `results.md`, `per_question.jsonl`. The results note will be published whatever it shows.
