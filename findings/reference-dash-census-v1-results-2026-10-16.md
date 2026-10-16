# Unicode dashes in publisher-deposited reference DOIs: census v1 results (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.
Research information about open citation metadata, not medical advice.

Pre-registration: `reference-dash-census-prereg-v1-2026-10-16.md` (committed in 450258f before any census data was
drawn). Job `dash-census-v1` ran in a sealed container on 2026-10-16, 16:21-16:27Z. All 12 offline tests passed.
Code: `dash_census.py`, `test_dash_census.py`. Data: `dash_census_v1/` (sampled articles, resolution checks,
OpenAlex/OpenCitations checks, generated results).

## Headline

**In a random sample of 300 Wiley journal articles from 2026 (January-September), 134 (44.7%) deposit at least one
reference DOI in which every hyphen is the Unicode HYPHEN (U+2010) instead of the ASCII hyphen-minus. None of those
DOIs resolve as deposited, and OpenAlex links only 1 of 134 such citations it could check.** Ten other large publishers
showed 0 affected articles. Within Wiley the share rose through 2026.

## Results against the predictions

| | Prediction (written before data) | Result | Verdict |
|---|---|---|---|
| H1 Wiley article share (articles with any hyphen-bearing publisher DOI) | ~45%; supported if Wilson lower bound > 5% | **134 / 263 = 51.0% (44.9-56.9%)** | supported |
| H2 other publishers | each <= 2%; holds for at least 9 of 10 | **0 affected articles in all 8 testable members**; 2 members had no data (below) | 8 of 8 testable hold; 9-of-10 not testable as written |
| H3 Wiley DOI share | >= 20% | **1,282 / 2,886 = 44.4%** of hyphen-bearing publisher DOIs | supported |
| H4 resolution (seeded 150 + 150) | dash as deposited <= 5%; normalised >= 90%; ASCII controls >= 90% | **0.0%; 98.7% (148/150); 99.3% (149/150)**; 0 lookup errors | supported |
| H5 OpenAlex link-by-link | dash <= 20%, controls >= 80%, >= 20 articles | **73 articles: 1 / 134 dash citations present (0.7%) vs 212 / 214 controls (99.1%)** | supported |
| H6 OpenCitations | dash <= 10%, controls >= 80%, >= 20 articles | 14 articles: 0 / 32 vs 39 / 42 (92.9%) | not testable (< 20 articles) |

Every dash character found was U+2010. No U+2011-U+2014, U+2212 or soft hyphen occurred in any member's sample.

### Per publisher (one random draw of 100 each; Wiley three draws, 300 distinct articles)

| Crossref member | Articles with a hyphen-bearing publisher DOI | Affected | Share (Wilson 95% CI) |
|---|---|---|---|
| Wiley (311) | 263 | 134 | 51.0% (44.9-56.9%) |
| Springer Nature (297) | 94 | 0 | 0% (0-3.9%) |
| Taylor & Francis / Informa (301) | 95 | 0 | 0% (0-3.9%) |
| SAGE (179) | 92 | 0 | 0% (0-4.0%) |
| Oxford University Press (286) | 65 | 0 | 0% (0-5.6%) |
| Wolters Kluwer / Ovid (276) | 9 | 0 | 0% (0-29.9%) |
| Frontiers (1965) | 96 | 0 | 0% (0-3.8%) |
| BMJ (239) | 79 | 0 | 0% (0-4.6%) |
| Cambridge University Press (56) | 89 | 0 | 0% (0-4.1%) |
| Elsevier (78) | 0 | - | no data |
| MDPI (1968) | 0 | - | no data |

**Why Elsevier and MDPI have no data (checked by hand, one article each):** they deposit references without a DOI, and
Crossref adds the DOI by matching (`doi-asserted-by: crossref`). In `10.1016/j.japhpi.2026.100096` all 8 reference
DOIs are Crossref-asserted; in `10.3390/electronics15153376` all 29 are. The census counts only publisher-asserted
DOIs, so these two members could not show the pattern. Matched DOIs come from Crossref's own index, so they would
not contain U+2010 anyway. Wolters Kluwer's 9 eligible articles are too few to say much.

## Exploratory (no predictions were made)

**Wiley by publication month** (affected / eligible): Jan 12/56 (21%), Feb 12/24 (50%), Mar 14/27 (52%), Apr 13/21
(62%), May 16/36 (44%), Jun 10/23 (43%), Jul 19/26 (73%), Aug 20/29 (69%), Sep 18/21 (86%). Pooled by quarter (hand
calculation): Q1 38/107 = 35.5% (27.1-44.9%), Q3 57/76 = 75.0% (64.2-83.4%). The intervals do not overlap, but this
was not pre-specified and the monthly samples are small. Census v2 (below) tests it.

**Whole lists or single entries:** 76 of the 134 affected articles carry U+2010 in every hyphen-bearing DOI. The other 58
mix both kinds. Some mixed lists have only one dashed DOI among many (Molecular Ecology 1 of 31; Business Ethics, the
Environment & Responsibility 1 of 28). Those few may come from the authors' own reference text, while the fully
dashed lists look like a production step. We have not checked how the dashes get in.

**Medicine and health are affected too.** Among the 134 affected articles are papers in the British Journal of
Clinical Pharmacology, Pediatric Blood & Cancer, The Laryngoscope, Digestive Endoscopy, Journal of Hepato-Biliary-
Pancreatic Sciences, Drug and Alcohol Review, International Journal of Eating Disorders, Journal of the International
AIDS Society, Clinical & Experimental Allergy, Journal of Clinical Nursing, Muscle & Nerve, Andrology, Medical Physics
and Journal of Applied Toxicology. Some lists are entirely affected: one Cell Proliferation article (78 of 78
hyphen-bearing DOIs), Advanced Materials (49 of 49), Journal of Applied Toxicology (30 of 30).

## Rough scale (hand extrapolation, not a pre-registered measure)

Crossref reports **230,121** Wiley journal articles with references published 2026-01-01 to 2026-09-30 (the census
frame, `total-results`, queried 2026-10-16). In the sample, 134 of 300 articles are affected (44.7%, Wilson 39.1-50.3%)
and the 300 articles carry 1,282 U+2010 DOIs (4.27 per article). Scaled to the frame, that is about **103,000 affected
articles (90,000-116,000)** and roughly **a million reference DOIs** (point estimate about 980,000). The DOIs cluster
within articles, so we give no interval for that figure. About 99% of these DOIs resolve once the dash is fixed, and
OpenAlex links almost none of them. **So on the order of a million citation links from 2026 Wiley papers are missing
from the open citation graph.** The cited works lose those citations. Systematic reviewers who chase citations
forwards or backwards with OpenAlex-based tools will not see these links. Census v2 replaces this extrapolation with
a full count.

## Is this new?

- Crossref's DOI rules allow only the ASCII hyphen-minus. Its troubleshooting page warns members about en- and
  em-dashes in their *own* DOIs (crossref.org/education/content-registration/verify-your-registration/troubleshooting-submissions/).
- Cioffi et al. 2022 (Scientometrics 127:3593, doi 10.1007/s11192-022-04367-w) sort invalid reference DOIs in Crossref
  by error type and publisher. Their cleaning rules don't cover U+2010, and their data predate 2026.
- Besançon et al. 2024 (JASIST, doi 10.1002/asi.24896) report reference lists that are sneaked or lost in deposited
  metadata. Czuma 2026 (arXiv 2606.24897) audits Unicode fidelity in *abstracts* across four APIs, not reference DOIs.
- Web searches on 2026-10-16 found no report of U+2010 in publisher-deposited reference DOIs, or of its scale or its
  effect on OpenAlex. That is not proof nobody has noticed. If you know of a report, please open an issue.

## Limits

- Crossref's `sample` is random but cannot be seeded. The drawn DOIs are saved in `dash_census_v1/articles.jsonl`.
- One snapshot (2026-10-16). Publishers can re-deposit references, so later counts may differ.
- H5 checks only citing articles that OpenAlex has references for (73 of 150 sampled) and cited works OpenAlex knows.
- The cause is not established. The pattern could come from typesetting, a reference-processing tool or author text.
- Nobody at Wiley, Crossref, OpenAlex or OpenCitations has been contacted. Any contact is held for Sheehan's approval
  and would point to this public write-up.

## Next: census v2 (pre-registered with this file, before its data)

`reference-dash-full-census-prereg-v2-2026-10-16.md` sets out a full count of all ~230,000 articles, a month-by-month
sample from 2023 to 2025 to find when the pattern began, and an open repair list mapping each deposited DOI to its
corrected form.

## Reproduce

`python dash_census.py --out out` (standard library, network). `python -m unittest test_dash_census` runs offline.
