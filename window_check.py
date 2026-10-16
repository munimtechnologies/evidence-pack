#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""window_check: sealed confirmation of the hand-computed numbers in
findings/gabapentin-aud-correction-2026-10-16.md and
findings/registry-pools-treatment-window-audit-2026-10-16.md.
Research information, not medical advice.

Downloads the published regpool.py and study lists from
munimtechnologies/evidence-pack, tags each row on / mixed / after treatment
as the audit classed it, and reruns regpool's own pooling. Rows "after"
treatment leave the main pool; "on" rows get the tag on_treatment, and
general-sample "on" rows also get general_on. Each result is compared with
the number stated by hand, within the tolerance stated here in advance.
"""
import argparse
import importlib.util
import json
import os
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/main/"
FILES = ["regpool.py", "studies/gabapentin_aud.json", "studies/varenicline_aud.json",
         "studies/acamprosate_aud.json"]

# The audit's classification (every row not listed is "on").
WINDOWS = {
    "gabapentin_aud": {"NCT01014533": "after", "NCT00183196": "mixed"},
    "varenicline_aud": {"NCT00705523": "mixed"},
    "acamprosate_aud": {},
}
TOL = 0.01  # hand numbers were computed from inputs rounded to three decimals

# (label, list, set or comparison, field, value stated by hand or by the earlier job)
EXPECTED = [
    ("gabapentin corrected main pool (job, 2026-10-14 leave-one-out)", "gabapentin_aud", "main", "g", -0.437),
    ("gabapentin corrected main pool, CI low", "gabapentin_aud", "main", "ci_lo", -0.754),
    ("gabapentin corrected main pool, CI high", "gabapentin_aud", "main", "ci_hi", -0.119),
    ("gabapentin corrected main pool, HKSJ low", "gabapentin_aud", "main", "hksj_lo", -0.883),
    ("gabapentin corrected main pool, HKSJ high", "gabapentin_aud", "main", "hksj_hi", 0.010),
    ("gabapentin on treatment (by hand)", "gabapentin_aud", "on_treatment", "g", -0.565),
    ("gabapentin on treatment, CI low", "gabapentin_aud", "on_treatment", "ci_lo", -0.950),
    ("gabapentin on treatment, CI high", "gabapentin_aud", "on_treatment", "ci_hi", -0.180),
    ("gabapentin on treatment, HKSJ low", "gabapentin_aud", "on_treatment", "hksj_lo", -1.189),
    ("gabapentin on treatment, HKSJ high", "gabapentin_aud", "on_treatment", "hksj_hi", 0.060),
    ("gabapentin on treatment, tau^2", "gabapentin_aud", "on_treatment", "tau2", 0.023),
    ("gabapentin general on treatment (by hand)", "gabapentin_aud", "general_on", "g", -0.759),
    ("gabapentin general on treatment, CI low", "gabapentin_aud", "general_on", "ci_lo", -1.167),
    ("gabapentin general on treatment, CI high", "gabapentin_aud", "general_on", "ci_hi", -0.352),
    ("varenicline on treatment, all samples (by hand)", "varenicline_aud", "on_treatment", "g", -0.200),
    ("varenicline general on treatment (by hand)", "varenicline_aud", "general_on", "g", -0.255),
    ("varenicline comorbid minus general_on (by hand)", "varenicline_aud", "diff", "diff", 0.180),
    ("varenicline comorbid minus general_on, SE", "varenicline_aud", "diff", "se", 0.145),
    ("two-drug average difference, acamprosate + varenicline (by hand)", "both", "compare", "mean", 0.156),
    ("two-drug average difference, SE", "both", "compare", "se", 0.118),
]
EXPECTED_K = {("gabapentin_aud", "main"): 5, ("gabapentin_aud", "on_treatment"): 4,
              ("gabapentin_aud", "general_on"): 3, ("varenicline_aud", "on_treatment"): 6,
              ("varenicline_aud", "general_on"): 3}


def fetch(dest):
    for name in FILES:
        path = os.path.join(dest, name)
        os.makedirs(os.path.dirname(path) or dest, exist_ok=True)
        req = urllib.request.Request(RAW + name, headers={"User-Agent": "MV2-Munim-window-check/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())


def load_regpool(path):
    spec = importlib.util.spec_from_file_location("regpool", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_windows(spec, windows):
    """Copy of a study list with window, on_treatment and general_on added.
    Rows "after" treatment become sensitivity_only."""
    out = json.loads(json.dumps(spec))
    for s in out["studies"]:
        w = windows.get(s["nct"], "on")
        s["window"] = w
        tags = list(s.get("tags", []))
        if w == "on":
            tags.append("on_treatment")
            if "general" in tags:
                tags.append("general_on")
        if w == "after":
            s["sensitivity_only"] = True
        s["tags"] = tags
    subsets = dict(out.get("subsets") or {})
    subsets["outcome window fully on treatment"] = "on_treatment"
    subsets["general AUD samples, on treatment"] = "general_on"
    out["subsets"] = subsets
    return out


def flat(r):
    d = {"k": r["k"], "g": r["g"], "ci_lo": r["ci"][0], "ci_hi": r["ci"][1], "tau2": r["tau2"],
         "I2": r["I2"], "Q": r["Q"]}
    if "hksj_ci" in r:
        d["hksj_lo"], d["hksj_hi"] = r["hksj_ci"]
    return d


def run(src, out_dir):
    rp = load_regpool(os.path.join(src, "regpool.py"))
    specs = {stem: apply_windows(rp.load(os.path.join(src, "studies", stem + ".json")), WINDOWS[stem])
             for stem in WINDOWS}
    got = {}
    for stem, spec in specs.items():
        _, sets, res, _ = rp.analyses(spec)
        for name, r in res.items():
            key = {"outcome window fully on treatment": "on_treatment",
                   "general AUD samples, on treatment": "general_on"}.get(name, name)
            got[(stem, key)] = flat(r)
            got[(stem, key)]["ids"] = sets[name]
        with open(os.path.join(out_dir, stem + "-windowed.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=1)
    d = rp.subgroup_difference(specs["varenicline_aud"], "general_on", "comorbid")
    got[("varenicline_aud", "diff")] = {"diff": d["diff"], "se": d["se"], "p": d["p"]}
    c = rp.compare([specs["acamprosate_aud"], specs["varenicline_aud"]], "general_on", "comorbid")
    got[("both", "compare")] = {"mean": c["mean"], "se": c["se"], "p": c["p"]}
    return got


def check(got):
    rows, ok = [], True
    for (stem, key), k in EXPECTED_K.items():
        g = got.get((stem, key), {}).get("k")
        good = g == k
        ok &= good
        rows.append((f"{stem} {key}: k", k, g, good))
    for label, stem, key, field, want in EXPECTED:
        v = got.get((stem, key), {}).get(field)
        good = v is not None and abs(v - want) <= TOL
        ok &= good
        rows.append((label, want, v, good))
    return ok, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--src", help="folder that already holds regpool.py and studies/ (skips the download)")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    src = args.src
    if not src:
        src = os.path.join(args.out_dir, "published")
        fetch(src)
    got = run(src, args.out_dir)
    ok, rows = check(got)
    lines = ["# Treatment-window confirmation (sealed run)", "",
             "Published regpool.py and study lists from munimtechnologies/evidence-pack (main), "
             "rows tagged as in findings/registry-pools-treatment-window-audit-2026-10-16.md. "
             f"Tolerance {TOL}. Research information, not medical advice.", "",
             "| check | stated | computed | match |", "|---|---|---|---|"]
    for label, want, v, good in rows:
        vs = "missing" if v is None else (str(v) if isinstance(v, int) else f"{v:.4f}")
        lines.append(f"| {label} | {want} | {vs} | {'yes' if good else 'NO'} |")
    lines += ["", f"**All match: {ok}**", "", "## Every pooled set", ""]
    for (stem, key), r in sorted(got.items()):
        lines.append(f"- {stem} / {key}: " + json.dumps({k: (round(v, 4) if isinstance(v, float) else v)
                                                        for k, v in r.items()}))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"all_match": ok, "checks": [{"check": l, "stated": w, "computed": v, "match": g}
                                               for l, w, v, g in rows],
                   "sets": {f"{s}/{k}": r for (s, k), r in got.items()}}, f, indent=1)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
