#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""phantom_refs: do 2026 meta-analyses cite references that cannot be verified?

Pre-registered in prereg-phantom-included-studies-v1.md (written before any data were read).
Standard library only.

  python phantom_refs.py --out /out [--n 240] [--deadline-min 200]

Sampling frame: PubMed meta-analysis[pt], 2026[dp], Entrez date 2026-01-01..2026-10-15, fetched in
monthly windows (esearch returns at most 9,999 ids), sorted by PMID; pick k (0..n-1) is
frame[floor(k * N / n)]. Picks are processed in a fixed hash order so that, if the deadline stops
the run early, the processed picks are still spread over the whole frame.

For each pick: its DOI (PubMed), its reference list (Crossref), and for every reference whose DOI
the publisher asserted: does the DOI exist (Crossref, then doi.org's handle API), and does the
title it resolves to match the reference's own title? Mismatched and missing DOIs are then searched
in Crossref by the reference's text; a reference whose text finds no matching work is a candidate
for the manual check (flags.jsonl). Nothing here says a reference is fabricated: that needs the
manual reads set out in the pre-registration.
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "mv2@munimtech.com"
UA = "mv2-munim-phantom-refs/1.0 (mailto:%s)" % MAILTO
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL = {"tool": "mv2-munim-phantom-refs", "email": MAILTO}
CROSSREF = "https://api.crossref.org/works"
HANDLES = "https://doi.org/api/handles/"
TERM = "meta-analysis[pt] AND 2026[dp] AND %s:%s[edat]"
WINDOWS = [("2026/%02d/01" % m, "2026/%02d/%02d" % (m, d)) for m, d in
           [(1, 31), (2, 28), (3, 31), (4, 30), (5, 31), (6, 30), (7, 31), (8, 31), (9, 30), (10, 15)]]
SEED = "phantom-v1"
MATCH_MIN = 0.5   # title containment at or above this: the DOI points at the cited work
FOUND_MIN = 0.8   # a Crossref search hit at or above this: the cited work exists under another DOI
STOP = set("""
the and for with from into of in on a an to by at or as is are was were be its their this that these those
than via versus vs
""".split())
DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
FLAGGED = ("mismatch", "not-found")
STATUSES = ("match", "mismatch", "short", "untitled", "other-ra", "not-found", "error")
OUTCOMES = ("unresolved", "real-work-other-doi", "search-returns-cited", "no-text", "search-error")


def get(url, timeout=60, tries=4):
    """(status, body). 400/404 come back at once; other errors back off and retry; (None, msg) if all fail."""
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


# ---------- text ----------

def tokens(text):
    """Lower-case ASCII word tokens with markup, accents and a few stopwords removed."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return [w for w in re.findall(r"[a-z0-9]+", text) if w not in STOP and (len(w) > 2 or w.isdigit())]


def containment(a, b):
    """Share of a's distinct tokens that are also in b."""
    a, b = set(a), set(b)
    return len(a & b) / len(a) if a else 0.0


def ref_text(ref):
    """('title', text), ('unstructured', text) or ('', '') for a Crossref reference entry."""
    title = (ref.get("article-title") or "").strip()
    if len(set(tokens(title))) >= 3:
        return "title", title
    unstructured = (ref.get("unstructured") or "").strip()
    if unstructured:
        return "unstructured", unstructured
    return "", ""


def similarity(kind, text, actual):
    at, rt = tokens(actual), tokens(text)
    if kind == "title":
        return max(containment(at, rt), containment(rt, at))
    return containment(at, rt)  # an unstructured string also holds authors, journal and pages


def judge(ref, actual_title):
    """('match' | 'mismatch' | 'short' | 'untitled', similarity or None)."""
    if len(set(tokens(actual_title))) < 3:
        return "short", None
    kind, text = ref_text(ref)
    if not kind:
        return "untitled", None
    s = similarity(kind, text, actual_title)
    return ("match" if s >= MATCH_MIN else "mismatch"), round(s, 3)


def clean_doi(doi):
    """The DOI without a URL/doi: prefix, spaces, trailing punctuation or an unbalanced closing bracket."""
    d = DOI_PREFIX.sub("", (doi or "").strip())
    d = re.sub(r"\s+", "", d)
    while d and d[-1] in ".,;:'\"":
        d = d[:-1]
    while d.endswith(")") and d.count(")") > d.count("("):
        d = d[:-1]
    while d.endswith("]") and d.count("]") > d.count("["):
        d = d[:-1]
    return d


# ---------- sampling ----------

def picks(frame, n):
    m = len(frame)
    return [frame[(k * m) // n] for k in range(n)]


def order(n):
    return sorted(range(n), key=lambda k: hashlib.sha256(("%s:%d" % (SEED, k)).encode()).hexdigest())


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


# ---------- network ----------

def eutil(name, params):
    time.sleep(0.4)  # NCBI asks for at most 3 requests a second without a key
    status, body = get(EUTILS + name + ".fcgi?" + urllib.parse.urlencode(dict(params, **TOOL)), timeout=120)
    if status != 200:
        raise RuntimeError("%s failed: %s %s" % (name, status, body[:200]))
    return json.loads(body)


def sampling_frame():
    pmids, windows = set(), []
    for lo, hi in WINDOWS:
        res = eutil("esearch", {"db": "pubmed", "term": TERM % (lo, hi), "retmax": 9999, "retmode": "json"})
        res = res["esearchresult"]
        count, ids = int(res["count"]), res.get("idlist") or []
        if count > 9999 or len(ids) != count:
            raise RuntimeError("window %s-%s: count %d, ids %d" % (lo, hi, count, len(ids)))
        windows.append({"from": lo, "to": hi, "count": count})
        pmids.update(ids)
    whole = eutil("esearch", {"db": "pubmed", "term": TERM % ("2026/01/01", "2026/10/15"), "retmax": 0,
                              "retmode": "json"})
    return sorted(pmids, key=int), windows, int(whole["esearchresult"]["count"])


def pubmed_meta(pmids):
    out = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        res = eutil("esummary", {"db": "pubmed", "id": ",".join(batch), "retmode": "json"}).get("result") or {}
        for p in batch:
            rec = res.get(p) or {}
            doi = next((a.get("value", "").strip() for a in rec.get("articleids") or [] if a.get("idtype") == "doi"), "")
            out[p] = {"doi": doi, "title": rec.get("title", ""), "journal": rec.get("source", "")}
    return out


class Lookup:
    """Crossref and doi.org lookups, cached by lower-case DOI."""

    def __init__(self):
        self.titles, self.handles, self.calls = {}, {}, 0

    def _get(self, url):
        self.calls += 1
        time.sleep(0.1)
        return get(url)

    def work(self, doi):
        """('found', message) | ('absent', None) | ('error', None)."""
        status, body = self._get(CROSSREF + "/" + urllib.parse.quote(doi, safe="/") + "?mailto=" + MAILTO)
        if status == 200:
            try:
                return "found", json.loads(body).get("message") or {}
            except ValueError:
                return "error", None
        return ("absent", None) if status in (400, 404) else ("error", None)

    def title(self, doi):
        key = doi.lower()
        if key not in self.titles:
            state, msg = self.work(doi)
            self.titles[key] = {"status": state, "title": " ".join((msg or {}).get("title") or [])}
        return self.titles[key]

    def handle(self, doi):
        """'exists' | 'not-found' | 'invalid' | 'error' at doi.org."""
        key = doi.lower()
        if key not in self.handles:
            status, _ = self._get(HANDLES + urllib.parse.quote(doi, safe="/"))
            self.handles[key] = {200: "exists", 404: "not-found", 400: "invalid"}.get(status, "error")
        return self.handles[key]

    def biblio(self, query):
        """Top Crossref hits for a free-text reference, or None on error."""
        q = urllib.parse.urlencode({"query.bibliographic": query, "rows": 5, "select": "DOI,title", "mailto": MAILTO})
        status, body = self._get(CROSSREF + "?" + q)
        if status != 200:
            return None
        try:
            items = (json.loads(body).get("message") or {}).get("items") or []
        except ValueError:
            return None
        return [{"doi": it.get("DOI", ""), "title": " ".join(it.get("title") or [])} for it in items]


# ---------- audit ----------

def check_ref(ref, look):
    """Resolve one publisher-asserted DOI: status in STATUSES; 'fixed' is the cleaned DOI if only it resolved."""
    raw = (ref.get("DOI") or "").strip()
    rec = {"key": ref.get("key", ""), "doi": raw, "fixed": ""}
    cleaned = clean_doi(raw)
    for d in [raw] + ([cleaned] if cleaned and cleaned != raw else []):
        fixed = d if d != raw else ""
        cr = look.title(d)
        if cr["status"] == "error":
            rec["status"] = "error"
            return rec
        if cr["status"] == "found":
            verdict, sim = judge(ref, cr["title"])
            rec.update(status=verdict, sim=sim, actual=cr["title"][:300], fixed=fixed)
            return rec
        h = look.handle(d)
        if h == "exists":
            rec.update(status="other-ra", fixed=fixed)
            return rec
        if h == "error":
            rec["status"] = "error"
            return rec
    rec["status"] = "not-found"
    return rec


def search(ref, cited, look):
    """Look for the cited work by its text: {'outcome': one of OUTCOMES, ...}."""
    kind, text = ref_text(ref)
    if not kind:
        return {"outcome": "no-text"}
    if kind == "title":
        query = " ".join(x for x in [text, ref.get("author") or "", ref.get("journal-title") or "",
                                     ref.get("year") or ""] if x)
    else:
        query = text
    hits = look.biblio(query[:300])
    if hits is None:
        return {"outcome": "search-error"}
    scored = [(similarity(kind, text, h["title"]), h["doi"], h["title"]) for h in hits
              if len(set(tokens(h["title"]))) >= 3]
    best = max(scored, default=(0.0, "", ""))
    found = {"best_sim": round(best[0], 3), "best_doi": best[1], "best_title": best[2][:300]}
    if best[0] < FOUND_MIN:
        found["outcome"] = "unresolved"
    elif best[1].lower() == cited.lower():
        found["outcome"] = "search-returns-cited"  # the title check was wrong, not the DOI
    else:
        found["outcome"] = "real-work-other-doi"
    return found


def audit_ma(pmid, meta, look):
    """(row, flags) for one sampled meta-analysis."""
    row = {"pmid": pmid, "doi": meta.get("doi", ""), "journal": meta.get("journal", "")}
    if not row["doi"]:
        row["status"] = "no-doi"
        return row, []
    state, msg = look.work(row["doi"])
    if state != "found":
        row["status"] = "not-in-crossref" if state == "absent" else "error"
        return row, []
    refs = msg.get("reference") or []
    row["n_refs"] = len(refs)
    row["references_count"] = msg.get("references-count", msg.get("reference-count"))
    if not refs:
        row["status"] = "no-references"
        return row, []
    row["status"] = "audited"
    counts, flags = {}, []

    def bump(name):
        counts[name] = counts.get(name, 0) + 1

    for ref in refs:
        if not ref.get("DOI"):
            bump("no-doi")
            continue
        if ref.get("doi-asserted-by") != "publisher":
            bump("crossref-asserted")
            continue
        rec = check_ref(ref, look)
        bump(rec["status"])
        if rec["fixed"]:
            bump("fixed")
        if rec["status"] in FLAGGED:
            rec.update(search(ref, rec["fixed"] or rec["doi"], look))
            bump(rec["outcome"])
            rec["pmid"] = pmid
            rec["ref"] = {k: ref.get(k) for k in ("article-title", "unstructured", "author", "year",
                                                   "journal-title", "volume", "first-page") if ref.get(k)}
            flags.append(rec)
    row["counts"] = counts
    return row, flags


def summarise(rows, flags, n_planned):
    audited = [r for r in rows if r["status"] == "audited"]
    totals = {}
    for r in audited:
        for name, c in r["counts"].items():
            totals[name] = totals.get(name, 0) + c
    n = len(audited)
    checked = sum(totals.get(s, 0) for s in STATUSES if s != "error")
    with_unresolved = sum(1 for r in audited if r["counts"].get("unresolved", 0))
    with_flag = sum(1 for r in audited if any(r["counts"].get(s, 0) for s in FLAGGED))
    status_counts = {}
    for r in rows:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    unresolved_refs = totals.get("unresolved", 0)
    return {
        "n_planned": n_planned,
        "n_processed": len(rows),
        "ma_status": status_counts,
        "n_audited": n,
        "reference_totals": totals,
        "publisher_dois_checked": checked,
        "primary_mas_with_unresolved": with_unresolved,
        "primary_share": with_unresolved / n if n else 0.0,
        "primary_wilson95": wilson(with_unresolved, n),
        "mas_with_any_flag": with_flag,
        "unresolved_refs": unresolved_refs,
        "unresolved_per_checked": unresolved_refs / checked if checked else 0.0,
        "unresolved_per_checked_wilson95": wilson(unresolved_refs, checked),
        "n_flags": len(flags),
    }


def results_md(s, frame_info):
    lo, hi = s["primary_wilson95"]
    rlo, rhi = s["unresolved_per_checked_wilson95"]
    t = s["reference_totals"]
    lines = [
        "# Phantom included studies v1: job output (candidates only; the manual check is still to come)",
        "",
        "- Frame: %d PMIDs (whole-range count %d), sha256 %s" % (frame_info["n"], frame_info["count_whole"],
                                                                  frame_info["sha256"]),
        "- Picks processed: %d of %d; audited (reference list deposited): %d" % (s["n_processed"], s["n_planned"],
                                                                                s["n_audited"]),
        "- Meta-analysis status: %s" % json.dumps(s["ma_status"], sort_keys=True),
        "- Publisher-asserted DOIs checked: %d" % s["publisher_dois_checked"],
        "- Reference outcomes: %s" % json.dumps(t, sort_keys=True),
        "",
        "## Pre-registered job outputs",
        "- **Primary (candidate):** meta-analyses with >=1 unresolved reference: %d / %d = %.1f%% (Wilson 95%% CI "
        "%.1f-%.1f%%)" % (s["primary_mas_with_unresolved"], s["n_audited"], 100 * s["primary_share"], 100 * lo, 100 * hi),
        "- Unresolved references per checked publisher DOI: %d / %d = %.2f%% (%.2f-%.2f%%)" % (
            s["unresolved_refs"], s["publisher_dois_checked"], 100 * s["unresolved_per_checked"], 100 * rlo, 100 * rhi),
        "- Meta-analyses with any mismatched or missing DOI: %d" % s["mas_with_any_flag"],
        "- DOIs that resolve only after cleaning (malformed but fixable): %d" % t.get("fixed", 0),
        "- Cited work found in Crossref under another DOI (citation error, not fabrication): %d"
        % t.get("real-work-other-doi", 0),
        "",
        "An unresolved reference is a candidate only. Each one is read by hand (PubMed, Europe PMC and the journal) "
        "before anything is called unverifiable, and then classed as an included study or background.",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--deadline-min", type=float, default=200)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    started = time.time()

    frame, windows, count_whole = sampling_frame()
    frame_text = "\n".join(frame) + "\n"
    frame_info = {"n": len(frame), "count_whole": count_whole, "windows": windows,
                  "sha256": hashlib.sha256(frame_text.encode()).hexdigest()}
    with open(os.path.join(args.out, "frame.txt"), "w") as f:
        f.write(frame_text)
    print("frame: %d PMIDs (whole-range count %d)" % (len(frame), count_whole), flush=True)
    if len(frame) < args.n:
        raise SystemExit("frame smaller than n")

    chosen = picks(frame, args.n)
    meta = pubmed_meta(chosen)
    look = Lookup()
    rows, flags = [], []
    deadline = started + args.deadline_min * 60
    with open(os.path.join(args.out, "mas.jsonl"), "w") as fm, open(os.path.join(args.out, "flags.jsonl"), "w") as ff:
        for i, k in enumerate(order(args.n)):
            if time.time() > deadline:
                print("deadline reached after %d picks" % i, flush=True)
                break
            pmid = chosen[k]
            row, found = audit_ma(pmid, meta.get(pmid) or {}, look)
            row["k"] = k
            rows.append(row)
            flags.extend(found)
            fm.write(json.dumps(row) + "\n")
            fm.flush()
            for rec in found:
                ff.write(json.dumps(rec) + "\n")
            ff.flush()
            print("%3d k=%3d pmid=%s %s %s" % (i, k, pmid, row["status"], json.dumps(row.get("counts", {}))),
                  flush=True)

    s = summarise(rows, flags, args.n)
    s["frame"] = frame_info
    s["lookups"] = look.calls
    s["minutes"] = round((time.time() - started) / 60, 1)
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(s, f, indent=1)
    with open(os.path.join(args.out, "results.md"), "w") as f:
        f.write(results_md(s, frame_info))
    print(results_md(s, frame_info))


if __name__ == "__main__":
    main()
