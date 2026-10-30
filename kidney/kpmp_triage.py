#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_triage: blinded patches of zero-TBM and size-matched measured tubules, for AI visual triage.

Pre-registration: findings/kpmp-triage-prereg-v1-2026-10-30.md.

The zero-TBM study (kidney.kpmp_zs 1.0) found that the share of a participant's tubule rows with no
"Average TBM Thickness" tracks atrophy and eGFR, mostly through the share of small tubules. Only
looking at the rows can say what they are. This job
  render: picks open v2 segmentation packages in a seeded order (one per participant), downloads
          each, reads its tubs sheet, draws PER_PACKAGE zero-TBM tubules at random and pairs each
          with the measured tubule of the nearest box area on the same slide, and writes a crop of
          every tubule (box outlined) under a shuffled ID, plus DUPLICATES repeated crops under new
          IDs to measure the reader's consistency;
  grade:  scores a reader's fixed categories against the pairing with exact sign tests.
The images and the key (package IDs and boxes) are KPMP data for private review and are never
published; pairs.csv (IDs, block, pair, group) and manifest.json hold no image data or package ID.

numpy, tifffile, imagecodecs and Pillow are needed only by render. Usage:
  python -m kidney.kpmp_triage render --file-list inputs/kpmp-segmentation-files.csv --out-dir /out
  python -m kidney.kpmp_triage grade --readings readings.csv --pairs pairs.csv --out-dir /out
"""
import argparse
import csv
import json
import math
import os
import random
import re
import shutil
import statistics
import tempfile
import time
import zipfile
from collections import Counter

from kidney import kpmp_patches as kp

PREREG = "findings/kpmp-triage-prereg-v1-2026-10-30.md"
CODE_VERSION = "1.0"
SEED = 20261030
STRATEGY = "Segmentation Masks & Pathomics Vectors"
N_PACKAGES = 12
PER_PACKAGE = 4
MIN_ZERO = 8
MIN_MEASURED = 40
DUPLICATES = 8
MAX_LISTED_BYTES = 1.5e9
SIDE = 512
FACTOR = 1.0
# KPMP's x1|x2 run along image rows: seen by eye in kpmp-patches-v1, where no workbook was read.
DEFAULT_ORIENT = "yx"
TBM = "average tbm thickness"
BOX = ("x1", "x2", "y1", "y2")
UNITS = {"B": 1, "kB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}
CATEGORIES = {"A": "atrophic", "B": "collapsed", "C": "tangential or partial",
              "D": "not a tubule or artefact", "E": "normal-looking", "F": "unreadable"}
ABNORMAL = "ABCD"
ALPHA = 0.05
HYPOTHESES = 3
MIN_PAIRS = 40
MIN_BLOCKS = 10
MAX_UNREADABLE = 0.10
AGREE_BAR = 0.75
MIN_AGREE_N = 6
# (key, categories counted, fewest discordant pairs for a grade)
TESTS = (("V1_abnormal", ABNORMAL, 8), ("V2_atrophic", "A", 5), ("V3_artefact", "D", 5))


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---- packages and workbooks ----

def parse_size(text):
    m = re.match(r"\s*([\d.]+)\s*([kMGT]?B)\s*$", text or "")
    return float(m.group(1)) * UNITS[m.group(2)] if m else 0.0


def load_v2_packages(path):
    """Open v2 segmentation packages from the Repository's CSV export, in file order."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Experimental Strategy") or "").strip() != STRATEGY:
                continue
            if (row.get("Access") or "").strip().lower() != "open":
                continue
            name = (row.get("File Name") or "").strip()
            if not name.lower().endswith("_v2.zip"):
                continue
            pids = [p.strip() for p in (row.get("Participant ID") or "").split(",") if p.strip()]
            out.append({"package": (row.get("Internal Package ID") or "").strip(), "name": name,
                        "listed": (row.get("Size") or "").strip(), "participants": pids})
    return out


def key(name):
    return " ".join(str(name if name is not None else "").lower().split())


def table(rows):
    """(header keys, data rows): the header is the fullest of the first 10 non-empty rows."""
    filled = [r for r in rows if any(x not in (None, "") for x in r)]
    if not filled:
        return [], []
    counts = [sum(1 for x in r if x not in (None, "")) for r in filled[:10]]
    h = counts.index(max(counts))
    return [key(x) for x in filled[h]], filled[h + 1:]


def tubule_rows(book):
    """[(tbm, box)] for every row of the workbook's tubs sheet with a TBM value and a full box."""
    rows = next((r for name, r in book.items() if key(name) == "tubs"), [])
    header, data = table(rows)
    idx = {h: j for j, h in enumerate(header) if h}
    if TBM not in idx or not all(b in idx for b in BOX):
        return []
    out = []
    for r in data:
        vals = [kp._num(r[idx[c]]) if idx[c] < len(r) else None for c in (TBM,) + BOX]
        if None in vals:
            continue
        out.append((vals[0], tuple(vals[1:])))
    return out


def workbook_rows(zpath, tmp_dir):
    """tubule_rows of the zip's one .xlsx member; None unless there is exactly one."""
    with zipfile.ZipFile(zpath) as z:
        books = [i for i in z.infolist() if i.filename.lower().endswith(".xlsx")]
        if len(books) != 1:
            return None
        path = os.path.join(tmp_dir, "book.xlsx")
        with z.open(books[0]) as src, open(path, "wb") as dst:
            shutil.copyfileobj(src, dst, kp.CHUNK)
    try:
        return tubule_rows(kp.read_xlsx(path))
    finally:
        os.remove(path)


# ---- pairing ----

def area(box):
    x1, x2, y1, y2 = box
    return (x2 - x1) * (y2 - y1)


def pick_pairs(rows, rng, n=PER_PACKAGE, min_zero=MIN_ZERO, min_measured=MIN_MEASURED):
    """n zero-TBM rows drawn at random, each paired with the unused measured row of the nearest box
    area (on the log scale; ties to the smaller box). None if the slide has too few of either."""
    zero = sorted((r for r in rows if r[0] <= 0 and area(r[1]) > 0), key=lambda r: r[1])
    measured = sorted((r for r in rows if r[0] > 0 and area(r[1]) > 0), key=lambda r: r[1])
    if len(zero) < max(min_zero, n) or len(measured) < max(min_measured, n):
        return None
    used, pairs = set(), []
    for z in rng.sample(zero, n):
        a = area(z[1])
        m = min((m for m in measured if m[1] not in used), key=lambda m: (abs(math.log(area(m[1]) / a)), m[1]))
        used.add(m[1])
        pairs.append({"zero": z, "measured": m, "area_ratio": area(m[1]) / a})
    return pairs


# ---- pixels ----

def render_crop(levels, rect, path, side=SIDE):
    """Crop around rect (level-0 pixels) with rect outlined, no longer than side; returns facts."""
    w0, h0 = levels[0][1], levels[0][2]
    win = kp.crop_window(rect, w0, h0, factor=FACTOR)
    li, ds = kp.pick_level([(w, h) for _, w, h in levels], win)
    page = levels[li][0]
    l, t = int(win[0] / ds), int(win[1] / ds)
    w = max(1, min(page.imagewidth - l, int(math.ceil((win[2] - win[0]) / ds))))
    h = max(1, min(page.imagelength - t, int(math.ceil((win[3] - win[1]) / ds))))
    arr = kp.read_region(page, l, t, w, h)
    box = ((rect[0] - win[0]) / ds, (rect[1] - win[1]) / ds, (rect[2] - win[0]) / ds, (rect[3] - win[1]) / ds)
    return {"window": list(win), "level": li, "written": kp.save_image(arr, path, [box], side=side)}


def render(file_list, out_dir, get=None, pause=None, n_packages=N_PACKAGES, per_package=PER_PACKAGE,
           min_zero=MIN_ZERO, min_measured=MIN_MEASURED, duplicates=DUPLICATES, budget_minutes=150,
           seed=SEED):
    import tifffile
    t0 = time.time()
    rng = random.Random(seed)
    pkgs = sorted(load_v2_packages(file_list), key=lambda p: (p["package"], p["name"]))
    rng.shuffle(pkgs)
    patch_dir, key_dir = os.path.join(out_dir, "patches"), os.path.join(out_dir, "key")
    os.makedirs(patch_dir, exist_ok=True)
    os.makedirs(key_dir, exist_ok=True)
    skipped, orients, seen, crops, errors = Counter(), Counter(), set(), [], []
    tried = blocks = 0
    with tempfile.TemporaryDirectory() as tmp:
        stage = os.path.join(tmp, "stage")
        os.makedirs(stage)
        for p in pkgs:
            if blocks >= n_packages:
                break
            if time.time() - t0 > budget_minutes * 60:
                skipped["budget"] += 1
                break
            if len(p["participants"]) != 1 or p["participants"][0] in seen:
                skipped["participant"] += 1
                continue
            if parse_size(p["listed"]) > MAX_LISTED_BYTES:
                skipped["too_large"] += 1
                continue
            tried += 1
            zpath, spath = os.path.join(tmp, "package.zip"), os.path.join(tmp, "slide.svs")
            try:
                d = kp.download(kp.download_url(p["package"], p["name"]), zpath, get=get, pause=pause)
                if not d["ok"]:
                    skipped["download"] += 1
                    continue
                rows = workbook_rows(zpath, tmp)
                if not rows:
                    skipped["workbook"] += 1
                    continue
                pairs = pick_pairs(rows, rng, per_package, min_zero, min_measured)
                if pairs is None:
                    skipped["too_few_tubules"] += 1
                    continue
                if not kp.extract_svs(zpath, spath):
                    skipped["no_svs"] += 1
                    continue
                os.remove(zpath)
                with tifffile.TiffFile(spath) as tif:
                    levels = kp.slide_levels(tif)
                    o = kp.orientation([r[1] for r in rows], levels[0][1], levels[0][2])
                    way = o["orientation"] or DEFAULT_ORIENT
                    orients[o["orientation"] or "undecided"] += 1
                    blocks += 1
                    seen.add(p["participants"][0])
                    for k, pr in enumerate(pairs, 1):
                        for group in ("zero", "measured"):
                            tbm, box = pr[group]
                            c = {"stage": "s%04d.jpg" % len(crops), "block": blocks, "pair": "%02d-%d" % (blocks, k),
                                 "group": group, "package": p["package"], "box": list(box), "tbm": tbm,
                                 "area": area(box), "area_ratio": round(pr["area_ratio"], 4), "orientation": way}
                            try:
                                c.update(render_crop(levels, kp.to_rect(box, way), os.path.join(stage, c["stage"])))
                            except Exception as e:
                                c["error"] = repr(e)[:300]
                            crops.append(c)
                log("block %d: %s rows=%d orientation=%s" % (blocks, p["package"][:8], len(rows), way))
            except Exception as e:
                skipped["error"] += 1
                errors.append(repr(e)[:300])
            finally:
                for q in (zpath, spath, zpath + ".part"):
                    if os.path.exists(q):
                        os.remove(q)
        bad = {c["pair"] for c in crops if "error" in c}
        originals = [c for c in crops if c["pair"] not in bad]
        rng2 = random.Random(seed + 1)
        entries = [{"src": c, "dup": False} for c in originals]
        entries += [{"src": c, "dup": True} for c in rng2.sample(originals, min(duplicates, len(originals)))]
        rng2.shuffle(entries)
        for i, e in enumerate(entries, 1):
            e["id"] = "c%03d" % i
        orig_id = {id(e["src"]): e["id"] for e in entries if not e["dup"]}
        key_rows = []
        for e in entries:
            c = e["src"]
            shutil.copyfile(os.path.join(stage, c["stage"]), os.path.join(patch_dir, e["id"] + ".jpg"))
            key_rows.append(dict({k: v for k, v in c.items() if k != "stage"}, id=e["id"],
                                 duplicate_of=orig_id[id(c)] if e["dup"] else ""))
    key_rows.sort(key=lambda r: r["id"])
    with open(os.path.join(key_dir, "key.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "Private: KPMP package IDs and boxes. Never publish.", "crops": key_rows}, f, indent=1)
    with open(os.path.join(key_dir, "pairs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "block", "pair", "group", "duplicate_of"])
        for r in key_rows:
            w.writerow([r["id"], r["block"], r["pair"], r["group"], r["duplicate_of"]])
    ratios = [c["area_ratio"] for c in originals if c["group"] == "measured"]
    manifest = {"prereg": PREREG, "code_version": CODE_VERSION, "seed": seed,
                "note": "Aggregate facts only: no image data, package ID or box.",
                "v2_packages_listed": len(pkgs), "packages_tried": tried, "blocks": blocks,
                "skipped": dict(skipped), "errors": errors[:10], "orientations": dict(orients),
                "pairs": len(ratios), "crops": len(originals), "duplicates": len(entries) - len(originals),
                "pairs_dropped_for_crop_errors": len(bad),
                "area_ratio": {"median": statistics.median(ratios), "min": min(ratios), "max": max(ratios),
                               "within_10pct": sum(1 for r in ratios if 1 / 1.1 <= r <= 1.1)} if ratios else None,
                "ids": [r["id"] for r in key_rows], "minutes": round((time.time() - t0) / 60, 1)}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps({k: manifest[k] for k in ("blocks", "pairs", "crops", "duplicates", "skipped", "orientations")}))
    return manifest


# ---- grading ----

def load_readings(path):
    """{id: category} from a CSV with columns id, category (and anything else, ignored)."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            i, cat = (row.get("id") or "").strip(), (row.get("category") or "").strip().upper()
            if cat not in CATEGORIES:
                raise ValueError("bad category %r for %s" % (cat, i))
            if i in out:
                raise ValueError("%s is read twice" % i)
            out[i] = cat
    return out


def load_pairs(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def sign_p(b, n):
    """One-sided exact sign test: P(X >= b) for X ~ Binomial(n, 1/2); 1.0 when n is 0."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def paired_test(pairs, readings, cats, min_discordant):
    """Pairs where only the zero member is in cats against pairs where only the measured one is."""
    b = sum(1 for z, m in pairs if readings[z] in cats and readings[m] not in cats)
    c = sum(1 for z, m in pairs if readings[m] in cats and readings[z] not in cats)
    p = sign_p(b, b + c)
    grade = "untestable" if b + c < min_discordant else ("pass" if p < ALPHA else "fail")
    return {"categories": cats, "zero_only": b, "measured_only": c, "p": p,
            "bonferroni": p < ALPHA / HYPOTHESES, "grade": grade}


def grade(readings, pair_rows, min_pairs=MIN_PAIRS, min_blocks=MIN_BLOCKS):
    orig = [r for r in pair_rows if not r["duplicate_of"]]
    dups = [r for r in pair_rows if r["duplicate_of"]]
    missing = sorted(r["id"] for r in pair_rows if r["id"] not in readings)
    extra = sorted(set(readings) - {r["id"] for r in pair_rows})
    by_pair = {}
    for r in orig:
        by_pair.setdefault(r["pair"], {})[r["group"]] = r["id"]
    complete = [(v["zero"], v["measured"]) for _, v in sorted(by_pair.items()) if "zero" in v and "measured" in v]
    readable = [(z, m) for z, m in complete
                if z in readings and m in readings and readings[z] != "F" and readings[m] != "F"]
    n_read = sum(1 for r in orig if r["id"] in readings)
    unreadable = sum(1 for r in orig if readings.get(r["id"]) == "F")
    gate = {"pairs": len(complete), "readable_pairs": len(readable), "blocks": len({r["block"] for r in orig}),
            "missing": missing, "extra": extra, "unreadable_share": unreadable / n_read if n_read else None}
    gate["pass"] = (not missing and not extra and gate["pairs"] >= min_pairs and gate["blocks"] >= min_blocks
                    and gate["unreadable_share"] is not None and gate["unreadable_share"] <= MAX_UNREADABLE)
    res = {"prereg": PREREG, "code_version": CODE_VERSION, "gate": gate, "categories": CATEGORIES,
           "table": {g: dict(sorted(Counter(readings[r["id"]] for r in orig
                                            if r["group"] == g and r["id"] in readings).items()))
                     for g in ("zero", "measured")},
           "tests": {k: paired_test(readable, readings, cats, n) for k, cats, n in TESTS}}
    agree = [readings[r["id"]] == readings[r["duplicate_of"]] for r in dups
             if readings.get(r["id"], "F") != "F" and readings.get(r["duplicate_of"], "F") != "F"]
    v4 = {"agree": sum(agree), "n": len(agree), "share": sum(agree) / len(agree) if agree else None}
    v4["grade"] = "untestable" if len(agree) < MIN_AGREE_N else ("pass" if v4["share"] >= AGREE_BAR else "fail")
    res["tests"]["V4_consistency"] = v4
    res["grades"] = {k: (t["grade"] if gate["pass"] else "untestable") for k, t in res["tests"].items()}
    return res


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--file-list", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--budget-minutes", type=float, default=150)
    g = sub.add_parser("grade")
    g.add_argument("--readings", required=True)
    g.add_argument("--pairs", required=True)
    g.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    if args.cmd == "render":
        return render(args.file_list, args.out_dir, get=get, pause=pause, budget_minutes=args.budget_minutes)
    res = grade(load_readings(args.readings), load_pairs(args.pairs))
    with open(os.path.join(args.out_dir, "triage-results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"gate": res["gate"]["pass"], "grades": res["grades"]}))
    return res


if __name__ == "__main__":
    main()
