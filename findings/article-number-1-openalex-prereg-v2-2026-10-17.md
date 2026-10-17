# Pre-registration: is OpenAlex's excess on MDPI and Frontiers article-1 records specific to article 1? (v2, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

This note is committed **before any OpenAlex count of a control article is collected**. The job that collects them (`openalex_article1.py`, in this repository) will be queued only after this commit is public, in a later run. Both times will be stated in the results note.

## Question

The v1 study (`article-number-1-v1-results-2026-10-17.md`) found no article-1 inflation at MDPI or Frontiers **in Crossref**. Its descriptive OpenAlex column showed something else. For volumes of 2016-2019, OpenAlex gives many article-1 records far more citations than Crossref does: Int J Mol Sci 17:1 has 862 against 15, and Front Plant Sci 2016:1 has 1,503 against 41. By a hand count, OpenAlex gives at least twice the Crossref count to 45 of 55 MDPI article-1 records of 2016-2019 and 36 of 40 Frontiers ones. For 2021-2023 the figure is 2 of 42 MDPI records.

That could have two causes:
- (a) an article-1 sink inside OpenAlex, like the one Kriváchy (arXiv:2511.01675) found at Springer Nature in Crossref;
- (b) a general excess that OpenAlex gives to all older papers. One plausible source is citation links inherited from Microsoft Academic Graph, which closed at the end of 2021. This is a guess, not a tested claim.

Only the same-volume controls can tell (a) from (b). **Their OpenAlex counts have not been looked at.** An OpenAlex community thread reports one such case, a 2019 Scientific Reports article with 1,787 OpenAlex citations against 30-40 elsewhere (groups.google.com/g/openalex-community/c/Os0ah6pU2Us). Kriváchy checked Crossref, OpenCitations and Semantic Scholar, not OpenAlex. We found no measurement for MDPI or Frontiers (searches on 2026-10-17).

## What we have already seen

- The Crossref counts of every article in `article1_check_v1_units.jsonl` (article 1, articles 2-30, articles 41-60).
- The OpenAlex counts of the **article-1 records only** (the `article1_openalex` column of `article1_check_v1_results.json`), including the hand count above.
- The H4 reads of v1 (Crossref-side references to three MDPI article-1 records).
- Nothing about OpenAlex counts or OpenAlex citers of any control article.

## Data and units

- **Input:** `article1_check_v1_units.jsonl`, unchanged. Crossref counts are the frozen ones in that file (read 2026-10-17 03:26-03:55 UTC), so article 1 and its controls come from one snapshot.
- **OpenAlex:** fresh `cited_by_count` and work id for article 1 and every far control (articles 41-60), looked up by DOI, 50 per call. If two OpenAlex works share a DOI, the one with more citations is used.
- **Excess** of an article: E = (OpenAlex count + 1) / (Crossref count + 1).
- **Unit:** one volume, as in v1. A unit is eligible if it is confirmatory (IJMS 20 stays excluded), article 1 has an OpenAlex count, and at least 10 far controls have one.
- **Eras:** "old" means volume years 2016-2019 and "new" means 2021-2023. 2020 is a transition year, reported but not tested. Frontiers has no new units (its DOI scheme changed in 2021).

## Hypotheses and rules (fixed now)

Per unit, article 1 is "top" if its E is **strictly** greater than every eligible far control's E. The effect is E(article 1) / median E(far controls).

- **H1 (article-1 excess in OpenAlex, old era).** The test pools MDPI and Frontiers old units. The number of top units is compared with chance: each unit's chance is 1/(number of controls + 1), with an exact Poisson-binomial tail. **Supported if p < 0.01 AND the median effect is at least 2.0.** Fewer than 10 units: untestable. *Our guess: supported.*
- **H2 (negative control, new era).** The same rule over MDPI new units. *Our guess: not supported.*
- **H3 (general excess on older papers).** Over MDPI units, compare the median across old units of the median control E with the same figure across new units. **Supported if the old figure is at least 1.5 times the new one** (each era needs at least 10 units). *Our guess: supported, low confidence.*
- **H4 (the OpenAlex excess is misattributed).**
  - Targets: the 3 old-era eligible units whose article 1 has the largest OpenAlex-minus-Crossref count, among those with at least 3 title words of 5+ letters.
  - For each target, a seeded random sample of 40 works that OpenAlex lists as citing it is read in Crossref (OpenAlex `sample` with seed 20261023 + i; citers without a DOI are dropped and counted). Each citer is classified:
    - if a deposited reference carries the target's DOI, it is classified exactly as in v1: **genuine**, **other_work**, **doi_only** or **undetermined**;
    - otherwise, **genuine** if any deposited reference's title text holds at least half (minimum 2) of the target's first 8 distinct title words of 5+ letters;
    - otherwise, **unsupported** if the citer deposited at least 5 references (OpenAlex's link has no basis in the deposit);
    - otherwise **too_few_references**; a citer missing from Crossref is **not_in_crossref**.
  - Genuine share = genuine / (genuine + other_work + unsupported). **Supported if the pooled share is under 0.50 with at least 20 such citers.** *Our guess: supported.*
  - **Calibration first:** the same reading of each target's control with the most OpenAlex citations must give a pooled genuine share of at least 0.70 on at least 10 citers. If not, H4 is "untestable (classifier failed calibration)".

**Descriptive only:**
- E for article 1 and controls in 2020 units;
- the per-unit table;
- the change in article-1 OpenAlex counts since the v1 snapshot;
- the number of DOIs OpenAlex does not know.

## Code, run and deviations

- `openalex_article1.py` (standard library; it imports the v1 helpers from `article1_check.py`), with offline tests in `test_openalex_article1.py`. Seed 20261023.
- It is run once as a sealed job with network access. Outputs: `results.json`, `units_oa.jsonl`, `reads.jsonl`.
- Thresholds and hypotheses will not change after this commit. Fixes to code that crashes or mis-parses an API response are allowed before the run, and each will be listed as a deviation with its commit.
- If more than 10% of DOIs lack an OpenAlex count because calls failed (not because OpenAlex lacks the work), the results will be reported as partial.

## Limits known in advance

- Crossref and OpenAlex counts are a few days apart. Both drift slowly, and the same applies to article 1 and its controls.
- An "unsupported" citer may still cite the target through a reference deposited with neither its DOI nor its title. The calibration on controls bounds this.
- OpenAlex may merge versions, such as a preprint and the article, which adds citations that are not errors. This would raise E for any article, not article 1 especially.
- AI agents designed this and will run and score it. Pre-registration guards against moving the goalposts. It does not replace an independent human check.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
