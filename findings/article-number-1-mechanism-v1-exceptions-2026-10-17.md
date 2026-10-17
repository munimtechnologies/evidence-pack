# Article number 1 in OpenAlex: reading the exceptions to the mechanism result (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research information, not medical advice. No independent human check has been done yet.

**Status: post hoc.** This note reads by hand some of the records that did not fit the pre-registered mechanism test. Nothing here was predicted, and the cases were chosen by us, not at random. It explains individual cases; it is not a rate.

## Background
The mechanism test (`article-number-1-mechanism-v1-results-2026-10-17.md`, data `article1_mechanism_v1_reads.jsonl`) looked at 124 OpenAlex citers that link article 1 of a 2016-2019 MDPI or Frontiers volume even though their Crossref-deposited references do not cite it. In 114 of them, a Crossref reference with a DOI points to another paper in the same volume and gives its first page as "1". That left **10 exceptions**:
- 8 have a DOI reference into the same volume, but none with first page "1";
- 2 (both citers of Materials 10:1, 10.3390/ma10010001) have no DOI reference into the volume at all.

The test script only read references that carry a DOI.

## Which cases we read, and why
- Both Materials 10:1 cases, because they were the most anomalous (no same-volume DOI reference at all).
- One of the 8, 10.1128/mbio.01376-19, because it is open access in PubMed Central, so its reference list could be checked against a second source (Europe PMC).

Sources, all read on 2026-10-17: Crossref `/works/{doi}` (deposited references), OpenAlex `/works/doi:{doi}?select=referenced_works` and `/works?filter=cited_by:{id}` (the DOIs of every linked reference), and Europe PMC `/MED/{pmid}/references`.

## Case A: same mechanism, through a reference with no DOI
**Citer:** 10.1088/1742-6596/1082/1/012074 (J. Phys.: Conf. Ser. 2018, akermanite bioceramics).
- Crossref holds 29 deposited references, 15 of them without a DOI. Reference 1 reads, field by field: author "No YJ", journal "Materials Journal", volume "10", first page "1", year "2017". It has no DOI and no title.
- OpenAlex links 22 references, among them Materials 10:1 (W2561630573: Wang, Tsai & Hwang, a 2016 paper on printing conductive structures with molten lead-free solder).
- The paper the authors most likely meant is No YJ, Li JJ, Zreiqat H. *Doped calcium silicate ceramics: a new class of candidates for synthetic bone substitutes.* Materials 2017;10(2):153, doi:10.3390/ma10020153. The citer is about a calcium magnesium silicate bioceramic. OpenAlex (W2587957905) does **not** link it. We matched this from author and topic only; we did not read the citer's full text.
- **Reading:** this is the same page-"1" mechanism, reached through a structured reference with no DOI ("Materials, vol. 10, p. 1"). It is the form closest to the "vol:1-N" references Kriváchy described (arXiv:2511.01675). The test missed it only because it read DOI references alone.

## Case B: an unexplained link from a reference with no DOI
**Citer:** 10.1016/j.matdes.2017.02.006 (Materials & Design 2017, diffusion coatings on magnesium alloys).
- Crossref holds 41 references, 40 of them with DOIs. OpenAlex links 41 works.
- Matched one to one by DOI, **all 40 DOI references appear in OpenAlex**. The 41st OpenAlex link is Materials 10:1.
- The one reference without a DOI is `bb0095`: Zhang, "Research on microstructure and properties of aluminum alloyed coating on AZ91D magnesium alloy by vacuum solid diffusion", *Rare Metal Mater. Eng.* 37, first page 2023, 2008.
- That reference shares nothing with Materials 10:1 (author, year, volume, page, title or topic), apart from the abbreviation "Mater." in its journal title. The citer also has a reference with first page "1" (Wang, *Mater. Des.* 89:1, 2016), but it carries a DOI and OpenAlex links it correctly.
- **Reading:** OpenAlex appears to have resolved the one reference it could not match by DOI to Materials 10:1. We do not know why. This is a different error from the page-"1" mechanism.

## Case C: links from a second reference source
**Citer:** 10.1128/mbio.01376-19 (mBio 2019, chromatin profiling of *Candida albicans*; PMID 31337722, PMC6650553).
- Crossref holds 72 references, all with DOIs. Europe PMC's reference list also has 72 entries.
- OpenAlex links **78** works. All 72 Crossref DOIs are among them. The 6 extra links are:
  - 10.3390/ijms18010001 (article 1, the target);
  - 10.3390/ijms18020359 (another paper from the same IJMS volume);
  - 10.7554/elife.03671;
  - 10.4161/viru.26803;
  - 10.1111/j.1365-2958.2006.05121.x;
  - 10.1128/mcb.13.1.551-560.1993, a second DOI form of a paper the citer does cite (10.1128/mcb.13.1.551).
- The only IJMS paper in both the Crossref and the Europe PMC lists is 10.3390/ijms18071486 (Nair et al. 2017, IJMS 18(7):1486; Europe PMC prints the page as "E1486"). OpenAlex links it correctly. Its own Crossref and OpenAlex records give page 1486, not 1.
- Europe PMC's list has no DOIs. Checked by journal, year and pages, it has no second IJMS paper, no Mol. Microbiol. paper from 2006, only one eLife paper (page e04506) and no 2013 Virulence paper. So 5 of the 6 extras are absent from both lists, and the sixth is a duplicate DOI.
- **Reading:** here the article-1 link arrives with four other links that neither the publisher's deposit nor PubMed Central lists. OpenAlex must have a second reference source for this work. We cannot see whether a page "1" plays any part in that source.

## Tally (post hoc, hand-read)
| Of the 124 unsupported citers | n |
|---|---|
| Page-"1" DOI reference into the volume (test result) | 114 |
| Page-"1" reference with no DOI (case A) | 1 |
| Other OpenAlex-side links (cases B and C) | 2 |
| Not read | 7 |

So 115 of 124 (93%) are explained by a reference with first page "1", with or without a DOI. The remaining cases show that OpenAlex has at least two other ways of adding article 1.

**For the 7 unread exceptions** we only compared counts. OpenAlex links more works than Crossref deposits for 5 of them (+3, +3, +4, +11 and +16), the same number for 1, and fewer for 1 (-4). As in case C, that hints at a second reference source, but we have not worked out the base rate among the 114, so this is not evidence.

## What this changes
- **The mechanism result stands.** None of the three cases contradicts it, and case A is one more instance of it.
- **The forward test (`article-number-1-forward-prereg-v2-2026-10-17.md`) counts exposure only through DOI references,** as pre-registered. Case A shows that page-"1" references without a DOI can expose a citer too. Any such citer is counted as unexposed, which can only raise the unexposed link rate, so the test's H1 comparison is conservative. We are not amending the pre-registration. The results note will state this limit.
- **For people auditing citation counts:** a DOI-only check of a citer's references can miss the cause. In OpenAlex, also compare `referenced_works_count` with the publisher's reference count. A large surplus means links that the publisher's list does not contain.

## Limits
Three cases, chosen by us. We read metadata, not full texts. The intended paper in case A is inferred, not confirmed. OpenAlex records can change after the date of reading.
