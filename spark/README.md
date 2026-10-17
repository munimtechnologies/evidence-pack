# SPARK Task 1 sample bench

MV2 of Munim, Inc. Researched and built by AI agents (Claude) working in MV2's name. Code Apache-2.0; text and dev sets CC BY 4.0.

A small, honest bench for NLM's SPARK PubMed/PMC Task 1 (known-item retrieval: given a written information need, return the one PubMed record it describes; scored by MRR@5). MV2 of Munim, Inc. is preparing an entry. The real task needs an index of all ~38 million PubMed records; this bench fits in 2 GB so ranking ideas can be compared quickly and in the open.

## How it works
- **Sample index:** 40 evenly spaced files of the challenge's own PubMed baseline, plus PubMed Best Match's top 20 for each dev question (hard negatives) and every answer. About 1.19 million records, in SQLite FTS5 with Porter stemming. Preprints and records outside 1959-2026 are left out, as in the Challenge Corpus.
- **Dev sets** (in this folder):
  - `devset_landmark_v1.jsonl`: 72 questions about well-known papers (methods, trials, priority claims), including 10 pairs of easily confused papers.
  - `devset_ordinary_v1.jsonl`: 26 questions about papers drawn by a fixed rule from across the PMID range (`prereg-devset-ordinary-v1.md`).
  - `devset_ordinary_v2.jsonl`: 28 held-out questions drawn by the same rule from targets halfway between v1's (`prereg-ce-switch-v1.md`). Scored in `ce-switch-v1-results-2026-10-17.md`.
  - All were written by AI agents with the answer in view, so they are easier than expert questions. Every answer PMID was checked against PubMed.
- **Scores** compare ranking variants with each other. The sample holds about 1/30 of the real distractors, so no score here is a claim about the real task.

## Results so far
| bench | finding |
|---|---|
| v1 (landmark set) | An iCite citation prior raised MRR@5 from 0.677 to 0.878. |
| v2 (ordinary set; `prereg-devset-ordinary-v1.md`) | The same prior cost 0.072 on ordinary papers (helped 0, hurt 4), which triggered the pre-registered rule to gate it. |
| v3 (both sets; `prereg-cite-gate-v1.md`, `v3-decision.md`) | Gating the prior on a priority cue in the question kept most of the gain: 0.838 landmark, 0.809 ordinary (mean 0.824), against 0.677 / 0.809 without a prior. |
| ce-rerank v1 (`prereg-ce-rerank-v1.md`, `ce-rerank-v1-results-2026-10-17.md`) | NCBI's open MedCPT cross-encoder: 0.962 on ordinary (v3: 0.809) but 0.704 on landmark (v3: 0.838). No candidate passed the decision rule, so v3 stays. On landmark questions with a priority cue it hurt 13 and helped 1. |
| ce-switch v1 (`prereg-ce-switch-v1.md`, `ce-switch-v1-results-2026-10-17.md`) | Held-out test of an idea found after ce-rerank v1. On 28 new ordinary questions the cross-encoder scored 0.958 against 0.929 for v3: +0.030, below the pre-registered +0.05. **Not replicated; v3 stays.** It fixed both of v3's misses and lost two first places. The set was easier than expected (v3 at 0.929, not about 0.81), which left little room for any gain. |

## Files
- `prereg-*.md`: pre-registrations, each committed before its job ran.
- `v3-decision.md`: the v3 decision table. `ce-rerank-v1-results-2026-10-17.md` and `ce_rerank_v1_*`: the cross-encoder results and raw job output. `ce-switch-v1-results-2026-10-17.md` and `ce_switch_v1_*`: the held-out test and its raw job output.
- At the repository root (it keeps code there): `spark_eval.py` and `pm_extract.py` (the index builder and v1-v3 ranking variants), `gate_compare.py` (the v3 decision), `test_spark_eval.py`; `spark_ce.py` and `test_spark_ce.py` (the cross-encoder bench); `spark_switch.py` and `test_spark_switch.py` (the ce-switch scorer). `test_spark_eval.py` expects the v1 dev sets in the working directory.

Research tooling, not medical advice.
