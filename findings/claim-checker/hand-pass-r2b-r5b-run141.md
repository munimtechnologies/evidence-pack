# Package 5 v26 E.2: registry-ID completeness by hand (R2b / R5b), run 141, 2026-10-21 ~06:15Z

Local working note. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it. Nothing here is published, queued or sent (hold posture). Option g of the run-140 playbook.

## Input
- Package: 20261020T232326Z-medicine/regen-package-5-metformin-knee-oa-v26.md, section E.2, "**Registered trials**" block (lines 163-173) and reference 39 (line 356).
- Live registry (one call, read-only): `clinicaltrials.gov/api/v2/studies?query.intr=metformin&query.cond=osteoarthritis&fields=NCTId,BriefTitle,OverallStatus,LastUpdatePostDate,InterventionName&pageSize=50&countTotal=true`, read 2026-10-21 ~06:10Z. **totalCount 11**, same as the package's "11 records".

## Result
| | Count |
|---|---|
| Records the package says the search returned (ClinicalTrials.gov) | 11 |
| Distinct NCT IDs printed in the block | 9 (NCT07065591, NCT05034029, NCT06096259, NCT06328426, NCT05638893, NCT06231758, NCT06126029, NCT06367283, NCT04767841) |
| Distinct NCT IDs in reference 39 | the same 9 |
| Records described without an ID | 2: "a topical iontophoresis trial" and "an ultrasound-therapy study" |
| Other-registry IDs in the block | 1 (ChiCTR2500107918; outside the ClinicalTrials.gov count) |

- The live 11 match the package's 11 one to one. The two unnamed records are **NCT07395895** ("Effect of Metformin Iontophoresis on Knee Osteoarthritis in Postmenopausal Women"; NOT_YET_RECRUITING; last update 2026-02-09) and **NCT07738692** ("Effects of Various Types of Ultrasound Therapy in Knee Osteoarthritis"; COMPLETED; last update 2026-07-31; the registry lists its intervention as "Metfomin", sic).
- No live record was updated after the package's 2026-10-20 read (the newest is NCT06096259, 2026-10-15). The trial landscape in E.2 is unchanged.
- **Finding:** the statement "11 records ..., all accounted for below" is true in count. But 2 of the 11 can't be checked from the package or its references, because neither carries an ID. This is a small identifiability gap (seed-set class J), not a factual error. No estimate or claim changes.

## Pending edit for the next package 5 version (v27; bundle it with real trims, like the package-4 i4 edit)
- E.2 line 173: "a topical iontophoresis trial and an ultrasound-therapy study" becomes "a topical iontophoresis trial (NCT07395895) and an ultrasound-therapy study (NCT07738692)".
- Reference 39: add NCT07395895 and NCT07738692 to the list of ClinicalTrials.gov records read.
- Cost is about +4 words. It goes with the first trim in the v26 notes (drop E.1a's approximate -0.34 clause, about -25).

## What this shows about the checker plan (v2, 20261021T042443Z-medicine)
1. **R5b as written misses this.** It checks that every *bullet or table row* naming a trial carries an ID. The bullet "Other registered trials" does carry IDs, so the two unnamed records pass. A bullet-level check can't see a trial described in a clause inside a bullet that already has other IDs.
2. **R2b as written gets the right flag with the wrong numbers.** It counts every registry pattern in the block: 10 distinct IDs (9 NCT + 1 ChiCTR) against "11", so it reports a gap of 1. The real gap is 2, partly hidden by a ChiCTR record that is outside the ClinicalTrials.gov count.
3. **Worse, R2b as written would false-positive on the corrected text.** After the edit above, the block holds 11 NCT + 1 ChiCTR = 12 IDs against "11". H-A uses the corrected packages as base texts, so this false flag would sit on an unmutated line in every H-A run and count against P3 (precision).
4. **Fix, before code freeze (dated amendment for plan v3; it comes from the development set, not a held-out set):**
   - **R2b registry scoping:** when the count sentence names a registry ("ClinicalTrials.gov", "ChiCTR", "ISRCTN", "ANZCTR", "EU CTR/CTIS", "DRKS", "IRCT", "jRCT"), count only that registry's ID pattern. "ICTRP" or no named registry means all patterns. The block runs from the count sentence to the next heading of the same or higher level. Report the stated count, the in-scope distinct IDs, and the out-of-scope IDs separately.
   - **R5b clause level:** inside a registry block, split each bullet on ";" and on list commas or "and", and treat each clause as an item. A clause with a trial-design noun ("trial", "study", "record") and no ID is flagged. A clause that only counts records ("The remaining three records are") is not an item.
   - **H-A operator added for R5b:** strip the ID from one clause in a bullet that keeps other IDs. This is the case found here.
   - Seed set: add **S82** (P5 v26 E.2; two of 11 search records described without IDs; class J; Input R (scoped R2b); v1 module R2b after the fix, not as written in v2). Development row only. Headline counts stay on the 79 rows (82-row figures: R 38, S 8, X 36).
5. This is the concrete worked example the plan asked for. It also shows why the rules must be written down before code: the as-written R2b would have looked fine on a mutated text and failed quietly on the clean one.
