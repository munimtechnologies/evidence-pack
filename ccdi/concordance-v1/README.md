# CCDI concordance census (pre-registered, v1)

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.

**Question:** when NCI's Childhood Cancer Data Initiative (CCDI) Participant Index links one child's records across resources, how often do those records disagree on sex, race, ethnicity, vital status or age? The Participant Index paper (Jagu et al., JCO Clinical Cancer Informatics 2026;10:e2500387) counts 63,875 participants mapped across two or more domains, but it reports no conflict rates. We found no published count.

**Data:** open-access only. The CCDI Data Federation Resource API (federation.ccdi.cancer.gov) and the NCI Genomic Data Commons (TARGET cases). There is no login, no controlled-access data, and no query by participant ID.

**Files**
- `prereg.md`: hypotheses H1-H7 with fixed thresholds, written before the job ran. It also lists what had already been seen by hand.
- `fetch_ccdi.py`: fetches every page. Requests are sequential and every response is logged with its SHA-256.
- `analyze.py`: produces aggregate counts only (no participant IDs or rows) and grades H1-H7.
- `test_analyze.py`: tests on made-up records (`python -m unittest -v test_analyze`).
- `job.json`: the sealed job that runs the tests, then the fetch, then the analysis.

**Status:** pre-registered on 2026-10-22. Results will be added next to these files, unchanged, with any post-hoc analysis labelled as such.

**Privacy:** CCDI resources guard small cohorts. We only publish aggregates, and the raw responses stay inside the sealed job.

**Purpose:** preliminary work toward a Track 2 Milestone 1 entry by Munim, Inc. in NCI's Childhood, Adolescent and Young Adult Cancer Data Innovation Challenge. This is research information, not medical advice.
