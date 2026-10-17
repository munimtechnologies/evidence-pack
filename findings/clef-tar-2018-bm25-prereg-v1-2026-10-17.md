# Pre-registration: a reproducible screening baseline on CLEF TAR 2018 (v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research tooling and information, not medical advice.

## Why

Systematic reviewers screen thousands of search results to find the few studies a review includes. Tools that rank the likely includes first ("screening prioritisation") can save much of that work. Claims about how much work they save are only worth something if anyone can rerun them.

MV2 is preparing an entry to AHRQ's Clinical Evidence Synthesis Transformation Challenge (Phase 1 due 2027-03-12). That challenge asks for quantified performance claims, so the first step is a baseline measured on a public benchmark, with code anyone can rerun. This study builds that harness and checks it against a published number before anything is built on top of it.

## Data

- **Collection:** CLEF eHealth TAR 2018, Task 2 (abstract and title screening), testing set: 30 Cochrane diagnostic-test-accuracy reviews. Files come from github.com/CLEF-TAR/tar (MIT), folder `2018-TAR/Task2/Testing/`: `topics/<CD id>` and `qrels/full.test.abs.2018.qrels` (primary), `qrels/full.test.content.2018.qrels` (secondary). Latest commit seen on 2026-10-17: dbc13d0 (2025-04-17). The job records the commit it actually reads.
- **Documents:** for every PMID in the abstract-level qrels, the title and abstract as PubMed returns them today (E-utilities efetch). Records PubMed no longer returns stay in the list with no text and so rank last. Their number is reported.
- **What we looked at before writing this:** the folder listing, the first lines of one qrels file, and the query lines of topics CD008122, CD010213 and CD012599, to learn the file formats. No document text, ranking or score was looked at.

## Method (fixed in `tar_bench.py`)

- **Candidates:** each topic's judged documents (qrels value 0, 1 or 2), as CLEF's evaluator counts them.
- **Text:** title + abstract, lower-cased, split into runs of letters and digits; pure numbers and a fixed stop list are dropped. No stemming.
- **Query terms** from the Ovid-style Boolean query:
  - lines that only combine earlier lines ("1 or 2", "or/1-41") contribute nothing;
  - lines starting with "limit" are skipped;
  - field tags (`.ti,ab.`, `.mp.`), floating subheadings (`di.fs.`), subheadings (`/di`), bracketed notes and operators (and, or, not, adjN, exp) are removed;
  - each remaining word counts once.
- **BM25:** k1 = 1.2, b = 0.75, Lucene idf ln(1 + (N - df + 0.5)/(df + 0.5)), computed within each topic's candidates. Ties are broken by a fixed hash of topic and PMID.
- **Variants:**
  - `bool`: the query words, with truncation marks removed (so `sensitiv:` is the literal word "sensitiv").
  - `bool_title`: `bool` plus the review title's words.
  - `bool_title_prefix`: `bool_title`, but each truncated word matches every word that starts with it, scored as one term.
  - `title` and `random` (a fixed pseudo-random order) are references only.
- **Measures:** the formulas of CLEF's evaluator (`scripts/tar_eval.py`, `measures/eval_measures.py`):
  - AP, divided by all relevant documents;
  - last_rel;
  - WSS@95 = (N - rank of the round(0.95 R)-th relevant)/N - 0.05;
  - WSS@100 = (N - last_rel)/N;
  - norm_area.
  - We also report recall in the top 1, 5, 10 and 20% of each list (top ceil(x·N/100) documents).
  - Each measure is averaged over topics with at least one relevant document.

## Predictions (scored on abstract-level qrels, all 30 topics)

The target is Wang et al., SIGIR-AP 2023 (arXiv 2309.05238), Table 2, CLEF-2018, Boolean query + BM25: MAP 0.154, WSS95 0.361 (also last_rel 6033.1, WSS100 0.264, recall at 1/5/10/20% of 0.082/0.242/0.391/0.563). That paper does not give its BM25 parameters, stemming or the fields it indexed, so we allow a margin.

- **H1 (reproduction):** `bool` has mean AP within 0.04 of 0.154 **and** mean WSS@95 within 0.06 of 0.361. If both hold, the harness reproduces the published baseline. If either fails, we report by how much and do not tune anything to close the gap in this version.
- **H2 (a cheap improvement):** `bool_title_prefix` has higher AP than `bool` in at least 20 of the 30 topics (a one-sided sign test gives p ≈ 0.049 at 20 of 30).

## Void rule

If PubMed fetches fail (after retries and splitting) for more than 1% of the PMIDs, the run is void and is re-run unchanged as -v2. PMIDs that PubMed simply no longer returns are not failures; they are counted and reported.

## Exploratory (not predictions)

- **Content-level qrels:** every variant is also scored against them.
- **Retractions:** how many judged records PubMed now marks as retracted ("Retracted Publication" or a "Retraction in" link), and how many of those are judged relevant. We found no earlier count of retracted records inside the CLEF TAR collections (search, 2026-10-17). A retracted included study in a benchmark rewards a system for finding a paper a reviewer should now drop. We will list any we find. Cochrane-related retractions are often for updating rather than misconduct, so each one is described, not judged.
- **Topic-level spread:** we report per-topic results, so it is visible whether a few large topics drive the means.

## Limits

- The benchmark text is today's PubMed, not the 2017-2018 snapshot. Abstracts added or changed since then shift the scores slightly.
- 30 reviews, all diagnostic-test-accuracy: the results say nothing about intervention or qualitative reviews.
- BM25 is a floor, not the goal. This study only establishes that the harness measures correctly; later versions compare stronger rankers against it.

## Outputs

- `results.json`: means, per-topic measures, topic statistics, verdicts and errors.
- `retracted.jsonl`: any retracted records found.
- Run files in TREC format (`runs/*.res.gz`), so the official `tar_eval.py` can recheck every number.

Results will be published as `findings/clef-tar-2018-bm25-v1-results-<date>.md` whatever they show.
