# Pre-registration 3b: is the NHANES spironolactone-drinking result specific and stable?

MV2 of Munim, Inc., 2026-10-15. Made with AI agents (Claude). Text CC BY 4.0; code Apache-2.0. Research information, not medical advice.

## Status and honesty note

This follow-up was written **after** the primary results of pre-registration 3 were seen (`findings/spironolactone-nhanes-results-2026-10-15.md`). What is fixed in advance is narrower: the checks, the drug groups and the reading rules below. All were written before any of these checks was run.

This plan could not be committed publicly before the checks ran: publishing was paused at the time. Proof that it came first is the timeline. The plan and code were written on 2026-10-15 at about 22:45Z, and the job's `summary.json` records when the checks started. This plan and the job's output will be published together.

The analysis code is `spiro_followup.py`. It reuses the unchanged `nhanes_spiro.py` and was written at the same time as this plan. Every check is reported whatever it shows. The primary result of pre-registration 3 stands as published and is not re-decided here.

## Data and population

Same NHANES files and the same eligibility rules as pre-registration 3. The rebuilt sample has to reproduce the primary β (−0.3404); if it does not, that is reported first.

## Checks

**E1. Randomization inference.**
- Within each stratum of cycle × number of other antihypertensive ingredients (capped at 4), shuffle the spironolactone label.
- Refit the primary weighted, adjusted model; repeat 2,000 times with seed 20261015.
- Two-sided p = (1 + number of |β_perm| ≥ |β_obs|) / 2,001.
- Why: cluster-robust errors can be too small when few clusters contain the exposure. In this sample the 70 users fall in at most 70 of 233 clusters.

**E2. Regimen restriction.**
- Keep only participants taking 3 or more distinct antihypertensive ingredients in total (spironolactone counts as one), as a proxy for resistant hypertension, the main reason spironolactone is used in hypertension.
- Same model and decision rule as H1.

**E3. Other drug groups in place of spironolactone.**
- Among non-users of spironolactone, the exposure becomes use of one drug group, against users of other antihypertensives.
- The adjustment counts the other antihypertensive ingredients outside that group. The model is otherwise the same as H1.
- Negative controls (no known effect on alcohol intake):
  - NC1, central agents and direct vasodilators, also used as add-ons in resistant hypertension: clonidine, methyldopa, hydralazine, minoxidil.
  - NC2, other potassium-sparing diuretics, which do not block the mineralocorticoid receptor: amiloride, triamterene.
  - NC3, loop diuretics, Loften 2026's closest comparator: furosemide, bumetanide, torsemide.
- Reported separately, and **not** a negative control: A1, alpha-1 blockers (doxazosin, prazosin, terazosin). They carry their own alcohol hypothesis (pre-registration 4).

**E4. Leave one cycle out.** Refit the primary model seven times, each time without one cycle.

**E5. Leave one user out.** Refit the primary model 70 times, each time without one spironolactone user. Report the range of β and how many refits change the decision.

## Reading rules (fixed now)

- **E1:** the result "survives randomization inference" if p < 0.05.
- **E2:** "survives the regimen restriction" if the upper 95% bound is below 0.
- **E3:** the association is "not specific to spironolactone" if any negative-control group with at least 20 exposed participants has β ≤ −0.34 and an upper 95% bound below 0. Otherwise: "no evidence against specificity". With these sample sizes that does not prove specificity.
- **E4/E5:** the result is "fragile" if any single cycle or any single user, once left out, turns the decision from supported to inconclusive.
- **Overall:**
  - "Robust": E1 survives, E2 survives, E3 shows no evidence against specificity, and E4/E5 are not fragile.
  - "Not robust": E1 fails or E3 says not specific.
  - "Mixed": anything in between.

In MV2's spironolactone evidence package, the NHANES analysis is described by this overall label.
