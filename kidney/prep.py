#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""prep: input plumbing for the pre-registered D1 and D2 lanes of MV2's open entry for the NIDDK Kidney AI Discovery
Challenge (findings/kidney-d1-prereg-v1-2026-11-12.md, findings/kidney-d2-prereg-v1-2026-11-12.md). It changes no
pre-registered number; it only makes sure the graders see each slide once and under the right participant.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical device,
not for diagnosis or patient care. Standard library only.

Why it exists: D2's slide pass runs as several compute jobs (one batch of slides each), and every job names its
slides from its own download list. Two batches that both start at "slide01" would give two different biopsies the
same name, and the graders, which key everything on the slide name, would silently drop one or pair a detector row
with the wrong KPMP mask. prep numbers the slides once across all batches and refuses inputs where a name is reused.

Commands (all outputs are PRIVATE, local files under KPMP's data use terms; the command line prints totals only):
  plan          KPMP's open file list -> batch-NN.json download lists ({"slide", "package", "name"}) for every open
                version 2 package in the file list's order, slide names numbered once across all batches, plus
                groups.json ({slide: participant}).
  participants  download lists -> sorted [participant, ...] of their packages (train.json, dev.json).
  merge-det     several emb.py `run` (or gsdet.py `detect`) documents -> one, each slide once: its first successful
                row, else its first row. The documents must agree on every model setting in HEADER_KEYS.
  merge-k       several kmask.py k.json files -> one; the same slide with two different records is a conflict.
Usage:
  python -m kidney.prep plan --csv files.csv --batch-size 20 --out-dir plan/
  python -m kidney.prep participants --csv files.csv --lists stage5-train.json --out train.json
  python -m kidney.prep merge-det --det emb-01.json emb-02.json --out emb.json
  python -m kidney.prep merge-k --k k-01.json k-02.json --out k.json
Each command exits 1 when its input has a problem it reports (a reused name, a package with no participant, ...).
"""
import argparse
import csv
import json
import os

CODE_VERSION = "0.1.0"
V2_SUFFIX = "_Seg_Masks_Features_v2.zip"
PREFIX = "d2s"
HEADER_KEYS = ("code_version", "gsdet", "anom", "train_steps", "tta", "fg_max_bg", "window", "stage", "emb_dim",
               "base_names")


def v2_rows(rows, suffix=V2_SUFFIX):
    """Open rows whose file name ends in `suffix`, in the file list's order (rows are dicts with KPMP's column
    names)."""
    return [r for r in rows if str(r.get("Access", "")).strip().lower() == "open"
            and str(r.get("File Name", "")).endswith(suffix)]


def part_map(rows):
    """({package id: participant}, number of packages listed with two different participants). A package listed
    twice with the same participant is fine; with two participants it is dropped from the map."""
    out, bad = {}, set()
    for r in rows:
        p, g = r.get("Internal Package ID"), r.get("Participant ID")
        if not p or not g:
            continue
        if p in out and out[p] != g:
            bad.add(p)
        out.setdefault(p, g)
    for p in bad:
        del out[p]
    return out, len(bad)


def plan(rows, batch_size, prefix=PREFIX):
    """[[{"slide", "package", "name"}, ...], ...]: `rows` cut into consecutive batches of at most batch_size, slides
    named prefix + a number counted once over all batches (zero-padded to at least 3 digits). A package listed twice
    is kept once (first place)."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    seen, keep = set(), []
    for r in rows:
        p = r["Internal Package ID"]
        if p in seen:
            continue
        seen.add(p)
        keep.append(r)
    width = max(3, len(str(len(keep))))
    items = [{"slide": "%s%0*d" % (prefix, width, i + 1), "package": r["Internal Package ID"], "name": r["File Name"]}
             for i, r in enumerate(keep)]
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def groups(lists, pmap):
    """({slide: participant}, problems) over several download lists. problems counts "name_reused" (one slide name
    for two different packages), "package_twice" (one package under two slide names) and "no_participant" (a package
    missing from pmap). Slides with a problem are left out of the map."""
    by_name, by_pkg = {}, {}
    prob = {"name_reused": 0, "package_twice": 0, "no_participant": 0}
    bad_names = set()
    for lst in lists:
        for s in lst:
            n, p = s["slide"], s["package"]
            if n in by_name and by_name[n] != p:
                prob["name_reused"] += 1
                bad_names.add(n)
                continue
            if p in by_pkg and by_pkg[p] != n:
                prob["package_twice"] += 1
                bad_names.add(n)
                continue
            by_name[n] = p
            by_pkg[p] = n
    out = {}
    for n in sorted(by_name):
        if n in bad_names:
            continue
        g = pmap.get(by_name[n])
        if g is None:
            prob["no_participant"] += 1
            continue
        out[n] = g
    return out, prob


def participants(lists, pmap):
    """(sorted unique participants of the packages in the download lists, number of packages with no participant)."""
    found, missing = set(), 0
    for lst in lists:
        for s in lst:
            g = pmap.get(s["package"])
            if g is None:
                missing += 1
            else:
                found.add(g)
    return sorted(found), missing


def merge_det(docs, keys=HEADER_KEYS):
    """(one detector document, stats). Raises ValueError when the documents disagree on a key of `keys` (a key
    missing from a document counts as None). Rows: each slide once, in order of first appearance; its first row with
    "ok" true, else its first row. stats: documents, rows read, slides, slides ok."""
    if not docs:
        raise ValueError("no documents")
    for k in keys:
        vals = [json.dumps(d.get(k), sort_keys=True) for d in docs]
        if len(set(vals)) > 1:
            raise ValueError("documents disagree on %r" % (k,))
    order, pick = [], {}
    n_rows = 0
    for d in docs:
        for r in d.get("rows", []):
            n_rows += 1
            s = r.get("slide")
            if s not in pick:
                order.append(s)
                pick[s] = r
            elif r.get("ok") and not pick[s].get("ok"):
                pick[s] = r
    out = {k: v for k, v in docs[0].items() if k != "rows"}
    out["merged_documents"] = len(docs)
    out["merged_by"] = "kidney.prep %s" % CODE_VERSION
    out["rows"] = [pick[s] for s in order]
    st = {"documents": len(docs), "rows_read": n_rows, "slides": len(order),
          "slides_ok": sum(1 for s in order if pick[s].get("ok"))}
    return out, st


def merge_k(docs):
    """(one k.json document, conflicts): slides in order of first appearance; the same slide with an equal record
    again is fine, with a different record it is a conflict and its first record is kept."""
    out, conflicts = {}, 0
    for d in docs:
        for s, v in d.items():
            if s not in out:
                out[s] = v
            elif json.dumps(out[s], sort_keys=True) != json.dumps(v, sort_keys=True):
                conflicts += 1
    return out, conflicts


# ---- command line ----

def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Input plumbing for the D1/D2 kidney lanes (local outputs only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--csv", required=True)
    p.add_argument("--batch-size", type=int, required=True)
    p.add_argument("--prefix", default=PREFIX)
    p.add_argument("--out-dir", required=True)
    p = sub.add_parser("participants")
    p.add_argument("--csv", required=True)
    p.add_argument("--lists", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("merge-det")
    p.add_argument("--det", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("merge-k")
    p.add_argument("--k", nargs="+", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rep = {"code_version": CODE_VERSION, "cmd": a.cmd}
    ok = True
    if a.cmd == "plan":
        rows = _read_csv(a.csv)
        pmap, ambiguous = part_map(rows)
        batches = plan(v2_rows(rows), a.batch_size, a.prefix)
        gmap, prob = groups(batches, pmap)
        os.makedirs(a.out_dir, exist_ok=True)
        for i, b in enumerate(batches):
            _write(os.path.join(a.out_dir, "batch-%02d.json" % (i + 1)), b)
        _write(os.path.join(a.out_dir, "groups.json"), gmap)
        rep.update(batches=len(batches), slides=sum(len(b) for b in batches), with_participant=len(gmap),
                   ambiguous_packages=ambiguous, problems=prob)
        ok = bool(batches) and ambiguous == 0 and not any(prob.values())
    elif a.cmd == "participants":
        pmap, ambiguous = part_map(_read_csv(a.csv))
        parts, missing = participants([_load(x) for x in a.lists], pmap)
        _write(a.out, parts)
        rep.update(participants=len(parts), packages_without_participant=missing, ambiguous_packages=ambiguous)
        ok = bool(parts) and missing == 0
    elif a.cmd == "merge-det":
        doc, st = merge_det([_load(x) for x in a.det])
        _write(a.out, doc)
        rep.update(st)
        ok = st["slides"] > 0
    else:
        doc, conflicts = merge_k([_load(x) for x in a.k])
        _write(a.out, doc)
        rep.update(slides=len(doc), conflicts=conflicts)
        ok = bool(doc) and conflicts == 0
    print(json.dumps(rep))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
