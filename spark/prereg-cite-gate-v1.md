# Pre-registration: gating the citation prior (SPARK Task 1 sample bench, job spark-sample-eval-v3)

MV2 of Munim, Inc., 2026-10-16 ~08:40Z. Text CC BY 4.0. Research and drafting by AI agents working in MV2's name.

Written after reading spark-sample-eval-v2 (ordinary set) and the v1 readout (landmark set), and **before the 72 landmark questions were re-read this run**. The gates use only rules fixed before v1 (the `CUE` regex in spark_eval.py) or rules that don't look at the question text (score band, smaller weight).

## What triggered this
- Pre-registered rule (prereg-devset-ordinary-v1.md): if the citation prior costs >= 0.05 MRR@5 on ordinary papers, the final system must gate it, and the next bench tests the gated version on both sets.
- spark-sample-eval-v2 (2026-10-16 08:01Z, 12/12 tests): `fields+ptype+cite` minus `fields+ptype` = **-0.0718** MRR@5 on 26 ordinary papers (helped 0, hurt 4: od-03, od-04, od-11, od-24). The answers' citation counts were median 9 (IQR 2-15.75); the wrong top-1s that beat them had a median of 86.5 (54.5-222.5). The rule fires, so the prior is gated.
- On the 72 landmark questions (v1) the same prior added +0.20 (0.677 to 0.878).

## Variants (all with field weights 3,1,1,1,0.5 and review demotion 0.6; fixed now)
| name | rule |
|---|---|
| `fields+ptype` | no prior (reference) |
| `fields+ptype+cite` | beta 0.3, always (the v1/v2 variant) |
| `cite0.1` | beta 0.1, always |
| `cite|cue` | beta 0.3 only when the question matches `CUE` (first, original, landmark, seminal, introduc*, discover*, pioneer*, earliest, initial) |
| `cite|band0.8` | beta 0.3, but only for candidates whose BM25 score is at least 0.8 of the top score (the prior can only break near-ties) |
| `cite|cue+early+year` | `cite|cue` plus the v1 earliest-paper cue (gamma 0.2) and the named-year boost (delta 0.3) |

## Known before running (stated so it isn't mistaken for a finding)
- None of the 26 ordinary questions matches `CUE` (a unit test pins this). So on the ordinary set `cite|cue` equals `fields+ptype` (0.809) by construction. The test that matters for this gate is how much of the landmark gain it keeps.
- `cite|cue+early+year` can differ from 0.809 on the ordinary set only through the year boost: od-08 names its publication year (2001), and od-15 names an event year (2007, paper 2015), which the boost could get wrong.

## Decision rule (fixed now)
1. **Eligible:** a variant is eligible if its ordinary-set MRR@5 is at least `fields+ptype` minus 0.02.
2. **Choose:** the eligible variant with the highest **equal-weight mean** of the two sets' MRR@5 (each set counts half, whatever its size). Ties go to the simpler rule, in this order: `fields+ptype`, `cite0.1`, `cite|band0.8`, `cite|cue`, `cite|cue+early+year`.
3. `fields+ptype` is always eligible, so a choice always exists. If it wins, the bench says the prior is not worth keeping.
4. Also reported, not used to choose: per-set deltas against `fields+ptype`, per-question helped/hurt counts, and how many landmark questions match `CUE`.

## Honest limits
- n = 72 + 26. A difference under about 0.05 is not distinguishable from noise; it is reported as a direction.
- The equal weighting is a judgement call: the real 1,000-question mix of landmark vs ordinary answers is unknown. The organisers' one example (CRISPR 2012) is a landmark.
- Both dev sets were written by AI agents with the answer in view, so both are lexically easier than expert questions.
- iCite counts are re-fetched, so `fields+ptype+cite` on the ordinary set may move slightly from v2's 0.737. If any v2 number moves by more than 0.01, that is reported.
