"""LinkCheck input from a saved snapshot of NCI's CCDI Data Federation (0.4.0).

A snapshot is the folder that the census's fetcher (evidence-pack tag v0.5.5,
ccdi/concordance-v1/fetch_ccdi.py) or the robust fetcher (tag v0.8.0,
ccdi/linkcheck-repro-v2/fetch_robust.py) writes, each response body gzipped as it came:
  subject/chosen.json            {"per_page": 100, "first_page": "probe-100.json", ...}
  subject/probe-<n>.json.gz      /subject page 1 (the probe the fetcher chose)
  subject/page-NNNN.json.gz      /subject pages 2, 3, ...
  mapping/page-NNNN.json.gz      /subject-mapping (Participant Index) pages 1, 2, ...
  fed/subject-summary.json.gz    /subject/summary

read_snapshot() turns it into:
  records  one per served subject: source, id (the subject's name), namespace (its study),
           alt_ids (the names of its other identifiers), and sex, race, ethnicity,
           vital_status and age_at_vital_status as served. Copies with the same source,
           organization, namespace and name are one subject; the first copy is kept;
  links    one row per Participant Index association, by the census's rules: a USI
           association (domain "usi", a six-letter USI) links the entry to every served
           subject that has that USI as its name or as an alternate id; any other
           association counts only if its category is organizational_identifier. A link
           end's domain name becomes a source and namespace when it is a namespace name
           (case-insensitively), a source when it is a source name, and is otherwise kept
           as it is. Nothing is resolved here: core.check() does that;
  pages    the per-source entry counts of every saved page of both endpoints, and each
           source's total from /subject/summary, for paging.audit().
check() runs the LinkCheck report and both paging audits on it in one step. Since 0.5.0 it
also takes declared OMB conventions per source (see core.race_standard), and the report
has a "standards" section; the reading of the snapshot itself is unchanged.

This is the reading MV2's pre-registered checks used (adapt() in ccdi/linkcheck-repro-v2,
tag v0.8.0, on the census's reader, tag v0.5.5; ccdi_pages.py, tag v0.7.0), moved into the
package so that one command checks a snapshot.

The records and links hold participant ids: keep them as private as the snapshot itself.
The report and the audits hold counts only.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import glob
import gzip
import json
import os
import re
import sys

from . import core, paging

USI = re.compile(r"^P[A-Z]{5}$")
PAGE = re.compile(r"^page-(\d+)\.json\.gz$")


# ---------- files ----------

def load(path):
    """The parsed JSON body of a saved response, or None if it is missing or not JSON."""
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as fh:
        body = fh.read()
    try:
        return json.loads(body)
    except ValueError:
        return None


def numbered(folder):
    """{page number: path} for the page-NNNN.json.gz files in a folder."""
    out = {}
    for path in glob.glob(os.path.join(folder, "page-*.json.gz")):
        m = PAGE.match(os.path.basename(path))
        if m:
            out[int(m.group(1))] = path
    return out


def subject_files(raw):
    """(per_page, {page number: path}) of the saved /subject pages."""
    with open(os.path.join(raw, "subject", "chosen.json"), encoding="utf-8") as fh:
        chosen = json.load(fh)
    files = numbered(os.path.join(raw, "subject"))
    files[1] = os.path.join(raw, "subject", chosen["first_page"] + ".gz")
    return chosen["per_page"], files


# ---------- subjects ----------

def val(x):
    return x.get("value") if isinstance(x, dict) else x


def subject(rec, source):
    """(key, record) for one served /subject entry. The key is (source, organization,
    namespace, name), as in the census; the record is LinkCheck input."""
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
    key = (source, str(ns.get("organization")), str(ns.get("name")), str(ident.get("name")))
    return key, {"source": source, "id": key[3], "namespace": key[2], "alt_ids": alt,
                 "sex": val(md.get("sex")), "race": [val(r) for r in races],
                 "ethnicity": val(md.get("ethnicity")),
                 "vital_status": val(md.get("vital_status")),
                 "age_at_vital_status": core.num(val(md.get("age_at_vital_status")))}


def read_subjects(raw):
    """Every saved /subject page, in page order. Returns (per_page, records, pages, facts,
    lookup): the served subjects (first copy kept); per page, each source's entries (None
    where its part of the page is an error; the whole page None if it is not a JSON list);
    per source, the entries served, repeated copies and error pages; and the lookups the
    Participant Index side needs to give an entry to a source."""
    per_page, files = subject_files(raw)
    kept, pages = {}, {}
    facts = collections.defaultdict(lambda: {"entries": 0, "repeats": 0, "error_pages": 0})
    domains, names = {}, {}
    for n in sorted(files):
        parsed = load(files[n])
        if not isinstance(parsed, list):
            pages[n] = None
            continue
        counts = {}
        for item in parsed:
            if not isinstance(item, dict) or "source" not in item:
                continue
            src = item["source"]
            data = item.get("data")
            if not isinstance(data, list):
                counts[str(src)] = None
                facts[str(src)]["error_pages"] += 1
                continue
            counts[str(src)] = len(data)
            domains.setdefault(str(src).lower(), str(src))
            for rec in data:
                key, r = subject(rec, src)
                facts[str(src)]["entries"] += 1
                if key in kept:
                    facts[str(src)]["repeats"] += 1
                else:
                    kept[key] = r
                ns = key[2].lower()
                domains.setdefault(ns, str(src))
                names.setdefault((str(src).lower(), key[3]), str(src))
                names.setdefault((ns, key[3]), str(src))
        pages[n] = counts
    facts = {s: dict(f) for s, f in sorted(facts.items())}
    return per_page, list(kept.values()), pages, facts, (domains, names)


# ---------- the Participant Index ----------

def read_mapping(raw, lookup):
    """Every saved /subject-mapping page, in page order. Returns (entries, pages, unmapped):
    the Participant Index entries; per page, each source's entries (the whole page None if it
    is not a JSON object); and the entries whose domain name matches no source. An entry
    goes to the source of the served subject it names (domain name as a source or
    namespace name, case-insensitively, plus the participant id), else to the source its
    domain name alone names."""
    domains, names = lookup
    entries, pages, unmapped = [], {}, 0
    for n, path in sorted(numbered(os.path.join(raw, "mapping")).items()):
        parsed = load(path)
        if not isinstance(parsed, dict):
            pages[n] = None
            continue
        counts = {}
        for e in parsed.get("participant_ids") or []:
            if not isinstance(e, dict):
                continue
            entries.append(e)
            dom = str(e.get("domain_name")).lower()
            src = names.get((dom, str(e.get("participant_id")))) or domains.get(dom)
            if src is None:
                unmapped += 1
                continue
            counts[src] = counts.get(src, 0) + 1
        pages[n] = counts
    return entries, pages, unmapped


def links_from(records, entries):
    """(links, counts): one LinkCheck link row per Participant Index association kept by the
    census's rules, and what happened to the associations."""
    sources, spaces = {}, collections.defaultdict(list)
    by_dom, by_usi = {}, collections.defaultdict(list)
    for r in records:
        sources.setdefault(r["source"].lower(), r["source"])
        if (r["source"], r["namespace"]) not in spaces[r["namespace"].lower()]:
            spaces[r["namespace"].lower()].append((r["source"], r["namespace"]))
        by_dom.setdefault((r["source"].lower(), r["id"]), r)
        by_dom.setdefault((r["namespace"].lower(), r["id"]), r)
        for n in [r["id"]] + r["alt_ids"]:
            if USI.match(n) and all(t is not r for t in by_usi[n]):
                by_usi[n].append(r)
    links, counts = [], collections.Counter()

    def end(d, pid):
        d, pid = str(d), str(pid)
        found = spaces.get(d.lower(), [])
        if len(found) > 1:
            counts["domain_name_of_several_namespaces"] += 1
            r = by_dom.get((d.lower(), pid))
            if r is not None:
                return r["source"], pid, r["namespace"]
        if found:
            return found[0][0], pid, found[0][1]
        return sources.get(d.lower(), d), pid, ""

    def row(a, b):
        return {"a_source": a[0], "a_id": a[1], "a_namespace": a[2],
                "b_source": b[0], "b_id": b[1], "b_namespace": b[2]}

    for e in entries:
        a = end(e.get("domain_name"), e.get("participant_id"))
        for x in e.get("associated_ids") or []:
            if not isinstance(x, dict):
                counts["association_not_an_object"] += 1
                continue
            d, pid = str(x.get("domain_name")), str(x.get("participant_id"))
            if d.lower() == "usi" and USI.match(pid):
                counts["usi_association"] += 1
                targets = by_usi.get(pid, [])
                if not targets:
                    counts["usi_served_by_no_subject"] += 1
                for t in targets:
                    links.append(row(a, (t["source"], t["id"], t["namespace"])))
                continue
            if x.get("domain_category") != "organizational_identifier":
                counts["other_category_skipped"] += 1
                continue
            counts["org_association"] += 1
            links.append(row(a, end(d, pid)))
    counts["link_rows"] = len(links)
    return links, dict(sorted(counts.items()))


def summary_totals(raw):
    """{source: total} from /subject/summary; sources without a count are left out."""
    summary = load(os.path.join(raw, "fed", "subject-summary.json.gz"))
    out = {}
    for item in summary if isinstance(summary, list) else []:
        if isinstance(item, dict) and item.get("source") is not None:
            total = (item.get("counts") or {}).get("total")
            if paging.is_count(total):
                out[str(item["source"])] = total
    return out


# ---------- the whole snapshot ----------

def read_snapshot(raw):
    """Everything LinkCheck needs from a snapshot folder (see the module docstring)."""
    per_page, records, spages, facts, lookup = read_subjects(raw)
    entries, mpages, unmapped = read_mapping(raw, lookup)
    links, counts = links_from(records, entries)
    return {"per_page": per_page, "records": records, "links": links,
            "link_counts": counts, "subject_pages": spages, "mapping_pages": mpages,
            "unmapped_mapping_entries": unmapped, "totals": summary_totals(raw),
            "facts": facts, "mapping_entries": len(entries)}


def check(raw, rules=core.RULES, priority=(), declared=None):
    """(aggregate result, cohort rows) for a snapshot: the LinkCheck report and the paging
    audits of both endpoints. Only the result is aggregate. declared: {source: '1997' or
    '2024'} (0.5.0; see core.check)."""
    snap = read_snapshot(raw)
    report, rows = core.check(snap["records"], snap["links"], rules, priority, declared)
    per_page, totals = snap["per_page"], snap["totals"]
    result = {"tool": "linkcheck ccdi " + core.__version__,
              "input": {"per_page": per_page, "subject_pages": len(snap["subject_pages"]),
                        "mapping_pages": len(snap["mapping_pages"]),
                        "records": len(snap["records"]),
                        "mapping_entries": snap["mapping_entries"],
                        "link_rows": len(snap["links"]), "summary_totals": totals,
                        "unmapped_mapping_entries": snap["unmapped_mapping_entries"],
                        "subject_page_facts": snap["facts"]},
              "link_counts": snap["link_counts"],
              "linkcheck": report,
              "paging": {"subject": paging.audit(snap["subject_pages"], per_page, totals),
                         "mapping": paging.audit(snap["mapping_pages"], per_page, totals)}}
    return result, rows


def write_jsonl(rows, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="linkcheck.ccdi",
        description="LinkCheck report and paging audits for a saved CCDI Data Federation "
                    "snapshot.")
    ap.add_argument("--raw", required=True, help="snapshot folder (subject/, mapping/, fed/)")
    ap.add_argument("--out", required=True, help="aggregate result (JSON)")
    ap.add_argument("--rules", default=",".join(core.RULES),
                    help="link rules, comma-separated (default: exact,alt_id,suffix)")
    ap.add_argument("--priority", default="", help="source order for vital_priority")
    ap.add_argument("--declare", default="",
                    help="OMB race/ethnicity convention a source follows, e.g. "
                         "CCDI-DCC=2024; used only where a record's own values cannot tell")
    ap.add_argument("--min-cell", type=int, default=0,
                    help="show every count of the LinkCheck report from 1 to N-1 as <N")
    ap.add_argument("--records", help="also write the records (JSON Lines; holds ids)")
    ap.add_argument("--links", help="also write the link rows (JSON Lines; holds ids)")
    ap.add_argument("--cohort", help="also write the cohort table (CSV; holds ids)")
    args = ap.parse_args(argv)
    rules = tuple(r for r in args.rules.split(",") if r)
    priority = tuple(s for s in args.priority.split(",") if s)
    declared = core.parse_declared(args.declare)
    if args.records or args.links:
        snap = read_snapshot(args.raw)
        if args.records:
            write_jsonl(snap["records"], args.records)
        if args.links:
            write_jsonl(snap["links"], args.links)
    result, rows = check(args.raw, rules, priority, declared)
    result["linkcheck"] = core.suppress(result["linkcheck"], args.min_cell)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    if args.cohort:
        core.write_cohort(rows, args.cohort)
    print(json.dumps({"records": result["input"]["records"],
                      "pairs_exact": result["linkcheck"]["links"]["pairs_exact"],
                      "subject_refetch_pages": result["paging"]["subject"]["refetch_pages"],
                      "mapping_refetch_pages": result["paging"]["mapping"]["refetch_pages"]},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
