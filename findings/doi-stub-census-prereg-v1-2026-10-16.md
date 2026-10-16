# DOI stubs: OpenAlex records whose DOI is only a journal's DOI stem absorb tens of thousands of citations. Pilot and pre-registered census v1 (2026-10-16)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
The pilot below was read by hand through the public OpenAlex and Crossref APIs on 2026-10-16 (21:30-22:00Z). The census plan is committed before any census data exist. Code: `stub_census.py` (standard library only); offline tests: `test_stub_census.py`. Sealed job: `stub-census-v1`.

## What we found (pilot, by hand through the APIs)
The citation-sink census (`citation-sink-census-v1-results-2026-10-16.md`) drew one hit from its random sample: OpenAlex **W4288364210**, whose DOI is `10.1136/bmjopen`. That is not an article DOI. It is the stem that every BMJ Open DOI begins with, as in `10.1136/bmjopen-2016-012545`. We then looked up other journals' stems as DOIs in OpenAlex (`filter=doi:<stem>`, 44 stems tried by hand, chosen from well-known medical journals). **12 of the 44 exist as OpenAlex records:**

| Stem used as a DOI | OpenAlex | Title on the record | Citations |
|---|---|---|---|
| 10.1016/s0140 (The Lancet) | W3120106258 | "Home visits: a strategy to improve newborn survival - Authors' reply" | **22,520** |
| 10.1016/s0140-6736 (The Lancet) | W2594075087 | "Correspondence - Tranexamic acid for traumatic brain injury" | **11,875** |
| 10.1136/bmjopen | W4288364210 | a 2014 protocol (cardiovascular mortality and oral antidiabetics) | 2,230 |
| 10.1136/annrheumdis | W2764515646 | "Annals of the Rheumatic Diseases" | 712 |
| 10.1016/s0002 | W4291238992 | "Ruby P. Puckett ... receives 2003 Copher Memorial Award." | 457 |
| 10.1136/archdischild | W2504004509 | "Archives of Disease in Childhood" | 429 |
| 10.1016/s0091 | W2085856905 | "Airway inflammation in chronic obstructive pulmonary disease: comparisons with asthma." | 358 |
| 10.1136/heartjnl | W2623039535 | a 2014 correction notice in Heart | 220 |
| 10.1136/thoraxjnl | W4242058682 | "Thorax" | 111 |
| 10.1186/1471 (BMC series) | W7111097456 | a 2017 Spanish systematic review | 33 |
| 10.1038/s41598 (Sci Rep) | W7119656477 | a 2021 C. difficile proteomics paper | 19 |
| 10.1016/s1470 (Lancet Oncol) | W7216360564 | a 2007 trial report | 1 |

Together that is **38,965 citations** on 12 records. Each record is either a real item that was given a truncated DOI (the Lancet letter's real DOI is 10.1016/S0140-6736(13)62361-2, PMID 24238553) or a journal-level placeholder. Its citation count is not that item's.

**Where the citations come from.**
- **The Unicode hyphen.** Our dash census (`reference-dash-census-v1-results-2026-10-16.md`, evidence-pack v0.4.8) found that about half of 2026 Wiley articles deposit reference DOIs with U+2010 HYPHEN instead of the ASCII hyphen. A DOI pattern such as `10.\d{4,9}/[-._;()/:a-z0-9]+` stops at the first U+2010, which leaves exactly the stem. In the record for Research Synthesis Methods 10.1002/jrsm.1715, a citer of the bmjopen stub, the deposited references are `"DOI":"10.1136/bmjopen‐2016‐012545"` and `"10.1136/bmjopen‐2023‐072254"`. In Br J Clin Pharmacol 10.1111/bcp.15970, a citer of the Lancet stub, the deposited reference is `"DOI":"10.1016/S0140‐6736(11)61817‐5"`.
- **Wiley dominates the BMJ Open stub.** 2,015 of its 2,229 citers (90%) are Wiley-published. In 2024 it is 1,045 of 1,089. For the Lancet stub `10.1016/s0140`, Wiley is the largest publisher but has only 4,145 of 22,484 citers (18%). For `10.1136/annrheumdis` it has 264 of 712 (37%).
- **Not everything is the hyphen.** Two non-Wiley citers of the Lancet stub deposit intact ASCII Lancet DOIs. SAGE 10.1177/17456916221141374 has `10.1016/S0140-6736(18)31130-9`, and OpenAlex links that paper to both the real Lancet article (W2809472886) and the stub. MDPI 10.3390/jcm13010040 has two intact Lancet DOIs. So for most of the Lancet stub's citers the link comes from another route that we have not identified. One candidate is references parsed from full text, where a DOI broken at a line-end hyphen would also leave the stem. The second stub, `10.1016/s0140-6736`, is the cut at the "(" of Lancet DOIs.
- **Impossible dates.** The Lancet stub record has citers dated 1949, 1967 and 1970 (7 in 1970), decades before any item it could stand for.

**Why it matters for medicine.** The Lancet, BMJ Open, Annals of the Rheumatic Diseases, Thorax, Heart and Archives of Disease in Childhood are core clinical journals. Every misdirected citation is a missing citation to the real article the authors cited. In the BMJ Open case, about 2,000 citations from Wiley papers are missing from the BMJ Open articles they were meant for. Tools that rank or screen literature by citation counts (systematic-review screening, PubMed-style "cited by" priors, research assessment) read these records as real.

**Prior art.** We searched (2026-10-16) for OpenAlex DOI truncation, Unicode-hyphen DOIs and stub records, and found none of the following documented: records whose DOI is a journal stem, U+2010 truncation as a cause of misdirected citations, or these 12 records. Related, different work: invalid DOIs in Crossref deposits (arXiv 2111.11263, which does not cover Unicode hyphens), "sneaked references" (Besançon et al., JASIST 2024), article-number-1 misattribution in Springer Nature journals (Kriváchy, arXiv 2511.01675), and an OpenAlex community thread on over-cited records (2025-02-26). If earlier reports exist, we will cite them.

## Census v1: plan, written before the data
**Questions.** (1) How many stub records exist beyond the 12 we found by hand? (2) Is the Unicode hyphen in Wiley deposits the mechanism behind their Wiley citers? (3) Are the "dash" stubs' citers more Wiley-heavy than the literature as a whole?

**Census arm.**
- Take a seeded OpenAlex sample (seed 20261019) of 6,000 works with `has_doi:true, type:article, publication_year:2000-2025, cited_by_count:>49`.
- From each DOI form its **dash stem**: everything before the first "-" in the suffix. Also form its **paren stem**: everything before the first "(". A stem needs at least 2 suffix characters and only `a-z 0-9 . _ / -`.
- Look up every distinct stem, plus the 12 pilot stems, as an exact OpenAlex DOI, 50 per call.

**Per record** (the 60 most-cited, to bound calls):
- Is the stem registered in Crossref? A registered stem would be a real DOI, not an error.
- The share of its citers that Wiley published (`primary_location.source.publisher_lineage`).
- How many citers are dated before the record's own year.
- 10 seeded-random citers' Crossref reference lists. Each citer gets the strongest label among its reference DOIs in that journal:
  - **exact:** the deposit already holds the stem;
  - **cut_at_unicode_dash:** the stem followed by a Unicode dash;
  - **has_unicode_dash:** Unicode dashes elsewhere in the DOI;
  - **intact_ascii:** a correct ASCII DOI;
  - **absent:** no DOI in that journal.

**Baseline.** Wiley's share of all OpenAlex articles from 2015 to 2025 (one group_by call).

**Hypotheses and predictions.**
- **H1 (more stubs exist):** the census arm finds at least 5 stub records whose stems are not in the pilot list. *Guess: supported*, from a hit rate of 12 of 44 in the pilot. We are unsure, though: the sample is drawn by article, not by citation, and the pilot list was picked by hand.
- **H2 (mechanism):** among Wiley-published citers of dash stubs whose deposits could be read, at least 80% carry a Unicode-dash DOI in the stub's journal (`cut_at_unicode_dash` or `has_unicode_dash`). At least 10 such reads are needed; otherwise H2 is untestable. *Prediction: supported* (pilot: 2 of 2).
- **H3 (Wiley excess):** among dash stubs with at least 50 citers, at least 75% have a Wiley citer share above twice the baseline. *Prediction: supported* (pilot: 90%, 37% and 18% against a baseline we expect to be under 9%).

**Descriptive outputs:**
- the labels for paren stubs and for non-Wiley citers of dash stubs, which test the "other route";
- the total citations absorbed by the census arm alone;
- citers dated before their record's year.

**Budget.** At most 400 OpenAlex calls, with back-off of 30 s to 10 min. Keyless OpenAlex use shares a small daily budget per IP. Calls, reported cost and refused or failed calls are written to `results.json`. If the budget runs short, arms are reported as incomplete, not filled in.

**Limits stated in advance.**
- The census finds only stubs formed by the two cut rules, from journals in the sample. Journals with no hyphen in their DOIs cannot produce a stub this way.
- Crossref deposits are not the only source of OpenAlex references, so an `intact_ascii` or `absent` label means the link came from somewhere else, not that it is right.
- We do not know OpenAlex's internal parser. The U+2010 mechanism is inferred from deposits and outcomes.
- **Deviation rule.** Any mismatch between this plan and the code, or any change after the data are seen, will be reported as a deviation in the results note (`doi-stub-census-v1-results-<date>.md`), which will be published whatever it shows.

No one at Wiley, BMJ, Elsevier, Crossref or OpenAlex has been contacted. This public note is the report. The fix on the data side looks simple: map U+2010 and similar dashes to ASCII before matching, and never accept a bare journal stem as a DOI. Users of OpenAlex citation counts can drop the records listed above today.
