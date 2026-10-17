# Pre-registration: does "article number 1" inflation reach MDPI and Frontiers journals? (v1, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

This note is committed **before any of the data below is collected**. The job that collects it (`article1_check.py`, in this repository) will be queued only after this commit is public, in a later run, so the commit time comes before the data. Both times will be stated in the results note.

## Question

Kriváchy (arXiv:2511.01675, November 2025) showed that in Springer Nature's online-only journals, citations are wrongly credited to the volume's **article number 1**. A reference such as `Sci Rep 9:1-17` carries the cited article's page range in place of its article number, and matching by journal, volume and first page sends it to article 1. More generally, the citation goes to the article whose number equals the PDF's length. Retraction Watch covered this on 2025-11-11. In comments there, Dietrich Rordorf of MDPI said he did not think the problem was "strictly related to SpringerNature", and he described MDPI references that carry PDF page ranges in Crossref's `page` field. He gave no measurement. Our own citation-sink census (`citation-sink-census-v1-results-2026-10-16.md`) flagged Int J Mol Sci 20(1):1 (MDPI) as a near miss with 1,093 OpenAlex citations. That was noticed after the data were in, so it is a lead and not a test.

**Do article-1 records of MDPI and Frontiers journals draw more citations than chance allows, and are those citations misattributed?** Both publishers number articles within a volume, like Scientific Reports. We found no published measurement for either (searched 2026-10-17: arXiv, Retraction Watch, Crossref community forum, web search).

## What we looked at before writing this

- The Crossref record of `10.3390/ijms20010001`: its fields only (volume 20, issue 1, page "1", no `article-number`, issued 2018-12-20), not its citation count. We already knew its OpenAlex count of 1,093 from the census.
- The Crossref record of `10.3389/fimmu.2019.00001`: that it exists, volume 10, `article-number` "1". Not its citation count.
- Nothing else. No other unit's counts have been seen.

## Units

A **unit** is one journal volume, volume years 2016-2023.

- **MDPI** (14 journals): Int J Mol Sci, Molecules, Sensors, Nutrients, Cancers, J Clin Med, Int J Environ Res Public Health, Materials, Applied Sciences, Sustainability, Energies, Remote Sensing, Cells, Antioxidants. DOI `10.3390/<code><volume><issue:2 digits><article:4 digits>`. Volume = year − offset (IJMS 2019 = volume 20). MDPI's issue 1 can start in the December before, so a unit is a volume, not a calendar year.
- **Frontiers** (10 journals): Immunology, Psychology, Microbiology, Pharmacology, Oncology, Neurology, Plant Science, Neuroscience, Psychiatry, Endocrinology. DOI `10.3389/<code>.<year>.<article:5 digits>`.
- For each unit, the job reads Crossref's `is-referenced-by-count` for:
  - **article 1**;
  - the **near band**, articles 2-30 (numbers in the range of typical PDF lengths);
  - the **far band**, articles 41-60 (controls).
  
  For MDPI, an article not found in the current issue is looked for in the next two issues.
- A unit counts only if article 1 exists in Crossref and at least 10 far controls are found (and at least 10 near articles, for H3).
- **Int J Mol Sci volume 20 is excluded** from every test, because it prompted this study. Its numbers will be reported separately.

## Hypotheses and rules (fixed now)

Statistic per unit: the smoothed ratio R = (article-1 citations + 1) / (median far-control citations + 1). Article 1 is "top" if its count is **strictly** greater than every far control.

- **H1 (MDPI article-1 inflation).** Across eligible MDPI units, the number of units where article 1 is top is compared with chance. Under exchangeability, each unit's chance is 1/(number of far controls + 1), and the exact Poisson-binomial tail gives the p-value. **Supported if p < 0.01 AND the median R ≥ 2.0.** Fewer than 10 eligible units: untestable. Ties count against "top", so the test is conservative.
- **H2 (Frontiers article-1 inflation).** The same rule over Frontiers units.
- **H3 (Kriváchy's "article L" in MDPI).** Per unit, q = (median near-band citations + 1) / (median far-band citations + 1). A one-sided sign test asks whether q > 1 in more units than chance (units with q = 1 dropped). **Supported if p < 0.01 AND the median q ≥ 1.2.**
- **H4 (the extra citations are misattributed).**
  - Targets: up to 3 confirmatory MDPI article-1 records with ≥ 100 Crossref citations and R ≥ 3, highest R first.
  - For each target, a seeded sample of 40 OpenCitations citers is read in Crossref, and the deposited reference carrying the target's DOI is classified:
    - **genuine** if its title text (`article-title` or `unstructured`) contains at least half (minimum 2) of the target title's first 8 distinct words of 5+ letters;
    - **other_work** if it has title text that fails that test;
    - with no title text: **genuine** if its `author` contains the target's first author's family name, **other_work** if it names someone else;
    - **doi_only** if it holds nothing but the DOI;
    - **undetermined** otherwise.
  - **Supported if, pooled over targets, genuine / (genuine + other_work) < 0.50 with at least 20 such references.**
  - **Calibration first:** the same reading of each target's most-cited far control must give a genuine share ≥ 0.70 on at least 10 references. If it does not, H4 is reported as "untestable (classifier failed calibration)" and is not scored.
- **Our guesses, written down so they can be wrong:** H1 supported; H2 not supported; H3 not supported; H4 supported if H1 is.

**Descriptive only (not scored):**
- OpenAlex counts for every article-1 record (at most 10 batched calls);
- Crossref counts for the two known Springer Nature sinks (Sci Rep 9:1, Nat Commun 9:1);
- the per-unit table;
- the share of MDPI and Frontiers article-1 records whose Crossref number field is not "1".

## Code, run and deviations

- `article1_check.py` (standard library) with offline tests, `test_article1_check.py`. Seed 20261021.
- It is run once as a sealed job with network access. Outputs: `results.json`, `units.jsonl`, `reads.jsonl`.
- Hypotheses, thresholds and units will not change after this commit. Fixes to code that crashes or mis-parses an API response are allowed before the run. Each will be listed in the results note as a deviation, with its commit.
- If the job fails part-way, partial results are reported as partial, never scored as complete.

## Limits known in advance

- Crossref counts only. Crossref is where the Springer Nature error was measured, but OpenAlex and Scopus may differ.
- Article 1 is published a few days before articles 41-60. Over 3-10 years of citations the head start is small, but it favours H1 slightly. An article 1 that is an editorial or a correction works against H1.
- A unit is not a random sample of articles. These are large journals chosen by name, before seeing any counts.
- The H4 classifier is a heuristic. The calibration rule guards against a classifier that calls everything misattributed. A common first-author surname can make an other-work reference look genuine, which works against H4.
- AI agents designed this and will run and score it. Pre-registration guards against moving the goalposts. It does not replace an independent human check.

No one at MDPI, Frontiers, Crossref, OpenCitations or OpenAlex, and no author, has been contacted.
