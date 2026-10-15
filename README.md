# evidence-pack

Triage generic drug -> condition pairs by how much clinical evidence exists, using public sources only: PubMed (NCBI E-utilities), ClinicalTrials.gov (API v2) and openFDA drug labels. Then pool the results that trials posted on ClinicalTrials.gov, as an independent check on what the journals report. No login, no patient data.

It is built for choosing and backing pairs for the NCATS **Repurposing Generic (ReGen) Drugs Evidence Package Challenge**, where packages are judged on the strength of clinical evidence that an off-patent drug works for a costly condition. The triage is a first pass, not an evidence review: counts include papers that only mention both terms, and nothing in it judges study quality.

Research information, not medical advice. Made by MV2 of Munim, Inc. with AI agents (Claude) working in his name. Code Apache-2.0; the findings text CC BY 4.0.

## Triage (`evidence_pack.py`)

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

## Registry pooling (`regpool.py`)

Journal meta-analyses pool what was published. `regpool.py` pools what sponsors posted on ClinicalTrials.gov, which includes small, terminated and never-published trials. Each study list in `studies/` names the trials, the posted outcome used and the transcribed numbers. The script gives each trial one standardized mean difference, signed so that a negative value favours the drug:

- mean and SD per arm, or mean and SE (SD = SE x sqrt(n)), as Hedges' g; two drug arms are combined first (Cochrane Handbook 6.5.2.10);
- `"kind": "groups"` (new in 0.3.0) for any number of drug and control arms, as in factorial designs, genotype strata or two doses. Each side is merged first. Spreads may be SDs, SEs, 95% CIs (SD from the t quantile, Cochrane 6.5.2.2) or medians with IQRs (mean and SD estimated as in Wan et al. 2014);
- counts of a good outcome (abstinent, no heavy drinking) or a bad one (relapse) per arm, as a log odds ratio x sqrt(3)/pi;
- a posted p-value and direction when the posted spread cannot be used;
- `"higher_better": true` for outcomes where more is better, such as days to relapse.

It pools them with DerSimonian-Laird random effects and reports Hartung-Knapp-Sidik-Jonkman intervals, prediction intervals, tagged subsets, a sensitivity set and leave-one-out. `--verify` re-downloads every trial's posted outcome measures, so each transcribed number can be checked against the registry record. `--compare A B` (new in 0.3.0) tests the subgroup difference (trials tagged B minus trials tagged A) in every study list, then combines the differences across lists and tests whether they agree (Q).

```
python -m unittest -v test_regpool
python regpool.py studies/topiramate_aud.json studies/gabapentin_aud.json studies/naltrexone_aud.json --out-dir out --verify --compare general comorbid
```

### Findings so far (alcohol use disorder, registry results only)

| Drug | Trials | g (all) | General AUD samples | Samples selected for another condition too | Status |
|---|---|---|---|---|---|
| [Topiramate](findings/topiramate-aud-registry-pool-2026-10-14.md) | 9 | -0.30 | -0.57 (k=4) | -0.10 (k=5) | registry-checked |
| [Gabapentin](findings/gabapentin-aud-registry-pool-2026-10-14.md) | 6 | -0.36 | -0.51 (k=4) | +0.04 (k=2) | registry-checked |
| [Naltrexone](findings/naltrexone-aud-registry-pool-2026-10-15.md) | 17 | -0.16 | -0.10 (k=6) | -0.22 (k=11) | preliminary (hand-computed), check queued |

The topiramate and gabapentin splits were found after the fact. The test fixed in advance on naltrexone ([pre-registration](findings/naltrexone-prereg-2026-10-15.md)) did not show the split, so it is not a general property of AUD trials. [Pre-registration 2](findings/aud-comorbidity-prereg-2-2026-10-15.md) fixes the same test for acamprosate, baclofen and varenicline before their data are read.

## First triage run (2026-10-14)

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
- Registry results are what sponsors typed in. Some posted SDs are on the wrong scale, some posted SEs come from models rather than raw data, and some posted "SDs" can only be SEs (NCT01932801). [ctgov-audit](https://github.com/munimtechnologies/ctgov-audit) screens for the impossible ones. `regpool.py` notes each conversion it makes.
- openFDA says its data are unvalidated; see [asof-kg's findings](https://github.com/munimtechnologies/asof-kg/tree/main/findings) on stale and empty label copies.

## Files

| File | What it is |
|---|---|
| `evidence_pack.py` | the triage script |
| `pairs.json` | the 13 pairs of the first run |
| `test_evidence_pack.py` | offline tests (queries, parsing, counts, rendering) |
| `regpool.py` | registry-results pooling and cross-list subgroup comparison |
| `studies/*.json` | study lists: topiramate, gabapentin and naltrexone for alcohol use disorder |
| `test_regpool.py` | offline tests (effect sizes, arm merging, pooling, hand-computed checks) |
| `findings/` | triage output, the three registry pools with job output and registry checks, and two pre-registrations |

Contact: MV2 of Munim, Inc., munimversion2@gmail.com.
