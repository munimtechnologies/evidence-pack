# On or after treatment? A check of every trial row in MV2's AUD registry pools (2026-10-16)

MV2 of Munim, Inc., with AI agents (Claude) working in his name. Research information, not medical advice. Text CC BY 4.0.

## Why

On 2026-10-16 we found that one trial in our gabapentin pool (NCT01014533) gave the drug for about 10 nights, while the drinking outcome we pooled was measured in the 12 weeks after the drug stopped ([correction](gabapentin-aud-correction-2026-10-16.md)). We had read "relapse to any drinking, 12 wk" as a 12-week treatment period without reading the arms. So we checked every other row the same way.

## Method

For each trial row in the seven study lists behind MV2's alcohol use disorder (AUD) registry pools (gabapentin, topiramate, naltrexone, acamprosate, baclofen, varenicline), we read the ClinicalTrials.gov API v2 record (`/api/v2/studies/<NCT>`) on 2026-10-16. From each record we took the arms' dosing schedule and duration, plus the description and time frame of the posted outcome we used. Each row was then classed as:

- **on**: the outcome window lies inside the dosing period, ending at or before the last dose;
- **after**: the window lies after the drug stopped;
- **mixed**: the window covers both.

Where the record does not state the dosing length, we used the trial's primary publication (PubMed abstract) and say so. This was done by AI agents reading the records, and no human has re-checked it yet. Every row gives its NCT number so anyone can check.

## Result

**49 rows: 46 on treatment, 2 mixed, 1 after treatment.**

| List | Rows | On | Mixed | After |
|---|---|---|---|---|
| Gabapentin (incl. 1 enacarbil sensitivity row) | 7 | 5 | 1 (NCT00183196) | 1 (NCT01014533, already corrected) |
| Topiramate (incl. 1 sensitivity row) | 10 | 10 | 0 | 0 |
| Naltrexone | 17 | 17 | 0 | 0 |
| Acamprosate | 6 | 6 | 0 | 0 |
| Baclofen | 2 | 2 | 0 | 0 |
| Varenicline | 7 | 6 | 1 (NCT00705523) | 0 |

### The two mixed rows

**NCT00183196 (Anton 2011, gabapentin added to naltrexone).** The record says: "naltrexone (50 mg/day) for 16-weeks plus gabapentin (up to 1200 mg/day in divided doses) for the first 6 weeks". The posted outcome we used, "Time to Relapse to Drinking", has the time frame "16 weeks". So 10 of its 16 weeks fall after gabapentin stopped, with only naltrexone continuing. The live gabapentin finding already noted that the paper reports its benefit over the 6 weeks gabapentin was given. It did not treat the row as partly off-drug.

**NCT00705523 (varenicline pilot, 40 participants).** The posted outcome "Rate of Heavy Drinking Days Per Week" has the time frame "12 weeks of treatment and one month follow-up". Only one value is posted per arm, so the on-drug part cannot be separated out.

### What changes in the published numbers

These were computed by hand from the per-trial g and SE that the sealed job printed (rounded to three decimals). The method is regpool.py's: DerSimonian-Laird with HKSJ. The next sealed run will confirm them.

**Gabapentin, outcome windows fully on treatment** (NCT00391716, NCT02349477, NCT01141049, NCT04052139): k = 4, **g = -0.565 (95% CI -0.950 to -0.180)**. The HKSJ interval is -1.189 to +0.060, tau² = 0.023 and I² = 15%. For comparison, the job's five-trial pool after the run-36 correction is g -0.437, and its HKSJ interval also crosses zero (-0.883 to +0.010). The point estimate grows once off-drug weeks are excluded, but four small trials cannot pin it down.

**Gabapentin, general AUD samples, on-treatment only** (NCT00391716, NCT02349477, NCT01141049): k = 3, g = -0.759 (95% CI -1.167 to -0.352), tau² = 0. The three trials agree almost exactly (Q = 0.007), which makes the HKSJ interval implausibly narrow (-0.813 to -0.706). This is a known quirk of HKSJ when the observed spread is smaller than chance. The DerSimonian-Laird interval is the one to read.

**Varenicline, pre-registration 2** ([results](aud-comorbidity-prereg-2-results-2026-10-15.md)). We dropped NCT00705523:
- The general-sample pool goes from -0.256 to -0.255 (k = 3, tau² = 0).
- The pre-registered difference goes from +0.181 to +0.180 (SE 0.145).
- The two-drug average goes from +0.156 to +0.156 (SE 0.118, p ≈ 0.19).
- Varenicline's overall estimate goes from -0.203 to -0.200 (k = 6).

The conclusion is unchanged: H1 is not supported. The row's "SD as SE" reading (judgement call 2 in that file) is a separate issue, and it stands as reported.

**Topiramate, naltrexone, acamprosate and baclofen:** no change.

### Rows classed "on" by inference

For these rows the record does not state the stop date, but the window matches the dosing period:
- **Topiramate:** NCT00167245, NCT03018704, NCT00550394. For NCT03176953 the record gives no dosing length; the primary paper (Norman et al., Am J Psychiatry 2025, PMID 40103353) says "16 weeks of treatment", which matches the week-16 outcome.
- **Naltrexone:** NCT00920829, NCT00302133, NCT00142818, NCT02330419, NCT01245647. For NCT01211769 the paper (Fogaça 2011, PMID 21787433) says "administered for 90 days". For NCT01227044 the paper (Edelman 2019, PMID 30073637) reports "≥ 5 injections" by 24 weeks, so week 12 is on treatment.
- **Acamprosate:** NCT00463346. NCT03818191's outcome says "3 month follow-up", but its other outcomes call the same window "during 3 months of treatment". For NCT00466661 the paper (Tolliver 2012, PMID 22329472) describes an 8-week trial.
- **Baclofen:** NCT01008280.

Four rows sit exactly at the end of dosing:
- NCT00006489 (week 24, "Posttreatment", 90-day recall);
- NCT01625091 ("month 4 when the drug is stopped");
- NCT01077310 (6 months after release; monthly injections for 6 months starting before release);
- NCT01932801 (week 12, three monthly injections).

### Registry inconsistencies seen along the way (for ctgov-audit)

- **NCT01146613:** varenicline is listed "for 12 weeks", placebo for "13 weeks", and the outcome runs "Weeks 2-13*". The paper (Litten 2013, PMID 23728065) says 2 mg/d "was maintained during weeks 2 to 13".
- **NCT00920829:** one placebo arm's text describes naltrexone dosing.
- **NCT00381043:** the arm says 333 mg t.i.d., the description says 666 mg t.i.d.
- **NCT00463346:** lists "1998 mg tid", which is the daily total.
- **NCT01008280:** says "11 visits" but lists nine weeks.
- **NCT03176953:** has no reference to its primary publication, and PubMed finds no record carrying the NCT number.

## Limits

- Classification relies on registry text. For 15 rows the timing is inferred, as listed above.
- "On treatment" here means inside the dosing window. Tapers are counted as on treatment: NCT01980706, NCT00862563 and NCT02371889 include or adjoin taper weeks.
- The hand-computed pools use rounded inputs, so expect differences in the third decimal.

## Rule

Every registry row now records its dosing schedule, the outcome time frame, and on / mixed / after. A pool's main analysis uses "on" rows. Mixed rows go to sensitivity analyses.
