# Phantom included studies v1: manual check, read 2 of 2 (2026-10-16)

MV2 of Munim, Inc. AI agents (Claude) research and draft this work in his name. Text CC BY 4.0.
Read 1: `findings/phantom-refs-manual-read1-2026-10-16.md`. Results: `findings/phantom-included-studies-v1-results-2026-10-16.md`.

Read 2 redid the searches in a separate session. It is not fully blind: it knew read 1's verdicts. For #15 its own bibliographic search found nothing, so it confirmed the correct DOI that read 1 had named; for #18, #19 and the language cases, its own searches found the records independently. It covered both of read 1's unverifiable references, all three of its wrong-DOI references and three of its non-English-title references.

| # | Read-2 searches | Read-2 verdict | Agrees with read 1 |
|---|---|---|---|
| 11 Alnoomani 2020, Egypt J Surg 39(4):1088 | Crossref bibliographic search (top 5: no match); Europe PMC `AUTH:"Alnoomani"` (1 hit, a 2011 hepatology paper); two web searches; DOI 10.4103/ejs.ejs_187_20 and neighbour ejs_188_20 (both 404); journal site (redirects to Ovid; LWW table of contents returns 402); Crossref facets for ISSN 1110-1121 in 2020 (69 works, issues 1-2 only, top page 512) | **unverifiable**. The cited title equals NCT04471155's official title, and issues 3-4 of the 2020 volume are missing from Crossref | yes |
| 11, role | Europe PMC references for PMID 42713842 (28 matched only; no Alnoomani); Cochrane Library references page (403); Crossref-deposited list of the review (158 entries) | **unclear** under the plan's rule. By position it is BIB0082, inside the alphabetical trial block BIB0080-0144 | n/a (read 1 did not reach it) |
| 14 ref 2348_CR121, PMID 42489790 | Crossref record of 10.1007/s10787-026-02348-6 (reference 125 of 287; neighbours CR118-CR124 are nanoparticle and inflammation papers); Crossref search for Physiol Behav 176:139 | **unverifiable**: a garbled reference-manager entry. Its volume and pages point at Bunney et al. 2017 (doi 10.1016/j.physbeh.2017.03.040), which is unrelated to the review's topic | yes |
| 14, role | single alphabetical reference list | **unclear** | n/a |
| 15 Goodman 2019 | Crossref `/works/10.1016/S2213-2600(19)30344-8` (404); `/works/…(19)30249-8` | verified, wrong DOI: real record "Challenges in the diagnosis of paediatric pneumonia in intervention field trials…", Lancet Respir Med 7(12):1068-1083 | yes |
| 18 Kari 2018 | Crossref bibliographic search | verified, wrong DOI: 10.1007/s12519-017-0110-x, World J Pediatr 14:134-142 | yes |
| 19 McCaffrey 2015 | Crossref bibliographic search | verified, wrong DOI and pages: 10.1007/s00467-015-3089-3, Pediatr Nephrol 30:1861-1871 | yes |
| 1 Binotto 2019 | Crossref author search within ISSN 1518-8345, 2019 | verified: 10.1590/1518-8345.2667-3138, e3138. The title is Portuguese only | yes |
| 5 Moubachir 2016 | Crossref bibliographic search | verified: 10.1016/j.rmr.2015.11.015, Rev Mal Respir 33:789-793. The title is French only; there is no `original-title` field | yes |
| 21 Neagoe 2016 | Crossref bibliographic search | verified: 10.5603/ep.a2016.0013, Endokrynol Pol 67:202-209. The title is Polish only | yes |

**Agreement: 8 of 8 references checked in both reads.** No third read is needed.

**One correction to read 1's suggested fix.** Read 1 proposed matching Crossref's `original-title` or `translated-title` fields. In all three language cases checked here, those fields are absent and only the original-language title is registered. A v2 screen should match on DOI + first author + year + first page, and compare titles only as a tiebreak.
