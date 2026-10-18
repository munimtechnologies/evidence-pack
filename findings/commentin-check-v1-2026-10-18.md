# commentin_check v1: flag PubMed "Comment in" links to read before citing them (2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Code Apache-2.0, text CC BY 4.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

## What it is

`commentin_check.py` (offline tests `test_commentin_check.py`; it reuses `integrity_check.py`, `doi_hygiene.py` and the link classifier of `pubmed_commentin.py`) takes PMIDs and DOIs and, for each record, lists its PubMed "Comment in" links. For each link it reads the target in PubMed and reports:

- `cls`: `pmid`, `bare_doi` (a bare "doi: 10.x/..." with no PMID) or `other_nopmid`, the same classes as census v1;
- `tgt_pmid`, `tgt_title`, `tgt_date`, `tgt_pubtypes`: the target, found from the link's PMID or by looking up its DOI;
- `earlier`: the target's PubMed sort date is before the record's;
- `reciprocal`: the target names the record under its own "Comment on";
- `tgt_comment_on`: the records the target says it comments on.

Flags: `bare_doi`, `other_nopmid`, `no_target_id`, `target_not_in_pubmed`, `target_unread` (a lookup failed, so nothing is concluded), `earlier`, `not_reciprocal`, `comment_on_other`. `--fail-on-flag` exits 2 when any link is flagged, so it can gate a reference list.

```
python commentin_check.py 40274279 10.1056/NEJMc2401126
python commentin_check.py --file references.txt --out comment_links.jsonl
```

Why: census v1 (`pubmed-commentin-census-v1-results-2026-10-17.md`) found that 12.1% of JAMA Network "Comment in" entries are bare DOIs without PMIDs, that none of 300 sampled targets links back, and that 38% point to older articles. Appraisal tools and reviewers read "Comment in" as "this paper has been discussed". This tool makes the check one command. It sits next to `integrity_check.py` as part of the error-detection evidence for MV2's evidence-synthesis work. It is a separate command; `integrity_check.py` is unchanged.

A flag says what to read, not what to conclude. Two live cases show why:

## Read live in PubMed (E-utilities esummary, 2026-10-18, by hand; the test fixtures copy these fields)

- **PMID 40274279** (JAMA 2025, metformin for knee osteoarthritis; the key trial behind MV2's ReGen package 5). There are two "Comment in" links, both bare DOIs with no PMID. `10.1001/jamanetworkopen.2023.3646` is PMID 36939700, a 2023-03-01 cohort study ("Development of Osteoarthritis in Adults With Type 2 Diabetes Treated With Metformin vs a Sulfonylurea"). `10.1001/jama.2024.17482` is PMID 39541114, a 2024-12-10 patient page ("What Is Knee Osteoarthritis?"). Both are older than the trial (2025-05-27), and both have empty link lists. Flags: `bare_doi`, `earlier`, `not_reciprocal` on each. Neither is a comment on the trial.
- **PMID 38507769** (NEJM letter, 2024-03-21) has a "Comment in" link with a PMID: 38012264, a Nat Rev Nephrol comment dated 2024-01-01. The target is older than the letter, but it names the letter back under "Comment on" (with 37931634). Flag: `earlier` only. PubMed links real comments this way too, so `earlier` on its own does not mean "not a comment".
- **PMID 28208186** (JAMA Oncol 2017) links `10.1001/jamaoncol.2016.6722` with a bare DOI. That DOI is PMID 28208180, typed Comment, which PubMed records as a comment on a different paper of the same issue, 28208174, and not on 28208186. Flags: `bare_doi`, `not_reciprocal`, `comment_on_other`.

## Limits

- PubMed only. Dates are PubMed `sortpubdate`, which can be an issue date. Census v1 dated links with Crossref, so the two `earlier` counts can differ near issue boundaries.
- A real commentary that discusses several papers may name only one of them in PubMed, so `not_reciprocal` and `comment_on_other` are reasons to read, not proof.
- Not yet run on live data in MV2's sandbox. The pre-registered census in `commentin-targets-prereg-v1-2026-10-18.md` is its first full use.

No one at JAMA Network, the AMA, NLM or any author has been contacted.
