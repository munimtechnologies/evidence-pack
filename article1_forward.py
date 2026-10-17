# article1_forward.py - Does a reference with first page "1" make OpenAlex link the citer to article 1 of that volume, and only for older citers?
# Pre-registration: findings/article-number-1-forward-prereg-v2-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public Crossref and OpenAlex APIs.
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse

import article1_check as a1
import article1_mechanism as m
import openalex_article1 as oa1

SEED = 20261027
ERAS = {"old": ("2019-01-01", "2021-12-31"), "new": ("2023-01-01", "2025-12-31")}  # citers; 2022 left out
VOL_YEARS = range(2016, 2020)  # cited volumes 2016-2019, as v2's H1
PER_CALL, MAX_CALLS, ENOUGH = 100, 250, 40  # Crossref random works per call; calls per era; stop at this many exposed pairs
MAX_FAILS = 5  # consecutive failed calls end an era's sampling
N_UNEXPOSED = 300  # seeded sample of unexposed pairs per era looked up in OpenAlex
PAUSE = 1.0

# Pre-registered thresholds
ALPHA = 0.01
MIN_EXPOSED, MIN_UNEXPOSED = 15, 50
H1_RATE, H1_RATIO = 0.30, 3.0
H2_MAX = 0.10

MDPI_RX = re.compile(r"^10\.3390/([a-z]+)(\d+)(\d{2})(\d{4})$")
FRONTIERS_RX = re.compile(r"^10\.3389/(f[a-z]+)\.(\d{4})\.(\d{5})$")


def volume_of(doi):
    """(volume key, article-1 DOI) for a DOI in a 2016-2019 volume of a covered MDPI journal or any Frontiers journal, else None."""
    d = (doi or "").strip().lower()
    x = MDPI_RX.match(d)
    if x:
        code, vol = x.group(1), int(x.group(2))
        if code in a1.MDPI and vol + a1.MDPI[code] in VOL_YEARS:
            return "%s %d" % (code, vol), a1.mdpi_doi(code, vol, 1, 1)
        return None
    x = FRONTIERS_RX.match(d)
    if x and int(x.group(2)) in VOL_YEARS:
        return "%s %s" % (x.group(1), x.group(2)), a1.frontiers_doi(x.group(1), int(x.group(2)), 1)
    return None


def pairs_of(work):
    """({volume key: pair}, unexposed pairs dropped) for one Crossref work.

    A pair holds the work's DOI references into one covered volume (article 1 itself left out) and those with
    first page "1". Pairs whose work cites article 1 by DOI are dropped. So are pairs with no page-1 reference
    when the work has a page-1 reference without a DOI, whose volume cannot be told."""
    refs = work.get("reference") or []
    cited = {(r.get("DOI") or "").strip().lower() for r in refs}
    blind = any(m.page1(r) and not r.get("DOI") for r in refs)
    out = {}
    for r in refs:
        d = (r.get("DOI") or "").strip().lower()
        v = volume_of(d)
        if not v or d == v[1]:
            continue
        p = out.setdefault(v[0], {"volume": v[0], "article1": v[1], "refs": 0, "page1": []})
        p["refs"] += 1
        if m.page1(r):
            p["page1"].append(m.slim(r))
    dropped = 0
    for k in sorted(out):
        if out[k]["article1"] in cited:
            del out[k]
        elif blind and not out[k]["page1"]:
            del out[k]
            dropped += 1
    return out, dropped


def sample_url(era, select=True):
    lo, hi = ERAS[era]
    q = {"sample": str(PER_CALL),
         "filter": "type:journal-article,has-references:true,from-pub-date:%s,until-pub-date:%s" % (lo, hi),
         "mailto": a1.MAILTO}
    if select:
        q["select"] = "DOI,issued,reference"
    return a1.CR.rstrip("/") + "?" + urllib.parse.urlencode(q)


def parse_sample(raw):
    """The works in a Crossref list response, or None if it is not one."""
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    msg = data.get("message") if isinstance(data, dict) else None
    if not isinstance(msg, dict):
        return None
    return msg.get("items") or []


def collect(fetch, era, max_calls=MAX_CALLS, enough=ENOUGH, pause=0.0):
    """Random Crossref journal articles of one era, until `enough` exposed pairs or max_calls calls.
    Returns (pairs, info, sorted DOIs of every work read)."""
    pairs, seen, fails = [], set(), 0
    info = {"calls": 0, "failed_calls": 0, "works": 0, "duplicates": 0, "citers": 0, "unexposed_dropped": 0}
    while info["calls"] < max_calls and fails < MAX_FAILS and sum(1 for p in pairs if p["page1"]) < enough:
        info["calls"] += 1
        items = parse_sample(fetch(sample_url(era)))
        if items is None:
            items = parse_sample(fetch(sample_url(era, select=False)))
        if pause:
            time.sleep(pause)
        if items is None:
            info["failed_calls"] += 1
            fails += 1
            continue
        fails = 0
        for w in items:
            d = (w.get("DOI") or "").lower()
            if not d:
                continue
            if d in seen:
                info["duplicates"] += 1
                continue
            seen.add(d)
            info["works"] += 1
            got, dropped = pairs_of(w)
            info["unexposed_dropped"] += dropped
            if got:
                info["citers"] += 1
            y = m.year_of(w)
            for k in sorted(got):
                pairs.append(dict(got[k], era=era, citer=d, year=y))
    info["pairs"] = len(pairs)
    info["exposed"] = sum(1 for p in pairs if p["page1"])
    return pairs, info, sorted(seen)


def choose(pairs, seed):
    """Every exposed pair, and a seeded sample of N_UNEXPOSED unexposed ones."""
    ex = [p for p in pairs if p["page1"]]
    un = sorted((p for p in pairs if not p["page1"]), key=lambda p: (p["citer"], p["volume"]))
    return ex + random.Random(seed).sample(un, min(N_UNEXPOSED, len(un)))


def link(fetch, pairs):
    """Mark each pair with whether OpenAlex lists article 1 of its volume among the citer's referenced works."""
    citers = sorted({p["citer"] for p in pairs if "|" not in p["citer"] and "," not in p["citer"]})
    works, c1, f1 = m.oa_refs(fetch, citers)
    firsts = sorted({p["article1"] for p in pairs})
    ids, c2, f2 = oa1.openalex_works(fetch, firsts)
    for p in pairs:
        w, a = works.get(p["citer"]), ids.get(p["article1"])
        p["citer_in_oa"], p["article1_oa_id"] = w is not None, a[0] if a else None
        p["oa"] = (a[0] in w[1]) if (w and a) else None
    return {"citers": len(citers), "citers_found": len(works), "article1s": len(firsts), "article1s_found": len(ids),
            "calls": c1 + c2, "failed_calls": f1 + f2}


def rates(pairs):
    e = [p for p in pairs if p["page1"] and p.get("oa") is not None]
    u = [p for p in pairs if not p["page1"] and p.get("oa") is not None]
    a, b = sum(1 for p in e if p["oa"]), sum(1 for p in u if p["oa"])
    return {"exposed": len(e), "exposed_linked": a, "exposed_rate": m.rate(a, len(e)),
            "unexposed": len(u), "unexposed_linked": b, "unexposed_rate": m.rate(b, len(u))}


def score_h1(old):
    """H1: for citers from 2019-2021, a page-1 reference into a volume goes with a link to its article 1."""
    d = rates(old)
    if d["exposed"] < MIN_EXPOSED or d["unexposed"] < MIN_UNEXPOSED:
        return "untestable", d
    d["p"] = m.fisher_greater(d["exposed_linked"], d["exposed"], d["unexposed_linked"], d["unexposed"])
    ok = d["exposed_rate"] >= H1_RATE and d["exposed_rate"] >= H1_RATIO * d["unexposed_rate"] and d["p"] < ALPHA
    return ("supported" if ok else "not supported"), d


def score_h2(old, new):
    """H2: for citers from 2023-2025 it rarely does, and less often than for 2019-2021 citers."""
    o, n = rates(old), rates(new)
    d = {"old_exposed": o["exposed"], "old_linked": o["exposed_linked"], "old_rate": o["exposed_rate"],
         "new_exposed": n["exposed"], "new_linked": n["exposed_linked"], "new_rate": n["exposed_rate"]}
    if o["exposed"] < MIN_EXPOSED or n["exposed"] < MIN_EXPOSED:
        return "untestable", d
    d["p"] = m.fisher_greater(o["exposed_linked"], o["exposed"], n["exposed_linked"], n["exposed"])
    ok = n["exposed_rate"] <= H2_MAX and d["p"] < ALPHA
    return ("supported" if ok else "not supported"), d


def describe(pairs):
    out = {}
    for era in ERAS:
        e = [p for p in pairs if p["era"] == era]
        out[era] = dict(rates(e), by_publisher={pub: rates([p for p in e if p["article1"].startswith(pre)])
                                                for pub, pre in (("MDPI", "10.3390/"), ("Frontiers", "10.3389/"))})
    return out


def run(fetch, out_dir, max_calls=MAX_CALLS, enough=ENOUGH, pause=0.0):
    os.makedirs(out_dir, exist_ok=True)
    res = {"seed": SEED, "eras": ERAS, "volume_years": [VOL_YEARS[0], VOL_YEARS[-1]], "sampling": {}}
    chosen = []
    for i, era in enumerate(ERAS):
        pairs, info, seen = collect(fetch, era, max_calls, enough, pause)
        res["sampling"][era] = info
        chosen += choose(pairs, SEED + i)
        with open(os.path.join(out_dir, "sampled_%s.txt" % era), "w", encoding="utf-8") as f:
            f.write("".join(d + "\n" for d in seen))
        sys.stderr.write("%s: %d works, %d pairs, %d exposed, %d calls (%d failed)\n"
                         % (era, info["works"], info["pairs"], info["exposed"], info["calls"], info["failed_calls"]))
    res["openalex"] = link(fetch, chosen)
    old = [p for p in chosen if p["era"] == "old"]
    new = [p for p in chosen if p["era"] == "new"]
    res["H1"], res["H1_detail"] = score_h1(old)
    res["H2"], res["H2_detail"] = score_h2(old, new)
    res["descriptive"] = describe(chosen)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for p in chosen:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-calls", type=int, default=MAX_CALLS)
    a = ap.parse_args(argv)
    res = run(a1.get_patient, a.out_dir, a.max_calls, ENOUGH, PAUSE)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
