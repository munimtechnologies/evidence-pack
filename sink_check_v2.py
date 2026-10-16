# sink_check_v2.py - full-population rerun of the Bunney 2017 citation-sink test
# (pre-registration: prereg-citation-sink-v2.md; v1 rule and thresholds unchanged).
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public OpenAlex, Crossref, OpenCitations and NCBI APIs.
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import sink_check as v1

SEED2 = 20261017
N_REFS = 300
OC = "https://api.opencitations.net/index/v2/citations/doi:"
IDCONV = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
WAITS = (30, 60, 120, 300, 600)  # back-off for OpenAlex's keyless daily budget (HTTP 401/429)

# Hand read of the 120 v1 references (findings/citation-sink-bunney-v1-results-2026-10-16.md).
HAND_V1 = {"found": 120, "genuine": 10, "doi_only": 13, "other_work": 97}

GENUINE = re.compile(r"\bBunney\b|nonexercise activity thermogenesis|orexin activation counteracts", re.I)
META_KEYS = {"key", "doi-asserted-by", "DOI"}


def get_patient(url, waits=WAITS, sleep=time.sleep):
    """GET with long back-off on 401/429/5xx. Returns bytes, or None after the last wait."""
    last = None
    for w in (0,) + tuple(waits):
        if w:
            sleep(w)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": v1.UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # network hiccup: wait and retry
            last = e
    sys.stderr.write("GET gave up %s: %s\n" % (url, last))
    return None


def citers_paged(openalex_id, fetch=get_patient, per_page=200):
    """Every OpenAlex work citing `openalex_id`, by page number (v1's cursor paging hit HTTP 401).
    Returns (works, meta count, complete)."""
    out, count, page = [], None, 1
    while True:
        q = urllib.parse.urlencode({
            "filter": "cites:" + openalex_id, "per-page": str(per_page), "page": str(page),
            "select": "id,doi,title,publication_year,abstract_inverted_index,ids", "mailto": v1.MAILTO})
        raw = fetch("https://api.openalex.org/works?" + q)
        if raw is None:
            break
        data = json.loads(raw)
        if count is None:
            count = (data.get("meta") or {}).get("count")
        results = data.get("results") or []
        out.extend(results)
        if not results or (count is not None and len(out) >= count):
            break
        page += 1
        time.sleep(0.2)
    return out, count, count is not None and len(out) >= count


def classify_ref(ref):
    """genuine: names Bunney or the paper's title; doi_only: nothing but the DOI; other_work: anything else."""
    blob = " ".join(str(v) for v in ref.values())
    if GENUINE.search(blob):
        return "genuine"
    if not (set(ref) - META_KEYS):
        return "doi_only"
    return "other_work"


def subtype(ref):
    """For other_work: journal_swap (Physiol Behav 176:139 in another work's reference) or
    doi_attached (Bunney's DOI on another work's otherwise different metadata)."""
    blob = " ".join(str(v) for v in ref.values())
    if "176" in blob and "139" in blob and "Physiol" in blob:
        return "journal_swap"
    if v1.strip_doi(ref.get("DOI")) == v1.TARGET["doi"]:
        return "doi_attached"
    return "other"


def year_of(msg):
    for k in ("issued", "published", "published-print", "published-online"):
        parts = ((msg.get(k) or {}).get("date-parts") or [[None]])[0]
        if parts and parts[0]:
            return parts[0]
    return None


def crossref_msg(doi):
    raw = v1.get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/") + "?mailto=" + v1.MAILTO)
    if raw is None:
        return None
    try:
        return json.loads(raw).get("message") or {}
    except ValueError:
        return None


def ref_record(doi, msg):
    rec = {"doi": doi}
    if msg is None:
        rec["status"] = "not_in_crossref"
        return rec
    title = " ".join(msg.get("title") or [])
    abstract = re.sub(r"<[^>]+>", " ", msg.get("abstract") or "")
    rec.update({"title": title[:200], "crossref_year": year_of(msg),
                "on_topic_crossref": v1.on_topic(title + " " + abstract)})
    refs = msg.get("reference")
    if not refs:
        rec["status"] = "no_reference_list"
        return rec
    hit = v1.find_target_ref(refs)
    if not hit:
        rec["status"] = "target_not_in_list"
        return rec
    cls = classify_ref(hit)
    rec.update({"status": "found", "class": cls, "subtype": subtype(hit) if cls == "other_work" else "",
                "asserted_by": hit.get("doi-asserted-by") or "", "ref": v1.describe_ref(hit)})
    return rec


def summarise_refs(recs):
    found = [x for x in recs if x.get("status") == "found"]
    cls = {k: sum(1 for x in found if x["class"] == k) for k in ("genuine", "doi_only", "other_work")}
    readable = [x for x in found if x["class"] != "doi_only"]
    p, lo, hi = v1.wilson(cls["genuine"], len(readable))
    return {
        "sampled": len(recs),
        "status": {s: sum(1 for x in recs if x.get("status") == s) for s in sorted({x.get("status") for x in recs})},
        "found": len(found),
        "class": cls,
        "subtype": {s: sum(1 for x in found if x.get("subtype") == s) for s in ("journal_swap", "doi_attached", "other")},
        "asserted_by": {s: sum(1 for x in found if x.get("asserted_by") == s) for s in sorted({x.get("asserted_by") for x in found})},
        "hhs_banner": sum(1 for x in found if x["ref"]["hhs_banner"]),
        "genuine_share_readable": {"n": len(readable), "k": cls["genuine"], "share": p, "lo": lo, "hi": hi},
    }


def genuine_by_year(recs, key="year"):
    out = {}
    readable = [x for x in recs if x.get("status") == "found" and x["class"] != "doi_only"]
    for y in sorted({x.get(key) for x in readable if x.get(key)}):
        rows = [x for x in readable if x.get(key) == y]
        k = sum(1 for x in rows if x["class"] == "genuine")
        out[str(y)] = {"n": len(rows), "genuine": k}
    return out


def parse_oc(raw):
    """Citing DOIs (lower case, unique, sorted) from an OpenCitations v2 citations response."""
    dois = set()
    for item in json.loads(raw) if raw else []:
        m = re.search(r"\bdoi:(\S+)", item.get("citing") or "")
        if m:
            dois.add(m.group(1).lower())
    return sorted(dois)


def parse_idconv(raw):
    """DOI -> PMC digits from a PMC ID Converter JSON response."""
    out = {}
    for r in (json.loads(raw).get("records") or []) if raw else []:
        m = re.search(r"PMC(\d+)", r.get("pmcid") or "")
        if m and r.get("doi"):
            out[r["doi"].lower()] = m.group(1)
    return out


def idconv(dois, batch=100):
    out = {}
    clean = [d for d in dois if d and "," not in d]
    for i in range(0, len(clean), batch):
        q = urllib.parse.urlencode({"ids": ",".join(clean[i:i + batch]), "format": "json",
                                    "tool": "mv2-sink-check", "email": v1.MAILTO})
        out.update(parse_idconv(v1.get(IDCONV + "?" + q)))
        time.sleep(0.4)
    return out


def sample_refs(dois, seed, n=N_REFS, extra=None):
    pick = random.Random(seed).sample(sorted(dois), min(n, len(dois)))
    out = []
    for d in pick:
        rec = ref_record(d, crossref_msg(d))
        if extra:
            rec.update(extra.get(d) or {})
        out.append(rec)
        time.sleep(0.1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--v1-dois", default="v1_crossref_dois.txt")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    res = {"target": v1.TARGET, "control": v1.CONTROL, "seed": SEED2}

    # Counts in the three open indexes
    cr_t, cr_c = crossref_msg(v1.TARGET["doi"]) or {}, crossref_msg(v1.CONTROL["doi"]) or {}
    oc_t = parse_oc(v1.get(OC + v1.TARGET["doi"]))
    oc_c = parse_oc(v1.get(OC + v1.CONTROL["doi"]))

    # H1, H2: every OpenAlex citer, v1 rule and thresholds
    tw, tcount, tdone = citers_paged(v1.TARGET["openalex"])
    cw, ccount, cdone = citers_paged(v1.CONTROL["openalex"])
    tgt, ctl = v1.classify(tw), v1.classify(cw)
    res["counts"] = {
        "crossref_is_referenced_by": [cr_t.get("is-referenced-by-count"), cr_c.get("is-referenced-by-count")],
        "opencitations_citers": [len(oc_t), len(oc_c)],
        "openalex_count": [tcount, ccount],
        "openalex_fetched": [len(tgt), len(ctl)],
        "openalex_complete": [tdone, cdone],
    }
    res["target_off"], res["control_off"] = v1.share_off(tgt), v1.share_off(ctl)
    t, c = res["target_off"], res["control_off"]
    ok = bool(t["n"] and c["n"] and t["share"] >= 0.70 and c["share"] <= 0.30 and t["lo"] > c["hi"])
    res["H1"] = ("supported" if ok else "not supported") if (tdone and cdone) else "incomplete"
    early, late = v1.by_year(tgt, {2017, 2018, 2019}), v1.by_year(tgt, {2020, 2021})
    res["early_off"], res["late_off"] = v1.share_off(early), v1.share_off(late)
    if len(early) < 10:
        res["H2"] = "untestable"
    else:
        res["H2"] = "supported" if res["late_off"]["lo"] > res["early_off"]["share"] else "not supported"
    res["target_off_by_year"] = {str(y): v1.share_off(v1.by_year(tgt, {y}))
                                 for y in sorted({r["year"] for r in tgt if r["year"]})}

    # H3: PMC contexts; PMCIDs from OpenAlex, filled in by the PMC ID Converter (v1 found none)
    pmc = idconv([r["doi"] for r in tgt if r["doi"] and not r["pmcid"]])
    for r in tgt:
        if not r["pmcid"] and r["doi"] in pmc:
            r["pmcid"] = pmc[r["doi"]]
    pm = v1.pmc_sample(tgt)
    got = [x for x in pm if x["status"] == "found"]
    res["H3"] = {
        "with_pmcid": sum(1 for r in tgt if r["pmcid"]),
        "sampled": len(pm),
        "status": {s: sum(1 for x in pm if x["status"] == s) for s in sorted({x["status"] for x in pm})},
        "with_context": len(got),
        "context_on_topic": sum(1 for x in got if x["context_on_topic"]),
    }

    # H4, H5: deposited references of 300 random OpenAlex citers
    meta = {r["doi"]: {"id": r["id"], "year": r["year"], "on_topic": r["on_topic"]} for r in tgt if r["doi"]}
    refs_a = sample_refs(list(meta), SEED2, extra=meta)
    res["H4"] = summarise_refs(refs_a)
    g = res["H4"]["genuine_share_readable"]
    res["H5"] = "untestable" if g["n"] < 30 else ("supported" if g["hi"] < 0.25 else "not supported")
    res["H5_by_year"] = genuine_by_year(refs_a)

    # H6: the fixed rule against the v1 hand read (same 150 DOIs)
    with open(a.v1_dois, encoding="utf-8") as f:
        v1_dois = [ln.strip() for ln in f if ln.strip()]
    refs_v1 = [ref_record(d, crossref_msg(d)) for d in v1_dois]
    s1 = summarise_refs(refs_v1)
    rule = dict(s1["class"], found=s1["found"])
    res["H6"] = {"hand": HAND_V1, "rule": rule,
                 "agree": all(abs(rule[k] - HAND_V1[k]) <= 2 for k in HAND_V1)}

    # Descriptive: OpenCitations' independent citer list
    oa = set(meta)
    res["opencitations"] = {"citers": len(oc_t), "also_in_openalex": len(oa & set(oc_t)),
                            "only_opencitations": len(set(oc_t) - oa), "only_openalex": len(oa - set(oc_t))}
    refs_b = sample_refs(oc_t, SEED2 + 1)
    titled = [x for x in refs_b if x.get("title")]
    res["opencitations_sample"] = summarise_refs(refs_b)
    res["opencitations_sample"]["off_topic_by_crossref_title"] = v1.share_off(
        [{"on_topic": x["on_topic_crossref"]} for x in titled])
    res["opencitations_sample"]["genuine_by_year"] = genuine_by_year(refs_b, key="crossref_year")

    with open(os.path.join(a.out_dir, "results_v2.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for name, rows in (("target_citers_v2.jsonl", tgt), ("control_citers_v2.jsonl", ctl),
                       ("refs_openalex_sample.jsonl", refs_a), ("refs_v1_recheck.jsonl", refs_v1),
                       ("refs_opencitations_sample.jsonl", refs_b), ("pmc_contexts_v2.jsonl", pm)):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(a.out_dir, "opencitations_citers.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(oc_t) + "\n")
    print(json.dumps({k: res[k] for k in ("counts", "target_off", "control_off", "H1", "early_off", "late_off",
                                          "H2", "H3", "H4", "H5", "H6", "opencitations")}, indent=1))


if __name__ == "__main__":
    main()
