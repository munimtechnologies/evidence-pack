# Comment links and notices in the reference lists of two ReGen evidence packages (2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

## What was done

Every PubMed record cited by MV2's two draft ReGen evidence packages was read in live PubMed (E-utilities esummary JSON, `references` array) on 2026-10-18 at about 02:30 UTC. The packages are metformin for knee osteoarthritis (package 5) and spironolactone for alcohol use disorder (package 4). For each record we read every "Comment in", "Retraction in", "Expression of concern in" and "Erratum in" entry. For every comment link we then read the target: its publication types, its own "Comment on" list and its date. Bare-DOI targets (links with no PMID) were resolved with esearch `"<doi>"[doi]` and their Crossref records were read.

This is the reading that `commentin_check.py` automates, done by hand because the sandbox queue is busy. All counts are hand counts from the API responses and are labelled as such.

- Package 5: 36 PMIDs, the 35 cited plus the cited erratum.
- Package 4: 14 PMIDs, one of them shared with package 5. That makes 49 distinct records.

## Results (hand counts)

**Notices.** None of the 49 records carries a "Retraction in" or "Expression of concern in" link. One carries an "Erratum in" link: the 2019 ACR/Arthritis Foundation guideline (31908163, erratum 33913629). Package 5 already cites it with its erratum.

**Comment links.** All 7 records that have them are in package 5. Package 4's 13 other records have none.

| Record (PMID) | Links with PMID | Bare-DOI links |
|---|---|---|
| Pan 2025, JAMA (40274279) | 0 | 2 |
| Dieleman 2020, JAMA (32125402) | 0 | 7 |
| Knowler 2002, NEJM (11832527) | 8 | 0 |
| Kolasinski 2020, Arthritis Rheumatol (31908163) | 2 | 0 |
| Bannuru 2019, Osteoarthritis Cartilage (31278997) | 2 | 0 |
| Zhu 2022, CMAJ (36535678) | 1 | 0 |
| Lim 2022, Osteoarthritis Cartilage (35597372) | 1 | 0 |
| **Total** | **14** | **9** |

- **Links with a PMID: 14 of 14 targets are typed Comment** (as Letter, Editorial, News or Journal Article plus Comment) **and list the record under "Comment on".** They are what the link says.
- **Bare-DOI links: 0 of 9 targets list the record under "Comment on".** In Crossref, 8 of 9 are dated before the record. In PubMed, all 9 are.

**The two JAMA records**
- **Pan 2025** (already reported in `commentin-check-v1-2026-10-18.md`): both targets are older JAMA Network items, a 2023 cohort study that the trial cites (36939700) and a 2024 Patient Page (39541114).
- **Dieleman 2020**, "US Health Care Spending by Payer and Health Condition, 1996-2016" (JAMA, 2020-03-03): it has 7 bare-DOI links, and all 7 targets are in PubMed.
  - **Six are earlier JAMA research reports on health spending (2016-2019):** 28027366, 29114831, 29536101, 30140875, 30912822, 31821423. All are typed Journal Article and none has a "Comment on" list. Three of them have PMID-linked comment lists of their own, as research articles do. Dieleman 2020's Crossref reference list cites 2 of the 6 (its group's 2016 and 2017 papers) and not the other 4. So the links are not simply the record's own references.
  - **One is a likely real commentary that PubMed cannot recognise:** Ayanian, "The Complex Mosaic of Health Care Spending in the United States" (JAMA Health Forum, 10.1001/jamahealthforum.2020.0238, PMID 36218585). It is written by that journal's editor, and its 5 Crossref references include Dieleman 2020. But its PubMed record is typed only Journal Article and has no "Comment on" link back.

## Date conflict

PubMed dates the Ayanian piece 2020/03/02 and Dieleman 2020 2020/03/03, so it looks one day earlier than the record it comments on. Crossref gives both 2020-03-03 (it puts 2020-03-02 only on the Health Forum issue). Census v1 used Crossref dates, so this link is in the population of the pre-registered `commentin-targets-v1` study ("earlier": false).

`commentin_check.py` uses PubMed sort dates, so it **would flag this link `earlier`**. That is a false positive for a link that is probably a real comment. The flag was always meant as "read this before citing it as commentary", not a verdict. This is the first case we have of the two date sources disagreeing about direction.

The code is deliberately left unchanged for now. The pre-registered job fetches `commentin_check.py` from main when it runs, so changing it would change a study's code after registration. A day-level tolerance, or a check against Crossref dates, is noted for a later version.

## Exposure note for the pre-registered study

The Dieleman 2020 to Ayanian link is one of the 1,786 JAMA Network links that `commentin-targets-v1` will classify. We read it after registration and before the job ran. By that study's rules it will be classed `untyped` (read, no comment type, no "Comment on"). Results will be given with and without it and the 6 disclosed pilot links. One link can move a share by at most 0.06 points.

## What this changes in the packages

- **Neither package cites any comment-link target as commentary.** Package 5 cites Baker 2023 (36939700) as a cohort study, which it is, and cites Dieleman 2020 only for its spending estimate.
- The one item package 5 calls a commentary, Chen, Ruan & Ding 2025 (40609734), is typed Editorial in PubMed and has no comment links, so it is described correctly.
- A one-line addition to the reference-check paragraph of package 5 (E.6) is warranted: two of its JAMA references carry bare-DOI "Comment in" links (2 and 7) that are not comments on them, and none was used as one.

## Limits

- The API responses were read through a fetch tool that summarises pages. The key fields were requested verbatim, and two records were re-read as raw JSON, but a transcription slip is possible. The sandbox job `integrity-live-v1` (queued) checks the same packages' DOIs by code.
- Two reference lists are a small, non-random sample. The contrast between PMID links (14 of 14 real) and bare-DOI links (0 of 9 reciprocal) agrees with census v1, but it adds no statistical weight.
- Calling the Ayanian piece a "likely commentary" rests on its title, its author's role and its references; we did not read its text.

No publisher, database or author has been contacted.
