# article1_mechanism.py - How do MDPI and Frontiers article-1 records gain OpenAlex citations their citers never made?
# Pre-registration: findings/article-number-1-mechanism-prereg-v1-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads article1_openalex_v2_units_oa.jsonl and the public Crossref, OpenCitations and OpenAlex APIs.
import argparse
import json
import math
import os
import random
import re
import sys
import urllib.parse

import article1_check as a1
import openalex_article1 as oa1

SEED = 20261025
YEARS = range(2016, 2020)  # volume years 2016-2019, as v2's H1
DONE = {"10.3389/fpls.2016.00001", "10.3389/fmicb.2016.00001", "10.3390/su8010001"}  # v2's H4 targets, already read
MIN_GAP = 50  # a target's OpenAlex minus Crossref citations
N_TARGETS, N_READS, MIN_OC = 8, 25, 5
NEW_ERA = 2022  # descriptive split by the citer's year: up to 2021 / 2022 on
STOPWORDS = {"in", "of", "the", "and", "for", "on"}

# Pre-registered thresholds
ALPHA = 0.01
H1_MIN_N, H1_MIN_C, H1_SHARE, H1_RATIO = 40, 20, 0.70, 2.0
H2_MIN_N, H2_RATE, H2_RATIO = 15, 0.30, 3.0
H3_MIN_N, H3_SHARE = 20, 0.80

REF_KEYS = ("key", "DOI", "doi-asserted-by", "journal-title", "volume", "first-page", "year", "author")


def tokens(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOPWORDS]


def journal_names(msg):
    """Token lists of a record's journal names (full and short), from Crossref."""
    out = []
    for k in ("container-title", "short-container-title"):
        for t in msg.get(k) or []:
            n = tokens(t)
            if n and n not in out:
                out.append(n)
    return out


def same_journal(title, names):
    """A reference's journal-title names the journal: the same tokens, or each token a prefix of a name's ("Front Plant Sci")."""
    t = tokens(title)
    return bool(t) and any(len(n) == len(t) and all(f.startswith(x) for x, f in zip(t, n)) for n in names)


def volume_regex(unit):
    """The DOI pattern of every article in the unit's volume."""
    if unit["publisher"] == "MDPI":
        return re.compile(r"^10\.3390/%s%s\d{6}$" % (re.escape(unit["journal"]), unit["volume"]))
    return re.compile(r"^10\.3389/%s\.%d\.\d{5}$" % (re.escape(unit["journal"]), unit["year"]))


def same_volume(ref, unit, names, rx):
    """The deposited reference points into the unit's volume: by its DOI, or (no DOI) by journal-title and volume."""
    d = (ref.get("DOI") or "").lower()
    if d:
        return bool(rx.match(d))
    return str(ref.get("volume") or "").strip() == str(unit["volume"]) and same_journal(ref.get("journal-title"), names)


def page1(ref):
    return str(ref.get("first-page") or "").strip() == "1"


def page1_refs(msg, unit, names, rx, exclude):
    """The deposited references into the unit's volume with first page "1", other than those whose DOI is in exclude."""
    return [r for r in (msg or {}).get("reference") or []
            if (r.get("DOI") or "").lower() not in exclude and page1(r) and same_volume(r, unit, names, rx)]


def slim(ref):
    return {k: str(ref[k])[:200] for k in REF_KEYS if k in ref}


def year_of(msg):
    parts = (((msg or {}).get("issued") or {}).get("date-parts") or [[None]])[0]
    return parts[0] if parts and isinstance(parts[0], int) else None


def is_top(u):
    """Article 1 has a larger OpenAlex excess than every far control (v2's H1 'top'; at least 10 controls)."""
    a, far = u["rows"][0], [r for r in u["rows"][1:] if r.get("oa") is not None]
    if a.get("oa") is None or len(far) < oa1.MIN_FAR:
        return False
    return oa1.excess(a["oa"], a["cites"]) > max(oa1.excess(r["oa"], r["cites"]) for r in far)


def pick_targets(units, n=N_TARGETS, seed=SEED):
    """A seeded sample of v2's 'top' 2016-2019 units not read before, whose article 1 has OpenAlex - Crossref >= 50."""
    pool = [u for u in units if u["confirmatory"] and u["publisher"] in ("MDPI", "Frontiers") and u["year"] in YEARS
            and is_top(u) and u["rows"][0]["doi"] not in DONE and u["rows"][0].get("oa_id")
            and u["rows"][0]["oa"] - u["rows"][0]["cites"] >= MIN_GAP]
    pool.sort(key=lambda u: u["rows"][0]["doi"])
    return random.Random(seed).sample(pool, min(n, len(pool))), len(pool)


def control_of(u):
    """The far control with the most Crossref citations (ties: lowest DOI)."""
    return min(u["rows"][1:], key=lambda r: (-r["cites"], r["doi"]))


def read_target(client, fetch, unit, trow, names, rx, seed, n=N_READS):
    """A seeded sample of article 1's OpenAlex citers; for each unsupported one, its page-1 references into the volume."""
    dois, returned = oa1.sample_citers(fetch, trow["oa_id"], seed, n)
    words = a1.title_words(trow["title"])
    out = []
    for d in dois:
        msg = client.work(d)
        label, _ = oa1.classify_citer(msg, trow["doi"], words, trow["first_author"])
        r = {"target": trow["doi"], "target_oa_id": trow["oa_id"], "citer": d, "label": label, "year": year_of(msg)}
        if label == "unsupported":
            refs = msg.get("reference") or []
            r["crossref_refs"] = len(refs)
            r["same_volume"] = sum(1 for x in refs if same_volume(x, unit, names, rx))
            r["page1"] = [slim(x) for x in page1_refs(msg, unit, names, rx, {trow["doi"]})]
        out.append(r)
    return out, returned


def control_citers(fetch, ctrl, seed, n=N_READS):
    """(DOIs, source, pool size): a seeded sample of OpenCitations citers, or OpenAlex's if OpenCitations has under 5."""
    dois = a1.parse_oc(fetch(a1.OC + ctrl["doi"]))
    if len(dois) >= MIN_OC:
        return random.Random(seed).sample(dois, min(n, len(dois))), "opencitations", len(dois)
    got, returned = oa1.sample_citers(fetch, ctrl["oa_id"], seed, n)
    return got, "openalex", returned


def read_control(client, fetch, unit, ctrl, trow, names, rx, seed, n=N_READS):
    """Citers of a same-volume control: the first page of their reference to it, and their other page-1 references."""
    dois, source, pool = control_citers(fetch, ctrl, seed, n)
    words = a1.title_words(trow["title"])
    out = []
    for d in dois:
        msg = client.work(d)
        r = {"control": ctrl["doi"], "article1": trow["doi"], "article1_oa_id": trow["oa_id"], "citer": d,
             "source": source, "year": year_of(msg)}
        own = [x for x in (msg or {}).get("reference") or [] if (x.get("DOI") or "").lower() == ctrl["doi"].lower()]
        if msg is None:
            r["status"] = "not_in_crossref"
        elif not own:
            r["status"] = "no_matching_reference"
        elif oa1.classify_citer(msg, trow["doi"], words, trow["first_author"])[0] not in ("unsupported", "too_few_references"):
            r["status"] = "cites_article1"
        else:
            r["status"] = "found"
            r["control_ref"] = slim(own[0])
            r["control_page1"] = page1(own[0])
            r["other_page1"] = len(page1_refs(msg, unit, names, rx, {ctrl["doi"].lower(), trow["doi"].lower()}))
        out.append(r)
    return out, {"source": source, "pool": pool, "read": len(dois)}


def oa_refs(fetch, dois, per=25):
    """{doi: (OpenAlex id, set of referenced work ids)}; a shared DOI keeps the work with more references."""
    out, calls, failed = {}, 0, 0
    for i in range(0, len(dois), per):
        calls += 1
        raw = fetch(a1.OA + "?" + urllib.parse.urlencode({"filter": "doi:" + "|".join(dois[i:i + per]), "per-page": "200",
                                                          "select": "id,doi,referenced_works", "mailto": a1.MAILTO}))
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        if not isinstance(data, dict):
            failed += 1
            continue
        for w in data.get("results") or []:
            d, refs = oa1.norm_doi(w.get("doi")), set(w.get("referenced_works") or [])
            if d and (d not in out or len(refs) > len(out[d][1])):
                out[d] = (w.get("id") or "", refs)
    return out, calls, failed


def annotate(t_reads, c_reads, works, ids):
    """Add what OpenAlex links: the target, each page-1 reference's own work, and (controls) article 1."""
    for r in t_reads:
        if r["label"] != "unsupported":
            continue
        w = works.get(r["citer"])
        r["oa_found"] = w is not None
        if not w:
            continue
        r["oa_refs"], r["oa_has_target"] = len(w[1]), r["target_oa_id"] in w[1]
        for x in r["page1"]:
            d = (x.get("DOI") or "").lower()
            x["in_oa"] = (ids[d][0] in w[1]) if d in ids else None
    for r in c_reads:
        if r.get("status") == "found":
            w = works.get(r["citer"])
            r["oa_article1"] = (r["article1_oa_id"] in w[1]) if w else None


def fisher_greater(a, n1, b, n2):
    """One-sided Fisher exact P that group 1 has a or more of the a + b successes, given the group sizes."""
    k, n = a + b, n1 + n2
    return sum(math.comb(k, x) * math.comb(n - k, n1 - x) for x in range(a, min(k, n1) + 1)) / math.comb(n, n1)


def rate(k, n):
    return k / n if n else None


def score_h1(t_reads, c_reads):
    """H1: unsupported citers of article 1 nearly always deposit a page-1 reference into its volume, controls' citers rarely."""
    t = [r for r in t_reads if r["label"] == "unsupported"]
    c = [r for r in c_reads if r.get("status") == "found"]
    a, b = sum(1 for r in t if r["page1"]), sum(1 for r in c if r["other_page1"])
    d = {"unsupported": len(t), "with_page1": a, "share": rate(a, len(t)),
         "control_citers": len(c), "control_with_other_page1": b, "control_share": rate(b, len(c))}
    if len(t) < H1_MIN_N or len(c) < H1_MIN_C:
        return "untestable", d
    d["p"] = fisher_greater(a, len(t), b, len(c))
    ok = d["share"] >= H1_SHARE and d["share"] >= H1_RATIO * d["control_share"] and d["p"] < ALPHA
    return ("supported" if ok else "not supported"), d


def h2_groups(c_reads, years=None):
    c = [r for r in c_reads if r.get("status") == "found" and not r["other_page1"] and r.get("oa_article1") is not None
         and (years is None or (r["year"] is not None and r["year"] in years))]
    return [r for r in c if r["control_page1"]], [r for r in c if not r["control_page1"]]


def h2_detail(g1, g0):
    a, b = sum(1 for r in g1 if r["oa_article1"]), sum(1 for r in g0 if r["oa_article1"])
    return {"page1": len(g1), "page1_linked": a, "page1_rate": rate(a, len(g1)),
            "other": len(g0), "other_linked": b, "other_rate": rate(b, len(g0))}


def score_h2(c_reads):
    """H2: a reference to a same-volume paper with first page "1" makes OpenAlex also link the citer to article 1."""
    g1, g0 = h2_groups(c_reads)
    d = h2_detail(g1, g0)
    if len(g1) < H2_MIN_N or len(g0) < H2_MIN_N:
        return "untestable", d
    d["p"] = fisher_greater(d["page1_linked"], len(g1), d["other_linked"], len(g0))
    ok = d["page1_rate"] >= H2_RATE and d["page1_rate"] >= H2_RATIO * d["other_rate"] and d["p"] < ALPHA
    return ("supported" if ok else "not supported"), d


def score_h3(t_reads):
    """H3: the link to article 1 is added, not swapped: OpenAlex still links the page-1 reference's own work."""
    xs = [x for r in t_reads if r["label"] == "unsupported" and r.get("oa_found")
          for x in r["page1"] if x.get("in_oa") is not None]
    k = sum(1 for x in xs if x["in_oa"])
    d = {"references": len(xs), "kept": k, "share": rate(k, len(xs))}
    if len(xs) < H3_MIN_N:
        return "untestable", d
    return ("supported" if d["share"] >= H3_SHARE else "not supported"), d


def describe(t_reads, c_reads):
    t = [r for r in t_reads if r["label"] == "unsupported"]
    f = [r for r in t if r.get("oa_found")]
    p1 = [x for r in t for x in r["page1"]]
    out = {"target_labels": {}, "control_status": {},
           "unsupported_years": {"to_2021": sum(1 for r in t if r["year"] is not None and r["year"] < NEW_ERA),
                                 "from_2022": sum(1 for r in t if r["year"] is not None and r["year"] >= NEW_ERA),
                                 "unknown": sum(1 for r in t if r["year"] is None)},
           "unsupported_in_openalex": len(f), "openalex_links_target": sum(1 for r in f if r["oa_has_target"]),
           "page1_refs": len(p1), "page1_refs_with_doi": sum(1 for x in p1 if x.get("DOI")),
           "unsupported_with_same_volume_ref": sum(1 for r in t if r["same_volume"]),
           "median_openalex_minus_crossref_refs": None,
           "h2_to_2021": h2_detail(*h2_groups(c_reads, range(0, NEW_ERA))),
           "h2_from_2022": h2_detail(*h2_groups(c_reads, range(NEW_ERA, 3000)))}
    for r in t_reads:
        out["target_labels"][r["label"]] = out["target_labels"].get(r["label"], 0) + 1
    for r in c_reads:
        out["control_status"][r["status"]] = out["control_status"].get(r["status"], 0) + 1
    gaps = sorted(r["oa_refs"] - r["crossref_refs"] for r in f)
    if gaps:
        out["median_openalex_minus_crossref_refs"] = gaps[len(gaps) // 2] if len(gaps) % 2 else (gaps[len(gaps) // 2 - 1] + gaps[len(gaps) // 2]) / 2
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default="article1_openalex_v2_units_oa.jsonl")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    targets, pool = pick_targets(oa1.load_units(a.units))
    client = a1.Client()
    t_reads, c_reads, tinfo = [], [], []
    for i, u in enumerate(targets):
        msg = client.work(u["rows"][0]["doi"])
        info = {"target": u["rows"][0]["doi"], "openalex": u["rows"][0]["oa"], "crossref": u["rows"][0]["cites"]}
        tinfo.append(info)
        if msg is None:
            info["status"] = "not_in_crossref"
            continue
        trow = dict(a1.row(msg, 1), oa_id=u["rows"][0]["oa_id"])
        names, rx = journal_names(msg), volume_regex(u)
        r1, n1 = read_target(client, a1.get_patient, u, trow, names, rx, SEED + i)
        ctrl = control_of(u)
        r2, n2 = read_control(client, a1.get_patient, u, ctrl, trow, names, rx, SEED + 100 + i)
        t_reads += r1
        c_reads += r2
        info.update({"journal_names": [" ".join(n) for n in names], "target_sample": n1, "control": ctrl["doi"],
                     "control_crossref": ctrl["cites"], "control_sample": n2})
        sys.stderr.write("%s: %d target citers, %d control citers, %d Crossref calls\n"
                         % (trow["doi"], len(r1), len(r2), client.calls))

    citers = sorted({r["citer"] for r in t_reads if r["label"] == "unsupported"}
                    | {r["citer"] for r in c_reads if r.get("status") == "found"})
    works, calls1, failed1 = oa_refs(a1.get_patient, citers)
    p1 = sorted({x["DOI"].lower() for r in t_reads for x in r.get("page1", []) if x.get("DOI")})
    ids, calls2, failed2 = oa1.openalex_works(a1.get_patient, p1)
    annotate(t_reads, c_reads, works, ids)

    res = {"seed": SEED, "eligible_units": pool, "targets": tinfo,
           "openalex": {"citers": len(citers), "citers_found": len(works), "page1_dois": len(p1), "page1_found": len(ids),
                        "lookup_calls": calls1 + calls2, "failed_lookup_calls": failed1 + failed2},
           "crossref_calls": client.calls}
    res["H1"], res["H1_detail"] = score_h1(t_reads, c_reads)
    res["H2"], res["H2_detail"] = score_h2(c_reads)
    res["H3"], res["H3_detail"] = score_h3(t_reads)
    res["descriptive"] = describe(t_reads, c_reads)

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(a.out_dir, "reads.jsonl"), "w", encoding="utf-8") as f:
        for r in t_reads + c_reads:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
