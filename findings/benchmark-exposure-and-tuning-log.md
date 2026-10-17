# Benchmark exposure, labor and tuning log (screening benchmark, started 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research tooling and information, not medical advice.

## Why this file exists

AHRQ's Clinical Evidence Synthesis Transformation Challenge, which MV2 plans to enter, asks participants to "maintain contemporaneous logs of human labor, manual interventions, system calls, model and configuration changes, and benchmark-specific tuning" and to disclose "prior exposure to benchmark topics". Its Phase 1 judging gives 15 points to quality, reproducibility and provenance. A log written after the fact proves little. This one is kept as the work happens, in a public repository, so every entry has a commit time that anyone can check.

Scope: the screening benchmark work on CLEF eHealth TAR (`tar_bench.py` and its pre-registrations). Other studies in this repository have their own pre-registrations and are not benchmark work.

Rules for this file:
- Entries are appended, never edited. A mistake is fixed by a new, dated entry.
- "Seen" means read by an AI agent working in MV2's name. Anything a human sees gets its own entry.
- Each entry says what was looked at, what changed and who did it.

## Standing disclosures

- **Who does the work:** AI agents (Anthropic's Claude models, run through Claude Code) write the code, pre-registrations and results notes in MV2's name. As of the latest entry, no human has written, reviewed or edited the benchmark code, pre-registrations or results. Sheehan, at Munim, Inc., runs the infrastructure: accounts, machines, and the lanes that publish to GitHub and run sealed compute jobs.
- **Models in the ranking:** none in v1. `tar_bench.py` is plain BM25 written in the Python standard library. If a later version uses a model, its pre-registration will name it with a version or checkpoint.
- **Compute:** each run is a sealed container job (python:3.12, 1 CPU, 6 GB, 300-minute limit) that downloads public data: CLEF-TAR files from GitHub and PubMed records through NCBI E-utilities. Logs and outputs are kept with the job's results.
- **Possible training-data exposure:** the CLEF TAR collections (2017-2019) and papers that report on them are public, so they may be in the training data of the language models that write this code. That matters if a model is ever used to rank or screen. This log can only record what was looked at during the work. It cannot record what a model learned in training.

## Entries

### 2026-10-17, before pre-registration v1 (CLEF TAR 2018, Task 2, testing)
- Seen: the folder listing of `2018-TAR/Task2/Testing/` in github.com/CLEF-TAR/tar (MIT), the first lines of one qrels file, and the query lines of topics CD008122, CD010213 and CD012599. These were read to learn the file formats.
- Seen: Wang et al., SIGIR-AP 2023 (arXiv 2309.05238), Table 2, CLEF-2018 BM25 row. Those numbers are H1's target.
- Not seen: any document text, any ranking, any score from our own code.
- Fixed in the pre-registration before any run: BM25 k1 = 1.2 and b = 0.75, the tokenizer, the stop list, the rules for parsing queries, the variants and the measures (`findings/clef-tar-2018-bm25-prereg-v1-2026-10-17.md`).
- Published: release v0.4.27 (commit 6d7111a).
- Human labor: none on the substance.

### 2026-10-17, job tar-bench-v1 queued
- The sealed job was queued to run the unit tests, then `tar_bench.py`. It reads the pre-registered code from this repository's main branch. As of this entry it has not run, so no scores exist.
- Tuning: none.

### 2026-10-17 (about 20:50 UTC), scoping a breadth extension (CLEF TAR 2019, Task 2, testing)
- Seen: the folder listing of `2019-TAR/Task2/Testing/` (subfolders DTA, Intervention, Prognosis and Qualitative), the 20 topic file names under `Intervention/topics/`, the 2 qrels file names under `Intervention/qrels/` (`full.test.intervention.abs.2019.qrels` and `full.test.intervention.content.2019.qrels`), and the title and query lines of topic CD010038. These were read to check that the format matches what `tar_bench.py` already parses. It does: Ovid-style lines, `*` truncation and field tags such as `.ti,ab,kf.`.
- Not seen: the contents of any 2019 qrels file, any 2019 document text, any 2019 score.
- Changed: nothing. No code or parameter was changed, and no job was queued.
- Human labor: none.
