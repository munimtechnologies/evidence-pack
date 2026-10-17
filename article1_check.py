# article1_check.py - Do article-number-1 records outside Springer Nature (MDPI, Frontiers) draw misattributed citations?
# Pre-registration: findings/article-number-1-prereg-v1-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public Crossref, OpenCitations and OpenAlex APIs.
import argparse
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "mv2@munimtech.com"
UA = "mv2-article1-check/1.0 (MV2 of Munim, Inc.; mailto:%s)" % MAILTO
CR = "https://api.crossref.org/works/"
OC = "https://api.opencitations.net/index/v2/citations/doi:"
OA = "https://api.openalex.org/works"
SEED = 20261021
YEARS = range(2016, 2024)  # volume years 2016-2023
WAITS = (5, 30, 120)

# MDPI DOIs are 10.3390/<code><volume><issue:02d><article:04d>; volume = year - offset
MDPI = {"ijms": 1999, "molecules": 1995, "s": 2000, "nu": 2008, "cancers": 2008, "jcm": 2011, "ijerph": 2003,
        "ma": 2007, "app": 2010, "su": 2008, "en": 2007, "rs": 2008, "cells": 2011, "antiox": 2011}
# Frontiers DOIs are 10.3389/<code>.<year>.<article:05d>
FRONTIERS = ("fimmu", "fpsyg", "fmicb", "fphar", "fonc", "fneur", "fpls", "fnins", "fpsyt", "fendo")
MOTIVATING = {("ijms", 20)}  # Int J Mol Sci 20(1):1, seen in the sink census before this study: reported, not tested
KNOWN_SINKS = {"Sci Rep 9:1": "10.1038/s41598-018-37186-2", "Nat Commun 9:1": "10.1038/s41467-017-02088-w"}

NEAR = range(2, 31)  # article numbers in the range of typical PDF lengths (Krivachy's "article L")
FAR = range(41, 61)  # controls: same volume, numbers past most PDF lengths

# Pre-registered thresholds
MIN_FAR, MIN_NEAR, MIN_UNITS = 10, 10, 10
ALPHA = 0.01
H1_MIN_RATIO = 2.0  # H1/H2: median smoothed ratio, article 1 to the median far control
H3_MIN_Q = 1.2  # H3: median ratio, near band to far band
H4_TOP, H4_MIN_CITES, H4_MIN_R, H4_READS = 3, 100, 3.0, 40
H4_MIN_N, H4_SHARE = 20, 0.50
CAL_MIN_N, CAL_SHARE = 10, 0.70

META_KEYS = {"key", "doi-asserted-by", "DOI"}
TITLE_KEYS = ("article-title", "unstructured")
STOP = {"about", "after", "among", "analysis", "based", "between", "during", "effect", "effects", "their", "these",
        "through", "under", "using", "which", "while", "within", "without", "study"}


def get_patient(url, waits=WAITS, sleep=time.sleep):
    """GET with back-off on 429/5xx. Returns bytes, or None (400/404 or after the last wait)."""
    last = None
    for w in (0,) + tuple(waits):
        if w:
            sleep(w)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            last = e
        except Exception as e:  # network hiccup: wait and retry
            last = e
    sys.stderr.write("GET gave up %s: %s\n" % (url, last))
    return None


class Client:
    """Crossref /works/{doi} lookups, cached and counted."""

    def __init__(self, fetch=get_patient, pause=0.05):
        self.fetch, self.pause, self.calls, self.cache = fetch, pause, 0, {}

    def work(self, doi):
        doi = doi.lower()
        if doi in self.cache:
            return self.cache[doi]
        self.calls += 1
        raw = self.fetch(CR + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
        if self.pause:
            time.sleep(self.pause)
        msg = None
        if raw:
            try:
                msg = json.loads(raw).get("message") or None
            except ValueError:
                msg = None
        self.cache[doi] = msg
        return msg


def mdpi_doi(code, vol, issue, n):
    return "10.3390/%s%d%02d%04d" % (code, vol, issue, n)


def frontiers_doi(code, year, n):
    return "10.3389/%s.%d.%05d" % (code, year, n)


def number_of(msg):
    """The article number Crossref gives (article-number, else the first page), as a string."""
    v = msg.get("article-number") or msg.get("page") or ""
    return str(v).split("-")[0].strip()


def cites(msg):
    return int((msg or {}).get("is-referenced-by-count") or 0)


def first_family(msg):
    authors = msg.get("author") or []
    return (authors[0].get("family") or "").lower() if authors else ""


def row(msg, n):
    t = msg.get("title") or [""]
    issued = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0]
    return {"doi": (msg.get("DOI") or "").lower(), "n": n, "cites": cites(msg), "number": number_of(msg),
            "issued": "-".join(str(x) for x in issued if x is not None), "type": msg.get("type") or "",
            "title": (t[0] if t else "")[:300], "first_author": first_family(msg)}


def find_mdpi(client, code, vol, n, start_issue, max_jump=3):
    """Article n of an MDPI volume, trying issues start..start+max_jump-1. Returns (msg, issue) or (None, start)."""
    for issue in range(start_issue, start_issue + max_jump):
        msg = client.work(mdpi_doi(code, vol, issue, n))
        if msg:
            return msg, issue
    return None, start_issue


def mdpi_unit(client, code, vol, near=NEAR, far=FAR):
    a1 = client.work(mdpi_doi(code, vol, 1, 1))
    if not a1:
        return None
    unit = {"publisher": "MDPI", "journal": code, "volume": vol, "year": vol + MDPI[code],
            "confirmatory": (code, vol) not in MOTIVATING, "article1": row(a1, 1), "near": [], "far": []}
    issue = 1
    for key, rng in (("near", near), ("far", far)):
        for n in rng:
            msg, issue = find_mdpi(client, code, vol, n, issue)
            if msg:
                unit[key].append(row(msg, n))
    return unit


def frontiers_unit(client, code, year, near=NEAR, far=FAR):
    a1 = client.work(frontiers_doi(code, year, 1))
    if not a1:
        return None
    unit = {"publisher": "Frontiers", "journal": code, "volume": a1.get("volume") or "", "year": year,
            "confirmatory": True, "article1": row(a1, 1), "near": [], "far": []}
    for key, rng in (("near", near), ("far", far)):
        for n in rng:
            msg = client.work(frontiers_doi(code, year, n))
            if msg:
                unit[key].append(row(msg, n))
    return unit


def smoothed_ratio(a, xs):
    return (a + 1) / (statistics.median(xs) + 1)


def is_top(unit):
    """Article 1 has strictly more Crossref citations than every far control."""
    far = [r["cites"] for r in unit["far"]]
    return bool(far) and unit["article1"]["cites"] > max(far)


def poisson_binomial_tail(ps, k):
    """P(K >= k) for K a sum of independent Bernoulli(p_i)."""
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for j, q in enumerate(dist):
            new[j] += q * (1 - p)
            new[j + 1] += q * p
        dist = new
    return sum(dist[k:]) if k < len(dist) else 0.0


def sign_test(pos, neg):
    """One-sided P(X >= pos) for X ~ Binomial(pos + neg, 1/2)."""
    n = pos + neg
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(pos, n + 1)) / 2 ** n


def score_top(units):
    """H1 (MDPI) and H2 (Frontiers): is article 1 the most cited of its volume's far controls more often than chance?"""
    elig = [u for u in units if u["confirmatory"] and len(u["far"]) >= MIN_FAR]
    detail = {"units": len(elig)}
    if len(elig) < MIN_UNITS:
        return "untestable", detail
    k = sum(1 for u in elig if is_top(u))
    ps = [1 / (len(u["far"]) + 1) for u in elig]
    p = poisson_binomial_tail(ps, k)
    med = statistics.median(smoothed_ratio(u["article1"]["cites"], [r["cites"] for r in u["far"]]) for u in elig)
    detail.update({"top": k, "expected_top": sum(ps), "p": p, "median_ratio": med})
    return ("supported" if p < ALPHA and med >= H1_MIN_RATIO else "not supported"), detail


def score_near(units):
    """H3: are articles 2-30 cited more than articles 41-60 of the same volume?"""
    elig = [u for u in units if u["confirmatory"] and len(u["near"]) >= MIN_NEAR and len(u["far"]) >= MIN_FAR]
    detail = {"units": len(elig)}
    if len(elig) < MIN_UNITS:
        return "untestable", detail
    qs = [(statistics.median(r["cites"] for r in u["near"]) + 1) / (statistics.median(r["cites"] for r in u["far"]) + 1)
          for u in elig]
    pos = sum(1 for q in qs if q > 1)
    neg = sum(1 for q in qs if q < 1)
    p = sign_test(pos, neg)
    med = statistics.median(qs)
    detail.update({"near_higher": pos, "far_higher": neg, "p": p, "median_q": med})
    return ("supported" if p < ALPHA and med >= H3_MIN_Q else "not supported"), detail


def title_words(title):
    seen = []
    for w in re.findall(r"[a-z0-9]+", re.sub(r"<[^>]+>", " ", title or "").lower()):
        if len(w) >= 5 and w not in STOP and w not in seen:
            seen.append(w)
    return seen[:8]


def classify_ref(ref, words, family):
    """genuine / other_work / doi_only / undetermined, for one deposited reference that carries the target's DOI."""
    if not (set(ref) - META_KEYS):
        return "doi_only"
    text = " ".join(str(ref.get(k) or "") for k in TITLE_KEYS).lower()
    if text.strip():
        ws = set(words)
        need = max(2, (len(ws) + 1) // 2)
        hits = sum(1 for w in ws if w in text)
        return "genuine" if ws and hits >= need else "other_work"
    auth = str(ref.get("author") or "").lower()
    if auth and family:
        return "genuine" if family in auth else "other_work"
    return "undetermined"


def parse_oc(raw):
    """Citing DOIs (lower case, unique, sorted) from an OpenCitations v2 citations response."""
    dois = set()
    try:
        items = json.loads(raw) if raw else []
    except ValueError:
        items = []
    for item in items:
        m = re.search(r"\bdoi:(\S+)", item.get("citing") or "")
        if m:
            dois.add(m.group(1).lower())
    return sorted(dois)


def h4_targets(units):
    """Up to 3 confirmatory MDPI article-1 records with >= 100 citations and ratio >= 3, highest ratio first."""
    c = []
    for u in units:
        if u["publisher"] != "MDPI" or not u["confirmatory"] or len(u["far"]) < MIN_FAR:
            continue
        a = u["article1"]
        r = smoothed_ratio(a["cites"], [x["cites"] for x in u["far"]])
        if a["cites"] >= H4_MIN_CITES and r >= H4_MIN_R and len(title_words(a["title"])) >= 3:
            c.append((r, u))
    c.sort(key=lambda x: (-x[0], x[1]["article1"]["doi"]))
    return [u for _, u in c[:H4_TOP]]


def read_citers(client, fetch, target, seed, n=H4_READS):
    """Classify the reference behind a seeded sample of a record's OpenCitations citers."""
    dois = parse_oc(fetch(OC + target["doi"]))
    pick = random.Random(seed).sample(dois, min(n, len(dois)))
    words = title_words(target["title"])
    out = []
    for d in pick:
        base = {"target": target["doi"], "citer": d}
        msg = client.work(d)
        if msg is None:
            out.append(dict(base, status="not_in_crossref"))
            continue
        refs = [r for r in msg.get("reference") or [] if (r.get("DOI") or "").lower() == target["doi"]]
        if not refs:
            out.append(dict(base, status="no_matching_reference"))
            continue
        out.append(dict(base, status="found", label=classify_ref(refs[0], words, target["first_author"]),
                        asserted_by=refs[0].get("doi-asserted-by") or "",
                        ref={k: str(v)[:300] for k, v in refs[0].items()}))
    return out, len(dois)


def share(reads):
    g = sum(1 for r in reads if r.get("label") == "genuine")
    o = sum(1 for r in reads if r.get("label") == "other_work")
    return {"n": g + o, "genuine": g, "share": (g / (g + o)) if g + o else None}


def score_h4(t_reads, c_reads):
    """H4: fewer than half the classifiable references behind the top MDPI article-1 records are genuine."""
    t, c = share(t_reads), share(c_reads)
    d = {"target": t, "control": c}
    if c["n"] < CAL_MIN_N or c["share"] < CAL_SHARE:
        return "untestable (classifier failed calibration)", d
    if t["n"] < H4_MIN_N:
        return "untestable", d
    return ("supported" if t["share"] < H4_SHARE else "not supported"), d


def openalex_counts(fetch, dois, cap=10):
    """OpenAlex cited_by_count for up to cap * 50 DOIs (descriptive only)."""
    out, calls = {}, 0
    for i in range(0, len(dois), 50):
        if calls >= cap:
            break
        calls += 1
        raw = fetch(OA + "?" + urllib.parse.urlencode({"filter": "doi:" + "|".join(dois[i:i + 50]), "per-page": "200",
                                                       "select": "doi,cited_by_count", "mailto": MAILTO}))
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            data = {}
        for w in data.get("results") or []:
            out[re.sub(r"^https?://(dx\.)?doi\.org/", "", w.get("doi") or "", flags=re.I).lower()] = w.get("cited_by_count")
    return out, calls


def summary_row(u):
    far = [r["cites"] for r in u["far"]]
    return {"publisher": u["publisher"], "journal": u["journal"], "volume": u["volume"], "year": u["year"],
            "confirmatory": u["confirmatory"], "article1_doi": u["article1"]["doi"],
            "article1_cites": u["article1"]["cites"], "article1_openalex": u["article1"].get("openalex_cites"),
            "article1_type": u["article1"]["type"], "article1_number": u["article1"]["number"], "n_near": len(u["near"]), "n_far": len(far),
            "far_median": statistics.median(far) if far else None, "far_max": max(far) if far else None,
            "ratio": smoothed_ratio(u["article1"]["cites"], far) if far else None, "top": is_top(u)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--only", default="", help="comma list of journal codes, for a trial run")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    only = {x for x in a.only.split(",") if x}
    client = Client()
    units = []
    for code, off in sorted(MDPI.items()):
        if only and code not in only:
            continue
        for y in YEARS:
            u = mdpi_unit(client, code, y - off)
            if u:
                units.append(u)
        sys.stderr.write("MDPI %s done, %d Crossref calls\n" % (code, client.calls))
    for code in FRONTIERS:
        if only and code not in only:
            continue
        for y in YEARS:
            u = frontiers_unit(client, code, y)
            if u:
                units.append(u)
        sys.stderr.write("Frontiers %s done, %d Crossref calls\n" % (code, client.calls))

    mdpi = [u for u in units if u["publisher"] == "MDPI"]
    fr = [u for u in units if u["publisher"] == "Frontiers"]
    res = {"seed": SEED, "years": [YEARS[0], YEARS[-1]], "units": {"MDPI": len(mdpi), "Frontiers": len(fr)}}
    res["H1"], res["H1_detail"] = score_top(mdpi)
    res["H2"], res["H2_detail"] = score_top(fr)
    res["H3"], res["H3_detail"] = score_near(mdpi)

    t_reads, c_reads, tinfo = [], [], []
    for i, u in enumerate(h4_targets(units)):
        r1, n1 = read_citers(client, get_patient, u["article1"], SEED + i)
        ctrl = max(u["far"], key=lambda x: (x["cites"], x["doi"]))
        r2, n2 = read_citers(client, get_patient, ctrl, SEED + 100 + i)
        t_reads += r1
        c_reads += r2
        tinfo.append({"target": u["article1"]["doi"], "opencitations_citers": n1, "control": ctrl["doi"],
                      "control_opencitations_citers": n2})
    res["H4"], res["H4_detail"] = score_h4(t_reads, c_reads)
    res["H4_targets"] = tinfo
    res["H4_labels"] = {"target": {}, "control": {}}
    for key, rr in (("target", t_reads), ("control", c_reads)):
        for r in rr:
            lab = r.get("label") or r["status"]
            res["H4_labels"][key][lab] = res["H4_labels"][key].get(lab, 0) + 1

    res["known_sinks_crossref"] = {k: cites(client.work(d)) for k, d in KNOWN_SINKS.items()}
    oa_counts, oa_calls = openalex_counts(get_patient, [u["article1"]["doi"] for u in units])
    for u in units:
        u["article1"]["openalex_cites"] = oa_counts.get(u["article1"]["doi"])
    res["calls"] = {"crossref": client.calls, "openalex": oa_calls}
    res["table"] = [summary_row(u) for u in units]

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for name, data in (("units.jsonl", units), ("reads.jsonl", t_reads + c_reads)):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "table"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
