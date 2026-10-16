# stub_census.py - OpenAlex records whose DOI is only the stem of a journal's DOIs ("DOI stubs"),
# and the citations they absorb. Pre-registration: findings/doi-stub-census-prereg-v1-2026-10-16.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public OpenAlex and Crossref APIs.
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

MAILTO = "mv2@munimtech.com"
UA = "mv2-stub-census/1.0 (MV2 of Munim, Inc.; mailto:%s)" % MAILTO
OA = "https://api.openalex.org/works"
SEED = 20261019
SAMPLE_FILTER = "has_doi:true,type:article,publication_year:2000-2025,cited_by_count:>49"
N_SAMPLE = 6000
BASELINE_FILTER = "type:article,publication_year:2015-2025"
N_READ = 10  # Crossref reads per stub
MAX_DETAIL = 60  # stubs that get the per-stub calls, largest cited_by_count first
MAX_OA_CALLS = 400
WAITS = (30, 60, 120, 300, 600)  # back-off for OpenAlex's keyless daily budget (HTTP 401/429)

# Pre-registered thresholds
MIN_NEW = 5  # H1: stub records found by the census arm that are not in the pilot list
H2_MIN_READS, H2_SHARE = 10, 0.80
H3_MIN_CITERS, H3_FACTOR, H3_SHARE = 50, 2.0, 0.75

DASHES = "‐‑‒–—―−"
SAFE = re.compile(r"^10\.\d{4,9}/[a-z0-9._/\-]+$")
WILEY_PREFIXES = ("10.1002/", "10.1111/", "10.1113/", "10.1046/", "10.1034/")
# Found by hand through the API on 2026-10-16 (before this census)
PILOT = ["10.1016/s0140", "10.1016/s0140-6736", "10.1136/bmjopen", "10.1136/annrheumdis", "10.1038/s41598",
         "10.1016/s0091", "10.1016/s1470", "10.1016/s0002", "10.1136/archdischild", "10.1136/heartjnl",
         "10.1136/thoraxjnl", "10.1186/1471"]
LABELS = ("exact", "cut_at_unicode_dash", "has_unicode_dash", "intact_ascii")  # strongest first


class Budget:
    """Counts OpenAlex calls and the cost OpenAlex reports; refuses calls past the cap."""

    def __init__(self, cap=MAX_OA_CALLS):
        self.cap, self.calls, self.cost, self.refused, self.failed = cap, 0, 0.0, 0, 0

    def take(self):
        if self.calls >= self.cap:
            self.refused += 1
            return False
        self.calls += 1
        return True


BUDGET = Budget()


def get_patient(url, waits=WAITS, sleep=time.sleep):
    """GET with long back-off on 401/429/5xx. Returns bytes, or None (400/404 or after the last wait)."""
    last = None
    for w in (0,) + tuple(waits):
        if w:
            sleep(w)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            last = e
        except Exception as e:  # network hiccup: wait and retry
            last = e
    sys.stderr.write("GET gave up %s: %s\n" % (url, last))
    return None


def oa(params, fetch=get_patient, budget=None):
    """One OpenAlex /works call. Returns parsed JSON or None."""
    budget = budget or BUDGET
    if not budget.take():
        return None
    q = dict(params)
    q["mailto"] = MAILTO
    raw = fetch(OA + "?" + urllib.parse.urlencode(q))
    if raw is None:
        budget.failed += 1
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        budget.failed += 1
        return None
    budget.cost += float((data.get("meta") or {}).get("cost_usd") or 0)
    time.sleep(0.2)
    return data


def sampled(filt, n, seed, select, fetch=get_patient, budget=None, per_page=200):
    """A seeded OpenAlex sample of up to n works, paged. Returns (works, complete)."""
    out, page = [], 1
    while len(out) < n:
        data = oa({"filter": filt, "sample": str(n), "seed": str(seed), "per-page": str(per_page),
                   "page": str(page), "select": select}, fetch, budget)
        if data is None:
            return out, False
        res = data.get("results") or []
        out.extend(res)
        total = (data.get("meta") or {}).get("count")
        if not res or (total is not None and len(out) >= min(n, total)):
            break
        page += 1
    return out, True


def short_id(wid):
    return (wid or "").rsplit("/", 1)[-1]


def strip_doi(doi):
    d = (doi or "").strip()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I).lower()


def stubs_of(doi):
    """The stems a parser leaves when it stops at the first hyphen ("dash") or the first "(" ("paren")."""
    d = strip_doi(doi)
    head, sep, tail = d.partition("/")
    if not sep:
        return []
    out = []
    for ch, kind in (("-", "dash"), ("(", "paren")):
        i = tail.find(ch)
        if i < 2:
            continue
        s = head + "/" + tail[:i]
        if SAFE.match(s) and (s, kind) not in out:
            out.append((s, kind))
    return out


def kind_of(stub):
    return "paren" if "-" in stub.partition("/")[2] else "dash"


def norm_dashes(s):
    return "".join("-" if c in DASHES else c for c in s)


def ref_label(ref_doi, stub):
    """How one deposited reference DOI relates to the stub, or None if it is not in the stub's journal."""
    rd = (ref_doi or "").strip().lower()
    if not rd or not norm_dashes(rd).startswith(stub):
        return None
    if rd == stub:
        return "exact"
    if rd.startswith(stub) and len(rd) > len(stub) and rd[len(stub)] in DASHES:
        return "cut_at_unicode_dash"
    if norm_dashes(rd) != rd:
        return "has_unicode_dash"
    return "intact_ascii"


def read_citer(doi, stub, msg):
    """The strongest label among the citer's deposited reference DOIs."""
    if msg is None:
        return {"doi": doi, "status": "not_in_crossref"}
    refs = msg.get("reference")
    if not refs:
        return {"doi": doi, "status": "no_reference_list"}
    found = [(ref_label(r.get("DOI"), stub), r) for r in refs]
    found = [(lab, r) for lab, r in found if lab]
    if not found:
        return {"doi": doi, "status": "found", "label": "absent", "wiley": is_wiley(doi)}
    lab, r = min(found, key=lambda x: LABELS.index(x[0]))
    return {"doi": doi, "status": "found", "label": lab, "wiley": is_wiley(doi),
            "ref_doi": r.get("DOI"), "asserted_by": r.get("doi-asserted-by") or "", "n_journal_refs": len(found)}


def is_wiley(doi):
    return strip_doi(doi).startswith(WILEY_PREFIXES)


def group_counts(data):
    """{key_display_name or key: count} from a group_by response, plus meta.count."""
    if not data:
        return {}, None
    g = {}
    for x in data.get("group_by") or []:
        name = str(x.get("key_display_name") or x.get("key") or "")
        g[name] = g.get(name, 0) + int(x.get("count") or 0)
    return g, (data.get("meta") or {}).get("count")


def wiley_share(data):
    g, n = group_counts(data)
    if not n:
        return None
    return sum(v for k, v in g.items() if "wiley" in k.lower()) / n


def earlier_citers(data, year):
    """Citers dated before the record's own publication year."""
    g, _ = group_counts(data)
    out = 0
    for k, v in g.items():
        try:
            if year and int(k) < int(year):
                out += v
        except ValueError:
            pass
    return out


def lookup(stubs, fetch=get_patient, budget=None, batch=50):
    """OpenAlex records whose DOI equals a stub. Returns (records, complete)."""
    out, done = [], True
    for i in range(0, len(stubs), batch):
        part = stubs[i:i + batch]
        data = oa({"filter": "doi:" + "|".join(part), "per-page": "200", "select": SELECT}, fetch, budget)
        if data is None:
            done = False
            continue
        want = set(part)
        out.extend(w for w in data.get("results") or [] if strip_doi(w.get("doi")) in want)
    return out, done


def crossref(doi, tries=4):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()).get("message") or {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 ** i)
    return None


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None, None)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def score_h1(census_stubs):
    new = sorted(s for s in census_stubs if s not in PILOT)
    return ("supported" if len(new) >= MIN_NEW else "not supported"), new


def score_h2(reads):
    """Wiley citers of dash stubs whose deposit carries a Unicode-dash DOI in the stub's journal."""
    w = [r for r in reads if r.get("kind") == "dash" and r["status"] == "found" and r.get("wiley")]
    k = sum(1 for r in w if r.get("label") in ("cut_at_unicode_dash", "has_unicode_dash"))
    p, lo, hi = wilson(k, len(w))
    if len(w) < H2_MIN_READS:
        v = "untestable"
    else:
        v = "supported" if p >= H2_SHARE else "not supported"
    return v, {"n": len(w), "k": k, "share": p, "lo": lo, "hi": hi}


def score_h3(rows, baseline):
    """Dash stubs with >= 50 citers whose Wiley share exceeds twice Wiley's share of all articles."""
    elig = [r for r in rows if r["kind"] == "dash" and (r.get("citers") or 0) >= H3_MIN_CITERS
            and r.get("wiley_share") is not None]
    if not elig or baseline is None:
        return "untestable", {"n": len(elig), "above": 0}
    above = sum(1 for r in elig if r["wiley_share"] > H3_FACTOR * baseline)
    return ("supported" if above / len(elig) >= H3_SHARE else "not supported"), {"n": len(elig), "above": above}


SELECT = "id,doi,display_name,publication_year,cited_by_count,counts_by_year,type"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    res = {"seed": SEED, "sample_filter": SAMPLE_FILTER, "n_sample": N_SAMPLE, "pilot": PILOT}

    # Census arm: stems of a seeded sample of well-cited articles' DOIs
    works, done = sampled(SAMPLE_FILTER, N_SAMPLE, SEED, "id,doi")
    cand = {}
    for w in works:
        for s, kind in stubs_of(w.get("doi")):
            cand.setdefault(s, kind)
    census = sorted(cand)
    res["sample"] = {"works": len(works), "complete": done and len(works) >= N_SAMPLE, "stems": len(census),
                     "stems_by_kind": dict(Counter(cand.values()))}

    recs, look_done = lookup(sorted(set(census) | set(PILOT)))
    res["lookup_complete"] = look_done
    by_stub = {}
    for w in recs:
        by_stub.setdefault(strip_doi(w.get("doi")), []).append(w)
    census_found = sorted(s for s in by_stub if s in cand)
    res["H1"], res["H1_new"] = score_h1(census_found)

    base = oa({"filter": BASELINE_FILTER, "group_by": "primary_location.source.publisher_lineage"})
    baseline = wiley_share(base)
    res["wiley_baseline"] = baseline

    rows = []
    for s, ws in by_stub.items():
        for w in ws:
            rows.append({"stub": s, "kind": cand.get(s) or kind_of(s), "arm": "census" if s in cand else "pilot",
                         "in_pilot": s in PILOT, "id": short_id(w.get("id")), "title": (w.get("display_name") or "")[:160],
                         "year": w.get("publication_year"), "type": w.get("type"), "citers": w.get("cited_by_count"),
                         "counts_by_year": {str(c["year"]): c.get("cited_by_count") for c in w.get("counts_by_year") or []}})
    rows.sort(key=lambda r: (-(r["citers"] or 0), r["stub"], r["id"]))

    reads = []
    for j, r in enumerate(rows):
        if j >= MAX_DETAIL or not r["citers"]:
            r["detail"] = False
            continue
        r["detail"] = True
        r["registered_in_crossref"] = crossref(r["stub"]) is not None
        r["wiley_share"] = wiley_share(oa({"filter": "cites:" + r["id"],
                                           "group_by": "primary_location.source.publisher_lineage"}))
        r["earlier_citers"] = earlier_citers(oa({"filter": "cites:" + r["id"], "group_by": "publication_year"}),
                                             r["year"])
        cit, _ = sampled("cites:" + r["id"], N_READ, SEED + 1 + j, "id,doi")
        rr = []
        for c in cit:
            d = strip_doi(c.get("doi"))
            if d:
                rr.append(dict(read_citer(d, r["stub"], crossref(d)), stub=r["stub"], kind=r["kind"]))
                time.sleep(0.1)
        r["reads"] = dict(Counter(x.get("label") or x["status"] for x in rr))
        reads.extend(rr)

    res["records"] = len(rows)
    res["citations_absorbed"] = {"all": sum(r["citers"] or 0 for r in rows),
                                 "census_arm": sum(r["citers"] or 0 for r in rows if r["arm"] == "census")}
    res["H2"], res["H2_detail"] = score_h2(reads)
    res["H3"], res["H3_detail"] = score_h3([r for r in rows if r.get("detail")], baseline)
    res["paren_reads"] = dict(Counter(x.get("label") or x["status"] for x in reads if x.get("kind") == "paren"))
    res["nonwiley_dash_reads"] = dict(Counter(x.get("label") or x["status"] for x in reads
                                              if x.get("kind") == "dash" and not x.get("wiley")))
    res["budget"] = {"openalex_calls": BUDGET.calls, "openalex_cost_usd": round(BUDGET.cost, 4),
                     "refused_over_cap": BUDGET.refused, "failed": BUDGET.failed}

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for name, data in (("stub_records.jsonl", rows), ("citer_reads.jsonl", reads)):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: res[k] for k in ("sample", "H1", "H1_new", "wiley_baseline", "records", "citations_absorbed",
                                          "H2", "H2_detail", "H3", "H3_detail", "paren_reads", "nonwiley_dash_reads",
                                          "budget")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
