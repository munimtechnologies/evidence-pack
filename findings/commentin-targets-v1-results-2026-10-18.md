# Results: what are JAMA Network's same-issue bare-DOI "Comment in" targets? (v1, run 2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Code Apache-2.0, text and data CC BY 4.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

Pre-registration: `commentin-targets-prereg-v1-2026-10-18.md` (committed 2026-10-18 before the run). Code: `commentin_targets.py` calling `commentin_check.py`, both at commit a61323e, which the job fetched from main and recorded in `commentin_targets_v1_provenance.json`. Job `commentin-targets-v1` ran in MV2's sealed sandbox on 2026-10-18 from 05:15 to 05:18 UTC (2.9 minutes of API time, 0 lookup errors). Outputs: `commentin_targets_v1_results.json` (counts and verdicts) and `commentin_targets_v1_targets.jsonl` (one row per link: source PMID, target DOI, class, target PMID, title, date, publication types, "Comment on" list).

## 1. Scorecard, exactly as pre-registered

Population: 1,786 JAMA Network links and 30 control links (the pre-registered file, rows with `cls` = `bare_doi`, a target DOI and `"earlier": false`). 1,492 distinct source records; all 1,492 were found in live PubMed. `link_gone`: 0. `unread` as the code counted it: 0, so the void rule (more than 2% unread) did not fire. See section 4 for a correction that moves 18 links from `not_in_pubmed` to `unread` (1.0%, still below the void share) and leaves every verdict unchanged.

JAMA Network, read targets (classes reciprocal, comment_on_other, comment_typed, research_typed, untyped): **1,760**.

| Hypothesis | Threshold | Result | Verdict |
|---|---|---|---|
| H1: reciprocal (target lists the record under "Comment on") | at most 5% of read targets | 1 of 1,760 = 0.06% | **supported** |
| H2: comment_on_other (target is a comment PubMed records on a different article) | at least 10% | 81 of 1,760 = 4.6% | **not supported** |
| H3: research_typed (target has a study-design publication type) | at least 10% | 133 of 1,760 = 7.6% | **not supported** |

The other read classes: comment_typed 25 (1.4%); **untyped 1,520 (86.4%)**. Not read: 26 links whose target DOI did not resolve to a PubMed record in the job (section 4).

Without the 6 disclosed pilot links (2 comment_on_other, 2 research_typed, 2 untyped): 1,754 read; reciprocal 1 (0.06%), comment_on_other 79 (4.5%), research_typed 131 (7.5%), untyped 1,518 (86.5%). Also without the one link read after registration (source 32125402, Dieleman 2020, to a JAMA Health Forum piece, class untyped): 1,753 read, untyped 1,517 (86.5%). Verdicts unchanged.

So one of three predictions held. The same-issue links are, by PubMed's own data, almost never reciprocal. But the two mechanisms we predicted for the rest, comments recorded on a different article and plain research articles, cover only 214 of 1,760 (12.2%) between them. Seven in eight targets are records that PubMed types only "Journal Article" and that carry no "Comment on" list, so PubMed's structured data cannot say what they are.

Shares in this note were computed by an AI agent from the counts in `commentin_targets_v1_results.json`; the class counts themselves come from the code.

## 2. Reported without prediction

**By era (JAMA Network, read targets):**

| Era | Read | reciprocal | comment_on_other | comment_typed | research_typed | untyped | unresolved DOI |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016-2023 | 565 | 1 (0.2%) | 72 (12.7%) | 21 (3.7%) | 93 (16.5%) | 378 (66.9%) | 25 |
| 2024 | 247 | 0 | 3 (1.2%) | 4 (1.6%) | 12 (4.9%) | 228 (92.3%) | 1 |
| 2025-2026 | 948 | 0 | 6 (0.6%) | 0 | 28 (3.0%) | 914 (96.4%) | 0 |

Post hoc: in 2016-2023 alone both H2 (12.7%) and H3 (16.5%) would have passed. The failures come from 2024-2026, where nearly every target is untyped. Part of that is indexing lag: PubMed adds publication types and comment links when a record is indexed for MEDLINE, which can take months, so some 2025-2026 targets may still gain a type. It is not all lag: the three 2024 invited commentaries read by hand below (published November and December 2024) are still typed only "Journal Article" on 2026-10-18.

**By journal (read targets; the share typed only "Journal Article"):** JAMA Network Open 1,002 read, 952 untyped (95.0%); JAMA 296 read, 227 (76.7%); JAMA Internal Medicine 108, 74 (68.5%); JAMA Oncology 54, 37 (68.5%); JAMA Dermatology 52, 35 (67.3%); JAMA Ophthalmology 42, 36; JAMA Pediatrics 39, 35; JAMA Otolaryngology-Head & Neck Surgery 37, 16 (43.2%; its research_typed share is the highest, 17 of 37); JAMA Health Forum 34, 34; JAMA Neurology 28, 21; JAMA Surgery 24, 19; JAMA Cardiology 23, 17; JAMA Psychiatry 21, 17. The only reciprocal link is at JAMA Otolaryngology (source 31513264 to 31513251, an invited commentary typed "Journal Article" whose record does list the source under "Comment on"). Full counts per journal are in the results file.

**Controls (30 links at NEJM, Lancet, BMJ and Annals of Internal Medicine; no prediction):** reciprocal 0, comment_on_other 3, comment_typed 10, research_typed 6, untyped 11, unresolved 0. At the controls 13 of 30 targets carry a comment type or a "Comment on" list; at JAMA Network 107 of 1,760 (6.1%) do. The control sample is small.

## 3. Exploratory hand read of `untyped` targets (post hoc; rule fixed before looking)

Rule: every JAMA Network `untyped` link whose target PMID ends in "00" (a fixed, reproducible rule in place of a seeded sample, because this read was done by hand). That gave 15 links to 13 distinct targets (two targets are linked from two sources each). For each target an AI agent read the article-type label on the JAMA Network page on 2026-10-18 (reached through doi.org) and the Europe PMC `pubType` list.

| Target PMID | Journal, date | JAMA Network label | PubMed types | Europe PMC types |
|---|---|---|---|---|
| 39556400 | JAMA Netw Open 2024-11 | Invited Commentary | Journal Article | article-commentary, Journal Article |
| 39585700 | JAMA Netw Open 2024-11 | Invited Commentary | Journal Article | Journal Article |
| 39699900 | JAMA Netw Open 2024-12 | Invited Commentary | Journal Article | Journal Article |
| 40238100 | JAMA Netw Open 2025-04 | Invited Commentary | Journal Article | Journal Article |
| 40465300 | JAMA Netw Open 2025-06 | Invited Commentary | Journal Article | Journal Article |
| 41143800 | JAMA Netw Open 2025-10 | Invited Commentary | Journal Article | Journal Article |
| 41284300 | JAMA Netw Open 2025-11 | Invited Commentary | Journal Article | Journal Article |
| 41661600 | JAMA Netw Open 2026-02 | Invited Commentary | Journal Article | Journal Article |
| 41701500 | JAMA Netw Open 2026-02 | Invited Commentary | Journal Article | Journal Article |
| 41941200 | JAMA 2026-04 | Editorial | Journal Article | Journal Article |
| 34661600 | JAMA Intern Med 2021-12 (2 links) | Original Investigation | Journal Article, Research Support | research-article, Journal Article, Research Support |
| 42804200 | JAMA 2026-09 | Research Letter | Journal Article | Journal Article |
| 30725100 | JAMA Dermatol 2019-03 (2 links) | page returned HTTP 403 | Journal Article, Research Support | research-article, Journal Article, Research Support |

Reading: 10 of 13 targets (10 of 15 links) are commentaries by the publisher's own label, 9 invited commentaries and 1 editorial. None of the 10 is typed Comment or Editorial in PubMed and none carries a "Comment on" list, so by PubMed's data they are indistinguishable from research. 3 of 13 (5 of 15 links) are research articles. For those three, we also read the five source records that link to them (Europe PMC, 2026-10-18): all five are themselves research articles (a JAMA randomized trial linking to a JAMA research letter on a related trial; two JAMA Internal Medicine cancer-drug-spending studies linking to a third in the same issue; two JAMA Dermatology gender-representation studies linking to a third). Those links join related research papers in one issue; neither end is a comment on the other.

So, as far as 13 targets can say, the large `untyped` class is mostly real commentary whose PubMed record lacks the Comment type and the back-link, with a minority of related-research links. The relationship the link asserts is usually real; what is missing is the type on the target and the reciprocal link. Europe PMC's JATS article type (`article-commentary`) was present for only 1 of the 10 commentaries, so it is not a general substitute for the missing PubMed type.

## 4. Correction to one class, found while reading the output

The code labelled 26 JAMA Network links `not_in_pubmed`. Reading them by hand on 2026-10-18:

- 18 are the JAMA Otolaryngology-Head & Neck Surgery targets of 2019-2020 (plus one such DOI linked from a JAMA record). Their DOIs sort together alphabetically, so `integrity_check.pubmed_lookup` sent them to PubMed in the same one or two esearch batches. Replaying exactly that 18-DOI esearch by hand returned 18 PMIDs with no warning. So these targets are in PubMed; the job's batch came back without them and without an error (a count of zero is not an error to the code), and every DOI in the batch was then labelled "not in PubMed". The honest class for these 18 is `unread`. Two of them were also read on the JAMA Network site: one is a systematic review with consensus statements (PMID 32857157), one a "Comment & Response" letter (PMID 31725832).
- 6 are genuinely not found by DOI in PubMed esearch today (`quotedphrasesnotfound` lists all six): 10.1001/jamaneurol.2017.4634, jamainternmed.2018.0098, jamasurg.2018.2792, jamacardio.2018.2412, jamapediatrics.2018.3179 and jamanetworkopen.2024.15614. They may be unindexed items or DOIs PubMed stores differently; we did not resolve them further.

Corrected JAMA Network tallies: `unread` 18 (1.0% of 1,786, under the 2% void share), `not_in_pubmed` 6. Both classes sit outside the "read" denominator, so H1-H3 and every share above are unchanged. The published `targets.jsonl` keeps the labels as the code wrote them; this section is the correction. Fix planned for `commentin_check` v1.1: a DOI counts as not in PubMed only when esearch names it under `quotedphrasesnotfound`; a batch that returns fewer records than that allows is retried and, if still short, its DOIs are `unread`. The same change applies to `integrity_check.pubmed_lookup`, which both tools share.

## 5. What this does and does not show

- By PubMed's structured data, JAMA Network's same-issue bare-DOI "Comment in" links are one-way in 1,759 of 1,760 cases (H1). Tools and studies that take a "Comment in" link to mean "a typed comment that links back" will miss these.
- The predicted "not a comment at all" mechanisms (H2, H3) explain about one link in eight. The dominant case, 86%, is a target PubMed cannot type. A hand read of 13 suggests most of those are invited commentaries, so the census v1 reading that same-issue links "may well comment on the record" is mostly right; the defect is in the target's record (no Comment type, no "Comment on"), not in the existence of a commentary.
- Related-research links do exist (7.6% typed research, plus 3 of 13 untyped in the hand read) and they are not comments in either direction. A reader cannot tell the two kinds apart from PubMed alone.
- We have not seen the publisher's XML and cannot say who creates the links or why the commentaries are deposited without a comment type. Publication types are NLM indexing and lag publication. The hand read is 13 targets chosen by a digit rule, not a random sample of 1,520.
- Nobody at JAMA Network, the AMA, NLM or any author has been contacted, and nobody will be about this unchecked result.

## 6. Next

1. `commentin_check` v1.1 and `integrity_check`: the `quotedphrasesnotfound` rule above; the `earlier` tolerance for same-day commentaries already noted in `regen-reference-commentlinks-2026-10-18.md`; offline tests for both.
2. If a type-level answer for all 1,520 untyped targets is wanted, a pre-registered v2 needs a machine-readable article type. PubMed and Crossref (`relation` is empty for the invited commentary checked) do not carry it; Europe PMC carries it for a minority. Reading 1,520 publisher pages by machine is not something we will do without checking the site's terms.
3. For MV2's own evidence packages the rule stands: never cite a bare-DOI "Comment in" target as commentary without reading it.
