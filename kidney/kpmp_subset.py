#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_subset: copy the Repository's file-list CSV, keeping one package version only.

kpmp-twinrel-v1 landed on a machine whose kpmp-open-files volume was empty, and atlas.kpmp.org
answered range requests with HTTP 200, so kpmp_fill skipped every package and nothing was graded
(results note findings/kpmp-twinrel-results-v1-2026-10-28.md). The twin studies read v2 packages
only, so a v2-only list lets `kpmp_fill --allow-full` download just those zips (each deleted once
its small members are kept) instead of every package of both versions.

Rows are kept by kidney.kpmp_census.version_of on the File Name column. The header and the kept rows
are written with every field quoted, as the Repository exports them. Standard library only. Usage:
  python -m kidney.kpmp_subset --file-list inputs/kpmp-segmentation-files.csv --version v2 \
      --out /out/kpmp-segmentation-files-v2.csv
"""
import argparse
import csv
import json
import os
import sys

from kidney import kpmp_census as kc

CODE_VERSION = "1.0"


def subset(src, dst, version):
    """Write the rows of src whose File Name is of `version` to dst. Returns kept and dropped counts."""
    with open(src, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        head = next(r)
        col = head.index("File Name")
        kept, dropped = [], 0
        for row in r:
            if len(row) > col and kc.version_of(row[col].strip()) == version:
                kept.append(row)
            else:
                dropped += 1
    if os.path.dirname(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(head)
        w.writerows(kept)
    return {"kept": len(kept), "dropped": dropped}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--version", choices=("v1", "v2"), required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = subset(a.file_list, a.out, a.version)
    print(json.dumps(dict(res, code_version=CODE_VERSION, version=a.version)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
