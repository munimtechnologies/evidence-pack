#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kmask: read KPMP's released glomerulus segmentation (OME-TIFF label masks) into the objects kidney/compare.py
counts.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
Implements the mask-reading rules of findings/kidney-glom-compare-plan-v0-addendum-2-2026-11-09.md, published
before any graded slide was processed.

KPMP's 'Seg_Masks_Features' packages hold a multilayer pyramidal OME-TIFF (axes CYX, one channel per tissue class,
each segmented unit a unique integer in its channel). The channel names come from the OME-XML. The two glomerulus
channels, 'non-globally-sclerotic glomeruli' and 'globally-sclerotic glomeruli', give objects of kind 'glom' and
'gs'. One object is one distinct non-zero label value; its area is the number of pixels carrying that label at the
pyramid level read. The OME-XML gives no pixel size, so the mask's pixel size is taken from the slide (.svs) header,
and only when the mask's level-0 width and height equal the slide's; otherwise the area floor is not applied and
the areas are not converted.

0.2.0 (stage 3b, findings/kidney-glom-stage3b-prereg-v1-2026-11-09.md): each slide's record also holds
`k_areas_by_kind`, the kept areas of each glomerulus class separately (same floor and rounding as count_k). Counting
is unchanged.

Outputs stay local: k.json maps each slide to count_k()'s result and kmask-diag.json holds per-slide checks. The
command line prints aggregates only. Standard-library parts and their tests run without numpy or tifffile. Usage:
  python -m kidney.kmask --masks /masks --wsi /wsi --out k.json [--diag kmask-diag.json]
(files: /masks/<slide>.ome.tif, optional /masks/<slide>_features.xlsx, /wsi/<slide>.svs)
"""
import argparse
import json
import os
import xml.etree.ElementTree as ET

CODE_VERSION = "0.2.0"
GLOM_CHANNELS = {"non-globally-sclerotic glomeruli": "glom", "globally-sclerotic glomeruli": "gs"}
SHEETS = {"glom": "gloms", "gs": "s_gloms"}
MAX_LEVEL_PIXELS = 100_000_000
STRIP_ROWS = 1024
MASK_SUFFIX = ".ome.tif"
SHEET_SUFFIX = "_features.xlsx"


# ---- standard-library parts ----

def norm(name):
    """Lower case, inner whitespace collapsed."""
    return " ".join(str(name).lower().split())


def ome_channel_names(xml_text):
    """Channel names, in order, from an OME-XML string ([] if none or unparsable)."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        return []
    return [el.attrib.get("Name", "") for el in root.iter() if el.tag == "Channel" or el.tag.endswith("}Channel")]


def channel_kinds(names):
    """{channel index: 'glom' | 'gs'} for the two glomerulus channels. ValueError unless each appears exactly once."""
    out = {}
    for i, n in enumerate(names):
        kind = GLOM_CHANNELS.get(norm(n))
        if kind is None:
            continue
        if kind in out.values():
            raise ValueError("glomerulus channel named twice: %r" % (n,))
        out[i] = kind
    if sorted(out.values()) != ["glom", "gs"]:
        raise ValueError("glomerulus channels not found in %r" % (list(names),))
    return out


def pick_level(shapes, max_pixels=MAX_LEVEL_PIXELS):
    """Index of the finest pyramid level with height x width <= max_pixels (the coarsest if none is that small).
    `shapes` is [(height, width)], level 0 first."""
    for i, (h, w) in enumerate(shapes):
        if h * w <= max_pixels:
            return i
    return len(shapes) - 1


def mask_mpp(slide_mpp0, slide_size0, mask_size0, level_width):
    """Micrometres per pixel of the mask level read, or None when it cannot be linked to the slide: no slide MPP,
    or the mask's level-0 (width, height) differs from the slide's."""
    if not slide_mpp0 or not level_width:
        return None
    if tuple(int(v) for v in slide_size0) != tuple(int(v) for v in mask_size0):
        return None
    return float(slide_mpp0) * (int(mask_size0[0]) / float(level_width))


def add_counts(acc, pairs):
    """Add (label, pixels) pairs into dict `acc`; label 0 is background and is skipped."""
    for lab, n in pairs:
        lab, n = int(lab), int(n)
        if lab != 0 and n > 0:
            acc[lab] = acc.get(lab, 0) + n
    return acc


def objects(label_pixels):
    """[(kind, pixels)]: one object per distinct non-zero label of each glomerulus channel, 'glom' first."""
    out = []
    for kind in ("glom", "gs"):
        px = label_pixels.get(kind, {})
        out.extend((kind, px[lab]) for lab in sorted(px))
    return out


def slide_k(label_pixels, mpp):
    """count_k() of one slide (kidney/compare.py) from its label pixel counts and the mask pixel size (or None),
    plus `k_areas_by_kind`: {kind: kept areas in um^2, sorted, or None without a pixel size}."""
    from kidney.compare import count_k
    obs = objects(label_pixels)
    out = count_k(obs, mask_mpp=mpp)
    out["k_areas_by_kind"] = {kind: count_k([o for o in obs if o[0] == kind], mask_mpp=mpp)["k_areas_um2"]
                              for kind in ("glom", "gs")}
    return out


def sheet_check(label_pixels, sheet_rows):
    """Do the label counts equal the feature workbook's row counts ('gloms', 's_gloms')? None if no workbook."""
    if sheet_rows is None:
        return None
    return all(len(label_pixels.get(kind, {})) == sheet_rows.get(sheet) for kind, sheet in SHEETS.items())


def slide_names(mask_dir, only=()):
    """Slide names with a <slide>.ome.tif in `mask_dir`, sorted."""
    names = sorted(f[:-len(MASK_SUFFIX)] for f in os.listdir(mask_dir) if f.lower().endswith(MASK_SUFFIX))
    return [n for n in names if not only or n in only]


def aggregate(diag):
    """Counts over slides only (no names, no per-slide values): safe to print."""
    rows = list(diag.values())
    ok = [r for r in rows if r.get("ok")]
    checked = [r for r in ok if r.get("sheet_match") is not None]
    return {"code_version": CODE_VERSION, "slides": len(rows), "ok": len(ok),
            "mpp_linked": sum(1 for r in ok if r.get("mask_mpp")),
            "sheet_checked": len(checked), "sheet_match": sum(1 for r in checked if r["sheet_match"])}


# ---- numpy / tifffile / openpyxl parts ----

def plane_counts(plane, strip_rows=STRIP_ROWS):
    """{label: pixels} of a 2-D unsigned-integer label plane, counted in row strips to bound memory."""
    import numpy as np
    a = np.asarray(plane)
    if a.ndim != 2 or a.dtype.kind != "u":
        raise ValueError("expected a 2-D unsigned integer plane, got %s %s" % (a.shape, a.dtype))
    acc = {}
    for r in range(0, a.shape[0], strip_rows):
        bc = np.bincount(a[r:r + strip_rows].ravel())
        nz = np.nonzero(bc)[0]
        add_counts(acc, zip(nz.tolist(), bc[nz].tolist()))
    return acc


def read_mask(path, max_pixels=MAX_LEVEL_PIXELS):
    """({kind: {label: pixels}}, info) for one OME-TIFF mask; info has the level read and the sizes."""
    import tifffile
    with tifffile.TiffFile(path) as tif:
        s = tif.series[0]
        axes = str(getattr(s, "axes", ""))
        if not (axes.endswith("YX") and "C" in axes and len(s.shape) == 3):
            raise ValueError("expected CYX axes, got %r %r" % (axes, s.shape))
        kinds = channel_kinds(ome_channel_names(tif.pages[0].description or ""))
        levels = list(getattr(s, "levels", [s]))
        shapes = [(lv.shape[-2], lv.shape[-1]) for lv in levels]
        li = pick_level(shapes, max_pixels)
        out = {}
        for c, kind in kinds.items():
            try:
                plane = levels[li].pages[c].asarray()
            except Exception:  # noqa: BLE001  (fall back to tifffile's own page selection)
                plane = levels[li].asarray(key=c)
            if tuple(plane.shape[-2:]) != tuple(shapes[li]):
                raise ValueError("plane shape %r differs from level shape %r" % (plane.shape, shapes[li]))
            out[kind] = plane_counts(plane.reshape(shapes[li]))
    h0, w0 = shapes[0]
    return out, {"level": li, "mask_size0": [w0, h0], "level_width": shapes[li][1]}


def read_sheet_rows(path):
    """{'gloms': rows, 's_gloms': rows} (data rows after the header) of a KPMP feature workbook."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        out = {}
        for ws in wb.worksheets:
            if ws.title in SHEETS.values():
                out[ws.title] = max(0, sum(1 for _ in ws.iter_rows(values_only=True)) - 1)
        return out
    finally:
        wb.close()


def slide_info(svs_path):
    """(level-0 MPP from the Aperio header or None, (width, height) of level 0)."""
    import tifffile
    from kidney.wsi_qc import parse_aperio, slide_levels
    with tifffile.TiffFile(svs_path) as tif:
        p0, w0, h0 = slide_levels(tif)[0]
        mpp0 = parse_aperio(getattr(p0, "description", "") or "").get("mpp")
    return mpp0, (w0, h0)


def run_slide(name, mask_dir, wsi_dir):
    """(count_k result or None, local diagnostic record) for one slide."""
    diag = {"ok": False, "errors": []}
    try:
        px, info = read_mask(os.path.join(mask_dir, name + MASK_SUFFIX))
        mpp0, size0 = slide_info(os.path.join(wsi_dir, name + ".svs"))
        mpp = mask_mpp(mpp0, size0, info["mask_size0"], info["level_width"])
        sheet = os.path.join(mask_dir, name + SHEET_SUFFIX)
        rows = read_sheet_rows(sheet) if os.path.exists(sheet) else None
        k = slide_k(px, mpp)
        diag.update(info, ok=True, mask_mpp=round(mpp, 4) if mpp else None, slide_size0=list(size0),
                    labels={kind: len(px.get(kind, {})) for kind in ("glom", "gs")}, sheet_rows=rows,
                    sheet_match=sheet_check(px, rows))
        return k, diag
    except Exception as e:  # one bad slide must not stop the folder
        diag["errors"].append(repr(e)[:300])
        return None, diag


def main(argv=None):
    ap = argparse.ArgumentParser(description="KPMP glomerulus objects from OME-TIFF label masks (local output).")
    ap.add_argument("--masks", required=True, help="folder with <slide>.ome.tif [and <slide>_features.xlsx]")
    ap.add_argument("--wsi", required=True, help="folder with <slide>.svs")
    ap.add_argument("--out", required=True, help="k.json for kidney/compare.py (local)")
    ap.add_argument("--diag", default="", help="per-slide diagnostics (local)")
    ap.add_argument("--only", default="", help="comma-separated slide names")
    a = ap.parse_args(argv)
    only = set(s for s in a.only.split(",") if s)
    k_doc, diag = {}, {}
    for name in slide_names(a.masks, only):
        k, d = run_slide(name, a.masks, a.wsi)
        diag[name] = d
        if k is not None:
            k_doc[name] = k
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(k_doc, f, indent=1)
    if a.diag:
        with open(a.diag, "w", encoding="utf-8") as f:
            json.dump(diag, f, indent=1)
    agg = aggregate(diag)
    print(json.dumps(agg))
    return 0 if agg["slides"] and agg["ok"] == agg["slides"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
