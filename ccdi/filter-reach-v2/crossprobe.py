"""Pre-registered follow-up to ccdi/filter-reach-v1 (ccdi/filter-reach-v2; predictions S1-S3 and
D1-D3 in README.md). Two count/filter disagreements found at v0.9.9 are tested record by record:

  1. StJude serves no vital status, yet its vital_status filter returned 31 for "Unknown" and
     3,234 for "Not reported", exactly its ethnicity totals for those values. Does the vital
     status filter return StJude's ethnicity records?
  2. CCDI-DCC's sex=U filter returned 396 while its count endpoint and its served records show
     432. Which records does it miss, and do raw stored sex values reach them?

Live part, sequential GET requests 2 s apart:
  1. two count endpoints, /subject/by/{sex,vital_status}/count;
  2. 18 filtered totals at per_page 1: ethnicity (4 values); vital_status (5 values, and the
     ethnicity values "Hispanic or Latino" and "Not Hispanic or Latino"); sex=U and six raw sex
     values;
  3. five walks at per_page 100: vital_status=Unknown, ethnicity=Unknown,
     vital_status=Not reported, ethnicity=Not reported (StJude's results) and sex=U
     (CCDI-DCC's results), pages 1..ceil(the target's page-1 total / 100), at most 60 each.
Offline part: the values StJude and CCDI-DCC serve in the newest saved snapshot under the data
folder, and which CCDI-DCC subjects served with sex "U" the walk did not return.

It reuses reachprobe.py from ccdi/filter-reach-v1 (tag v0.9.8) unchanged.

Only aggregates leave the job: per response its status, size and SHA-256; per source and value
the filter totals, the count endpoint's counts and the values served on walked pages; the sizes
of subject-set comparisons; and, for CCDI-DCC, counts of unreached subjects by study namespace
and by their other values. Subject keys are compared inside the job only; no record or
identifier is written out, and no query by participant ID is sent.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import glob
import json
import math
import os
import sys
import time

import reachprobe as rp

PAUSE = 2
PER_PAGE = 100
MAX_PAGES = 60
ST, DCC, PCDC = "stjude", "ccdi-dcc", "pcdc"
ETH = ("Hispanic or Latino", "Not Hispanic or Latino", "Unknown", "Not reported")
VITAL = ("Alive", "Dead", "Unknown", "Not reported", "Unspecified")
CROSS = ("Hispanic or Latino", "Not Hispanic or Latino")
SHARED = ("Unknown", "Not reported")
RAW_SEX = ("Not Reported", "Unknown", "Undifferentiated", "Unspecified", "Intersex",
           "Not Allowed to Collect")
COUNT_FIELDS = ("sex", "vital_status")
WALKS = (("vital_status", "Unknown", ST), ("ethnicity", "Unknown", ST),
         ("vital_status", "Not reported", ST), ("ethnicity", "Not reported", ST),
         ("sex", "U", DCC))

# Thresholds fixed in README.md before the job runs.
DCC_FILTER_U = (390, 400)
DCC_COUNT_U = (426, 438)
DCC_UNREACHED = (30, 42)
NOT_IN_SNAPSHOT_MAX = 10


def totals_plan():
    """(field, value) of every per_page-1 request, in order."""
    return ([("ethnicity", v) for v in ETH] + [("vital_status", v) for v in VITAL + CROSS]
            + [("sex", "U")] + [("sex", v) for v in RAW_SEX])


def keys_of(parsed, target):
    """Subject keys of the target source's entries on one page (kept inside the job)."""
    keys = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or str(item.get("source", "")).lower() != target:
            continue
        data = item.get("data")
        for rec in data if isinstance(data, list) else []:
            if isinstance(rec, dict):
                keys.append(rp.subject_key(rec, str(item["source"])))
    return keys


# ---------- the live part ----------

def read_counts(client):
    out = {}
    for field in COUNT_FIELDS:
        status, parsed = client.json(rp.url_of("/subject/by/%s/count" % field), "count " + field)
        out[field] = {"status": status, "sources": rp.count_items(parsed)}
    return out


def read_totals(client):
    out = {}
    for field, value in totals_plan():
        status, parsed = client.json(
            rp.url_of("/subject", [("page", 1), ("per_page", 1), (field, value)]),
            "filter %s=%s" % (field, value))
        out["%s=%s" % (field, value)] = {"field": field, "value": value, "status": status,
                                         "sources": rp.page_sources(parsed, field, value)}
    return out


def walk(client, field, value, target):
    """Pages 1..ceil(the target's page-1 total / PER_PAGE), at most MAX_PAGES (1 if no total).
    Every page is tallied for all four fields; with_value counts the walked value."""
    pages, keys, planned, page = [], [], 1, 1
    while page <= planned:
        status, parsed = client.json(
            rp.url_of("/subject", [("page", page), ("per_page", PER_PAGE), (field, value)]),
            "walk %s=%s page %d" % (field, value, page))
        per_field = {f: rp.page_sources(parsed, f, value) for f in rp.FIELDS}
        keys.extend(keys_of(parsed, target))
        pages.append({"page": page, "status": status, "per_field": per_field})
        if page == 1:
            t = rp.clean_total(rp.one(per_field[field], target))
            planned = min(MAX_PAGES, max(1, math.ceil(t / PER_PAGE))) if t else 1
        page += 1
    by_field = {f: rp.by_source([{"page": p["page"], "sources": p["per_field"][f]}
                                 for p in pages]) for f in rp.FIELDS}
    return {"field": field, "value": value, "target": target, "pages_planned": planned,
            "statuses": sorted({p["status"] for p in pages}), "by_field": by_field,
            "keys": keys}


# ---------- the saved snapshot ----------

def snapshot(raw, sources=(ST, DCC)):
    """(summary, subjects): for each listed source (lower case), its distinct served subjects
    and their values (the census's key; the first copy counts; kept inside the job)."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = {}
    for path in glob.glob(os.path.join(raw, "subject", "page-*.json.gz")):
        m = rp.PAGE.match(os.path.basename(path))
        if m:
            files[int(m.group(1))] = path
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    seen, out = set(), {s: {} for s in sources}
    read, unreadable = 0, 0
    for n in sorted(files):
        parsed = rp.load(files[n])
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
                key = rp.subject_key(rec, src)
                if key in seen:
                    continue
                seen.add(key)
                if src.lower() in out:
                    out[src.lower()][key] = {f: rp.values_of(rec, f) for f in rp.FIELDS}
    summary = {"path": raw, "pages_read": read, "pages_unreadable": unreadable,
               "subjects": {s: len(v) for s, v in out.items()}}
    return summary, out


# ---------- comparing ----------

def total(totals, field, value, src):
    """The source's clean total for one per_page-1 request, else None."""
    t = totals.get("%s=%s" % (field, value))
    return rp.clean_total(rp.one(t["sources"], src)) if t else None


def count_value(counts, field, value, src):
    it = rp.one(counts[field]["sources"], src)
    if it is None or it["error"]:
        return None
    c = it["values"].get(value, 0)
    return c if type(c) is int else None


def target_of(w, field=None):
    return rp.one(w["by_field"][field or w["field"]], w["target"])


def served_in_full(w):
    """The walk returned 200 throughout and the target served exactly its page-1 total, on
    every walked page, with no error page and no subject twice."""
    k = target_of(w)
    return (w["statuses"] == [200] and k is not None and k["first_total"] is not None
            and k["first_total"] >= 1 and k["error_pages"] == 0
            and k["pages"] == w["pages_planned"] and k["entries"] == k["first_total"]
            and len(set(w["keys"])) == len(w["keys"]))


def same_subjects(walks):
    """For each shared value, StJude's subjects from the vital status walk against those from
    the ethnicity walk (sizes only)."""
    out = {}
    for v in SHARED:
        a = set(walks[("vital_status", v)]["keys"])
        b = set(walks[("ethnicity", v)]["keys"])
        out[v] = {"vital_walk": len(a), "ethnicity_walk": len(b), "both": len(a & b),
                  "vital_only": len(a - b), "ethnicity_only": len(b - a)}
    return out


def stjude_snapshot(walks, subj):
    """How StJude's vital-status-walked subjects are served in the snapshot (sizes only)."""
    out = {}
    for v in SHARED:
        keys = set(walks[("vital_status", v)]["keys"])
        has = {k for k, vals in subj.items() if v in vals["ethnicity"]}
        vital = collections.Counter()
        for k in keys & set(subj):
            vital.update(subj[k]["vital_status"])
        out[v] = {"walked": len(keys), "not_in_snapshot": len(keys - set(subj)),
                  "snapshot_with_ethnicity_value": len(has),
                  "walked_with_ethnicity_value": len(keys & has),
                  "with_ethnicity_value_not_walked": len(has - keys),
                  "vital_status_of_walked": dict(sorted(vital.items()))}
    return out


def dcc_unreached(w, subj):
    """Which CCDI-DCC subjects served with sex "U" the sex=U walk did not return, counted by
    study namespace and by their other values."""
    walked = set(w["keys"])
    has = {k for k, vals in subj.items() if "U" in vals["sex"]}
    miss = has - walked

    def tab(field):
        c = collections.Counter()
        for k in miss:
            c.update(subj[k][field])
        return dict(sorted(c.items()))
    return {"served_u": len(has), "walked_entries": len(w["keys"]),
            "walked_distinct": len(walked), "walked_not_in_snapshot": len(walked - set(subj)),
            "walked_without_u_in_snapshot": len((walked & set(subj)) - has),
            "unreached": len(miss),
            "u_by_namespace": dict(sorted(collections.Counter(k[2] for k in has).items())),
            "unreached_by_namespace": dict(sorted(collections.Counter(k[2] for k in miss)
                                                  .items())),
            "values_of_unreached": {f: tab(f) for f in rp.FIELDS}}


def dcc_sex(totals, counts):
    """CCDI-DCC's sex=U total, its count endpoint's "U", and each raw value's total or errors."""
    raw = {}
    for v in RAW_SEX:
        it = rp.one(totals["sex=%s" % v]["sources"], DCC)
        raw[v] = {"total": rp.clean_total(it), "error_kinds": it["error_kinds"] if it else None}
    return {"filter_u": total(totals, "sex", "U", DCC),
            "count_u": count_value(counts, "sex", "U", DCC), "raw": raw}


def pcdc(counts, totals):
    """Descriptive only: does PCDC answer vital status, by count endpoint or by filter?"""
    c = rp.one(counts["vital_status"]["sources"], PCDC)
    f = {v: rp.one(totals["vital_status=%s" % v]["sources"], PCDC) for v in VITAL}
    count_ok = c is not None and not c["error"] and bool(c["values"])
    clean = [v for v, it in f.items() if rp.clean_total(it) is not None]
    if clean:
        r = "filter_works"
    elif count_ok:
        r = "count_without_filter"
    elif c is not None and c["error"]:
        r = "both_unavailable"
    else:
        r = "other"
    return {"count": c, "filter_totals": {v: rp.clean_total(it) for v, it in f.items()},
            "filter_error_kinds": {v: (it["error_kinds"] if it else None)
                                   for v, it in f.items()},
            "reading": r}


# ---------- grades ----------

def grade(totals, counts, walks, same, dcc):
    """S1-S3 and D1-D3 exactly as pre-registered in README.md."""
    s1 = True
    for v in SHARED:
        w = walks[("vital_status", v)]
        k, e = target_of(w), target_of(w, "ethnicity")
        eth = total(totals, "ethnicity", v, ST)
        s1 = s1 and (served_in_full(w) and k["values"] == {rp.MISSING: k["entries"]}
                     and e is not None and e["with_value"] == k["entries"]
                     and eth is not None and k["first_total"] == eth)
    s2 = all(served_in_full(walks[("vital_status", v)])
             and served_in_full(walks[("ethnicity", v)])
             and same[v]["both"] >= 1 and same[v]["vital_only"] == 0
             and same[v]["ethnicity_only"] == 0 for v in SHARED)
    s3 = True
    for v in CROSS:
        vt, et = total(totals, "vital_status", v, ST), total(totals, "ethnicity", v, ST)
        s3 = s3 and vt is not None and vt >= 1 and vt == et
    wu = walks[("sex", "U")]
    ku = target_of(wu)
    ds = dcc_sex(totals, counts)
    cu, fu = ds["count_u"], ds["filter_u"]
    d1 = (served_in_full(wu) and DCC_FILTER_U[0] <= ku["first_total"] <= DCC_FILTER_U[1]
          and ku["with_value"] == ku["entries"]
          and cu is not None and DCC_COUNT_U[0] <= cu <= DCC_COUNT_U[1])
    d2 = (dcc is not None and DCC_UNREACHED[0] <= dcc["unreached"] <= DCC_UNREACHED[1]
          and dcc["walked_not_in_snapshot"] <= NOT_IN_SNAPSHOT_MAX)
    others = [ds["raw"][v]["total"] for v in RAW_SEX[1:]]
    d3 = (fu is not None and ds["raw"]["Not Reported"]["total"] == fu and cu is not None
          and all(o is not None for o in others) and abs(fu + sum(others) - cu) <= 1)
    g = {"S1": s1, "S2": s2, "S3": s3, "D1": d1, "D2": d2, "D3": d3}
    return {k: "pass" if v else "fail" for k, v in g.items()}


def reading(g, totals, counts):
    """The pre-registered readings."""
    if g["S1"] == g["S2"] == g["S3"] == "pass":
        st = "reads_ethnicity"
    elif g["S1"] == g["S2"] == "pass":
        st = "matches_ethnicity_on_shared_values"
    else:
        st = "other"
    ds = dcc_sex(totals, counts)
    if g["D3"] == "pass":
        dc = "else_bucket_found"
    elif all(r["total"] is None for r in ds["raw"].values()):
        dc = "raw_rejected"
    elif ds["filter_u"] is not None and ds["raw"]["Not Reported"]["total"] == ds["filter_u"]:
        dc = "partly_found"
    else:
        dc = "other"
    return {"stjude_vital_filter": st, "dcc_sex_u": dc}


def main(argv=None, fetch=None, pause=PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="/data")
    args = ap.parse_args(argv)
    client = rp.Client(fetch or rp.get, pause)
    counts = read_counts(client)
    totals = read_totals(client)
    walks = {(f, v): walk(client, f, v, t) for f, v, t in WALKS}
    raw = rp.find_snapshot(args.data_dir)
    snap, subj = snapshot(raw) if raw else (None, {ST: {}, DCC: {}})
    same = same_subjects(walks)
    st_snap = stjude_snapshot(walks, subj[ST]) if raw else None
    dcc = dcc_unreached(walks[("sex", "U")], subj[DCC]) if raw else None
    g = grade(totals, counts, walks, same, dcc)
    for w in walks.values():
        del w["keys"]
    out = {"probe": "ccdi/filter-reach-v2",
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "grades": g, "reading": reading(g, totals, counts),
           "stjude": {"vital_totals": {v: total(totals, "vital_status", v, ST)
                                       for v in VITAL + CROSS},
                      "ethnicity_totals": {v: total(totals, "ethnicity", v, ST) for v in ETH},
                      "same_subjects": same, "snapshot": st_snap},
           "ccdi_dcc": {"sex": dcc_sex(totals, counts), "unreached": dcc},
           "pcdc": pcdc(counts, totals),
           "walks": [walks[(f, v)] for f, v, _ in WALKS],
           "counts": counts, "totals": totals, "snapshot": snap, "requests": client.log}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "crossprobe.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(g, sort_keys=True), json.dumps(out["reading"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
