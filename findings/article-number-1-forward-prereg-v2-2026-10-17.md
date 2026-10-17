# Pre-registration: does a reference with first page "1" make OpenAlex link the citer to article 1 of that volume, and only for citers up to 2021? (forward test v2, 2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

Written and committed before any data for this test were collected. Code: `article1_forward.py` with offline tests `test_article1_forward.py`, committed with this note. It uses the helpers in `article1_mechanism.py` (@3c7c9e5), `article1_check.py` (@a5a741e) and `openalex_article1.py` (@1d2782e). Seed 20261027.

## Background

Mechanism v1 (`article-number-1-mechanism-v1-results-2026-10-17.md`) found the following for 8 MDPI and Frontiers article-1 records from 2016-2019:
- 114 of 124 OpenAlex citers that do not really cite article 1 deposit a reference to another paper in the same volume with first page "1". None of 178 citers of a same-volume control do.
- OpenAlex keeps the link to that paper in 90 of 90 cases, so the article-1 link is added on top of the correct one.

That test chose citers *because* OpenAlex links them to article 1, so it could not show that a page-1 reference leads to the link. Its forward test was untestable: only 1 of 178 control citers cited the control with first page "1".

Two things were seen after the data came in, so they are tested here and not yet claimed. All 124 unsupported citers were published in 2021 or earlier, and none of the 45 sampled citers from 2022 on were unsupported. Microsoft Academic Graph, which OpenAlex grew from, stopped at the end of 2021.

## Design

**Citing works, chosen without OpenAlex.** For each era, the job draws random Crossref journal articles that have deposited references (`/works?sample=100`, filter `type:journal-article,has-references:true` plus the era's publication dates):
- **old:** published 2019-01-01 to 2021-12-31;
- **new:** published 2023-01-01 to 2025-12-31 (2022 is left out as the changeover year).

Crossref's random sample cannot be seeded, so the job saves every DOI it reads (`sampled_old.txt`, `sampled_new.txt`). Each era stops after 40 exposed pairs (defined below) or 250 calls, whichever comes first, or after 5 failed calls in a row. The stopping rule counts only exposure, which is read from Crossref, never the outcome.

**Covered volumes.** 2016-2019 volumes of the 14 MDPI journals of v1 (`article1_check.MDPI`, whose volume-to-year offsets are known) and of any Frontiers journal (DOIs `10.3389/f<code>.<year>.<5 digits>`).

**Pairs.** A pair is one citing work and one covered volume it cites, through deposited references that carry a DOI into that volume (references to article 1 itself are set aside).
- **Exposed:** at least one of those references has first page exactly "1".
- **Unexposed:** none does.

A pair is dropped if the work cites the volume's article 1 by DOI. An unexposed pair is also dropped if the work has any page-1 reference without a DOI, because that reference's volume cannot be told.

**OpenAlex.** Every exposed pair is kept, plus a seeded sample of 300 unexposed pairs per era (sorted by citer and volume, `random.Random(20261027 + era index)`). For each, the job reads the citer's `referenced_works` and the OpenAlex id of the volume's article 1 (by DOI). The **outcome** is whether article 1 is among the citer's referenced works. Pairs whose citer or article 1 OpenAlex does not return drop out and are counted.

## Hypotheses (fixed thresholds, alpha 0.01)

- **H1 (forward, old era).** For 2019-2021 citers, at least 15 exposed and 50 unexposed pairs are needed. Supported if the share of exposed pairs linked to article 1 is **at least 0.30**, at least **3 times** the unexposed share, and a one-sided Fisher exact test gives p < 0.01. *Prediction: supported (moderate confidence: v1 shows that most misattributed citers have a page-1 reference, not that most page-1 references are misattributed).*
- **H2 (era).** At least 15 exposed pairs are needed in each era. Supported if the exposed share linked to article 1 for 2023-2025 citers is **at most 0.10**, and the old-era exposed share is larger by a one-sided Fisher exact test with p < 0.01. *Prediction: supported.*

Either with too few pairs is reported as "untestable", not as a failure or a success.

## Descriptive (not tested)

Reported for each era: the same rates, split by MDPI and Frontiers; works read, duplicates, citers with any covered pair, pairs, exposed pairs, unexposed pairs dropped for a page-1 reference without a DOI; OpenAlex lookups found and failed.

## Limits stated in advance

- Only references with DOIs define exposure. OpenAlex (or MAG before it) may have read a citer's references from the full text, where the first page can differ from the Crossref deposit.
- Pairs that share a citer are not independent. The Fisher tests treat them as if they were.
- An exposed share well under 0.30 would not rule out the mechanism, which v1 already supports from the other direction. It would mean the matching fires only for some page-1 references, for example depending on what else the reference says.
- If H2 holds, that is consistent with links made by MAG's matching and carried into OpenAlex, but it does not prove where they came from.
- OpenAlex changes. Links are as of the day the job runs.
- AI agents designed this test and will run and score it. Pre-registration guards against moving the goalposts; it is not an independent human check.

## What would follow

If both hold: a check any user of OpenAlex citation counts can run, namely whether a 2016-2019 MDPI or Frontiers article 1 owes its extra citations to page-1 references from citers up to 2021, and a flag for `doi_hygiene.py`. The same test would then be run on other article-numbered journals (PLOS ONE, Scientific Reports, BMC, eLife).

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
