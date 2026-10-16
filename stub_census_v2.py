# stub_census_v2.py - DOI-stub census v2: stems of PubMed-indexed articles' DOIs, and where stub records come from.
# Pre-registration: findings/doi-stub-census-prereg-v2-2026-10-16.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reuses stub_census.py (evidence-pack commit 1e3632b) for sampling, stems and lookups.
import argparse
import csv
import json
import os
from collections import Counter

import stub_census as sc

SEED = 20261020
SAMPLE_FILTER = "indexed_in:pubmed,has_doi:true,type:article,publication_year:2000-2025,cited_by_count:>9"
N_SAMPLE = 10000  # OpenAlex's largest sample
SELECT = "id,doi,ids,display_name,publication_year,cited_by_count,type,primary_location"
MAX_OA_CALLS = 300
MAX_WILEY = 40  # new records that get a Wiley-share call, largest first (descriptive only)

# Pre-registered thresholds
H1_MIN_NEW = 10  # unregistered new stems found as OpenAlex DOIs
H2_SHARE = 0.60  # share of absorbed citations on unregistered records that carry a MAG id
H3_MAX_PMID = 2  # unregistered stub records carrying a PMID
H4_MIN_CITERS, H4_SHARE = 50, 0.50  # share of large unregistered records not hosted by a journal source

# The 73 stems known before this census: the 12-stem pilot and the 61 new stems of census v1
KNOWN = sc.PILOT + [
    "10.1002/1097", "10.1007/978", "10.1007/jhep03", "10.1007/s00335", "10.1007/s00381", "10.1007/s10853",
    "10.1007/s11367", "10.1007/s12144", "10.1016/b978", "10.1016/s0098", "10.1016/s0301-6226", "10.1016/s0305",
    "10.1016/s0921", "10.1016/s1470-2045", "10.1016/s1473-3099", "10.1044/1092-4388", "10.1046/j.1365",
    "10.1088/0022", "10.1088/0957", "10.1088/1741", "10.1088/1742", "10.1108/aaaj", "10.1108/ara", "10.1108/bfj",
    "10.1108/ccij", "10.1108/ejim", "10.1108/ijrdm", "10.1108/ijsms", "10.1108/imds", "10.1108/itp",
    "10.1108/jbim", "10.1108/jcom", "10.1108/jfbm", "10.1108/jfmm", "10.1108/medar", "10.1108/mip", "10.1108/tg",
    "10.1111/j.1365", "10.1111/j.1439", "10.1111/j.1468", "10.1111/j.1469", "10.1111/j.1476", "10.1111/j.1540",
    "10.1136/jmedgenet", "10.1186/1475", "10.1186/s13054", "10.1186/s13068", "10.1186/s40168", "10.1302/2046",
    "10.1515/jpem", "10.1515/jpm", "10.1515/sagmb", "10.1530/eje", "10.1530/joe", "10.1641/0006-3568",
    "10.1666/0022-3360", "10.21037/tlcr", "10.2495/ei", "10.25171/instgeoph_pas_publs", "10.31073/mivg202001",
    "10.9790/3008"]

FIELDS = ("stub", "kind", "known", "id", "title", "year", "type", "citers", "registered_in_crossref", "has_mag",
          "pmid", "source_type", "source_name", "wiley_share")


def record_row(w, stub, kind, known):
    """One blocklist row from an OpenAlex work whose DOI equals the stub."""
    ids = w.get("ids") or {}
    src = (w.get("primary_location") or {}).get("source") or {}
    pmid = str(ids.get("pmid") or "").rstrip("/").rsplit("/", 1)[-1]
    return {"stub": stub, "kind": kind, "known": known, "id": sc.short_id(w.get("id")),
            "title": (w.get("display_name") or "")[:160], "year": w.get("publication_year"), "type": w.get("type"),
            "citers": w.get("cited_by_count") or 0, "registered_in_crossref": None, "has_mag": bool(ids.get("mag")),
            "pmid": pmid, "source_type": src.get("type") or "", "source_name": src.get("display_name") or "",
            "wiley_share": None}


def unregistered(rows):
    return [r for r in rows if r["registered_in_crossref"] is False]


def score_h1(rows):
    new = sorted({r["stub"] for r in unregistered(rows) if not r["known"]})
    return ("supported" if len(new) >= H1_MIN_NEW else "not supported"), new


def score_h2(rows):
    u = unregistered(rows)
    total = sum(r["citers"] for r in u)
    if not total:
        return "untestable", {"citations": 0, "on_mag": 0, "share": None}
    mag = sum(r["citers"] for r in u if r["has_mag"])
    share = mag / total
    return ("supported" if share >= H2_SHARE else "not supported"), {"citations": total, "on_mag": mag,
                                                                      "share": share}


def score_h3(rows):
    with_pmid = [r["id"] for r in unregistered(rows) if r["pmid"]]
    return ("supported" if len(with_pmid) <= H3_MAX_PMID else "not supported"), with_pmid


def score_h4(rows):
    """Large unregistered records whose primary location is not a journal source (a missing source counts)."""
    big = [r for r in unregistered(rows) if r["citers"] >= H4_MIN_CITERS]
    if not big:
        return "untestable", {"n": 0, "not_journal": 0}
    nj = sum(1 for r in big if r["source_type"] != "journal")
    return ("supported" if nj / len(big) >= H4_SHARE else "not supported"), {"n": len(big), "not_journal": nj}


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    sc.BUDGET = sc.Budget(MAX_OA_CALLS)
    sc.SELECT = SELECT  # lookup() reads the module's SELECT
    res = {"seed": SEED, "sample_filter": SAMPLE_FILTER, "n_sample": N_SAMPLE, "known": len(KNOWN)}

    works, done = sc.sampled(SAMPLE_FILTER, N_SAMPLE, SEED, "id,doi")
    cand = {}
    for w in works:
        for s, kind in sc.stubs_of(w.get("doi")):
            cand.setdefault(s, kind)
    res["sample"] = {"works": len(works), "complete": done and len(works) >= N_SAMPLE, "stems": len(cand),
                     "stems_by_kind": dict(Counter(cand.values())),
                     "known_stems_in_sample": sum(1 for s in cand if s in KNOWN)}

    recs, look_done = sc.lookup(sorted(set(cand) | set(KNOWN)))
    res["lookup_complete"] = look_done
    rows = []
    for w in recs:
        s = sc.strip_doi(w.get("doi"))
        rows.append(record_row(w, s, cand.get(s) or sc.kind_of(s), s in KNOWN))
    rows.sort(key=lambda r: (-r["citers"], r["stub"], r["id"]))

    reg = {}
    for r in rows:
        if r["stub"] not in reg:
            reg[r["stub"]] = sc.crossref(r["stub"]) is not None
        r["registered_in_crossref"] = reg[r["stub"]]
    for r in [x for x in rows if not x["known"] and x["citers"]][:MAX_WILEY]:
        r["wiley_share"] = sc.wiley_share(sc.oa({"filter": "cites:" + r["id"],
                                                 "group_by": "primary_location.source.publisher_lineage"}))

    u = unregistered(rows)
    res["records"] = {"all": len(rows), "unregistered": len(u), "new": sum(1 for r in rows if not r["known"]),
                      "new_unregistered": sum(1 for r in u if not r["known"])}
    res["citations_absorbed"] = {"all": sum(r["citers"] for r in rows), "unregistered": sum(r["citers"] for r in u),
                                 "new_unregistered": sum(r["citers"] for r in u if not r["known"])}
    res["H1"], res["H1_new_unregistered"] = score_h1(rows)
    res["H2"], res["H2_detail"] = score_h2(rows)
    res["H3"], res["H3_with_pmid"] = score_h3(rows)
    res["H4"], res["H4_detail"] = score_h4(rows)
    res["source_types_unregistered"] = dict(Counter(r["source_type"] or "(none)" for r in u))
    res["budget"] = {"openalex_calls": sc.BUDGET.calls, "openalex_cost_usd": round(sc.BUDGET.cost, 4),
                     "refused_over_cap": sc.BUDGET.refused, "failed": sc.BUDGET.failed}

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(a.out_dir, "stub_records_v2.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_csv(rows, os.path.join(a.out_dir, "stub_blocklist.csv"))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
