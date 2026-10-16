# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Internal-consistency re-check of published terazosin / dementia numbers.

1. Zhang Q ... Narayanan NS, Alzheimers Res Ther 2026 (PMID 42426853, PMC13644072),
   MarketScan new-user cohort: the text gives cases and person-years per group.
   Crude rate ratios and Poisson log-SEs from those counts are compared with the
   printed HRs, t statistics and CIs.
2. Tae BS ... Bae JH, J Urol 2019 (PMID 30840545): terazosin vs tamsulosin
   HR 1.112 (1.052-1.196); the CI is not centred on the HR on the log scale.

Rate ratios only approximate Cox HRs. They are used here because, for the one
contrast where both are printed (crude TZ/DZ/AZ vs tamsulosin), they agree
(0.698 vs 0.69). Standard library only.
"""
import json
import math

Z = 1.959964

# (cases, person-years), copied from the Results text of PMC13644072.
CRUDE = {"tz": (7054, 594862), "tam": (46915, 2761034), "ari": (4586, 352377)}
WEIGHTED = {"tz": (7200, 533753), "tam": (47228, 2870393), "ari": (4887, 322522)}

# Printed lines: (HR, lo, hi, t).
PRINTED = {
    "crude tz vs tam": (0.69, 0.67, 0.71, -29.4),
    "crude tz vs ari": (0.77, 0.74, 0.88, -18.2),
    "weighted tz vs tam": (0.84, 0.84, 0.84, -867.9),
    "weighted ari vs tam": (0.93, 0.93, 0.93, -385.5),
}

TAE = (1.112, 1.052, 1.196)


def rate(cases, py):
    return 1000.0 * cases / py


def ratio(groups, a, b):
    (ca, pa), (cb, pb) = groups[a], groups[b]
    rr = (ca / pa) / (cb / pb)
    se = math.sqrt(1.0 / ca + 1.0 / cb)
    return {"rr": rr, "se": se, "t": math.log(rr) / se}


def implied_se(hr, t):
    return abs(math.log(hr) / t)


def ci_midpoint(lo, hi):
    return math.exp((math.log(lo) + math.log(hi)) / 2)


def symmetric_partners(hr, lo, hi):
    """The upper limit that would make lo symmetric, and the lower limit for hi."""
    m = math.log(hr)
    return {"hi_if_lo_right": math.exp(2 * m - math.log(lo)),
            "lo_if_hi_right": math.exp(2 * m - math.log(hi))}


def run():
    out = {"crude_rates_per_1000": {k: rate(*v) for k, v in CRUDE.items()},
           "weighted_rates_per_1000": {k: rate(*v) for k, v in WEIGHTED.items()}}
    out["crude"] = {"tz vs tam": ratio(CRUDE, "tz", "tam"),
                    "tz vs ari": ratio(CRUDE, "tz", "ari"),
                    "ari vs tam": ratio(CRUDE, "ari", "tam")}
    out["weighted"] = {"tz vs tam": ratio(WEIGHTED, "tz", "tam"),
                       "tz vs ari": ratio(WEIGHTED, "tz", "ari"),
                       "ari vs tam": ratio(WEIGHTED, "ari", "tam")}
    out["printed_implied_se"] = {k: implied_se(v[0], v[3]) for k, v in PRINTED.items()}
    out["printed_ci_midpoint"] = {k: ci_midpoint(v[1], v[2]) for k, v in PRINTED.items()}

    # Weighted TZ/DZ/AZ vs 5-ARI from the two printed HRs (same model, same
    # tamsulosin reference), with a count-based SE. Weighting inflates variance,
    # so this interval is a floor on the true width.
    hr_tz, hr_ari = PRINTED["weighted tz vs tam"][0], PRINTED["weighted ari vs tam"][0]
    d = math.log(hr_tz) - math.log(hr_ari)
    se = out["weighted"]["tz vs ari"]["se"]
    out["weighted_tz_vs_ari_from_printed"] = {
        "hr": math.exp(d), "lo": math.exp(d - Z * se), "hi": math.exp(d + Z * se)}

    # How much narrower the printed weighted SEs are than count-based ones.
    out["weighted_se_shrink"] = {
        "tz vs tam": out["weighted"]["tz vs tam"]["se"] / out["printed_implied_se"]["weighted tz vs tam"],
        "ari vs tam": out["weighted"]["ari vs tam"]["se"] / out["printed_implied_se"]["weighted ari vs tam"]}
    s = out["weighted"]["tz vs tam"]["se"]
    out["weighted_tz_vs_tam_count_ci"] = {"lo": hr_tz * math.exp(-Z * s), "hi": hr_tz * math.exp(Z * s)}

    out["tae_2019"] = {"midpoint": ci_midpoint(TAE[1], TAE[2]), **symmetric_partners(*TAE)}
    return out


if __name__ == "__main__":
    import sys
    res = run()
    text = json.dumps(res, indent=1)
    print(text)
    if len(sys.argv) > 2 and sys.argv[1] == "--out":
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
