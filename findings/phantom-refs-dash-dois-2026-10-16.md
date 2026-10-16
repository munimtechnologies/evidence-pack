# Unicode hyphens in deposited reference DOIs: the dash-dois-v1 follow-up (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.
Research information about open citation metadata, not medical advice.

Follow-up to `phantom-included-studies-v1-results-2026-10-16.md` (side finding 2). That job found 148 reference DOIs, in 11
of 232 audited meta-analyses, that resolved nowhere and had no title text. This job re-read those 11 reference lists from
Crossref and checked every publisher-asserted reference DOI twice: as deposited, and with Unicode dashes replaced by the
ASCII hyphen-minus. It was added after the phantom-refs job, so it was not pre-registered; it is a descriptive count.

## Result (job `dash-dois-v1`, 2026-10-16 13:47-13:50Z, 12/12 offline tests passed)

| | count |
|---|---|
| Meta-analyses audited | 11 of 11 (10 Wiley, 1 Taylor & Francis) |
| Publisher-asserted reference DOIs | 582 |
| ... resolve as deposited | 434 |
| ... contain a Unicode dash | **131, every one U+2010 (HYPHEN)** |
| ... of those, resolve as deposited | **0 of 131** |
| ... of those, resolve once U+2010 is replaced by "-" | **129 of 131 (98.5%)** |
| Plain-ASCII DOIs that fail | 17 (14 in one Taylor & Francis paper, all cut off mid-DOI, e.g. `10.1136/bmj`) |

131 dash + 17 plain = the 148 references of the earlier side finding.

- **The dash is the whole problem.** No U+2010 DOI resolved as deposited, and 129 resolved after one character substitution.
  The two that still fail (both in PMID 42030436, normalised: `10.1590/S1517-838220100002000034` and
  `10.1016/S0168-1605(01)00753-8`) were not found at Crossref or doi.org even after normalising. Why was not checked.
- **It looks like a deposit pattern, not author typos.** In the 10 Wiley reference lists, 131 of the 143 publisher-asserted
  DOIs that contain any hyphen carry U+2010 in place of every hyphen, and 12 keep the ASCII hyphen. 8 of those 12 are in
  one article (Wound Repair and Regeneration, PMID 42332835: 8 ASCII, 1 U+2010), so lists can be mixed. In the same lists, DOIs
  without a hyphen (for example `10.3322/caac.21834` in PMID 42287032, next to `10.1038/s41572‐020‐00224‐3` with U+2010)
  resolve as deposited.
- **Not every Wiley article is affected.** A two-article random draw from Crossref (Wiley, 2026, by hand) gave one article
  with ASCII hyphens throughout (`10.1111/ics.70077`) and one with U+2010 (`10.1002/aenm.71508`).

## Downstream: the citations are missing from OpenAlex (by hand, 3 articles, 2026-10-16)

| Citing article | publisher DOIs | resolve as deposited | U+2010 | OpenAlex `referenced_works` |
|---|---|---|---|---|
| 10.1111/jop.70155 | 48 | 28 | 20 | **28** |
| 10.1111/scd.70230 | 82 | 52 | 30 | **52** |
| 10.1111/wvn.70108 | 61 | 45 | 16 | 0 (no references recorded) |

In the two articles OpenAlex has processed, its reference count equals the number of deposited DOIs that resolve, so
none of the 50 U+2010 citations appears to be counted. This is a count match, not a link-by-link check. The
pre-registered census below checks it link by link. OpenCitations had no references yet for `10.1111/jop.70155`
(empty list), so its coverage could not be judged from these articles.

**Why it matters for medicine:** systematic reviewers use forward and backward citation chasing (OpenAlex-based tools and
OpenCitations) to find studies, and citation counts feed research assessment. A cited trial that loses links this way
is harder to find by chasing and is under-counted.

## Is this new?

Crossref's DOI rules allow only the ASCII hyphen-minus (U+002D) and list U+2011-U+2014 as not allowed
(crossref.org/documentation/member-setup/constructing-your-dois). The open DOI-cleaning procedure of Cioffi et al. 2022
(Scientometrics 127:3593, doi 10.1007/s11192-022-04367-w; code open-sci/2020-2021-grasshoppers-code, `clean_dois.py`) has
no rule for Unicode dashes. A web search on 2026-10-16 found no report of U+2010 in publisher-deposited reference DOIs.
That is not proof that nobody has noticed. If you know of an earlier report, please open an issue.

## Next: a pre-registered census

`reference-dash-census-prereg-v1-2026-10-16.md` (committed with this file, before any census data is drawn) fixes how
the rate across Wiley and 10 other publishers will be measured, along with the link-by-link OpenAlex and OpenCitations
check.

## Limits

- The 11 meta-analyses were selected because they had failing references, so 131/134 says nothing about how common the
  pattern is. The census measures that.
- Resolution was checked against Crossref, then doi.org's handle API, on 2026-10-16. A later re-deposit could fix it.
- Nobody has been contacted about this. Contact is held for Sheehan's approval.

## Reproduce

`python dash_dois.py --out out` (standard library, network). `python -m unittest test_dash_dois` runs offline.
The job's per-article counts are in `dash_dois_rows.json`.
