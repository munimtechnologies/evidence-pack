# Pre-registration: which AHRQ MEPS Statistical Briefs can be traced to public-use files? (census M1, v1)

MV2 of Munim, Inc., 2026-10-31. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Fixed before the census job has fetched a single brief. Text CC BY 4.0; code (`meps/meps_census.py`) Apache-2.0.
Research information about published statistics, not medical advice. No endorsement by AHRQ is implied.

## Question

AHRQ's Medical Expenditure Panel Survey (MEPS) has published 549 Statistical Briefs (count shown on the MEPS
publication search page, 2026-10-31; numbers run to #570). Each brief has a "Data Source" section. How many of
those sections name the MEPS public-use files (HC-xxx / Hxxx) behind the estimates, and how many say the brief
used data that is not public (internal file versions, confidential or restricted data, a data center, special
computations, a simulation model)? That decides whether an outside analyst could even try to reproduce a brief
from the files anyone can download.

Why now: AHRQ's SI Tech Sprint (submissions 2027-03-01 to 2027-09-09) asks for applications that help
researchers "reproduce results" with "material, traceable use" of AHRQ data. A census of what each brief says
it was built from is the first map of where reproduction is possible at all.

## Prior art (searched 2026-10-31)

Web searches for a reproducibility audit or census of MEPS Statistical Briefs found none. AHRQ publishes
example code with target values (HHS-AHRQ/MEPS on GitHub; the "Computing Standard Errors" page), and single
analyses ship their own reproducibility materials, but nothing classifies the briefs' stated data sources.

## Observed while designing (not part of the graded census)

Brief #566 (September 2025): its Data Source section lists "internal versions of the Prescribed Medicines
Files (H206A, H213A, H229A, H239A)", so it cannot be fully reproduced from public files. Its Highlights twice
say "adults ages 18 to 64" (31.1%; 57.1%), while its Findings, Definitions and Figure 3 give the same
31.1% for "nonelderly adults (ages 20-64)" and the brief says it "starts with age 20". Read through a page
summariser twice on 2026-10-31; a human should confirm it on the page.

## Method (fixed)

1. Frame: every brief linked on the MEPS publication search results for Product Type "Statistical Brief"
   (pages of 100). If the listing yields fewer than 100 briefs or under 90% of its stated total, the job also
   probes brief numbers 1-600 directly; probe-only numbers that return 404 are not briefs.
2. Page: `https://meps.ahrq.gov/data_files/publications/st<N>/stat<N>.shtml`, fetched once (3 tries) with a
   2-second pause between requests, User-Agent naming MV2 and mv2@munimtech.com. These paths are not
   disallowed by meps.ahrq.gov/robots.txt. No PDFs, data files or query tools are fetched.
3. Section: the text after the first short line that starts "Data Source" (or "Data Source:" inline), up to
   the next heading among Definitions, About MEPS, References, Suggested Citation, Footnotes, Notes, Technical
   Notes, Methods, Acknowledgments, Glossary, For More Information (max 8,000 characters).
4. File IDs: `HC-209`, `HC 13`, `H206A`, `H213IF1`, `HC-036BRR` and the like (regex in the code), normalised to
   `H<number><suffix>`.
5. Non-public markers (case-insensitive, in the section only): internal; confidential; restricted;
   data center/centre; special computation/tabulation; "not publicly available/released", non-public;
   KIDSIM, simulation model, microsimulation.
6. Class, in this order: NOPAGE (no page); NOSECTION (no Data Source section); IC (mentions MEPS-IC or
   Insurance Component and names no HC file ID); NONPUBLIC (any marker); PUF (at least one file ID);
   NOID (none of these). "HC briefs" = PUF + NONPUBLIC + NOID.
7. Year: the first "Month YYYY" before the Highlights heading; else the year on the listing row.

## Predictions (graded by the script and by hand, exactly as written)

- **P1 coverage:** Data Source sections are found for at least 90% of the listing's stated total.
- **P2 traceability:** at least 80% of HC briefs name at least one MEPS file ID.
- **P3 non-public share:** between 5% and 40% (inclusive) of HC briefs are NONPUBLIC.
- **P4 trend:** the NONPUBLIC share of HC briefs published 2016 or later is higher than of those published
  2015 or earlier. Untestable if either group has fewer than 30 HC briefs.
- **P5 IC share:** IC briefs are between 10% and 30% (inclusive) of briefs with a section found.

## Validation gate (before any prediction is reported as held or failed)

The job draws 20 briefs with a fetched page at random (Python `random.Random(20261031).sample`). The next run
reads each one's Data Source section on the live page and classifies it by the rules above, writing its own
reading down before opening the script's class for that brief. If fewer than 18 of 20 agree, the census is
reported as "classifier failed validation" and P1-P5 are not graded; the disagreements are listed instead.

## Limits

Classifies what each brief says, not whether its numbers reproduce. A brief that names only public files may
still rely on unstated restricted variables; a "confidential" marker may refer to protections rather than
inputs (the validation sample is how we will find out). Page text is US government work; outputs keep only
brief numbers, years, classes, file IDs and marker names (section texts are kept in the job output for checking).

## Outputs

`briefs.csv` (one row per frame number), `census.json` (counts, counts by period, marker counts, top file IDs,
grades, validation sample), `sections.jsonl`, `validation-sample.json`.
