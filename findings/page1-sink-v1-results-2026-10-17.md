# Results: OpenAlex citation sinks outside Hindawi, in journals whose articles all start at page 1 (v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

Pre-registration: `page1-sink-prereg-v1-2026-10-17.md` (committed before the run). Code: `page1_sink.py`. Job `page1-sink-v1`, run in MV2's sandbox on 2026-10-17 22:38-22:44 UTC: offline tests passed, 160 old and 80 new journal-years examined, **0 failed listing calls, 0 failed examinations, `"void": false`**, so the run is scored. Data: `page1_sink_v1_results.json`, `page1_sink_v1_journal_years.jsonl`, `page1_sink_v1_reads.jsonl`.

## Verdicts, exactly as `page1_sink.py` computed them

| | Prediction | Result | Verdict |
|---|---|---|---|
| H1 | at least 25% of scored 2016-2019 journal-years have a sink | **15 of 132 (11%)** | **not supported** |
| H2 | at most 5% of scored 2022-2023 journal-years have one, fewer than old (Fisher p < 0.01) | 0 of 70; p = 0.0013 | supported |
| H3 | at least 70% of sink citers labelled sibling or unsupported are sibling (n >= 40) | 15 of 31: n below 40 | **untestable** |
| H4 | OpenAlex links the sibling's own work in at least 80% (n >= 20) | 3 of 3: n below 20 | **untestable** |
| H5 | sink's share of citations dated up to 2021 beats its control's (sign test p < 0.01) and the sinks' median share is at least 0.90 | 15 of 15 pairs, p = 3.1e-5; but median **0.66** (controls 0.32) | **not supported** |

**1 of 5 predictions held, 2 failed and 2 could not be tested.** The page-"1" sink we found at Hindawi, MDPI and Frontiers does **not** generalise to journals that merely give every article pages 1-N. Sinks are as rare here as at Hindawi (11%), their citations are not concentrated in the Microsoft Academic Graph era, and too few of their citers deposit usable references to test the mechanism (67 of the 119 labelled sink citers had fewer than 5 deposited references). The only prediction that held is the era one: no sink in 2022-2023.

13 sampled journal-years were mostly Hindawi DOIs and were set aside as the pre-registration said.

## What the 15 "sinks" are (descriptive, read after scoring)

They are a mix, and **8 of the 15 are records that stand for a whole journal**: their title is the journal's own name.

| Journal-year | Record | OpenAlex | Crossref | Kind |
|---|---|---|---|---|
| Indian Journal of Science and Technology 2019 | 10.17485/ijst | 1,913 | 27 | journal-level record |
| IEEE Photonics Journal 2016 | 10.1109/jphot.2016.2530561 | 224 | 7 | article |
| Pesquisa Brasileira em Odontopediatria e Clinica Integrada 2019 | 10.4034/pboci.2019.191.61 | 201 | 16 | article |
| Journal of Global Oncology 2018 | 10.1200/jgo.18.21100 | 194 | 2 | article |
| British Microbiology Research Journal 2016 | 10.9734/bmrj | 136 | 7 | journal-level record |
| Journal of Biomedical Optics 2016 | 10.1117/1.jbo.21.9.099801 | 119 | 7 | erratum |
| Journal of Scientific Research and Reports 2019 | 10.9734/jsrr | 109 | 10 | journal-level record |
| IMF Staff Country Reports 2016 | 10.5089/9781475529685.002 | 107 | 0 | report |
| IMF Working Paper 2019 | 10.5089/9781498302708.001.a001 | 105 | 1 | report section |
| IEEE Trans Applied Superconductivity 2016 | 10.1109/tasc.2016.2610258 | 98 | 0 | journal-level record |
| Revista Panamericana de Salud Publica 2017 | 10.26633/rpsp | 89 | 2 | journal-level record |
| Journal of Economics, Management and Trade 2019 | 10.9734/jemt | 74 | 0 | journal-level record |
| IMF Staff Country Reports 2018 | 10.5089/9781484376881.002 | 67 | 0 | report |
| Microbiology Research Journal International 2019 | 10.9734/mrji | 65 | 1 | journal-level record |
| J Geography, Environment and Earth Science Int 2019 | 10.9734/jgeesi | 64 | 3 | journal-level record |

"Kind" is from the title alone, except for the first row. Checked by hand on 2026-10-17: Crossref registers 10.17485/ijst as type `journal` (no date, 27 citations). OpenAlex has it as W4213255817, type `paratext`, `is_paratext: true`, year 2019, and 1,913 citations dated **2012-2026** (406 in 2016 alone, 33 in 2025). So it collects citations from before and after the MAG era, from works that probably cite some IJST article. That is a different failure from the page-"1" sink. Five of the eight journal-level records belong to one publisher's DOI prefix (10.9734).

By DOI prefix, old era: 10.9734 had sinks in 5 of 38 journal-years, IEEE (10.1109) 2 of 16, SPIE (10.1117) 1 of 15, ACM (10.1145) 0 of 10, ASCO (10.1200) 1 of 4, IMF (10.5089) 3 of 4. Phantom citations (OpenAlex minus Crossref) over all 15: 3,482, of which 1,886 are the IJST record.

## What we learned

- **A design flaw, stated plainly:** the census did not exclude journal-level or paratext records, so its sink rule picked them up. They are real count errors but not the mechanism under test, which diluted H3 and H5. We will not re-score this run; a follow-up that excludes `is_paratext` records would have to be pre-registered as a new version.
- **The page-"1" sink is not a general property of page-1 journals.** At MDPI and Frontiers (article 1 of each volume) and at Hindawi (one record per journal-year) the mechanism is confirmed. In IEEE, SPIE, ACM and ASCO journals with the same page structure, we found few sinks: 4 among 45 journal-years, one of them a journal-level record. Why some page-1 journals get sinks and others do not remains open.
- **Prior art on journal-level records:** the OpenAlex community forum has discussed highly cited table-of-contents and other paratext records (N. Haupka and G. Schubert, 2025-02-26), and OpenAlex offers an `is_paratext` flag. So the journal-level records are a known kind of error. The counts above are new as far as we found, but we claim no discovery for them.

## Limits

- Top 200 sources per year and the 25 most-cited works per journal-year only.
- The sink thresholds came from the Hindawi pilot and were not tuned here.
- Titles were classified by eye after scoring; only the IJST record was checked in both Crossref and OpenAlex.
- AI agents designed, ran and scored this study. Pre-registration limits goalpost-moving but is not an independent check.

No publisher, OpenAlex or OurResearch staff member, or author has been contacted.
