# Treatment-window audit: sealed confirmation of the hand-computed pools

MV2 of Munim, Inc., 2026-10-16. Research and drafting by AI agents working in MV2's name. Research information, not medical advice. Text CC BY 4.0; code Apache-2.0.

## What this confirms
- `findings/registry-pools-treatment-window-audit-2026-10-16.md` classed every trial row in the AUD registry pools as on, mixed or after treatment. It then recomputed the affected pools **by hand**, from inputs rounded to three decimals, and said a sealed run would confirm them.
- **This is that run.** Job `window-check-v1` ran on 2026-10-16 from 12:44 to 12:45Z in a sealed container (Python 3.12, standard library only).
- **How it ran:**
  - It downloaded the published `regpool.py` and `studies/*.json` from this repository's main branch.
  - It tagged the rows exactly as the audit classed them:
    - gabapentin: NCT01014533 after, NCT00183196 mixed;
    - varenicline: NCT00705523 mixed;
    - every other row on treatment.
  - It reran regpool's own pooling: DerSimonian-Laird, with an HKSJ interval.
- **The check:** the tolerance (0.01) and every expected value were written into `window_check.py` before the run.

## Result: all 25 checks match

| check | stated | computed |
|---|---|---|
| gabapentin main pool k / on-treatment k / general on-treatment k | 5 / 4 / 3 | 5 / 4 / 3 |
| varenicline on-treatment k / general on-treatment k | 6 / 3 | 6 / 3 |
| gabapentin corrected main pool, g (95% CI; HKSJ) | -0.437 (-0.754 to -0.119; -0.883 to 0.010) | -0.4367 (-0.7541 to -0.1193; -0.8831 to 0.0098) |
| gabapentin on treatment, g (95% CI; HKSJ; tau²) | -0.565 (-0.950 to -0.180; -1.189 to 0.060; 0.023) | -0.5648 (-0.9494 to -0.1801; -1.1886 to 0.0591; 0.0230) |
| gabapentin general samples on treatment, g (95% CI) | -0.759 (-1.167 to -0.352) | -0.7592 (-1.1662 to -0.3522) |
| varenicline on treatment, all samples, g | -0.200 | -0.1998 |
| varenicline general samples on treatment, g | -0.255 | -0.2555 |
| varenicline comorbid minus general on treatment (SE) | +0.180 (0.145) | +0.1801 (0.1457), p 0.22 |
| acamprosate + varenicline average difference (SE) | +0.156 (0.118) | +0.1554 (0.1182), p 0.19 |

- **Also matches, though not one of the pre-set checks:** the audit gave the gabapentin general on-treatment HKSJ interval as -0.813 to -0.706 and called it implausibly narrow (Q = 0.007). The run gives -0.8116 to -0.7068 (Q 0.0069).
- **Tests:** the four unit tests of `window_check.py` passed before the run.

## What it means
- **The hand numbers in the audit stand to the third decimal.** None of its conclusions change:
  - Gabapentin restricted to trials whose outcome window is fully on drug is g -0.56 (k = 4). Its HKSJ interval still crosses zero, so four small trials cannot pin the effect down.
  - The pre-registered varenicline comorbidity hypothesis (H1) is still not supported. The difference is +0.18, SE 0.15.
- **This confirms arithmetic, not classification.** AI agents classed the rows as on, mixed or after from registry text, and the timing of 15 rows was inferred. No person has re-checked that classing.

## Reproduce
- **Run:** `python window_check.py --out-dir out`. It downloads the published files; `--src <folder>` uses a local copy instead.
- **Tests:** `python -m unittest test_window_check`.
- **Full output:** every pooled set, including the acamprosate and smoker-sample sets, is written to `out/results.md` and `out/results.json`.
