# Results: Hindawi journal-year sinks in OpenAlex (v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

Pre-registration: `hindawi-sink-prereg-v1-2026-10-17.md` (committed before the run). Code: `hindawi_sink.py`. Job `hindawi-sink-v1`, run in MV2's sandbox on 2026-10-17 22:28-22:38 UTC: offline tests passed, then 160 old and 80 new journal-years were examined with **0 failed examinations and 0 failed listing calls**. Data: `hindawi_sink_v1_results.json`, `hindawi_sink_v1_journal_years.jsonl` (every journal-year, its 25 most-cited works with OpenAlex and Crossref counts), `hindawi_sink_v1_reads.jsonl` (every citer read).

## Verdicts, exactly as `hindawi_sink.py` computed them

| | Prediction | Result | Verdict |
|---|---|---|---|
| H1 | at least 40% of scored 2016-2019 journal-years have a sink | **11 of 100 (11%)** | **not supported** |
| H2 | at most 5% of scored 2022-2023 journal-years have one, and fewer than old (Fisher p < 0.01) | 0 of 65; p = 0.0032 | supported |
| H3 | at least 70% of sink citers labelled sibling or unsupported are sibling; calibration: at least 70% of control citers are genuine | 105 of 114 (92%); calibration 106 of 106 | supported |
| H4 | OpenAlex also links the sibling's own work in at least 80% of sibling references with DOIs | 66 of 66 | supported |
| H5 | sink's share of citations dated up to 2021 exceeds its control's (sign test p < 0.01), sinks' median share at least 0.90 | 11 of 11 pairs; p = 0.00049; median 0.993 (controls 0.342) | supported |

**4 of 5 predictions held. The one that failed is the one about how common sinks are.** We predicted that most Hindawi journal-years from the Microsoft Academic Graph era would have one; about one in nine does. Where a sink exists, everything else we predicted about it held: its citers cite a *different* paper of the same journal-year with first page "1", OpenAlex keeps the correct link and adds the sink on top, almost all of the sink's citations are dated 2021 or earlier, and no sink appears in 2022-2023.

Why only 100 of 160 old (and 65 of 80 new) journal-years were scored: a journal-year needs at least 10 of its top 25 works to be 10.1155 DOIs of that year. Several sampled journals were published by Wiley in those years and moved to Hindawi later, so their top works carry Wiley DOIs (for example, Journal of Tissue Engineering and Regenerative Medicine 2017 kept none). This was the pre-registered rule.

## The 11 sinks (descriptive)

Phantom citations = OpenAlex minus Crossref.

| Journal-year | Sink DOI | OpenAlex | Crossref | Share dated to 2021 |
|---|---|---|---|---|
| BioMed Research International 2016 | 10.1155/2016/5186461 | 1,772 | 20 | 0.99 |
| Stem Cells International 2016 | 10.1155/2016/3846971 | 524 | 6 | 1.00 |
| Evid Based Complement Alternat Med 2017 | 10.1155/2017/4212534 | 312 | 5 | 1.00 |
| Evid Based Complement Alternat Med 2018 | 10.1155/2018/7378608 | 228 | 2 | 1.00 |
| Oxid Med Cell Longev 2019 | 10.1155/2019/7621561 | 217 | 1 | 1.00 |
| Mathematical Problems in Engineering 2018 | 10.1155/2018/3905879 | 133 | 1 | 0.98 |
| Journal of Diabetes Research 2019 | 10.1155/2019/9134280 | 124 | 11 | 0.94 |
| Mathematical Problems in Engineering 2016 | 10.1155/2016/5269236 | 119 | 0 | 0.98 |
| Stem Cells International 2019 | 10.1155/2019/7378594 | 106 | 6 | 0.95 |
| International Journal of Endocrinology 2018 | 10.1155/2018/3093208 | 98 | 1 | 1.00 |
| Journal of Ophthalmology 2019 | 10.1155/2019/9382467 | 81 | 5 | 0.98 |

Total phantom citations over the 11 sinks: **3,656** (by year 2016: 2,389; 2017: 307; 2018: 455; 2019: 505; 2022-2023: 0). One journal-year had more than one work over the sink thresholds. The sink was the journal-year's most-cited work in OpenAlex in 3 of 11. The International Journal of Endocrinology sink is a "Response to: Comment #2" letter, credited with 98 citations.

The two pilot journal-years (held out, never scored) are unchanged: BioMed Research International 2017 (10.1155/2017/6353510, 1,178 against 8) and Oxidative Medicine and Cellular Longevity 2018 (10.1155/2018/5879281, 363 against 10).

## Read by hand (2026-10-17, after scoring)

- **Sibling, confirmed.** J Diabetes Complications 2021 (10.1016/j.jdiacomp.2021.107996) is an OpenAlex citer of the J Diabetes Res 2019 sink (W2945690941, which is in its OpenAlex `referenced_works`). Its Crossref deposit has no reference to the sink. Its reference bb0165 is Canivell, "J Diabetes Res", volume "2019", first page "1", DOI 10.1155/2019/2018374: a different paper of the same journal-year.
- **Sibling, confirmed.** Phytother Res 2019 (10.1002/ptr.6346), an OpenAlex citer of the eCAM 2017 sink: its deposit cites Chen Q., eCAM volume 2017, first page 1, DOI 10.1155/2017/5140297, and nothing with the sink's DOI or title.
- **"Unsupported", but probably the same thing.** J Mater Res 2020 (10.1557/jmr.2020.108), an OpenAlex citer of the Int J Endocrinol 2018 sink, was labelled unsupported. Its deposit has one 10.1155 reference: a bare DOI, 10.1155/2018/9041694, with no journal, volume or page. That DOI is another Int J Endocrinol 2018 paper (in fact this journal-year's control). The deposit carries no page "1", so the classifier could not call it a sibling. OpenAlex presumably got the page from its own parsing of the article. One case, read after scoring: some of the 9 "unsupported" citers may belong to the same mechanism.

## What this adds, and prior art

- A post on the OpenAlex community forum (G. Schubert, 2025-02-26, "Publications with many more citations in OpenAlex than in other databases") reported a 2019 Scientific Reports paper with 1,787 OpenAlex citations against 30-40 elsewhere, cause unknown. We have not checked whether that case is a page-"1" sink. We did not find a published explanation or census.
- Our earlier studies (`article-number-1-*`) showed the page-"1" mechanism at MDPI and Frontiers. This census shows it at Hindawi, a large medical publisher, with a negative control and a held-out pilot. It also shows it is **not** the norm there (11%), which we did not expect.
- The fault appears to be inherited from Microsoft Academic Graph (citations dated to 2021, none after), but the inflated counts are still live in OpenAlex today.

## Practical advice for users of OpenAlex counts

For a 2016-2019 Hindawi paper, compare OpenAlex's `cited_by_count` with Crossref's `is-referenced-by-count`. A ratio of 10 or more with nearly all citations dated up to 2021 is the sink signature. Read a few citers' Crossref references before trusting the count. `doi_hygiene.py link` checks a single link of this kind.

## Limits

- Only the 25 most-cited works per journal-year were examined, which biases H1 downwards. A sink outside the top 25 is missed, so 11% is a lower bound for sinks this large.
- The sink thresholds (E >= 10 and a gap of 50) were set after seeing two pilot sinks.
- The study cannot see OpenAlex's or MAG's code; the mechanism is inferred from what the deposits contain.
- AI agents designed, ran and scored this study. Pre-registration limits goalpost-moving but is not an independent check.

No one at Hindawi, Wiley, OpenAlex or OurResearch, and no author, has been contacted.
