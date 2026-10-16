# Pre-registration v2: Bunney et al. 2017 as a citation sink, full population (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.
Frozen on 2026-10-16 (~17:00Z) before job `sink-check-v2` runs, and published before its data exist. The results will be published whatever they show.

## Why a v2
v1 (`findings/citation-sink-prereg-v1-2026-10-16.md`; results in `findings/citation-sink-bunney-v1-results-2026-10-16.md`) planned to read **every** OpenAlex work citing Bunney PE et al., "Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT) caused by high-fat diet", Physiol Behav 2017;176:139-148 (doi 10.1016/j.physbeh.2017.03.040). OpenAlex refused the second cursor page (HTTP 401). Keyless OpenAlex calls now draw on a small shared daily budget per IP address. So v1 read only the first 200 of 2,067 citers, in OpenAlex's default order, not at random. H1 held on those 200, but that is a deviation, not the planned test. Also, v1 found no PMCIDs among them, so H3 could not run.

v2 runs the v1 plan on the full population and adds the reference-level hypotheses that the v1 hand read suggested.

## Unchanged from v1
- Target, control (Zink AN et al., Int J Obes 2018, doi 10.1038/ijo.2017.276), the on-topic rule (title + abstract regex), the thresholds, H1-H4 as written, and the Wilson 95% intervals.
- The code reuses `sink_check.py` (v1) unchanged.

## Changes (method only)
1. **Paging.** OpenAlex is read by page number (200 per page), with waits of 30 s, 60 s, 2 min, 5 min and 10 min after a refusal. If any page is still refused, H1 is reported as **incomplete** (with the counts fetched) and is not scored.
2. **PMCIDs.** The PMC ID Converter API fills in PMCIDs that OpenAlex lacks. H3 is still descriptive.
3. **Reference sample.** H4 uses 300 random OpenAlex citers (seed 20261017), instead of 150 drawn from the first page.

## New hypotheses
Each deposited Crossref reference that points at Bunney (by DOI, or by text containing "176", "139" and "Physiol") is classed by a fixed rule:
- **genuine:** the reference contains "Bunney", "nonexercise activity thermogenesis" or "orexin activation counteracts";
- **doi_only:** it has nothing but its key, the DOI and who asserted the DOI;
- **other_work:** anything else, meaning it names other authors or another title.

other_work references are split into two kinds:
- **journal_swap:** "176", "139" and "Physiol" appear in another work's reference;
- **doi_attached:** Bunney's DOI sits on otherwise different metadata.

- **H5 (main).** Among found, readable (not doi_only) references in the 300-citer sample, the genuine share has a Wilson upper bound **below 25%**. It needs at least 30 readable references, otherwise it is untestable. Prediction: about 10%, from the v1 hand read (10 of 107).
- **H6 (rule check).** Applied to the same 150 citers as v1, the rule reproduces the v1 hand read to within ±2 on each count: found 120, genuine 10, doi_only 13, other_work 97. The hand read was made before this rule was written down. A failure means the rule, not the data, is in question, and both are reported.

## Descriptive (no thresholds)
- The citation counts in Crossref (`is-referenced-by-count`), OpenCitations and OpenAlex, for the target and the control. On 2026-10-16, by hand: 1,191 / 1,557 / 2,067 for the target.
- OpenCitations' citer list: its overlap with OpenAlex's, and a random 300 (seed 20261018) classed by the same reference rule. Topic is judged from Crossref's title and abstract.
- The genuine share by citing year (does the sink start in 2019-2020?).
- Who asserted the DOI: publisher or crossref.

## Stated now
- The working explanation is a hypothesis, not a finding: some reference-management record gave Bunney's journal, volume, pages and/or DOI to many other papers. Many of those are NIH author manuscripts, with the "HHS Public Access" banner. This study cannot tell which tool or database did it.
- If H5 holds, Bunney 2017's counts in all three open indexes are mostly misdirected citations, and the papers the authors meant to cite are missing them.
- No contact with any author, publisher, Elsevier, Crossref, OpenAlex or OpenCitations is planned; any such step is Sheehan's to decide.
