# hindawi_sink.py - Does one record in each Hindawi journal-year collect OpenAlex citations meant for its other papers?
# Pre-registration: findings/hindawi-sink-prereg-v1-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public Crossref and OpenAlex APIs.
import argparse
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.parse

import article1_check as a1
import article1_mechanism as m
import openalex_article1 as oa1

SEED = 20261031
OLD, NEW = range(2016, 2020), range(2022, 2024)  # journal-years; NEW is the era after Microsoft Academic Graph ended (2021)
PILOT = {("S1010394304", 2017), ("S20935308", 2018)}  # BioMed Res Int 2017, Oxid Med Cell Longev 2018: seen before pre-registration
MIN_WORKS, TOP_K = 100, 25  # journal-years with 100+ OpenAlex works; their 25 most cited works in OpenAlex
MAX_OLD, MAX_NEW = 160, 80  # seeded sample of journal-years per era
ISSN_BATCH = 40
N_SINKS, N_READS = 8, 15
PAUSE = 0.2

# Pre-registered thresholds
ALPHA = 0.01
SINK_E, SINK_GAP, CONTROL_E = 10.0, 50, 2.0
MIN_ROWS = 10  # top works with a Crossref count, for a journal-year to be scored
H1_MIN_N, H1_SHARE = 30, 0.40
H2_MIN_N, H2_MAX = 30, 0.05
H3_MIN_N, H3_SHARE = 40, 0.70
CAL_MIN_N, CAL_SHARE = 30, 0.70
H4_MIN_N, H4_SHARE = 20, 0.80
H5_MIN_N, H5_MEDIAN = 10, 0.90
LAST_MAG_YEAR = 2021

DOI_RX = re.compile(r"^10\.1155/(\d{4})/\d+$")
ISSN_RX = re.compile(r"(\d{4}-\d{3}[\dX])")


def get_json(fetch, url):
    raw = fetch(url)
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    return data if isinstance(data, dict) else None


def doi_year(doi):
    x = DOI_RX.match((doi or "").strip().lower())
    return int(x.group(1)) if x else None


def issn_url(year):
    q = {"filter": "prefix:10.1155,type:journal-article,from-pub-date:%d-01-01,until-pub-date:%d-12-31" % (year, year),
         "facet": "issn:*", "rows": "0", "mailto": a1.MAILTO}
    return a1.CR.rstrip("/") + "?" + urllib.parse.urlencode(q)


def parse_issns(data):
    """Sorted ISSNs in a Crossref issn facet, or None if the response has none."""
    try:
        values = data["message"]["facets"]["issn"]["values"]
    except (KeyError, TypeError):
        return None
    out = set()
    for k in values or {}:
        x = ISSN_RX.search(str(k).upper())
        if x:
            out.add(x.group(1))
    return sorted(out)


def sources_url(year, issns):
    q = {"filter": "publication_year:%d,primary_location.source.issn:%s" % (year, "|".join(issns)),
         "group_by": "primary_location.source.id", "mailto": a1.MAILTO}
    return a1.OA + "?" + urllib.parse.urlencode(q)


def parse_groups(data):
    """[(short source id, name, works)] from an OpenAlex group_by response."""
    out = []
    for g in (data or {}).get("group_by") or []:
        sid = str(g.get("key") or "").rsplit("/", 1)[-1]
        if re.match(r"^S\d+$", sid):
            out.append((sid, g.get("key_display_name") or "", int(g.get("count") or 0)))
    return out


def journal_years(fetch, year, pause=0.0):
    """The OpenAlex journals holding Hindawi (10.1155) articles of one year, with their work counts."""
    info = {"issns": 0, "calls": 1, "failed_calls": 0}
    issns = parse_issns(get_json(fetch, issn_url(year)))
    if issns is None:
        info["failed_calls"] += 1
        return [], info
    info["issns"] = len(issns)
    found = {}
    for i in range(0, len(issns), ISSN_BATCH):
        info["calls"] += 1
        data = get_json(fetch, sources_url(year, issns[i:i + ISSN_BATCH]))
        if pause:
            time.sleep(pause)
        if data is None:
            info["failed_calls"] += 1
            continue
        for sid, name, n in parse_groups(data):
            if sid not in found or n > found[sid][1]:
                found[sid] = (name, n)
    return [{"source": s, "name": found[s][0], "year": year, "works": found[s][1]} for s in sorted(found)], info


def top_url(source, year):
    q = {"filter": "primary_location.source.id:%s,publication_year:%d" % (source, year), "sort": "cited_by_count:desc",
         "per-page": str(TOP_K), "select": "id,doi,cited_by_count,counts_by_year,title", "mailto": a1.MAILTO}
    return a1.OA + "?" + urllib.parse.urlencode(q)


def crossref_counts(fetch, dois):
    """{doi: is-referenced-by-count} for up to 50 DOIs in one Crossref call, or None if the call failed."""
    if not dois:
        return {}
    q = {"filter": ",".join("doi:" + d for d in dois), "rows": "50", "select": "DOI,is-referenced-by-count",
         "mailto": a1.MAILTO}
    data = get_json(fetch, a1.CR.rstrip("/") + "?" + urllib.parse.urlencode(q))
    try:
        items = data["message"]["items"]
    except (KeyError, TypeError):
        return None
    return {(w.get("DOI") or "").lower(): a1.cites(w) for w in items or [] if w.get("DOI")}


def to_2021(cby):
    """Share of the OpenAlex citations by year that are dated up to 2021, or None if there are none."""
    tot = sum(int(c.get("cited_by_count") or 0) for c in cby or [])
    old = sum(int(c.get("cited_by_count") or 0) for c in cby or [] if int(c.get("year") or 0) <= LAST_MAG_YEAR)
    return old / tot if tot else None


def rows_of(results, year, counts):
    """The top works whose DOI is a 10.1155 DOI of this year and which have a Crossref count."""
    out = []
    for w in results or []:
        d = oa1.norm_doi(w.get("doi"))
        if doi_year(d) != year or d not in counts:
            continue
        oa, cr = int(w.get("cited_by_count") or 0), counts[d]
        out.append({"doi": d, "oa_id": w.get("id") or "", "oa": oa, "cr": cr, "e": oa1.excess(oa, cr),
                    "to_2021": to_2021(w.get("counts_by_year")), "title": (w.get("title") or "")[:200]})
    return out


def judge(rows):
    """The journal-year's sink (the largest excess among works with excess >= 10 and OpenAlex - Crossref >= 50) and its control."""
    out = {"rows": len(rows), "sink": None, "control": None, "max_e": None, "second_e": None, "over": 0, "sink_rank": None}
    if not rows:
        return out
    by_e = sorted(rows, key=lambda r: (-r["e"], r["doi"]))
    out["max_e"] = by_e[0]["e"]
    out["second_e"] = by_e[1]["e"] if len(by_e) > 1 else None
    is_sink = [r for r in by_e if r["e"] >= SINK_E and r["oa"] - r["cr"] >= SINK_GAP]
    out["over"] = len(is_sink)
    if is_sink:
        out["sink"] = is_sink[0]
        by_oa = sorted(rows, key=lambda r: (-r["oa"], r["doi"]))
        out["sink_rank"] = [r["doi"] for r in by_oa].index(is_sink[0]["doi"]) + 1
    ctrl = [r for r in rows if r["e"] < CONTROL_E]
    if ctrl:
        out["control"] = min(ctrl, key=lambda r: (-r["oa"], r["doi"]))
    return out


def examine(fetch, jy, pause=0.0):
    """Add the journal-year's top works, their Crossref counts and the judgement. Returns the number of failed calls."""
    data = get_json(fetch, top_url(jy["source"], jy["year"]))
    if pause:
        time.sleep(pause)
    results = (data or {}).get("results")
    if results is None:
        jy["status"] = "openalex_failed"
        return 1
    dois = [d for d in (oa1.norm_doi(w.get("doi")) for w in results) if doi_year(d) == jy["year"]]
    counts = crossref_counts(fetch, dois)
    if pause:
        time.sleep(pause)
    if counts is None:
        jy["status"] = "crossref_failed"
        return 1
    rows = rows_of(results, jy["year"], counts)
    jy["status"] = "ok"
    jy["top"] = rows
    jy["judge"] = judge(rows)
    return 0


def scored(jys):
    return [j for j in jys if j.get("status") == "ok" and j["judge"]["rows"] >= MIN_ROWS
            and (j["source"], j["year"]) not in PILOT]


def sink_share(jys):
    k = sum(1 for j in jys if j["judge"]["sink"])
    return k, len(jys), m.rate(k, len(jys))


def score_h1(old):
    """H1: in 2016-2019, at least 40% of Hindawi journal-years have a sink."""
    k, n, r = sink_share(old)
    d = {"journal_years": n, "with_sink": k, "share": r}
    if n < H1_MIN_N:
        return "untestable", d
    return ("supported" if r >= H1_SHARE else "not supported"), d


def score_h2(old, new):
    """H2: in 2022-2023 sinks are rare (5% or fewer), and rarer than in 2016-2019."""
    ko, no, ro = sink_share(old)
    kn, nn, rn = sink_share(new)
    d = {"old": no, "old_with_sink": ko, "new": nn, "new_with_sink": kn, "new_share": rn}
    if no < H1_MIN_N or nn < H2_MIN_N:
        return "untestable", d
    d["p"] = m.fisher_greater(ko, no, kn, nn)
    return ("supported" if rn <= H2_MAX and d["p"] < ALPHA else "not supported"), d


def siblings(refs, target, names, year):
    """A citer's deposited references with first page "1" to another paper of the target's journal-year."""
    out = []
    for r in refs or []:
        d = (r.get("DOI") or "").strip().lower()
        if d == target or not m.page1(r):
            continue
        jt = r.get("journal-title")
        if d:
            if doi_year(d) == year and (not jt or m.same_journal(jt, names)):
                out.append(r)
        elif m.same_journal(jt, names) and str(year) in (str(r.get("volume") or "").strip(), str(r.get("year") or "").strip()):
            out.append(r)
    return out


def label_citer(msg, target, words, names, year):
    """(label, sibling references): genuine / sibling / unsupported / too_few_references / not_in_crossref."""
    if msg is None:
        return "not_in_crossref", []
    refs = msg.get("reference") or []
    if any((r.get("DOI") or "").strip().lower() == target for r in refs):
        return "genuine", []
    ws = set(words)
    need = max(2, (len(ws) + 1) // 2)
    for r in refs:
        text = " ".join(str(r.get(k) or "") for k in a1.TITLE_KEYS).lower()
        if ws and text.strip() and sum(1 for w in ws if w in text) >= need:
            return "genuine", []
    sib = siblings(refs, target, names, year)
    if sib:
        return "sibling", sib
    return ("unsupported" if len(refs) >= oa1.MIN_REFS else "too_few_references"), []


def read_citers(client, fetch, row, words, names, year, seed, role, n=N_READS):
    dois, returned = oa1.sample_citers(fetch, row["oa_id"], seed, n)
    out = []
    for d in dois:
        msg = client.work(d)
        label, sib = label_citer(msg, row["doi"], words, names, year)
        out.append({"role": role, "target": row["doi"], "target_oa_id": row["oa_id"], "citer": d, "label": label,
                    "year": m.year_of(msg), "siblings": [m.slim(x) for x in sib]})
    return out, returned


def annotate(reads, fetch):
    """For sibling citers: does OpenAlex link the target, and each sibling's own work?"""
    sib = [r for r in reads if r["label"] == "sibling"]
    works, c1, f1 = m.oa_refs(fetch, sorted({r["citer"] for r in sib}))
    ids, c2, f2 = oa1.openalex_works(fetch, sorted({x["DOI"].lower() for r in sib for x in r["siblings"] if x.get("DOI")}))
    for r in sib:
        w = works.get(r["citer"])
        r["oa_found"] = w is not None
        r["oa_has_target"] = (r["target_oa_id"] in w[1]) if w else None
        for x in r["siblings"]:
            d = (x.get("DOI") or "").lower()
            x["in_oa"] = (ids[d][0] in w[1]) if (w and d in ids) else None
    return {"citers": len(works), "calls": c1 + c2, "failed_calls": f1 + f2}


def score_h3(t_reads, c_reads):
    """H3: most sink citers that do not cite the sink cite a page-1 sibling instead (classifier calibrated on controls)."""
    t = [r for r in t_reads if r["label"] in ("sibling", "unsupported")]
    c = [r for r in c_reads if r["label"] in ("genuine", "sibling", "unsupported")]
    a, g = sum(1 for r in t if r["label"] == "sibling"), sum(1 for r in c if r["label"] == "genuine")
    d = {"readable": len(t), "sibling": a, "share": m.rate(a, len(t)), "control_readable": len(c),
         "control_genuine": g, "control_share": m.rate(g, len(c)),
         "sink_genuine": sum(1 for r in t_reads if r["label"] == "genuine")}
    if len(c) < CAL_MIN_N or d["control_share"] < CAL_SHARE:
        return "untestable (classifier failed calibration)", d
    if len(t) < H3_MIN_N:
        return "untestable", d
    return ("supported" if d["share"] >= H3_SHARE else "not supported"), d


def score_h4(t_reads):
    """H4: OpenAlex keeps the link to the sibling actually cited (the sink's link is added, not swapped)."""
    xs = [x for r in t_reads if r["label"] == "sibling" for x in r["siblings"] if x.get("in_oa") is not None]
    k = sum(1 for x in xs if x["in_oa"])
    d = {"references": len(xs), "kept": k, "share": m.rate(k, len(xs))}
    if len(xs) < H4_MIN_N:
        return "untestable", d
    return ("supported" if d["share"] >= H4_SHARE else "not supported"), d


def score_h5(old):
    """H5: a sink's OpenAlex citations are dated up to 2021, more so than its control's."""
    pairs = [(j["judge"]["sink"]["to_2021"], j["judge"]["control"]["to_2021"]) for j in old
             if j["judge"]["sink"] and j["judge"]["control"]
             and j["judge"]["sink"]["to_2021"] is not None and j["judge"]["control"]["to_2021"] is not None]
    pos, neg = sum(1 for s, c in pairs if s > c), sum(1 for s, c in pairs if s < c)
    d = {"pairs": len(pairs), "sink_higher": pos, "control_higher": neg}
    if len(pairs) < H5_MIN_N:
        return "untestable", d
    d["p"] = a1.sign_test(pos, neg)
    d["median_sink"] = statistics.median(s for s, _ in pairs)
    d["median_control"] = statistics.median(c for _, c in pairs)
    return ("supported" if d["p"] < ALPHA and d["median_sink"] >= H5_MEDIAN else "not supported"), d


def describe(jys):
    out = {}
    for y in sorted({j["year"] for j in jys}):
        js = scored([j for j in jys if j["year"] == y])
        sinks = [j["judge"]["sink"] for j in js if j["judge"]["sink"]]
        out[str(y)] = {"journal_years": len(js), "with_sink": len(sinks),
                       "phantom_citations": sum(s["oa"] - s["cr"] for s in sinks),
                       "multiple_over_threshold": sum(1 for j in js if j["judge"]["over"] > 1),
                       "sink_rank_1": sum(1 for j in js if j["judge"]["sink_rank"] == 1)}
    return out


def pick(pool, n, seed):
    pool = sorted(pool, key=lambda j: (j["year"], j["source"]))
    return random.Random(seed).sample(pool, min(n, len(pool)))


def run(fetch, out_dir, pause=0.0, max_old=MAX_OLD, max_new=MAX_NEW, n_sinks=N_SINKS, n_reads=N_READS):
    os.makedirs(out_dir, exist_ok=True)
    res = {"seed": SEED, "old": [OLD[0], OLD[-1]], "new": [NEW[0], NEW[-1]], "listing": {}, "failed_examinations": 0}
    pools = {"old": [], "new": []}
    pilot = []
    for era, years in (("old", OLD), ("new", NEW)):
        for y in years:
            jys, info = journal_years(fetch, y, pause)
            info["journals"], info["eligible"] = len(jys), sum(1 for j in jys if j["works"] >= MIN_WORKS)
            res["listing"][str(y)] = info
            for j in jys:
                if j["works"] < MIN_WORKS:
                    continue
                (pilot if (j["source"], y) in PILOT else pools[era]).append(j)
    res["pool"] = {k: len(v) for k, v in pools.items()}
    chosen = {"old": pick(pools["old"], max_old, SEED), "new": pick(pools["new"], max_new, SEED + 1)}
    for j in chosen["old"] + chosen["new"] + pilot:
        res["failed_examinations"] += examine(fetch, j, pause)
    sys.stderr.write("examined %d old, %d new, %d pilot journal-years (%d failed)\n"
                     % (len(chosen["old"]), len(chosen["new"]), len(pilot), res["failed_examinations"]))
    old, new = scored(chosen["old"]), scored(chosen["new"])
    res["H1"], res["H1_detail"] = score_h1(old)
    res["H2"], res["H2_detail"] = score_h2(old, new)
    res["H5"], res["H5_detail"] = score_h5(old)

    client = a1.Client(fetch, pause=0.05 if pause else 0.0)
    t_reads, c_reads, targets = [], [], []
    with_sink = sorted((j for j in old if j["judge"]["sink"]), key=lambda j: j["judge"]["sink"]["doi"])
    for i, j in enumerate(random.Random(SEED + 2).sample(with_sink, min(n_sinks, len(with_sink)))):
        s, c = j["judge"]["sink"], j["judge"]["control"]
        msg = client.work(s["doi"])
        info = {"source": j["source"], "name": j["name"], "year": j["year"], "sink": s["doi"], "oa": s["oa"], "cr": s["cr"],
                "control": c["doi"] if c else None}
        targets.append(info)
        if msg is None:
            info["status"] = "not_in_crossref"
            continue
        names = m.journal_names(msg)
        info["journal_names"] = [" ".join(x) for x in names]
        r1, info["sink_sample"] = read_citers(client, fetch, s, a1.title_words((msg.get("title") or [""])[0]), names,
                                              j["year"], SEED + 10 + i, "sink", n_reads)
        t_reads += r1
        if c:
            cmsg = client.work(c["doi"]) or {}
            r2, info["control_sample"] = read_citers(client, fetch, c, a1.title_words((cmsg.get("title") or [""])[0]),
                                                     names, j["year"], SEED + 100 + i, "control", n_reads)
            c_reads += r2
    res["reads"] = {"targets": targets, "crossref_calls": client.calls, "openalex": annotate(t_reads, fetch)}
    res["H3"], res["H3_detail"] = score_h3(t_reads, c_reads)
    res["H4"], res["H4_detail"] = score_h4(t_reads)
    res["labels"] = {role: {} for role in ("sink", "control")}
    for r in t_reads + c_reads:
        res["labels"][r["role"]][r["label"]] = res["labels"][r["role"]].get(r["label"], 0) + 1
    res["descriptive"] = describe(chosen["old"] + chosen["new"])
    res["pilot"] = [{"source": j["source"], "name": j["name"], "year": j["year"], "status": j.get("status"),
                     "sink": (j.get("judge") or {}).get("sink")} for j in pilot]

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "journal_years.jsonl"), "w", encoding="utf-8") as f:
        for j in chosen["old"] + chosen["new"] + pilot:
            f.write(json.dumps(dict(j, era="pilot" if (j["source"], j["year"]) in PILOT
                                    else ("old" if j["year"] in OLD else "new")), ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "reads.jsonl"), "w", encoding="utf-8") as f:
        for r in t_reads + c_reads:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    res = run(a1.get_patient, a.out_dir, PAUSE)
    print(json.dumps({k: v for k, v in res.items() if k not in ("pilot",)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
