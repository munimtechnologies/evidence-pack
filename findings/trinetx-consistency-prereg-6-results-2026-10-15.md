# Are the numbers in TriNetX abstracts internally consistent? A pre-registered random-sample check

MV2 of Munim, Inc., 2026-10-15 (published 2026-10-16). Research and drafting by AI agents working in MV2's name. Every number was copied from PubMed, and the arithmetic is in code. A sealed run (job trinetx-audit-v1, 11 unit tests passing) reproduced every count below. Text CC BY 4.0; code Apache-2.0.

## Why this matters
- TriNetX is a federated EHR platform with push-button cohort analytics. Papers using it rose from about 33 a year in 2020 to nearly 2,700 in 2025 (Science, June 2026).
- Earlier critiques looked at designs and authorship patterns:
  - Lin et al., Eur J Epidemiol 2026, PMID 41721987: index-event designs that the platform can't produce.
  - Wang, SSRN 7323739: inconsistencies in 16 papers from one team.
- **We know of no published check of whether the printed numbers in a *random* sample of TriNetX papers agree with themselves.** That is what this audit does. The search was run on 2026-10-15.

## Method (pre-registered before any abstract was read)
- **Pre-registration:** `trinetx-consistency-prereg-6-2026-10-15.md`, written about 19:55Z on 2026-10-15, before the frame was fetched. It was kept in MV2's work folder and first committed here together with these results, so its date rests on the run record, not on a public timestamp.
- **Selection log:** `trinetx-consistency-selection-log-2026-10-15.md` has every id read, with the reason for each exclusion.
- **Frame:** PubMed `TriNetX[tiab] AND hasabstract AND 2025/01/01:2026/09/30[edat]`, giving N = 3,252.
- **Sample:** 40 systematic picks at retstart = floor(k·N/40). An ineligible pick moved on to the next record, at most 5 times.
- **Unit:** the first three hazard, odds or risk ratios with a labelled 95% CI in each abstract, copied as printed.
- **Checks:** `rwe_recheck.py`, the same tool used on the ReGen dossiers.
  - **centre:** the estimate sits at the log-scale CI midpoint, allowing for rounding.
  - **width / crude-table:** run where the same sentence prints both arms' events and denominators.
- **Benchmark:** Georgescu & Wren 2018 (PMID 29309530) found 5.6-7.5% of ratio/CI items discrepant across MEDLINE.

## Results
- **Sample:** 67 abstracts read; 39 papers and 102 estimates analysed. Pick k = 36 was dropped after six ineligible records in a row.
- **Primary: 2 of 102 estimates (2.0%; Wilson 95% CI 0.5-6.9%) fail the midpoint check.** Under the pre-registered rule this is **consistent with the MEDLINE benchmark**. The point estimate is lower, but the interval overlaps 5.6-7.5%.

| PMID | Estimate as printed | CI midpoint | Likely reading |
|---|---|---|---|
| 42243216 (Sci Rep 2026) | HR = 1.402, 95% C.I.= 0.599-28.60 | 4.14 | No simple slip explains it. A limit of 2.860 would give a midpoint of 1.309. The upper limit that fits 1.402 and 0.599 is about 3.28. |
| 40905294 (Spine 2026) | RR: 0.909; 95% CI: 0.834-0.980 | 0.904 | A small gap, but beyond rounding. The printed P = 0.0123 fits neither 0.909 (P ≈ 0.020) nor 0.904 (P ≈ 0.014) exactly. |

- **Re-fetch:** both flagged rows were fetched a second time and matched word for word.
- **Secondary:**
  - 2 of 39 papers (5.1%; 1.4-16.9%) have at least one flag.
  - Only 1 paper (2 estimates, JAHA 2025, PMID 39921523) printed both arms' counts next to its odds ratios. Both rebuild exactly from the 2x2 table: 0.670 (0.633-0.710) and 0.777 (0.755-0.800).
- **In plain words:** in this sample, TriNetX abstracts' ratio/CI arithmetic is about as clean as MEDLINE's, or cleaner. That fits numbers exported from a platform rather than typed by hand.

## Exploratory (not pre-registered; say so if cited)
- **P-value check:** 15 estimates printed a P value in the same parenthesis. One doesn't fit its own CI:
  - PMID 40353424 (Curr Drug Saf 2025) prints OR 1.013 (95% CI 0.880-1.166) with P = 0.121.
  - The CI implies P ≈ 0.86. The paper's four other P values all match their CIs.
- **Reporting gap:** 11 of the 67 abstracts read (16%) print hazard, risk or odds ratios with a P value but no CI.
- **Seen outside the first-three rule, so not counted:**
  - PMID 40996400 prints "OR, 2.35; 95% CI, 2.37-4.13": the estimate lies outside its own interval.
  - PMID 40759247 describes HR 1.212 (95% CI 1.044 to 1.406) as "no significant differences".

## Limits
- **Abstracts only.** Full-text tables may correct or differ from these numbers.
- **Few count checks.** TriNetX abstracts rarely put counts and denominators in the same sentence as the estimate, so the strong count-based checks could run on only 2 rows.
- **Transcription.** A language-model fetch tool did the reading, so a transcription error is possible. Every flagged row was confirmed by a second fetch; unflagged rows were not.
- **Ordering.** PubMed's pub_date sort put records in an order that is not chronological. The frame order is recorded as fetched.
- **A flag is not an accusation.** It says a number needs a second look, not that a conclusion is wrong. No author has been contacted.

## Reproduce
`python trinetx_audit.py trinetx_rows.json --out result.json` and `python -m unittest test_trinetx_audit`. The expected values in the tests were computed by hand before the code ran.
