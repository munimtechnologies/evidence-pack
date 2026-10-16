# sink_census.py - how common are citation sinks? (pre-registration: citation-sink-census-prereg-v1.md)
# A citation sink is a paper whose citation count is inflated by references that are really to other works.
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
UA = "mv2-sink-census/1.0 (MV2 of Munim, Inc.; mailto:%s)" % MAILTO
OA = "https://api.openalex.org/works"
SEED = 20261018
SEEDS = {  # the two known sinks (calibration positives)
    "W2599766179": "10.1016/j.physbeh.2017.03.040",  # Bunney 2017, Physiol Behav 176:139-148
    "W2983201012": "10.1038/s41598-019-52748-8",  # Sci Rep 2019; OpenAlex community thread, 2025-02-26
}
RANDOM_FILTER = "type:article,publication_year:2012-2020,cited_by_count:>99"
N_RANDOM = 4000
N_SNOW = 400  # sampled jump-year citers per seed
MIN_COCITED = 3  # a snowball candidate is referenced by at least this many sampled citers
TOP_CANDIDATES = 100  # per seed
N_VERIFY = 20  # Crossref reads per sink
MAX_OA_CALLS = 700
WAITS = (30, 60, 120, 300, 600)  # back-off for OpenAlex's keyless daily budget (HTTP 401/429)

# Pre-registered thresholds
J_LATE, J_EARLY = 8.0, 25.0  # jump ratio for y >= pub+2, and for y == pub+1
MIN_JUMP_COUNT = 50
FIRST_JUMP_YEAR, LAST_YEAR = 2016, 2025
T_MAX = 0.15  # top-subfield share of jump-year citers
GENUINE_MAX = 0.25  # confirmed sink: at most this share of read citers genuinely cite the paper
MIN_VERIFY = 10
DEPOSIT_RATIO = 0.3  # Crossref/OpenAlex count ratio at or above which the misdirection is in Crossref deposits

META_KEYS = {"key", "doi-asserted-by", "DOI"}
STOP = {"with", "from", "that", "this", "their", "into", "after", "during", "between", "among", "using",
        "study", "effect", "effects", "analysis", "role", "case", "based", "via", "under", "over", "than"}


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
    """GET with long back-off on 401/429/5xx. Returns bytes, or None (404 or after the last wait)."""
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


def counts_map(work):
    return {int(c["year"]): int(c.get("cited_by_count") or 0) for c in work.get("counts_by_year") or []}


def jump(work):
    """Largest one-year jump: (ratio, year, count). ratio = c[y] / max(10, mean(c[y-1], c[y-2])),
    over y from max(pub+1, 2016) to 2025 with c[y] >= 50."""
    c, pub = counts_map(work), work.get("publication_year") or 0
    best = (0.0, None, 0)
    for y in range(max(pub + 1, FIRST_JUMP_YEAR), LAST_YEAR + 1):
        n = c.get(y, 0)
        if n < MIN_JUMP_COUNT:
            continue
        r = n / max(10.0, (c.get(y - 1, 0) + c.get(y - 2, 0)) / 2.0)
        if r > best[0]:
            best = (r, y, n)
    return best


def flagged(work):
    r, y, _ = jump(work)
    if y is None:
        return False
    return r >= (J_EARLY if y == (work.get("publication_year") or 0) + 1 else J_LATE)


def top_share(data):
    """(share, subfield name, n) of the largest primary-topic subfield in a group_by response."""
    if not data:
        return None
    n = (data.get("meta") or {}).get("count") or 0
    groups = [g for g in data.get("group_by") or []
              if g.get("key") and "unknown" not in str(g.get("key")).lower()]
    if not n or not groups:
        return {"share": None, "subfield": "", "n": n}
    g = max(groups, key=lambda x: x.get("count") or 0)
    return {"share": (g.get("count") or 0) / n, "subfield": g.get("key_display_name") or "", "n": n}


def coherence(wid, year=None, fetch=get_patient, budget=None):
    filt = "cites:" + short_id(wid) + (",publication_year:%d" % year if year else "")
    return top_share(oa({"filter": filt, "group_by": "primary_topic.subfield.id", "per-page": "5"}, fetch, budget))


def is_sink(jump_ok, coh):
    """Pre-registered screen: a flagged jump, at least 50 jump-year citers, top-subfield share <= 0.15."""
    return bool(jump_ok and coh and coh.get("share") is not None and coh["n"] >= MIN_JUMP_COUNT
                and coh["share"] <= T_MAX)


def cocited(citers, exclude):
    """How many sampled citers reference each work (each citer counted once per work)."""
    cnt = Counter()
    ex = {short_id(x) for x in exclude}
    for w in citers:
        for r in {short_id(x) for x in w.get("referenced_works") or []}:
            if r and r not in ex:
                cnt[r] += 1
    return cnt


def candidates(cnt, k=MIN_COCITED, top=TOP_CANDIDATES):
    return [w for w, n in sorted(cnt.items(), key=lambda x: (-x[1], x[0])) if n >= k][:top]


def by_ids(ids, select, fetch=get_patient, budget=None, batch=50):
    out = []
    for i in range(0, len(ids), batch):
        data = oa({"filter": "openalex_id:" + "|".join(ids[i:i + batch]), "per-page": str(batch),
                   "select": select}, fetch, budget)
        out.extend((data or {}).get("results") or [])
    return out


# ---- Crossref verification ----

def strip_doi(doi):
    d = (doi or "").strip()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I).lower()


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


def target_meta(doi, msg):
    msg = msg or {}
    authors = msg.get("author") or [{}]
    page = str(msg.get("page") or msg.get("article-number") or "")
    return {"doi": strip_doi(doi), "title": " ".join(msg.get("title") or []),
            "family": (authors[0].get("family") or "") if authors else "",
            "volume": str(msg.get("volume") or ""), "first_page": page.split("-")[0].strip(),
            "crossref_count": msg.get("is-referenced-by-count")}


def title_words(title):
    return {w for w in re.findall(r"[a-z]{4,}", (title or "").lower()) if w not in STOP}


def find_ref(refs, t):
    """The reference that points at the target: by DOI, else by the same volume and first page,
    else by free text naming the target (first author plus first page, or most title words)."""
    for r in refs or []:
        if t["doi"] and strip_doi(r.get("DOI")) == t["doi"]:
            return r
    if t["volume"] and t["first_page"]:
        for r in refs or []:
            if str(r.get("volume") or "") == t["volume"] and str(r.get("first-page") or "") == t["first_page"]:
                return r
    for r in refs or []:
        blob = " ".join(str(v) for k, v in r.items() if k not in META_KEYS)
        named = t["family"] and re.search(r"\b%s\b" % re.escape(t["family"]), blob, re.I)
        if named and t["first_page"] and re.search(r"\b%s\b" % re.escape(t["first_page"]), blob):
            return r
        tw = title_words(t["title"])
        if tw and len(tw & title_words(blob)) >= 0.6 * len(tw):
            return r
    return None


def classify_ref(ref, t):
    """genuine: names the target's first author or most of its title words; doi_only; other_work."""
    blob = " ".join(str(v) for k, v in ref.items() if k not in META_KEYS)
    if not blob.strip():
        return "doi_only"
    if t["family"] and re.search(r"\b%s\b" % re.escape(t["family"]), blob, re.I):
        return "genuine"
    tw = title_words(t["title"])
    if tw and len(tw & title_words(blob)) >= 0.6 * len(tw):
        return "genuine"
    return "other_work"


def read_citer(doi, t, msg):
    if msg is None:
        return {"doi": doi, "status": "not_in_crossref"}
    refs = msg.get("reference")
    if not refs:
        return {"doi": doi, "status": "no_reference_list"}
    hit = find_ref(refs, t)
    if hit is None:
        return {"doi": doi, "status": "target_not_in_list"}
    return {"doi": doi, "status": "found", "class": classify_ref(hit, t), "via_doi": bool(hit.get("DOI")),
            "asserted_by": hit.get("doi-asserted-by") or "",
            "ref": {k: str(v)[:160] for k, v in hit.items() if k != "key"}}


def verdict(reads):
    """Share of read citers (with a readable reference list) whose deposit genuinely cites the target.
    DOI-only matches cannot be judged and are left out of the denominator."""
    listed = [r for r in reads if r["status"] == "target_not_in_list"
              or (r["status"] == "found" and r.get("class") != "doi_only")]
    genuine = sum(1 for r in listed if r.get("class") == "genuine")
    n = len(listed)
    share = genuine / n if n else None
    if n < MIN_VERIFY:
        v = "unverified"
    else:
        v = "confirmed" if share <= GENUINE_MAX else "not_confirmed"
    found = [r for r in reads if r["status"] == "found"]
    return {"n_listed": n, "genuine": genuine, "share": share, "verdict": v,
            "status": dict(Counter(r["status"] for r in reads)),
            "class": dict(Counter(r.get("class") for r in found)),
            "found_via_doi": sum(1 for r in found if r.get("via_doi"))}


def mechanism(crossref_count, openalex_count):
    if not openalex_count or crossref_count is None:
        return None, "unknown"
    ratio = crossref_count / openalex_count
    return ratio, ("crossref_deposits" if ratio >= DEPOSIT_RATIO else "openalex_matching")


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None, None)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def verify(work, year, seed, fetch=get_patient, budget=None):
    """Read N_VERIFY random jump-year citers' deposited references in Crossref."""
    wid = short_id(work["id"])
    doi = strip_doi(work.get("doi"))
    t = target_meta(doi, crossref(doi) if doi else None)
    cit, _ = sampled("cites:%s,publication_year:%d" % (wid, year), N_VERIFY, seed, "id,doi", fetch, budget)
    reads = []
    for c in cit:
        d = strip_doi(c.get("doi"))
        if d:
            reads.append(read_citer(d, t, crossref(d)))
            time.sleep(0.1)
    ratio, mech = mechanism(t["crossref_count"], work.get("cited_by_count"))
    return {"target": t, "reads": reads, "verdict": verdict(reads), "crossref_openalex_ratio": ratio,
            "mechanism": mech}


SELECT = "id,doi,display_name,publication_year,cited_by_count,counts_by_year,primary_topic,type"


def screen(works, budget=None, fetch=get_patient):
    """Jump flag for every work; a coherence call for each flagged one."""
    rows = []
    for w in works:
        r, y, n = jump(w)
        f = flagged(w)
        row = {"id": short_id(w.get("id")), "doi": strip_doi(w.get("doi")), "year": w.get("publication_year"),
               "cited_by": w.get("cited_by_count"), "field": ((w.get("primary_topic") or {}).get("field") or {}).get(
                   "display_name"), "jump": round(r, 2), "jump_year": y, "jump_count": n, "flagged": f}
        if f:
            row["coherence_jump_year"] = coherence(row["id"], y, fetch, budget)
            row["sink_screen"] = is_sink(True, row["coherence_jump_year"])
        rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    res = {"seed": SEED, "thresholds": {"J_late": J_LATE, "J_early": J_EARLY, "min_jump_count": MIN_JUMP_COUNT,
                                        "T_max": T_MAX, "genuine_max": GENUINE_MAX, "deposit_ratio": DEPOSIT_RATIO}}

    # H1: calibration on the two known sinks
    seeds = by_ids(list(SEEDS), SELECT)
    seed_rows = screen(seeds)
    res["H1_rows"] = seed_rows
    res["H1"] = "supported" if len(seed_rows) == 2 and all(r.get("sink_screen") for r in seed_rows) else "not supported"

    # H2: prevalence in a seeded random sample
    rnd, rnd_done = sampled(RANDOM_FILTER, N_RANDOM, SEED, SELECT)
    rnd_rows = screen(rnd)
    k = sum(1 for r in rnd_rows if r.get("sink_screen"))
    p, lo, hi = wilson(k, len(rnd_rows))
    res["random"] = {"n": len(rnd_rows), "complete": rnd_done and len(rnd_rows) >= N_RANDOM,
                     "flagged": sum(1 for r in rnd_rows if r["flagged"]), "sink_screen": k,
                     "share": p, "lo": lo, "hi": hi}
    res["H2"] = ("untestable" if len(rnd_rows) < 1000 else ("supported" if hi is not None and hi < 0.005
                                                            else "not supported"))

    # H3: snowball from each seed's jump-year citers
    snow, snow_rows, snow_works, seen = {}, [], [], set(SEEDS)
    for i, sid in enumerate(SEEDS):
        cit, done = sampled("cites:%s,publication_year:2020-2021" % sid, N_SNOW, SEED + 1 + i, "id,referenced_works")
        cnt = cocited(cit, SEEDS)
        cands = [c for c in candidates(cnt) if c not in seen]
        seen.update(cands)
        works = by_ids(cands, SELECT)
        snow_works.extend(works)
        rows = screen(works)
        for r in rows:
            r["seed"], r["cocited_by"] = sid, cnt.get(r["id"], 0)
        snow[sid] = {"citers_read": len(cit), "complete": done, "candidates": len(cands),
                     "flagged": sum(1 for r in rows if r["flagged"]),
                     "sink_screen": sum(1 for r in rows if r.get("sink_screen"))}
        snow_rows.extend(rows)
    res["snowball"] = snow
    new = [r for r in snow_rows if r.get("sink_screen")]

    # Verification and mechanism for every screened sink (seeds included)
    ver = {}
    allw = {short_id(w["id"]): w for w in seeds + rnd + snow_works}
    for j, r in enumerate([x for x in seed_rows + rnd_rows + new if x.get("sink_screen")]):
        if r["id"] in ver or r["id"] not in allw:
            continue
        ver[r["id"]] = verify(allw[r["id"]], r["jump_year"], SEED + 10 + j)
    res["verification"] = {w: {kk: v[kk] for kk in ("target", "verdict", "crossref_openalex_ratio", "mechanism")}
                           for w, v in ver.items()}
    confirmed_new = [r["id"] for r in new if (ver.get(r["id"]) or {}).get("verdict", {}).get("verdict") == "confirmed"]
    res["H3"] = "supported" if confirmed_new else "not supported"
    res["H3_new_confirmed"] = confirmed_new
    res["H4_mechanism"] = dict(Counter(v["mechanism"] for w, v in ver.items()
                                       if v["verdict"]["verdict"] == "confirmed"))
    res["random_jump_distribution"] = dict(Counter(
        ">=25" if r["jump"] >= 25 else ">=8" if r["jump"] >= 8 else ">=4" if r["jump"] >= 4 else "<4" for r in rnd_rows))
    res["budget"] = {"openalex_calls": BUDGET.calls, "openalex_cost_usd": round(BUDGET.cost, 4),
                     "refused_over_cap": BUDGET.refused, "failed": BUDGET.failed}

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for name, rows in (("random_rows.jsonl", rnd_rows), ("snowball_rows.jsonl", snow_rows),
                       ("verification_reads.jsonl", [dict(r, target_id=w) for w, v in ver.items() for r in v["reads"]])):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: res[k] for k in ("H1", "random", "H2", "snowball", "H3", "H3_new_confirmed",
                                          "H4_mechanism", "budget")}, indent=1))


if __name__ == "__main__":
    main()
