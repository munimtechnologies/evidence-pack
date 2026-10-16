# Terazosin and neurodegeneration: Fung et al. 2024 re-read against a 5-alpha-reductase-inhibitor comparator

MV2 of Munim, Inc. The analysis was done on 2026-10-15 and published 2026-10-16. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

- **Code:** `bucher_fung.py`, with `test_bucher_fung.py` checking it against the hand-computed values below.
- **Verified:** both ran in sealed job `med-checks-v1`, and the tests passed against these values (HR within 0.005, CI limits within 0.01).

## Source
- Fung KW, Baye F, Baik SH, McDonald CJ. PLoS One 2024;19(8):e0309222. PMID 39172922; PMC11340942. The authors are at NLM's Lister Hill Center, independent of the Iowa group (Simmering/Narayanan/Welsh). Read in full via NCBI efetch.
- **Population:** about 1.13 M Medicare men aged 65 and older with BPH, 2007-2020.
- **Comparisons:** every hazard ratio uses tamsulosin as the reference (898,523 users). The models are Cox with propensity-score regression adjustment. The only sensitivity analysis is use for more than 1 year.
- **Outcomes:** AD is defined by the CMS chronic-condition indicator; PD by ICD-9 332.0 / ICD-10 G20. Prevalent cases are excluded and at least 1 year of follow-up is required. No lag window is described.
- **Table 2** includes finasteride (n 72,205) and dutasteride (14,524) against the same reference. So an indirect alpha-1-blocker vs 5-ARI contrast can be read off the paper; the authors do not report one.

## Indirect HRs vs finasteride (Bucher method)
- **Method:** HR(A vs finasteride) = HR(A vs tamsulosin) / HR(finasteride vs tamsulosin), with the log-SEs combined as if independent.
- Both estimates share the tamsulosin group, so the true covariance is positive and the true intervals are slightly narrower than these (conservative).

| Contrast | AD | PD |
|---|---|---|
| Terazosin vs finasteride, overall | **0.74 (0.65-0.86)** | 0.82 (0.71-0.95) |
| Terazosin vs finasteride, >1 year of use | 0.77 (0.64-0.91) | 0.75 (0.63-0.89) |
| Doxazosin vs finasteride, overall | 0.86 (0.76-0.97) | 0.88 (0.77-1.00) |
| Terazosin vs finasteride, **death** | 1.04 (0.99-1.09) | |

## Reading
- **The AD association does not depend on tamsulosin being harmful.** Finasteride has no proposed PGK1 mechanism and a similar BPH user base. Against it, terazosin's AD HR stays at 0.74.
- **There is little sign of a healthy-user effect for terazosin.** Its mortality HR is about 1.0 against both tamsulosin (0.97) and finasteride (1.04). By contrast, tadalafil, a likely healthy-user drug, shows a death HR of 0.60 vs tamsulosin alongside AD 0.66. Mortality is not a clean negative-control outcome, though.
- **The drugs fall in the order the PGK1 hypothesis predicts:** terazosin (0.74) < doxazosin (0.86) < finasteride (reference). That holds only if terazosin engages PGK1 more than doxazosin does, which was not checked. It is an ordering across three drugs, not a dose-response.
- **The silodosin and prazosin rows fit too:**
  - silodosin, a uroselective blocker without the quinazoline structure, is null vs tamsulosin: 1.08 (0.90-1.30);
  - prazosin, a quinazoline, gives 0.71 (0.50-1.03), but its group is small.
- **A separate data source agrees:** with the Iowa group's DLB estimate vs 5-ARI (Hart 2024: 0.73, 0.57-0.93), two groups give terazosin-vs-5-ARI HRs of about 0.73-0.74 for two dementias, from different data (MarketScan vs Medicare).

## Limits
- This is an indirect contrast from a paper that adjusted each drug against tamsulosin, not a head-to-head model.
- AD is defined by a CMS algorithm. There is no lag window, so reverse causation is possible. The comparisons are between prevalent users.
- Observational association only. It does not show that terazosin prevents dementia.

## Trials (ClinicalTrials.gov, 2026-10-15; intervention terazosin; condition dementia, Alzheimer, Lewy or cognitive)
Two records, both not yet recruiting:
- NCT07796308, "Terazosin And Metabolic Engagement in Alzheimer's Disease", phase 2, n 100, start 2027-08;
- NCT04760860, "Terazosin for Dementia With Lewy Bodies", phase 1/2, n 40, start 2027-10.

No terazosin trial in dementia is past phase 2 or enrolling.
