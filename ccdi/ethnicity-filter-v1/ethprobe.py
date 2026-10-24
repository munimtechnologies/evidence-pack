"""Pre-registered probe of how the CCDI Data Federation answers ethnicity filters
(ccdi/ethnicity-filter-v1; predictions E1-E5 in README.md).

Eight sequential GET requests: /info, /subject/by/ethnicity/count, and /subject at page 1,
per_page 1, once unfiltered and once for each of the five ethnicity values of the Federation
API specification. No query by participant ID is ever sent. Only aggregates leave the job:
status, size, SHA-256, and per source the reported total (counts.all), the number of entries
served and the kinds of any error objects. No record is written out.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FED = "https://federation.ccdi.cancer.gov/api/v1"
UA = "MV2 of Munim, Inc. (mv2@munimtech.com); aggregate data-quality study; sequential requests"
PAUSE = 2
DCC = "ccdi-dcc"
OTHERS = ("kidsfirst", "pcdc", "stjude", "treehouse")
NODE_VALUES = ("Hispanic or Latino", "Not reported")
REQUESTS = (("info", "/info", None),
            ("count", "/subject/by/ethnicity/count", None),
            ("all", "/subject", None),
            ("hispanic", "/subject", "Hispanic or Latino"),
            ("not-reported", "/subject", "Not reported"),
            ("not-hispanic", "/subject", "Not Hispanic or Latino"),
            ("unknown", "/subject", "Unknown"),
            ("not-allowed", "/subject", "Not allowed to collect"))


def url_of(path, ethnicity):
    if path != "/subject":
        return FED + path
    params = {"page": 1, "per_page": 1}
    if ethnicity:
        params["ethnicity"] = ethnicity
    return FED + path + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


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


def error_kinds(errs):
    if errs is None:
        return []
    if not isinstance(errs, list):
        return ["?"]
    return sorted({str(e.get("kind")) if isinstance(e, dict) else "?" for e in errs})


def subject_sources(parsed):
    """{source: {"all", "entries", "error", "error_kinds"}} for an aggregated /subject page."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        summary = item.get("summary")
        counts = summary.get("counts") if isinstance(summary, dict) else None
        data = item.get("data")
        out[str(item["source"])] = {
            "all": counts.get("all") if isinstance(counts, dict) else None,
            "entries": len(data) if isinstance(data, list) else None,
            "error": "errors" in item,
            "error_kinds": error_kinds(item.get("errors"))}
    return out


def count_sources(parsed):
    """{source: {"total", "missing", "values", "error"}} for /subject/by/ethnicity/count."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        vals = item.get("values")
        out[str(item["source"])] = {
            "total": item.get("total"), "missing": item.get("missing"),
            "values": ({str(x.get("value")): x.get("count") for x in vals if isinstance(x, dict)}
                       if isinstance(vals, list) else None),
            "error": "errors" in item}
    return out


def versions(obj, prefix=""):
    """[[path, value]] of every scalar whose key mentions 'version' (for /info)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = prefix + "/" + str(k)
            if isinstance(v, (dict, list)):
                out += versions(v, p)
            elif "version" in str(k).lower():
                out.append([p, v])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            seg = str(v["source"]) if isinstance(v, dict) and "source" in v else str(i)
            out += versions(v, prefix + "/" + seg)
    return out[:100]


def describe(name, path, ethnicity, status, body, secs):
    """The aggregate record of one response."""
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    rec = {"name": name, "path": path, "ethnicity": ethnicity, "status": status,
           "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
           "seconds": round(secs, 1)}
    if path == "/subject":
        rec["sources"] = subject_sources(parsed)
    elif path == "/info":
        rec["info_versions"] = versions(parsed)
    else:
        rec["count"] = count_sources(parsed)
    return rec


def one(sources, name):
    """The single item whose source is name (any case), else None."""
    hits = [v for k, v in (sources or {}).items() if k.lower() == name]
    return hits[0] if len(hits) == 1 else None


def clean_zero(rec):
    """HTTP 200, and CCDI-DCC answers with total 0, no entries and no error object."""
    item = one(rec.get("sources"), DCC)
    return (rec["status"] == 200 and item is not None and not item["error"]
            and item["all"] == 0 and item["entries"] == 0)


def total(item):
    """counts.all of a clean item, else None."""
    if item is None or item["error"] or not isinstance(item["all"], int):
        return None
    return item["all"]


def grade(r):
    """E1-E5 exactly as pre-registered in README.md; r maps request name to its record."""
    nh = r["not-hispanic"]
    others = [total(one(nh.get("sources"), n)) for n in OTHERS]
    h, nr, a = (total(one(r[n].get("sources"), DCC)) for n in ("hispanic", "not-reported", "all"))
    cnt = one(r["count"].get("count"), DCC)
    vals = cnt["values"] if cnt and not cnt["error"] else None
    g = {"E1": clean_zero(nh),
         "E2": nh["status"] == 200 and all(t is not None and t >= 1000 for t in others),
         "E3": clean_zero(r["unknown"]),
         "E4": (all(r[n]["status"] == 200 for n in ("hispanic", "not-reported", "all"))
                and None not in (h, nr, a) and a >= 59000 and h + nr == a),
         "E5": (r["count"]["status"] == 200 and isinstance(vals, dict) and bool(vals)
                and set(vals) <= set(NODE_VALUES))}
    return {k: "pass" if v else "fail" for k, v in g.items()}


def reading(r):
    """Which pre-registered reading of CCDI-DCC's answer to 'Not Hispanic or Latino' applies."""
    nh = r["not-hispanic"]
    item = one(nh.get("sources"), DCC)
    nr = total(one(r["not-reported"].get("sources"), DCC))
    if nh["status"] != 200 or item is None:
        return "missing"
    if item["error"]:
        return "error"
    if item["all"] == 0 and item["entries"] == 0:
        return "silent_zero"
    if isinstance(item["all"], int) and nr and abs(item["all"] - nr) <= 0.02 * nr:
        return "matches_not_reported"
    return "other"


def totals(r):
    """Descriptive: per /subject request, the sum of clean totals over all sources."""
    out = {}
    for name, rec in r.items():
        if rec["path"] == "/subject":
            ts = [total(v) for v in rec["sources"].values()]
            out[name] = {"sum_all": sum(t for t in ts if t is not None),
                         "sources": len(ts),
                         "sources_with_error": sorted(k for k, v in rec["sources"].items()
                                                      if v["error"])}
    return out


def main(argv=None, fetch=None, pause=PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    fetch = fetch or get
    recs = {}
    for i, (name, path, ethnicity) in enumerate(REQUESTS):
        if i:
            time.sleep(pause)
        status, body, secs = fetch(url_of(path, ethnicity))
        recs[name] = describe(name, path, ethnicity, status, body, secs)
        print(name, status, len(body), "bytes", round(secs, 1), "s", flush=True)
    out = {"probe": "ccdi/ethnicity-filter-v1",
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "grades": grade(recs), "reading": reading(recs), "totals": totals(recs),
           "requests": [recs[n] for n, _, _ in REQUESTS]}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "ethprobe.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out["grades"], sort_keys=True), out["reading"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
