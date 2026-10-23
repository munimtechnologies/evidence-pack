"""A fresh CCDI snapshot taken by fetch_robust.py, and the 87 shared CCDI-DCC ids (PRE-REGISTERED).

The predictions are in README.md in this folder, published at evidence-pack tag v0.8.2
before the sealed job ccdi-fresh-v1 ran. The job first takes a fresh snapshot of the CCDI
Data Federation with fetch_robust.py (tag v0.8.0) into its own folder on the data volume,
then runs repro2.py (tag v0.8.0) on it unchanged, which grades P1-P4 and F1 as
pre-registered at v0.8.0. This module then:
  1  grades G1-G3 on the fresh snapshot (G1, G2 against the second snapshot's numbers);
  2  describes the subjects of one source that share a name, split by whether the name is
     USI-shaped, with the study namespaces involved, and whether the census's own
     cross-source links already put the two records in one person;
  3  does the same description on the kept second snapshot, if this machine holds it.

Aggregates only: counts, source names and study namespace names (public dbGaP study
accessions), never participant IDs.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os

import analyze
import ensure_snapshot2

# Second snapshot (2026-10-22/23): /subject/summary totals (diagnostics-v1, paging-audit-v1)
# and the shared CCDI-DCC names (linkcheck-repro-v1 and -v2, S1).
TOTALS2 = {"CCDI-DCC": 59795, "KidsFirst": 38440, "PCDC": 24432, "StJude": 14681,
           "Treehouse": 12723, "ccdi-ecDNA": 3205, "ccdi-iusccc-pst": 504}
SHARED2 = {"groups": 87, "extra_records": {"CCDI-DCC": 87}, "group_sizes": {"2": 87},
           "same_namespace_name": 0}
CONFLICT = {"sex": ("disagree",), "ethnicity": ("disagree",), "race": ("disagree", "overlap"),
            "vital": ("alive_after_death", "alive_dead_no_ages"),
            "death_age": ("within_30_days", "over_30_days")}
LABEL = ("PRE-REGISTERED: predictions G1-G3 in README.md, published at evidence-pack tag "
         "v0.8.2 before this job ran")


def totals(raw):
    """{source: total} from /subject/summary, read as the census reads it (section A),
    leaving out any item that names no source."""
    summary = analyze.load(os.path.join(raw, "fed", "subject-summary.json.gz")) or []
    return {i.get("source"): (i.get("counts") or {}).get("total")
            for i in summary if isinstance(i, dict) and i.get("source")}


def components(pairs):
    """find() over the census's cross-source pairs, as in analyze.section_d."""
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
    return find, {k for pair in pairs for k in pair}


def persons(n_subjects, pairs):
    """De-duplicated persons, computed as analyze.section_d does."""
    find, members = components(pairs)
    return n_subjects - len(members) + len({find(k) for k in members})


def conflicts(t):
    """Number of pairs with any conflict in a tally."""
    return {f: sum(t[f].get(k, 0) for k in keys) for f, keys in CONFLICT.items()}


def describe(subjects, entries):
    """Subjects of one source that share a name, and what the census's links say of them."""
    by_dom, by_usi = analyze.fed_indexes(subjects)
    pairs, _, _ = analyze.mapping_links(entries, by_dom, by_usi)
    find, members = components(pairs)
    groups = collections.defaultdict(list)
    for s in subjects.values():
        groups[(s["source"], s["name"])].append(s)
    multi = [g for _, g in sorted(groups.items()) if len(g) > 1]
    shape, spaces, linkage = collections.Counter(), collections.Counter(), collections.Counter()
    by_shape = collections.defaultdict(list)
    extra, sizes = collections.Counter(), collections.Counter()
    merged = dict(pairs)
    for g in multi:
        kind = "usi" if analyze.USI.match(g[0]["name"]) else "other"
        shape[kind] += 1
        extra[g[0]["source"]] += len(g) - 1
        sizes[str(len(g))] += 1
        spaces[" | ".join(sorted(s["ns"] for s in g))] += 1
        by_shape[kind] += [(g[0], other) for other in g[1:]]
        keys = [s["key"] for s in g]
        inside = [k for k in keys if k in members]
        if len(inside) == len(keys) and len({find(k) for k in keys}) == 1:
            linkage["one_person_by_links"] += 1
        elif len(inside) == len(keys):
            linkage["different_persons_by_links"] += 1
        elif inside:
            linkage["only_some_in_links"] += 1
        else:
            linkage["none_in_links"] += 1
        for k in keys[1:]:
            merged[tuple(sorted([keys[0], k]))] = None
    tallies = {k: analyze.tally(v) for k, v in sorted(by_shape.items())}
    return {"groups": len(multi), "extra_records": dict(sorted(extra.items())),
            "group_sizes": dict(sorted(sizes.items())),
            "same_namespace_name": sum(1 for g in multi if len({s["ns"] for s in g}) < len(g)),
            "groups_by_name_shape": dict(sorted(shape.items())),
            "agreement_by_name_shape": tallies,
            "conflicts_by_name_shape": {k: conflicts(t) for k, t in tallies.items()},
            "namespace_pairs": dict(sorted(spaces.items())),
            "linkage": dict(sorted(linkage.items())),
            "census_persons": persons(len(subjects), pairs),
            "persons_if_shared_names_are_one_person": persons(len(subjects), merged)}


def verdict(ok, **observed):
    return {"grade": "pass" if ok else "fail", "observed": observed}


def grade(got_totals, shared):
    out = {}
    got = {k: got_totals.get(k) for k in sorted(set(TOTALS2) | set(got_totals))}
    out["G1"] = verdict(got == dict(sorted(TOTALS2.items())), totals=got,
                        differing=sorted(k for k in got if got[k] != TOTALS2.get(k)))
    mine = {k: shared[k] for k in SHARED2}
    out["G2"] = verdict(mine == SHARED2, **mine)
    found = {k: v for k, c in shared["conflicts_by_name_shape"].items()
             for v in [{f: n for f, n in c.items() if n}] if v}
    out["G3"] = verdict(not found and set(shared["groups_by_name_shape"]) == {"usi", "other"},
                        conflicts=found, groups_by_name_shape=shared["groups_by_name_shape"])
    return out


def run(raw):
    _, _, subjects, _ = analyze.read_subjects(raw)
    entries = analyze.read_mappings(raw)
    return {"subjects": len(subjects), "mapping_entries": len(entries),
            "totals": totals(raw), "shared_names": describe(subjects, entries)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh-root", required=True,
                    help="folder holding this job's fresh snapshot (ccdi-raw-fresh-<UTC time>)")
    ap.add_argument("--kept", help="kept second snapshot, described too if present")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    found = ensure_snapshot2.complete(args.fresh_root)
    if not found:
        raise SystemExit("no complete fresh snapshot under " + args.fresh_root)
    fresh = run(found[-1])
    result = {"label": LABEL, "fresh_snapshot": os.path.basename(found[-1]),
              "complete": json.load(open(os.path.join(found[-1], "complete.json"),
                                         encoding="utf-8")),
              "grades": grade(fresh["totals"], fresh["shared_names"]), "fresh": fresh}
    if args.kept and os.path.exists(os.path.join(args.kept, "subject", "chosen.json")):
        result["kept_second_snapshot"] = run(args.kept)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "fresh1.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
