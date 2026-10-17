# openalex_article1.py - Is OpenAlex's excess on MDPI and Frontiers article-1 records specific to article 1?
# Pre-registration: findings/article-number-1-openalex-prereg-v2-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads article1_check_v1_units.jsonl and the public OpenAlex and Crossref APIs.
import argparse
import json
import os
import re
import statistics
import sys
import urllib.parse

import article1_check as a1

SEED = 20261023
OLD = range(2016, 2020)  # volume years 2016-2019
NEW = range(2021, 2024)  # volume years 2021-2023 (MDPI only: Frontiers DOIs changed in 2021)

# Pre-registered thresholds
MIN_FAR, MIN_UNITS, ALPHA = 10, 10, 0.01
MIN_EFFECT = 2.0  # H1/H2: median E(article 1) / median E(far controls)
MIN_ERA = 1.5  # H3: old-era median control E over new-era median control E
H4_TOP, H4_READS, MIN_REFS = 3, 40, 5
H4_MIN_N, H4_SHARE = 20, 0.50
CAL_MIN_N, CAL_SHARE = 10, 0.70


def norm_doi(s):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", s or "", flags=re.I).lower()


def excess(oa, cr):
    return (oa + 1) / (cr + 1)


def load_units(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def openalex_works(fetch, dois, per=50):
    """{doi: (OpenAlex id, cited_by_count)} for DOIs, per DOIs a call; the more-cited work wins a shared DOI."""
    out, calls, failed = {}, 0, 0
    for i in range(0, len(dois), per):
        calls += 1
        raw = fetch(a1.OA + "?" + urllib.parse.urlencode({"filter": "doi:" + "|".join(dois[i:i + per]), "per-page": "200",
                                                          "select": "id,doi,cited_by_count", "mailto": a1.MAILTO}))
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        if not isinstance(data, dict):
            failed += 1
            continue
        for w in data.get("results") or []:
            d = norm_doi(w.get("doi"))
            n = int(w.get("cited_by_count") or 0)
            if d and (d not in out or n > out[d][1]):
                out[d] = (w.get("id") or "", n)
    return out, calls, failed


def attach(units, works):
    """Add oa (count or None) and oa_id to article 1 and every far control."""
    for u in units:
        for r in [u["article1"]] + u["far"]:
            w = works.get(r["doi"].lower())
            r["oa"], r["oa_id"] = (w[1], w[0]) if w else (None, "")


def far_with_oa(u):
    return [r for r in u["far"] if r.get("oa") is not None]


def eligible(units, years, publishers=("MDPI", "Frontiers")):
    return [u for u in units if u["confirmatory"] and u["publisher"] in publishers and u["year"] in years
            and u["article1"].get("oa") is not None and len(far_with_oa(u)) >= MIN_FAR]


def unit_excess(u):
    """(E of article 1, [E of each far control with an OpenAlex count])."""
    a = u["article1"]
    return excess(a["oa"], a["cites"]), [excess(r["oa"], r["cites"]) for r in far_with_oa(u)]


def score_excess(units):
    """H1 (old era) and H2 (new era): is article 1's excess the largest in its volume more often than chance?"""
    detail = {"units": len(units)}
    if len(units) < MIN_UNITS:
        return "untestable", detail
    k, ps, effects = 0, [], []
    for u in units:
        e1, ec = unit_excess(u)
        if e1 > max(ec):
            k += 1
        ps.append(1 / (len(ec) + 1))
        effects.append(e1 / statistics.median(ec))
    p = a1.poisson_binomial_tail(ps, k)
    med = statistics.median(effects)
    detail.update({"top": k, "expected_top": sum(ps), "p": p, "median_effect": med})
    return ("supported" if p < ALPHA and med >= MIN_EFFECT else "not supported"), detail


def score_era(old, new):
    """H3: is the controls' excess larger in old volumes than in new ones?"""
    detail = {"old_units": len(old), "new_units": len(new)}
    if len(old) < MIN_UNITS or len(new) < MIN_UNITS:
        return "untestable", detail
    mo = statistics.median(statistics.median(unit_excess(u)[1]) for u in old)
    mn = statistics.median(statistics.median(unit_excess(u)[1]) for u in new)
    detail.update({"old_median_control_excess": mo, "new_median_control_excess": mn, "ratio": mo / mn})
    return ("supported" if mo / mn >= MIN_ERA else "not supported"), detail


def classify_citer(msg, doi, words, family):
    """(label, reference) for one OpenAlex citer, read from its Crossref deposit."""
    if msg is None:
        return "not_in_crossref", None
    refs = msg.get("reference") or []
    for r in refs:
        if (r.get("DOI") or "").lower() == doi.lower():
            return a1.classify_ref(r, words, family), r
    ws = set(words)
    need = max(2, (len(ws) + 1) // 2)
    for r in refs:
        text = " ".join(str(r.get(k) or "") for k in a1.TITLE_KEYS).lower()
        if ws and text.strip() and sum(1 for w in ws if w in text) >= need:
            return "genuine", r
    if len(refs) >= MIN_REFS:
        return "unsupported", None
    return "too_few_references", None


def sample_citers(fetch, wid, seed, n=H4_READS):
    """DOIs of a seeded random sample of the works OpenAlex lists as citing wid, and the sample size returned."""
    raw = fetch(a1.OA + "?" + urllib.parse.urlencode({"filter": "cites:" + wid.rsplit("/", 1)[-1], "sample": str(n),
                                                      "seed": str(seed), "per-page": str(n), "select": "id,doi",
                                                      "mailto": a1.MAILTO}))
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    got, dois = data.get("results") or [], []
    for w in got:
        d = norm_doi(w.get("doi"))
        if d and d not in dois:
            dois.append(d)
    return dois, len(got)


def read_oa_citers(client, fetch, row, seed, n=H4_READS):
    dois, returned = sample_citers(fetch, row["oa_id"], seed, n)
    words = a1.title_words(row["title"])
    out = []
    for d in dois:
        label, ref = classify_citer(client.work(d), row["doi"], words, row["first_author"])
        r = {"target": row["doi"], "citer": d, "label": label}
        if ref is not None:
            r["ref"] = {k: str(v)[:300] for k, v in ref.items()}
        out.append(r)
    return out, {"returned": returned, "with_doi": len(dois)}


def share(reads):
    g = sum(1 for r in reads if r["label"] == "genuine")
    b = sum(1 for r in reads if r["label"] in ("other_work", "unsupported"))
    return {"n": g + b, "genuine": g, "share": (g / (g + b)) if g + b else None}


def score_h4(t_reads, c_reads):
    """H4: fewer than half the readable OpenAlex citers of the top article-1 records really cite them."""
    t, c = share(t_reads), share(c_reads)
    d = {"target": t, "control": c}
    if c["n"] < CAL_MIN_N or c["share"] < CAL_SHARE:
        return "untestable (classifier failed calibration)", d
    if t["n"] < H4_MIN_N:
        return "untestable", d
    return ("supported" if t["share"] < H4_SHARE else "not supported"), d


def h4_targets(units):
    """Up to 3 units whose article 1 has the largest OpenAlex-minus-Crossref count, with 3+ title words."""
    c = [u for u in units if u["article1"].get("oa_id") and len(a1.title_words(u["article1"]["title"])) >= 3]
    c.sort(key=lambda u: (-(u["article1"]["oa"] - u["article1"]["cites"]), u["article1"]["doi"]))
    return c[:H4_TOP]


def h4_control(u):
    """The far control with the most OpenAlex citations (ties: lowest DOI)."""
    rows = [r for r in far_with_oa(u) if r.get("oa_id")]
    return min(rows, key=lambda r: (-r["oa"], r["doi"])) if rows else None


def table_row(u):
    e1, ec = unit_excess(u) if u["article1"].get("oa") is not None else (None, [])
    return {"publisher": u["publisher"], "journal": u["journal"], "volume": u["volume"], "year": u["year"],
            "confirmatory": u["confirmatory"], "article1_doi": u["article1"]["doi"],
            "article1_crossref": u["article1"]["cites"], "article1_openalex": u["article1"].get("oa"),
            "article1_openalex_v1": u["article1"].get("openalex_cites"), "article1_excess": e1,
            "n_far_oa": len(ec), "far_median_excess": statistics.median(ec) if ec else None,
            "top": bool(ec) and e1 > max(ec)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default="article1_check_v1_units.jsonl")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    units = load_units(a.units)
    dois = sorted({r["doi"].lower() for u in units for r in [u["article1"]] + u["far"]})
    works, calls, failed = openalex_works(a1.get_patient, dois)
    attach(units, works)
    sys.stderr.write("OpenAlex: %d of %d DOIs found, %d calls, %d failed\n" % (len(works), len(dois), calls, failed))

    old = eligible(units, OLD)
    res = {"seed": SEED, "openalex": {"dois": len(dois), "found": len(works), "calls": calls, "failed_calls": failed,
                                      "partial": failed * 50 > 0.10 * len(dois)}}
    res["H1"], res["H1_detail"] = score_excess(old)
    res["H2"], res["H2_detail"] = score_excess(eligible(units, NEW, ("MDPI",)))
    res["H3"], res["H3_detail"] = score_era(eligible(units, OLD, ("MDPI",)), eligible(units, NEW, ("MDPI",)))
    res["descriptive_2020"] = score_excess(eligible(units, range(2020, 2021)))[1]

    client = a1.Client()
    t_reads, c_reads, tinfo = [], [], []
    for i, u in enumerate(h4_targets(old)):
        r1, n1 = read_oa_citers(client, a1.get_patient, u["article1"], SEED + i)
        ctrl = h4_control(u)
        r2, n2 = read_oa_citers(client, a1.get_patient, ctrl, SEED + 100 + i) if ctrl else ([], {})
        t_reads += r1
        c_reads += r2
        tinfo.append({"target": u["article1"]["doi"], "target_openalex": u["article1"]["oa"],
                      "target_crossref": u["article1"]["cites"], "target_sample": n1,
                      "control": ctrl["doi"] if ctrl else "", "control_openalex": ctrl["oa"] if ctrl else None,
                      "control_crossref": ctrl["cites"] if ctrl else None, "control_sample": n2})
    res["H4"], res["H4_detail"] = score_h4(t_reads, c_reads)
    res["H4_targets"] = tinfo
    res["H4_labels"] = {"target": {}, "control": {}}
    for key, rr in (("target", t_reads), ("control", c_reads)):
        for r in rr:
            res["H4_labels"][key][r["label"]] = res["H4_labels"][key].get(r["label"], 0) + 1
    res["calls"] = {"openalex": calls + 2 * len(tinfo), "crossref": client.calls}
    res["table"] = [table_row(u) for u in units]

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(a.out_dir, "units_oa.jsonl"), "w", encoding="utf-8") as f:
        for u in units:
            slim = {k: u[k] for k in ("publisher", "journal", "volume", "year", "confirmatory")}
            slim["rows"] = [{k: r.get(k) for k in ("doi", "n", "cites", "oa", "oa_id")} for r in [u["article1"]] + u["far"]]
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")
    with open(os.path.join(a.out_dir, "reads.jsonl"), "w", encoding="utf-8") as f:
        for r in t_reads + c_reads:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "table"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
