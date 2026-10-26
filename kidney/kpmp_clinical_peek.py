#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_clinical_peek: what does KPMP's open clinical file hold, and for how many of the
participants with segmentation packages or TIV scores?

Blind step before the Kidney AI question-2 pre-registration (findings/kpmp-q2-plan-v1-2026-10-26.md).
It reads only the open clinical file(s) named in the KPMP Atlas Repository's own file-list export
(Data Type "Clinical Study Data"), plus the participant IDs listed in the segmentation and TIV file
lists. It never opens a feature workbook or a TIV score, so the question-2 predictions are fixed
before any feature or score is joined to a clinical value.
Only column names, per-column marginal counts and participant overlap counts go to the output;
no row of the clinical file does. No KPMP file is re-hosted.

Standard library only (reuses kidney.kpmp_census). Usage:
  python -m kidney.kpmp_clinical_peek --file-list inputs/kpmp-clinical-files.csv \
      --seg-list inputs/kpmp-segmentation-files.csv --tiv-list inputs/kpmp-descriptor-files.csv \
      --out-dir /out --data-dir /data
"""
import argparse
import csv
import io
import json
import os
import statistics
import sys
import time
import zipfile
from collections import Counter

from kidney import kpmp_census as kc

PLAN = "findings/kpmp-q2-plan-v1-2026-10-26.md"
CODE_VERSION = "1.0"
TABLE_EXT = ("csv", "tsv", "txt", "xlsx")
FILE_EXT = TABLE_EXT + ("zip",)
MAX_FILES = 5
MAX_LISTED_BYTES = 500_000_000
MAX_MEMBER_BYTES = 50_000_000
MAX_LEVELS = 40
NUMERIC_SHARE = 0.9


def load_file_list(path):
    """Open rows of a Repository CSV export: package, name, listed size, format."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Access") or "").strip().lower() != "open":
                continue
            out.append({"package": (row.get("Internal Package ID") or "").strip(),
                        "name": (row.get("File Name") or "").strip(),
                        "listed": (row.get("Size") or "").strip(),
                        "format": (row.get("Data Format") or "").strip(),
                        "category": (row.get("Data Category") or "").strip(),
                        "strategy": (row.get("Experimental Strategy") or "").strip()})
    return out


def participant_set(path):
    """Every participant ID listed in a Repository CSV export (comma-separated per row)."""
    ids = set()
    if not path or not os.path.exists(path):
        return ids
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ids.update(p.strip() for p in (row.get("Participant ID") or "").split(",") if p.strip())
    return ids


def check_list(files):
    """None if the list looks like the clinical files only, else the reason it does not."""
    if not files:
        return "no open rows in the file list"
    if len(files) > MAX_FILES:
        return f"{len(files)} open rows; expected at most {MAX_FILES} clinical files"
    total = 0
    for p in files:
        try:
            total += kc.parse_size(p["listed"])
        except (ValueError, KeyError):
            return f"unreadable size {p['listed']!r} for {p['name']!r}"
        if kc.ext_of(p["name"]) not in FILE_EXT:
            return f"unexpected file type {p['name']!r}"
    if total > MAX_LISTED_BYTES:
        return f"listed total {total} bytes is over {MAX_LISTED_BYTES}"
    return None


# ---- tables ----

def read_delimited(data):
    """(header, rows) from csv/tsv bytes; tab-delimited if the first line has more tabs than commas."""
    text = data.decode("utf-8-sig", errors="replace")
    first = text.split("\n", 1)[0]
    delim = "\t" if first.count("\t") > first.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(x.strip() for x in r)]
    if not rows:
        return [], []
    header = [h.strip() or f"col{j + 1}" for j, h in enumerate(rows[0])]
    return header, rows[1:]


def tables_of(name, data):
    """[(table label, header, rows)] for one clinical file or zip member."""
    ext = kc.ext_of(name)
    if ext in ("csv", "tsv", "txt"):
        header, rows = read_delimited(data)
        return [(os.path.basename(name), header, rows)]
    if ext == "xlsx":
        out = []
        for sheet, rows in kc.read_xlsx(io.BytesIO(data)).items():
            header, body = kc.sheet_table(rows)
            out.append((f"{os.path.basename(name)}#{sheet}", header, body))
        return out
    return []


def file_tables(path, name):
    """Tables in a downloaded clinical file, and the zip members seen (name, bytes, read)."""
    with open(path, "rb") as f:
        data = f.read()
    if kc.ext_of(name) != "zip":
        return tables_of(name, data), []
    tables, members = [], []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            use = kc.ext_of(i.filename) in TABLE_EXT and i.file_size <= MAX_MEMBER_BYTES
            members.append({"name": i.filename, "bytes": i.file_size, "read": use})
            if use:
                tables.extend(tables_of(i.filename, z.read(i)))
    return tables, members


def id_column(header):
    """Index of the participant ID column, or None."""
    for j, h in enumerate(header):
        n = kc.norm(h).replace("_", " ")
        if "participant" in n and "id" in n.split():
            return j
    for j, h in enumerate(header):
        if kc.norm(h).replace("_", " ") in ("participant", "subject id", "record id", "id"):
            return j
    return None


def column_summary(values):
    """Marginal summary of one column's values (strings; '' and None count as empty)."""
    filled = [str(v).strip() for v in values if v is not None and str(v).strip() != ""]
    out = {"filled": len(filled), "empty": len(values) - len(filled), "distinct": len(set(filled))}
    nums = [x for x in (kc.parse_float(v) for v in filled) if x is not None]
    if out["distinct"] <= MAX_LEVELS:
        out["levels"] = [{"value": v, "n": n} for v, n in sorted(Counter(filled).items())]
    elif filled and len(nums) >= NUMERIC_SHARE * len(filled):
        out["numeric"] = {"n": len(nums), "min": min(nums), "median": statistics.median(nums), "max": max(nums)}
    return out


def summarise(label, header, rows, seg_ids, tiv_ids):
    """Header, marginals and participant overlap for one table. Marginals are also given for the
    rows of participants with segmentation packages, since those are the ones question 2 can use."""
    width = len(header)
    cols = [[(r[j] if j < len(r) else None) for r in rows] for j in range(width)]
    out = {"table": label, "rows": len(rows), "header": header, "id_column": None, "columns": []}
    j_id = id_column(header)
    seg_rows = list(range(len(rows)))
    if j_id is not None:
        ids = [str(x).strip() for x in cols[j_id] if x is not None and str(x).strip()]
        distinct = set(ids)
        seg_rows = [i for i, x in enumerate(cols[j_id]) if x is not None and str(x).strip() in seg_ids]
        out["id_column"] = header[j_id]
        out["participants"] = {"distinct": len(distinct), "rows_with_id": len(ids),
                               "repeated_ids": sum(1 for n in Counter(ids).values() if n > 1),
                               "with_segmentation": len(distinct & seg_ids), "with_tiv": len(distinct & tiv_ids),
                               "with_both": len(distinct & seg_ids & tiv_ids),
                               "segmentation_not_in_table": len(seg_ids - distinct),
                               "tiv_not_in_table": len(tiv_ids - distinct)}
    for j, h in enumerate(header):
        if j == j_id:
            continue
        c = {"name": h, "all": column_summary(cols[j])}
        if j_id is not None:
            c["segmented"] = column_summary([cols[j][i] for i in seg_rows])
        out["columns"].append(c)
    return out


def main(argv=None, get=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--seg-list", default="")
    ap.add_argument("--tiv-list", default="")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    args = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-clinical")
    files = load_file_list(args.file_list)
    seg_ids, tiv_ids = participant_set(args.seg_list), participant_set(args.tiv_list)
    res = {"plan": PLAN, "code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "file_list": [{k: p[k] for k in ("name", "listed", "format", "category", "strategy")} for p in files],
           "segmentation_participants": len(seg_ids), "tiv_participants": len(tiv_ids),
           "seg_and_tiv_participants": len(seg_ids & tiv_ids), "files": []}
    res["list_problem"] = check_list(files)
    if res["list_problem"] is None:
        for p in files:
            pdir = os.path.join(cache, p["package"])
            os.makedirs(pdir, exist_ok=True)
            path = os.path.join(pdir, os.path.basename(p["name"]))
            rec = {"name": p["name"], "listed": p["listed"]}
            if os.path.exists(path):
                rec["download"] = {"ok": True, "cached": True, "bytes": os.path.getsize(path)}
            else:
                rec["download"] = kc.download(kc.download_url(p["package"], p["name"]), path, get=get)
            if rec["download"]["ok"]:
                rec["size_ok"] = kc.size_ok(rec["download"]["bytes"], p["listed"])
                try:
                    tables, rec["members"] = file_tables(path, p["name"])
                    rec["tables"] = [summarise(*t, seg_ids, tiv_ids) for t in tables]
                except Exception as e:
                    rec["error"] = repr(e)[:300]
            res["files"].append(rec)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"list_problem": res["list_problem"], "files": len(res["files"]),
                      "tables": sum(len(r.get("tables", [])) for r in res["files"]),
                      "segmentation_participants": len(seg_ids), "minutes": res["minutes"]}))
    return 0 if res["list_problem"] is None and res["files"] and all(r["download"]["ok"] for r in res["files"]) else 1


if __name__ == "__main__":
    sys.exit(main())
