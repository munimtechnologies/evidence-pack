# A citation sink in the open indexes: Bunney et al. 2017 (Physiol Behav 176:139-148). v1 results

MV2 of Munim, Inc., 2026-10-16. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.

- Pre-registration: `findings/citation-sink-prereg-v1-2026-10-16.md`. It was frozen locally before the job ran and is first published here with the results, as it said it would be.
- Job `sink-check-v1`: sealed container, 2026-10-16 15:13-15:15Z, 10/10 offline tests passed.
- Code: `sink_check.py`, with tests in `test_sink_check.py`.
- Data:
  - `sink_v1_results.json`;
  - `sink_v1_target_citers.jsonl` and `sink_v1_control_citers.jsonl`;
  - `sink_v1_crossref_refs.jsonl`.
- Follow-up pre-registration, published here before its job runs: `findings/citation-sink-prereg-v2-2026-10-16.md`.

## In one paragraph
Bunney et al. 2017 is a mouse study of orexin and non-exercise activity. The open indexes count it as heavily cited: OpenAlex 2,067, OpenCitations 1,557, Crossref 1,191 (read 2026-10-16). A related paper from the same lab has 70 OpenAlex citations. In the first 200 OpenAlex citers, 82.5% are off-topic by a broad, fixed rule, against 7.1% for that control paper. Reading the publisher-deposited references behind 120 of those citations shows the cause. **Only 10 of the 107 readable references name Bunney's paper.** The other 97 cite other works (cancer immunology, single-cell methods, periodontitis and many more). Their references carry either Bunney's journal, volume and first page ("Physiol Behav 176:139") or Bunney's DOI. Most of the paper's index citation count appears to be misdirected citations. The papers those authors meant to cite are missing them.

## Pre-registered tests
| | Plan | Result |
|---|---|---|
| H1 (sink) | Off-topic share ≥ 70% for the target, ≤ 30% for the control, Wilson CIs disjoint | **Holds on a partial, non-random sample (deviation 1).** Target: 165 of 200 = 82.5% (95% CI 76.6-87.1). Control: 5 of 70 = 7.1% (3.1-15.7), which is every control citer. |
| H2 (onset) | 2020-21 vs 2017-19 | **Untestable**: only 5 of the 200 are from 2017-2019, under the planned minimum of 10. |
| H3 (PMC contexts) | descriptive | **Not run**: none of the 200 records had a PMCID in OpenAlex (deviation 2). |
| H4 (deposited references) | descriptive | In a random 150 (seed 20261016), 120 references point at Bunney and 30 list no such reference. The job's counts are 10 with Bunney's real title, 10 with an "HHS Public Access" banner, and 56 with no Bunney DOI. The hand read is below. |

Off-topic share by citing year, among the 200: 2019 4/4, 2020 66/77, 2021 73/92, 2022 14/15, 2023 8/10 (2018 and 2024 have 1 each).

## Deviations
1. **Only the first 200 of 2,067 target citers were read.** OpenAlex returned HTTP 401 for the second cursor page, four times. Keyless OpenAlex requests now share a small daily budget per IP address (stated in the API's own `meta.notice`, 2026-10-16), and the sandbox's address had evidently used it up. The 200 are the first page in OpenAlex's default order, not a random sample. Their years match the index-wide pattern (2020-2021 dominate), but H1 has not had its planned test. **v2 re-runs it on every citer.**
2. **H3 had no input**, because OpenAlex gave no PMCIDs for these 200. v2 fills them in from the PMC ID Converter.
3. The job counted 56 of the 120 found references as "no Bunney DOI". Hand reading shows this lumps two different things together. 48 of them have no DOI at all, and 8 carry another work's DOI, sometimes glued to the start of a title (`10.1111/micc.12461.Establishment`). The counts in the job output are as run; the split is by hand.

## Hand read of the 120 found references (one read, by hand from the job's output; v2 checks it with a fixed rule, H6)
| Class | n | What it looks like |
|---|---|---|
| Names Bunney's paper (title or author) | **10** | e.g. "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) caused by high-fat diet ... Bunney 2017 Physiol. Behav." |
| DOI only, nothing else deposited | 13 | `ref28/cit28 publisher 10.1016/j.physbeh.2017.03.040`: the intended work can't be told |
| Another work's title, with "Physiol Behav 176:139" swapped in | **59** | e.g. "Mechanisms of resistance to PD-1 and PD-L1 blockade, Nowicki 2019, Physiol. Behav. 139/176"; "Integrating single-cell transcriptomic data across different conditions ... Butler 2017, Physiol Behav 176:139" |
| Another work, with its own journal but Bunney's DOI attached | **21** | e.g. "The neurovascular unit coming of age ... Iadecola 2017 Neuron 96:17" with DOI 10.1016/j.physbeh.2017.03.040; "Update on prevalence of periodontitis ... Eke 2015 J. Periodontol. 86:611", same DOI |
| Another author, a banner or a garbled template, no title | 17 | e.g. "176 Koh A. 2017 Physiol. Behav.", "ref_383 HHS Public Access 176 Rodney 2017 Physiol. Behav.", "139 176 2018 Physiol. Behav." |

Readable references (all except DOI-only): **10 of 107 name Bunney = 9.3% (Wilson 95% CI 5.2-16.4%).**

The 10: keys `1052_CR217`, `ref_11`, `10.1016/j.drup.2020.100718_bib0080`, `10.1007/s13311-022-01228-5_bib214`, `10.1016/j.neuropharm.2018.11.017_bib32`, `B25`, `ref_37`, `2303_CR92`, `ref_71`, `10.1016/j.ccr.2020.213736_b0455`.

The 13 DOI-only: `ref28/cit28`, `154`, `ref41`, `CIT0079`, `e_1_2_7_235_1`, `e_1_3_4_6_1`, `ref64/cit64`, `cit0022`, `B13`, `e_1_2_7_7_1`, `e_1_3_3_67_2`, `ref94/cit94`, `e_1_2_9_4_1`.

**Who put Bunney's DOI there (by hand, the 64 references carrying it):**
- 47 were asserted by the **publisher**: 2 genuine, 13 DOI-only, 32 other works.
- 17 were asserted by **Crossref's** matching: 8 genuine, 9 other works.

So most wrong links were deposited by publishers from the authors' reference lists. Crossref's own matching then adds more, for references whose journal, volume and page had been swapped.

**One paper, several swaps (spot check by hand, Crossref, 2026-10-16):** 10.1016/j.bbcan.2021.188526 deposits four different references with journal "Physiol. Behav." and volume "176" (keys bb0110, bb0185, bb0225 and bb0300; three of them with first page 139). They are cancer-immunology papers by Nowicki 2019, Hyochol Ahn 2017 (twice) and Christopher 2016. An index counts that as one citation of Bunney, but four intended papers lose one each.

**A shared template:** in this sample, four references in four different citing papers read (a fifth is the case that started this study, PMID 42489790) `乳鼠心肌提取 HHS public access ... Physiol. Behav. 176 139` ("乳鼠心肌提取" is Chinese for "neonatal rat cardiomyocyte extraction"). Ten carry the "HHS Public Access" banner that NIH author manuscripts in PMC show. Bunney 2017 is itself an NIH author manuscript (PMC5510739).

## What this does and does not show
- **Shown, for this sample:** most references that the open indexes link to Bunney 2017 are about other papers. The links come from wrong metadata deposited by publishers, plus Crossref's matching on journal/volume/page. Anyone who uses Crossref, OpenCitations or OpenAlex counts for this paper is mostly counting errors.
- **Not shown:**
  - which reference manager or database spread the wrong record. The working hypothesis is that one shared library record, for NIH author manuscripts with the "HHS Public Access" banner, carried Bunney's metadata. The 2019 onset and the 2021 peak fit that idea, but this study can't test it;
  - whether the share holds across all 2,067 citers (v2);
  - the authors' intent. In every class the authors appear to have meant another, real paper. Nothing here suggests misconduct.
- **Prior art (searched 2026-10-16):** related problems are documented:
  - "sneaked references": deliberately added reference metadata (Besançon et al., JASIST 2024, doi 10.1002/asi.24896);
  - invalid DOIs in Crossref data (Heibi, Peroni et al., arXiv 2111.11263);
  - an OpenAlex community thread on works with inflated counts caused by wrong DOIs in citing articles.

  We found no report on this paper, and none of one paper soaking up well over a thousand citations through a shared journal/volume/page or DOI substitution.

## Next
- `sink-check-v2` (pre-registered in `citation-sink-prereg-v2-2026-10-16.md`):
  - all citers;
  - 300 random reference reads with a fixed rule (H5: genuine share upper bound < 25%);
  - the rule checked against this hand read (H6);
  - OpenCitations' citer list;
  - PMC contexts.
- Not planned: contacting Elsevier, the authors, Crossref, OpenAlex or OpenCitations. A public write-up is the report; any contact is Sheehan's call.
