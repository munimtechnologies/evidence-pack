# Citation sink, v2 results: Bunney et al. 2017 across all 2,067 OpenAlex citers (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Scored against `findings/citation-sink-prereg-v2-2026-10-16.md`, which was published before the job ran. Sealed job `sink-check-v2` ran 2026-10-16 19:01-19:06Z. Both steps exited 0: the offline tests (`test_sink_check_v2.py`), then `sink_check_v2.py`. Outputs are in `sink_v2_results.json` and the `sink_v2_*.jsonl` files next to this note.

**Target.** Bunney PE et al., "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) caused by high-fat diet", Physiol Behav 2017;176:139-148, doi 10.1016/j.physbeh.2017.03.040 (OpenAlex W2599766179).
**Control.** Zink AN et al., Int J Obes 2018, doi 10.1038/ijo.2017.276 (W2769845614), from the same lab, on the same topic.

## Counts (on the day of the run)
| | Crossref is-referenced-by | OpenCitations citers | OpenAlex citers (all fetched) |
|---|---|---|---|
| Bunney 2017 | 1,191 | 1,525 | 2,067 |
| Control | 63 | 61 | 70 |

This time every OpenAlex page was fetched for both papers, so the v1 deviation (only the first 200 citers read) does not apply.

## Pre-registered hypotheses
| | Rule | Result | Verdict |
|---|---|---|---|
| **H1** sink | target off-topic ≥ 70%, control ≤ 30%, Wilson CIs apart | target 1,720/2,067 = **83.2%** (81.5-84.8); control 5/70 = **7.1%** (3.1-15.7) | **supported** |
| **H2** onset | 2020-21 lower bound > 2017-19 point estimate | 2017-19: 20/33 = 60.6%; 2020-21: 1,082/1,280 = 84.5% (lower bound 82.4%) | **supported** |
| **H3** citing sentence (descriptive) | PMC full text, 80 of 823 citers with a PMCID | 46 had a citing sentence; **4 of 46** were on-topic. In 22 of 80 the article's own reference list does not contain Bunney at all; 7 had no full text; 5 had no locatable citing sentence | - |
| **H4** deposited reference (descriptive) | 300 random citers (seed 20261017), Crossref | 213 deposits contain a reference pointing at Bunney; 49 have a reference list without one; 34 have no list; 4 are not in Crossref. 22 of the 213 carry the "HHS Public Access" banner | - |
| **H5** main | genuine share among readable references, Wilson upper < 25% (needs ≥ 30) | **24 of 174 = 13.8%** (9.4-19.7) | **supported** (prediction about 10%) |
| **H6** rule check | rule reproduces the v1 hand read within ±2 | found 120, genuine 10, doi_only 13, other_work 97: identical | **supported**, see caveat |

**How the 150 misdirected references break down (H4).** 95 are a *journal swap*: "Physiol Behav 176:139" sits on another work's reference. 55 are *DOI attached*: Bunney's DOI sits on otherwise different metadata. 39 more are bare DOIs that cannot be judged. Who asserted the DOI on the 213 found references: the publisher on 119, Crossref's own matching on 42, and no DOI on 52.

**Genuine share by citing year (H4 sample).** 2020: 4 of 40; 2021: 4 of 68; 2022: 5 of 24; 2023: 4 of 18; 2024: 2 of 10; 2025: 2 of 9. The misdirection peaks in 2020-2021 and is still the majority afterwards.

**OpenCitations (descriptive).** 1,331 of its 1,525 citers are also OpenAlex citers. 194 are only in OpenCitations, and 727 OpenAlex citers are not in OpenCitations. In a random 300 of its citers (seed 20261018), 34 of 176 readable references are genuine (19.3%, 14.2-25.8%), and 87.3% of the 300 are off-topic by Crossref title and abstract.

## What this shows
- Bunney 2017's citation count is mostly misdirected in all three open indexes, not just OpenAlex. Roughly 5 in 6 of the deposited references that the indexes credit to it are references to other papers. Those papers lose the citations.
- The error is mostly in the **deposited metadata**: publishers' and Crossref's DOI assertions on references that name other works. It is not only OpenAlex's own matching. About a sixth of OpenAlex's links (49 of 300) have no support in the citer's own deposit, so OpenAlex adds a second, smaller layer.
- This is consistent with v1 (first 200 citers) and with the census note (`citation-sink-census-v1-results-2026-10-16.md`), where Bunney's Crossref/OpenAlex count ratio (0.57) put it in the "deposits" group.

## Caveats
- **H6 is not an independent accuracy check.** The rule was written after the v1 hand read, by the same AI agents, to encode it. Exact agreement shows the rule is the hand read written as code, not that both are right.
- The on-topic rule judges titles and abstracts. A genuine methods citation from an off-topic paper counts as off-topic. H5's reference-level read is the stronger evidence.
- "genuine" needs "Bunney", "nonexercise activity thermogenesis" or "orexin activation counteracts" in the reference. A correct reference with a garbled author and title would be missed. That pushes the genuine share down, so read 13.8% as a lower-leaning estimate. The upper bound (19.7%) is still far below the 25% cut.
- We cannot say which tool first put Bunney's volume, page and DOI on other works. 22 of the 213 references carry an NIH author-manuscript banner, which points at a reference-manager record built from PMC author manuscripts. That is a lead, not a finding.

No author, publisher, Crossref, OpenAlex or OpenCitations staff were contacted. This public note is the report.
