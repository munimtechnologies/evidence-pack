# PubMed "Comment in" links that are not comments: pilot and pre-registered census (v1)

MV2 of Munim, Inc., 2026-10-17. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice. No independent human check yet.

Status: **pilot read; census pre-registered and not yet run.** Code: `pubmed_commentin.py` (standard library), tests: `test_pubmed_commentin.py`.

## Why this matters

PubMed shows "Comment in:" under a record to point readers to letters, editorials and other items that comment on it. NLM's policy is that "a mere mention of one or more articles in the text or references does not constitute a comment" ([NLM, Errata, Retractions, and Other Linked Citations](https://www.nlm.nih.gov/bsd/policy/errata.html)). Reviewers, appraisal checklists and software read these links as "this paper has been discussed". A link that points somewhere else misleads all of them.

## How we found it (post hoc)

We were rechecking the references of an evidence package for the NCATS ReGen challenge. PubMed's record for the metformin knee-osteoarthritis trial (Pan et al., JAMA 2025, PMID 40274279) lists two "Comment in" links. Both are bare DOIs with no PMID:
- `10.1001/jamanetworkopen.2023.3646` is Baker et al. 2023, a cohort study that the trial itself cites as its reference 29 (Crossref deposit).
- `10.1001/jama.2024.17482` is "What Is Knee Osteoarthritis?", a JAMA Patient Page from 2024-12-10.

Neither can comment on a trial published in 2025.

## Pilot: every JAMA randomized trial dated 2025 (hand tally, 2026-10-17)

- **Records.** The search `"JAMA"[ta] AND 2025[dp] AND randomized controlled trial[pt]` returns 76 records. We read each record's "Comment in" entries from E-utilities esummary.
- **Records with any "Comment in":** 61 of 76. The query `hascommentin AND ...` independently returns 61, so the tally and the filter agree.
- **Two kinds of entry:**
  - **With a PMID:** 57 entries on 47 records. Each has a full citation string. Each points to an item dated the same day or later: a same-issue editorial, or a later letter or commentary in JAMA, JAMA Cardiology, AJR, J Thorac Dis, Ann Transl Med or Transl Gastroenterol Hepatol.
  - **Bare DOI, no PMID:** 30 entries on 14 records (27 distinct DOIs). Every one is a JAMA Network DOI (prefix 10.1001).
- **What the 27 bare-DOI targets are** (titles and dates from Crossref):
  - earlier trials and cohorts on the same topic. Examples: tenecteplase trials from 2020 and 2024 for the 2025 ANGEL-TNK trial; negative-pressure wound-therapy trials and a review from 2018-2020 for the 2025 SUNRRISE negative-pressure dressing trial; atrial-fibrillation screening papers from 2018-2022 for the 2025 AMALFI screening trial; the Spironolactone vs Amiloride trial for the zilebesiran KARDIA-2 trial;
  - systematic reviews, a USPSTF statement ("Screening for Atrial Fibrillation", 2022), guideline and clinical-review pages, Patient Pages ("What Is Knee Osteoarthritis?", "Iron Deficiency in Adults"), a Medical News item and a Viewpoint.
- **Dates:** 26 of the 27 were published (Crossref print/issue date) before the record that lists them as comments. The exception is a companion trial published at the same time in JAMA Neurology (PMID 40616333, "Intra-Arterial Tenecteplase After Successful Reperfusion..."), and the two records list each other.
- **Reading:** these look like the publisher's "related articles" carried into PubMed's "Comment in" field, without PMIDs. That is a hypothesis about the cause, not a finding. We have not seen the publisher's XML.

## Prior art

We searched the web, NLM documentation and the PubMed literature for reports of "Comment in" links that predate the record, or that carry only a DOI (2026-10-17). We found:
- NLM's policy on linked citations;
- NLM's XML help for data providers, which says a comment link may be supplied by PMID, DOI or PII (NBK3828);
- general studies of PubMed and Crossref metadata errors.

We found no report of this pattern. Our searches were limited, so we say only that we found none.

## Census design (held out from the pilot)

- **Groups:**
  - **JAMA Network (13 journals):** JAMA, JAMA Netw Open, JAMA Intern Med, JAMA Pediatr, JAMA Cardiol, JAMA Neurol, JAMA Surg, JAMA Oncol, JAMA Psychiatry, JAMA Dermatol, JAMA Ophthalmol, JAMA Otolaryngol Head Neck Surg, JAMA Health Forum.
  - **Control (4 journals with many comment links):** N Engl J Med, Lancet, BMJ, Ann Intern Med.
- **Population:** every PubMed record from 2016 to 2026 (`[dp]`) in those journals that matches `hascommentin`. Any journal-year above 9,999 hits is split by month. **The 76 pilot records are excluded.**
- **Classes of "Comment in" entry:**
  - `pmid`: the entry has a PMID;
  - `bare_doi`: no PMID, and the RefSource is only "doi: 10.x/...";
  - `other_nopmid`: anything else.
- **Dating:**
  - **Which links:** every `bare_doi` link (up to 20,000, seeded sample above that) and a seeded sample of up to 3,000 `pmid` links per group whose citation carries a DOI.
  - **Date used:** each end's Crossref `published` date, the earliest of print and online.
  - **"Earlier":** the target is strictly before the source, compared at the coarser precision of the two dates. A tie counts as not earlier.
- **Reciprocity:** a seeded sample of up to 300 links per class per group.
  - `bare_doi` targets are resolved to a PMID by `<doi>[doi]` (exactly one hit, or unresolved).
  - We then check whether the target's own "Comment on" list names the source PMID. A true comment link is normally two-way.
- **Seed:** 20261017.

## Hypotheses (JAMA Network unless stated; thresholds fixed now)

- **H1 (exists, and is specific to the publisher):**
  - at JAMA Network, `bare_doi` entries are at least 2% of all "Comment in" entries;
  - at the control journals, they are at most 0.5%.
- **H2 (time-reversed):**
  - at least 80% of dated `bare_doi` links point to a target published before the source;
  - at most 5% of dated `pmid` links do.
- **H3 (not comments):**
  - at most 10% of resolved `bare_doi` targets list the source in their own "Comment on";
  - at least 90% of sampled `pmid` targets do.
- **H4 (same publisher):** at least 90% of `bare_doi` targets have the prefix 10.1001.

**Scoring rules:**
- Each hypothesis is supported only if every part passes.
- A hypothesis is untestable if any denominator is below its minimum: 100 entries for H1; 30 dated or resolved links for each part of H2-H4.
- We will also report, without prediction:
  - the share of records with a `bare_doi` entry by year and journal (to date the onset);
  - the control group's dating and reciprocity;
  - the 20 most common target prefixes.

## Limits

- `hascommentin` may miss records whose only links were added in ways the filter does not index. That would bias toward the PMID class.
- Crossref `published` dates can be issue dates for some deposits, so a same-week companion can look earlier or later by a few days. That is why H2 uses 80%, not 100%.
- Reciprocity needs the target in PubMed. Targets outside PubMed are reported as unresolved, not as non-comments.
- If the census supports H1-H3, the fix sits with the publisher's PubMed data (PubMed Data Management), not with NLM. We will publish the result and the list. We will not contact the publisher or NLM without approval.

## Outputs

`results.json` (counts, tallies, verdicts, search log), `nopmid_links.jsonl` (every link without a PMID, with dates), `pmid_dated_sample.jsonl`, `reciprocity.jsonl`. The results note will say how each hypothesis fared, including failures.
