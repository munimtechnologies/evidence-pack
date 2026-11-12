#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""annot: the glomeruli that kidney/pipeline.py found, as QuPath-importable GeoJSON, one file per slide, so a
pathologist can open a slide in QuPath, drag its .geojson file onto it and review every box the model drew.

The NIDDK Kidney AI Discovery Challenge asks submitted code to write "annotations marking the regions it flags" and
asks how experts would review the outputs; this is that output for MV2's open entry. It reads only the pipeline's
glomeruli.csv and slides.csv (no image, no model) and uses the standard library only.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical
device, not for diagnosis or patient care.

Geometry: the pipeline gives each glomerulus's bounding box in micrometres of the slide (kidney/glom.py
region_records: working-image pixels x the working image's um per pixel, which equals level-0 pixels x the
scanner's level-0 MPP along both axes). QuPath wants level-0 (full-resolution) pixels with the origin at the top
left, so each corner is um / scan_mpp (slides.csv, from kidney/wsi_qc.py's Aperio header), rounded to 0.1 pixel.
Each box becomes a closed 5-point Polygon ring. Properties follow QuPath 0.3+ GeoJSON: objectType ("annotation", or
"detection" with --detections, lighter when a slide has thousands of objects), name "glomerulus <n>", and
classification {"name": class, "color": [r, g, b]}.

A slide gets no file when slides.csv says its detection failed, when it has no scan_mpp (QC was skipped or the
header has no MPP), or when its safe file name clashes with an earlier slide's; a slide that is only in
glomeruli.csv gets none either. Each such slide is listed in the report with the reason. A detected slide with no
glomerulus gets an empty FeatureCollection. A row with a missing coordinate or an empty box is dropped and counted.

Outputs in --out-dir: <slide>.geojson per slide (characters other than A-Z a-z 0-9 . _ - become _) and
annot-report.json (version, files, features, dropped rows, skipped slides).
Exit code: 0 when every slide in slides.csv got a file and no row was dropped, 1 otherwise, 2 when an input is
missing. Usage:
  python -m kidney.annot --glomeruli out/glomeruli.csv --slides out/slides.csv --out-dir out/annotations
"""
import argparse
import csv
import json
import os
import re
import sys

CODE_VERSION = "0.1.0"
COLORS = {"globally_sclerotic": [214, 39, 40], "non_globally_sclerotic": [44, 160, 44]}
OTHER_COLOR = [127, 127, 127]
REPORT = "annot-report.json"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def to_float(v):
    """float of a CSV cell; None for None, '', text that is not a number, NaN and infinities."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def is_true(v):
    """True for the CSV spellings of a true flag ('True', 'true', '1', 'yes')."""
    return str(v).strip().lower() in ("true", "1", "yes")


def safe_name(slide):
    """File-name stem for a slide name: every character other than A-Z a-z 0-9 . _ - becomes _."""
    return _UNSAFE.sub("_", slide or "") or "_"


def box_ring(x0, y0, x1, y1):
    """Closed polygon ring of a box, clockwise on screen from the top-left corner."""
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


def feature(row, mpp, object_type="annotation"):
    """QuPath GeoJSON feature of one glomeruli.csv row on a slide of level-0 MPP `mpp`, or None when a box
    coordinate is missing or the box is empty."""
    vals = [to_float(row.get(k)) for k in ("x0_um", "y0_um", "x1_um", "y1_um")]
    if None in vals:
        return None
    x0, y0, x1, y1 = [round(v / mpp, 1) for v in vals]
    if x1 <= x0 or y1 <= y0:
        return None
    cls = row.get("class") or "unclassified"
    return {"type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [box_ring(x0, y0, x1, y1)]},
            "properties": {"objectType": object_type, "name": "glomerulus %s" % row.get("glomerulus", ""),
                           "classification": {"name": cls, "color": list(COLORS.get(cls, OTHER_COLOR))}}}


def build(glom_rows, slide_rows, object_type="annotation"):
    """(docs, report): docs maps '<safe slide name>.geojson' to a FeatureCollection, slides in sorted order;
    glomeruli keep their order in glomeruli.csv."""
    info = {}
    for r in slide_rows:
        info[r.get("slide") or ""] = r
    by_slide = {}
    for r in glom_rows:
        by_slide.setdefault(r.get("slide") or "", []).append(r)
    docs, skipped, owner = {}, [], {}
    features = dropped = 0
    for slide in sorted(set(info) | set(by_slide)):
        r = info.get(slide)
        if r is None:
            skipped.append({"slide": slide, "reason": "not in slides.csv"})
            continue
        if not is_true(r.get("detect_ok")):
            skipped.append({"slide": slide, "reason": "detection failed"})
            continue
        mpp = to_float(r.get("scan_mpp"))
        if mpp is None or mpp <= 0:
            skipped.append({"slide": slide, "reason": "no scan_mpp (QC skipped or no MPP in the header)"})
            continue
        fname = safe_name(slide) + ".geojson"
        if fname in owner:
            skipped.append({"slide": slide, "reason": "file name clash with slide %s" % owner[fname]})
            continue
        owner[fname] = slide
        feats = []
        for g in by_slide.get(slide, []):
            f = feature(g, mpp, object_type)
            if f is None:
                dropped += 1
            else:
                feats.append(f)
        docs[fname] = {"type": "FeatureCollection", "features": feats}
        features += len(feats)
    report = {"annot": CODE_VERSION, "object_type": object_type, "files": len(docs), "features": features,
              "dropped_rows": dropped, "skipped": skipped}
    return docs, report


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(out_dir, docs, report):
    os.makedirs(out_dir, exist_ok=True)
    for fname, doc in docs.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            json.dump(doc, f)
    with open(os.path.join(out_dir, REPORT), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="kidney/pipeline.py glomeruli -> QuPath GeoJSON per slide "
                                             "(research only).")
    ap.add_argument("--glomeruli", required=True, help="the pipeline's glomeruli.csv")
    ap.add_argument("--slides", required=True, help="the pipeline's slides.csv (scan_mpp, detect_ok)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--detections", action="store_true",
                    help="write QuPath detection objects instead of annotations")
    a = ap.parse_args(argv)
    for p in (a.glomeruli, a.slides):
        if not os.path.isfile(p):
            print(json.dumps({"error": "missing input file %s" % p}))
            return 2
    docs, report = build(read_csv(a.glomeruli), read_csv(a.slides),
                         "detection" if a.detections else "annotation")
    write(a.out_dir, docs, report)
    print(json.dumps(report))
    return 0 if not report["skipped"] and not report["dropped_rows"] else 1


if __name__ == "__main__":
    sys.exit(main())
