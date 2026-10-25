"""Pre-registered census of filter reach in NCI's CCDI Data Federation (ccdi/filter-reach-v1;
predictions R1-R3 and K1-K3 in README.md): for every source, every demographic field the API
filters on (sex, race, ethnicity, vital status) and every value, does the filter's total agree
with the count endpoint, and does it reach every subject served with that value?

Live part, sequential GET requests 2 s apart:
  1. the four count endpoints, /subject/by/<field>/count;
  2. 20 filtered totals, /subject?<field>=<value> at per_page 1 (totals only);
  3. one page of /subject?vital_status=Alive at per_page 100 (what PCDC's entries carry);
  4. two walks of KidsFirst's filtered results at per_page 100, ethnicity=Unknown and
     race=Unknown, pages 1..ceil(KidsFirst's page-1 total / 100), at most 120 pages each.
Offline part: the values each source serves for each field in the newest saved snapshot under
the data folder (the census's format), and, for KidsFirst, which subjects served as "Unknown"
the two walks did not return.

Only aggregates leave the job: per response its status, size and SHA-256; per source, field and
value the served count, the count endpoint's count and the filter's total; for KidsFirst, counts
of unreached subjects by study namespace and by their other values. Subject keys are compared
inside the job only; no record or identifier is written out, and no query by participant ID is
sent.

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
FIELDS = ("sex", "race", "ethnicity", "vital_status")
VALUES = {"sex": ("F", "M", "U"),
          "race": ("American Indian or Alaska Native", "Asian", "Black or African American",
                   "Native Hawaiian or other Pacific Islander", "White", "Unknown",
                   "Not Reported", "Not allowed to collect"),
          "ethnicity": ("Hispanic or Latino", "Not Hispanic or Latino", "Unknown",
                        "Not reported"),
          "vital_status": ("Alive", "Dead", "Unknown", "Not reported", "Unspecified")}
TARGET = "kidsfirst"
WALKS = ("ethnicity", "race")
WALK_VALUE = "Unknown"
OVER = ("vital_status", "Alive")
MISSING = "<missing>"
PAGE = re.compile(r"^page-(\d+)\.json\.gz$")
STAMP = re.compile(r"(\d{8}T\d{6}Z)")

# Thresholds fixed in README.md before the job runs.
MIN_CELLS = 100
GAP_MIN = 10
ETH_GAP = (1900, 2100)
RACE_GAP = (2550, 2750)
PCDC_MIN = {"Alive": 15000, "Dead": 4000, "Unknown": 2000}
NOT_IN_SNAPSHOT_MAX = 10
SHARED, SEPARATE = 0.8, 0.2


def url_of(path, params=()):
    q = urllib.parse.urlencode(list(params), quote_via=urllib.parse.quote)
    return FED + path + ("?" + q if q else "")


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


def values_of(rec, field):
    """The values an entry is served with for field, as a list (race may hold several);
    [MISSING] when it has none."""
    md = rec.get("metadata") if isinstance(rec, dict) else None
    raw = md.get(field) if isinstance(md, dict) else None
    items = raw if isinstance(raw, list) else [raw]
    out = [str(v) for v in (val(x) for x in items) if v is not None and v != ""]
    return out or [MISSING]


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


def subject_key(rec, src):
    ident = rec.get("id") if isinstance(rec.get("id"), dict) else {}
    ns = ident.get("namespace") if isinstance(ident.get("namespace"), dict) else {}
    return (src, str(ns.get("organization")), str(ns.get("name")), str(ident.get("name")))


# ---------- reading responses ----------

def count_items(parsed):
    """{source: {"error", "error_kinds", "total", "missing", "values"}} for a count endpoint."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        values = {}
        for x in item.get("values") or []:
            if isinstance(x, dict) and "value" in x:
                values[str(x.get("value"))] = x.get("count")
        out[str(item["source"])] = {"error": "errors" in item,
                                    "error_kinds": error_kinds(item.get("errors")),
                                    "total": item.get("total"), "missing": item.get("missing"),
                                    "values": values}
    return out


def page_sources(parsed, field, value=None):
    """{source: {"all", "entries", "error", "error_kinds", "values", "with_value"}} for one
    /subject page; values counts every value the entries carry for field."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        summary = item.get("summary")
        counts = summary.get("counts") if isinstance(summary, dict) else None
        data = item.get("data")
        values, with_value = collections.Counter(), 0
        for rec in data if isinstance(data, list) else []:
            vs = values_of(rec, field)
            values.update(vs)
            with_value += value in vs
        out[str(item["source"])] = {
            "all": counts.get("all") if isinstance(counts, dict) else None,
            "entries": len(data) if isinstance(data, list) else None,
            "error": "errors" in item,
            "error_kinds": error_kinds(item.get("errors")),
            "values": dict(values), "with_value": with_value}
    return out


def target_keys(parsed):
    """Subject keys of the target source's entries on one page (kept inside the job)."""
    keys = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or str(item.get("source", "")).lower() != TARGET:
            continue
        data = item.get("data")
        for rec in data if isinstance(data, list) else []:
            if isinstance(rec, dict):
                keys.append(subject_key(rec, str(item["source"])))
    return keys


def clean_total(item):
    """counts.all of an item without an error object, else None."""
    if item is None or item["error"] or type(item["all"]) is not int:
        return None
    return item["all"]


def by_source(pages):
    """Per source, over the pages of one walk: pages it appeared on, entries served, entries
    carrying the walked value, pages with an error object, the error kinds, the totals seen,
    the values served and its clean total on page 1."""
    out = {}
    for p in pages:
        for src, it in p["sources"].items():
            s = out.setdefault(src, {"pages": 0, "entries": 0, "with_value": 0, "error_pages": 0,
                                     "error_kinds": [], "totals": [], "values": {},
                                     "first_total": None})
            s["pages"] += 1
            if p["page"] == 1:
                s["first_total"] = clean_total(it)
            if it["error"]:
                s["error_pages"] += 1
            s["error_kinds"] = sorted(set(s["error_kinds"]) | set(it["error_kinds"]))
            if isinstance(it["entries"], int):
                s["entries"] += it["entries"]
            s["with_value"] += it["with_value"]
            if it["all"] not in s["totals"]:
                s["totals"].append(it["all"])
            for v, c in it["values"].items():
                s["values"][v] = s["values"].get(v, 0) + c
    return out


# ---------- the live part ----------

class Client:
    """Sequential requests, PAUSE seconds apart; logs status, size and SHA-256 of each."""

    def __init__(self, fetch, pause):
        self.fetch, self.pause, self.log = fetch, pause, []

    def json(self, url, label):
        if self.log:
            time.sleep(self.pause)
        status, body, secs = self.fetch(url)
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = None
        self.log.append({"label": label, "status": status, "bytes": len(body),
                         "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 1)})
        print(label, status, len(body), "bytes", round(secs, 1), "s", flush=True)
        return status, parsed


def read_counts(client):
    out = {}
    for field in FIELDS:
        status, parsed = client.json(url_of("/subject/by/%s/count" % field), "count " + field)
        out[field] = {"status": status, "sources": count_items(parsed)}
    return out


def read_filters(client):
    out = {}
    for field in FIELDS:
        out[field] = {}
        for value in VALUES[field]:
            status, parsed = client.json(
                url_of("/subject", [("page", 1), ("per_page", 1), (field, value)]),
                "filter %s=%s" % (field, value))
            out[field][value] = {"status": status, "sources": page_sources(parsed, field, value)}
    return out


def read_over(client):
    field, value = OVER
    status, parsed = client.json(
        url_of("/subject", [("page", 1), ("per_page", PER_PAGE), (field, value)]),
        "page %s=%s" % (field, value))
    return {"field": field, "value": value, "per_page": PER_PAGE, "status": status,
            "sources": page_sources(parsed, field, value)}


def walk(client, field, value):
    """Pages 1..ceil(the target's page-1 total / PER_PAGE), at most MAX_PAGES (1 if no total)."""
    pages, keys, planned, page = [], [], 1, 1
    while page <= planned:
        status, parsed = client.json(
            url_of("/subject", [("page", page), ("per_page", PER_PAGE), (field, value)]),
            "walk %s=%s page %d" % (field, value, page))
        srcs = page_sources(parsed, field, value)
        keys.extend(target_keys(parsed))
        pages.append({"page": page, "status": status, "sources": srcs})
        if page == 1:
            t = clean_total(one(srcs, TARGET))
            planned = min(MAX_PAGES, max(1, math.ceil(t / PER_PAGE))) if t else 1
        page += 1
    return {"field": field, "value": value, "pages_planned": planned,
            "statuses": sorted({p["status"] for p in pages}), "by_source": by_source(pages),
            "keys": keys}


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


def snapshot(raw):
    """(summary, target): per field and source, the values of its distinct served subjects
    (the census's key: source, organization, namespace, name; the first copy counts; race
    counts each value in the list); and, for the target source, each subject's namespace and
    values (kept inside the job)."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = {}
    for path in glob.glob(os.path.join(raw, "subject", "page-*.json.gz")):
        m = PAGE.match(os.path.basename(path))
        if m:
            files[int(m.group(1))] = path
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    seen, subjects, target = set(), collections.Counter(), {}
    served = {f: collections.defaultdict(collections.Counter) for f in FIELDS}
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
                subjects[src] += 1
                vals = {f: values_of(rec, f) for f in FIELDS}
                for f in FIELDS:
                    served[f][src].update(vals[f])
                if src.lower() == TARGET:
                    target[key] = (key[2], vals)
    summary = {"path": raw, "pages_read": read, "pages_unreadable": unreadable,
               "subjects": dict(sorted(subjects.items())),
               "served": {f: {s: dict(c) for s, c in sorted(served[f].items())} for f in FIELDS}}
    return summary, target


# ---------- comparing ----------

def cells(snap, counts, filters):
    """One row per field, value and source: served (snapshot), count (count endpoint) and
    filter (the filter's clean total); None where a number is not available."""
    out = []
    for field in FIELDS:
        c_src = counts[field]["sources"]
        s_src = snap["served"][field] if snap else {}
        for value in VALUES[field]:
            f_src = filters[field][value]["sources"]
            for src in sorted(set(f_src) | set(c_src) | set(s_src)):
                ci, it = c_src.get(src), f_src.get(src)
                count = None
                if ci is not None and not ci["error"]:
                    count = ci["values"].get(value, 0)
                    count = count if type(count) is int else None
                out.append({"field": field, "value": value, "source": src,
                            "served": s_src.get(src, {}).get(value, 0) if snap else None,
                            "count": count, "filter": clean_total(it),
                            "filter_error_kinds": it["error_kinds"] if it else None})
    return out


def gap(c):
    """served - filter, or None."""
    if c["served"] is None or c["filter"] is None:
        return None
    return c["served"] - c["filter"]


def find(cs, src, field, value):
    hits = [c for c in cs
            if c["source"].lower() == src and c["field"] == field and c["value"] == value]
    return hits[0] if len(hits) == 1 else None


def kidsfirst(target, walks):
    """Which KidsFirst subjects served as "Unknown" each walk did not return, and how the
    unreached ones split by namespace and by their other values (counts only)."""
    if not target:
        return None
    out, unreached = {}, {}
    for field in WALKS:
        walked = set(walks[field]["keys"])
        has = {k for k, (_, vals) in target.items() if WALK_VALUE in vals[field]}
        unreached[field] = has - walked
        out[field] = {"served_unknown": len(has), "walked_entries": len(walks[field]["keys"]),
                      "walked_distinct": len(walked),
                      "walked_not_in_snapshot": len(walked - set(target)),
                      "walked_without_value_in_snapshot": len((walked & set(target)) - has),
                      "unreached": len(unreached[field])}
    both = unreached["ethnicity"] & unreached["race"]
    out["both_unreached"] = len(both)
    out["either_unreached"] = len(unreached["ethnicity"] | unreached["race"])
    by_ns = collections.defaultdict(collections.Counter)
    for k, (ns, vals) in target.items():
        row = by_ns[ns]
        row["subjects"] += 1
        row["eth_unknown"] += WALK_VALUE in vals["ethnicity"]
        row["race_unknown"] += WALK_VALUE in vals["race"]
        row["eth_unreached"] += k in unreached["ethnicity"]
        row["race_unreached"] += k in unreached["race"]
        row["both_unreached"] += k in both
    out["by_namespace"] = {ns: dict(c) for ns, c in sorted(by_ns.items())}

    def tab(keys, field):
        c = collections.Counter()
        for k in keys:
            c.update(target[k][1][field])
        return dict(sorted(c.items()))
    out["values_of_unreached"] = {name: {f: tab(unreached[w], f) for f in FIELDS}
                                  for name, w in (("ethnicity_unreached", "ethnicity"),
                                                  ("race_unreached", "race"))}
    return out


# ---------- grades ----------

def walk_full(w):
    """The walk returned 200 throughout and the target served exactly its page-1 total, on
    every walked page, with no error page, every entry carrying the walked value."""
    k = one(w["by_source"], TARGET)
    return (w["statuses"] == [200] and k is not None and k["first_total"] is not None
            and k["first_total"] >= 1 and k["error_pages"] == 0
            and k["pages"] == w["pages_planned"] and k["entries"] == k["first_total"]
            and k["with_value"] == k["entries"])


def overlap(kf):
    """Share of the ethnicity-unreached subjects that the race walk also missed, or None."""
    if not kf or not kf["ethnicity"]["unreached"]:
        return None
    return kf["both_unreached"] / kf["ethnicity"]["unreached"]


def grade(cs, over, walks, kf):
    """R1-R3 and K1-K3 exactly as pre-registered in README.md."""
    comparable = [c for c in cs if c["count"] is not None and c["filter"] is not None]
    r1 = len(comparable) >= MIN_CELLS and all(abs(c["filter"] - c["count"]) <= 1
                                              for c in comparable)
    gaps = {(c["source"].lower(), c["field"], c["value"]): gap(c) for c in cs
            if gap(c) is not None and gap(c) > GAP_MIN}
    eth, race = ("kidsfirst", "ethnicity", "Unknown"), ("kidsfirst", "race", "Unknown")
    r2 = (set(gaps) == {eth, race} and ETH_GAP[0] <= gaps[eth] <= ETH_GAP[1]
          and RACE_GAP[0] <= gaps[race] <= RACE_GAP[1])
    pc = {v: find(cs, "pcdc", "vital_status", v) for v in PCDC_MIN}
    po = one(over["sources"], "pcdc")
    r3 = (all(pc[v] is not None and pc[v]["filter"] is not None and pc[v]["filter"] >= m
              and pc[v]["served"] == 0 for v, m in PCDC_MIN.items())
          and over["status"] == 200 and po is not None and not po["error"]
          and isinstance(po["entries"], int) and po["entries"] >= 1
          and po["values"] == {MISSING: po["entries"]})
    k1 = all(walk_full(walks[f]) for f in WALKS)
    k2 = (kf is not None and ETH_GAP[0] <= kf["ethnicity"]["unreached"] <= ETH_GAP[1]
          and RACE_GAP[0] <= kf["race"]["unreached"] <= RACE_GAP[1]
          and all(kf[f]["walked_not_in_snapshot"] <= NOT_IN_SNAPSHOT_MAX for f in WALKS))
    share = overlap(kf)
    k3 = share is not None and share >= SHARED
    g = {"R1": r1, "R2": r2, "R3": r3, "K1": k1, "K2": k2, "K3": k3}
    return {k: "pass" if v else "fail" for k, v in g.items()}


def reading(g, kf):
    """The pre-registered readings."""
    share = overlap(kf)
    if share is None:
        shared = "none"
    elif share >= SHARED:
        shared = "shared"
    elif share >= SEPARATE:
        shared = "partly_shared"
    else:
        shared = "separate"
    return {"count_and_filter": "agree" if g["R1"] == "pass" else "disagree",
            "under_reach": "kidsfirst_unknown_only" if g["R2"] == "pass" else "other",
            "pcdc_vital_status": "filter_without_value" if g["R3"] == "pass" else "other",
            "kidsfirst_overlap": shared}


def main(argv=None, fetch=None, pause=PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="/data")
    args = ap.parse_args(argv)
    client = Client(fetch or get, pause)
    counts = read_counts(client)
    filters = read_filters(client)
    over = read_over(client)
    walks = {f: walk(client, f, WALK_VALUE) for f in WALKS}
    raw = find_snapshot(args.data_dir)
    snap, target = snapshot(raw) if raw else (None, None)
    cs = cells(snap, counts, filters)
    kf = kidsfirst(target, walks)
    g = grade(cs, over, walks, kf)
    for w in walks.values():
        del w["keys"]
    out = {"probe": "ccdi/filter-reach-v1",
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "grades": g, "reading": reading(g, kf), "overlap": overlap(kf),
           "gaps_over_%d" % GAP_MIN: [c for c in cs if gap(c) is not None and gap(c) > GAP_MIN],
           "cells": cs, "kidsfirst": kf, "over_page": over, "walks": [walks[f] for f in WALKS],
           "counts": counts, "filters": filters, "snapshot": snap, "requests": client.log}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "reachprobe.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(g, sort_keys=True), json.dumps(out["reading"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
