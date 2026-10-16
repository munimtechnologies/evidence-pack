#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""spiro_followup: pre-registered robustness checks of the NHANES spironolactone
result (findings/spironolactone-nhanes-followup-prereg-2026-10-15.md).
Research information, not medical advice.

Rebuilds the pre-registration 3 sample with nhanes_spiro.py (unchanged), keeps
each participant's antihypertensive ingredients, and runs:
E1 randomization inference (label shuffled within cycle x n_other strata),
E2 restriction to regimens of 3+ antihypertensive ingredients,
E3 other drug groups in place of spironolactone (negative controls NC1-NC3,
   alpha-1 blockers A1 reported separately),
E4 leave one cycle out, E5 leave one spironolactone user out.
"""
import argparse
import json
import os
import random

import nhanes_spiro as ns

GROUPS = {
    "NC1_central_vasodilator": {"CLONIDINE", "METHYLDOPA", "HYDRALAZINE", "MINOXIDIL"},
    "NC2_other_k_sparing": {"AMILORIDE", "TRIAMTERENE"},
    "NC3_loop": {"BUMETANIDE", "FUROSEMIDE", "TORSEMIDE"},
    "A1_alpha1_blockers": {"DOXAZOSIN", "PRAZOSIN", "TERAZOSIN"},
}
NEGATIVE_CONTROLS = ["NC1_central_vasodilator", "NC2_other_k_sparing", "NC3_loop"]
N_PERM = 2000
SEED = 20261015
PRIMARY_BETA = -0.3403546241095232  # spiro-nhanes-v1, primary_H1
MIN_EXPOSED = 20


def antihypertensive_sets(records):
    """records: (seqn, drug name) taken in the past month -> {seqn: set of
    antihypertensive ingredients other than spironolactone}."""
    out = {}
    for seqn, drug in records:
        out.setdefault(seqn, set()).update(set(ns.ingredients(drug)) & ns.ANTIHYPERTENSIVES)
    return out


def build(data_dir, log):
    """Same rows as nhanes_spiro.build, each with "ings" (sorted ingredient list)."""
    rows = []
    for label, year, legacy, pattern, wvar, years in ns.CYCLES:
        recs = {}
        for base in ns.FILES:
            name = pattern.format(base)
            urls = ["https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/%s/DataFiles/%s.xpt" % (year, name),
                    "https://wwwn.cdc.gov/Nchs/Nhanes/%s/%s.XPT" % (legacy, name)]
            recs[base] = ns.read_records(ns.fetch(urls, os.path.join(data_dir, name + ".xpt"), log))
        merged = {}
        for base in ["DEMO", "ALQ", "BPQ", "MCQ"]:
            for rec in recs[base]:
                s = ns.code(rec.get("SEQN"))
                if s is not None and (base == "DEMO" or s in merged):
                    merged.setdefault(s, {}).update(rec)
        taken = [(ns.code(r.get("SEQN")), r.get("RXDDRUG"), r.get("RXDDAYS"))
                 for r in recs["RXQ_RX"] if ns.code(r.get("RXDUSE")) == 1]
        rx = ns.summarize_rx(taken)
        sets = antihypertensive_sets((s, d) for s, d, _ in taken)
        for s, raw in merged.items():
            row = ns.analysis_row(raw, rx.get(s))
            if row is None:
                continue
            w = raw.get(wvar)
            if ns.code(w) is None or float(w) <= 0:
                continue
            row.update({"seqn": s, "cycle": label, "w": float(w) * years / ns.TOTAL_YEARS,
                        "cluster": "%s|%s|%s" % (label, ns.code(raw.get("SDMVSTRA")), ns.code(raw.get("SDMVPSU"))),
                        "ings": sorted(sets.get(s, ()))})
            rows.append(row)
        log.append("%s: %d rows so far" % (label, len(rows)))
    return rows


def strata(rows):
    """Index lists of rows sharing (cycle, n_other)."""
    out = {}
    for i, r in enumerate(rows):
        out.setdefault((r["cycle"], r["n_other"]), []).append(i)
    return list(out.values())


def permute_labels(labels, groups, rng):
    new = list(labels)
    for idx in groups:
        vals = [labels[i] for i in idx]
        rng.shuffle(vals)
        for i, v in zip(idx, vals):
            new[i] = v
    return new


def wls_beta(X, y, w, j):
    import numpy as np
    sw = np.sqrt(w)
    coef = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    return float(coef[j])


def randomization_test(rows, cycles, n_perm=N_PERM, seed=SEED):
    import numpy as np
    X, names = ns.design(rows, cycles)
    X = np.array(X)
    j = names.index("spiro")
    y = np.array([float(r["y"]) for r in rows])
    w = np.array([r["w"] for r in rows])
    obs = wls_beta(X, y, w, j)
    labels = [r["spiro"] for r in rows]
    groups = strata(rows)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(n_perm):
        X[:, j] = np.array(permute_labels(labels, groups, rng), dtype=float)
        if abs(wls_beta(X, y, w, j)) >= abs(obs) - 1e-12:
            extreme += 1
    return {"beta": obs, "n_perm": n_perm, "seed": seed, "extreme": extreme,
            "p": (extreme + 1) / (n_perm + 1)}


def regimen_rows(rows, min_total=3):
    return [r for r in rows if r["n_other"] + r["spiro"] >= min_total]


def group_rows(rows, group):
    """Non-users of spironolactone, with "spiro" replaced by use of the drug
    group and n_other by the count of ingredients outside it."""
    out = []
    for r in rows:
        if r["spiro"]:
            continue
        ings = set(r["ings"])
        out.append(dict(r, spiro=int(bool(ings & group)), n_other=min(len(ings - group), 4)))
    return out


def specificity(results, spiro_beta=PRIMARY_BETA, min_exposed=MIN_EXPOSED):
    flagged = [k for k in NEGATIVE_CONTROLS
               if "error" not in results[k] and results[k]["n_spiro"] >= min_exposed
               and results[k]["beta"] <= spiro_beta and results[k]["ci_high"] < 0]
    return ("not specific to spironolactone" if flagged else "no evidence against specificity"), flagged


def fragile(refits):
    return any(r.get("decision") != "supported" for r in refits)


def overall(e1_p, e2_decision, flagged, is_fragile):
    if e1_p >= 0.05 or flagged:
        return "not robust"
    if e2_decision == "supported" and not is_fragile:
        return "robust"
    return "mixed"


def short(r):
    keep = ("n", "n_spiro", "clusters", "beta", "se", "ci_low", "ci_high", "p", "decision", "error")
    return {k: r[k] for k in keep if k in r}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)
    log = []
    rows = build(a.data_dir, log)
    cycles = [c[0] for c in ns.CYCLES]

    primary = ns.fit(rows, "y", cycles)
    check = {"n": len(rows), "n_spiro": sum(r["spiro"] for r in rows), "beta": primary["beta"],
             "reproduces_primary": abs(primary["beta"] - PRIMARY_BETA) < 1e-9,
             "n_other_mismatches": sum(1 for r in rows if min(len(r["ings"]), 4) != r["n_other"])}

    e1 = randomization_test(rows, cycles)
    e2 = ns.fit(regimen_rows(rows), "y", cycles)
    e3 = {}
    for k, g in GROUPS.items():
        e3[k] = ns.fit(group_rows(rows, g), "y", cycles)
    e4 = {}
    for c in cycles:
        e4[c] = ns.fit([r for r in rows if r["cycle"] != c], "y", [x for x in cycles if x != c])
    e5 = []
    for i, r in enumerate(rows):
        if r["spiro"]:
            res = ns.fit(rows[:i] + rows[i + 1:], "y", cycles)
            e5.append(dict(short(res), dropped_seqn=r["seqn"], dropped_cycle=r["cycle"]))

    spec, flagged = specificity(e3)
    is_fragile = fragile(list(e4.values()) + e5)
    verdict = overall(e1["p"], e2.get("decision"), flagged, is_fragile)
    e5_betas = [x["beta"] for x in e5 if "beta" in x]
    e5_summary = {"refits": len(e5), "beta_min": min(e5_betas), "beta_max": max(e5_betas),
                  "ci_high_max": max(x["ci_high"] for x in e5 if "ci_high" in x),
                  "not_supported": sum(1 for x in e5 if x.get("decision") != "supported")}

    res = {
        "check": check, "primary_H1": short(primary),
        "E1_randomization": e1, "E1_survives": e1["p"] < 0.05,
        "E2_regimen_3plus": short(e2), "E2_survives": e2.get("decision") == "supported",
        "E3_groups": {k: short(v) for k, v in e3.items()}, "E3_reading": spec, "E3_flagged": flagged,
        "E4_leave_cycle_out": {k: short(v) for k, v in e4.items()},
        "E5_summary": e5_summary, "E5_leave_user_out": e5,
        "fragile": is_fragile, "overall": verdict,
    }
    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)

    lines = ["# NHANES spironolactone follow-up (pre-registration 3b): results", "",
             "Plan: findings/spironolactone-nhanes-followup-prereg-2026-10-15.md", "",
             "- rebuild: %s" % json.dumps(check),
             "- primary H1: %s" % ns.fmt(primary), "",
             "## E1 randomization inference", "",
             "- beta %+.4f; %d of %d shuffles as extreme; p %.4f -> survives: %s"
             % (e1["beta"], e1["extreme"], e1["n_perm"], e1["p"], res["E1_survives"]), "",
             "## E2 regimens of 3+ ingredients", "",
             "- %s -> survives: %s" % (ns.fmt(e2), res["E2_survives"]), "",
             "## E3 drug groups in place of spironolactone (exposed count shown as 'spironolactone')", ""]
    lines += ["- %s: %s" % (k, ns.fmt(v)) for k, v in e3.items()]
    lines += ["", "E3 reading: **%s** %s" % (spec, flagged), "", "## E4 leave one cycle out", ""]
    lines += ["- without %s: %s" % (k, ns.fmt(v)) for k, v in e4.items()]
    lines += ["", "## E5 leave one spironolactone user out", "", "- %s" % json.dumps(e5_summary), "",
              "Fragile: %s" % is_fragile, "", "**Overall: %s**" % verdict, "", "## Log", ""]
    lines += ["- " + s for s in log]
    with open(os.path.join(a.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
