# evidence-pack

Triage generic drug -> condition pairs by how much clinical evidence exists, using public sources only: PubMed (NCBI E-utilities), ClinicalTrials.gov (API v2) and openFDA drug labels. No login, no patient data.

It is built for choosing pairs for the NCATS **Repurposing Generic (ReGen) Drugs Evidence Package Challenge**, where packages are judged on the strength of clinical evidence that an off-patent drug works for a costly condition. It is a first pass, not an evidence review: counts include papers that only mention both terms, and nothing here judges study quality.

Research information, not medical advice. Made by MV2 of Munim, Inc. with AI agents (Claude) working in his name. Code Apache-2.0; the findings text CC BY 4.0.

## What it does

For each pair in `pairs.json` (a drug, a PubMed condition clause and a ClinicalTrials.gov condition query), `evidence_pack.py`:

- counts PubMed records naming the drug and the condition, overall and by publication type (randomized controlled trial, meta-analysis, systematic review, observational study, phase II, phase III), and lists the 15 newest trials and reviews (PMID, year, journal, title);
- pulls every ClinicalTrials.gov registration of the drug in the condition and counts interventional, phase 2+, completed, with posted results, and still active;
- counts openFDA labels of the drug and how many carry a boxed warning, and quotes one;
- ranks the pairs by a rough score, RCTs + 2 x meta-analyses + 3 x phase 2+ trials with posted results, and writes `triage.md` plus one JSON file per pair.

```
python -m unittest -v test_evidence_pack
python evidence_pack.py --pairs pairs.json --out out
```

Standard library only (Python 3.9+). It makes about 10 requests per pair and pauses between them.

## First run (2026-10-14)

13 pairs on conditions from the ReGen priority list. Full output: [findings/triage-2026-10-14.md](findings/triage-2026-10-14.md).

| Pair | RCT | Meta-an. | Phase 2+ with results | Score |
|---|---|---|---|---|
| topiramate -> alcohol use disorder | 51 | 10 | 9 | 98 |
| pramipexole -> depression | 35 | 13 | 6 | 79 |
| varenicline -> alcohol use disorder | 30 | 6 | 10 | 72 |
| minocycline -> depression | 26 | 14 | 3 | 63 |
| gabapentin -> alcohol use disorder | 26 | 9 | 5 | 59 |
| lithium -> Alzheimer's disease / MCI | 16 | 9 | 3 | 43 |
| prazosin -> alcohol use disorder | 21 | 2 | 5 | 40 |
| levetiracetam -> Alzheimer's disease / MCI | 7 | 2 | 2 | 17 |
| metformin -> knee osteoarthritis | 5 | 5 | 0 | 15 |
| mirtazapine -> methamphetamine use disorder | 8 | 2 | 1 | 15 |
| methotrexate -> knee osteoarthritis | 5 | 3 | 0 | 11 |
| verapamil -> type 1 diabetes | 1 | 1 | 2 | 9 |
| spironolactone -> alcohol use disorder | 0 | 0 | 0 | 0 |

What the counts do not tell you, from reading the abstracts afterwards:

- **The score rewards volume, not results.** Methotrexate for knee osteoarthritis scores low, but it has two large placebo-controlled trials: a positive one (PROMOTE, n=155, pain -0.79 points on a 0-10 scale at 6 months, 95% CI 0.08 to 1.51; PMID 39074374) and a null one (n=215, 52 weeks; PMID 40455462). Pramipexole's count includes many Parkinson's-disease depression papers; its newest unipolar trial (PAX-D, n=150, QIDS-SR16 difference -3.91, 95% CI -5.37 to -2.45; PMID 40602411) is what makes it strong.
- **A boxed-warning count is a label count, not a drug fact.** "58/120" for lithium means 58 of 120 lithium labels in openFDA carry the box; labels of combination products and copies differ.
- **Popular is not the same as unknown.** Topiramate and gabapentin already appear in alcohol-use-disorder guidelines, so a package on them argues for wider use rather than a new idea.

## Limits

- PubMed publication types are assigned by indexers and lag new papers by weeks.
- ClinicalTrials.gov condition and intervention searches are fuzzy: they find related trials (for example smoking cessation in heavy drinkers under varenicline -> alcohol use disorder).
- openFDA says its data are unvalidated; see [asof-kg's findings](https://github.com/munimtechnologies/asof-kg/tree/main/findings) on stale and empty label copies.

## Files

| File | What it is |
|---|---|
| `evidence_pack.py` | the triage script |
| `pairs.json` | the 13 pairs of the first run |
| `test_evidence_pack.py` | offline tests (queries, parsing, counts, rendering) |
| `findings/triage-2026-10-14.md` | the first run's full output |

Contact: MV2 of Munim, Inc., munimversion2@gmail.com.
