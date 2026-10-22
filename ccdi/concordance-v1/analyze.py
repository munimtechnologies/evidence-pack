"""Run step of the CCDI concordance job: read what fetch_ccdi.py stored in raw/ and write
aggregate counts only (no participant IDs, no participant-level rows) to --out.

Sections (pre-registered in prereg.md):
  A  internal consistency of each federation source: summary totals, per-field count
     endpoints, and the records the source actually serves on its pages;
  B  GDC TARGET open clinical data against federation subjects, joined on the COG USI;
  C  attribute agreement between federation subjects that the CCDI Participant Index
     links across sources;
  D  how much a naive union of sources over-counts participants.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import glob
import gzip
import json
import os
import re

USI = re.compile(r"^P[A-Z]{5}$")
GDC_ID = re.compile(r"^TARGET-\d{2}-(P[A-Z]{5})(?:-.*)?$")
RACES = {"white": "White", "black or african american": "Black or African American",
         "asian": "Asian", "american indian or alaska native": "American Indian or Alaska Native",
         "native hawaiian or other pacific islander": "Native Hawaiian or other Pacific Islander"}
MISSING = "<missing>"
MIN_PAIRS = 100


# ---------- normalising ----------

def val(x):
    return x.get("value") if isinstance(x, dict) else x


def norm_sex(v):
    return {"m": "M", "male": "M", "f": "F", "female": "F"}.get(str(v or "").strip().lower())


def norm_race(values):
    if values is None:
        return frozenset()
    if not isinstance(values, (list, tuple)):
        values = [values]
    return frozenset(r for r in (RACES.get(str(v or "").strip().lower()) for v in values) if r)


def norm_eth(v):
    return {"hispanic or latino": "H",
            "not hispanic or latino": "NH"}.get(str(v or "").strip().lower())


def norm_vital(v):
    return {"alive": "Alive", "living": "Alive", "dead": "Dead",
            "deceased": "Dead"}.get(str(v or "").strip().lower())


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def fed_subject(rec, source):
    md = rec.get("metadata") or {}
    ident = rec.get("id") or {}
    ns = ident.get("namespace") or {}
    races = md.get("race") or []
    if isinstance(races, dict):
        races = [races]
    alt = []
    for i in md.get("identifiers") or []:
        v = val(i)
        if isinstance(v, dict) and v.get("name") is not None:
            alt.append(str(v["name"]))
    raw_vital = val(md.get("vital_status"))
    return {"key": (source, str(ns.get("organization")), str(ns.get("name")),
                    str(ident.get("name"))),
            "source": source, "ns": str(ns.get("name")), "name": str(ident.get("name")),
            "alt": alt,
            "raw": {"sex": val(md.get("sex")), "ethnicity": val(md.get("ethnicity")),
                    "vital_status": raw_vital, "race": [val(r) for r in races]},
            "sex": norm_sex(val(md.get("sex"))), "race": norm_race([val(r) for r in races]),
            "eth": norm_eth(val(md.get("ethnicity"))), "vital": norm_vital(raw_vital),
            "age": num(val(md.get("age_at_vital_status")))}


def gdc_case(hit):
    sid = str(hit.get("submitter_id") or "")
    m = GDC_ID.match(sid)
    demo = hit.get("demographic") or {}
    dxs = hit.get("diagnoses") or []
    ages = [num(d.get("age_at_diagnosis")) for d in dxs]
    ages = [a for a in ages if a is not None]
    age_dx = min(ages) if ages else None
    follow = [num(d.get("days_to_last_follow_up")) for d in dxs]
    follow += [num(f.get("days_to_follow_up")) for f in hit.get("follow_ups") or []]
    follow = [f for f in follow if f is not None]
    dtd = num(demo.get("days_to_death"))
    vital = norm_vital(demo.get("vital_status"))
    age = None
    if age_dx is not None:
        if vital == "Dead" and dtd is not None:
            age = age_dx + dtd
        elif vital == "Alive" and follow:
            age = age_dx + max(follow)
    return {"usi": m.group(1) if m else None,
            "project": str((hit.get("project") or {}).get("project_id")),
            "submitter_id": sid,
            "sex": norm_sex(demo.get("sex_at_birth")), "race": norm_race(demo.get("race")),
            "eth": norm_eth(demo.get("ethnicity")), "vital": vital, "age_dx": age_dx,
            "age": age}


# ---------- comparing ----------

def cmp_scalar(a, b):
    if a is None or b is None:
        return "uninformative"
    return "agree" if a == b else "disagree"


def cmp_race(a, b):
    if not a or not b:
        return "uninformative"
    if a == b:
        return "agree"
    return "overlap" if a & b else "disagree"


def cmp_vital(av, aa, bv, ba):
    """Vital status of one person in two records, each with the age (days) it refers to."""
    if av is None or bv is None:
        return "uninformative"
    if av == bv:
        return "both_alive" if av == "Alive" else "both_dead"
    alive_age, dead_age = (aa, ba) if av == "Alive" else (ba, aa)
    if alive_age is None or dead_age is None:
        return "alive_dead_no_ages"
    return "alive_then_dead" if alive_age <= dead_age + 1 else "alive_after_death"


def cmp_death_age(a, b):
    """Both records say Dead: do the ages at death agree?"""
    if a["vital"] != "Dead" or b["vital"] != "Dead" or a["age"] is None or b["age"] is None:
        return None
    d = abs(a["age"] - b["age"])
    return "within_1_day" if d <= 1 else ("within_30_days" if d <= 30 else "over_30_days")


def tally(pairs):
    """Aggregate attribute agreement over (a, b) record pairs."""
    out = {"pairs": 0, "sex": collections.Counter(), "ethnicity": collections.Counter(),
           "race": collections.Counter(), "vital": collections.Counter(),
           "death_age": collections.Counter()}
    for a, b in pairs:
        out["pairs"] += 1
        out["sex"][cmp_scalar(a["sex"], b["sex"])] += 1
        out["ethnicity"][cmp_scalar(a["eth"], b["eth"])] += 1
        out["race"][cmp_race(a["race"], b["race"])] += 1
        out["vital"][cmp_vital(a["vital"], a["age"], b["vital"], b["age"])] += 1
        d = cmp_death_age(a, b)
        if d:
            out["death_age"][d] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, collections.Counter) else v)
            for k, v in out.items()}


# ---------- loading ----------

def load(path):
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as fh:
        body = fh.read()
    try:
        return json.loads(body)
    except ValueError:
        return None


def subject_pages(raw):
    chosen = json.load(open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8"))
    paths = [os.path.join(raw, "subject", chosen["first_page"] + ".gz")]
    paths += sorted(glob.glob(os.path.join(raw, "subject", "page-*.json.gz")))
    return chosen, paths


def read_subjects(raw):
    """Unique federation subjects, plus per-source page facts."""
    chosen, paths = subject_pages(raw)
    subjects, facts = {}, collections.defaultdict(lambda: {"records": 0, "repeats": 0,
                                                           "page_all": None, "errors": 0})
    for p in paths:
        parsed = load(p)
        for item in parsed if isinstance(parsed, list) else []:
            if not isinstance(item, dict) or "source" not in item:
                continue
            src = item["source"]
            f = facts[src]
            counts = (item.get("summary") or {}).get("counts") or {}
            if counts.get("all") is not None:
                f["page_all"] = counts["all"]
            data = item.get("data")
            if not isinstance(data, list):
                f["errors"] += 1
                continue
            for rec in data:
                s = fed_subject(rec, src)
                f["records"] += 1
                if s["key"] in subjects:
                    f["repeats"] += 1
                else:
                    subjects[s["key"]] = s
    return chosen, len(paths), subjects, facts


def read_mappings(raw):
    entries = []
    for p in sorted(glob.glob(os.path.join(raw, "mapping", "page-*.json.gz"))):
        parsed = load(p)
        if isinstance(parsed, dict):
            entries.extend(e for e in parsed.get("participant_ids") or [] if isinstance(e, dict))
    return entries


def read_gdc(raw):
    hits = []
    for p in sorted(glob.glob(os.path.join(raw, "gdc", "cases-*.json.gz"))):
        parsed = load(p)
        hits.extend(((parsed or {}).get("data") or {}).get("hits") or [])
    return [gdc_case(h) for h in hits]


# ---------- sections ----------

def section_a(raw, subjects, facts):
    summary = load(os.path.join(raw, "fed", "subject-summary.json.gz")) or []
    totals = {i.get("source"): ((i.get("counts") or {}).get("total"))
              for i in summary if isinstance(i, dict)}
    by_source = collections.defaultdict(list)
    for s in subjects.values():
        by_source[s["source"]].append(s)
    out = {}
    for src in sorted(set(totals) | set(facts) | set(by_source)):
        subs = by_source.get(src, [])
        row = {"summary_total": totals.get(src), "page_all": facts[src]["page_all"],
               "records_served": facts[src]["records"], "unique_served": len(subs),
               "repeated_records": facts[src]["repeats"], "page_errors": facts[src]["errors"],
               "fields": {}}
        for field in ("sex", "ethnicity", "vital_status", "race"):
            ep = load(os.path.join(raw, "fed", "count-%s.json.gz" % field))
            item = next((i for i in ep or [] if isinstance(i, dict) and i.get("source") == src),
                        None)
            served = collections.Counter()
            for s in subs:
                v = s["raw"][field]
                if field == "race":
                    for r in (v or [MISSING]):
                        served[str(r) if r is not None else MISSING] += 1
                else:
                    served[str(v) if v is not None else MISSING] += 1
            frow = {"served": dict(sorted(served.items()))}
            if item:
                values = {str(x.get("value")): x.get("count") for x in item.get("values") or []
                          if isinstance(x, dict)}
                frow["endpoint_total"] = item.get("total")
                frow["endpoint_missing"] = item.get("missing")
                frow["endpoint_values"] = dict(sorted(values.items()))
                frow["endpoint_sum"] = sum(c for c in values.values() if isinstance(c, int)) + (
                    item.get("missing") or 0)
                if field != "race":
                    want = dict(values)
                    want[MISSING] = item.get("missing") or 0
                    keys = set(want) | set(served)
                    diffs = {k: [want.get(k, 0), served.get(k, 0)] for k in sorted(keys)
                             if want.get(k, 0) != served.get(k, 0)}
                    frow["endpoint_vs_served"] = diffs
                    frow["consistent"] = not diffs
            else:
                frow["endpoint_total"] = None
            row["fields"][field] = frow
        out[src] = row
    return out


def fed_indexes(subjects):
    """(domain or namespace lower, name) -> subject; USI -> subjects."""
    by_dom, by_usi = {}, collections.defaultdict(list)
    for s in subjects.values():
        by_dom.setdefault((s["source"].lower(), s["name"]), s)
        by_dom.setdefault((s["ns"].lower(), s["name"]), s)
        for n in [s["name"]] + s["alt"]:
            if USI.match(n) and s not in by_usi[n]:
                by_usi[n].append(s)
    return by_dom, by_usi


def mapping_links(entries, by_dom, by_usi):
    """Cross-source subject pairs asserted by the Participant Index, and USI links."""
    pairs, usi_links = {}, collections.defaultdict(list)
    links = collections.Counter()
    for e in entries:
        s = by_dom.get((str(e.get("domain_name")).lower(), str(e.get("participant_id"))))
        if s is None:
            links["entry_unresolved"] += 1
            continue
        for a in e.get("associated_ids") or []:
            dom, pid = str(a.get("domain_name")), str(a.get("participant_id"))
            if dom.lower() == "usi" and USI.match(pid):
                if s not in usi_links[pid]:
                    usi_links[pid].append(s)
                for t in by_usi.get(pid, []):
                    if t["source"] != s["source"]:
                        pairs[tuple(sorted([s["key"], t["key"]]))] = (s, t)
                continue
            if a.get("domain_category") != "organizational_identifier":
                continue
            t = by_dom.get((dom.lower(), pid))
            if t is None:
                links["org_link_unresolved: " + dom] += 1
            elif t["source"] != s["source"]:
                links["org_link_resolved: " + dom] += 1
                pairs[tuple(sorted([s["key"], t["key"]]))] = (s, t)
    return pairs, usi_links, dict(sorted(links.items()))


def section_b(cases, by_usi, usi_links):
    with_usi = [c for c in cases if c["usi"]]
    groups = collections.defaultdict(list)
    for c in with_usi:
        groups[c["usi"]].append(c)
    for g in groups.values():
        g.sort(key=lambda c: (c["project"], c["submitter_id"]))
    multi = {u: g for u, g in groups.items() if len(g) > 1}
    internal = [(g[0], other) for g in multi.values() for other in g[1:]]
    dx_age = collections.Counter()
    for a, b in internal:
        if a["age_dx"] is None or b["age_dx"] is None:
            dx_age["uninformative"] += 1
        else:
            dx_age["agree" if abs(a["age_dx"] - b["age_dx"]) <= 1 else "disagree"] += 1
    by_source, linked = collections.defaultdict(list), set()
    for usi, g in groups.items():
        feds = list(by_usi.get(usi, []))
        for s in usi_links.get(usi, []):
            if s not in feds:
                feds.append(s)
        for s in feds:
            by_source[s["source"]].append((g[0], s))
            linked.add(usi)
    vital_dir, ratios = collections.Counter(), []
    for pairs in by_source.values():
        for a, s in pairs:
            if a["vital"] and s["vital"] and a["vital"] != s["vital"]:
                vital_dir["gdc_%s_fed_%s" % (a["vital"], s["vital"])] += 1
            if a["age"] and s["age"] and a["age"] > 0 and s["age"] > 0:
                ratios.append(s["age"] / a["age"])
    projects = collections.Counter(c["project"] for c in cases)
    return {"cases": len(cases), "cases_with_usi": len(with_usi), "distinct_usis": len(groups),
            "cases_by_project": dict(sorted(projects.items())),
            "usis_in_2plus_cases": len(multi),
            "gdc_internal": dict(tally(internal), age_at_diagnosis=dict(sorted(dx_age.items()))),
            "usis_linked_to_federation": len(linked),
            "gdc_vs_federation": {src: tally(p) for src, p in sorted(by_source.items())},
            "gdc_vs_federation_all": tally([p for ps in by_source.values() for p in ps]),
            "vital_disagreement_direction": dict(sorted(vital_dir.items())),
            "age_ratio_fed_over_gdc": {"n": len(ratios), "median": median(ratios)}}


def median(xs):
    if not xs:
        return None
    xs = sorted(xs)
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def section_c(pairs):
    by_pair = collections.defaultdict(list)
    for s, t in pairs.values():
        by_pair[" | ".join(sorted([s["source"], t["source"]]))].append((s, t))
    return {"pairs": len(pairs), "by_source_pair": {k: tally(v) for k, v in sorted(by_pair.items())},
            "all": tally(list(pairs.values()))}


def section_d(subjects, pairs):
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    for k1, k2 in pairs:
        r1, r2 = find(k1), find(k2)
        if r1 != r2:
            parent[r1] = r2
    members = {k for pair in pairs for k in pair}
    roots = {find(k) for k in members}
    return {"subjects_served": len(subjects), "subjects_in_cross_source_links": len(members),
            "linked_persons": len(roots),
            "deduplicated_total": len(subjects) - len(members) + len(roots),
            "naive_overcount": len(members) - len(roots)}


# ---------- grading ----------

def share(counter, keys, among):
    n = sum(counter.get(k, 0) for k in among)
    return (sum(counter.get(k, 0) for k in keys) / n if n else None), n


def grade(a, b, c):
    g = {}
    kf = a.get("KidsFirst", {})
    kf_missing = kf.get("fields", {}).get("vital_status", {}).get("served", {}).get(MISSING, 0)
    total = kf.get("summary_total")
    if not kf or not total:
        g["H1"] = {"result": "not testable"}
    else:
        ok = abs(kf["unique_served"] - total) <= 0.01 * total and kf_missing >= 30000
        g["H1"] = {"result": "pass" if ok else "fail", "unique_served": kf["unique_served"],
                   "summary_total": total, "vital_missing_served": kf_missing}
    pc = a.get("PCDC", {})
    vs = pc.get("fields", {}).get("vital_status", {})
    if not pc or not pc.get("unique_served") or vs.get("endpoint_total") is None:
        g["H2"] = {"result": "not testable"}
    else:
        frac = vs["served"].get(MISSING, 0) / pc["unique_served"]
        ok = frac >= 0.95 and vs.get("endpoint_missing") == 0
        g["H2"] = {"result": "pass" if ok else "fail", "served_missing_share": round(frac, 4),
                   "endpoint_missing": vs.get("endpoint_missing")}
    g["H3"] = {"result": "pass" if b["usis_linked_to_federation"] >= 1000 else "fail",
               "usis_linked": b["usis_linked_to_federation"]}
    allp = b["gdc_vs_federation_all"]
    rate, n = share(allp["sex"], ["disagree"], ["agree", "disagree"])
    g["H4"] = ({"result": "not testable", "n": n} if n < MIN_PAIRS else
               {"result": "pass" if rate <= 0.01 else "fail", "rate": round(rate, 4), "n": n})
    v = allp["vital"]
    aged = ["both_alive", "both_dead", "alive_then_dead", "alive_after_death"]
    informative = aged + ["alive_dead_no_ages"]
    r1, n1 = share(v, ["alive_after_death"], aged)
    r2, n2 = share(v, ["alive_then_dead"], informative)
    ratio = b["age_ratio_fed_over_gdc"]["median"]
    if ratio is None or not 0.5 <= ratio <= 2:
        g["H5"] = {"result": "not testable (age units)", "age_ratio_median": ratio}
    elif n1 < MIN_PAIRS or n2 < MIN_PAIRS:
        g["H5"] = {"result": "not testable", "n_aged": n1, "n_informative": n2}
    else:
        g["H5"] = {"result": "pass" if (r1 <= 0.01 and r2 >= 0.02) else "fail",
                   "alive_after_death_rate": round(r1, 4), "n_aged": n1,
                   "alive_then_dead_rate": round(r2, 4), "n_informative": n2}
    sx = b["gdc_internal"]["sex"]
    ok = b["usis_in_2plus_cases"] >= 50 and sx.get("disagree", 0) == 0
    g["H6"] = {"result": "pass" if ok else "fail", "usis_in_2plus_cases": b["usis_in_2plus_cases"],
               "sex_disagree": sx.get("disagree", 0)}
    rate, n = share(c["all"]["sex"], ["disagree"], ["agree", "disagree"])
    if c["pairs"] < 1000:
        g["H7"] = {"result": "fail", "pairs": c["pairs"], "sex_rate": rate, "n": n}
    elif n < MIN_PAIRS:
        g["H7"] = {"result": "not testable", "pairs": c["pairs"], "n": n}
    else:
        g["H7"] = {"result": "pass" if rate <= 0.01 else "fail", "pairs": c["pairs"],
                   "sex_rate": round(rate, 4), "n": n}
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    chosen, n_pages, subjects, facts = read_subjects(args.raw)
    entries = read_mappings(args.raw)
    cases = read_gdc(args.raw)
    by_dom, by_usi = fed_indexes(subjects)
    pairs, usi_links, links = mapping_links(entries, by_dom, by_usi)
    a = section_a(args.raw, subjects, facts)
    b = section_b(cases, by_usi, usi_links)
    c = dict(section_c(pairs), link_resolution=links)
    d = section_d(subjects, pairs)
    result = {"per_page": chosen["per_page"], "subject_pages_read": n_pages,
              "mapping_entries": len(entries),
              "A_internal_consistency": a, "B_gdc_target": b, "C_cpi_links": c,
              "D_overcount": d, "grades": grade(a, b, c)}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "concordance.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    log = json.load(open(os.path.join(args.raw, "fetch-log.json"), encoding="utf-8"))
    with open(os.path.join(args.out, "fetch-log.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1)
    print(json.dumps({"grades": result["grades"], "D": d}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
