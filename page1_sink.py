# page1_sink.py - Outside Hindawi, does one record per page-reset journal-year collect OpenAlex citations meant for its other papers?
# Pre-registration: findings/page1-sink-prereg-v1-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public Crossref and OpenAlex APIs.
import argparse
import json
import os
import random
import sys
import time
import urllib.parse

import article1_check as a1
import article1_mechanism as m
import hindawi_sink as h
import openalex_article1 as oa1

SEED = 20261107
OLD, NEW = h.OLD, h.NEW  # 2016-2019 (Microsoft Academic Graph era) and 2022-2023
TOP_K = h.TOP_K  # the 25 most cited works in OpenAlex per journal-year
MIN_PAGE1, MIN_SHARE = 100, 0.80  # journal-years with 100+ first-page-"1" articles, at least 80% of their articles
MAX_OLD, MAX_NEW = 160, 80
N_SINKS, N_READS = 8, 15
PAUSE = 0.2
HINDAWI = "10.1155/"  # studied on its own (hindawi_sink.py)
HINDAWI_ORG = "P4310319869"  # OpenAlex publisher Hindawi Publishing Corporation
SOURCE_BATCH = 50
TOP_SINKS = 25
TITLE_LEN = 120
MAX_FAILED = 0.10  # more failed examinations than this voids the run (re-run unchanged on another day)

# Pre-registered thresholds (H2-H5 and the sink rule are hindawi_sink.py's)
MIN_ROWS = h.MIN_ROWS
H1_MIN_N, H1_SHARE = 30, 0.25


def groups_url(year):
    """The journals with the most first-page-"1" articles in one year (OpenAlex returns the top 200), Hindawi left out."""
    q = {"filter": "publication_year:%d,type:article,primary_location.source.type:journal,biblio.first_page:1,"
                   "primary_location.source.host_organization:!%s" % (year, HINDAWI_ORG),
         "group_by": "primary_location.source.id", "mailto": a1.MAILTO}
    return a1.OA + "?" + urllib.parse.urlencode(q)


def totals_url(year, sources):
    q = {"filter": "publication_year:%d,type:article,primary_location.source.id:%s" % (year, "|".join(sources)),
         "group_by": "primary_location.source.id", "mailto": a1.MAILTO}
    return a1.OA + "?" + urllib.parse.urlencode(q)


def journal_years(fetch, year, pause=0.0):
    """Journals of one year whose articles nearly all start at page 1 (Hindawi set aside), with their counts."""
    info = {"groups": 0, "eligible_groups": 0, "calls": 1, "failed_calls": 0, "no_total": 0, "low_share": 0, "candidates": 0}
    data = h.get_json(fetch, groups_url(year))
    if data is None:
        info["failed_calls"] += 1
        return [], info
    groups = h.parse_groups(data)
    info["groups"] = len(groups)
    eligible = [g for g in groups if g[2] >= MIN_PAGE1]
    info["eligible_groups"] = len(eligible)
    totals = {}
    for i in range(0, len(eligible), SOURCE_BATCH):
        info["calls"] += 1
        data = h.get_json(fetch, totals_url(year, [g[0] for g in eligible[i:i + SOURCE_BATCH]]))
        if pause:
            time.sleep(pause)
        if data is None:
            info["failed_calls"] += 1
            continue
        for sid, _, n in h.parse_groups(data):
            totals[sid] = n
    out = []
    for sid, name, p1 in eligible:
        n = totals.get(sid)
        if not n:
            info["no_total"] += 1
            continue
        if p1 / n < MIN_SHARE:
            info["low_share"] += 1
            continue
        out.append({"source": sid, "name": name, "year": year, "works": n, "page1": p1, "page1_share": p1 / n})
    info["candidates"] = len(out)
    return out, info


def top_url(source, year):
    q = {"filter": "primary_location.source.id:%s,publication_year:%d" % (source, year), "sort": "cited_by_count:desc",
         "per-page": str(TOP_K), "select": "id,doi,cited_by_count,counts_by_year,title,biblio", "mailto": a1.MAILTO}
    return a1.OA + "?" + urllib.parse.urlencode(q)


def prefix_of(dois):
    """The most common DOI prefix (ties: the lowest), or "" if there are none."""
    n = {}
    for d in dois:
        p = d.split("/", 1)[0]
        n[p] = n.get(p, 0) + 1
    return min(n, key=lambda p: (-n[p], p)) if n else ""


def rows_of(results, counts):
    """The top works with a DOI that Crossref returns, with their OpenAlex volume."""
    out = []
    for w in results or []:
        d = oa1.norm_doi(w.get("doi"))
        if not d or d not in counts:
            continue
        oa, cr = int(w.get("cited_by_count") or 0), counts[d]
        out.append({"doi": d, "oa_id": w.get("id") or "", "oa": oa, "cr": cr, "e": oa1.excess(oa, cr),
                    "to_2021": h.to_2021(w.get("counts_by_year")), "volume": str((w.get("biblio") or {}).get("volume") or "").strip(),
                    "title": (w.get("title") or "")[:TITLE_LEN]})
    return out


def examine(fetch, jy, pause=0.0):
    """Add the journal-year's top works, their Crossref counts and the judgement. Returns the number of failed calls."""
    data = h.get_json(fetch, top_url(jy["source"], jy["year"]))
    if pause:
        time.sleep(pause)
    results = (data or {}).get("results")
    if results is None:
        jy["status"] = "openalex_failed"
        return 1
    dois = []
    for w in results:
        d = oa1.norm_doi(w.get("doi"))
        if d and d not in dois:
            dois.append(d)
    if 2 * sum(1 for d in dois if d.startswith(HINDAWI)) > len(dois):
        jy["status"] = "hindawi"
        return 0
    counts = h.crossref_counts(fetch, dois)
    if pause:
        time.sleep(pause)
    if counts is None:
        jy["status"] = "crossref_failed"
        return 1
    rows = rows_of(results, counts)
    jy.update(status="ok", top=rows, judge=h.judge(rows), prefix=prefix_of(r["doi"] for r in rows))
    return 0


def scored(jys):
    return [j for j in jys if j.get("status") == "ok" and j["judge"]["rows"] >= MIN_ROWS]


def score_h1(old):
    """H1: in 2016-2019, at least 25% of page-reset journal-years outside Hindawi have a sink."""
    k, n, r = h.sink_share(old)
    d = {"journal_years": n, "with_sink": k, "share": r}
    if n < H1_MIN_N:
        return "untestable", d
    return ("supported" if r >= H1_SHARE else "not supported"), d


def oa_places(fetch, dois, per=50):
    """{doi: (OpenAlex id, source id, volume)}; the first work listed wins a shared DOI."""
    out, calls, failed = {}, 0, 0
    for i in range(0, len(dois), per):
        calls += 1
        data = h.get_json(fetch, a1.OA + "?" + urllib.parse.urlencode(
            {"filter": "doi:" + "|".join(dois[i:i + per]), "per-page": "200", "select": "id,doi,primary_location,biblio",
             "mailto": a1.MAILTO}))
        if data is None:
            failed += 1
            continue
        for w in data.get("results") or []:
            d = oa1.norm_doi(w.get("doi"))
            src = str((((w.get("primary_location") or {}).get("source") or {}).get("id")) or "").rsplit("/", 1)[-1]
            if d and d not in out:
                out[d] = (w.get("id") or "", src, str((w.get("biblio") or {}).get("volume") or "").strip())
    return out, calls, failed


def is_sibling(ref, source, volume, names, works):
    """A page-1 reference to another paper of the same journal and volume: by OpenAlex's record of its DOI, or (no DOI)
    by journal-title and volume."""
    if not volume:
        return False
    d = (ref.get("DOI") or "").strip().lower()
    if d:
        w = works.get(d)
        return bool(w) and w[1] == source and w[2] == volume
    return m.same_journal(ref.get("journal-title"), names) and str(ref.get("volume") or "").strip() == volume


def label_citer(msg, target, words):
    """First pass: (label, page-1 references); label is genuine / candidate / unsupported / too_few_references / not_in_crossref."""
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
    p1 = [r for r in refs if m.page1(r) and (r.get("DOI") or "").strip().lower() != target]
    if p1:
        return "candidate", p1
    return ("unsupported" if len(refs) >= oa1.MIN_REFS else "too_few_references"), []


def read_citers(client, fetch, row, words, names, source, seed, role, n=N_READS):
    """Read a seeded sample of row's OpenAlex citers; a candidate becomes sibling if a page-1 reference is a sibling."""
    dois, returned = oa1.sample_citers(fetch, row["oa_id"], seed, n)
    first = []
    for d in dois:
        msg = client.work(d)
        label, p1 = label_citer(msg, row["doi"], words)
        first.append((d, msg, label, p1))
    look = sorted({(x.get("DOI") or "").strip().lower() for _, _, _, p1 in first for x in p1} - {""})
    works, calls, failed = oa_places(fetch, look)
    out = []
    for d, msg, label, p1 in first:
        sib = [x for x in p1 if is_sibling(x, source, row["volume"], names, works)]
        if label == "candidate":
            label = "sibling" if sib else ("unsupported" if len(msg.get("reference") or []) >= oa1.MIN_REFS
                                           else "too_few_references")
        out.append({"role": role, "target": row["doi"], "target_oa_id": row["oa_id"], "citer": d, "label": label,
                    "year": m.year_of(msg),
                    "siblings": [dict(m.slim(x), oa_id=works.get((x.get("DOI") or "").strip().lower(), ("",))[0])
                                 for x in sib]})
    return out, {"returned": returned, "lookup_calls": calls, "failed_lookup_calls": failed}


def annotate(reads, fetch):
    """For sibling citers: does OpenAlex link the target, and each sibling's own work?"""
    sib = [r for r in reads if r["label"] == "sibling"]
    works, calls, failed = m.oa_refs(fetch, sorted({r["citer"] for r in sib}))
    for r in sib:
        w = works.get(r["citer"])
        r["oa_found"] = w is not None
        r["oa_has_target"] = (r["target_oa_id"] in w[1]) if w else None
        for x in r["siblings"]:
            x["in_oa"] = (x["oa_id"] in w[1]) if (w and x.get("oa_id")) else None
    return {"citers": len(works), "calls": calls, "failed_calls": failed}


def describe(jys):
    out = {"by_year": {}, "by_prefix_old": {}, "top_sinks": []}
    for y in sorted({j["year"] for j in jys}):
        js = scored([j for j in jys if j["year"] == y])
        sinks = [j["judge"]["sink"] for j in js if j["judge"]["sink"]]
        out["by_year"][str(y)] = {"journal_years": len(js), "with_sink": len(sinks),
                                  "phantom_citations": sum(s["oa"] - s["cr"] for s in sinks),
                                  "multiple_over_threshold": sum(1 for j in js if j["judge"]["over"] > 1),
                                  "sink_rank_1": sum(1 for j in js if j["judge"]["sink_rank"] == 1)}
    for j in scored([j for j in jys if j["year"] in OLD]):
        p = out["by_prefix_old"].setdefault(j["prefix"], {"journal_years": 0, "with_sink": 0, "phantom_citations": 0})
        p["journal_years"] += 1
        s = j["judge"]["sink"]
        if s:
            p["with_sink"] += 1
            p["phantom_citations"] += s["oa"] - s["cr"]
    sinks = [(j, j["judge"]["sink"]) for j in scored(jys) if j["judge"]["sink"]]
    sinks.sort(key=lambda t: (-(t[1]["oa"] - t[1]["cr"]), t[1]["doi"]))
    out["top_sinks"] = [{"source": j["source"], "name": j.get("name", ""), "year": j["year"], "doi": s["doi"], "oa": s["oa"],
                         "cr": s["cr"], "title": s.get("title", "")} for j, s in sinks[:TOP_SINKS]]
    return out


def run(fetch, out_dir, pause=0.0, max_old=MAX_OLD, max_new=MAX_NEW, n_sinks=N_SINKS, n_reads=N_READS):
    os.makedirs(out_dir, exist_ok=True)
    res = {"seed": SEED, "old": [OLD[0], OLD[-1]], "new": [NEW[0], NEW[-1]], "listing": {}, "failed_examinations": 0}
    pools = {"old": [], "new": []}
    for era, years in (("old", OLD), ("new", NEW)):
        for y in years:
            jys, info = journal_years(fetch, y, pause)
            res["listing"][str(y)] = info
            pools[era] += jys
    res["pool"] = {k: len(v) for k, v in pools.items()}
    chosen = {"old": h.pick(pools["old"], max_old, SEED), "new": h.pick(pools["new"], max_new, SEED + 1)}
    for j in chosen["old"] + chosen["new"]:
        res["failed_examinations"] += examine(fetch, j, pause)
    res["status"] = {}
    for j in chosen["old"] + chosen["new"]:
        res["status"][j["status"]] = res["status"].get(j["status"], 0) + 1
    examined = len(chosen["old"]) + len(chosen["new"])
    res["void"] = (any(i["failed_calls"] for i in res["listing"].values())
                   or res["failed_examinations"] > MAX_FAILED * examined)
    sys.stderr.write("examined %d old, %d new journal-years (%d failed)\n"
                     % (len(chosen["old"]), len(chosen["new"]), res["failed_examinations"]))
    old, new = scored(chosen["old"]), scored(chosen["new"])
    res["H1"], res["H1_detail"] = score_h1(old)
    res["H2"], res["H2_detail"] = h.score_h2(old, new)
    res["H5"], res["H5_detail"] = h.score_h5(old)

    client = a1.Client(fetch, pause=0.05 if pause else 0.0)
    t_reads, c_reads, targets = [], [], []
    with_sink = sorted((j for j in old if j["judge"]["sink"]), key=lambda j: j["judge"]["sink"]["doi"])
    for i, j in enumerate(random.Random(SEED + 2).sample(with_sink, min(n_sinks, len(with_sink)))):
        s, c = j["judge"]["sink"], j["judge"]["control"]
        msg = client.work(s["doi"])
        info = {"source": j["source"], "name": j["name"], "year": j["year"], "sink": s["doi"], "oa": s["oa"], "cr": s["cr"],
                "volume": s["volume"], "control": c["doi"] if c else None}
        targets.append(info)
        if msg is None:
            info["status"] = "not_in_crossref"
            continue
        names = m.journal_names(msg)
        info["journal_names"] = [" ".join(x) for x in names]
        r1, info["sink_sample"] = read_citers(client, fetch, s, a1.title_words((msg.get("title") or [""])[0]), names,
                                              j["source"], SEED + 10 + i, "sink", n_reads)
        t_reads += r1
        if c:
            cmsg = client.work(c["doi"]) or {}
            r2, info["control_sample"] = read_citers(client, fetch, c, a1.title_words((cmsg.get("title") or [""])[0]),
                                                     names, j["source"], SEED + 100 + i, "control", n_reads)
            c_reads += r2
    res["reads"] = {"targets": targets, "crossref_calls": client.calls, "openalex": annotate(t_reads, fetch)}
    res["H3"], res["H3_detail"] = h.score_h3(t_reads, c_reads)
    res["H4"], res["H4_detail"] = h.score_h4(t_reads)
    res["labels"] = {role: {} for role in ("sink", "control")}
    for r in t_reads + c_reads:
        res["labels"][r["role"]][r["label"]] = res["labels"][r["role"]].get(r["label"], 0) + 1
    res["descriptive"] = describe(chosen["old"] + chosen["new"])

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "journal_years.jsonl"), "w", encoding="utf-8") as f:
        for j in chosen["old"] + chosen["new"]:
            f.write(json.dumps(dict(j, era="old" if j["year"] in OLD else "new"), ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "reads.jsonl"), "w", encoding="utf-8") as f:
        for r in t_reads + c_reads:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    res = run(a1.get_patient, a.out_dir, PAUSE)
    print(json.dumps({k: v for k, v in res.items() if k != "descriptive"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
