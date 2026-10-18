# Results: PubMed "Comment in" links without PMIDs at JAMA Network (census v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

Pre-registration: `pubmed-commentin-census-prereg-v1-2026-10-17.md`, with the operational amendment `pubmed-commentin-census-prereg-v1-amendment-2026-10-17.md` (both committed before this run). Code: `pubmed_commentin.py` v1.1. Job `pubmed-commentin-v2`, run in MV2's sandbox on 2026-10-17 23:17-23:36 UTC: offline tests passed; **29,310 records fetched, 0 failed, 0 errors, `"void": false`**, so the run is scored. The 61 pilot records were held out. Data: `pubmed_commentin_v1_results.json` (counts, verdicts, full search log), `pubmed_commentin_v1_nopmid_links.jsonl` (every link without a PMID, with Crossref dates and titles), `pubmed_commentin_v1_reciprocity.jsonl`.

Groups: 13 JAMA Network journals against 4 controls (N Engl J Med, Lancet, BMJ, Ann Intern Med), every record from 2016-2026 that PubMed marks `hascommentin`.

## Verdicts, exactly as `pubmed_commentin.py` computed them

| | Prediction | Result | Verdict |
|---|---|---|---|
| H1 | bare-DOI entries are at least 2% of JAMA Network "Comment in" entries and at most 0.5% at the controls | **2,877 of 23,758 (12.1%)** against 85 of 23,209 (0.37%) | supported |
| H2 | at least 80% of dated bare-DOI links point to an earlier target, and at most 5% of PMID links do | **1,091 of 2,877 (37.9%)**; PMID links 63 of 2,999 (2.1%) | **not supported** |
| H3 | at most 10% of resolved bare-DOI targets list the source in their own "Comment on", and at least 90% of PMID targets do | **0 of 300**; PMID targets 300 of 300 | supported |
| H4 | at least 90% of bare-DOI targets are JAMA Network DOIs (10.1001) | 2,877 of 2,877 | supported |

Shares are hand-computed from the counts in `results.json`.

**3 of 4 predictions held.** The failed one matters for how the finding is read, so it comes first.

## What H2's failure shows: two kinds of bare-DOI link

The pilot (26 of 27 targets earlier than the record) did not generalise. Of the 1,786 bare-DOI links at JAMA Network whose target is **not** earlier, 1,684 have a target dated in the same calendar month as the source, and (counting both groups) only 9 have a target in a later year. The ones we read are companion pieces published on the same day, for example the invited commentary that JAMA Network Open publishes alongside a study. So the bare-DOI links are a mix of:

1. **Earlier related articles (1,091 links, 38%).** Earlier trials, cohorts, USPSTF statements, Patient Pages. These cannot be comments on the record. They look like the publisher's "related articles" list carried into PubMed's "Comment in" field.
2. **Same-issue companion pieces (most of the rest).** These may well comment on the record, but the link carries no PMID, and the commentary's own PubMed record does not link back.

The mix has shifted over time (hand-computed from `nopmid_links.jsonl`): the earlier kind is 729 of 1,319 links (55%) for records dated 2017-2023, 131 of 379 (35%) in 2024, and 231 of 1,179 (20%) in 2025-2026.

H3 (0 of 300 reciprocal) holds for both kinds, so the pre-registration's reading "not comments" was too strong. The data support **"not reciprocal, and not resolved to a PMID"** for all of them, and **"not a comment"** only for the earlier kind. All 300 sampled bare-DOI targets resolved to exactly one PubMed record by DOI, so the PMID existed and was simply not attached.

## Onset and spread (reported without prediction)

Share of JAMA Network records with at least one bare-DOI "Comment in" link:

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Records with comment links | 1,472 | 1,598 | 1,747 | 1,660 | 1,858 | 1,857 | 1,704 | 1,556 | 1,323 | 969 | 916 |
| With a bare-DOI link | 0 | 36 | 49 | 107 | 129 | 115 | 97 | 113 | 207 | 479 | 503 |
| Share | 0% | 2.3% | 2.8% | 6.4% | 6.9% | 6.2% | 5.7% | 7.3% | 15.6% | 49.4% | 54.9% |

By journal (2016-2026): JAMA Network Open 897 of 2,675 records (34%), JAMA 517 of 4,239 (12%), JAMA Health Forum 30 of 82; the other ten journals 2-9%. At the controls, BMJ and Lancet have none; Ann Intern Med has 26 records (76 links, all to its own prefix 10.7326) and NEJM 9 (to 10.1056), all dated 2020-2024. Control dating: 55 of 85 bare-DOI links earlier, 69 of 2,998 PMID links earlier; control reciprocity 0 of 85 and 300 of 300.

## Read by hand in live PubMed (E-utilities esummary, 2026-10-17, after scoring)

9 bare-DOI links on 3 records:
- **PMID 39808433** (JAMA Netw Open 2025, location of death in young adults with cancer): one link, `doi: 10.1001/jamanetworkopen.2024.53972`, no PMID. That DOI is PMID 39808434, a same-day piece titled "Location of Death Preferences in Adolescents and Young Adults With Cancer", typed only "Journal Article", with an empty link list: no "Comment on" back to 39808433.
- **PMID 38857021** (JAMA 2024, trends in preeclampsia risk factors): three links, all bare DOIs, including the USPSTF statements of 2017 (10.1001/jama.2017.3988, "Screening for Preeclampsia During Pregnancy") and 2021 (10.1001/jama.2021.14781).
- **PMID 38873722** (JAMA 2024, germline CDH1 variants): five links, all bare DOIs; four point to JAMA Oncology and JAMA Surgery papers from 2019-2022.

## Why it matters

Software, appraisal checklists and reviewers read "Comment in" as "this paper has been discussed". At JAMA Network, half of the records from 2025-2026 now carry such links without PMIDs. Tools keyed on PMIDs miss them; tools that count them count related articles as commentary; and the commentaries that really exist lose their link back to the paper. NLM's policy says a mere mention is not a comment. The fix would sit in the publisher's data supplied to PubMed. We have not seen that XML, so the cause stays a hypothesis.

Prior art: our pre-registration searched for reports of this pattern and found none; we have found none since.

## Limits

- `hascommentin` may not index every record with links.
- Crossref `published` dates can be issue dates, so "same month" groups companion pieces with other items from the same issue. We read 3 records, not a sample big enough to estimate how many same-month targets are true commentaries.
- The two-kind split, the era shares and the same-month count were computed after scoring, from the published per-link file. They are descriptive, not tests.
- AI agents designed, ran and scored this study. Pre-registration limits goalpost-moving but is not an independent check.

No one at JAMA Network, the AMA, NLM or any author has been contacted.
