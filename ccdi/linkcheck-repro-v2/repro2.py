"""Does LinkCheck 0.3.0 reproduce MV2's CCDI census on real data? (PRE-REGISTERED)

The predictions are in README.md in this folder, published at evidence-pack tag v0.8.0
before this job ran. The first reproduction (ccdi/linkcheck-repro-v1, tag v0.6.0) failed
P1-P4 because LinkCheck 0.1.0 keyed records by (source, id), and 87 CCDI-DCC records share
an id with a record in another namespace. LinkCheck 0.3.0 keys a record by its namespace
too. The sealed job downloads, unchanged, the census code (analyze.py, fetch_ccdi.py) from
tag v0.5.5, the paging-audit reader (ccdi_pages.py) from tag v0.7.0, and LinkCheck 0.3.0
plus this folder from tag v0.8.0, then:
  1  reads the kept second snapshot of the CCDI Data Federation or, on a machine without
     it, a fresh snapshot kept under /data by fetch_robust.py (ensure_snapshot2.py);
  2  turns it into LinkCheck input with adapt(): one record per served subject, with its
     namespace, and one link row per Participant Index association. A link end names a
     namespace when its domain name is a namespace name; adapt() resolves nothing;
  3  runs the census code and LinkCheck on the same data and compares them (P1-P4);
     checks the looser rules, the absolute counts and the shared ids against the second
     snapshot (P5, P6, S1; kept snapshot only); and audits the paging of a fresh
     snapshot (F1; fresh snapshots only);
  4  describes the subjects of one source that share a name (aggregates only).

Aggregates only: counts, page numbers and source names, never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os

import analyze
import ccdi_pages
import ensure_snapshot2
from linkcheck import core, paging

# Second snapshot (2026-10-22/23): census re-run (diagnostics-v1), stage-2 diagnostics, and
# the 87 shared CCDI-DCC ids seen in the third snapshot (linkcheck-repro-v1).
SNAPSHOT2 = {
    "absolute": {"records": 153580, "pairs_exact": 20496, "persons": 135849,
                 "naive_overcount": 17731, "linked_persons": 14847, "records_in_links": 32578},
    "rules": {"pairs_added_by_rule": {"alt_id": 1094}, "pairs_with_rules": 21590,
              "overcount_with_rules": {"persons": 135044, "naive_overcount": 18536,
                                       "linked_persons": 15403, "records_in_links": 33939},
              "extra_disagree": {"sex": 3, "race": 0, "ethnicity": 2}},
    "shared": {"CCDI-DCC": 87}}
RENAME = {"vital": "vital_status", "death_age": "age_at_death"}
PRIORITY = ("CCDI-DCC", "KidsFirst")
LABEL = ("PRE-REGISTERED: predictions P1-P6, S1 and F1 in README.md, published at "
         "evidence-pack tag v0.8.0 before this job ran")


def row(a, b):
    return {"a_source": a[0], "a_id": a[1], "a_namespace": a[2],
            "b_source": b[0], "b_id": b[1], "b_namespace": b[2]}


def lc_key(s):
    """A census subject's LinkCheck key."""
    return core.key_of(s["source"], s["name"], s["ns"])


def adapt(subjects, entries):
    """Census subjects and Participant Index entries -> (records, links, counts).

    A domain name that is a namespace name (case-insensitively) becomes that source and
    namespace; one that is a source name becomes that source, with no namespace; anything
    else is kept as it is. If two sources have a namespace of that name, the census's own
    lookup by (domain, participant id) decides which, and this is counted. Associations are
    kept by the census's rules: a USI association (domain "usi", a six-letter USI) links to
    every subject serving that USI as its name or an alternate id; any other association
    counts only if its category is organizational_identifier."""
    records, sources, spaces = [], {}, collections.defaultdict(list)
    for s in subjects.values():
        sources.setdefault(s["source"].lower(), s["source"])
        if (s["source"], s["ns"]) not in spaces[s["ns"].lower()]:
            spaces[s["ns"].lower()].append((s["source"], s["ns"]))
        raw = s["raw"]
        records.append({"source": s["source"], "id": s["name"], "namespace": s["ns"],
                        "alt_ids": s["alt"], "sex": raw["sex"], "race": raw["race"],
                        "ethnicity": raw["ethnicity"], "vital_status": raw["vital_status"],
                        "age_at_vital_status": s["age"]})
    by_dom, by_usi = analyze.fed_indexes(subjects)
    links, counts = [], collections.Counter()

    def end(d, pid):
        d, pid = str(d), str(pid)
        found = spaces.get(d.lower(), [])
        if len(found) > 1:
            counts["domain_name_of_several_namespaces"] += 1
            s = by_dom.get((d.lower(), pid))
            if s is not None:
                return s["source"], pid, s["ns"]
        if found:
            return found[0][0], pid, found[0][1]
        return sources.get(d.lower(), d), pid, ""

    for e in entries:
        a = end(e.get("domain_name"), e.get("participant_id"))
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
                    links.append(row(a, (t["source"], t["name"], t["ns"])))
                continue
            if x.get("domain_category") != "organizational_identifier":
                counts["other_category_skipped"] += 1
                continue
            counts["org_association"] += 1
            links.append(row(a, end(d, pid)))
    counts["link_rows"] = len(links)
    return records, links, dict(sorted(counts.items()))


def census(subjects, entries):
    """The census's own pairs, section C and section D on the same data (analyze.py v0.5.5),
    with each pair written as two LinkCheck keys."""
    by_dom, by_usi = analyze.fed_indexes(subjects)
    pairs, _, link_counts = analyze.mapping_links(entries, by_dom, by_usi)
    keys = {tuple(sorted((lc_key(s), lc_key(t)))) for s, t in pairs.values()}
    return {"pairs": len(pairs), "pair_keys": keys, "links": link_counts,
            "c": analyze.section_c(pairs), "d": analyze.section_d(subjects, pairs)}


def shared_names(subjects):
    """Served subjects of one source that share a name: how many, and how alike they are.
    Agreement compares the first record of each group with each other one, with the
    census's comparisons (sex, ethnicity, race, vital status, age at death)."""
    groups = collections.defaultdict(list)
    for s in subjects.values():
        groups[(s["source"], s["name"])].append(s)
    multi = [g for _, g in sorted(groups.items()) if len(g) > 1]
    extra, sizes = collections.Counter(), collections.Counter()
    for g in multi:
        extra[g[0]["source"]] += len(g) - 1
        sizes[str(len(g))] += 1
    return {"groups": len(multi), "records": sum(len(g) for g in multi),
            "extra_records": dict(sorted(extra.items())),
            "group_sizes": dict(sorted(sizes.items())),
            "same_namespace_name": sum(1 for g in multi if len({s["ns"] for s in g}) < len(g)),
            "name_is_usi": sum(1 for g in multi if analyze.USI.match(g[0]["name"])),
            "namespaces_involved": len({s["ns"] for g in multi for s in g}),
            "agreement": analyze.tally([(g[0], other) for g in multi for other in g[1:]])}


def page_audits(raw):
    """LinkCheck's paging audit of both endpoints of a snapshot (ccdi_pages.py, v0.7.0)."""
    per_page, spages, domains, names = ccdi_pages.subject_walk(raw)
    mpages, unmapped = ccdi_pages.mapping_walk(raw, domains, names)
    totals = ccdi_pages.summary_totals(raw)
    return {"subject": paging.audit(spages, per_page, totals),
            "mapping": paging.audit(mpages, per_page, totals),
            "unmapped_mapping_entries": unmapped}


def renamed(t):
    return {RENAME.get(k, k): v for k, v in t.items()}


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def disagree(t, field):
    return t[field].get("disagree", 0)


def fetch_check(audits):
    """F1: both endpoints walked to their end, and every loss explained."""
    problems = {}
    for name in ("subject", "mapping"):
        rep = audits[name]
        for s, r in sorted(rep["sources"].items()):
            if r["total"] is None:
                continue
            if r["lost"]["pages_not_walked"] or r["unexplained"] != 0:
                problems.setdefault(name, {})[s] = {
                    "pages_not_walked": r["lost"]["pages_not_walked"],
                    "unexplained": r["unexplained"]}
        if rep["missing_pages"]:
            problems.setdefault(name, {})["missing_pages"] = rep["missing_pages"]
    return verdict(not problems, problems=problems,
                   last_page={n: audits[n]["last_page"] for n in ("subject", "mapping")})


def grade(ref, report, lc_exact, n_subjects, shared, expected=None, audits=None):
    """P1-P4 compare LinkCheck with the census code on the same data. P5, P6 and S1 use
    the second snapshot's numbers and are graded only when `expected` is given. F1 is
    graded only when the audits of a fresh snapshot are given."""
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
        for p in ("P5", "P6", "S1"):
            out[p] = {"grade": "not graded",
                      "why": "fresh snapshot: the predicted numbers belong to snapshot 2"}
    else:
        r = expected["rules"]
        got_r = {k: oc_r[k] for k in r["overcount_with_rules"]}
        rules_all, exact_all = report["conflicts"]["with_rules"]["all"], lc_c["all"]
        extra = {f: disagree(rules_all, f) - disagree(exact_all, f) for f in r["extra_disagree"]}
        out["P5"] = verdict(report["links"]["pairs_added_by_rule"] == r["pairs_added_by_rule"]
                            and report["links"]["pairs_with_rules"] == r["pairs_with_rules"]
                            and got_r == r["overcount_with_rules"]
                            and extra == r["extra_disagree"],
                            pairs_added_by_rule=report["links"]["pairs_added_by_rule"],
                            pairs_with_rules=report["links"]["pairs_with_rules"],
                            overcount_with_rules=got_r, extra_disagree=extra)
        a = expected["absolute"]
        got_a = dict(mine, records=oc_e["records"], pairs_exact=report["links"]["pairs_exact"])
        out["P6"] = verdict(got_a == a, **got_a)
        out["S1"] = verdict(shared["extra_records"] == expected["shared"],
                            extra_records=shared["extra_records"], groups=shared["groups"])
    if audits is None:
        out["F1"] = {"grade": "not graded",
                     "why": "kept second snapshot: taken by the census's own fetcher"}
    else:
        out["F1"] = fetch_check(audits)
    return dict(sorted(out.items()))


def pick(kept, root):
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        return kept, "kept second snapshot"
    found = ensure_snapshot2.complete(root) if root else []
    if found:
        return found[-1], "kept fresh snapshot " + os.path.basename(found[-1])
    raise SystemExit("no snapshot under " + kept + (" or " + root if root else ""))


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(raw, expected=None, fresh=False, priority=PRIORITY):
    _, n_pages, subjects, facts = analyze.read_subjects(raw)
    entries = analyze.read_mappings(raw)
    records, links, adapter_counts = adapt(subjects, entries)
    ref = census(subjects, entries)
    report, _ = core.check(records, links, core.RULES, priority)
    index = core.Index(records)
    pairs, _ = core.resolve_links(index, links, core.RULES)
    lc_exact = {p for p, rule in pairs.items() if rule == "exact"}
    shared = shared_names(subjects)
    audits = page_audits(raw)
    return {"label": LABEL, "linkcheck": report["tool"],
            "input": {"subject_pages": n_pages, "subjects": len(subjects),
                      "mapping_entries": len(entries),
                      "source_page_errors": {k: v["errors"] for k, v in sorted(facts.items())},
                      "fetch_retries": read_json(os.path.join(raw, "retries.json"))},
            "grades": grade(ref, report, lc_exact, len(subjects), shared, expected,
                            audits if fresh else None),
            "adapter_counts": adapter_counts, "census_link_counts": ref["links"],
            "shared_names": shared, "paging": audits, "linkcheck_report": report}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True, help="kept second snapshot (raw/ of ccdi-diag-v1)")
    ap.add_argument("--fresh-root", help="folder holding kept fresh snapshots "
                                         "(ccdi-raw-fresh-<UTC time>, with complete.json)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw, which = pick(args.kept, args.fresh_root)
    second = raw == args.kept
    result = run(raw, SNAPSHOT2 if second else None, fresh=not second)
    result["input"]["snapshot"] = which
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "repro2.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot": which, "grades": result["grades"],
                      "shared_names": result["shared_names"]}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
