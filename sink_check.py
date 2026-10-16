# sink_check.py - is a paper a citation sink? (pre-registration: prereg-citation-sink-v1.md)
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. Reads the public OpenAlex, Crossref and NCBI E-utilities APIs.
import argparse
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAILTO = "mv2@munimtech.com"
UA = "mv2-sink-check/1.0 (MV2 of Munim, Inc.; mailto:%s)" % MAILTO
TARGET = {"openalex": "W2599766179", "doi": "10.1016/j.physbeh.2017.03.040"}
CONTROL = {"openalex": "W2769845614", "doi": "10.1038/ijo.2017.276"}
SEED = 20261016
N_CROSSREF = 150
N_PMC = 80

ON_TOPIC = re.compile(
    r"orexin|hypocretin|thermogen|energy expenditure|energy balance|energy homeostasis|obes|adipos|"
    r"physical activity|spontaneous activity|sedentar|high[- ]fat|locomot|feeding|food intake|"
    r"body weight|weight gain|dreadd|hypothalam|metabol", re.I)
NEAT = re.compile(r"\bNEAT\b")


def on_topic(text):
    text = text or ""
    return bool(ON_TOPIC.search(text) or NEAT.search(text))


def abstract_text(inv):
    """Rebuild an abstract from OpenAlex's abstract_inverted_index."""
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    return " ".join(w for _, w in pos)


def strip_doi(doi):
    if not doi:
        return ""
    d = doi.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    return d.lower()


def pmcid_of(ids):
    v = (ids or {}).get("pmcid") or ""
    m = re.search(r"PMC(\d+)", v)
    return m.group(1) if m else ""


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def get(url, tries=4, pause=1.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # network hiccup: retry
            last = e
        time.sleep(pause * (2 ** i))
    sys.stderr.write("GET failed %s: %s\n" % (url, last))
    return None


def citers(openalex_id):
    out, cursor = [], "*"
    while cursor:
        q = urllib.parse.urlencode({
            "filter": "cites:" + openalex_id, "per-page": "200", "cursor": cursor,
            "select": "id,doi,title,publication_year,abstract_inverted_index,ids", "mailto": MAILTO})
        raw = get("https://api.openalex.org/works?" + q)
        if raw is None:
            break
        page = json.loads(raw)
        out.extend(page.get("results") or [])
        cursor = (page.get("meta") or {}).get("next_cursor")
        if not page.get("results"):
            break
        time.sleep(0.2)
    return out


def classify(works):
    rows = []
    for w in works:
        text = (w.get("title") or "") + " " + abstract_text(w.get("abstract_inverted_index"))
        rows.append({
            "id": (w.get("id") or "").rsplit("/", 1)[-1],
            "doi": strip_doi(w.get("doi")),
            "year": w.get("publication_year"),
            "title": w.get("title") or "",
            "has_abstract": bool(w.get("abstract_inverted_index")),
            "on_topic": on_topic(text),
            "pmcid": pmcid_of(w.get("ids")),
        })
    return rows


def share_off(rows):
    n = len(rows)
    k = sum(1 for r in rows if not r["on_topic"])
    p, lo, hi = wilson(k, n)
    return {"n": n, "off_topic": k, "share": p, "lo": lo, "hi": hi}


def find_target_ref(refs, doi=TARGET["doi"]):
    """Return the deposited reference that points at the target, or None."""
    for r in refs or []:
        if strip_doi(r.get("DOI")) == doi:
            return r
    for r in refs or []:
        blob = " ".join(str(v) for v in r.values())
        if "176" in blob and "139" in blob and "Physiol" in blob:
            return r
    return None


def describe_ref(r):
    blob = " ".join(str(v) for v in r.values())
    return {
        "key": r.get("key"),
        "doi": strip_doi(r.get("DOI")),
        "doi_is_target": strip_doi(r.get("DOI")) == TARGET["doi"],
        "hhs_banner": bool(re.search(r"HHS Public Access|Author manuscript", blob, re.I)),
        "real_title": bool(re.search(r"nonexercise activity thermogenesis|orexin activation", blob, re.I)),
        "text": blob[:400],
    }


def crossref_sample(rows):
    pool = sorted([r for r in rows if r["doi"]], key=lambda r: r["id"])
    pick = random.Random(SEED).sample(pool, min(N_CROSSREF, len(pool)))
    out = []
    for r in pick:
        raw = get("https://api.crossref.org/works/" + urllib.parse.quote(r["doi"], safe="/") +
                  "?mailto=" + MAILTO)
        rec = {"id": r["id"], "doi": r["doi"], "year": r["year"], "on_topic": r["on_topic"]}
        if raw is None:
            rec["status"] = "not_in_crossref"
        else:
            msg = json.loads(raw).get("message") or {}
            refs = msg.get("reference")
            if not refs:
                rec["status"] = "no_reference_list"
            else:
                hit = find_target_ref(refs)
                rec["status"] = "found" if hit else "target_not_in_list"
                if hit:
                    rec["ref"] = describe_ref(hit)
        out.append(rec)
        time.sleep(0.1)
    return out


def _walk(elem, rid, parts):
    is_hit = elem.tag == "xref" and rid in (elem.get("rid") or "").split()
    if is_hit:
        parts.append("[[*]]")
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        _walk(child, rid, parts)
        if child.tail:
            parts.append(child.tail)


def contexts(root, rid):
    """Sentences in the body that cite reference `rid`, with the citation marked [[*]]."""
    body = root.find(".//body")
    if body is None:
        return []
    out = []
    for p in body.iter("p"):
        if not any(x.tag == "xref" and rid in (x.get("rid") or "").split() for x in p.iter("xref")):
            continue
        parts = []
        _walk(p, rid, parts)
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text):
            if "[[*]]" in s:
                out.append(s[:600])
    return out


def target_rid(root):
    for ref in root.iter("ref"):
        blob = " ".join(ref.itertext())
        dois = [strip_doi(p.text) for p in ref.iter("pub-id") if (p.get("pub-id-type") == "doi" and p.text)]
        if TARGET["doi"] in dois or re.search(r"nonexercise activity thermogenesis", blob, re.I):
            return ref.get("id"), re.sub(r"\s+", " ", blob)[:400]
    return None, ""


def pmc_sample(rows):
    pool = sorted([r for r in rows if r["pmcid"]], key=lambda r: r["id"])
    pick = random.Random(SEED).sample(pool, min(N_PMC, len(pool)))
    out = []
    for r in pick:
        rec = {"id": r["id"], "pmcid": "PMC" + r["pmcid"], "year": r["year"], "on_topic": r["on_topic"],
               "title": r["title"][:200]}
        raw = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&rettype=xml&id=" + r["pmcid"])
        time.sleep(0.4)
        if raw is None:
            rec["status"] = "fetch_failed"
            out.append(rec)
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            rec["status"] = "bad_xml"
            out.append(rec)
            continue
        rid, ref_text = target_rid(root)
        if not rid:
            rec["status"] = "target_not_in_refs" if root.find(".//body") is not None else "no_full_text"
            out.append(rec)
            continue
        ctx = contexts(root, rid)
        rec.update({"status": "found" if ctx else "no_context", "ref_text": ref_text, "contexts": ctx,
                    "context_on_topic": any(on_topic(c.replace("[[*]]", "")) for c in ctx)})
        out.append(rec)
    return out


def by_year(rows, years):
    return [r for r in rows if r["year"] in years]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)

    res = {"target": TARGET, "control": CONTROL, "seed": SEED}
    tgt = classify(citers(TARGET["openalex"]))
    ctl = classify(citers(CONTROL["openalex"]))
    res["n_target_citers"], res["n_control_citers"] = len(tgt), len(ctl)
    res["target_off"], res["control_off"] = share_off(tgt), share_off(ctl)
    t, c = res["target_off"], res["control_off"]
    res["H1_supported"] = bool(t["n"] and c["n"] and t["share"] >= 0.70 and c["share"] <= 0.30 and t["lo"] > c["hi"])

    early, late = by_year(tgt, {2017, 2018, 2019}), by_year(tgt, {2020, 2021})
    res["early_off"], res["late_off"] = share_off(early), share_off(late)
    if len(early) < 10:
        res["H2"] = "untestable"
    else:
        res["H2"] = "supported" if res["late_off"]["lo"] > res["early_off"]["share"] else "not supported"
    res["target_off_by_year"] = {str(y): share_off(by_year(tgt, {y})) for y in sorted({r["year"] for r in tgt if r["year"]})}

    cr = crossref_sample(tgt)
    found = [x for x in cr if x["status"] == "found"]
    res["H4"] = {
        "sampled": len(cr),
        "status": {s: sum(1 for x in cr if x["status"] == s) for s in sorted({x["status"] for x in cr})},
        "found": len(found),
        "hhs_banner": sum(1 for x in found if x["ref"]["hhs_banner"]),
        "real_title": sum(1 for x in found if x["ref"]["real_title"]),
        "doi_not_target": sum(1 for x in found if not x["ref"]["doi_is_target"]),
    }

    pm = pmc_sample(tgt)
    got = [x for x in pm if x["status"] == "found"]
    res["H3"] = {
        "sampled": len(pm),
        "status": {s: sum(1 for x in pm if x["status"] == s) for s in sorted({x["status"] for x in pm})},
        "with_context": len(got),
        "context_on_topic": sum(1 for x in got if x["context_on_topic"]),
    }

    with open(os.path.join(a.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for name, rows in (("target_citers.jsonl", tgt), ("control_citers.jsonl", ctl),
                       ("crossref_refs.jsonl", cr), ("pmc_contexts.jsonl", pm)):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({k: res[k] for k in ("n_target_citers", "n_control_citers", "target_off", "control_off",
                                          "H1_supported", "early_off", "late_off", "H2", "H3", "H4")}, indent=1))


if __name__ == "__main__":
    main()
