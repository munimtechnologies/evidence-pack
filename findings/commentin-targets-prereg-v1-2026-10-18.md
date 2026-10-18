# Pre-registration: what are JAMA Network's same-issue bare-DOI "Comment in" targets? (v1, 2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Code Apache-2.0, text CC BY 4.0.
Research information about bibliographic data, not medical advice. Committed before any data for this study are collected.

## Question

Census v1 (`pubmed-commentin-census-v1-results-2026-10-17.md`) found 2,877 bare-DOI "Comment in" links (no PMID) at 13 JAMA Network journals, 2016-2026. 1,091 point to targets dated before the record, which cannot be comments on it. For the other 1,786, the census said only that they "may well comment on the record", having read just 3 records. **This study reads every one of the 1,786 targets in live PubMed and asks what they are.**

Why it matters: NLM's policy says a comment link is for a piece "written primarily for the purpose of making a comment" on that article, and that a mere mention is not a comment. Large studies use these links as data. For example, "Scientific commentaries are dealing with uncertainty and complexity in science" (Information Processing & Management, 2024) compared over 0.8 million commented PubMed papers with all of PubMed. If one-way bare-DOI links count related research as commentary, those studies and appraisal tools inherit the error.

Prior art: the census pre-registration searched for reports of bare-DOI or one-way "Comment in" links at JAMA Network and found none. A new search on 2026-10-18 (PubMed comment-link accuracy, CommentsCorrections completeness, invited commentary linkage) found NLM's policy page and studies that use the links, but none that measures how accurate the links are.

## Data and code

- Population: every row of `pubmed_commentin_v1_nopmid_links.jsonl` (census v1, on main) with `cls` = `bare_doi`, a target DOI and `"earlier": false` (target not dated before the record in Crossref). By hand count of that file: 1,786 rows at JAMA Network (the scored group) and 30 at the controls, which are reported without prediction.
- Code: `commentin_targets.py`, which calls `commentin_check.py` (both committed with this note, with offline tests). It re-reads each record in live PubMed, matches its current links by target DOI, reads each target and sorts it into exactly one class, checked in this order:
  1. `link_gone`: the record no longer carries the link.
  2. `not_in_pubmed` / `unread`: the target DOI is not in PubMed, or a lookup failed.
  3. `reciprocal`: the target lists the record under "Comment on".
  4. `comment_on_other`: the target lists other records under "Comment on", but not this one.
  5. `comment_typed`: the target has publication type Comment or Editorial, with no "Comment on" list.
  6. `research_typed`: the target has a study-design publication type (any type containing "Trial", or Review, Systematic Review, Meta-Analysis, Observational Study, Multicenter Study, Comparative Study, Validation Study, Evaluation Study, Case Reports, Twin Study).
  7. `untyped`: read, and none of the above (mostly items typed only "Journal Article").
- Denominator for the hypotheses: JAMA Network targets in classes 3-7 ("read").
- Job: `commentin-targets-v1` in MV2's sandbox. It fetches the code and the census file from the current commit on main and records that commit.

## Pilot (disclosed; seen before writing the hypotheses)

On 2026-10-18 we read 6 of these links by hand: the **first six `"earlier": false` rows in file order** (all 2017, not a random sample). The 6 targets were 28030664 (typed Review), 28196229 (typed only Journal Article), 28199449 (Comment, recorded as a comment on 28297009), 28208180 (Comment, recorded as a comment on 28208174), 28208174 (Clinical Trial, Multicenter Study) and 28257531 (typed only Journal Article; a research report with its own comment, 28257532). By the classes above that is 2 `comment_on_other`, 2 `research_typed`, 2 `untyped` and 0 `reciprocal`. The census's own hand read adds one `untyped` (39808434, 2025). These 6 links stay in the population. They are 0.3% of it and cannot move any share by more than 0.4 points. Results will also be given without them.

Lesson from census v1: a pilot taken from striking or first-in-file cases overstated prevalence (96% earlier in the pilot, 38% in the census). So the thresholds below are set well under the pilot's 33%.

## Hypotheses (JAMA Network; each needs at least 100 read targets, else "untestable")

- **H1:** at most 5% of read targets are `reciprocal`. (Census v1: 0 of 300 sampled bare-DOI targets linked back, both kinds mixed.)
- **H2:** at least 10% of read targets are `comment_on_other`. These are comments that PubMed records as being on a different article.
- **H3:** at least 10% of read targets are `research_typed`. These are research articles or reviews, not comments.

**Void rule:** if more than 2% of the 1,786 JAMA Network links end in `unread` (failed lookups), the run is void and is reported as void, not scored. `link_gone` and `not_in_pubmed` are real-world outcomes and are reported, not voided.

## Reported without prediction

- Class shares by era (2016-2023, 2024, 2025-2026) and by journal; the 30 control links.
- After scoring, a seeded hand read of up to 20 `untyped` targets (titles and JAMA Network article type where visible), to estimate how many are invited commentaries typed only "Journal Article". This is exploratory and labelled as such.

## What the results can and cannot say

If H1 and either H2 or H3 hold, the same-issue bare-DOI links are, to a measurable degree, not comments on the record by PubMed's own data. That would extend census v1's "not a comment" reading from the earlier kind to part of the same-issue kind. It would not show who creates the links: we have not seen the publisher XML. `untyped` targets can still be real commentaries. Publication types are NLM's indexing, which is itself imperfect.

No one at JAMA Network, the AMA, NLM or any author has been contacted, and no one will be about an unchecked result.
