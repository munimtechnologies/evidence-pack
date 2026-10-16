# How common are citation sinks? Census v1 results (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Scored against `findings/citation-sink-census-prereg-v1-2026-10-16.md` (published 19:07Z, before the job ran). Sealed job `sink-census-v1` ran 2026-10-16 20:55-20:56Z. Both steps exited 0: 17 offline tests (`test_sink_census.py`), then `sink_census.py`. It used 53 OpenAlex calls ($0.0053), none refused or failed, so every arm is complete. Outputs: `sink_census_results.json`, `sink_census_random_rows.jsonl`, `sink_census_snowball_rows.jsonl` and `sink_census_verification_reads.jsonl`.

## Scores
| | Prediction | Result | Verdict |
|---|---|---|---|
| **H1** calibration | both seeds pass the screen | Bunney: J 38.0, T 0.101. Sci Rep 2019 (Conroy-Beam): J 53.9, T 0.087. Both confirmed by Crossref reads (0 genuine of 18 and of 20) | **supported**, as predicted |
| **H2** prevalence | Wilson upper < 0.5%, 0-4 passing | 4,000 works read, 8 flagged, **1 passed** (0.025%, Wilson 0.004-0.14%) | **supported**, as predicted |
| **H3** snowball | guess: not supported | **2 new sinks confirmed**: Scientific Reports 9:1 (Santos et al. 2019) and Nature Communications 9:1 (McCoy et al. 2018) | **supported**: our guess was wrong |
| **H4** mechanism | Bunney deposits (R ≈ 0.57); Sci Rep 2019 matching (R ≈ 0.02) | Bunney R 0.567 (deposits); Conroy-Beam R 0.023 (OpenAlex matching); the two new sinks R 0.84 and 0.88 (deposits) | as predicted for the seeds |

## The two "new" sinks were already known: article number 1
Both new sinks are the first article (article number 1) of an online-only Springer Nature journal volume:

| OpenAlex | DOI | OpenAlex / Crossref citations | Crossref reads |
|---|---|---|---|
| W2909240409 | 10.1038/s41598-018-37186-2 (Sci Rep **9**:1, airborne nitro-PAHs) | 8,494 / 7,152 | 0 genuine of 18 judged |
| W2777639606 | 10.1038/s41467-017-02088-w (Nat Commun **9**:1, super-black feathers) | 7,417 / 6,502 | 0 genuine of 10 judged |

The deposits show how it happens. People write page ranges such as "Sci Rep 9:1-17" for article-number journals, so the reference matches the one article in volume 9 whose "page" is 1. Three of the deposited references, verbatim from the job's reads:
- `Mousavi S et al (2019) Physiological, epigenetic and genetic regulation in some olive cultivars under salt stress. Sci Rep 9:1–17`, given Santos's DOI, asserted by Crossref (in 10.1007/s00344-020-10138-9);
- `Jeong, S. B. et al. Electrospray patterning of yeast cells for applications in alcoholic fermentation. Sci. Rep. 9, 1–7 (2019).`, given Santos's DOI, asserted by the publisher (in 10.1038/s41598-020-74146-1);
- `Weng, Z. et al. Active sites of copper-complex catalytic materials for electrochemical carbon dioxide reduction. Nat. Commun. 9, 1–9 (2018).`, given McCoy's DOI, asserted by the publisher (in 10.1038/s41467-019-10996-2).

**Prior art.** This mechanism is published: T. Kriváchy, "Incorrect Citation Association for Articles in Online-Only Springer Nature Journals", arXiv:2511.01675 (November 2025). It found that 5 of the 10 most-cited articles in both Scientific Reports and Nature Communications have article number 1, using Crossref, OpenCitations, Semantic Scholar and the journal sites. We found that paper only after the job ran. So H3's two sinks are an **independent rediscovery**, not a new finding. What they add is a check of the screen: without knowing the mechanism, the screen and the Crossref reads picked out the right papers. Our census adds that the same sinks are inflated in OpenAlex too, by about as much as in Crossref.

## The random-arm hit is new: an OpenAlex record whose DOI is just "10.1136/bmjopen"
The one random-sample work that passed the screen is **W4288364210**. Its DOI is `10.1136/bmjopen`, which is only the stem that every BMJ Open DOI starts with. It is titled as a 2014 protocol, but it has 2,230 OpenAlex citations, 1,090 of them from 2024 and 850 from 2025. The job's Crossref verification cannot judge it: there is no Crossref record for that DOI, so all 20 reads came out "target_not_in_list". The automatic "confirmed" is therefore uninformative. We checked it by hand through the APIs instead. The cause ties back to our dash census: **Wiley deposits DOIs with Unicode hyphens (U+2010)**, and the indexer apparently cuts the DOI at the first such hyphen. That finding, with more such records (one "Lancet" stub with 22,520 citations), is in `doi-stub-census-prereg-v1-2026-10-16.md`, together with a pre-registered census.

## Other descriptive results
- **Near misses that fit article number 1.** W2790756470 (Nat Commun **10**:1; 8,161 citations; T 0.160) failed coherence just above the 0.15 cut. W2905301720 (Int J Mol Sci **20**(1):1, an MDPI article; 1,093 citations; T 0.179) also failed. The MDPI case is outside the publisher family Kriváchy studied, which is a lead worth checking. We noted it after seeing the data, so it is not a test.
- **Two shapes over time** (OpenAlex counts by year, read 2026-10-16). The article-number sinks keep absorbing citations: Santos 2,228 (2021), 1,828 (2022) and 538 (2025). The OpenAlex-only sink (Conroy-Beam, R 0.02) collapses from 1,136 (2021) to 9 (2022), and so does Int J Mol Sci 20:1 (646, then 15). Microsoft Academic Graph, which OpenAlex built on, stopped at the end of 2021. So one **hypothesis**, not tested here, is that OpenAlex-only sinks whose citers stop in 2021 come from inherited MAG reference matching.
- **Screened but not confirmed.** The IPCC AR5 "Summary for Policymakers" (doi 10.1017/cbo9781107415324.004; 23,866 citations) passed the screen, but 4 of 15 judged references are genuine (27% > 25%).
- **Flagged works that failed coherence** include CA Cancer J Clin's GLOBOCAN 2018 (T 0.17), U-Net (T 0.56) and IQ-TREE (T 0.27). These are genuine surges, which is the case the coherence step is there for.
- **Random-arm jump distribution:** J < 4 for 3,835; 4-8 for 135; ≥ 8 for 30. None reached 25. Only 8 of the 30 were flagged, because the other 22 jumped in the year right after publication, where the bar is J ≥ 25.

## Deviations and limits
- **Verification rule, a small coding gap.** The volume-and-page fallback in `find_ref` can match a reference whose DOI points at a different paper. This happened in 2 of the 40 reads for the two new sinks (in 10.1371/journal.pbio.3000934 and 10.1371/journal.pone.0214552). Under the pre-registered rule, a deposit without a reference to the sink counts as not genuine either way, so neither verdict changes. McCoy's verdict rests on exactly the minimum of 10 judged references.
- "target_not_in_list" verifies nothing when the sink has no Crossref record, as with the bmjopen stub. Version 2 of the screen should mark such targets "unverifiable".
- The screen only sees sinks with an abrupt onset. Its random arm covers 2012-2020 articles with at least 100 citations.

No one at a publisher, Crossref, OpenAlex or the arXiv author was contacted. This public note is the report.
