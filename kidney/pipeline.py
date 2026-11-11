#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""pipeline: one command from a folder of .svs whole-slide images to glomerulus tables, for MV2's open kidney work
on KPMP data (NIDDK Kidney AI Discovery Challenge, which asks for code that runs end to end on a directory of SVS
images and writes to an output directory).

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical
device, not for diagnosis or patient care.

What it does, per slide, in file-name order:
  1. slide quality checks with kidney/wsi_qc.py (pyramid, scanner MPP, tissue fraction, tissue pieces, ink, focus);
  2. glomerulus detection and labelling with kidney/gsdet.py `detect` and a 3-class checkpoint written by
     `gsdet train` (background / non-globally-sclerotic / globally sclerotic glomerulus). A glomerulus is an
     8-connected region where P(background) < 0.5 of at least 2,000 um^2; it is globally sclerotic when its summed
     P(GS) exceeds its summed P(NS). Positions and areas are in micrometres of the slide.
Measured limits of the recipe (pre-registered, graded on open KPMP biopsies): findings/kidney-glom-stage5-*.md and,
once graded, findings/kidney-glom-stage6-*.md in this repository. The fine-tuned weights are not published here
(KPMP data terms are being checked), so the checkpoint is passed in with --model.

Outputs in --out-dir:
  glomeruli.csv   one row per detected glomerulus: slide, number, class, centre, box, area (um, um^2)
  slides.csv      one row per slide: QC fields, counts by class, sclerotic share, median area, errors
  inputs.csv      every input file with its size in bytes and SHA-256 (the list of images used)
  qc.json         wsi_qc's full records;  detections.json  gsdet's detection document
  manifest.json   code versions, model file name, SHA-256 and training steps, settings, totals, timings
Exit code: 0 when every slide was detected, 1 when at least one failed (its row says why), 2 when the folder holds
no .svs file. Usage:
  python -m kidney.pipeline --in-dir /input --out-dir /output --model /models/gs.pth [--threads 4] [--no-qc]
"""
import argparse
import csv
import hashlib
import json
import os
import time

CODE_VERSION = "0.1.0"
SUFFIX = ".svs"
CLASS_NAMES = {"gs": "globally_sclerotic", "ns": "non_globally_sclerotic"}
OBJECT_FIELDS = ["slide", "glomerulus", "class", "cx_um", "cy_um", "x0_um", "y0_um", "x1_um", "y1_um", "area_um2"]
SLIDE_FIELDS = ["slide", "qc_ok", "detect_ok", "scan_mpp", "tissue_fraction", "pieces", "green_ink_fraction",
                "blur_median", "glomeruli", "globally_sclerotic", "non_globally_sclerotic", "gs_share",
                "median_area_um2", "seconds", "errors"]
INPUT_FIELDS = ["file", "bytes", "sha256"]
DISCLAIMER = ("Research output made with AI agents (Claude) working in MV2's name (Munim, Inc.). Not a medical "
              "device; not for diagnosis or patient care.")


# ---- standard-library parts ----

def list_slides(in_dir, suffix=SUFFIX):
    """File names in in_dir ending in suffix (any case), sorted: the same files gsdet.run_detect reads."""
    return sorted(f for f in os.listdir(in_dir) if f.lower().endswith(suffix) and
                  os.path.isfile(os.path.join(in_dir, f)))


def median(values):
    """Median of a list of numbers (mean of the middle two for an even count); None when empty."""
    v = sorted(values)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def object_rows(det_rows):
    """One dict per detected glomerulus of every slide whose detection succeeded, numbered from 1 per slide."""
    out = []
    for r in det_rows:
        if not r.get("ok"):
            continue
        for i, (obj, cls) in enumerate(zip(r.get("objects") or [], r.get("classes") or []), 1):
            cx, cy, x0, y0, x1, y1, area = obj
            out.append({"slide": r["slide"], "glomerulus": i, "class": CLASS_NAMES.get(cls, cls), "cx_um": cx,
                        "cy_um": cy, "x0_um": x0, "y0_um": y0, "x1_um": x1, "y1_um": y1, "area_um2": area})
    return out


def slide_rows(names, qc_rows, det_rows, qc_ran=True):
    """One dict per slide name (in the order given), joining its QC record and its detection record by name.
    Counts are None when detection failed or did not run; gs_share is None when no glomerulus was found. A slide
    with no QC record gets the error 'qc: not run' only when the QC stage ran (qc_ran)."""
    qc = {r["slide"]: r for r in qc_rows}
    det = {r["slide"]: r for r in det_rows}
    out = []
    for name in names:
        q = qc.get(name)
        d = det.get(name)
        ok = bool(d and d.get("ok"))
        classes = list(d.get("classes") or []) if ok else []
        areas = [o[6] for o in d.get("objects") or []] if ok else []
        n, g = len(classes), classes.count("gs")
        errs = ["qc: %s" % e for e in (q or {}).get("errors", [])]
        errs += ["detect: %s" % e for e in (d or {}).get("errors", [])]
        if q is None and qc_ran:
            errs.append("qc: not run")
        if d is None:
            errs.append("detect: not run")
        m = median(areas)
        q = q or {}
        out.append({"slide": name, "qc_ok": bool(q.get("ok")), "detect_ok": ok, "scan_mpp": q.get("mpp"),
                    "tissue_fraction": q.get("tissue_fraction"), "pieces": q.get("pieces"),
                    "green_ink_fraction": q.get("green_ink_fraction"), "blur_median": q.get("blur_median"),
                    "glomeruli": n if ok else None, "globally_sclerotic": g if ok else None,
                    "non_globally_sclerotic": n - g if ok else None,
                    "gs_share": round(g / float(n), 4) if ok and n else None,
                    "median_area_um2": round(m, 1) if m is not None else None,
                    "seconds": round(float(q.get("seconds") or 0) + float((d or {}).get("seconds") or 0), 1),
                    "errors": "; ".join(errs)})
    return out


def totals(rows):
    """Folder totals over slide rows; the pooled sclerotic share is over slides whose detection succeeded."""
    det = [r for r in rows if r["detect_ok"]]
    n = sum(r["glomeruli"] for r in det)
    g = sum(r["globally_sclerotic"] for r in det)
    return {"slides": len(rows), "qc_ok": sum(1 for r in rows if r["qc_ok"]), "detect_ok": len(det),
            "glomeruli": n, "globally_sclerotic": g, "non_globally_sclerotic": n - g,
            "gs_share": round(g / float(n), 4) if n else None}


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow(r)


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---- the run (numpy, OpenCV, tifffile and torch are imported by the stages) ----

def run(in_dir, out_dir, model_path, qc=True, tta=True, hash_inputs=True, threads=0):
    """Run every stage over in_dir, write every output, and return (exit code, manifest)."""
    t0, started = time.time(), utc_now()
    os.makedirs(out_dir, exist_ok=True)
    files = list_slides(in_dir)
    names = [os.path.splitext(f)[0] for f in files]
    inputs = [{"file": f, "bytes": os.path.getsize(os.path.join(in_dir, f)),
               "sha256": sha256_file(os.path.join(in_dir, f)) if hash_inputs else ""} for f in files]
    write_csv(os.path.join(out_dir, "inputs.csv"), INPUT_FIELDS, inputs)
    manifest = {"pipeline": CODE_VERSION, "started_at": started, "in_dir": os.path.abspath(in_dir),
                "slides": len(files), "notice": DISCLAIMER}
    if not files:
        manifest.update(error="no %s file in the input folder" % SUFFIX, finished_at=utc_now())
        write_json(os.path.join(out_dir, "manifest.json"), manifest)
        return 2, manifest
    qc_rows, qc_version = [], None
    if qc:
        from kidney import wsi_qc
        qc_version = wsi_qc.CODE_VERSION
        for k, f in enumerate(files):
            rec = wsi_qc.qc_slide(os.path.join(in_dir, f))
            qc_rows.append(rec)
            print("qc %d/%d ok=%s %.1fs" % (k + 1, len(files), rec["ok"], rec.get("seconds", 0)), flush=True)
        write_json(os.path.join(out_dir, "qc.json"), {"code_version": qc_version, "rows": qc_rows})
    if threads:
        import torch
        torch.set_num_threads(threads)
    from kidney import glom, gsdet
    det = gsdet.run_detect(in_dir, model_path, tta=tta)
    write_json(os.path.join(out_dir, "detections.json"), det)
    rows = slide_rows(names, qc_rows, det["rows"], qc_ran=qc)
    objs = object_rows(det["rows"])
    write_csv(os.path.join(out_dir, "glomeruli.csv"), OBJECT_FIELDS, objs)
    write_csv(os.path.join(out_dir, "slides.csv"), SLIDE_FIELDS, rows)
    tot = totals(rows)
    manifest.update({
        "code_versions": {"pipeline": CODE_VERSION, "wsi_qc": qc_version, "gsdet": gsdet.CODE_VERSION,
                          "glom": glom.CODE_VERSION},
        "model": {"file": os.path.basename(model_path), "sha256": sha256_file(model_path),
                  "train_steps": det.get("train_steps")},
        "settings": {"qc": qc, "tta": tta, "target_mpp": glom.TARGET_MPP, "tile": glom.TILE,
                     "fg_max_bg": gsdet.FG_MAX_BG, "min_area_um2": glom.MIN_AREA_UM2, "threads": threads},
        "totals": tot, "finished_at": utc_now(), "minutes": round((time.time() - t0) / 60.0, 2)})
    write_json(os.path.join(out_dir, "manifest.json"), manifest)
    return (0 if tot["detect_ok"] == len(files) else 1), manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Folder of .svs slides -> slide QC + glomerulus tables (research only).")
    ap.add_argument("--in-dir", required=True, help="folder of .svs whole-slide images")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", required=True, help="3-class checkpoint written by `python -m kidney.gsdet train`")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = torch's default)")
    ap.add_argument("--no-qc", action="store_true", help="skip the slide quality checks")
    ap.add_argument("--no-tta", action="store_true", help="no flip test-time augmentation (faster, not as graded)")
    ap.add_argument("--no-hash", action="store_true", help="do not compute SHA-256 of the input slides")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.in_dir):
        print(json.dumps({"error": "input folder not found"}))
        return 2
    if not os.path.isfile(a.model):
        print(json.dumps({"error": "model file not found"}))
        return 2
    code, manifest = run(a.in_dir, a.out_dir, a.model, qc=not a.no_qc, tta=not a.no_tta, hash_inputs=not a.no_hash,
                         threads=a.threads)
    print(json.dumps({"pipeline": CODE_VERSION, "slides": manifest["slides"], "totals": manifest.get("totals"),
                      "minutes": manifest.get("minutes"), "exit": code}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
