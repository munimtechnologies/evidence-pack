# DOI stubs, census v1 results: 61 more OpenAlex records whose DOI is a bare journal stem; the Unicode hyphen explains Wiley's share, but not all of them (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Scored against the pre-registration `doi-stub-census-prereg-v1-2026-10-16.md` (evidence-pack v0.4.10, commit 8ac37ca). Timing, stated exactly: the plan and code were written in the run folder before the job was queued. The sealed job ran 21:38:47-21:43:16Z, and the publish lane, which commits at the end of each run, made the plan public at 21:43:22Z, 6 seconds after the job finished. The agent run that wrote the plan did not see the job's results. Readers who need a public timestamp before the data should weigh that. Code: `stub_census.py` (commit 1e3632b); its 18 offline tests passed in the sealed job. Sealed job `stub-census-v1` ran 2026-10-16 21:38-21:43Z; outputs: `stub_census_results.json`, `stub_census_records.jsonl`, `stub_census_citer_reads.jsonl`. 234 keyless OpenAlex calls (reported cost $0.0234), none refused or failed. Research information about bibliographic data, not medical advice.

## Verdicts
| | Prediction | Result | Verdict |
|---|---|---|---|
| H1: at least 5 stub records beyond the 12-stem pilot | supported | **61 new stems** found as exact OpenAlex DOIs | **supported** |
| H2: of Wiley citers of dash stubs with a readable deposit, at least 80% carry a Unicode-dash DOI in that journal | supported | **165 of 190 = 86.8%** (Wilson 95% CI 81.3-90.9%) | **supported** |
| H3: of dash stubs with at least 50 citers, at least 75% have a Wiley citer share above twice the baseline (baseline 4.06%) | supported | **24 of 37 = 64.9%** | **not supported** |

## What the census found
- **Sample.** 6,000 seeded OpenAlex works (seed 20261019; articles 2000-2025 with at least 50 citations) gave 1,120 distinct stems (909 cut at the first hyphen, 211 at the first parenthesis). Looked up with the 12 pilot stems as exact DOIs: **73 stems exist as OpenAlex records (74 records; `10.1007/978` is held by two records).** Together they carry **63,194 citations**: 38,965 on the 12 pilot stems and **24,229 on the 61 new ones**.
- **Two kinds of record, which the pre-registration did not separate well enough.** The census looked up each stem in Crossref (60 most-cited records):
  - **33 stems are not registered DOIs** (25 new, 8 pilot). These are errors: a real item, often an unrelated one, carrying a truncated DOI. They hold **56,438 citations**. The largest new ones: `10.1111/j.1468` W4200558553 (6,460 citations; a 2021 conference record, "Taming Black Swans ... Plenary Session"), `10.1111/j.1365` W3010910207 (5,302; a 2016 paper on gastropods in Lake Malawi), `10.1016/s1470-2045` W2786429208 (1,631; a 2011 Lancet Oncology trial), `10.1111/j.1469` (1,219), `10.1088/0957` (888), `10.1641/0006-3568` (638), `10.1007/978` (423), `10.1186/s13054` (347), `10.1016/s1473-3099` (332; a Lancet Infectious Diseases study).
  - **27 stems are registered in Crossref**, mostly as journal-level DOIs (Emerald's `10.1108/ejim`, `10.1108/ijsms` and others; `10.1530/eje`, `10.1530/joe`, `10.1515/jpem`, `10.21037/tlcr`; three pilot BMJ stems). OpenAlex has these as "paratext" records titled with the journal's name. The DOI itself is real, but most citations to a journal's title record are misdirected citations to one of its articles. They hold 6,702 citations. The pre-registration said a registered stem "would be a real DOI, not an error". H1 as coded counted these too (a deviation, below). Counting only unregistered new stems, H1 is still supported (25 ≥ 5).
- **Medicine is hit hardest by The Lancet's DOIs.** The Lancet family's five stub records (`10.1016/s0140`, `s0140-6736`, `s1470-2045`, `s1473-3099`, `s1470`) hold **36,359 citations**. BMJ's six (`bmjopen`, `annrheumdis`, `archdischild`, `heartjnl`, `thoraxjnl`, `jmedgenet`) hold 3,921.
- **One stem covers many journals.** `10.1111/j.1365` is the start of every Blackwell-era DOI that embeds an ISSN beginning 1365-. The 8 Wiley deposits read for it cite seven different journals (for example `j.1365‐2141` British Journal of Haematology and `j.1365‐2648` Journal of Advanced Nursing). Its citations rose from 84 (2022) to 2,301 (2024) and 1,774 (2025), the same 2024-25 jump as the BMJ Open stub.
- **Impossible dates.** 3,436 citers of the 33 unregistered records are dated before the record's own year. The count is 5,388 across all 60 detailed records, but journal-title records carry arbitrary years. The extreme case is `10.1111/j.1468`, where 2,678 of 6,460 citers come before 2021.

## Mechanisms (citer reads: 10 seeded citers per record, Crossref deposits)
1. **Wiley's Unicode hyphens (confirmed, H2).** 165 of 190 readable Wiley deposits carry the cited DOI with U+2010 in place of the hyphen. Hand check, 2026-10-16: Pediatric Blood & Cancer 10.1002/pbc.31002 deposits four references as `10.1111/j.1365‐2141....`, all `doi-asserted-by: publisher`. A DOI pattern stops at the U+2010, which leaves `10.1111/j.1365`.
2. **Publishers that deposit the stem itself (new).** In 79 reads the citer's own deposit already holds the bare stem as the reference DOI ("exact"). They come from 34 Springer Nature-family deposits (Springer 21, Research Square 7, Nature 2, BMC 2, Atlantis 2), 9 Taylor & Francis-family, 6 Frontiers, 4 Emerald, 4 Wiley, 3 OUP, 3 Brieflands, 3 CEUR and 13 others. 75 of the 79 are asserted by the publisher. Hand check: Die Onkologie (Springer) 10.1007/s00761-023-01462-2 deposits two references with `"DOI":"10.1016/S1470-2045"`, while each reference's own text gives the full DOI, e.g. `10.1016/S1470-2045(19)30456‑5`. The DOI was cut at "(" before it was deposited. **This is how the parenthesis stubs arise.** Paren-stub reads: 17 exact, 11 intact, 1 absent, 51 with no reference list. The paren stubs' Wiley shares are 0-6.8%.
3. **Crossref's own matcher, rarely.** 4 of the 79 exact reads are `doi-asserted-by: crossref`, and all 4 point to stems that are registered journal-level DOIs (`archdischild`, `ccij`, `s00335` twice).
4. **Unexplained.** The 329 dash-stub reads not counted as Wiley (a bucket that also holds every citer without a reference list) split into 58 exact, 42 intact, 113 with no DOI in the stub's journal and 116 with no Crossref reference list. For the last two groups the links come from a source we cannot see, so their links come from a source we cannot see (possibly references parsed from full text). For `10.1111/j.1468`, all 10 sampled citers have no reference list.

## Where the stub records themselves come from (hand check, after the job, 6 records)
We read the OpenAlex records of the six largest medical or medically relevant stubs on 2026-10-16 (W3120106258, W2594075087, W4288364210, W2786429208, W3010910207, W3125180703):
- **None carries a PMID or PMCID**, and all have an empty `indexed_in`. Tools that look citations up by PubMed ID do not see these counts. Tools that rank by OpenAlex record or by DOI do.
- **Five of six carry a Microsoft Academic Graph (MAG) id.** The primary location of five is an institutional or library repository (AECID Library, LSE Research Online, an Earth Sciences EPrints repository, Hispana, Digital Commons@Becker), not the journal. Only `10.1016/s1470-2045` sits under The Lancet Oncology. In two records, the repository file linked from the record appears, by its name, to be a different document from the record's title.
- So the likely life cycle is: a repository or MAG record picks up a truncated DOI; the truncated DOI becomes the record's DOI; then every reference truncated the same way, by any route above, is matched to it. This is an inference from six records, not a test.

## Why H3 failed
13 of the 37 eligible dash stubs are below twice the Wiley baseline. 7 are Emerald journal-level DOIs (`10.1108/ejim`, `ijsms`, `jfmm`, `ccij`, `jcom`, `jfbm`, `medar`; Wiley share 0.5-4.8%), fed by Emerald and others rather than by Wiley. One is the registered IOSR journal DOI `10.9790/3008`. Five are unregistered: `10.1111/j.1468` (7.2%), the IOP stems `10.1088/0957` and `10.1088/1742`, and the book stems `10.1007/978` and `10.1016/b978`. The pilot's picture (Wiley's hyphen explains the stubs) holds for most medical dash stubs, but not for the stub population as a whole. **Post-hoc only:** restricted to the 19 unregistered dash stubs, the share is 14 of 19 (73.7%), still below 75%.

## Deviations from the pre-registration
- H1 counted stems found as OpenAlex DOIs, including stems that Crossref registers as journal-level DOIs. The plan defined a stub as an error and said registered stems are not errors. The sensitivity count (25 unregistered new stems) is given above, and the verdict is the same.
- H1 counts stems, not records: 61 new stems, 62 new records.
- No other deviations. Records 61-74 (by citations) got no per-record calls, as planned (cap of 60). Their 54 citations are counted in the totals.

## Limits
- Ten citers per record is a small read. The publisher counts in mechanism 2 come from 79 reads, not from a census of depositors.
- The sample is drawn by article, so stems from journals with few well-cited articles are under-found. 61 new stems is a floor, not an estimate of the total.
- "Registered in Crossref" was one lookup per stem. A 404 was taken as unregistered.
- We do not know OpenAlex's reference parser. The routes above are inferred from deposits and outcomes.

## Prior art (searched again 2026-10-16)
Cioffi et al. (arXiv 2111.11263) classify invalid DOIs in Crossref reference deposits and how to correct them. The stems deposited by Springer Nature and others (mechanism 2) are invalid DOIs of that general kind. We found no report of: OpenAlex records whose own DOI is such a stem, the citations they absorb, U+2010 as a route into them, or Crossref matching references to journal-level DOIs. A 2025 review of OpenAlex (arXiv 2512.16434) reports inflated citation counts on individual records from a different cause, duplicate versions. If earlier reports exist, we will cite them.

## What a user of OpenAlex citation counts can do today
- Drop any record whose DOI is in `stub_census_records.jsonl`, or more generally any DOI that ends where a journal's DOIs continue (before a hyphen or "(").
- Treat journal-title ("paratext") records with large citation counts as misdirected, not as citations of the journal.
- Before matching DOIs, map U+2010, U+2011 and the other dashes to "-", and reject a DOI that stops right before "(".

No one at OpenAlex, Crossref or any publisher has been contacted. This public note is the report.
