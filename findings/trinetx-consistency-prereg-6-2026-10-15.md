# Pre-registration 6: internal consistency of ratio estimates in a random sample of TriNetX papers

MV2 of Munim, Inc. Written 2026-10-15, about 19:55Z. No abstract in the frame had been read when this was written. Research and drafting by AI agents working in MV2's name. Text CC BY 4.0. Code Apache-2.0.

## Why
- In 2025, nearly 2,700 papers cited the TriNetX federated EHR platform (Science, June 2026).
- Prior work checked these papers' designs, not their numbers:
  - Lin et al., Eur J Epidemiol 2026 (PMID 41721987): 13 papers whose index-event designs can't be built on the platform.
  - Wang, SSRN 7323739: inconsistencies in 16 papers from one authorship team.
- Georgescu & Wren 2018 (PMID 29309530) ran the CI-midpoint check over all of MEDLINE and found 5.6-7.5% of items discrepant.
- As far as a search on 2026-10-15 shows, nobody has run a rounding-aware consistency check, including a count-based CI-width check, on a **random sample** of TriNetX papers.
- TriNetX gives a strong check that general corpora lack. Its built-in analyses run on 1:1 propensity-matched cohorts. So a printed risk ratio is the crude ratio of the printed counts. A Cox HR's CI should also be about as wide as sqrt(1/a + 1/b) from the event counts.

## Sampling frame (fixed before any record is read)
- **Query:** PubMed esearch `TriNetX[tiab] AND hasabstract AND 2025/01/01:2026/09/30[edat]`, with sort=pub_date.
- **Freeze:** N is the count esearch returns at the time of the first fetch. Record the time and N in the selection log.
- **Picks:** for k = 0..39, retstart = floor(k * N / 40), retmax = 1. That gives 40 picks spread evenly over the frame.
- **Ineligible picks:** if a pick is ineligible, move to retstart + 1, and repeat until an eligible record is found (at most 5 steps, then drop that k). Every step goes in the log.
- **Eligible:** the abstract reports at least one hazard, odds or risk ratio with a 95% CI from an analysis that used TriNetX data. Meta-analyses, reviews, letters with no estimate, and papers using TriNetX only as a comparator are ineligible.

## Extraction
- **Source:** the PubMed abstract only (efetch rettype=abstract, retmode=text).
- **Which estimates:** the first 3 ratio estimates with a 95% CI, in reading order. Each is copied as printed: the estimate, lo and hi as strings.
- **Counts:** if the same sentence gives event counts for both arms (n, or percentage plus denominator), record them as a, b, na, nb. Counts are derived from a percentage only when the denominator is printed, and are marked as derived.
- **Verification:** every row that a check flags is re-fetched in a second, independent fetch and compared verbatim. If the two copies differ, the second fetch decides. The row is kept, and the difference is logged.

## Checks (rwe_recheck.py, from run 26, unchanged)
- **centre:** the estimate lies at the CI's log-scale midpoint, allowing for rounding.
- **width:** only for rows with counts. Flagged if the widest CI the rounding allows is below 0.67 x sqrt(1/a + 1/b).
- **crude:** only for rows printed as a risk ratio or odds ratio with all four counts. These are crude by construction on matched cohorts, so they are marked crude=true. Flagged beyond 3 count SEs.

## Outcomes and decision rules
- **Primary:** the share of estimates with a centre flag, with a Wilson 95% CI. Benchmark: Georgescu & Wren's 5.6-7.5%.
  - Call the rate **higher than MEDLINE** only if the Wilson lower bound is above 7.5%.
  - Call it **lower** only if the upper bound is below 5.6%.
  - Otherwise call it **consistent with the benchmark**.
- **Secondary:**
  - the share of papers with at least one flag of any kind;
  - the share of count-bearing rows flagged by width or crude.
- **Clustering:** report the share of papers as well as the share of estimates, since estimates within a paper aren't independent. No significance test beyond the Wilson intervals.
- **Reporting:** results are reported whatever they show. A flag says a number needs a second look, not that a paper is wrong.

## What will not be done
- No author is contacted about a flag before a person has checked it and Sheehan has approved the contact.
- Flagged papers are named in the results with their PMIDs. The write-up states the checks' limits and that abstracts round.
- No full texts are used. That keeps the check reproducible from public abstracts alone.
