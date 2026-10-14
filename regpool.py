#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""regpool: random-effects pooling of a drug vs control using only results
posted on ClinicalTrials.gov (registry results, so unpublished and terminated
trials count too). Research information, not medical advice.

Each trial gives one standardized mean difference on its posted outcome,
signed so that a negative value favours the drug:
  arms     (mean, SD, n) per arm, Hedges' g
  arms_se  (mean, SE, n) per arm; SD = SE * sqrt(n)
  arms2    two drug arms combined (Cochrane Handbook 6.5.2.10), then Hedges' g
  p        two-sided p and direction only (g from z * sqrt(1/n1 + 1/n2))
  binary   (events, n) per arm; log odds ratio * sqrt(3)/pi (Chinn 2000),
           "event": "good" (abstinent, no heavy drinking) or "bad" (relapse)
"higher_better": true flips continuous outcomes where more is better
(e.g. days to relapse). DerSimonian-Laird tau^2, plus the
Hartung-Knapp-Sidik-Jonkman interval and a prediction interval.

Study lists are JSON files (see studies/). --verify re-downloads each trial's
posted outcome measures so the transcribed numbers can be checked.
"""
import argparse
import json
import math
import os
import sys
import urllib.request
from statistics import NormalDist

T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
        10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
        18: 2.101, 19: 2.093, 20: 2.086}
LOGIT_TO_D = math.sqrt(3) / math.pi


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def combine_arms(a, b):
    """Cochrane Handbook 6.5.2.10: one arm from two (mean, SD, n)."""
    m1, s1, n1 = a
    m2, s2, n2 = b
    n = n1 + n2
    m = (n1 * m1 + n2 * m2) / n
    var = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2 + n1 * n2 / n * (m1 - m2) ** 2) / (n - 1)
    return m, math.sqrt(var), n


def hedges(t, c):
    m1, s1, n1 = t
    m2, s2, n2 = c
    sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    j = 1 - 3 / (4 * (n1 + n2) - 9)
    g = j * (m1 - m2) / sp
    return g, (n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2))


def log_odds_ratio(t, c):
    """(events, n) per arm -> (log OR, variance), 0.5 added to every cell if any is 0."""
    a, n1 = t
    b, n2 = c
    cells = [a, n1 - a, b, n2 - b]
    if min(cells) == 0:
        cells = [x + 0.5 for x in cells]
    a, a_no, b, b_no = cells
    return math.log((a * b_no) / (a_no * b)), sum(1 / x for x in cells)


def effect(s):
    k = s["kind"]
    if k == "binary":
        lor, v = log_odds_ratio(s["t"], s["c"])
        sign = -1 if s.get("event", "good") == "good" else 1
        return sign * lor * LOGIT_TO_D, v * LOGIT_TO_D ** 2
    if k == "arms":
        g, v = hedges(s["t"], s["c"])
    elif k == "arms_se":
        t = (s["t"][0], s["t"][1] * math.sqrt(s["t"][2]), s["t"][2])
        c = (s["c"][0], s["c"][1] * math.sqrt(s["c"][2]), s["c"][2])
        g, v = hedges(t, c)
    elif k == "arms2":
        g, v = hedges(combine_arms(s["t"], s["t2"]), s["c"])
    elif k == "p":
        n1, n2 = s["n"]
        z = NormalDist().inv_cdf(1 - s["p"] / 2)
        d = s["direction"] * z * math.sqrt(1 / n1 + 1 / n2)
        g = (1 - 3 / (4 * (n1 + n2) - 9)) * d
        v = (n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2))
    else:
        raise ValueError(k)
    return (-g if s.get("higher_better") else g), v


def arm_sizes(s):
    k = s["kind"]
    if k == "p":
        return tuple(s["n"])
    if k == "binary":
        return s["t"][1], s["c"][1]
    if k == "arms2":
        return s["t"][2] + s["t2"][2], s["c"][2]
    return s["t"][2], s["c"][2]


def chi2_sf(x, df):
    """Upper tail of chi-square (series for the regularized lower gamma)."""
    if x <= 0:
        return 1.0
    a, y = df / 2, x / 2
    term = total = 1 / a
    n = 0
    while term > 1e-15 * total and n < 10000:
        n += 1
        term *= y / (a + n)
        total += term
    lower = math.exp(-y + a * math.log(y) - math.lgamma(a)) * total
    return max(0.0, 1 - lower)


def pool(effects):
    """effects = [(g, var)] -> dict of DL random-effects results."""
    k = len(effects)
    w = [1 / v for _, v in effects]
    sw = sum(w)
    fixed = sum(wi * g for wi, (g, _) in zip(w, effects)) / sw
    q = sum(wi * (g - fixed) ** 2 for wi, (g, _) in zip(w, effects))
    c = sw - sum(wi ** 2 for wi in w) / sw
    tau2 = max(0.0, (q - (k - 1)) / c) if k > 1 else 0.0
    ws = [1 / (v + tau2) for _, v in effects]
    sws = sum(ws)
    mu = sum(wi * g for wi, (g, _) in zip(ws, effects)) / sws
    se = math.sqrt(1 / sws)
    z = mu / se
    out = {"k": k, "g": mu, "se": se, "ci": (mu - 1.959964 * se, mu + 1.959964 * se),
           "p": 2 * (1 - NormalDist().cdf(abs(z))), "tau2": tau2, "Q": q,
           "Q_p": chi2_sf(q, k - 1) if k > 1 else 1.0,
           "I2": max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0, "fixed": fixed}
    if k > 1:
        t = T975.get(k - 1, 2.0)
        qh = sum(wi * (g - mu) ** 2 for wi, (g, _) in zip(ws, effects)) / (k - 1)
        se_h = math.sqrt(qh / sws)
        out["hksj_ci"] = (mu - t * se_h, mu + t * se_h)
        if k > 2:
            tp = T975.get(k - 2, 2.0)
            half = tp * math.sqrt(tau2 + se ** 2)
            out["pi"] = (mu - half, mu + half)
    return out


def fmt(r):
    s = f"k={r['k']}: g = {r['g']:.3f} (95% CI {r['ci'][0]:.3f} to {r['ci'][1]:.3f}; p = {r['p']:.4f})"
    if "hksj_ci" in r:
        s += f"; HKSJ CI {r['hksj_ci'][0]:.3f} to {r['hksj_ci'][1]:.3f}"
    if "pi" in r:
        s += f"; prediction interval {r['pi'][0]:.3f} to {r['pi'][1]:.3f}"
    s += f"; tau^2 = {r['tau2']:.4f}, I^2 = {100 * r['I2']:.0f}%, Q = {r['Q']:.2f} (p = {r['Q_p']:.3f})"
    return s


def analyses(spec):
    """Main pool (trials not marked sensitivity_only), its tagged subsets,
    main plus sensitivity-only trials, and leave-one-out over the main pool."""
    studies = spec["studies"]
    eff = {s["nct"]: effect(s) for s in studies}
    main = [s["nct"] for s in studies if not s.get("sensitivity_only")]
    sets = {"main": main}
    for name, tag in (spec.get("subsets") or {}).items():
        sets[name] = [s["nct"] for s in studies if not s.get("sensitivity_only") and tag in s.get("tags", [])]
    if len(main) < len(studies):
        sets["main plus sensitivity-only trials"] = [s["nct"] for s in studies]
    res = {name: pool([eff[n] for n in ids]) for name, ids in sets.items() if ids}
    loo = {n: pool([eff[m] for m in main if m != n]) for n in main} if len(main) > 2 else {}
    return eff, sets, res, loo


def report(spec, eff, res, loo):
    lines = [f"# {spec['title']}", "", spec.get("intro", ""), "",
             "Research information, not medical advice. g < 0 favours the drug.", "",
             "| NCT | trial | posted outcome used | n (drug/control) | g | SE | note |",
             "|---|---|---|---|---|---|---|"]
    for s in spec["studies"]:
        g, v = eff[s["nct"]]
        n = arm_sizes(s)
        note = s.get("note", "")
        if s.get("sensitivity_only"):
            note = ("sensitivity only. " + note).strip()
        lines.append(f"| {s['nct']} | {s['label']} | {s['measure']} | {n[0]}/{n[1]} | {g:.3f} | "
                     f"{math.sqrt(v):.3f} | {note} |")
    lines += ["", "## Pooled (DerSimonian-Laird random effects)", ""]
    for name, r in res.items():
        lines.append(f"- {name}: {fmt(r)}")
    if loo:
        lines += ["", "## Leave one out (main pool)", ""]
        for n, r in loo.items():
            lines.append(f"- without {n}: {fmt(r)}")
    return "\n".join(lines) + "\n"


def verify(spec, out_dir):
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    lines = [f"# Registry check of transcribed inputs: {spec['title']}", ""]
    for s in spec["studies"]:
        url = (f"https://clinicaltrials.gov/api/v2/studies/{s['nct']}"
               "?fields=resultsSection.outcomeMeasuresModule&format=json")
        req = urllib.request.Request(url, headers={"User-Agent": "MV2-Munim-regpool/0.1 (munimversion2@gmail.com)"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
        except Exception as e:  # report and go on
            lines.append(f"- {s['nct']}: fetch failed: {e}")
            continue
        with open(os.path.join(out_dir, "raw", s["nct"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        oms = ((data.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
        hit = [om for om in oms if s["outcome"].lower() in (om.get("title") or "").lower()]
        lines.append(f"## {s['nct']} ({s['label']})")
        lines.append(f"transcribed: kind={s['kind']} t={s.get('t')} t2={s.get('t2')} c={s.get('c')} "
                     f"p={s.get('p')} n={s.get('n')} event={s.get('event')} higher_better={s.get('higher_better')}")
        if not hit:
            lines.append(f"NO MEASURE TITLED LIKE '{s['outcome']}'")
        for om in hit[:1]:
            groups = {g["id"]: g.get("title", "") for g in om.get("groups") or []}
            dn = {}
            for d in om.get("denoms") or []:
                for c in d.get("counts") or []:
                    dn.setdefault(c["groupId"], c.get("value"))
            lines.append(f"posted: {om.get('title')} | {om.get('paramType')} / {om.get('dispersionType')} | "
                         f"{om.get('unitOfMeasure')} | {om.get('timeFrame')}")
            for cls in om.get("classes") or []:
                for cat in cls.get("categories") or []:
                    for m in cat.get("measurements") or []:
                        lines.append(f"- {cls.get('title', '')} {cat.get('title', '')} {groups.get(m['groupId'])}: "
                                     f"n={dn.get(m['groupId'])} value={m.get('value')} spread={m.get('spread')} "
                                     f"lo={m.get('lowerLimit')} hi={m.get('upperLimit')}")
            for a in om.get("analyses") or []:
                lines.append(f"- analysis: p={a.get('pValue')} method={a.get('statisticalMethod')} "
                             f"estimate={a.get('paramValue')} ci={a.get('ciLowerLimit')}..{a.get('ciUpperLimit')}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("studies", nargs="+", help="study-list JSON files")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.studies:
        spec = load(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        eff, sets, res, loo = analyses(spec)
        text = report(spec, eff, res, loo)
        with open(os.path.join(args.out_dir, stem + ".md"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(args.out_dir, stem + ".json"), "w", encoding="utf-8") as f:
            json.dump({"effects": eff, "sets": sets, "results": res, "leave_one_out": loo}, f, indent=1)
        print(text)
        if args.verify:
            vdir = os.path.join(args.out_dir, stem + "-verify")
            text = verify(spec, vdir)
            with open(os.path.join(vdir, "verify.md"), "w", encoding="utf-8") as f:
                f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
