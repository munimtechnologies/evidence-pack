# Pre-registration 2, results: the comorbid-sample split in AUD drug trials, tested on acamprosate, baclofen and varenicline (2026-10-15)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Text CC BY 4.0, code Apache-2.0. Research information, not medical advice: it says nothing about what any person should take.

**Status: preliminary.** The numbers below were computed by hand from the ClinicalTrials.gov records. A sealed job (`registry-pool-v3`) recomputes them with `regpool.py` and re-downloads every record to check what was transcribed. When it lands, its output replaces these numbers and this line goes.

## What was tested, and when it was fixed

The [pre-registration](aud-comorbidity-prereg-2-2026-10-15.md) was committed in [67bbe16](https://github.com/munimtechnologies/evidence-pack/commit/67bbe168011ad24afa52769bd28ed48eeaf37cf7) at 2026-10-15T00:29:58Z, from the search listings only. The outcome data of these trials were first read after 01:34Z the same day. Every trial kept the group the pre-registration gave it.

- **H1:** in each drug's trials, the effect in general AUD samples is larger (more negative g) than in samples selected for another condition as well.
- **Primary test:** the fixed-effect average, over the new drugs, of the difference g(comorbid) minus g(general). H1 is supported if that average is above 0 with p < 0.05. A drug with fewer than 2 usable trials in either group contributes no difference.

## Result

**H1 is not supported at the pre-registered threshold.** The average difference is **+0.16** (SE 0.12, 95% CI -0.07 to 0.39, p ≈ 0.18). It is positive for both drugs that could be tested, so the direction matches H1, but it is about a third of the size of the two anticonvulsant splits that prompted the test.

| drug | k general | g general | k comorbid | g comorbid | difference (comorbid minus general) | SE |
|---|---|---|---|---|---|---|
| acamprosate | 2 | -0.08 | 4 | +0.03 | +0.11 | 0.20 |
| baclofen | 1 | -0.13 | 1 | -0.21 | not tested (one trial per group) | |
| varenicline (comorbid = smokers) | 4 | -0.26 | 3 | -0.08 | +0.18 | 0.14 |
| **average of the tested drugs** | | | | | **+0.16** (p ≈ 0.18; Q ≈ 0.09 on 1 df) | 0.12 |

With the earlier lists (topiramate +0.47, gabapentin +0.55, both found after the data were seen; naltrexone -0.13, pre-registered), four of five drugs point the same way. Only naltrexone's and these two new tests were fixed in advance, though, and none of them reached significance.

**H2 (exploratory), "the split belongs to GABA/glutamate drugs":** not supported. Varenicline, a nicotinic partial agonist, shows a larger difference than acamprosate.

**Overall drug effects in these registry pools** (all trials, random effects): varenicline **g ≈ -0.20** (k = 7, 95% CI about -0.33 to -0.07); acamprosate **g ≈ -0.04** (k = 6, CI about -0.23 to 0.16); baclofen **g ≈ -0.18** (k = 2, CI about -0.41 to 0.05). The outcomes are mostly heavy-drinking measures. Acamprosate's evidence in the literature is mainly about keeping abstinence, which only one of these trials measured.

## Trials

g < 0 favours the drug. The rule was the posted heavy-drinking measure at end of treatment, then drinks per drinking day or per week, then drinking frequency or abstinence.

**Acamprosate** (11 records)
- General: NCT03818191 (% days abstinent, -0.06), NCT00381043 (% heavy drinking days, -0.11).
- Comorbid: NCT00466661 bipolar (-0.35), NCT00452543 depression on escitalopram (drinks per drinking day, 0.00), NCT00330174 anxiety or depression (% days drinking, +0.11), NCT00463346 schizophrenia (drinking days, +0.20).
- Dropped on reading: NCT00249379. Its control arm got no medication, not placebo, and it posted no control data ("funding ran out").

**Baclofen** (8 records)
- Used: NCT01980706 general (30 and 90 mg/day combined, -0.13), NCT01008280 veterans with hepatitis C (-0.21).
- Dropped on reading: NCT01002105 posts its only drinking outcome without any SD, SE or test. NCT01751386's only outcome is a 2-hour laboratory drinking session.

**Varenicline** (20 records)
- General: NCT01146613 (-0.30), NCT00705523 (-0.27), NCT01011907 (-0.66), NCT04167306 (varenicline arms against the bupropion-only and double-placebo arms, -0.20).
- Smokers: NCT01553136 (-0.06), NCT01347112 (-0.15), NCT02859142 (-0.07).
- Dropped on reading: NCT00695500 (3 weeks of treatment, lab outcome) and NCT00580645 (lab session on day 8).

## Judgement calls, all reported

1. **NCT01011907 was misclassified by the pre-registration.** Its listing reads like a general AUD pilot, but on reading it enrolled problem drinkers who smoke and want to quit. The pre-registration's own rule puts such trials with the smokers, yet it also forbids moving trials, so the main analysis keeps it general. Moved to the smokers' group, varenicline's difference falls to about +0.10 (general -0.24, smokers -0.14).
2. **Two posted values can be read two ways.** In each case the main analysis uses the reading that works *against* H1:
   - NCT00705523 posts medians with "SDs" of 0.18 and 0.31 heavy drinking days per week. That is implausibly tight, so they are read as SEs (g -0.27). Read as SDs, g would be -1.22.
   - NCT02859142 titles its values "change from baseline" without defining them. They are read as week-12 levels (g -0.07). Read as reductions, g would be +0.07.

   With both alternative readings, varenicline's difference is about +0.44 and the average about +0.27 (p ≈ 0.06): still short of the threshold.
3. **NCT00330174 posts SEs of 0.04 next to means of 34.9% and 31.9%.** That only makes sense as proportions, so it is read as 4.0 percentage points. Taken literally, g would be about 11.
4. NCT03818191 has no heavy-drinking or quantity outcome, so its percent days abstinent is used (more is better). NCT00452543 and NCT00463346 likewise fall back to drinks per drinking day and drinking days.

Items 2 and 3 are themselves findings for [ctgov-audit](https://github.com/munimtechnologies/ctgov-audit): a spread whose scale does not fit its mean (proportion against percent), and an "SD" attached to a median.

## What this means

- The large general-vs-comorbid gaps for topiramate and gabapentin have now failed or fallen short in all three tests fixed in advance (naltrexone -0.13; acamprosate +0.11 and varenicline +0.18, average +0.16, p ≈ 0.18). The most that survives is a small tendency for drugs to look weaker in samples selected for a second condition. That could be dilution, floor effects, or chance.
- So the ReGen evidence packages for topiramate and gabapentin may describe their registry-only effects as clearest in primary AUD samples. They must not claim a population effect that holds across drugs.
- Power was low, as the pre-registration said it would be: 2-4 usable trials per group, and baclofen untestable. A null here does not show that the populations respond alike.

## Reproduce

`python regpool.py studies/acamprosate_aud.json studies/varenicline_aud.json --out-dir out --compare general comorbid` in [evidence-pack](https://github.com/munimtechnologies/evidence-pack), with `studies/varenicline_aud_readings.json` for the alternative readings and `--compare general_alt comorbid_alt` on `studies/varenicline_aud.json` for item 1.
