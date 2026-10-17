# rebuild_units.py - Rebuild the article-1 v1 units file with the frozen article1_check.py, and split it for publishing.
# Amendment: findings/article-number-1-openalex-prereg-v2-amendment-2026-10-17.md
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Standard library only. The v1 units file is over the 2 MB per-file publishing limit, so the v2 test reads this rebuild.
import argparse
import json
import os
import statistics
import sys

import article1_check as a1

PART_BYTES = 1_900_000


def build(client):
    """The same traversal as article1_check.main(): MDPI journals in sorted order, then Frontiers."""
    units = []
    for code, off in sorted(a1.MDPI.items()):
        for y in a1.YEARS:
            u = a1.mdpi_unit(client, code, y - off)
            if u:
                units.append(u)
        sys.stderr.write("MDPI %s done, %d Crossref calls\n" % (code, client.calls))
    for code in a1.FRONTIERS:
        for y in a1.YEARS:
            u = a1.frontiers_unit(client, code, y)
            if u:
                units.append(u)
        sys.stderr.write("Frontiers %s done, %d Crossref calls\n" % (code, client.calls))
    return units


def compare(units, v1_table):
    """Agreement with v1's published per-unit table. Copies v1's article-1 OpenAlex count into each matched unit."""
    v1 = {r["article1_doi"]: r for r in v1_table}
    now = {u["article1"]["doi"]: u for u in units}
    both = sorted(set(v1) & set(now))
    diffs, same_top, same_far = [], 0, 0
    for d in both:
        u, r = now[d], v1[d]
        u["article1"]["openalex_cites"] = r.get("article1_openalex")
        diffs.append(u["article1"]["cites"] - r["article1_cites"])
        same_top += a1.is_top(u) == bool(r.get("top"))
        same_far += len(u["far"]) == r.get("n_far")
    return {"v1_units": len(v1), "rebuilt_units": len(now), "matched": len(both),
            "only_v1": sorted(set(v1) - set(now)), "only_rebuilt": sorted(set(now) - set(v1)),
            "article1_cites_change": {"median": statistics.median(diffs) if diffs else None,
                                      "min": min(diffs) if diffs else None, "max": max(diffs) if diffs else None},
            "same_top": same_top, "same_n_far": same_far}


def write_parts(units, out_dir, prefix="units_rebuilt_part", limit=PART_BYTES):
    """Whole units, in order, into files of at most limit bytes each. Returns the file names."""
    parts, buf, size = [], [], 0
    for u in units:
        line = (json.dumps(u, ensure_ascii=False) + "\n").encode("utf-8")
        if buf and size + len(line) > limit:
            parts.append(buf)
            buf, size = [], 0
        buf.append(line)
        size += len(line)
    if buf:
        parts.append(buf)
    names = []
    for i, p in enumerate(parts, 1):
        name = "%s%d.jsonl" % (prefix, i)
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(b"".join(p))
        names.append(name)
    return names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--v1-results", default="article1_check_v1_results.json")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    client = a1.Client()
    units = build(client)
    with open(a.v1_results, encoding="utf-8") as f:
        check = compare(units, json.load(f)["table"])
    check["crossref_calls"] = client.calls
    with open(os.path.join(a.out_dir, "units_rebuilt.jsonl"), "w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    check["parts"] = write_parts(units, a.out_dir)
    with open(os.path.join(a.out_dir, "rebuild_check.json"), "w", encoding="utf-8") as f:
        json.dump(check, f, indent=1, ensure_ascii=False)
    print(json.dumps(check, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
