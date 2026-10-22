"""POST-HOC diagnostics for the CCDI concordance census (ccdi-concord-v1).

Written on 2026-10-22 AFTER the v1 results were seen, to explain five things the v1 output
showed but could not explain. None of this was pre-registered; every number it produces is
labelled post hoc in the write-up.

  1  failed pages: which in-range /subject pages came back without a record list (v1 lost
     100 PCDC subjects this way), what the error said, and whether one retry fixes it;
  2  age offsets between linked records, per source pair (v1: all 10 CCDI-DCC|ccdi-ecDNA
     pairs that both say Dead differ in age at death by more than 30 days);
  3  which side says Dead when linked records disagree on vital status;
  4  sex disagreements by source pair and study namespace (v1: 4 of 43 KidsFirst|StJude);
  5  the shape of Participant Index links that do not resolve to a served subject (v1: all
     3,734 organizational links into PCDC), and whether a looser match would resolve them;
  plus served records with no sex or vital status, by study namespace; and the v1 analysis
  re-run unchanged on this second snapshot.

Aggregates only: no participant IDs and no participant-level rows leave the job.
Identifier shapes are reduced to character classes and run lengths (e.g. "A{6}").

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import math
import os
import re
import shutil
import time

import analyze
import fetch_ccdi

ID_LIKE = re.compile(r"[A-Za-z]*\d{3,}[A-Za-z0-9_-]*|\bP[A-Z]{5}\b")


def shape(s):
    """Character-class shape with run lengths: 'PT_00A' -> 'A{2}_9{2}A'."""
    out, prev, n = [], None, 0

    def cls(ch):
        if "A" <= ch <= "Z":
            return "A"
        if "a" <= ch <= "z":
            return "a"
        if ch.isdigit():
            return "9"
        return ch

    for ch in str(s):
        c = cls(ch)
        if c == prev:
            n += 1
            continue
        if prev is not None:
            out.append(prev + ("{%d}" % n if n > 1 else ""))
        prev, n = c, 1
    if prev is not None:
        out.append(prev + ("{%d}" % n if n > 1 else ""))
    return "".join(out)


def scrub(text, limit=200):
    """Short error text with anything identifier-like replaced."""
    return ID_LIKE.sub("<id>", str(text))[:limit]


def quantiles(xs):
    if not xs:
        return None
    xs = sorted(xs)

    def q(p):
        return xs[min(len(xs) - 1, int(math.floor(p * (len(xs) - 1) + 0.5)))]

    return {"n": len(xs), "min": xs[0], "p10": q(0.1), "p25": q(0.25), "median": q(0.5),
            "p75": q(0.75), "p90": q(0.9), "max": xs[-1]}


def top(counter, k=15):
    return [[key, n] for key, n in counter.most_common(k)]


# ---------- 1 failed pages ----------

def failed_pages(raw, retry=False, pause=fetch_ccdi.PAUSE):
    chosen, paths = analyze.subject_pages(raw)
    per_page = chosen["per_page"]
    pages, totals = [], {}
    for i, p in enumerate(paths):
        page = 1 if i == 0 else int(re.search(r"page-(\d+)", p).group(1))
        items = [x for x in analyze.load(p) or [] if isinstance(x, dict)]
        pages.append((page, items))
        for item in items:
            n = ((item.get("summary") or {}).get("counts") or {}).get("all")
            if n is not None:
                totals[item.get("source")] = max(n, totals.get(item.get("source"), 0))
    out = []
    for page, items in pages:
        for item in items:
            if isinstance(item.get("data"), list):
                continue
            total = totals.get(item.get("source"))
            if total is None or page > math.ceil(total / per_page):
                continue
            row = {"source": item.get("source"), "page": page,
                   "keys": sorted(k for k in item if k != "data"),
                   "message": scrub(json.dumps({k: v for k, v in item.items()
                                                if k not in ("data", "summary")}))}
            if retry:
                time.sleep(pause)
                status, body = fetch_ccdi.get(fetch_ccdi.fed_url(
                    "/subject", page=page, per_page=per_page))[:2]
                again = None
                try:
                    again = json.loads(body)
                except (TypeError, ValueError):
                    pass
                mine = next((x for x in again or [] if isinstance(x, dict)
                             and x.get("source") == row["source"]), None)
                data = mine.get("data") if mine else None
                row["retry"] = {"status": status,
                                "records": len(data) if isinstance(data, list) else None}
            out.append(row)
    return out


# ---------- 2-4 linked pairs ----------

def ordered(s, t):
    return (s, t) if s["source"] <= t["source"] else (t, s)


def pair_diagnostics(pairs):
    ages = collections.defaultdict(lambda: collections.defaultdict(list))
    vital_dir = collections.defaultdict(collections.Counter)
    sex_dis = collections.Counter()
    for s, t in pairs.values():
        a, b = ordered(s, t)
        key = a["source"] + " | " + b["source"]
        if a["age"] is not None and b["age"] is not None:
            combo = "%s/%s" % (a["vital"] or "none", b["vital"] or "none")
            ages[key][combo].append(b["age"] - a["age"])
            ages[key]["all"].append(b["age"] - a["age"])
        if a["vital"] and b["vital"] and a["vital"] != b["vital"]:
            vital_dir[key]["%s=%s, %s=%s" % (a["source"], a["vital"], b["source"],
                                              b["vital"])] += 1
        if a["sex"] and b["sex"] and a["sex"] != b["sex"]:
            sex_dis["%s [%s] %s vs %s [%s] %s" % (a["source"], a["ns"], a["sex"],
                                                 b["source"], b["ns"], b["sex"])] += 1
    age_out = {}
    for key, combos in sorted(ages.items()):
        age_out[key] = {}
        for combo, ds in sorted(combos.items()):
            row = quantiles(ds)
            row["within_1_day"] = sum(1 for d in ds if abs(d) <= 1)
            row["second_older"] = sum(1 for d in ds if d > 1)
            row["first_older"] = sum(1 for d in ds if d < -1)
            age_out[key][combo] = row
    return {"age_difference_days_second_minus_first": age_out,
            "vital_disagreement_direction": {k: dict(v) for k, v in sorted(vital_dir.items())},
            "sex_disagreements": dict(sorted(sex_dis.items()))}


# ---------- 5 unresolved links ----------

def unresolved_links(entries, subjects, by_dom):
    sources = {}
    for s in subjects.values():
        sources.setdefault(s["source"].lower(), s["source"])
        sources.setdefault(s["ns"].lower(), s["source"])
    names_ci = collections.defaultdict(set)
    alts = collections.defaultdict(set)
    alnum = collections.defaultdict(set)
    any_name = set()
    served_shapes = collections.defaultdict(collections.Counter)
    for s in subjects.values():
        names_ci[s["source"]].add(s["name"].lower())
        alnum[s["source"]].add(re.sub(r"[^a-z0-9]", "", s["name"].lower()))
        for n in s["alt"]:
            alts[s["source"]].add(n)
        any_name.add(s["name"])
        served_shapes[s["source"]][shape(s["name"])] += 1
    rows = collections.defaultdict(lambda: {"links": 0, "shapes": collections.Counter(),
                                            "tests": collections.Counter()})
    for e in entries:
        if by_dom.get((str(e.get("domain_name")).lower(), str(e.get("participant_id")))) is None:
            continue
        for a in e.get("associated_ids") or []:
            if a.get("domain_category") != "organizational_identifier":
                continue
            dom, pid = str(a.get("domain_name")), str(a.get("participant_id"))
            src = sources.get(dom.lower())
            if src is None or by_dom.get((dom.lower(), pid)) is not None:
                continue
            r = rows[src]
            r["links"] += 1
            r["shapes"][shape(pid)] += 1
            t = r["tests"]
            t["case_insensitive_name"] += pid.lower() in names_ci[src]
            t["alt_identifier_in_source"] += pid in alts[src]
            t["alnum_only_name"] += re.sub(r"[^a-z0-9]", "", pid.lower()) in alnum[src]
            t["name_in_any_source"] += pid in any_name
    out = {}
    for src, r in sorted(rows.items()):
        out[src] = {"unresolved_links": r["links"], "unresolved_shapes": top(r["shapes"]),
                    "served_name_shapes": top(served_shapes[src]),
                    "would_resolve_by": dict(sorted(r["tests"].items()))}
    return out


# ---------- missing demographics by namespace ----------

def missing_by_namespace(subjects, k=20):
    rows = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for s in subjects.values():
        c = rows[s["source"]][s["ns"]]
        c["records"] += 1
        c["sex_null"] += s["raw"]["sex"] is None
        c["vital_null"] += s["raw"]["vital_status"] is None
    out = {}
    for src, by_ns in sorted(rows.items()):
        ranked = sorted(by_ns.items(), key=lambda kv: (-kv[1]["sex_null"], -kv[1]["records"]))
        out[src] = {"namespaces": len(by_ns),
                    "top_by_sex_null": [dict(ns=ns, **dict(c)) for ns, c in ranked[:k]]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--out", required=True)
    ap.add_argument("--retry", action="store_true", help="re-fetch failed in-range pages once")
    ap.add_argument("--keep", help="copy raw/ here for later jobs")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    analyze.main(["--raw", args.raw, "--out", os.path.join(args.out, "snapshot2")])
    _, _, subjects, _ = analyze.read_subjects(args.raw)
    entries = analyze.read_mappings(args.raw)
    by_dom, by_usi = analyze.fed_indexes(subjects)
    pairs, _, _ = analyze.mapping_links(entries, by_dom, by_usi)
    result = {"label": "POST HOC: written after ccdi-concord-v1 results were seen",
              "failed_pages": failed_pages(args.raw, retry=args.retry),
              "pairs": pair_diagnostics(pairs),
              "unresolved_links": unresolved_links(entries, subjects, by_dom),
              "missing_by_namespace": missing_by_namespace(subjects)}
    with open(os.path.join(args.out, "diagnostics.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    if args.keep:
        shutil.copytree(args.raw, args.keep, dirs_exist_ok=True)
    print(json.dumps({"failed_pages": result["failed_pages"],
                      "unresolved": {k: v["would_resolve_by"]
                                     for k, v in result["unresolved_links"].items()}},
                     indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
