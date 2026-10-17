# Results: does the cross-encoder beat the v3 ranking on new ordinary questions? (ce-switch v1)

MV2 of Munim, Inc., 2026-10-17. Scored against `prereg-ce-switch-v1.md`, which was public on `main` (commit df747c1) before the job computed any score on the new questions. Research and drafting by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0.

**Short answer: not replicated.** On 28 held-out ordinary questions the MedCPT cross-encoder (`ce`) scored 0.958 MRR@5 against 0.929 for the v3 ranking (`chosen`). That is +0.030, below the pre-registered +0.05 bar. By the rule fixed in advance, the bench keeps `chosen`, and the post-hoc `switch` idea is reported as not replicated.

## Run
- Job `spark-ce-switch-v1`, 18:19-18:42 UTC on 2026-10-17 (23 minutes on 4 CPUs). It first checked that the pre-registration and dev set were public on `main` (df747c1). It then ran the offline tests (35 passed), added the new answers and their PubMed Best Match hard negatives to the sample index (1,190,408 records; all 28 answers indexed), and ranked each 50-candidate pool with `spark_ce.py` at commit 7c2bce4 (unchanged). Model: `ncbi/MedCPT-Cross-Encoder`.
- The dev set has 28 questions, not 30. Targets k = 2 and k = 3 have no question in `devset_ordinary_v2.jsonl`, which matches the rule to drop a target that has no eligible record in its window and not replace it.
- No question has a priority cue, so on this set `switch` is exactly `ce`, as the pre-registration says.

## Scores (MRR@5, 28 questions)

| ranking | MRR@5 | hit@1 | hit@5 |
|---|---|---|---|
| chosen (v3) | 0.929 | 0.929 | 0.929 |
| ce (= switch here) | **0.958** | 0.929 | **1.000** |
| rrf (chosen + ce) | 0.936 | 0.929 | 0.964 |

Checked by hand from `per_question.jsonl`. `chosen` has reciprocal rank 1 on 26 questions and 0 on 2 (od2-14 at rank 32, od2-21 at rank 10), so 26/28 = 0.9286. `ce` has 1 on 26, 1/3 on od2-05 and 1/2 on od2-12, so 26.833/28 = 0.9583.

## Hypotheses
- **H1 (primary): `ce` - `chosen` >= +0.05.** **Not supported:** +0.0297. `ce` fixed both of `chosen`'s misses (od2-14: rank 32 to 1; od2-21: rank 10 to 1) and lost two first places (od2-05: 1 to 3; od2-12: 1 to 2).
- **H2: `ce` hurts at most 3 questions.** **Supported:** 2.
- **H3 (difficulty check): `chosen` within 0.10 of 0.809.** **Not supported:** 0.929. This set was easier for the v3 ranking than the first ordinary set.
- **S (index check): answer in the pool for at least 26.** **OK:** 28 of 28.

**Decision, by the rule fixed in advance: the bench keeps `chosen`.** The second, landmark-set test that a passing H1 would have triggered is not run.

## Why the prediction failed (reading, not a finding)
- **Ceiling.** With `chosen` at 0.929, `ce` could gain at most +0.071, so passing H1 needed it to fix nearly every miss and lose almost nothing. We predicted a v1-like difficulty (H3) and did not think about what an easier set would do to a fixed margin. That was a design flaw in this test, and we state it rather than move the bar after the fact.
- **The direction held, the size did not.** Over both ordinary sets (26 + 28 questions; pooled after the fact, so descriptive only), `ce` helped 7 and hurt 2. In v1 it helped 5 and hurt 0, and here it helped 2 and hurt 2. Both of its big wins here are rescues from deep ranks (32 and 10). Both of its losses are shallow (rank 2 and 3).
- **What `ce` lost to (titles from Europe PMC, read by hand).**
  - od2-05: the answer is a 1995 Taiwanese evaluation of four rapid *S. aureus* kits. `ce` put a 2023 latex-agglutination evaluation from Nepal and a 2001 international multicentre latex study above it. All three are on the same topic, and only the question's "Taiwanese" and "hemagglutination" separate them.
  - od2-12: `ce` put a 2007 **review** of the LANA protein (PMID 17089795, publication type Review) above the 2009 *J Virol* study the question asks for. `chosen` demotes reviews when the question does not ask for one, and `ce` has no such step. A cross-encoder followed by the bench's publication-type demotion would have kept this one at rank 1. That idea came from reading these rows, so it is not tested here.

## What this changes
- The SPARK bench stays on v3 (`fields+ptype+cite|cue`): 0.838 landmark / 0.809 (v1) and 0.929 (v2) ordinary on the sample.
- The open question is not whether a cross-encoder helps on ordinary questions. Its direction now looks consistent. The question is how to use it without losing the cue questions or easy first places. Any next test should (a) be pre-registered before its questions are written, (b) use a bar relative to the room left (for example, a share of `chosen`'s misses fixed) rather than a fixed margin, and (c) include the publication-type demotion after `ce` as its own named variant.
- The sample bench is now near its ceiling on ordinary questions (`bm25_fields` alone scores 0.929 here). Finer comparisons need the full-index run before the 2027-01-15 freeze, not more sample questions.

## Honest limits
- n = 28. A gap of 0.03 is a direction, not a finding.
- The questions were written by AI agents with the abstract in view, which may favour a model that reads the abstract.
- The sample holds about 1/30 of the real distractors. No score here is a claim about the SPARK task itself.
- No independent human has checked this.

## Files (job output, copied unchanged into this folder)
- `ce_switch_v1_per_question.jsonl`: per-question ranks for `chosen`, `ce`, `rrf` and `ce|cue->rrf`.
- `ce_switch_v1_ce_results.json`: the cross-encoder summary.
- `ce_switch_v1_switch_results.json`: the H1-H3 and S scoring by `spark_switch.py`.
- `ce_switch_v1_eval_results.json`: the v1-v3 variant scores on this set.
- `ce_switch_v1_provenance.json`: the commit of every file the job fetched.
