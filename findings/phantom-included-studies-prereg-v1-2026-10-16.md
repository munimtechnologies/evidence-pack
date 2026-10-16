# Pre-registration: phantom included studies in 2026 meta-analyses (v1)

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-10-16 before any reference list in the sample was read.
The study design, code and write-up are researched and drafted by AI agents working in MV2's name.
Text CC BY 4.0; code (`phantom_refs.py`, `test_phantom_refs.py`) Apache-2.0.

## Question
A meta-analysis pools numbers from its included studies. If one of those studies cannot be verified to exist
(a reference whose DOI points at an unrelated paper or at nothing, and whose title matches no real work), the pooled
estimate may rest partly on a phantom. **How often do 2026 medical meta-analyses cite references that cannot be
verified, and how many of those are among the included studies rather than background citations?**

## Prior art, and what is new here
- Topaz et al., *Lancet* 2026 (research letter, DOI 10.1016/S0140-6736(26)00603-3; CITADEL): 2.5 million PMC papers,
  2023 to 2026-02-18. They found about 4,000 fabricated references (reports give 4,046 or 4,406) in 2,810 papers, about 1 in 277
  papers in early 2026. Most fake
  references carried identifiers that resolve to unrelated papers. The paper notes that some have reached systematic reviews.
- Zhao et al., arXiv 2605.07723 (2026): about 147k hallucinated citations in 2025 across arXiv, bioRxiv, SSRN and PMC.
- Han, *JASIST* 2026, DOI 10.1002/asi.70104 ("Phantom citations"): non-existent and unverifiable references in scholarly literature.
- **New here:** none of these asks whether an unverifiable reference is one of the **included studies** of a
  meta-analysis, the place where it can change a pooled result. Our searches on 2026-10-16 found no such audit.
  This study also uses only open infrastructure (PubMed E-utilities, Crossref, the doi.org handle API), and the code is
  published.

## Sampling frame (fixed)
- PubMed `meta-analysis[pt] AND 2026[dp] AND 2026/01/01:2026/10/15[edat]`. On 2026-10-16 the count was **14,355**.
  The job re-fetches the frame in ten monthly Entrez-date windows and records the count and a sha256 of the sorted
  PMID list. A small drift from later indexing is expected and will be reported.
- Sort the PMIDs numerically (N of them). Pick k = 0..239 is `frame[floor(k*N/240)]`.
- Picks are processed in the order of sha256("phantom-v1:k"). If the 200-minute deadline stops the job early, the
  analysed set is the processed prefix, which is still spread over the frame. The number is reported.
- No replacement. A pick with no DOI, not in Crossref, or with no deposited reference list is reported by category
  and excluded from the denominators.

## Measurement (automatic, `phantom_refs.py`)
For every reference in the pick's Crossref record:
1. Count references with no DOI, and those whose DOI Crossref matched itself (`doi-asserted-by: crossref`). These are
   not checked further, because a Crossref-matched DOI exists by construction.
2. For each **publisher-asserted DOI**: look it up in Crossref. If Crossref lacks it, ask doi.org's handle API
   (HTTP 200 means it exists at another agency, 404 means not found). If the raw DOI fails, try it once cleaned
   (prefix, spaces, trailing punctuation, unbalanced closing bracket). A clean hit counts as **malformed but fixable**.
3. If found in Crossref: compare the reference's own title (`article-title`, else the `unstructured` string) with the
   DOI's registered title. Use lower-case ASCII word tokens with markup and a few stopwords removed. The similarity is
   max(containment both ways) for a title, or the share of the registered title's tokens present in an unstructured
   string. **>= 0.5 is a match.** Registered titles under 3 tokens are "short" and not judged. References with no
   title text are "untitled".
4. For each **mismatch** or **not found**: run a Crossref bibliographic search on the reference text (top 5). If a
   hit has similarity >= 0.8 under another DOI, it is a **real work, wrong DOI** (a citation error, not a phantom).
   Otherwise it is **unresolved** (a candidate). A not-found DOI with no title text is reported separately ("no-text").

## Manual check (after the job; before any claim)
Each unresolved candidate is read twice, independently, by AI agents working in MV2's name, and the record of both
reads is published:
- **Existence:** search the reference title in PubMed, Europe PMC and Crossref, plus the cited journal's
  site/issue where reachable. **Verified** means a real work matching title and first author is found (the reference
  has a wrong DOI). **Unverifiable** means none of these finds it. Only "unverifiable" in both reads counts. A
  disagreement goes to a third read.
- **Role (unverifiable references only):** from the meta-analysis full text (Europe PMC open-access XML or the
  publisher page). **Included** means the reference appears in the included-studies table, the
  characteristics-of-studies table or a forest plot, or the text says it was included. **Background** means it is
  cited elsewhere only. **Unclear** means the full text is not reachable.

## Endpoints
- **Primary:** share of audited meta-analyses with >= 1 reference that is **unverifiable after the manual check**,
  with a Wilson 95% CI. The job's automatic "unresolved" share is reported beside it as the screening rate.
- **Key secondary:** number of meta-analyses with >= 1 unverifiable reference that is an **included study**, and
  the share of all unverifiable references that are included studies.
- Other secondary outputs:
  - unverifiable references per checked publisher DOI;
  - real-work-wrong-DOI rate;
  - malformed-but-fixable rate;
  - not-found rate;
  - share of meta-analyses with deposited references.

## Power, stated in advance
With about 240 meta-analyses: if the true share were 1 in 100, we expect about 2-3 positives. If none is found, the
upper 95% bound is about 1.6%. This is a screening study, sized to find out whether phantom included studies
exist at a measurable rate in 2026 meta-analyses, not to pin the rate down.

## Known limits
- References without DOIs (about 10% in the first record checked) are not tested.
- Phantoms whose DOI points at a paper with a similar title, or at a short-titled item, are missed.
- Crossref search can miss real works with no DOI, so the manual check uses PubMed and Europe PMC too.
- Title metadata errors and non-English titles cause false mismatches, which the manual check removes.

## Reporting and conduct
- Results are reported whatever they show, including a null.
- The public report gives aggregate counts. A specific reference is described only as "could not be verified in
  PubMed, Europe PMC or Crossref on <date>", never as "fabricated". Its paper is named only where both reads agree
  and the evidence is shown.
- No author, journal or publisher is contacted about any flag unless Sheehan (Munim, Inc.) has reviewed it first.
- Any change after the job runs is listed as a deviation, with its reason, in the results file.
