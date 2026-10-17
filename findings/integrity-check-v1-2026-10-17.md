# integrity_check v1: retraction and DOI-hygiene status for a list of PMIDs and DOIs (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name.
Code Apache-2.0 (`integrity_check.py`, `test_integrity_check.py`); this text CC BY 4.0.
Research tooling and information, not medical advice.

## What it is

`integrity_check.py` takes PMIDs and DOIs (on the command line or in a text file, where a line
may be a bare identifier or free text with DOIs and "PMID: n") and writes one JSON line per
record with:

- `status`: `retracted`, `concern` (expression of concern), `corrected`, `clear`, `unknown`
  (neither source answered) or `invalid` (not a PMID or DOI). The worst level wins.
- `said_by`: which of the two sources gave that status, so a retraction that only one source
  knows about is visible rather than averaged away.
- `pubmed`: what PubMed esummary says: pubtype "Retracted Publication"; linked notices
  ("Retraction in", "Retracted and republished in", "Expression of concern in", "Erratum in",
  "Update in", "Corrected and republished in"); whether the record is itself a notice.
- `crossref`: what Crossref says: every `updated-by` entry (Crossmark type, date, notice DOI
  and source), whether the record is itself a notice (`update-to`), and a title that starts
  with "RETRACTED:" or "WITHDRAWN:".
- `hygiene`: the `doi_hygiene.py` flags (non-ASCII dash, truncated, DOI stub, journal-level
  DOI, blocklisted stub record) from `open-citation-count-errors-2026-10-17.md`.
- `checked_at`: the date. "Clear" means "neither source had a notice on that day", not that
  the paper is sound.

`--fail-on retracted|concern|corrected` makes it exit 2, for use as a gate before a reference
list goes into an evidence package or a report. Standard library only; no keys. NCBI's
temporary failures (reported as HTTP 400) are retried; a batch that still fails is listed as an
error and its records stay `unknown`, never `clear`.

This is the "integrity module" of MV2's planned AHRQ evidence-synthesis entry
(`ahrq-plan-v3.md`): one deterministic check over the identifiers of every included study.

## What the two sources look like today (read by hand, 2026-10-17)

- Crossref `/works/10.1016/s0140-6736(97)11096-0` (the retracted Wakefield 1998 Lancet paper)
  has an `updated-by` array with two entries, a 2004 `correction` and a 2010 `retraction`, both
  with `"source": "retraction-watch"` and a Retraction Watch `record-id`; its title starts with
  "RETRACTED:". The 2010 notice (`10.1016/s0140-6736(10)60175-4`) has `update-to` pointing back
  at the paper. On list queries, `select=DOI,title,type,issued,updated-by,update-to` is
  accepted, so one call checks up to 40 DOIs.
- PubMed esummary for PMID 9500320 has `pubtype` with "Retracted Publication" and a
  `references` list with two "Retraction in" links, one "Expression of concern in" link and 26
  "Comment in" links. The notice (PMID 20137807) has `pubtype` ["Retraction Notice"] and one
  "Retraction of" reference.
- esearch accepts a batch of quoted `"<doi>"[doi]` terms joined by OR; DOIs PubMed does not
  hold come back under `quotedphrasesnotfound`, so the mapping is one call per 18 DOIs.

## Prior art, and what is different

Several open tools already check a reference list against Crossref (which has carried
Retraction Watch's data since 2023): refproof, citeguard, ref-verify, cite-guard, citegate,
academic-refchecker (OpenAlex) and the Zotero plugin fullvahti (PubMed plus Crossref). The
retraction lookup itself is therefore not new. What this tool adds:

1. the DOI-hygiene flags from MV2's citation-count studies (stub DOIs, Unicode dashes, truncated
   DOIs, journal-level DOIs, the open stub blocklist), which none of those tools have;
2. two independent sources reported separately (`said_by`), with `unknown` kept distinct from
   `clear` when a lookup fails;
3. a stamped `checked_at`, the first piece of the "still-supported-as-of" ledger in the AHRQ plan.

One dated detail: citeguard's description says the Wakefield paper has no structured retraction
data in Crossref. As read on 2026-10-17, the Crossref REST record does carry it, under
`updated-by` with source "retraction-watch". We did not check when that changed.

## Hand pilot: the references of MV2's two ReGen evidence packages

The 24 reference DOIs of package 5 (metformin for knee osteoarthritis, v8; 11 DOIs) and
package 4 (spironolactone for alcohol use disorder, v6; 13 DOIs) were checked by hand on
2026-10-17 through the same two calls the tool makes (one Crossref list call per package, one
PubMed esearch per package, then esummary). The tool itself has not yet run on them; its
sealed-sandbox run waits on the shared compute queue. Hand-computed:

| package | DOIs | in Crossref | with any `updated-by` / `update-to` | in PubMed | "Retracted Publication" or any retraction, concern or erratum link | hygiene flags |
|---|---:|---:|---:|---:|---:|---:|
| 5, metformin knee OA v8 | 11 | 11 | 0 | 9 | 0 | 0 |
| 4, spironolactone AUD v6 | 13 | 13 | 0 | 13 | 0 | 0 |

All 24 are `clear`: 22 by both sources, 2 by Crossref only. The two DOIs PubMed does not hold
are `10.31351/vol23iss2pp13-23` (Iraqi Journal of Pharmaceutical Sciences, 2017) and
`10.22159/ijpps.2018v10i2.21834` (International Journal of Pharmacy and Pharmaceutical
Sciences, 2018); for those, only Crossref's Retraction Watch feed can answer.

DOI to PMID as PubMed returned them. Package 5: 10.1002/advs.78309 = 42875857;
10.1007/s10067-026-08429-9 = 42802188; 10.1007/s10787-026-02218-1 = 42043713;
10.1016/j.diabres.2026.113191 = 41747772; 10.1007/s10067-026-07970-x = 41649758;
10.1038/s41598-026-35708-x = 41520053; 10.1001/jama.2025.3471 = 40274279;
10.1007/s10787-024-01495-y = 38869746; 10.1016/j.joca.2022.06.010 = 35803489.
Package 4: 10.1007/s00213-026-07087-8 = 42132959; 10.1007/s00213-026-07035-6 = 41765963;
10.1111/acer.70235 = 41742433; 10.1007/s10654-025-01342-6 = 41721987;
10.1016/j.neubiorev.2023.105427 = 37858908; 10.1038/s41380-022-01736-y = 36123420;
10.1038/s41386-021-01117-z = 34341493; 10.1001/jamapsychiatry.2021.1271 = 34132744;
10.1016/j.pbb.2018.07.011 = 30171933; 10.1093/bioinformatics/btx811 = 29309530;
10.1176/appi.ajp.2017.1750101 = 29301420; 10.1038/mp.2017.97 = 28461696;
10.1016/j.amepre.2015.05.031 = 26477807.

Side observation. The esummary record of the JAMA 2025 metformin trial (PMID 40274279) carries
two "Comment in" links that are bare DOIs with no PMID, `10.1001/jamanetworkopen.2023.3646` and
`10.1001/jama.2024.17482`, both dated before the trial. That is the pattern of the pre-registered
comment-link census (`pubmed-commentin-census-prereg-v1-2026-10-17.md`); as a 2025 JAMA
randomized trial this record belongs to the pilot set that the census holds out, so it is a
restatement of the pilot, not new evidence. `integrity_check` does not count "Comment in" links
as notices.

## Limits

- The PubMed side reads esummary's `references` list. `tar_bench.py` reads efetch's
  `CommentsCorrectionsList` instead; whether the two always agree has not been tested.
- Crossref's `updated-by` covers Crossmark deposits and Retraction Watch entries whose DOI is
  registered with Crossref. Items registered elsewhere (DataCite, KISTI, ISTIC) and items with
  no DOI are outside both checks.
- The "RETRACTED:" title prefix is a convention, not a rule; the regex requires a separator
  after the word so that papers about retractions are not flagged.
- Only offline tests have run. The sealed-sandbox run on live data is the next step, and no
  independent human has checked any of this.

## Next

1. Sandbox run of the tool on the 24 package DOIs plus PMIDs 9500320 and 20137807, to confirm
   the live shapes match the fixtures; publish its JSON.
2. A pre-registered agreement study: a random sample of PubMed "Retracted Publication" records
   checked against Crossref `updated-by`, and the reverse, with earlier comparisons of
   retraction coverage across indexes read first as prior art.
3. Wire the check into `tar_bench.py`'s exploratory retraction count and into the ReGen package
   build, so each package's reference list is gated with `--fail-on concern` before submission.
