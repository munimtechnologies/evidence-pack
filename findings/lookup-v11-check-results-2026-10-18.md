# integrity_check / commentin_check v1.1: live check results (2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Code Apache-2.0; text and data CC BY 4.0.
Research information, not medical advice. No independent human check yet.

## What was run

Job `lookup-v11-check-v1` (Blade, 1 CPU, 1 GB, network on), 2026-10-18 10:03:12 to 10:04:24 UTC, 71 s. It ran the three offline test files of v1.1, then `validate_v11.py`, which runs v1.1 `commentin_check` live against PubMed on the 26 "Comment in" links that the comment-target study (`commentin-targets-v1-results-2026-10-18.md`) labelled "not in PubMed". Those links come from 24 source records. The pre-registration is in `lookup-v11-2026-10-18.md`, committed before the run.

- Offline tests: 44 run, 44 passed.
- Live run: 24 of 24 source records read, 0 lookup errors.
- Code: `doi_hygiene.py` and `pubmed_commentin.py` fetched from main at 32d12b6; the v1.1 modules and tests from the job folder. SHA-256 of every file is in `lookup_v11_check_v1_provenance.json`.

## Expected (written before the run) against outcome

| Prediction | Outcome |
|---|---|
| All 20 JAMA Otolaryngology links (18 DOIs) resolve to PMIDs | **Held.** 20 of 20 found, 18 distinct target PMIDs |
| The 6 others (JAMA Neurol, Intern Med, Surg, Cardiol, Pediatr 2018; JAMA Netw Open 2024) are named absent by PubMed and flagged `target_not_in_pubmed` | **Held.** 6 of 6 |
| None is `target_unread` | **Held.** 0 |

So the v1.1 lookup does what it was built to do on the exact case that exposed the bug: the batch that v1 read as "18 DOIs not in PubMed" now resolves, and the 6 DOIs that really are absent are still called absent, each because PubMed named it under `quotedphrasesnotfound`.

## What the 20 recovered links are (read after scoring; not pre-registered)

Counted by hand from `lookup_v11_check_v1_links.jsonl`:
- **0 of 20 link back** to their source record (all flagged `not_reciprocal`).
- 2 are typed "Comment" and PubMed records them as comments on a different article (`comment_on_other`): a "Reply" (PMID 32077928) and PMID 32267483.
- The other 18 are typed Journal Article only (10, one also with an NIH funding tag), Review (4), Editorial (1), or Systematic Review / Consensus Statement (3 links, all to one target, PMID 32857157, from three source records).
- None is flagged `earlier`.
- Several titles read like invited commentaries ("Prolonging Life, but at What Price?", "Sinus Space in Outer Space."). That is a reading of titles only, not checked against the publisher's labels.

This matches the published comment-target study: most same-issue bare-DOI targets carry no comment type and no back-link in PubMed.

## Effect on the comment-target study's verdicts

The study is **not re-scored**; its correction stands (the 18 are counted as unread). As a bound only: the study read 1,760 targets, with about 4.6% comments on a different article and 7.6% typed research. Adding these 20 links, even if every one fell into one class, gives at most about 5.7% and 8.7%. Both stay below the 10% thresholds of H2 and H3, and none of the 20 is reciprocal, so H1 is unchanged. No verdict could change. (AI arithmetic from the rounded published percentages.)

## Limits

- One live run on one known batch. It shows the fix works here, not that every silent esearch failure is now caught. The count check is a heuristic (see `lookup-v11-2026-10-18.md`).
- PubMed changes over time; these outcomes are as of 2026-10-18 10:03 UTC.

## Data

- `lookup_v11_check_v1_results.json`: counts, expected flags, errors.
- `lookup_v11_check_v1_links.jsonl`: one row per link (source PMID, target DOI, outcome, target PMID, flags, title, date, publication types).
- `lookup_v11_check_v1_provenance.json`: commit and SHA-256 of each file the job used.

Nobody was contacted.
