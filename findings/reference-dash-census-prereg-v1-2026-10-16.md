# Pre-registration: Unicode dashes in publisher-deposited reference DOIs, a random-sample census (v1, 2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.

**Status:** written and committed before any census data was drawn. The job (`dash-census-v1`) runs later in a
sealed container. The code (`dash_census.py`, `test_dash_census.py`) will be published together with the results, and
any difference between this plan and the code will be listed there as a deviation.

## Background

`phantom-refs-dash-dois-2026-10-16.md`: in 10 Wiley reference lists, 131 publisher-asserted reference DOIs carry U+2010
(HYPHEN) instead of the ASCII hyphen-minus. 0 of the 131 resolve as deposited and 129 resolve after normalising. In two of those
articles, OpenAlex's reference count equals the number of resolving DOIs (28 and 52). Those 11 lists were selected because
they had failures, so they cannot show how common the pattern is.

## Questions

1. What share of Wiley's 2026 journal articles deposit at least one reference DOI with a Unicode dash?
2. Is the pattern specific to Wiley, or do other large publishers do it too?
3. Do those DOIs fail to resolve as deposited, and resolve once normalised?
4. Do the affected citations go missing from OpenAlex and OpenCitations?

## Sample

- **Source:** Crossref REST API, `/works?filter=member:<id>,from-pub-date:2026-01-01,until-pub-date:2026-09-30,`
  `type:journal-article,has-references:true&sample=100`. Crossref's `sample` is random but not seedable, so every drawn
  article DOI is saved.
- **Members and draws:** Wiley (311), 3 draws of 100, de-duplicated. One draw of 100 each from Elsevier (78), Springer
  Nature (297), Taylor & Francis (301), SAGE (179), Oxford University Press (286), Ovid / Wolters Kluwer (276), MDPI
  (1968), Frontiers (1965), BMJ (239) and Cambridge University Press (56). (Hindawi, member 98, was considered and left
  out: Crossref shows it with no current DOIs, since its journals moved to Wiley.)
- **Unit:** an article. Only references with `doi-asserted-by: publisher` count, since those DOIs were supplied by the
  publisher, not matched by Crossref.
- **Dash characters:** U+2010, U+2011, U+2012, U+2013, U+2014, U+2212 and U+00AD. Normalising replaces each with "-"
  and deletes U+00AD.

## Measures and hypotheses (predictions written before data)

- **H1 (primary), Wiley article share.** Denominator: sampled Wiley articles with at least one publisher-asserted
  reference DOI that contains any hyphen (ASCII or Unicode). Numerator: those with at least one Unicode-dash DOI.
  Supported if the Wilson 95% lower bound is above 5%. *Prediction: about 45% (any value from 20% to 80% would not
  surprise us).*
- **H2, other publishers.** Same share for each of the other 10 members. Predicted at or below 2% for every one of them.
  Each member is reported separately with its Wilson CI. *Prediction: holds for at least 9 of 10.*
- **H3, Wiley DOI share (descriptive).** Unicode-dash DOIs / all hyphen-bearing publisher-asserted DOIs, pooled over the
  Wiley sample. *Prediction: at least 20%.* The DOIs cluster within articles, so this is descriptive only.
- **H4, resolution.** Seed 20261016 (Python `random.Random`). From the sorted pool of (article, DOI) pairs, draw up to
  150 Unicode-dash DOIs and up to 150 ASCII-hyphen DOIs (the control), both from the Wiley sample. Each is checked at
  Crossref `/works/{doi}`, then doi.org `/api/handles/{doi}`. Lookup errors are excluded and counted.
  Supported if (a) at most 5% of dash DOIs resolve as deposited, (b) at least 90% resolve after normalising, and (c) at
  least 90% of the controls resolve.
- **H5, OpenAlex.** For each citing article in the H4 dash sample: its OpenAlex `referenced_works`, plus up to 3 control
  DOIs drawn with the same seed from that article's publisher-asserted DOIs that contain no Unicode dash. Cited DOIs are
  mapped to OpenAlex IDs with `filter=doi:`. The test uses only articles OpenAlex records at least one reference for, and
  only cited works OpenAlex has.
  Supported if, with at least 20 such articles, at most 20% of dash citations and at least 80% of control citations
  appear in `referenced_works`. *Prediction: about 0% vs about 95%.*
- **H6, OpenCitations (secondary).** The same test on `api.opencitations.net/index/v2/references/doi:{citing}`, using
  articles with at least one recorded citation. *Thresholds: at most 10% and at least 80%.* Not testable with fewer
  than 20 such articles. That is a real possibility, because OpenCitations lags and returned nothing for one 2026 article we checked.

## Exploratory (no predictions)

- Wiley breakdown by journal and by publication month.
- Which dash characters occur, per member.
- Articles with both ASCII and Unicode hyphens (mixed lists).

## What would change the reading

- If H1 fails (Wiley under 5%), the 10 lists were a rare cluster. The finding stays a curiosity, written up as such.
- If H2 fails for several members, the problem is industry-wide, not one publisher's pipeline.
- If H5 fails because dash citations are present in OpenAlex, OpenAlex is repairing them, and the practical harm is
  limited to Crossref and tools built on it.

## Reporting and contact

- Results will be published whatever they show, as `reference-dash-census-v1-results-<date>.md`, with the code and the
  sampled DOI list.
- No publisher, Crossref, OpenAlex or OpenCitations staff will be contacted unless Sheehan approves it. Any such contact
  would point to the public write-up only.
