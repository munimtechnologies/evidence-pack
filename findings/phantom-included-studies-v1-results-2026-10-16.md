# Unverifiable references in 2026 meta-analyses: results of pre-registration v1 (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name; both manual reads below were done by AI agents. No human has re-checked them yet. Text CC BY 4.0; code (`phantom_refs.py`, `test_phantom_refs.py`) Apache-2.0.

Plan: `findings/phantom-included-studies-prereg-v1-2026-10-16.md`. It was written and frozen locally before any reference list was read, but it was **not** published before the job ran (see Deviations).

## Bottom line

- **Screening (automatic): 18 of 232 meta-analyses (7.8%, 95% CI 5.0-11.9%) had at least one reference whose DOI did not lead to the cited work and that a Crossref search could not place.**
- **After two independent manual reads: 2 of 232 (0.9%, 95% CI 0.2-3.1%) still had a reference that could not be verified** in PubMed, Europe PMC, Crossref, the web or the journal's site.
- **Neither is shown to be a fabricated study.** One is a randomized trial that is registered on ClinicalTrials.gov, published in a journal issue that was never deposited with Crossref. The other is a garbled reference-manager entry.
- **The automatic screen overcalls about ninefold (21 candidates, 2 left).** Most false alarms are correct references to papers whose only registered title is not in English.

## What ran

`phantom-refs-v1` (sealed job, 2026-10-16 09:35-10:07 UTC; 15 of 15 tests passed):
- **Frame:** PubMed `meta-analysis[pt] AND 2026[dp]`, Entrez dates 2026-01-01 to 10-15. That gave 14,400 PMIDs (sha256 1553caaf…903c60); the plan's estimate was 14,355.
- **Sample:** 240 systematic picks, all processed. 232 had a deposited reference list. One had no DOI, 2 were not in Crossref and 5 had no references.
- **References read:** 7,673 publisher-asserted DOIs were checked. Of those, 4,809 matched the cited title, 48 were too short to judge and 2,534 had no title text to compare. 25 were mismatches and 178 were not found. 34 were real works cited under the wrong DOI (found by search), 79 were registered at another agency, 2 were fixable typos and 21 were unresolved.

## Manual check: 21 candidates, two reads

Read 1 and read 2 were done in separate sessions on 2026-10-16. Read 2 knew read 1's verdicts, so it is not fully blind (details in the read-2 record). Read 2 redid the searches for the two unverifiable references, the three wrong-DOI references and three of the non-English-title cases. **The two reads agreed on every reference checked twice; no third read was needed.**

| Verdict | References | Notes |
|---|---|---|
| Verified, DOI correct; the registered title is non-English or the citation shortens it | 13 | Portuguese, Italian, French, German and Polish titles. In the 3 spot-checked in read 2, Crossref holds **only** the original-language title (no `original-title` or `translated-title` field) |
| Verified, wrong DOI | 3 | the right DOI was found for each (Lancet Respir Med 2019, World J Pediatr 2018, Pediatr Nephrol 2015) |
| Verified on the publisher's site; DOI never registered | 2 | ATS conference abstracts (Am J Respir Crit Care Med supplements) |
| Verified; DOI correct, but **Crossref's record for the DOI is wrong** | 1 | see Side finding 1 |
| **Unverifiable after both reads** | **2** | below |

### The two unverifiable references

The plan's rule allows these to be named: both reads agree, and the evidence is shown. Neither is a claim of fabrication. Each could not be verified in PubMed, Europe PMC or Crossref on 2026-10-16.

1. **Alnoomani 2020, Egyptian Journal of Surgery 39(4):1088, DOI 10.4103/ejs.ejs_187_20**, cited in Cochrane review CD013291.pub2 (HoLEP for benign prostatic hyperplasia, 2026; PMID 42713842).
   - The DOI resolves nowhere. The paper is not in PubMed or Europe PMC, and the journal's old site now redirects to Ovid (no open access).
   - **Mitigating evidence:**
     - The cited title matches the official title of a completed, registered randomized trial word for word: NCT04471155, Ain Shams University, "Comparison of Holmium Laser Enucleation Prostatectomy and Open Transvesical Prostatectomy in Large Prostate More Than 80 Grams in Egyptian Men". Its investigator is M. N. Alnoomani.
     - Crossref holds 69 records for this journal's 2020 volume, all from issues 1 and 2 (pages up to 512). **Issues 3-4 were never deposited**, so a missing DOI for a paper on page 1088 of issue 4 is expected even if the paper exists.
   - **Role:** *unclear* under the plan's rule, because the review's full text is paywalled. Indirect evidence: in the review's Crossref-deposited reference list, this entry is reference 82, inside an alphabetical block (references 80-144, Ahmad 2026 to Zhang 2020) that holds the trial reports. The background and methods references (1-79) come before that block; a trial registration, a protocol and a second alphabetical run of other studies and reviews (145-158) follow it. So it is probably one of the 52 included trials.
   - Most likely reading: a real trial report in a journal issue that open metadata never captured. That is a gap in verifiability, not evidence of a phantom.
2. **Reference 2348_CR121 in PMID 42489790** (a 2026 systematic review and meta-analysis of gold nanoparticles as anti-inflammatory agents, Inflammopharmacology).
   - The deposited reference reads "Kuschner O'connor, Butz AM (2017) 乳鼠心肌提取 HHS Public Access. Physiol Behav 176:139-148", with DOI `10.1016/j.chempr.2016.07.007.Immunomodulatory` (the DOI of a *Chem* paper with a word glued on).
   - The Chinese text means roughly "neonatal rodent myocardium extraction". "HHS Public Access" is the banner printed on NIH author manuscripts in PMC. The same template, with different authors and DOI, appears in a Springer book chapter (10.1007/978-981-97-3115-2_3). So this is a reference-manager artefact copied between libraries, not a one-off typo.
   - **Role:** *unclear*. The paper's reference list is one alphabetical list, so position says nothing. The intended source cannot be identified.
   - Physiol Behav 176:139-148 is a real paper (Bunney et al. 2017, orexin and NEAT in mice). Its citation count looks badly inflated, and that is now a separate pre-registered study (`sink-check-v1`, queued).

### Endpoints

- **Primary:** 2/232 = **0.9% (Wilson 95% CI 0.2-3.1%)** of meta-analyses with ≥1 reference unverifiable after the manual check. The screening rate beside it is 18/232 = 7.8% (5.0-11.9%).
- **Key secondary:** 0 meta-analyses with an unverifiable reference *confirmed* as an included study. One is probably included (#1 above, role unclear under the rule).
- **Other secondary outcomes:**
  - unverifiable references per checked publisher DOI: 2/7,673 = 0.03%;
  - real work under a wrong DOI: 34 found by search plus 3 by hand, 37/7,673 = 0.48%;
  - malformed but fixable: 2;
  - not found: 178;
  - meta-analyses with deposited references: 232/240.

## Side findings (not part of the plan)

1. **One DOI, two papers.** For `10.1007/s10021-003-0125-0`, Springer's landing page shows Bubier et al., Ecosystems 6:353-367 (2003). Crossref's record for the same DOI says Zinko et al., Ecosystems 8(4):430-441 (2005). The citing paper gives Bubier's title and pages with "8(4)", which appears to be copied from the Crossref record. A DOI-based check flags this correct citation, and a Crossref lookup would make it wrong.
2. **Unicode dashes break deposited reference DOIs.** 148 references in 11 meta-analyses had DOIs that resolved nowhere and no title text. Nearly all contain U+2010 (hyphen) where the DOI has an ASCII hyphen-minus (for example `10.1038/s41572‐020‐00224‐3`). They never became candidates, so the primary endpoint is unaffected. A follow-up job (`dash-dois-v1`) is queued to count how many resolve once the dash is normalised.

## What this means for screening tools

A DOI-plus-title screen of meta-analysis reference lists flags about 8% of 2026 meta-analyses. About 90% of those flags (19 of 21 references; 16 of 18 meta-analyses) are false alarms: non-English registered titles, wrong DOIs on real papers, undeposited conference abstracts and journal issues, and Crossref metadata errors. **Matching on titles is the weak link, and adding translated-title fields will not fix it, because those fields are usually absent.** A v2 screen should match on DOI + first author + year + first page before comparing titles.

## Deviations from the plan

1. The plan was frozen locally on 2026-10-16 before the job ran, but published only now, with these results.
2. The existence check also used general web search; the plan named PubMed, Europe PMC, Crossref and the journal site. Web search found the two ATS abstracts.
3. Read 2 rechecked 8 of the 21 candidates (the two unverifiable ones, the three wrong-DOI ones and three non-English-title ones), not all 21. The other 13 were each verified with a matching title, first author and DOI in read 1. The plan asked for independent reads; read 2 knew read 1's verdicts, so agreement between them is weaker evidence than two blind reads would give. A human check of #11 and #14 is still owed.
4. For #1, the role was judged as "unclear" under the plan's rule. Its position in the reference list is reported as extra evidence and does not change that label.
5. The Unicode-dash follow-up and the citation-sink study were added after the job; neither changes the primary endpoint.

## Reproduce

`python phantom_refs.py --out out` (public PubMed E-utilities, Crossref and doi.org APIs; standard library only). `python -m unittest -v test_phantom_refs`.
