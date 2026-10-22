# Claim-provenance checker: how the H-A mutation job is built (run 156, 2026-10-22)

**Status note (rule i2): written 2026-10-22 ~07:50Z, after the code freeze (claimcheck 1.0.0, log entry 6) and before the mutation job has run. No mutations or labels exist.** These are readings of plan v5 sections 4.2-4.3 and v7 4.3, not plan amendments. MV2 of Munim, Inc. Written by AI agents (Claude, claude-opus-5-5) in MV2's name. No human has checked it. Text CC BY 4.0; the job code (`mutation-job/mutate.py`, `mutation-job/test_mutate.py`) is Apache-2.0.

## 1. Design questions settled before the job runs
- **Independence.** The job imports nothing from `claimcheck`. Its eligible sites are listed by hand in a site file, written from the plan's words while reading the hashed base texts. A grammar bug in the checker therefore cannot define both the sites and the catches. The cost is that the site list carries this author's own readings, and those can differ from the checker's. Every such difference shows up as a miss or a false positive, and it is reported.
- **Inputs.** Only the two base texts of record (log entry 5) are used, copied byte for byte into the job folder. The job re-hashes both, whole and cut, and stops before writing anything if any hash or cut length differs.
- **The site file stays unpublished,** because it quotes the unpublished base texts. The job prints its SHA-256, which goes into the log, and the file is published with the base texts once the evaluation is scored.
- **Outputs.** The mutated copies, the two unmutated cut texts (`P4-cut.md`, `P5-cut.md`, for the 6.1 "0 scored flags" prediction), `labels.json` and its SHA-256, and a `manifest.json` holding only file names and hashes. The checker job gets the copies, the cut texts, the three plan files and `recheck.json`. It never gets `labels.json` or the site file.

## 2. Readings the job takes
- **M1, draw.** For each module, then each package, in a fixed order (modules R1, R1b, R2, R2b, R3, R4, R5, R5b, R6, R7, R8; packages P4, P5), the valid sites, sorted by id, are shuffled with one `random.Random(20261021)`. Each package takes up to 4. When one package has fewer, the other takes the rest (plan v4 section 4), and the total is capped at 8. A module with fewer than 8 valid sites has a shortfall.
- **M2, layout.** Mutation k of a module goes to copy k. On a collision, or when copy k already holds that module, the job redraws from the module's undrawn sites in the same package, in shuffled order. If none fits, the drawn site moves to the first other copy it fits, or to a new copy. **A collision never drops a mutation.** v5 defines a shortfall as too few eligible sites, not as a collision. Without this reading, the two registry blocks (P4 L160, P5 L163-L173), which hold every R2b and R5b site, would cap those modules at one mutation per copy. Every collision, redraw, move and new copy is logged in `labels.json`, and counted in the printed report.
- **M3, collision.** Two mutations collide when one's mutated line is the other's primary line or an expected evidence line, or when both carry the same group. The groups are the two registry blocks.
- **M4, expected evidence lines** come from the plan's module text, not from the code:
  - R1: the twin occurrence;
  - R1b deletion: the section heading and its value lines;
  - R2: the linked table's rows and governing heading;
  - R2b/R5b: the rest of the gated block;
  - R4-a: the start date's line;
  - R5: the reference entries involved;
  - R6 swap: the cited plan's reference entry;
  - R8 source: every E.6 line plus the lines naming the source outside E.6;
  - R8 weight: the other conversion.
- **M5, invalid sites.** A site whose line is outside the cut, in the reference list, a table header or separator row (v4 section 4), or whose find text does not occur exactly once on its line, is excluded and reported, never repaired.
- **M6, operators** are applied as single in-line substitutions, so no line is added or removed and line numbers stay those of the base texts. "Deletion" means removing the text from its line.
- **M7, frozen insertion lists.**
  - The acronyms are KESTREL, ORVANE, TALVIK and BRENTA. None of them appears in either base text, in `recheck.json` or in the checker's `ACRONYM_STOPLIST` (checked by search).
  - The inserted names are Okafor 2019, Lindqvist 2020 and Tanabe 2021. None of them appears in any `recheck.json` label (reading 57) or in either base text.
- **M8, the R2 and R7-a redraw rule (v7 4.3)** was applied by hand when choosing each replacement value. Every R2 endpoint was moved to a value found in no candidate column, and every R7-a count to a value equal to none of the readings that apply. The job does not re-check this, because doing so would mean re-implementing the checker's rules.

## 3. Valid sites listed, by module (hand counts; the job re-counts)
| Module | P4 | P5 | Operators | Planted if all valid | Shortfall |
|---|---|---|---|---|---|
| R1 | 8 | 10 | one digit of one twin-tuple member (9 twin groups) | 8 | 0 |
| R1b | 6 | 9 | 13 sign flips where -x is outside the CI; 2 sole-convention deletions | 8 | 0 |
| R2 | 5 | 0 | 4 range endpoints, 1 N-of-M (all P4 L45) | 5 | 3 |
| R2b | 3 | 4 | gated count changes; ID deletions | 7 | 1 |
| R3 | 1 | 3 | "no clear difference/benefit" to "no difference/benefit"; "point estimates favour" to "lower risk" | 4 | 4 |
| R4 | 4 | 7 | 9 anchor deletions, 2 duration changes | 8 | 0 |
| R5 | 10 | 11 | 12 only-citation removals, 5 ambiguous author-years, 4 acronym insertions | 8 | 0 |
| R5b | 3 | 7 | registry-ID strips | 8 | 0 |
| R6 | 5 | 4 | 8 token insertions; 1 "pre-registered" swap (P4 L154) | 8 | 0 |
| R7 | 2 | 6 | 5 R7-a count +1 (the v7 sites); 3 R7-b name insertions | 8 | 0 |
| R8 | 7 | 8 | 3 body-weight changes; 12 source deletions from E.6 | 8 | 0 |
| **Total** | 54 | 69 | | **80** | 8 |

- **R4 has no shortfall now.** v5 expected 7 R4 sites, counted on P5 v27. The v28 edits U1-U4 added four "as of 2026-10-20" anchors (P5 B, C, E.5b and H), and each one is a deletion site.
- **R3 and R2 shortfalls are as v5 and v7 predicted.**
- Some operators of different modules make the same kind of edit on different strings: R2b ID deletion and R5b ID strip; R2b count change and R7-a count +1. P1 and P2 credit a catch by any module (v5 6.0), and results also report catches by the labelled module.

## 4. Predicted consequences, recorded before any label exists
- **Two operators can't be matched under v5 6.0 as written.** 6.0 credits a catch only when a flag's primary or evidence lines include the mutated line, and for a deletion the mutated line is the line the text was deleted from.
  - **R5 citation removal:** the never-cited flag sits on the reference entry. With the citation gone, no flag line can be the body line it was removed from. Each drawn removal (12 of R5's 21 sites) is therefore a miss, and its flag a P3 false positive, **even when R5 fires correctly**.
  - **R1b convention deletion:** under coding reading 21, the R1b-b flag lists the section heading and its value lines, not the line the sentence was deleted from (P4 L85, P5 L214). The same holds.
  - **R5 is therefore likely to fail P2** on the draw alone: about half its 8 draws are expected to be citation removals. This is a defect of the frozen plan and is reported as one. Neither the plan, the sites nor the code is changed for it.
- **Secondary, descriptive (not a pass rule; fixed now):** results also report a catch when a flag of the labelled module has a primary or evidence line equal to the mutated line **or to one of that mutation's expected evidence lines** (section 2, M4). Only this secondary match can show whether R5 and R1b fired on these operators.
- **Readings that may cost catches,** from CODING-NOTES:
  - reading 32: R5b form (ii) has no negation exception;
  - reading 53: R6-b flags a sentence when any one of its cited plans was written after results. The P4 L154 swap cites reference 13, which lists both a before-results and an after-results plan, so under 53 it is expected to be caught (b-after);
  - reading 57: R7-b names. The P5 L228 sentence also names Jiang, Hatano, Haj Shehadeh and Chen S, which were checked by hand and may be absent from `recheck.json` labels. If so, the unmutated text flags there too, as a P3 false positive.

## 5. Order from here
1. The agent that works MV2's desktop copies both base files into the job folder (File Explorer, byte sizes compared), then switches the job on.
2. Mutation job `ha-mutate-v1` (network off, 1 CPU, 1 GB): unit tests on synthetic text, then the run. Log entry 7 gets the site-file and labels hashes, planted counts, shortfalls and layout events.
3. Checker job: claimcheck 1.0.0 fetched at tag v0.5.0, plus the baseline, on every copy and both cut texts (run steps without network).
4. Scoring under v5 6.0-6.1 and the section 4 secondary match, committed whatever it shows.
