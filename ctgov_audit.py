#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""ctgov_audit: find summary statistics that cannot be true in the results
posted on ClinicalTrials.gov.

Checks that no real data can fail (allowing for the rounding of the posted
numbers), tier "impossible":
  inverted_interval        lower limit above upper limit (IQR, full range, CI)
  center_outside_interval  median outside its own IQR or range, mean outside
                           its full range, any estimate outside its own CI
  negative_dispersion      SD or SE below zero
  mean_outside_bounds      mean of a percent-of-days/time or proportion
                           measure above its ceiling, or below its floor by
                           more than any difference of two such values can be
  sd_above_width           SD of such a measure larger than the full width of
                           its bounds: impossible even if the posted numbers
                           are an unlabelled change score
  sd_above_max             SD larger than any data inside those bounds can
                           have (Bhatia-Davis: var <= (hi-mean)(mean-lo),
                           times n/(n-1) for the sample SD), in a measure with
                           no sign of being a change score
Same two checks against a score range stated in the outcome's own text,
tier "scale" (impossible if the parsed range is right; the parse can be wrong):
  scale_mean_outside, scale_sd_above_max
Tier "se_implied" (impossible if the posted SE is the SE of a plain mean of
the n values counted for that group):
  se_implies_sd_above_width  a posted SE of a mean whose SE * sqrt(n) is
                           larger than the full width of the measure's
                           bounds (percent-of-days/time, proportion or a
                           stated score range); usually an SD typed as an SE
Heuristics, tier "suspect", never called impossible:
  sd_scale_suspect         percent-unit mean of 10 or more with an SD of 1 or
                           less, the shape of a proportion-scale SD typed next
                           to a percent-scale mean
  mean_below_floor         bounded measure with a mean below its floor (most
                           often a change score whose title does not say so)
  sd_above_max_if_level    sd_above_max in a measure that looks like a change
                           score: its description or a class/category title
                           says "change" or "differ", or another mean in the
                           same measure is below the floor
  se_implied_cluster       se_implies_sd_above_width in a study whose posted
                           analyses mention clustering: a model SE that allows
                           for clusters can be far larger than SD/sqrt(n)

v0.3 (2026-10-15): the percent-of-days/time bound now needs the time word in
the unit, not the title ("Y-balance at Week 12", unit "% of limb length", was
a false positive in v0.2); negative means move to mean_below_floor; new
sd_above_width.
v0.4 (2026-10-15): new se_implies_sd_above_width, in its own tier so the
"impossible" counts stay comparable with v0.2 and v0.3.
v0.5 (2026-10-16): hand triage of the v0.4 census found 6 of 12 new
sd_above_max/mean_outside_bounds studies were not impossible: 4 unlabelled
change scores (NCT05785832 class "Change from Baseline"; NCT02365064 and
NCT04623086 descriptions "Change ..."; NCT03477838 a negative sibling mean),
a medication possession ratio that can pass 100% (NCT06033521) and a per-day
rate (NCT01687400). Change-score measures now go to sd_above_max_if_level;
rates, possession ratios and areas under the curve get no bounds.
v0.6 (2026-10-16): hand triage of the 23 v0.5 se_implied studies found 4 that
are not SDs typed as SEs: a community-randomised trial whose SEs come from a
model with clustering (NCT01881373, now se_implied_cluster), two per-item
ranges with total-score means far above them (NCT03674892 means 53-60 on
"0-10", NCT02405962 means 15-20 on "1-7"; the SE check now skips bounds the
measure's own means do not fit), and a normed "Average Range 85-115"
(NCT00085202) read as the scale limits ("average range" is no longer a scale).

Stdlib only. Reads the public ClinicalTrials.gov API v2.
"""
import argparse
import csv
import datetime
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

API = "https://clinicaltrials.gov/api/v2/studies"
FIELDS_FULL = ",".join([
    "protocolSection.identificationModule.nctId",
    "protocolSection.sponsorCollaboratorsModule.leadSponsor",
    "protocolSection.statusModule.resultsFirstPostDateStruct",
    "resultsSection.outcomeMeasuresModule",
])
FIELDS_MIN = "protocolSection.identificationModule.nctId,resultsSection.outcomeMeasuresModule"
UA = "MV2-Munim-ctgov-audit/0.6 (mv2@munimtech.com)"

CHANGE_WORDS = re.compile(
    r"chang|differ|reduc|increas|decreas|improv|relative|ratio|baseline|predict|normal|"
    r"inhibit|recover|target|control|reference|expect|ideal|maxim|growth|excess|"
    r"coefficient|variation|weight|dose|elevation|participant|patient|subject", re.I)
PERCENT = re.compile(r"percent|%|\bpct\b", re.I)
DAYTIME = re.compile(r"\b(days?|time|weeks?|nights?)\b", re.I)
PROPORTION = re.compile(r"\bproportion\b", re.I)
# v0.5: quantities that are not confined to [0, 100] or [0, 1] even when the unit says so
UNBOUNDED_TU = re.compile(r"\brates?\b|area under|\bauc\b|possession ratio", re.I)
UNBOUNDED_DESC = re.compile(r"(?i:possession ratio)|\bMPR\b")
CHANGE_TEXT = re.compile(r"chang|differ", re.I)
# v0.6: an analysis that allows for clusters (community, school or practice randomisation)
CLUSTER = re.compile(r"\bcluster(?:s|ed|ing)?\b(?!\s+headache)", re.I)

SCALE_UNIT = re.compile(r"score|scale|\bpoints?\b", re.I)
SCALE_TITLE_EXCLUDE = re.compile(CHANGE_WORDS.pattern + r"|t-score|z-score|percentile|\blog|area under|\bauc\b",
                                 re.I)
SCALE_DESC_EXCLUDE = re.compile(
    r"chang|differ|from baseline|\bitems?\b|\beach\b|subscale|sub-scale|domain|t-score|z-score|"
    r"percentile|standardi[sz]ed|norm|logit|area under|\bauc\b|average range", re.I)
NUM = r"([-+]?\d+(?:\.\d+)?)"
SEP = r"\s*(?:\([^()]{0,60}\)\s*)?(?:to|-|–|—)\s*"
LIMIT_WORD = r"\s+(?:possible\s+)?(?:total\s+)?(?:score|value)?\s*(?:is|of|=|:)?\s*"
RANGE_PATTERNS = [
    re.compile(r"\b(?:range[sd]?|ranging)\b[\s:=]*(?:(?:is|are|of|between|from)\s+)?"
               + NUM + SEP + NUM, re.I),
    re.compile(NUM + SEP + NUM + r"[\s-]*(?:[A-Za-z-]+\s+){0,3}(?:scale|vas)\b", re.I),
    re.compile(r"\bminimum" + LIMIT_WORD + NUM + r"[^.;]{0,60}?\bmaximum" + LIMIT_WORD + NUM, re.I),
    re.compile(r"\bmaximum" + LIMIT_WORD + NUM + r"[^.;]{0,60}?\bminimum" + LIMIT_WORD + NUM, re.I),
]


def num(s):
    """Posted value as float, or None for 'NA', blanks and text."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        v = float(s)
    else:
        try:
            v = float(str(s).strip().replace(",", ""))
        except ValueError:
            return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def half_unit(s):
    """Half a unit in the last decimal place of a posted number (rounding slack)."""
    t = str(s).strip().replace(",", "")
    if "e" in t.lower():
        v = num(t)
        return abs(v) * 1e-6 if v is not None else 0.0
    if "." in t:
        return 0.5 * 10 ** -len(t.split(".", 1)[1])
    return 0.5


def disp_kind(d):
    u = (d or "").upper()
    if "DEVIATION" in u:
        return "SD"
    if "ERROR" in u:
        return "SE"
    if "QUARTILE" in u:
        return "IQR"
    if "RANGE" in u:
        return "RANGE"
    if "CONFIDENCE" in u or u == "CI":
        return "CI"
    return ""


def param_kind(p):
    u = (p or "").upper().replace(" ", "_")
    if "MEDIAN" in u:
        return "MEDIAN"
    if "GEOMETRIC" in u:
        return "GEOMETRIC"
    if "LEAST" in u:
        return "LSMEAN"
    if "LOG" in u:
        return "LOGMEAN"
    if u in ("MEAN", "ARITHMETIC_MEAN"):
        return "MEAN"
    return u


def bounds_for(title, unit, desc=""):
    """(lo, hi, kind) for percent-of-days/time and proportion measures, else None.

    The time word must be in the unit itself: a title like "... at Week 12"
    says when it was measured, not what the percentage is of.
    """
    text = f"{title} {unit}"
    if CHANGE_WORDS.search(text):
        return None
    if UNBOUNDED_TU.search(text) or UNBOUNDED_DESC.search(desc or ""):
        return None
    if not DAYTIME.search(unit or ""):
        return None
    if PERCENT.search(unit or ""):
        return (0.0, 100.0, "percent")
    if PROPORTION.search(unit or ""):
        return (0.0, 1.0, "proportion")
    return None


def scale_bounds(title, unit, desc):
    """(lo, hi, 'scale') when the outcome's own text states exactly one score range."""
    if not SCALE_UNIT.search(unit or ""):
        return None
    if SCALE_TITLE_EXCLUDE.search(f"{title} {unit}"):
        return None
    if SCALE_DESC_EXCLUDE.search(desc or ""):
        return None
    text = f"{title} {desc} {unit}".replace("−", "-")
    found = set()
    for pat in RANGE_PATTERNS:
        for m in pat.finditer(text):
            a, b = sorted((float(m.group(1)), float(m.group(2))))
            if a < b:
                found.add((a, b))
    if len(found) != 1:
        return None
    lo, hi = found.pop()
    return (lo, hi, "scale")


def sd_max(mean, lo, hi, n):
    """Largest sample SD any n values inside [lo, hi] with this mean can have."""
    v = (hi - mean) * (mean - lo)
    if v <= 0:
        return 0.0
    base = math.sqrt(v)
    if n and n > 1:
        return base * math.sqrt(n / (n - 1))
    return base


def denom_counts(denoms):
    out = {}
    for d in denoms or []:
        for c in d.get("counts") or []:
            gid = c.get("groupId")
            v = num(c.get("value"))
            if v is not None and gid not in out:
                out[gid] = v
    return out


def measurements(om):
    """Yield (group_id, class_title, category_title, measurement, n)."""
    base_n = denom_counts(om.get("denoms"))
    for cls in om.get("classes") or []:
        cls_n = denom_counts(cls.get("denoms"))
        for cat in cls.get("categories") or []:
            for m in cat.get("measurements") or []:
                gid = m.get("groupId")
                yield gid, cls.get("title", ""), cat.get("title", ""), m, cls_n.get(gid, base_n.get(gid))


def looks_like_change(om, rows, bounds):
    """True when a bounded measure may hold change scores despite its unit."""
    if CHANGE_TEXT.search(om.get("description") or ""):
        return True
    if any(CHANGE_TEXT.search(f"{c or ''} {k or ''}") for _, c, k, _, _ in rows):
        return True
    if bounds:
        for _, _, _, m, _ in rows:
            v = num(m.get("value"))
            if v is not None and v < bounds[0] - half_unit(m.get("value")):
                return True
    return False


def means_fit(rows, bounds):
    """True when every posted mean could be a level or a change score inside these bounds.

    A mean above the ceiling, or below the floor by more than the width, says the
    bounds belong to something else (one item of a total score, say).
    """
    blo, bhi, _ = bounds
    for _, _, _, m, _ in rows:
        v = num(m.get("value"))
        if v is None:
            continue
        tv = half_unit(m.get("value"))
        if v > bhi + tv or v < blo - (bhi - blo) - tv:
            return False
    return True


def study_clustered(oms):
    """True when any posted analysis of the study mentions clusters or clustering."""
    for om in oms or []:
        for a in om.get("analyses") or []:
            if CLUSTER.search(json.dumps(a)):
                return True
    return False


def check_measure(om, nct="", stats=None, clustered=False):
    """Flags for one outcome measure."""
    stats = stats if stats is not None else Counter()
    flags = []
    title = om.get("title") or ""
    unit = om.get("unitOfMeasure") or ""
    desc = om.get("description") or ""
    pk = param_kind(om.get("paramType"))
    dk = disp_kind(om.get("dispersionType"))
    groups = {g.get("id"): g.get("title", "") for g in om.get("groups") or []}
    pct = bounds_for(title, unit, desc)
    scale = None if pct else scale_bounds(title, unit, desc)
    rows = list(measurements(om))
    changey = looks_like_change(om, rows, pct) if pct else False
    se_bounds = [b for b in (pct, scale) if b and means_fit(rows, b)]
    if dk == "SE" and len(se_bounds) < len([b for b in (pct, scale) if b]):
        stats["measures_se_bounds_misfit"] += 1
    for gid, ctitle, cattitle, m, n in rows:
        v_s = m.get("value")
        v = num(v_s)
        if v is None:
            continue
        stats["cells"] += 1
        sp_s = m.get("spread")
        sp = num(sp_s)
        lo_s, hi_s = m.get("lowerLimit"), m.get("upperLimit")
        lo, hi = num(lo_s), num(hi_s)

        def flag(check, tier, limit=None, ratio=None, blo=None, bhi=None):
            flags.append({
                "nct": nct, "check": check, "tier": tier,
                "outcome_type": om.get("type", ""), "title": title, "unit": unit,
                "param_type": om.get("paramType", ""), "dispersion_type": om.get("dispersionType", ""),
                "group": groups.get(gid) or gid or "", "class": ctitle or "", "category": cattitle or "",
                "n": "" if n is None else int(n), "value": v_s,
                "spread": "" if sp_s is None else sp_s,
                "lower": "" if lo_s is None else lo_s, "upper": "" if hi_s is None else hi_s,
                "bound_lo": "" if blo is None else blo, "bound_hi": "" if bhi is None else bhi,
                "limit": "" if limit is None else round(limit, 4),
                "ratio": "" if ratio is None else round(ratio, 3),
                "url": f"https://clinicaltrials.gov/study/{nct}?tab=results" if nct else "",
            })

        if dk in ("SD", "SE") and sp is not None:
            stats["cells_dispersion"] += 1
            if sp < 0:
                flag("negative_dispersion", "impossible")

        if dk in ("IQR", "RANGE", "CI"):
            tv = half_unit(v_s)
            if lo is not None and hi is not None:
                stats["cells_interval"] += 1
                if lo - hi > half_unit(lo_s) + half_unit(hi_s):
                    flag("inverted_interval", "impossible")
                    continue
            applies = (dk == "CI" or (dk == "IQR" and pk == "MEDIAN")
                       or (dk == "RANGE" and pk in ("MEDIAN", "MEAN", "GEOMETRIC")))
            if applies:
                stats["cells_center"] += 1
                if lo is not None and v < lo - (tv + half_unit(lo_s)):
                    flag("center_outside_interval", "impossible", limit=lo)
                elif hi is not None and v > hi + (tv + half_unit(hi_s)):
                    flag("center_outside_interval", "impossible", limit=hi)

        if pk == "MEAN" and dk == "SD" and sp is not None and sp >= 0:
            tv, ts = half_unit(v_s), half_unit(sp_s)
            for b, outside, above, tier in ((pct, "mean_outside_bounds", "sd_above_max", "impossible"),
                                            (scale, "scale_mean_outside", "scale_sd_above_max", "scale")):
                if not b:
                    continue
                blo, bhi, _ = b
                stats["cells_" + tier] += 1
                if v < blo - tv or v > bhi + tv:
                    if tier == "impossible" and blo - (bhi - blo) - tv <= v < blo - tv:
                        flag("mean_below_floor", "suspect", blo=blo, bhi=bhi)
                    else:
                        flag(outside, tier, blo=blo, bhi=bhi)
                    continue
                if n is None or n < 2:
                    continue
                if tier == "impossible":
                    wcap = (bhi - blo) * math.sqrt(n / (n - 1))
                    if sp - ts > wcap * (1 + 1e-9):
                        flag("sd_above_width", tier, limit=wcap, ratio=sp / wcap, blo=blo, bhi=bhi)
                        continue
                mid = (blo + bhi) / 2
                m_best = min(max(mid, v - tv), v + tv)
                cap = sd_max(m_best, blo, bhi, n)
                if sp - ts > cap * (1 + 1e-9):
                    ratio = sp / cap if cap > 0 else None
                    if tier == "impossible" and changey:
                        flag("sd_above_max_if_level", "suspect", limit=cap, ratio=ratio, blo=blo, bhi=bhi)
                    else:
                        flag(above, tier, limit=cap, ratio=ratio, blo=blo, bhi=bhi)
            if (PERCENT.search(unit) and abs(v) >= 10 and 0 < sp <= 1
                    and n is not None and n >= 10):
                stats["cells_suspect"] += 1
                flag("sd_scale_suspect", "suspect")

        if pk == "MEAN" and dk == "SE" and sp is not None and sp >= 0 and n is not None and n >= 2:
            for b in se_bounds:
                blo, bhi, _ = b
                stats["cells_se_implied"] += 1
                wcap = (bhi - blo) * math.sqrt(n / (n - 1))
                implied = max(0.0, sp - half_unit(sp_s)) * math.sqrt(n)
                if implied > wcap * (1 + 1e-9):
                    if clustered:
                        flag("se_implied_cluster", "suspect", limit=wcap, ratio=implied / wcap,
                             blo=blo, bhi=bhi)
                    else:
                        flag("se_implies_sd_above_width", "se_implied", limit=wcap, ratio=implied / wcap,
                             blo=blo, bhi=bhi)
    return flags


def fetch_json(url, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise
            last = e
        except Exception as e:  # network hiccups: retry with backoff
            last = e
        time.sleep(5 * (i + 1))
    raise last


def iter_studies(page_size=200, limit=0, meta=None, pause=0.3):
    meta = meta if meta is not None else {}
    fields = FIELDS_FULL
    token = None
    seen = 0
    while True:
        q = {"filter.advanced": "AREA[HasResults]true", "fields": fields,
             "pageSize": str(page_size), "format": "json"}
        if token:
            q["pageToken"] = token
        else:
            q["countTotal"] = "true"
        try:
            data = fetch_json(API + "?" + urllib.parse.urlencode(q))
        except urllib.error.HTTPError as e:
            if e.code == 400 and fields == FIELDS_FULL and not token:
                fields = FIELDS_MIN
                meta["fields_fallback"] = True
                continue
            raise
        if "totalCount" in data:
            meta["total_count"] = data["totalCount"]
        meta["fields"] = fields
        for s in data.get("studies", []):
            yield s
            seen += 1
            if limit and seen >= limit:
                return
        token = data.get("nextPageToken")
        if not token:
            return
        time.sleep(pause)


def iter_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def study_info(s):
    ps = s.get("protocolSection") or {}
    nct = (ps.get("identificationModule") or {}).get("nctId", "")
    sponsor = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    posted = ((ps.get("statusModule") or {}).get("resultsFirstPostDateStruct") or {}).get("date", "")
    oms = (((s.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}).get("outcomeMeasures")) or []
    return nct, sponsor.get("class", ""), sponsor.get("name", ""), posted[:4], oms


CSV_FIELDS = ["nct", "check", "tier", "outcome_type", "title", "unit", "param_type", "dispersion_type",
              "group", "class", "category", "n", "value", "spread", "lower", "upper",
              "bound_lo", "bound_hi", "limit", "ratio", "sponsor_class", "sponsor", "results_year", "url"]


def run(studies, out_dir, meta, max_raw=5000):
    os.makedirs(out_dir, exist_ok=True)
    raw_dir = os.path.join(out_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    stats = Counter()
    by_class = defaultdict(Counter)
    by_year = defaultdict(Counter)
    flags_all = []
    raw_saved = 0
    for s in studies:
        nct, sclass, sname, year, oms = study_info(s)
        stats["studies"] += 1
        by_class[sclass or "UNKNOWN"]["studies"] += 1
        by_year[year or "unknown"]["studies"] += 1
        clustered = study_clustered(oms)
        if clustered:
            stats["studies_clustered"] += 1
        sflags = []
        for om in oms:
            stats["measures"] += 1
            stats["param:" + (param_kind(om.get("paramType")) or "none")] += 1
            stats["disp:" + (disp_kind(om.get("dispersionType")) or "none")] += 1
            for f in check_measure(om, nct, stats, clustered):
                f.update({"sponsor_class": sclass, "sponsor": sname, "results_year": year})
                sflags.append(f)
        tiers = {f["tier"] for f in sflags}
        for t in tiers:
            by_class[sclass or "UNKNOWN"]["with_" + t] += 1
            by_year[year or "unknown"]["with_" + t] += 1
            stats["studies_with_" + t] += 1
        if sflags and raw_saved < max_raw:
            with open(os.path.join(raw_dir, f"{nct}.json"), "w", encoding="utf-8") as f:
                json.dump(oms, f, indent=1)
            raw_saved += 1
        flags_all.extend(sflags)
        if stats["studies"] % 5000 == 0:
            print(f"{stats['studies']} studies, {len(flags_all)} flags", flush=True)

    with open(os.path.join(out_dir, "flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in flags_all:
            w.writerow(row)

    per_check = {}
    for chk in sorted({f["check"] for f in flags_all}):
        rows = [f for f in flags_all if f["check"] == chk]
        per_check[chk] = {
            "tier": rows[0]["tier"],
            "cells": len(rows),
            "measures": len({(r["nct"], r["outcome_type"], r["title"]) for r in rows}),
            "studies": len({r["nct"] for r in rows}),
            "primary_outcome_studies": len({r["nct"] for r in rows if r["outcome_type"] == "PRIMARY"}),
        }
    tier_studies = {}
    for f in flags_all:
        tier_studies.setdefault(f["tier"], set()).add(f["nct"])
    summary = {
        "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "api": API, "meta": meta, "stats": dict(stats), "per_check": per_check,
        "by_sponsor_class": {k: dict(v) for k, v in sorted(by_class.items())},
        "by_results_year": {k: dict(v) for k, v in sorted(by_year.items())},
        "raw_saved": raw_saved,
        "studies_by_tier": {k: sorted(v) for k, v in sorted(tier_studies.items()) if k != "suspect"},
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)

    lines = ["# ClinicalTrials.gov impossible-statistics audit", "",
             f"Run {summary['run_at']}. Studies with posted results scanned: {stats['studies']} "
             f"(API total {meta.get('total_count', '?')}). Outcome measures: {stats['measures']}. "
             f"Numeric cells: {stats['cells']}.", "",
             "| check | tier | cells | measures | studies | studies (primary outcome) |",
             "|---|---|---|---|---|---|"]
    for chk, d in per_check.items():
        lines.append(f"| {chk} | {d['tier']} | {d['cells']} | {d['measures']} | {d['studies']} | "
                     f"{d['primary_outcome_studies']} |")
    lines += ["", "Cells checked: " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items())
                                               if k.startswith("cells")), ""]
    for chk in per_check:
        rows = [f for f in flags_all if f["check"] == chk]
        rows.sort(key=lambda r: -(r["ratio"] or 0) if r["ratio"] != "" else 0)
        lines += [f"## {chk} (first 60)", ""]
        for r in rows[:60]:
            lines.append(f"- {r['nct']} [{r['outcome_type']}] {r['title'][:90]} | unit {r['unit'][:40]} | "
                         f"{r['group'][:40]} | {r['class'][:30]} | {r['category'][:30]} n={r['n']} "
                         f"value={r['value']} spread={r['spread']} "
                         f"lo={r['lower']} hi={r['upper']} bounds={r['bound_lo']}-{r['bound_hi']} "
                         f"limit={r['limit']} ratio={r['ratio']} | {r['sponsor_class']} {r['results_year']}")
        lines.append("")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return summary, flags_all


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--input", help="JSON-lines file of studies instead of the live API")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--max-raw", type=int, default=5000)
    args = ap.parse_args(argv)
    meta = {}
    studies = iter_jsonl(args.input) if args.input else iter_studies(args.page_size, args.limit, meta)
    summary, _ = run(studies, args.out_dir, meta, args.max_raw)
    print(json.dumps(summary["per_check"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
