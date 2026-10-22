# CCDI concordance census (pre-registered, v1)

MV2 of Munim, Inc. Code Apache-2.0; text and aggregate data CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.

**Question:** when NCI's Childhood Cancer Data Initiative (CCDI) Participant Index links one child's records across resources, how often do those records disagree on sex, race, ethnicity, vital status or age? The Participant Index paper (Jagu et al., JCO Clinical Cancer Informatics 2026;10:e2500387) counts 63,875 participants mapped across two or more domains, but it reports no conflict rates. We found no published count.

**Data:** open-access only. The CCDI Data Federation Resource API (federation.ccdi.cancer.gov) and the NCI Genomic Data Commons (TARGET cases). There is no login, no controlled-access data, and no query by participant ID.

**Results (2026-10-22): six of seven predictions held; H5 failed.** See `results.md`. In short:
- Where both linked records hold a value, they almost always agree. Sex disagrees in 7 of 19,702 Participant Index pairs (0.04%).
- The larger problem is missing values. Vital status is missing on one or both sides in 93% of linked pairs. Two sources' count endpoints report values or completeness that their served records do not carry: PCDC serves no vital status while its count endpoint reports 0 missing, and KidsFirst's endpoint covers 2,576 of 38,440 records.
- Alive-versus-Dead conflicts cluster in one source pair: CCDI-DCC | ccdi-ecDNA, 145 of 1,089 (13.3%).
- Pooling the 7 sources naively over-counts children by at least 17,731 records (11.5%).

**Files**
- `prereg.md`: hypotheses H1-H7 with fixed thresholds, written before the job ran. It also lists what had already been seen by hand.
- `fetch_ccdi.py`: fetches every page. Requests are sequential and every response is logged with its SHA-256.
- `analyze.py`: produces aggregate counts only (no participant IDs or rows) and grades H1-H7.
- `test_analyze.py`: tests on made-up records (`python -m unittest -v test_analyze`).
- `job.json`: the sealed job that runs the tests, then the fetch, then the analysis.
- `results.md`: grades, the main numbers, post-hoc notes (labelled), and limits.
- `out/concordance.json`: every aggregate the job produced, unchanged.
- `out/fetch-log.json`: URL, status, size and SHA-256 of every response.

**Privacy:** CCDI resources guard small cohorts. We publish only aggregates; the raw responses stay inside the sealed job.

**Purpose:** preliminary work toward a Track 2 Milestone 1 entry by Munim, Inc. in NCI's Childhood, Adolescent and Young Adult Cancer Data Innovation Challenge. This is research information, not medical advice.
