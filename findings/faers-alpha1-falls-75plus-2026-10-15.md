# FAERS falls / syncope / orthostatic hypotension: alpha-1 blockers and 5-ARIs, reports for people 75+ (2026-10-15)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0.
Research notes for the terazosin ReGen evidence package (package 6), not medical advice.

**Status.** The analysis plan was written before any data was pulled. It was kept locally and not published before
the data, so this is **not** a public pre-registration. Every count was read twice from openFDA, and every ratio was
first worked out by hand. The sealed job `faers-alpha1-v1` then re-ran all 18 RORs from the live API (`faers_alpha1.py`,
output `faers_alpha1_out.json`) and matched the hand table exactly; its 4 offline tests passed
(`test_faers_alpha1.py`).

Source: openFDA drug/event, `meta.last_updated` 2026-07-30, queried 2026-10-15. Patients aged 75-120 years (age unit
801). Drugs matched on `openfda.generic_name` in any role. Reference drug: tamsulosin. ROR with Woolf 95% CI.

| Drug | N reports 75+ | Fall n (%) | ROR fall | Syncope n (%) | ROR syncope | Orthostatic hypotension n (%) | ROR OH |
|---|---|---|---|---|---|---|---|
| Tamsulosin (ref) | 6,472 | 262 (4.05) | 1 | 138 (2.13) | 1 | 77 (1.19) | 1 |
| Terazosin | 2,503 | 136 (5.43) | **1.36 (1.10-1.68)** | 52 (2.08) | 0.97 (0.71-1.34) | 20 (0.80) | 0.67 (0.41-1.10) |
| Doxazosin | 9,831 | 393 (4.00) | 0.99 (0.84-1.16) | 374 (3.80) | **1.82 (1.49-2.21)** | 173 (1.76) | **1.49 (1.14-1.95)** |
| Alfuzosin | 1,493 | 69 (4.62) | 1.15 (0.88-1.51) | 31 (2.08) | 0.97 (0.66-1.44) | 19 (1.27) | 1.07 (0.65-1.77) |
| Finasteride | 15,502 | 777 (5.01) | **1.25 (1.08-1.44)** | 258 (1.66) | **0.78 (0.63-0.96)** | 130 (0.84) | **0.70 (0.53-0.93)** |
| Dutasteride | 3,059 | 140 (4.58) | 1.14 (0.92-1.40) | 77 (2.52) | 1.19 (0.89-1.57) | 55 (1.80) | **1.52 (1.07-2.16)** |

Co-listing (same age filter): dutasteride + tamsulosin 499 reports (16% of dutasteride's); finasteride + tamsulosin
1,029 (6.6%); terazosin + finasteride 394 (15.7% of terazosin's).

## Against the expectations in the plan

- Expected terazosin and doxazosin above 1 for syncope and OH: **doxazosin yes (1.82; 1.49). Terazosin no (0.97; 0.67,
  both CIs include 1).**
- Expected the 5-ARIs below 1: **finasteride yes for syncope and OH, but above 1 for falls (1.25). Dutasteride was
  above 1 for OH (1.52).**

## Reading

1. **In people 75+, terazosin shows no disproportionate reporting of syncope or orthostatic hypotension against
   tamsulosin.** Doxazosin does. In FAERS the two quinazolines are not interchangeable, and the haemodynamic signal sits
   with doxazosin.
2. **The terazosin falls ROR (1.36) is not specific to terazosin.** Finasteride has no effect on blood pressure, yet
   it gives 1.25 for falls. Fall reports track who is being reported on (older, frailer, more drugs), not the drug's
   mechanism. FAERS falls should not be cited as a harm specific to terazosin.
3. Dutasteride's OH signal fits co-listing: 16% of its 75+ reports also name tamsulosin (a dutasteride-tamsulosin
   combination product exists), and drug role is not matched.
4. **For package 6, section D:** FAERS adds no terazosin-specific safety signal beyond the label (first-dose syncope,
   orthostasis, titration from 1 mg at bedtime). A DLB/ADRD trial would still need orthostatic blood pressure at each
   titration step and falls as a pre-specified safety outcome. That rests on the label and on the disease (DLB
   itself causes dysautonomia), not on FAERS.

## Limits

These are spontaneous reports, so they give no user denominators, no incidence and no causality. Stimulated and
duplicate reports are not removed. Drug role (suspect or concomitant) is not tied to the matched drug. Age is missing on
many reports, so N is a subset. Indications differ: doxazosin and terazosin are also antihypertensives, while
tamsulosin and the 5-ARIs are BPH-only, and this confounds the haemodynamic events. Only MedDRA preferred terms are
used, with no SMQ. There is one reference drug and no adjustment for multiple comparisons (18 RORs).

## Prior art

Search: PubMed, `(FAERS OR "adverse event reporting system")` with the alpha-1 blocker names; 23 hits, titles read, 4
abstracts read.

- Ren 2025, Sci Rep (PMID 40133436): against the whole of FAERS, terazosin is the top orthostatic-hypotension signal of
  all drugs, ROR 153.96 (124.57-190.28); doxazosin 37.06. All ages, whole-database reference.
- Ohyama 2019, Pharmazie (PMID 31907118): men over 40. Non-selective alpha-1 blockers were associated with syncope; in
  hypertensive men tamsulosin (ROR 1.08, 0.90-1.30) and silodosin were not. Whole-database reference.
- Yoshimura 2013, Int J Med Sci (PMID 23781132): all four (alfuzosin, doxazosin, tamsulosin, terazosin) signal for
  dizziness and OH.
- Zhao 2026, Aging Male (PMID 41876378): BPH drugs including both 5-ARIs; its abstract reports no syncope, OH or falls
  results.
- **What this adds:** a within-class, active-comparator view in people 75+. Against tamsulosin, terazosin's OH and
  syncope RORs are 0.67 and 0.97. So the huge whole-database terazosin signal mostly reflects what any alpha-1 blocker
  for BPH carries, not anything extra terazosin adds in the oldest patients. Doxazosin, by contrast, stays elevated
  against tamsulosin. The finasteride falls ROR serves as a negative control, which the papers above don't use. This is
  an appraisal for package 6, not a discovery claim. The counts are small (20 terazosin OH reports), it uses one
  database, and it has not been replicated in JADER.

## Reproduce

`python faers_alpha1.py --out-dir out` (standard library, network). `python -m unittest test_faers_alpha1` runs offline.
