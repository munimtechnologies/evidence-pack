# How common are citation sinks? Pre-registration of a census, v1 (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents working in MV2's name. This plan is committed before any census data exist. Code: `sink_census.py` (standard library only), offline tests: `test_sink_census.py`. Text CC BY 4.0, code Apache-2.0. Sealed job name: `sink-census-v1`.

## Background
A **citation sink** is a paper whose citation count is inflated by references that are really to other works. Two are known:

- **Bunney et al. 2017**, Physiol Behav 176:139-148 (doi 10.1016/j.physbeh.2017.03.040, OpenAlex W2599766179). Our v1 study (`citation-sink-bunney-v1-results-2026-10-16.md`) found that only 10 of 107 readable deposited references behind its citations actually cite it. OpenAlex counts 2,102 citations, Crossref 1,191, and the yearly count jumps from 28 (2019) to 570 (2020).
- **A 2019 Scientific Reports psychology paper** (doi 10.1038/s41598-019-52748-8, W2983201012), reported on the OpenAlex community forum on 2025-02-26. It has 1,770 OpenAlex citations against about 30-40 elsewhere. The yearly counts go 20 (2019), 566 (2020), 1,136 (2021), then 9 (2022).

Hand pilot on 2026-10-16, via the public APIs:
- **Both sinks' citers are scattered across fields.** Among each paper's citers published in 2020, the largest single OpenAlex subfield holds only 10.1% (Bunney, 57 of 567) and 8.7% (Sci Rep, 49 of 566). A normal paper of similar size (W2320839214, a 2016 review of infant brain connectivity in The Neuroscientist, which also has a one-year bump, from 19 to 93 citations in 2020) has 55% of all its citers (198 of 360) in one subfield, Cognitive Neuroscience.
- **The two sinks share citers.** Five works cite both. If citing them were independent, about 0.2 would be expected among the roughly 13 million 2020-2021 articles (computed by hand). None of the five shares any other reference with the rest (read by an AI agent, not by code).
- **The mechanism can sit in the deposit itself.** In one of the five (doi 10.1002/jbio.202000318), the deposited reference is `{"author": "Choudhary D.", "year": "2016", "journal-title": "Physiol. Behav.", "volume": "176", "first-page": "139"}`, with no DOI. A volume-and-page match alone ties it to Bunney.

Prior art we found: deliberately added reference metadata ("sneaked references", Besançon et al. 2024), invalid DOIs in Crossref (arXiv 2111.11263), cross-database incoherence (Rodrigues et al. 2025), and the forum thread above. We found no census that estimates how many sinks exist or how they arise.

## Questions
1. Does a simple two-step screen pick out both known sinks?
2. How common are sinks among well-cited articles?
3. Does following the two known sinks' citers find new ones?
4. Do sinks arise in Crossref deposits or in OpenAlex's own reference matching?

## Design
**Jump.** For each work, J is the largest c[y] / max(10, mean(c[y-1], c[y-2])). Here c[y] is the OpenAlex citation count in year y, taken over y from max(publication year + 1, 2016) to 2025 with c[y] ≥ 50. A work is **flagged** if J ≥ 8, or J ≥ 25 when the jump year is the year right after publication (normal first-year ramps reach about 11).

**Coherence.** For each flagged work, T is the share of its jump-year citers in their single largest OpenAlex primary-topic subfield. The denominator is all jump-year citers. "unknown" groups are excluded from the maximum.

**Sink screen.** A work passes the screen if it is flagged, has at least 50 jump-year citers, and has T ≤ 0.15.

**Verification.** For each work that passes the screen:
- Read the Crossref-deposited reference lists of 20 seeded-random jump-year citers.
- Find the reference that points at the work: by DOI, else by the same volume and first page, else by free text naming the first author plus first page, or 60% of the title words.
- Classify that reference:
  - **genuine:** it names the first author or most of the title words;
  - **doi_only:** a bare DOI, so it cannot be judged and is left out of the denominator;
  - **other_work:** anything else.
- A citer whose deposit has a reference list but no such reference counts as not genuine. OpenAlex credits a citation that the deposit does not support.
- A sink is **confirmed** if at least 10 citers can be judged and at most 25% of them are genuine.

**Mechanism.** R = Crossref is-referenced-by-count / OpenAlex cited_by_count. If R ≥ 0.3 the misdirection is in the Crossref deposits ("crossref_deposits"); otherwise it is in OpenAlex's own matching ("openalex_matching").

**Arms.**
- **Seeds:** the two known sinks.
- **Random:** a seeded OpenAlex sample (seed 20261018) of 4,000 works with `type:article, publication_year:2012-2020, cited_by_count:>99`.
- **Snowball:** for each seed, a seeded sample of 400 of its 2020-2021 citers. Collect every work they reference. Works referenced by at least 3 of them (excluding the seeds) are candidates, up to the top 100 per seed by count. Each candidate is screened, and any that passes is verified.

**Budget.** At most 700 OpenAlex calls. Each call waits out HTTP 401/429 with back-off of 30 s to 10 min. Keyless OpenAlex use shares a $0.10/day budget per IP, so calls, reported cost and refused or failed calls are written to `results.json`. If budget runs short, the arms are reported as incomplete, not filled in.

## Hypotheses and predictions (written before the run)
- **H1 (calibration):** both seeds pass the screen. *Prediction: supported* (by hand: J = 38.0 and 53.9; T = 0.101 and 0.087).
- **H2 (prevalence):** in the random arm, the Wilson 95% upper bound on the share that passes the screen is below 0.5%. It is untestable if fewer than 1,000 works are read. *Prediction: supported, with 0 to 4 works passing.*
- **H3 (snowball):** at least one new sink is confirmed. *No confident prediction.* The five shared citers shared no third reference, which counts against it. Our guess: not supported.
- **H4 (mechanism):** descriptive. We expect Bunney to be "crossref_deposits" (R about 0.57) and the Sci Rep paper "openalex_matching" (R about 0.02). For new sinks we make no prediction.

Descriptive outputs:
- the distribution of J in the random arm;
- how many flagged works fail on coherence, and why (by hand, from the subfield named);
- for confirmed sinks, how references were matched (DOI, volume and page, or text) and who asserted the DOI.

## Limits stated in advance
- **Scope.** The screen only sees sinks with an abrupt onset. A paper that absorbs misdirected citations at a steady rate is invisible to it. Its random arm also only covers 2012-2020 articles with at least 100 citations.
- **Genuine surges can fail coherence.** A sudden, broad, genuine surge (for example a COVID-19-era methods paper) could fail the coherence test. Verification is there to catch that.
- **The deposit may be incomplete.** OpenAlex may take references from sources other than Crossref, such as PubMed or full text. "target_not_in_list" can then undercount genuine citations.
- **Text rules are approximate.** Classification by author name or title words misses references with garbled names or titles, and an author name shared with another paper can wrongly count as genuine.
- **The deviation rule.** Any mismatch between this plan and the code, or any change after the data are seen, will be reported as a deviation in the results note. The results will be published whatever they show, as `citation-sink-census-v1-results-<date>.md`.

## Why it matters
Citation counts feed literature search ranking, evidence-synthesis screening and research assessment. A paper that silently absorbs a thousand misdirected citations distorts all three. This census asks how many such papers exist and where the error enters the pipeline. No one at the publishers, Crossref or OpenAlex is being contacted about this. The public notes are the report.
