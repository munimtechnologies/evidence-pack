# Article number 1 at MDPI and Frontiers: results, scored against the pre-registration (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice. No independent human check yet.

- Pre-registration: `article-number-1-prereg-v1-2026-10-17.md`, committed in 92cd81f (release v0.4.13, 2026-10-17 01:44 UTC).
- Code: `article1_check.py` at a5a741e (offline tests passed in the job before the run).
- Job `article1-check-v1`: ran 2026-10-17 03:26:14 to 03:55:10 UTC, after the pre-registration was public. 8,788 Crossref calls.
- Data, in this repository: `article1_check_v1_results.json` (with the per-unit table: every unit's article-1 and far-control summary) and `article1_check_v1_reads.jsonl` (the 240 deposited references classified for H4). The full per-article file (`units.jsonl`, about 2.4 MB) is over the repository's 2 MB per-file limit and is not published. The same frozen code rebuilds it from Crossref (see `rebuild_units.py` and `article-number-1-openalex-prereg-v2-amendment-2026-10-17.md`).
- Deviations: none in code or thresholds. One gap in coverage is described below.

## Bottom line

**In Crossref, article-1 records at MDPI and Frontiers are not inflated the way Springer Nature's are.** All four hypotheses failed. Frontiers came closest (p = 0.032 against the pre-set 0.01). One MDPI record is a clear sink, though. Of 28 classifiable references credited to Energies 11:1 in a random sample, 27 cite other papers. Crossref's own matcher linked them, and they share the article's first-author surname (Wang), the journal and "page 1".

A separate, unscored pattern is larger. **OpenAlex** gives many 2016-2019 article-1 records 5 to 57 times their Crossref counts. For example, Int J Mol Sci 17:1 has 862 in OpenAlex and 15 in Crossref, and Front Plant Sci 2016:1 has 1,503 and 41. Whether this is specific to article 1 can only be tested against the controls. That test is pre-registered separately: `article-number-1-openalex-prereg-v2-2026-10-17.md`.

## Scores

| | Our guess | Result | Verdict |
|---|---|---|---|
| H1 MDPI: article 1 top more often than chance (p < 0.01) and median R of at least 2.0 | supported | 102 units; top in 8 (4.87 expected); p = 0.115; median R 1.65 | **not supported** |
| H2 Frontiers: same rule | not supported | 50 units; top in 6 (2.40 expected); p = 0.032; median R 2.20 | **not supported** |
| H3 MDPI near band (articles 2-30) above far band (41-60) | not supported | 102 units; 50 higher, 50 lower; p = 0.54; median q 1.00 | **not supported** |
| H4 misattributed: genuine share under 0.50 (n of at least 20); calibration first | supported if H1 is | calibration passed (102 of 104 control references genuine, 0.98); targets 67 of 97 genuine (0.69) | **not supported** |

Two of our four guesses were right (H2 and H3). H1 was wrong. H4 was guessed only conditionally ("supported if H1 is"), and it failed along with H1.

## Units and coverage

- **MDPI:** 111 volumes found (14 journals, 2016-2023; Sustainability volume 10 has no article 1 in Crossref). 102 are eligible. Excluded: Int J Mol Sci 20 (the motivating case) and 8 volumes with fewer than 10 far controls found (IJMS 17 and 19, Remote Sensing 10, Molecules 23, Cells 5 and 6, Antioxidants 5, Nutrients 8).
- **Frontiers:** 50 units, 2016-2020 only. **Coverage gap:** the pre-registration assumed 5-digit Frontiers article numbers (`10.3389/fimmu.2021.00001`). From 2021, Frontiers DOIs end in 6-digit numbers (for example `10.3389/fonc.2021.617597`, one of the citers read for H4), so no 2021-2023 unit could be built. The rule found nothing for those years, and nothing was changed after the data were seen.
- **Article-number field:** 20 of the 50 Frontiers article-1 records (all ten journals in 2016 and 2017) have no `article-number` in Crossref. Every MDPI record gives "1".
- **IJMS 20:1 (motivating, reported separately):** 46 Crossref citations against a far-control median of 32 (R 1.42, not top). OpenAlex gives it 1,093. Its excess is in OpenAlex, not Crossref.
- **Known Springer Nature sinks, for scale:** Crossref gives Sci Rep 9:1 7,152 and Nat Commun 9:1 6,502. No MDPI or Frontiers article 1 has more than 296 in Crossref.

## Reading the H4 rows

The three targets were the confirmatory MDPI article-1 records with at least 100 Crossref citations and the highest R. Forty OpenCitations citers of each were read:

| Target | Crossref cites | R | genuine | other work | DOI only | no matching ref |
|---|---|---|---|---|---|---|
| J Clin Med 7:1 (`10.3390/jcm7010001`) | 277 | 17.4 | 34 | 0 | 5 | 0 (1 citer not in Crossref) |
| Materials 13:1 (`10.3390/ma13010001`) | 196 | 14.6 | 32 | 3 | 4 | 1 |
| Energies 11:1 (`10.3390/en11010001`) | 136 | 7.8 | 1 | 27 | 7 | 5 |

The pooled 0.69 hides two different stories. J Clin Med 7:1 and Materials 13:1 are mostly cited for themselves; they are simply well-cited papers. **Energies 11:1 is a sink.** Its first author is Jing Wang. Of the 27 references to other work, 23 were linked by Crossref itself (`doi-asserted-by: crossref`). The 8 we read in full each name a different Wang paper in Energies with first page "1" (the rest are in `article1_check_v1_reads.jsonl`), for example:

- "Overview of compressed air energy storage and technology development" (Energies, 2017, volume given as 991)
- "Reservoir permeability evolution during the process of CO2 enhanced coalbed methane recovery" (Energies, volume 11, 2018)
- "Influencing factors and decoupling elasticity of China's transportation carbon emissions" (Energies, volume 11, 2018)
- "Impact of thermal pretreatment temperatures on woody biomass chemical composition, physical properties and microstructure" (Energies, volume 11, 2018)

The woody-biomass paper is article 25 of the same volume (`10.3390/en11010025`, first author also Wang). Its PDF's page range "1-..." stood in for the article number, which is the mechanism Kriváchy described. Several of these references give volume 10 or a garbled volume, and Crossref still matched them to volume 11, article 1. The one genuine reference gives the real title. **Rough extrapolation, not a test:** if the sample is typical, about 96% (27 of 28) of the classifiable references credited to Energies 11:1 cite something else.

Materials 13:1 has 3 other-work references. Two of them carry only an author name (Slepicka) and no title, so they are less certain.

## What this adds

Kriváchy (arXiv:2511.01675) measured article-1 inflation at Springer Nature in Crossref, OpenCitations and Semantic Scholar. MDPI's Dietrich Rordorf suggested on Retraction Watch that MDPI references carry PDF page ranges, without a measurement. We found no published measurement for MDPI or Frontiers (searches on 2026-10-17). This study gives one:

- At volume level in Crossref, no systematic inflation shows at MDPI. Frontiers shows a weak signal that falls short of the bar.
- Individual sinks exist. They arise when Crossref's matcher pairs a reference's author surname, journal and first page "1" with an article 1 by an author of the same surname.

The much larger OpenAlex excess on 2016-2019 records is a lead. An OpenAlex community thread already reports one similar case: a 2019 Scientific Reports article with 1,787 OpenAlex citations against 30-40 elsewhere (groups.google.com/g/openalex-community/c/Os0ah6pU2Us). We found no measurement across journals.

## Limits

- Crossref counts only, for the scored tests. A unit is a volume of a large journal chosen by name before any counts were seen, not a random sample.
- The H4 classifier is a heuristic. It passed its calibration, but the per-target split above was read after scoring.
- The Frontiers 2021-2023 gap means H2 covers 2016-2020 only.
- AI agents designed, ran and scored this. The pre-registration guards against moving the goalposts. It does not replace an independent human check.

No one at MDPI, Frontiers, Crossref, OpenCitations or OpenAlex, and no author, has been contacted.
