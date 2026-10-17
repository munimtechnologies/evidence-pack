# MedCPT cross-encoder rerank on the SPARK Task 1 sample bench (prereg-ce-rerank-v1.md)

| dev set | answer in pool | chosen | ce | rrf | ce|cue->rrf |
|---|---|---|---|---|---|
| devset_landmark_v1.jsonl | 0.972 | 0.838 | 0.704 | 0.805 | 0.786 |
| devset_ordinary_v1.jsonl | 0.962 | 0.809 | 0.962 | 0.873 | 0.962 |

- H1 (ce beats chosen on ordinary): supported
- H2 (ce below chosen on landmark): supported
- H3 (a candidate passes the rule): not supported; eligible none
- **Pick: chosen** (means {'chosen': 0.8235, 'ce': 0.8329, 'rrf': 0.839, 'ce|cue->rrf': 0.8739})
- Sanity (chosen within 0.01 of v3): devset_landmark_v1.jsonl 0.838 vs 0.838 ok, devset_ordinary_v1.jsonl 0.809 vs 0.809 ok
