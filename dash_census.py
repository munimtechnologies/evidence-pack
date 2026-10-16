#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""dash_census: how often do publishers deposit reference DOIs with Unicode dashes, and what breaks?

Pre-registration: findings/reference-dash-census-prereg-v1-2026-10-16.md (munimtechnologies/evidence-pack).
Draws random 2026 journal articles per Crossref member, counts publisher-asserted reference DOIs that carry a
Unicode dash, checks a seeded sample of them at Crossref / doi.org, and checks whether the citations appear in
OpenAlex and OpenCitations. Standard library only.

  python dash_census.py --out /out
"""
import argparse
import collections
import json
import math
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "mv2@munimtech.com"
UA = "mv2-munim-dash-census/1.0 (mailto:%s)" % MAILTO
CROSSREF = "https://api.crossref.org/works"
HANDLES = "https://doi.org/api/handles/"
OPENCITATIONS = "https://api.opencitations.net/index/v2/references/doi:"
OPENALEX = "https://api.openalex.org/works"
SEED = 20261016
WILEY = "311"
# (Crossref member id, number of sample=100 draws)
MEMBERS = [(WILEY, 3), ("78", 1), ("297", 1), ("301", 1), ("179", 1), ("286", 1),
           ("276", 1), ("1968", 1), ("1965", 1), ("239", 1), ("56", 1)]
WINDOW = "from-pub-date:2026-01-01,until-pub-date:2026-09-30,type:journal-article,has-references:true"
SELECT = "DOI,reference,container-title,issued,member,publisher"
N_RESOLVE = 150
N_CONTROLS = 3
# hyphen, non-breaking hyphen, figure dash, en dash, em dash, minus sign, soft hyphen
DASHES = "‐‑‒–—−­"
NORMALISE = {ord(c): "-" for c in DASHES[:-1]}
NORMALISE[ord("­")] = None
RESOLVES = ("crossref", "other-ra")


def get(url, timeout=120, tries=5):
    """(status, body). 400/404 come back at once; other errors back off and retry."""
    last = ""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as err:
            if err.code in (400, 404):
                return err.code, b""
            last = "HTTP %d" % err.code
        except Exception as err:  # network hiccups: back off and retry
            last = repr(err)
        time.sleep(5 * (attempt + 1))
    return None, last.encode()


def has_dash(doi):
    return any(c in DASHES for c in doi or "")


def has_hyphen(doi):
    return "-" in (doi or "") or has_dash(doi)


def normalise(doi):
    return (doi or "").translate(NORMALISE)


def dash_codes(doi):
    return sorted({"U+%04X" % ord(c) for c in doi or "" if c in DASHES})


def wilson(k, n, z=1.959964):
    if not n:
        return None, None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def share(k, n):
    return k / n if n else None


# ---- sample -------------------------------------------------------------------------------------

def sample_url(member):
    q = "filter=member:%s,%s&sample=100&select=%s&mailto=%s" % (member, WINDOW, SELECT, MAILTO)
    return CROSSREF + "?" + q


def draw(member, draws, fetch=get):
    """Up to 100 * draws distinct articles for one member -> (items, failed draws)."""
    seen, items, failed = set(), [], 0
    for _ in range(draws):
        status, body = fetch(sample_url(member), timeout=300)
        if status != 200:
            failed += 1
            continue
        for it in (json.loads(body).get("message") or {}).get("items") or []:
            key = (it.get("DOI") or "").lower()
            if key and key not in seen:
                seen.add(key)
                items.append(it)
        if fetch is get:
            time.sleep(2)
    return items, failed


def article_row(item, member):
    dois = [r["DOI"].strip() for r in item.get("reference") or []
            if r.get("DOI") and r.get("doi-asserted-by") == "publisher"]
    dashed = [d for d in dois if has_dash(d)]
    issued = [p for p in (((item.get("issued") or {}).get("date-parts") or [[]])[0] or []) if p is not None]
    return {"doi": item.get("DOI", ""), "member": member, "publisher": item.get("publisher", ""),
            "journal": " ".join(item.get("container-title") or [])[:120],
            "issued": "-".join(str(p) if i == 0 else "%02d" % p for i, p in enumerate(issued)),
            "references": len(item.get("reference") or []), "publisher_dois": len(dois),
            "hyphen_dois": sum(1 for d in dois if has_hyphen(d)), "dash_dois": len(dashed),
            "dash_codes": sorted({c for d in dashed for c in dash_codes(d)}),
            "dashed": dashed,
            "ascii_hyphen": [d for d in dois if "-" in d and not has_dash(d)],
            "plain": [d for d in dois if not has_dash(d)]}


def member_summary(rows):
    hy = [r for r in rows if r["hyphen_dois"]]
    k = sum(1 for r in hy if r["dash_dois"])
    lo, hi = wilson(k, len(hy))
    hd = sum(r["hyphen_dois"] for r in rows)
    dd = sum(r["dash_dois"] for r in rows)
    names = collections.Counter(r["publisher"] for r in rows)
    return {"publisher": names.most_common(1)[0][0] if names else "", "articles": len(rows),
            "with_publisher_dois": sum(1 for r in rows if r["publisher_dois"]),
            "with_hyphen_dois": len(hy), "affected": k, "share": share(k, len(hy)), "lo": lo, "hi": hi,
            "mixed": sum(1 for r in rows if r["dash_dois"] and r["ascii_hyphen"]),
            "hyphen_dois": hd, "dash_dois": dd, "doi_share": share(dd, hd),
            "dash_codes": sorted({c for r in rows for c in r["dash_codes"]})}


def breakdown(rows, key):
    """Affected / with-hyphen-DOIs per value of key (journal or month), largest first."""
    tab = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["hyphen_dois"]:
            v = r[key] if key != "month" else r["issued"][:7]
            tab[v][1] += 1
            tab[v][0] += 1 if r["dash_dois"] else 0
    return sorted(([v, a, n] for v, (a, n) in tab.items()), key=lambda x: (-x[2], x[0]))


def pick(pool, n, rng):
    pool = sorted(pool)
    return rng.sample(pool, min(n, len(pool)))


# ---- resolution ---------------------------------------------------------------------------------

class Lookup:
    """Crossref, then doi.org; cached by lower-case DOI."""

    def __init__(self, fetch=get):
        self.fetch, self.cache, self.calls = fetch, {}, 0

    def resolve(self, doi):
        """'crossref' | 'other-ra' | 'not-found' | 'error'."""
        key = doi.lower()
        if key not in self.cache:
            self.calls += 1
            if self.fetch is get:
                time.sleep(0.1)
            status, _ = self.fetch(CROSSREF + "/" + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
            if status == 200:
                self.cache[key] = "crossref"
            elif status in (400, 404):
                status, _ = self.fetch(HANDLES + urllib.parse.quote(doi, safe="/"))
                self.cache[key] = {200: "other-ra", 404: "not-found", 400: "not-found"}.get(status, "error")
            else:
                self.cache[key] = "error"
        return self.cache[key]


def resolution(pairs, look):
    out = []
    for citing, doi in pairs:
        rec = {"citing": citing, "doi": doi, "raw": look.resolve(doi), "normalised": ""}
        if has_dash(doi):
            rec["normalised"] = look.resolve(normalise(doi))
        out.append(rec)
    return out


# ---- downstream ---------------------------------------------------------------------------------

def oc_cited(citing, fetch=get):
    """Lower-case cited DOIs OpenCitations records for one citing DOI; None if the call failed."""
    status, body = fetch(OPENCITATIONS + urllib.parse.quote(citing, safe="/"), timeout=120)
    if status == 404:
        return set()
    if status != 200:
        return None
    try:
        data = json.loads(body)
    except ValueError:
        return None
    cited = set()
    for row in data if isinstance(data, list) else []:
        for tok in (row.get("cited") or "").split():
            if tok.startswith("doi:"):
                cited.add(tok[4:].lower())
    return cited


def oa_refs(citing, fetch=get):
    """OpenAlex referenced_works of one citing DOI; None if the call failed."""
    url = OPENALEX + "/doi:" + urllib.parse.quote(citing, safe="/") + "?select=id,referenced_works&mailto=" + MAILTO
    status, body = fetch(url)
    if status == 404:
        return set()
    if status != 200:
        return None
    return set(json.loads(body).get("referenced_works") or [])


def oa_ids(dois, fetch=get):
    """lower-case DOI -> OpenAlex work id, 50 DOIs per call (DOIs with ',' or '|' are skipped)."""
    out = {}
    todo = sorted({d.lower() for d in dois if "," not in d and "|" not in d})
    for i in range(0, len(todo), 50):
        chunk = ["https://doi.org/" + d for d in todo[i:i + 50]]
        q = urllib.parse.urlencode({"filter": "doi:" + "|".join(chunk), "select": "id,doi",
                                    "per-page": "50", "mailto": MAILTO})
        status, body = fetch(OPENALEX + "?" + q)
        if status != 200:
            continue
        for w in json.loads(body).get("results") or []:
            d = (w.get("doi") or "").lower().replace("https://doi.org/", "")
            if d:
                out[d] = w.get("id")
        if fetch is get:
            time.sleep(0.2)
    return out


def citation_check(dash_sample, rows_by_doi, rng, fetch=get):
    groups = {}
    for citing, doi in dash_sample:
        groups.setdefault(citing, []).append(normalise(doi).lower())
    recs = []
    for citing in sorted(groups):
        plain = sorted({d.lower() for d in rows_by_doi[citing.lower()]["plain"]})
        controls = rng.sample(plain, min(N_CONTROLS, len(plain)))
        oc = oc_cited(citing, fetch)
        oa = oa_refs(citing, fetch)
        recs.append({"citing": citing, "dashed": groups[citing], "controls": controls,
                     "oc_error": oc is None, "oc_indexed": bool(oc),
                     "oc_dashed": [d in oc for d in groups[citing]] if oc else [],
                     "oc_controls": [d in oc for d in controls] if oc else [],
                     "oa_error": oa is None, "oa_refs": sorted(oa or [])})
        if fetch is get:
            time.sleep(1)
    ids = oa_ids([d for r in recs for d in r["dashed"] + r["controls"]], fetch)
    for r in recs:
        refs = set(r.pop("oa_refs"))
        r["oa_indexed"] = bool(refs)
        r["oa_dashed"] = [(ids[d] in refs) if d in ids else None for d in r["dashed"]] if refs else []
        r["oa_controls"] = [(ids[d] in refs) if d in ids else None for d in r["controls"]] if refs else []
    return recs


# ---- verdicts -----------------------------------------------------------------------------------

def presence(recs, flag, key):
    vals = [v for r in recs if r[flag] for v in r[key] if v is not None]
    return sum(1 for v in vals if v), len(vals)


def verdicts(summ, res_dash, res_ctrl, cites):
    v = {}
    w = summ[WILEY]
    v["H1"] = {"k": w["affected"], "n": w["with_hyphen_dois"], "share": w["share"], "ci": [w["lo"], w["hi"]],
               "verdict": "supported" if w["lo"] is not None and w["lo"] > 0.05 else "not supported"}
    h2 = {}
    for m, s in summ.items():
        if m == WILEY:
            continue
        verdict = "no data" if s["share"] is None else ("holds" if s["share"] <= 0.02 else "fails")
        h2[m] = {"publisher": s["publisher"], "k": s["affected"], "n": s["with_hyphen_dois"], "share": s["share"],
                 "ci": [s["lo"], s["hi"]], "verdict": verdict}
    v["H2"] = {"members": h2, "holds": sum(1 for x in h2.values() if x["verdict"] == "holds"),
               "fails": sum(1 for x in h2.values() if x["verdict"] == "fails")}
    v["H3"] = {"dash_dois": w["dash_dois"], "hyphen_dois": w["hyphen_dois"], "share": w["doi_share"],
               "verdict": "supported" if (w["doi_share"] or 0) >= 0.20 else "not supported"}
    raw = [r["raw"] for r in res_dash if r["raw"] != "error"]
    norm = [r["normalised"] for r in res_dash if r["normalised"] != "error"]
    ctrl = [r["raw"] for r in res_ctrl if r["raw"] != "error"]
    a = share(sum(1 for s in raw if s in RESOLVES), len(raw))
    b = share(sum(1 for s in norm if s in RESOLVES), len(norm))
    c = share(sum(1 for s in ctrl if s in RESOLVES), len(ctrl))
    ok = None not in (a, b, c) and a <= 0.05 and b >= 0.90 and c >= 0.90
    v["H4"] = {"dash_n": len(res_dash), "dash_raw_resolves": a, "dash_normalised_resolves": b,
               "control_n": len(res_ctrl), "control_resolves": c,
               "errors": len(res_dash) - len(raw) + len(res_dash) - len(norm) + len(res_ctrl) - len(ctrl),
               "verdict": "supported" if ok else ("not testable" if None in (a, b, c) else "not supported")}
    for name, flag, pre, lim in (("H5", "oa_indexed", "oa", 0.20), ("H6", "oc_indexed", "oc", 0.10)):
        n_art = sum(1 for r in cites if r[flag])
        dk, dn = presence(cites, flag, pre + "_dashed")
        ck, cn = presence(cites, flag, pre + "_controls")
        ds, cs = share(dk, dn), share(ck, cn)
        if n_art < 20 or ds is None or cs is None:
            verdict = "not testable"
        else:
            verdict = "supported" if ds <= lim and cs >= 0.80 else "not supported"
        v[name] = {"articles": n_art, "dash_present": [dk, dn], "dash_share": ds,
                   "control_present": [ck, cn], "control_share": cs,
                   "errors": sum(1 for r in cites if r[pre + "_error"]), "verdict": verdict}
    return v


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def report(summ, v, wiley_rows, draws_log):
    lines = ["# Reference-dash census v1: results (generated)", "",
             "Pre-registration: findings/reference-dash-census-prereg-v1-2026-10-16.md", "",
             "## Sample", ""]
    lines += ["- member %s: %d draws, %d failed, %d articles" % (d["member"], d["draws"], d["failed"], d["articles"])
              for d in draws_log]
    lines += ["", "## Per member (articles with >=1 hyphen-bearing publisher-asserted DOI)", "",
              "| member | publisher | articles | with hyphen DOIs | affected | share (Wilson 95% CI) | mixed |"
              " DOI share | dash codes |", "|---|---|---|---|---|---|---|---|---|"]
    for m, s in summ.items():
        ci = "n/a" if s["lo"] is None else "%s-%s" % (pct(s["lo"]), pct(s["hi"]))
        lines.append("| %s | %s | %d | %d | %d | %s (%s) | %d | %s | %s |" % (
            m, s["publisher"], s["articles"], s["with_hyphen_dois"], s["affected"], pct(s["share"]), ci,
            s["mixed"], pct(s["doi_share"]), " ".join(s["dash_codes"])))
    lines += ["", "## Hypotheses", ""]
    h1 = v["H1"]
    lines.append("- H1 Wiley article share: %d/%d = %s (CI %s-%s): %s" % (
        h1["k"], h1["n"], pct(h1["share"]), pct(h1["ci"][0]), pct(h1["ci"][1]), h1["verdict"]))
    lines.append("- H2 other members: holds %d, fails %d" % (v["H2"]["holds"], v["H2"]["fails"]))
    for m, x in v["H2"]["members"].items():
        lines.append("  - %s %s: %d/%d = %s: %s" % (m, x["publisher"], x["k"], x["n"], pct(x["share"]), x["verdict"]))
    h3 = v["H3"]
    lines.append("- H3 Wiley DOI share: %d/%d = %s: %s" % (h3["dash_dois"], h3["hyphen_dois"], pct(h3["share"]),
                                                          h3["verdict"]))
    h4 = v["H4"]
    lines.append("- H4 resolution: dash raw %s, dash normalised %s (n %d); control %s (n %d); errors %d: %s" % (
        pct(h4["dash_raw_resolves"]), pct(h4["dash_normalised_resolves"]), h4["dash_n"],
        pct(h4["control_resolves"]), h4["control_n"], h4["errors"], h4["verdict"]))
    for name in ("H5", "H6"):
        x = v[name]
        lines.append("- %s %s: %d articles; dash present %d/%d (%s); control present %d/%d (%s); errors %d: %s" % (
            name, "OpenAlex" if name == "H5" else "OpenCitations", x["articles"], x["dash_present"][0],
            x["dash_present"][1], pct(x["dash_share"]), x["control_present"][0], x["control_present"][1],
            pct(x["control_share"]), x["errors"], x["verdict"]))
    lines += ["", "## Exploratory: Wiley by journal (affected / with hyphen DOIs; top 25)", ""]
    lines += ["- %s: %d/%d" % (j, a, n) for j, a, n in breakdown(wiley_rows, "journal")[:25]]
    lines += ["", "## Exploratory: Wiley by month", ""]
    lines += ["- %s: %d/%d" % (mo, a, n) for mo, a, n in sorted(breakdown(wiley_rows, "month"))]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(SEED)
    rows, draws_log = [], []
    for member, draws in MEMBERS:
        items, failed = draw(member, draws)
        draws_log.append({"member": member, "draws": draws, "failed": failed, "articles": len(items)})
        rows.extend(article_row(it, member) for it in items)
        print(json.dumps(draws_log[-1]), flush=True)
    summ = {m: member_summary([r for r in rows if r["member"] == m]) for m, _ in MEMBERS}
    wiley = [r for r in rows if r["member"] == WILEY]
    dash_sample = pick([(r["doi"], d) for r in wiley for d in r["dashed"]], N_RESOLVE, rng)
    ctrl_sample = pick([(r["doi"], d) for r in wiley for d in r["ascii_hyphen"]], N_RESOLVE, rng)
    look = Lookup()
    res_dash = resolution(dash_sample, look)
    res_ctrl = resolution(ctrl_sample, look)
    print("resolution done: %d lookups" % look.calls, flush=True)
    cites = citation_check(dash_sample, {r["doi"].lower(): r for r in rows}, rng)
    v = verdicts(summ, res_dash, res_ctrl, cites)
    with open(os.path.join(args.out, "articles.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"draws": draws_log, "members": summ, "verdicts": v, "lookups": look.calls}, f, indent=1)
    with open(os.path.join(args.out, "resolution.jsonl"), "w", encoding="utf-8") as f:
        for r in res_dash + res_ctrl:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out, "citations.jsonl"), "w", encoding="utf-8") as f:
        for r in cites:
            f.write(json.dumps(r) + "\n")
    text = report(summ, v, wiley, draws_log)
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
