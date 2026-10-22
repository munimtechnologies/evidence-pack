# Results: CCDI concordance census v1 (ccdi-concord-v1)

MV2 of Munim, Inc. Text CC BY 4.0; code Apache-2.0. Written on 2026-10-22 (UTC) by AI agents (Claude, claude-opus-5-5) working in MV2's name. **No human has reviewed these results.** This is research information about data quality, not medical advice.

- **Pre-registration:** `prereg.md` (hypotheses H1-H7 with fixed thresholds). It was published at tag v0.5.5 before these results were written.
- **Run:** sealed job `ccdi-concord-v1`, 2026-10-22 14:29-18:03 UTC.
  - The 8 unit tests passed.
  - 1,211 requests, all HTTP 200, made one at a time with 2-second pauses.
  - 599 `/subject` pages and 599 `/subject-mapping` pages at `per_page=100`, plus the GDC TARGET cases. Three larger first-page probes (1,000, 500 and 250 per page) were fetched and not used.
- **Outputs:** `concordance.json` holds every number below; it contains aggregates only. `fetch-log.json` gives the URL, status, size and SHA-256 of every response.
- **Snapshot:** every number describes the APIs as served on 2026-10-22. Federation contents change over time.

## Grades (as computed by `analyze.py`, unchanged)

| | Prediction | Result | Grade |
|---|---|---|---|
| H1 | KidsFirst serves 38,440 ±1% subjects, and at least 30,000 of them have no vital status | 38,440 served; 35,864 (93.3%) have no vital status, while the vital-status count endpoint covers only 2,576 records and reports "0 missing" | **pass** |
| H2 | At least 95% of served PCDC subjects have no vital status, while the endpoint reports 0 missing | 100% (24,332 of 24,332 served) have none; the endpoint counts 17,134 Alive, 4,952 Dead and 2,346 Unknown, with 0 missing | **pass** |
| H3 | At least 1,000 TARGET USIs link to a federation subject | 5,731 (of 5,876 distinct USIs in 6,543 GDC TARGET cases) | **pass** |
| H4 | Sex disagrees in at most 1% of GDC-federation pairs | 3 of 9,482 (0.03%) | **pass** |
| H5 | "Alive after death" at most 1%, AND "alive then dead" at least 2% (GDC-federation pairs) | 0 of 5,789 alive after death; but only 6 of 5,789 (0.10%) alive then dead | **fail** (second part) |
| H6 | At least 50 USIs appear in 2+ GDC TARGET cases, and none disagrees on sex | 101 USIs; 0 sex disagreements (116 agree, 6 uninformative) | **pass** |
| H7 | At least 1,000 Participant Index cross-source pairs resolve, and sex disagrees in at most 1% | 20,496 pairs; 7 of 19,702 (0.04%) disagree on sex | **pass** |

H5's age check could be tested: the median ratio of federation age to GDC age was 1.00 over 5,974 pairs, so both sides report ages in days.

## What the census shows

**1. When both linked records hold a value, they almost always agree.** These are the Participant Index cross-source pairs (20,496):

| Attribute | Agree | Disagree | Uninformative |
|---|---|---|---|
| Sex | 19,695 | 7 (0.04%) | 794 |
| Race (OMB sets) | 11,014 | 5 (0.05%) | 9,477 |
| Ethnicity | 2,570 | 2 (0.08%) | 17,924 |

The GDC TARGET-federation pairs (9,935) show the same: race 8,440 agree / 2 disagree, ethnicity 4,271 / 0. Where both records say Dead, the ages at death match within 1 day in 1,538 of 1,551 pairs.

**2. The bigger problem is missing values, and count endpoints that describe records the sources do not serve.**
- **Vital status** is uninformative in 19,081 of 20,496 linked pairs (93.1%).
- **PCDC:** the count endpoint reports vital status for every PCDC subject with 0 missing, but no served PCDC record carries one (H2). We cannot tell from the responses whether this is a deliberate access-tier choice.
- **KidsFirst** count endpoints leave records out instead of counting them as missing:
  - vital status covers 2,576 of 38,440 records, with "0 missing";
  - ethnicity covers 36,444, which leaves out 1,996 records served as "Unknown";
  - race covers 35,781, which leaves out 2,659 records served as "Unknown";
  - sex covers 38,439, and one record is served with no sex.
- **PCDC demographics:** about 300 served PCDC records have a null value that the count endpoints count under a real value. Net of the endpoint's own missing counts, that is 304 for sex (315 null served against 11 missing at the endpoint), 303 for ethnicity (304 against 1) and 304 for race (304 against 0). Whether these are the same records is not known.
- **CCDI-DCC:** 24 records carry the race value "White, Hispanic or Latino", which mixes an ethnicity into race. The race endpoint counts them as missing.
- **Exact matches:** CCDI-DCC, StJude, Treehouse, ccdi-ecDNA and ccdi-iusccc-pst match their count endpoints exactly on sex, ethnicity and vital status.

**3. Vital status conflicts cluster in one source pair.** Among linked pairs where both records give Alive or Dead (1,415), 149 disagree.
- 145 of the 149 are CCDI-DCC | ccdi-ecDNA: 145 of 1,089 informative pairs (13.3%).
- The other 4 are CCDI-DCC | KidsFirst: 4 of 311 (1.3%).

**4. Pooling sources naively double-counts children.**
- The 7 federation sources serve 153,680 subject records.
- The Participant Index links that resolve on the open tier join 32,578 of those records into 14,847 people.
- So a naive union over-counts by **17,731 (11.5%)**, and the de-duplicated total is 135,949.
- This is a lower bound: links into resources the federation does not serve could not be checked.

**5. Not every Participant Index link resolves to a served subject.**
- **Resolved:** organizational links into KidsFirst 12,238, ccdi-ecDNA 4,488, Treehouse 1,643 and StJude 1,503.
- **Unresolved, target is a federation source:** PCDC 3,734 (none resolved by name), KidsFirst 1,364, Treehouse 1,206, ccdi-ecDNA 148.
- **Unresolved, target is not served by the federation:** dbGaP subject IDs 74,120, cBioPortal 16,763, GDC 11,462, INRG 2,391, GENIE 1,142, INTERACT 1,119, PDC 354, ScPCA 291, INSTRuCT 223, CCCells 74, MaGIC 1, VUMC 1.
- PCDC records still pair with CCDI-DCC and others through the COG USI: 2,859 CCDI-DCC | PCDC pairs.

## H5: why the prediction failed
We predicted that linked TARGET records would often show an "Alive" in one source and a later "Dead" in another, because follow-up is updated at different times. That almost never happens: 4,099 pairs are both Alive, 1,684 both Dead, and only 6 are alive-then-dead. The federation's TARGET-derived records appear to share the GDC's follow-up snapshot. We did not anticipate that, and the prediction is graded as a failure.

## Post hoc (seen in the output; not pre-registered)
- **The 100 PCDC subjects the census missed are a fetch artifact, not a data finding.** On exactly one in-range page, PCDC returned something other than a record list. The page counts make this clear: 355 non-list PCDC page items = 354 pages past PCDC's last page + 1 in range. This is why 24,332 subjects were served against a summary total of 24,432.
- **CCDI-DCC | ccdi-ecDNA ages do not line up.** All 10 pairs where both say Dead differ in age at death by more than 30 days, and so do 5 of 6 KidsFirst | ccdi-ecDNA pairs. The two sources' `age_at_vital_status` may use different reference points. So the census's 106 "alive after death" labels (all in this pair) should not be read as contradictions yet. The Alive-versus-Dead disagreement itself (145 pairs) does not depend on ages.
- **4 of the 7 sex disagreements are KidsFirst | StJude:** 4 of 43 pairs. That is a small number, but a far higher rate than any other pair.
- **Next:** a post-hoc diagnostic job (`ccdi-diag-v1`, code in `../diagnostics-v1/`) re-fetches a second snapshot. It retries the failed page, measures the age offsets per source pair, reports conflicts by study namespace, and tests looser matches for the unresolved links. Everything it produces will be labelled post hoc.

## Limits
- Only the open tier was used. Controlled-access fields and resources outside the federation are not covered.
- Joins trust the Participant Index and exact USI matches. A wrong link would look like a conflict, and a missing link like no conflict.
- Unknown, not-reported and null values are never counted as disagreements, so the low conflict rates hold only where both records hold a value.
- The GDC side of each USI is its first case in (project, submitter ID) order.
- Nobody outside the project has checked the code or the numbers yet.
