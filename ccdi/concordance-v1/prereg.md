# Pre-registration: attribute concordance of participants across the CCDI Data Ecosystem (ccdi-concord-v1)

MV2 of Munim, Inc. Written 2026-10-22 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name, before the job runs. No human has reviewed it. Code: Apache-2.0; this text: CC BY 4.0.

## Question
The CCDI Participant Index (CPI) links the same child's records across NCI's Childhood Cancer Data Initiative resources. Its 2026 paper (Jagu et al., JCO Clin Cancer Inform 10:e2500387, PMC13068442) reports 63,875 of 443,476 participants mapped across two or more domains, but it quantifies no conflicts: researchers are told to "make informed decisions about potentially conflicting data from multiple sources". We found no published count of how often linked records disagree on basic attributes. This job makes that count from open data only, as preliminary work for a Track 2 Milestone 1 entry in NCI's Childhood, Adolescent and Young Adult Cancer Data Innovation Challenge.

## Data (all open access, no login)
- CCDI Data Federation Resource API v1 (federation.ccdi.cancer.gov/api/v1): `/subject/summary`, `/subject/by/{sex,race,ethnicity,vital_status,age_at_vital_status,depositions}/count`, `/info`, every page of `/subject` and of `/subject-mapping` (unfiltered pages only; no query by participant ID).
- NCI Genomic Data Commons `/cases` for program TARGET: submitter ID, project, sex at birth, race, ethnicity, vital status, days to death, age at diagnosis, days to last follow-up.
- Joins: the COG Universal Subject Identifier (USI, `P` + 5 capital letters) taken from the TARGET submitter ID (`TARGET-NN-USI`), matched exactly to federation subject names or identifier names, and to CPI mapping entries whose associated domain is `USI`; and CPI `organizational_identifier` links between federation sources.

## What we saw before writing this (disclosed so it is not mistaken for prediction)
On 2026-10-22, by hand: the subject summary totals (PCDC 24,432; Treehouse 12,723; StJude 14,681; KidsFirst 38,440; ccdi-ecDNA 3,205; ccdi-iusccc-pst 504; CCDI-DCC 59,795); the vital-status count table (KidsFirst total 2,576 with 0 missing; PCDC 0 missing); the sex count table (KidsFirst total 38,439); one subject per source from page 1 (the PCDC one has vital_status null); a 2-per-source page of `/subject-mapping`; that PCDC answers an ID-filtered query with "NotFound" (small-cohort protection); GDC TARGET has 6,543 cases; two TARGET-NBL cases. Nothing else.

## Hypotheses (graded by analyze.py; thresholds fixed here)
- **H1.** KidsFirst serves 38,440 subjects within 1% on its pages, and at least 30,000 of them carry no vital status (so the count endpoint's vital-status total of 2,576 with "0 missing" does not describe the served records).
- **H2.** At least 95% of PCDC subjects served on pages carry no vital status, while the count endpoint reports 0 missing for vital status.
- **H3.** At least 1,000 distinct TARGET USIs link to at least one federation subject.
- **H4.** Among GDC-federation pairs where both records give male or female, sex disagrees in at most 1%. Not testable under 100 pairs.
- **H5.** Among GDC-federation pairs where both give Alive or Dead with ages on both sides, "alive after death" (the Alive record's age exceeds the Dead record's age at death by more than 1 day) is at most 1%; and among pairs with Alive or Dead on both sides, "alive then dead" (consistent with later follow-up) is at least 2%. Not testable under 100 pairs, or if the median federation-to-GDC age ratio lies outside 0.5-2 (different age units).
- **H6.** At least 50 USIs appear in two or more TARGET cases in the GDC, and none of them disagrees on sex.
- **H7.** At least 1,000 distinct cross-source pairs asserted by the CPI resolve to served subjects on both ends, and sex disagrees in at most 1% of those with male or female on both sides (fail if under 1,000 pairs).

Descriptive only (no prediction): per-field agreement between count endpoints and served records for every source; ethnicity and race agreement; age-at-death agreement; age-at-diagnosis agreement inside the GDC; vital-status disagreement direction; how many CPI links resolve to served subjects, by target domain; how many participants a naive union of sources counts twice.

## Rules
- Comparisons per (USI, federation subject): the GDC side is the USI's first case in (project, submitter ID) order. "Unknown", "Not reported", "Not allowed to collect", "U" and nulls are uninformative, never disagreements. Race compares sets of the five OMB categories: agree, overlap or disagree.
- Ages are in days on both sides (the GDC: age at diagnosis plus days to death, or plus the latest follow-up day).
- Outputs are aggregates only: no participant IDs and no participant-level rows leave the job. Raw responses stay inside the sealed job; their SHA-256 values are published in fetch-log.json.
- Requests are sequential with a 2-second pause, identified by a User-Agent naming MV2 of Munim, Inc.
- Any analysis not listed here, or any change after the results are seen, is labelled post hoc.
