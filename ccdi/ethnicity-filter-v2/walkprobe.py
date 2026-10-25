"""Pre-registered follow-up of ccdi/ethnicity-filter-v1 (ccdi/ethnicity-filter-v2; predictions
F1-F6 in README.md): can a client page through the federation's ethnicity filter, and does
the filter reach every subject served with that value?

Live part: three walks of /subject at per_page 100, each filtered by one ethnicity value
("Not reported", "Unknown", "Hispanic or Latino"); sequential GET requests, 2 s apart. Each
walk asks for page 1, reads its target source's total there, then asks for pages
2..ceil(total / 100), at most 120 pages. Offline part: the ethnicity values each source
serves in the newest saved snapshot under the data folder (the census's snapshot format).

Only aggregates leave the job: per response its status, size and SHA-256; per source its
reported total, the number of entries served, the kinds of any error objects and a count of
the ethnicity values served. No record or identifier is written out, and no query by
participant ID is sent.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import glob
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FED = "https://federation.ccdi.cancer.gov/api/v1"
UA = "MV2 of Munim, Inc. (mv2@munimtech.com); aggregate data-quality study; sequential requests"
PAUSE = 2
PER_PAGE = 100
MAX_PAGES = 120
WALKS = (("not-reported", "Not reported", "stjude"),
         ("unknown", "Unknown", "kidsfirst"),
         ("hispanic", "Hispanic or Latino", "stjude"))
MISSING = "<missing>"
PAGE = re.compile(r"^page-(\d+)\.json\.gz$")
STAMP = re.compile(r"(\d{8}T\d{6}Z)")


def url_of(ethnicity, page):
    params = {"page": page, "per_page": PER_PAGE, "ethnicity": ethnicity}
    return FED + "/subject?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def get(url, tries=3, wait=30):
    """(status, body, seconds). 5xx and network errors are retried."""
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.status, r.read(), time.time() - t0
        except urllib.error.HTTPError as err:
            if err.code < 500 or i == tries - 1:
                return err.code, err.read(), time.time() - t0
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
            if i == tries - 1:
                return -1, str(err).encode(), time.time() - t0
        time.sleep(wait * (i + 1))


def val(x):
    return x.get("value") if isinstance(x, dict) else x


def eth_value(rec):
    """The ethnicity value an entry is served with, or MISSING."""
    md = rec.get("metadata") if isinstance(rec, dict) else None
    v = val(md.get("ethnicity")) if isinstance(md, dict) else None
    return MISSING if v is None or v == "" else str(v)


def error_kinds(errs):
    if errs is None:
        return []
    if not isinstance(errs, list):
        return ["?"]
    return sorted({str(e.get("kind")) if isinstance(e, dict) else "?" for e in errs})


def one(mapping, name):
    """The single value whose key is name (any case), else None."""
    hits = [v for k, v in (mapping or {}).items() if str(k).lower() == name]
    return hits[0] if len(hits) == 1 else None


def page_sources(parsed):
    """{source: {"all", "entries", "error", "error_kinds", "values"}} for one /subject page."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        summary = item.get("summary")
        counts = summary.get("counts") if isinstance(summary, dict) else None
        data = item.get("data")
        values = collections.Counter(eth_value(r) for r in data) if isinstance(data, list) else {}
        out[str(item["source"])] = {
            "all": counts.get("all") if isinstance(counts, dict) else None,
            "entries": len(data) if isinstance(data, list) else None,
            "error": "errors" in item,
            "error_kinds": error_kinds(item.get("errors")),
            "values": dict(values)}
    return out


def clean_total(item):
    """counts.all of an item without an error object, else None."""
    if item is None or item["error"] or type(item["all"]) is not int:
        return None
    return item["all"]


def by_source(pages):
    """Per source, over the pages of one walk: pages it appeared on, entries served, pages
    with an error object, the error kinds, the totals seen, the values served and its clean
    total on page 1."""
    out = {}
    for p in pages:
        for src, it in p["sources"].items():
            s = out.setdefault(src, {"pages": 0, "entries": 0, "error_pages": 0, "error_kinds": [],
                                     "totals": [], "values": {}, "first_total": None})
            s["pages"] += 1
            if p["page"] == 1:
                s["first_total"] = clean_total(it)
            if it["error"]:
                s["error_pages"] += 1
            s["error_kinds"] = sorted(set(s["error_kinds"]) | set(it["error_kinds"]))
            if isinstance(it["entries"], int):
                s["entries"] += it["entries"]
            if it["all"] not in s["totals"]:
                s["totals"].append(it["all"])
            for v, c in it["values"].items():
                s["values"][v] = s["values"].get(v, 0) + c
    return out


def walk(request, name, ethnicity, target):
    """Pages 1..ceil(target's page-1 total / PER_PAGE), at most MAX_PAGES (1 if no total)."""
    pages, planned, page = [], 1, 1
    while page <= planned:
        status, body, secs = request(url_of(ethnicity, page))
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = None
        srcs = page_sources(parsed)
        pages.append({"page": page, "status": status, "bytes": len(body),
                      "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 1),
                      "sources": srcs})
        print(name, page, status, len(body), "bytes", round(secs, 1), "s", flush=True)
        if page == 1:
            t = clean_total(one(srcs, target))
            planned = min(MAX_PAGES, max(1, math.ceil(t / PER_PAGE))) if t else 1
        page += 1
    return {"name": name, "ethnicity": ethnicity, "target": target, "pages_planned": planned,
            "statuses": sorted({p["status"] for p in pages}), "by_source": by_source(pages),
            "pages": pages}


def run_walks(fetch, pause):
    calls = []

    def request(url):
        if calls:
            time.sleep(pause)
        calls.append(url)
        return fetch(url)
    return {name: walk(request, name, eth, target) for name, eth, target in WALKS}


# ---------- the saved snapshot ----------

def load(path):
    """The parsed JSON body of a saved response, or None if it is missing or unreadable."""
    if not os.path.exists(path):
        return None
    try:
        with gzip.open(path, "rb") as fh:
            return json.loads(fh.read())
    except (OSError, EOFError, ValueError):
        return None


def find_snapshot(root):
    """The snapshot folder under root with the newest time stamp in its path, else None."""
    cands = glob.glob(os.path.join(root, "**", "subject", "chosen.json"), recursive=True)
    if not cands:
        return None

    def key(path):
        stamps = STAMP.findall(path)
        return (stamps[-1] if stamps else "", path)
    return os.path.dirname(os.path.dirname(max(cands, key=key)))


def subject_key(rec, src):
    ident = rec.get("id") if isinstance(rec.get("id"), dict) else {}
    ns = ident.get("namespace") if isinstance(ident.get("namespace"), dict) else {}
    return (src, str(ns.get("organization")), str(ns.get("name")), str(ident.get("name")))


def snapshot_values(raw):
    """Per source, the ethnicity values of its distinct served subjects (the census's key:
    source, organization, namespace, name; the first copy counts)."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = {}
    for path in glob.glob(os.path.join(raw, "subject", "page-*.json.gz")):
        m = PAGE.match(os.path.basename(path))
        if m:
            files[int(m.group(1))] = path
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    seen, values = set(), collections.defaultdict(collections.Counter)
    read, unreadable = 0, 0
    for n in sorted(files):
        parsed = load(files[n])
        if not isinstance(parsed, list):
            unreadable += 1
            continue
        read += 1
        for item in parsed:
            if not isinstance(item, dict) or "source" not in item:
                continue
            data = item.get("data")
            if not isinstance(data, list):
                continue
            src = str(item["source"])
            for rec in data:
                if not isinstance(rec, dict):
                    continue
                key = subject_key(rec, src)
                if key in seen:
                    continue
                seen.add(key)
                values[src][eth_value(rec)] += 1
    return {"path": raw, "pages_read": read, "pages_unreadable": unreadable,
            "subjects": {s: sum(c.values()) for s, c in sorted(values.items())},
            "values": {s: dict(c) for s, c in sorted(values.items())}}


# ---------- grades ----------

def grade(walks, snap):
    """F1-F6 exactly as pre-registered in README.md."""
    def ok(name):
        return walks[name]["statuses"] == [200]
    sj_nr = one(walks["not-reported"]["by_source"], "stjude")
    sj_unk = one(walks["unknown"]["by_source"], "stjude")
    sj_h = one(walks["hispanic"]["by_source"], "stjude")
    kf = one(walks["unknown"]["by_source"], "kidsfirst")
    sv = (snap or {}).get("values") or {}
    kf_snap = one(sv, "kidsfirst") or {}
    sj_snap = one(sv, "stjude") or {}
    g = {"F1": (ok("not-reported") and sj_nr is not None and sj_nr["first_total"] is not None
                and sj_nr["first_total"] >= 3000 and sj_nr["entries"] == 0),
         "F2": (ok("unknown") and sj_unk is not None and sj_unk["first_total"] is not None
                and sj_unk["first_total"] >= 1 and sj_unk["entries"] == 0),
         "F3": (ok("hispanic") and sj_h is not None and sj_h["first_total"] is not None
                and sj_h["first_total"] >= 1 and sj_h["error_pages"] == 0
                and sj_h["entries"] == sj_h["first_total"]
                and sj_h["values"] == {"Hispanic or Latino": sj_h["first_total"]}),
         "F4": (ok("unknown") and kf is not None and kf["first_total"] is not None
                and kf["first_total"] >= 1 and kf["error_pages"] == 0
                and kf["pages"] == walks["unknown"]["pages_planned"]
                and kf["entries"] == kf["first_total"]
                and kf["values"] == {"Unknown": kf["first_total"]}),
         "F5": (kf is not None and kf["first_total"] is not None and kf["first_total"] <= 8300
                and kf_snap.get("Unknown", 0) >= 10180),
         "F6": sj_snap.get("Not reported", 0) >= 3000 and sj_snap.get("Unknown", 0) >= 1}
    return {k: "pass" if v else "fail" for k, v in g.items()}


def reading(g, walks):
    """The pre-registered reading of the StJude and KidsFirst results."""
    sj = one(walks["not-reported"]["by_source"], "stjude")
    t = sj["first_total"] if sj else None
    if g["F1"] == "pass" and g["F6"] == "pass":
        stjude = "counted_not_served"
    elif t and sj["entries"] == t:
        stjude = "served_in_full"
    elif t and 0 < sj["entries"] < t:
        stjude = "partial"
    else:
        stjude = "other"
    kidsfirst = "unreached" if g["F4"] == "pass" and g["F5"] == "pass" else "other"
    return {"stjude": stjude, "kidsfirst": kidsfirst}


def main(argv=None, fetch=None, pause=PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="/data")
    args = ap.parse_args(argv)
    walks = run_walks(fetch or get, pause)
    raw = find_snapshot(args.data_dir)
    snap = snapshot_values(raw) if raw else None
    g = grade(walks, snap)
    out = {"probe": "ccdi/ethnicity-filter-v2",
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "grades": g, "reading": reading(g, walks), "snapshot": snap,
           "walks": [walks[n] for n, _, _ in WALKS]}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "walkprobe.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(g, sort_keys=True), json.dumps(out["reading"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
