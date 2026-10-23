"""POST-HOC diagnostics, stage 2, for the CCDI concordance census (ccdi-concord-v1).

Written on 2026-10-23 AFTER the ccdi-diag-v1 results were seen. Nothing here was
pre-registered; every number it produces is labelled post hoc in the write-up. It reads the
second snapshot that ccdi-diag-v1 kept (no new crawl) and asks:

  1  Do the Participant Index links that did not resolve to a served subject resolve under
     a looser rule? Three rules, each tried on every such link: the target source's
     alternate identifiers (unique matches only), the part after the last underscore, and
     the same name served by any other source. For links a rule resolves: is the pair new,
     do the linked records agree (same tally as the census), and what does it do to the
     over-count (section D)?
  2  Which metadata keys each source fills, and, for linked pairs with ccdi-ecDNA on one
     side, the age differences for every numeric key whose name contains "age".
  3  (--probe, network) The PCDC part of /subject page 35 failed with identical bytes in
     both snapshots. Re-request it at per_page 100, 50, 25 and 10, with page 34 as a
     control, and count PCDC records the snapshot lacks.

Aggregates only: no participant IDs leave the job. A link segment is printed only when it
looks like a program name or a COG protocol number (public study labels); anything else is
reduced to its shape, and a USI is printed as <USI>.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import os
import re
import time

import analyze
import diag
import fetch_ccdi

PROGRAM = re.compile(r"^[A-Z]{3}$")
PROTOCOL = re.compile(r"^A[A-Z]{3}\d{2}[A-Z0-9]\d$")
RULES = ("alt_identifier", "after_last_underscore", "name_in_other_source")
PROBES = (((34, 100), (35, 100), (69, 50), (70, 50))
          + tuple((p, 25) for p in range(137, 141)) + tuple((p, 10) for p in range(341, 351)))


def segment_label(seg):
    if analyze.USI.match(seg):
        return "<USI>"
    if PROGRAM.match(seg) or PROTOCOL.match(seg):
        return seg
    return diag.shape(seg)


def link_label(pid):
    return "_".join(segment_label(seg) for seg in str(pid).split("_"))


def filled(v):
    x = analyze.val(v)
    return x is not None and x != "" and x != [] and x != {}


# ---------- 1 looser link rules ----------

def indexes(subjects):
    alt, names = collections.defaultdict(list), collections.defaultdict(list)
    for s in subjects.values():
        for n in s["alt"]:
            if s not in alt[(s["source"], n)]:
                alt[(s["source"], n)].append(s)
        names[s["name"]].append(s)
    return alt, names


def candidates(pid, src, by_dom, alt, names):
    """{rule: subject} for every rule that resolves pid to exactly one subject."""
    found = {}
    hits = alt.get((src, pid), [])
    if len(hits) == 1:
        found["alt_identifier"] = hits[0]
    if "_" in pid:
        t = by_dom.get((src.lower(), pid.rsplit("_", 1)[1]))
        if t is not None:
            found["after_last_underscore"] = t
    others = [t for t in names.get(pid, []) if t["source"] != src]
    if len(others) == 1:
        found["name_in_other_source"] = others[0]
    return found


def loose_links(entries, subjects, by_dom, pairs):
    src_of = {}
    for s in subjects.values():
        src_of.setdefault(s["source"].lower(), s["source"])
        src_of.setdefault(s["ns"].lower(), s["source"])
    alt, names = indexes(subjects)
    rows = collections.defaultdict(lambda: {"links": 0, "shapes": collections.Counter(),
                                            "rules": collections.Counter(),
                                            "agreement": collections.Counter(),
                                            "outcome": collections.Counter(),
                                            "other": collections.Counter()})
    new_pairs = collections.defaultdict(dict)
    for e in entries:
        s = by_dom.get((str(e.get("domain_name")).lower(), str(e.get("participant_id"))))
        if s is None:
            continue
        for a in e.get("associated_ids") or []:
            if a.get("domain_category") != "organizational_identifier":
                continue
            dom, pid = str(a.get("domain_name")), str(a.get("participant_id"))
            src = src_of.get(dom.lower())
            if src is None or by_dom.get((dom.lower(), pid)) is not None:
                continue
            r = rows[src]
            r["links"] += 1
            r["shapes"][link_label(pid)] += 1
            found = candidates(pid, src, by_dom, alt, names)
            for rule in found:
                r["rules"][rule] += 1
            if len(found) > 1:
                same = len({id(t) for t in found.values()}) == 1
                r["agreement"]["rules_agree" if same else "rules_disagree"] += 1
            if "name_in_other_source" in found:
                r["other"][found["name_in_other_source"]["source"]] += 1
            if not found:
                r["outcome"]["none"] += 1
                continue
            rule = next(x for x in RULES if x in found)
            t = found[rule]
            if t is s:
                r["outcome"][rule + ": the linking record itself"] += 1
            elif t["source"] == s["source"]:
                r["outcome"][rule + ": another record of the linking source"] += 1
            else:
                key = tuple(sorted([s["key"], t["key"]]))
                if key in pairs:
                    r["outcome"][rule + ": pair already linked"] += 1
                else:
                    r["outcome"][rule + ": new pair"] += 1
                    new_pairs[rule][key] = (s, t)
    out = {}
    for src, r in sorted(rows.items()):
        out[src] = {"unresolved_links": r["links"], "link_shapes": diag.top(r["shapes"], 10),
                    "rules_matching": dict(sorted(r["rules"].items())),
                    "rule_agreement": dict(sorted(r["agreement"].items())),
                    "outcome": dict(sorted(r["outcome"].items())),
                    "name_in_other_source_by_source": dict(sorted(r["other"].items()))}
    effect = {}
    merged_all = dict(pairs)
    for rule, found_pairs in sorted(new_pairs.items()):
        by_pair = collections.defaultdict(list)
        for s, t in found_pairs.values():
            by_pair[" | ".join(sorted([s["source"], t["source"]]))].append((s, t))
        merged = dict(pairs)
        merged.update(found_pairs)
        merged_all.update(found_pairs)
        effect[rule] = {"new_unique_pairs": len(found_pairs),
                        "by_source_pair": {k: analyze.tally(v) for k, v in sorted(by_pair.items())},
                        "overcount_with_these_pairs": analyze.section_d(subjects, merged)}
    effect["all_rules"] = {"new_unique_pairs": len(merged_all) - len(pairs),
                           "overcount_with_these_pairs": analyze.section_d(subjects, merged_all)}
    return {"by_target_source": out, "new_pairs": effect,
            "overcount_census": analyze.section_d(subjects, pairs)}


# ---------- 2 metadata keys and ecDNA ages ----------

def metadata(raw, pairs):
    keys, served, ages = collections.defaultdict(collections.Counter), collections.Counter(), {}
    _, paths = analyze.subject_pages(raw)
    for p in paths:
        parsed = analyze.load(p)
        for item in parsed if isinstance(parsed, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("data"), list):
                continue
            src = item.get("source")
            for rec in item["data"]:
                if not isinstance(rec, dict):
                    continue
                key = analyze.fed_subject(rec, src)["key"]
                if key in ages:
                    continue
                served[src] += 1
                found = {}
                for k, v in (rec.get("metadata") or {}).items():
                    if filled(v):
                        keys[src][k] += 1
                    if "age" in k.lower():
                        n = analyze.num(analyze.val(v))
                        if n is not None:
                            found[k] = n
                ages[key] = found
    diffs, ratios = collections.defaultdict(list), collections.defaultdict(list)
    for s, t in pairs.values():
        if s["source"] == t["source"] or "ccdi-ecDNA" not in (s["source"], t["source"]):
            continue
        e, o = (s, t) if s["source"] == "ccdi-ecDNA" else (t, s)
        for k1, v1 in sorted(ages.get(e["key"], {}).items()):
            for k2, v2 in sorted(ages.get(o["key"], {}).items()):
                name = "%s: ecDNA %s minus %s" % (o["source"], k1, k2)
                diffs[name].append(v1 - v2)
                if v1 > 0 and v2 > 0:
                    ratios[name].append(v1 / v2)
    age_out = {}
    for name, ds in sorted(diffs.items()):
        row = diag.quantiles(ds)
        row["within_1_day"] = sum(1 for d in ds if abs(d) <= 1)
        row["within_365_days"] = sum(1 for d in ds if abs(d) <= 365)
        row["ratio_median"] = round(analyze.median(ratios[name]), 3) if ratios[name] else None
        age_out[name] = row
    return {"served_records": dict(sorted(served.items())),
            "filled_keys": {src: dict(sorted(c.items())) for src, c in sorted(keys.items())},
            "ecDNA_age_differences_days": age_out}


# ---------- 3 the persistent PCDC page ----------

def probe(subjects, get=None, pause=fetch_ccdi.PAUSE):
    get = get or fetch_ccdi.get
    names = {s["name"] for s in subjects.values() if s["source"] == "PCDC"}
    rows = []
    for page, per_page in PROBES:
        time.sleep(pause)
        status, body = get(fetch_ccdi.fed_url("/subject", page=page, per_page=per_page))[:2]
        try:
            parsed = json.loads(body)
        except (TypeError, ValueError):
            parsed = None
        item = None
        if isinstance(parsed, list):
            item = next((x for x in parsed if isinstance(x, dict) and x.get("source") == "PCDC"),
                        None)
        data = item.get("data") if item else None
        row = {"page": page, "per_page": per_page, "status": status}
        if isinstance(data, list):
            got = [analyze.fed_subject(r, "PCDC")["name"] for r in data if isinstance(r, dict)]
            row["records"] = len(got)
            row["not_in_snapshot"] = sum(1 for n in got if n not in names)
        else:
            row["records"] = None
            row["error"] = diag.scrub(json.dumps({k: v for k, v in (item or {}).items()
                                                  if k not in ("data", "summary")}))
        rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="raw/ folder kept by ccdi-diag-v1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true", help="re-request the failing PCDC page")
    args = ap.parse_args(argv)
    if not os.path.exists(os.path.join(args.raw, "subject", "chosen.json")):
        raise SystemExit("kept snapshot not found under " + args.raw)
    _, _, subjects, _ = analyze.read_subjects(args.raw)
    entries = analyze.read_mappings(args.raw)
    by_dom, by_usi = analyze.fed_indexes(subjects)
    pairs, _, links = analyze.mapping_links(entries, by_dom, by_usi)
    result = {"label": "POST HOC: written after ccdi-diag-v1 results were seen",
              "snapshot_check": {"subjects": len(subjects), "mapping_entries": len(entries),
                                 "pairs": len(pairs),
                                 "entry_unresolved": links.get("entry_unresolved", 0)},
              "loose_links": loose_links(entries, subjects, by_dom, pairs),
              "metadata": metadata(args.raw, pairs)}
    if args.probe:
        result["page35_probe"] = probe(subjects)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "diagnostics2.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({"snapshot_check": result["snapshot_check"],
                      "outcomes": {k: v["outcome"] for k, v in
                                   result["loose_links"]["by_target_source"].items()},
                      "page35_probe": result.get("page35_probe")}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
