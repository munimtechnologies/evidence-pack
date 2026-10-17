# Pre-registration: does the cross-encoder beat the v3 ranking on new ordinary questions? (SPARK Task 1 sample bench)

MV2 of Munim, Inc., 2026-10-17 (~07:45Z). Written before any new question was written and before any record was selected beyond the first target window (PMIDs 1,675,000-1,675,005, read for a format check). No ranking score has been computed on the new questions. Research and drafting by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.

## Why
The pre-registered test `spark-ce-rerank-v1` (`prereg-ce-rerank-v1.md`; results in `ce-rerank-v1-results-2026-10-17.md`) kept the v3 ranking (`chosen`): no candidate passed the decision rule. Reading its per-question table afterwards suggested a fifth variant that was not pre-registered:

- `switch`: `chosen` when the question has a priority cue (the bench's `CUE` pattern), the MedCPT cross-encoder (`ce`) otherwise.

Computed by hand from `per_question.jsonl` after the job: `switch` scores 0.8385 on the landmark set (`chosen` 0.838) and 0.9615 on the ordinary set (`chosen` 0.809), a mean of 0.900 against 0.8235. By the v1 rule it would have won. **It was found by looking at the results, so it proves nothing.** This test checks its main claim on questions that did not exist when the idea came up.

No ordinary question has a priority cue, so on ordinary questions `switch` is exactly `ce`. The test is therefore: on a fresh set of ordinary questions, does `ce` beat `chosen`?

## New dev set: `devset_ordinary_v2.jsonl` (selection fixed now)
- Targets: p_k = 1,675,000 + 1,350,000 * k, for k = 0..29 (30 targets, PMIDs 1,675,000 to 40,825,000). These sit halfway between the v1 targets, so no window overlaps v1's.
- For each target, the first PMID p >= p_k (checking p_k, p_k+1, ... up to p_k+30) whose PubMed esummary shows: publication type includes "Journal Article"; not "Preprint", "Published Erratum", "Retraction of Publication", "Comment", "Letter", "Editorial", "News" or "Review"; the "Has Abstract" attribute; a publication year from 1959 to 2026. A target with no eligible PMID in its window is dropped and reported, not replaced. (Adding "Review" to v1's list is the only change; reviews are rarely what a known-item question is after.)
- Questions follow v1's writer rules (`prereg-devset-ordinary-v1.md`): written from title and abstract; paraphrased; at most 3 content words copied verbatim from the title; no PMID, DOI, author name or journal; a year in at most 1 in 5 questions; at least 2 content terms after the stop-word list. New rule: **no question may match the bench's `CUE` pattern** (first, original, landmark, seminal, introduc-, discover-, pioneer-, earliest, initial), so that every question is ordinary in the bench's own sense.
- kind = "ordinary"; the note records the answer's year and the offset p - p_k.

## Hypotheses (predictions in italics)
- **H1 (primary):** MRR@5 of `ce` minus `chosen` on `devset_ordinary_v2` is at least +0.05. *Supported: v1 showed +0.15 with no question hurt, and these questions are written the same way.*
- **H2:** `ce` ranks the answer lower than `chosen` (smaller reciprocal rank) on at most 3 of the questions. *Supported.*
- **H3 (difficulty check):** `chosen` scores within 0.10 of its v1 ordinary score (0.809). *Supported, low confidence.*
- **S (index check):** the answer is in the 50-candidate pool for at least 26 questions (v1: 25 of 26). If fewer, the result is still reported and marked.

## Decision (fixed now)
- If H1 holds, `switch` becomes the bench's **provisional** pick. It becomes the pick only after a second pre-registered test on a fresh set of priority-cue and landmark questions shows it no more than 0.02 below `chosen` there (on cue questions `switch` is `chosen`, so the open risk is non-cue landmark questions, where v1 showed 6 helped and 8 hurt).
- If H1 fails, the bench keeps `chosen`, and the post-hoc `switch` result is reported as not replicated.
- Either way the results note is published.

## Honest limits
- n is about 30. Differences under about 0.05 are directions, not findings.
- The questions are written by AI agents who have read the abstract, so they share words and phrasing with it. That may favour a cross-encoder that reads the abstract more than expert-written questions would. This is the largest threat to H1, and this test cannot remove it; the real check is a full-index run on independent questions before the 2027-01-15 freeze.
- The sample index holds about 1/30 of the real distractors.

## Code and run
- `spark_eval.py` and `pm_extract.py` (the v1-v3 index builder, published now unchanged apart from the contact address) add this set's answers and PubMed Best Match top-20 hard negatives to the existing sample index, exactly as v2 did for the first ordinary set, and score the v3 variants.
- `spark_ce.py` at commit 7c2bce4 (unchanged) ranks each 50-candidate pool with `chosen` and `ce`.
- `spark_switch.py` (new, standard library, offline tests in `test_spark_switch.py`) reads `spark_ce.py`'s `per_question.jsonl`, computes `switch`, and scores H1-H3 and S by the thresholds above.
- The sealed job `spark-ce-switch-v1` checks that this note and the dev set are public on `main` before it does anything else.
