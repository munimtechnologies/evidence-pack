"""Does LinkCheck 0.1.0 reproduce MV2's CCDI census on real data? (PRE-REGISTERED)

The predictions are in README.md in this folder, published at evidence-pack tag v0.6.0
before this job ran. The sealed job downloads, unchanged, LinkCheck and this folder from tag
v0.6.0 and the census code (analyze.py, fetch_ccdi.py) from tag v0.5.5, then:
  1  reads the kept second snapshot of the CCDI Data Federation, or, on a machine without
     it, a fresh snapshot taken by the census's own fetch_ccdi.py;
  2  turns it into LinkCheck input with adapt(): one record per served subject, and one
     link row per Participant Index association, with each USI association expanded into
     one row per subject that serves that USI;
  3  runs the census code and LinkCheck on the same data and compares them (P1-P4), and
     checks LinkCheck's looser rules and the absolute counts against the census and the
     stage-2 diagnostics of the second snapshot (P5-P6; kept snapshot only).

Aggregates only: counts, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os

import analyze
from linkcheck import core

# Second snapshot (2026-10-22/23): census re-run (diagnostics-v1) and stage-2 diagnostics.
SNAPSHOT2 = {
    "absolute": {"records": 153580, "pairs_exact": 20496, "persons": 135849,
                 "naive_overcount": 17731, "linked_persons": 14847, "records_in_links": 32578},
    "rules": {"pairs_added_by_rule": {"alt_id": 1094}, "pairs_with_rules": 21590,
              "overcount_with_rules": {"persons": 135044, "naive_overcount": 18536,
                                       "linked_persons": 15403, "records_in_links": 33939},
              "extra_disagree": {"sex": 3, "race": 0, "ethnicity": 2}}}
RENAME = {"vital": "vital_status", "death_age": "age_at_death"}
PRIORITY = ("CCDI-DCC", "KidsFirst")
LABEL = ("PRE-REGISTERED: predictions P1-P6 in README.md, published at evidence-pack tag "
         "v0.6.0 before this job ran")


def row(a_source, a_id, b_source, b_id):
    return {"a_source": a_source, "a_id": a_id, "b_source": b_source, "b_id": b_id}


def adapt(subjects, entries):
    """Census subjects and Participant Index entries -> (records, links, counts).

    A domain name is matched to a source the way the census matches it: case-insensitively,
    by source name or by namespace name. Associations are kept by the census's rules: a
    USI association (domain "usi", a six-letter USI) links to every subject serving that
    USI as its name or an alternate id; any other association counts only if its category
    is organizational_identifier. Nothing is resolved here; LinkCheck does that."""
    records, dom = [], {}
    for s in subjects.values():
        dom.setdefault(s["source"].lower(), s["source"])
        dom.setdefault(s["ns"].lower(), s["source"])
        raw = s["raw"]
        records.append({"source": s["source"], "id": s["name"], "alt_ids": s["alt"],
                        "sex": raw["sex"], "race": raw["race"], "ethnicity": raw["ethnicity"],
                        "vital_status": raw["vital_status"], "age_at_vital_status": s["age"]})
    _, by_usi = analyze.fed_indexes(subjects)

    def end(d, pid):
        d = str(d)
        return dom.get(d.lower(), d), str(pid)

    links, counts = [], collections.Counter()
    for e in entries:
        a_src, a_id = end(e.get("domain_name"), e.get("participant_id"))
        for x in e.get("associated_ids") or []:
            if not isinstance(x, dict):
                counts["association_not_an_object"] += 1
                continue
            d, pid = str(x.get("domain_name")), str(x.get("participant_id"))
            if d.lower() == "usi" and analyze.USI.match(pid):
                counts["usi_association"] += 1
                targets = by_usi.get(pid, [])
                if not targets:
                    counts["usi_served_by_no_subject"] += 1
                for t in targets:
                    links.append(row(a_src, a_id, t["source"], t["name"]))
                continue
            if x.get("domain_category") != "organizational_identifier":
                counts["other_category_skipped"] += 1
                continue
            counts["org_association"] += 1
            links.append(row(a_src, a_id, *end(d, pid)))
    counts["link_rows"] = len(links)
    return records, links, dict(sorted(counts.items()))


def census(subjects, entries):
    """The census's own pairs, section C and section D on the same data (analyze.py v0.5.5)."""
    by_dom, by_usi = analyze.fed_indexes(subjects)
    pairs, _, link_counts = analyze.mapping_links(entries, by_dom, by_usi)
    keys = {tuple(sorted(((s["source"], s["name"]), (t["source"], t["name"]))))
            for s, t in pairs.values()}
    return {"pairs": len(pairs), "pair_keys": keys, "links": link_counts,
            "c": analyze.section_c(pairs), "d": analyze.section_d(subjects, pairs)}


def renamed(t):
    return {RENAME.get(k, k): v for k, v in t.items()}


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def disagree(t, field):
    return t[field].get("disagree", 0)


def grade(ref, report, lc_exact, n_subjects, expected=None):
    """P1-P4 compare LinkCheck with the census code on the same data. P5-P6 compare with the
    numbers of the second snapshot; they are graded only when `expected` is given."""
    oc_e, oc_r = report["overcount"]["exact"], report["overcount"]["with_rules"]
    d = ref["d"]
    repeats = sum(v["repeated_records"] for v in report["completeness"].values())
    out = {}
    out["P1"] = verdict(oc_e["records"] == n_subjects and repeats == 0,
                        linkcheck_records=oc_e["records"], census_subjects=n_subjects,
                        repeated_records=repeats)
    only_census, only_lc = len(ref["pair_keys"] - lc_exact), len(lc_exact - ref["pair_keys"])
    out["P2"] = verdict(only_census == 0 and only_lc == 0
                        and report["links"]["pairs_exact"] == ref["pairs"],
                        linkcheck_pairs=report["links"]["pairs_exact"], census_pairs=ref["pairs"],
                        census_only=only_census, linkcheck_only=only_lc)
    mine = {"persons": oc_e["persons"], "naive_overcount": oc_e["naive_overcount"],
            "linked_persons": oc_e["linked_persons"], "records_in_links": oc_e["records_in_links"]}
    theirs = {"persons": d["deduplicated_total"], "naive_overcount": d["naive_overcount"],
              "linked_persons": d["linked_persons"],
              "records_in_links": d["subjects_in_cross_source_links"]}
    out["P3"] = verdict(mine == theirs, linkcheck=mine, census=theirs)
    lc_c, ref_c = report["conflicts"]["exact"], ref["c"]
    ref_pairs = {k: renamed(v) for k, v in ref_c["by_source_pair"].items()}
    differing = sorted(k for k in set(ref_pairs) | set(lc_c["by_source_pair"])
                       if ref_pairs.get(k) != lc_c["by_source_pair"].get(k))
    out["P4"] = verdict(renamed(ref_c["all"]) == lc_c["all"] and not differing,
                        all_equal=renamed(ref_c["all"]) == lc_c["all"],
                        source_pairs=len(ref_pairs), source_pairs_differing=differing)
    if expected is None:
        out["P5"] = out["P6"] = {"grade": "not graded",
                                 "why": "fresh snapshot: the stage-2 numbers belong to snapshot 2"}
        return out
    r = expected["rules"]
    got_r = {k: oc_r[k] for k in r["overcount_with_rules"]}
    rules_all, exact_all = report["conflicts"]["with_rules"]["all"], lc_c["all"]
    extra = {f: disagree(rules_all, f) - disagree(exact_all, f) for f in r["extra_disagree"]}
    out["P5"] = verdict(report["links"]["pairs_added_by_rule"] == r["pairs_added_by_rule"]
                        and report["links"]["pairs_with_rules"] == r["pairs_with_rules"]
                        and got_r == r["overcount_with_rules"] and extra == r["extra_disagree"],
                        pairs_added_by_rule=report["links"]["pairs_added_by_rule"],
                        pairs_with_rules=report["links"]["pairs_with_rules"],
                        overcount_with_rules=got_r, extra_disagree=extra)
    a = expected["absolute"]
    got_a = dict(mine, records=oc_e["records"], pairs_exact=report["links"]["pairs_exact"])
    out["P6"] = verdict(got_a == a, **got_a)
    return out


def pick(kept, fallback):
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        return kept, "kept second snapshot"
    if fallback and os.path.exists(os.path.join(fallback, "subject", "chosen.json")):
        return fallback, "fresh snapshot taken by this job"
    raise SystemExit("no snapshot under " + kept + (" or " + fallback if fallback else ""))


def run(raw, expected=None, priority=PRIORITY):
    _, n_pages, subjects, facts = analyze.read_subjects(raw)
    entries = analyze.read_mappings(raw)
    records, links, adapter_counts = adapt(subjects, entries)
    ref = census(subjects, entries)
    report, _ = core.check(records, links, core.RULES, priority)
    index = core.Index(records)
    pairs, _ = core.resolve_links(index, links, core.RULES)
    lc_exact = {p for p, rule in pairs.items() if rule == "exact"}
    return {"label": LABEL, "linkcheck": report["tool"],
            "input": {"subject_pages": n_pages, "subjects": len(subjects),
                      "mapping_entries": len(entries),
                      "source_page_errors": {k: v["errors"] for k, v in sorted(facts.items())}},
            "grades": grade(ref, report, lc_exact, len(subjects), expected),
            "adapter_counts": adapter_counts, "census_link_counts": ref["links"],
            "linkcheck_report": report}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="kept snapshot (raw/ folder of ccdi-diag-v1)")
    ap.add_argument("--fallback-raw", help="fresh snapshot, used only if --raw has none")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw, which = pick(args.raw, args.fallback_raw)
    result = run(raw, SNAPSHOT2 if raw == args.raw else None)
    result["input"]["snapshot"] = which
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "repro.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot": which, "grades": result["grades"]}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
