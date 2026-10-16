# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""FAERS fall / syncope / orthostatic hypotension reporting odds ratios for
alpha-1 blockers and 5-ARIs in reports for patients aged 75+, vs tamsulosin.

Plan fixed before any counts were read: faers-alpha1-falls-plan.md.
Signal measure only: spontaneous reports give no incidence and no causality.
"""
import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.fda.gov/drug/event.json"
DRUGS = ["TERAZOSIN", "DOXAZOSIN", "ALFUZOSIN", "TAMSULOSIN", "FINASTERIDE", "DUTASTERIDE"]
EVENTS = ["FALL", "SYNCOPE", "ORTHOSTATIC HYPOTENSION"]
REFERENCE = "TAMSULOSIN"
AGE = "patient.patientonsetage:[75 TO 120] AND patient.patientonsetageunit:801"


def search_for(drug, event=None):
    q = 'patient.drug.openfda.generic_name:"%s" AND %s' % (drug, AGE)
    if event:
        q += ' AND patient.reaction.reactionmeddrapt.exact:"%s"' % event
    return q


def total(query):
    url = API + "?" + urllib.parse.urlencode({"search": query, "limit": 1}, safe=':[]')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                body = json.load(r)
            return body["meta"]["results"]["total"], body["meta"].get("last_updated")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # openFDA answers "no matches" with 404
                return 0, None
            time.sleep(2 ** attempt)
    raise RuntimeError("openFDA failed: " + url)


def ror(a, n1, c, n2):
    """Reporting odds ratio with Woolf 95% CI: a of n1 reports vs c of n2."""
    b, d = n1 - a, n2 - c
    est = (a / b) / (c / d)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return est, math.exp(math.log(est) - 1.96 * se), math.exp(math.log(est) + 1.96 * se)


def analyse(counts):
    """counts: {drug: {"N": n, event: k, ...}} -> rows of proportions and RORs vs REFERENCE."""
    ref = counts[REFERENCE]
    rows = []
    for drug in DRUGS:
        for event in EVENTS:
            row = {"drug": drug, "event": event, "reports": counts[drug][event],
                   "n": counts[drug]["N"], "pct": 100 * counts[drug][event] / counts[drug]["N"]}
            if drug != REFERENCE:
                row["ror"], row["lo"], row["hi"] = ror(counts[drug][event], counts[drug]["N"],
                                                       ref[event], ref["N"])
            rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=".")
    args = p.parse_args()
    counts, updated = {}, None
    for drug in DRUGS:
        n, updated = total(search_for(drug))
        counts[drug] = {"N": n}
        for event in EVENTS:
            counts[drug][event] = total(search_for(drug, event))[0]
    rows = analyse(counts)
    out = {"openfda_last_updated": updated, "counts": counts, "rows": rows}
    with open(args.out_dir.rstrip("/") + "/faers_alpha1.json", "w") as f:
        json.dump(out, f, indent=1)
    for r in rows:
        tail = "" if "ror" not in r else "  ROR %.2f (%.2f-%.2f)" % (r["ror"], r["lo"], r["hi"])
        print("%-11s %-24s %5d/%-6d %5.2f%%%s" % (r["drug"], r["event"], r["reports"], r["n"], r["pct"], tail))


if __name__ == "__main__":
    main()
