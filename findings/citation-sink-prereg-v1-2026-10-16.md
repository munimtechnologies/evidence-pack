# Pre-registration: is Bunney et al. 2017 (Physiol Behav 176:139-148) a citation sink? (v1, 2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.
Frozen locally on 2026-10-16 before `sink-check-v1` runs. It will be published with the results, whatever they show.

## Where this came from

The phantom-references study (read 2, 2026-10-16) found a garbled reference in a 2026 meta-analysis (PMID 42489790, Crossref key 2348_CR121): "Kuschner O'connor, Butz AM (2017) 乳鼠心肌提取 HHS Public Access. Physiol Behav 176:139-148", with a DOI belonging to another journal. A Springer book chapter (10.1007/978-981-97-3115-2_3) carries the same template. Physiol Behav 176:139-148 is a real paper: Bunney PE, Zink AN, Holm AA, Billington CJ, Kotz CM, "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) caused by high-fat diet", doi 10.1016/j.physbeh.2017.03.040, PMC5510739, an NIH author manuscript (its PMC PDF carries the "HHS Public Access" banner).

Observations made before freezing this plan (OpenAlex and Crossref, 2026-10-16; these motivate the hypotheses and are not the test):
- OpenAlex W2599766179: cited_by_count 2,102. By year: 2017 3, 2018 2, 2019 28, 2020 570, 2021 724, 2022 284, 2023 206, 2024 139, 2025 101, 2026 40.
- Control: Zink AN et al., "Neuromodulation of orexin neurons reduces diet-induced adiposity", Int J Obes 2018, doi 10.1038/ijo.2017.276 (same lab, same topic, one year later). OpenAlex W2769845614: 70 citations, 1-13 per year, with no spike.
- A random sample of 25 OpenAlex citers from 2021 (seed 7): 24 had nothing to do with orexin, energy balance or activity (pressure ulcers, CT artefacts, Drosophila satellites and so on). One was on-topic.
- One off-topic citer (J Mol Histol 2025, seminoma; 10.1007/s10735-025-10565-6) deposits a complete, correct Bunney reference. So whatever the mechanism, the wrong citation is not always visibly garbled.
- A web search (three queries) found no report that this paper is miscited.

## Hypotheses

- **H1 (sink).** Classify each citing work as on-topic or off-topic with the fixed rule below. Supported if the off-topic share among Bunney 2017's citers is ≥ 70%, the control's is ≤ 30%, and the two Wilson 95% CIs do not overlap.
- **H2 (onset).** Among Bunney citers, the off-topic share in 2020-2021 is higher than in 2017-2019. Supported if the 2020-2021 lower Wilson bound exceeds the 2017-2019 point estimate. If 2017-2019 has fewer than 10 citers, H2 is reported as untestable.
- **H3 (context, descriptive).** For open-access citers in PMC, extract the sentence(s) where the Bunney reference is cited. Report the share whose sentence matches the on-topic rule. No threshold: this is for the hand read.
- **H4 (reference text, descriptive).** For a random sample of 150 Bunney citers with DOIs, read the publisher-deposited Crossref reference that points at Bunney. Report how many deposit no reference list, how many have "HHS Public Access" or "Author manuscript" in the reference, how many give Bunney's real title, and how many have a DOI other than Bunney's.

## On-topic rule (fixed; applied to title + abstract, as reconstructed from OpenAlex)

Case-insensitive regular expression: `orexin|hypocretin|thermogen|energy expenditure|energy balance|energy homeostasis|obes|adipos|physical activity|spontaneous activity|sedentar|high[- ]fat|locomot|feeding|food intake|body weight|weight gain|dreadd|hypothalam|metabol`. The case-sensitive word `NEAT` also counts.

The rule is deliberately broad: "metabol" and "hypothalam" pull many unrelated papers into "on-topic". That works **against** H1.

## Data and method

- OpenAlex API: every work with `cites:W2599766179` and `cites:W2769845614`, cursor-paged at 200 per page. Fields: id, doi, title, publication_year, abstract_inverted_index, ids.
- Crossref REST API: `/works/{doi}` for 150 Bunney citers drawn at random (Python `random.Random(20261016).sample` over citers with a DOI, sorted by OpenAlex id). The matching reference is the one whose DOI is 10.1016/j.physbeh.2017.03.040, or whose text has "176" and "139" and "Physiol".
- PMC: up to 80 Bunney citers with a PMCID (same seed), via efetch JATS XML. The reference is found by DOI or by its title ("nonexercise activity thermogenesis"); in-text citations by `xref rid`. Citations inside numeric ranges ("5-7") are missed, and that count is reported.
- Wilson 95% intervals throughout.

## Deviations policy

Any change after the job runs goes in a Deviations section with its reason. The rule and the thresholds will not change.

## Limits, stated now

- OpenAlex's citation links are themselves made by matching, so some "citers" may be OpenAlex errors, not the authors'. H4 (publisher-deposited references) is there to separate the two.
- A title and abstract can be off-topic while a citation is still legitimate: for example, a methods citation, or a review that touches on activity. H3's sentences give the hand read for that.
- No contact with any author, publisher, OpenAlex or Crossref is planned. Anything of that kind is held for Sheehan.
