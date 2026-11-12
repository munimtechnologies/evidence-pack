#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""emb: one slide pass that detects glomeruli exactly as kidney/gsdet.py `detect` does and also saves, for every
detected glomerulus, an encoder embedding and a hand-crafted baseline feature vector. These are the inputs of the
planned D2 lane (anomaly ranking, kidney/anom.py) of MV2's open entry for the NIDDK Kidney AI Discovery Challenge.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical
device, not for diagnosis or patient care. No D2 analysis has been run; its readings will be pre-registered before
any D2 output exists.

Per slide (file-name order), with a 3-class checkpoint written by `gsdet train`:
  1. the working image at 1.5 um per pixel (kidney/glom.py `slide_image`), gsdet.predict3 and gsdet.decode: the same
     objects [cx, cy, x0, y0, x1, y1, area] (um) and classes ("gs" / "ns") as `gsdet detect`;
  2. the same 8-connected regions are labelled again, and each kept region (area >= MIN_AREA_UM2) gets a WINDOW x
     WINDOW pixel window centred on its centroid (gsdet.crop_origin; outside the slide is white) and its own mask in
     that window (only its own label; neighbours are left out);
  3. embedding: the checkpoint's encoder (efficientnet-b2) run once on the window, the feature map of encoder stage
     `stage` (default: the deepest, stride 32, 352 channels) pooled over the object's mask with anom.masked_mean;
     baseline: anom.baseline_features of the window and mask (area in window pixels, extent, aspect, RGB means and
     SDs, pale fraction). `clipped` is True when the region's box does not fit in the window (its window area and
     mask are then cut).
The window is 288 pixels (432 um), a multiple of the encoder's stride of 32.

Outputs stay local (KPMP data use terms): the embedding document holds per-object values and is never published;
the command line prints aggregates only. Standard-library parts and their tests run without numpy, torch or OpenCV.
Usage:
  python -m kidney.emb run --in-dir /wsi --model gs.pth --out emb.json [--threads 3] [--delete]
  python -m kidney.emb table --emb emb.json --groups groups.json --kind emb --out objects.json
  (groups.json maps slide name -> group, e.g. participant; objects.json is the input of `python -m kidney.anom score`)
"""
import argparse
import json
import os
import time

from kidney import gsdet
from kidney.glom import MIN_AREA_UM2

CODE_VERSION = "0.1.0"
WINDOW = 288
STRIDE = 32
BATCH = 16
STAGE = -1
ROUND = 5
KINDS = ("emb", "base")


# ---- standard-library parts ----

def check_window(size):
    """Raise ValueError unless size is a positive multiple of STRIDE."""
    if int(size) != size or size <= 0 or size % STRIDE:
        raise ValueError("window must be a positive multiple of %d" % STRIDE)
    return int(size)


def kept_labels(rows, sx, min_area_um2=MIN_AREA_UM2):
    """Indices into `rows` ((left, top, width, height, area_px, cx, cy), label order) of the regions that
    glom.region_records keeps: area_px x sx x sx >= min_area_um2."""
    return [i for i, r in enumerate(rows) if r[4] * sx * sx >= min_area_um2]


def clipped(left, top, width, height, wl, wt, size=WINDOW):
    """True when the box [left, left + width) x [top, top + height) is not fully inside the window
    [wl, wl + size) x [wt, wt + size)."""
    return left < wl or top < wt or left + width > wl + size or top + height > wt + size


def rounded(values, nd=ROUND):
    return [round(float(v), nd) for v in values]


def table(doc, groups, kind="emb"):
    """(objects, skipped): anom's input rows {"group", "slide", "index", "class", "x"} for every object of every
    slide that succeeded, where `x` is the object's `kind` vector ("emb" or "base") and `index` counts from 1 per
    slide as in pipeline's glomeruli.csv. Objects of slides without a group, or without a vector, are skipped and
    counted. PRIVATE output: keep local."""
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    out, skipped = [], {"no_group": 0, "no_vector": 0}
    for r in doc.get("rows", []):
        if not r.get("ok"):
            continue
        g = groups.get(r["slide"])
        vecs = r.get(kind) or []
        classes = r.get("classes") or []
        for j, v in enumerate(vecs):
            if g is None:
                skipped["no_group"] += 1
            elif v is None:
                skipped["no_vector"] += 1
            else:
                out.append({"group": g, "slide": r["slide"], "index": j + 1,
                            "class": classes[j] if j < len(classes) else None, "x": list(v)})
    return out, skipped


def aggregate(doc):
    """Totals over slides only (no names, no per-slide values)."""
    rows = doc.get("rows", [])
    ok = [r for r in rows if r.get("ok")]
    return {"code_version": CODE_VERSION, "slides": len(rows), "ok": len(ok),
            "objects": sum(len(r.get("objects") or []) for r in ok),
            "with_emb": sum(1 for r in ok for v in (r.get("emb") or []) if v is not None),
            "clipped": sum(1 for r in ok for c in (r.get("clipped") or []) if c),
            "emb_dim": doc.get("emb_dim"),
            "minutes": round(sum(float(r.get("seconds") or 0) for r in rows) / 60.0, 1)}


# ---- numpy / OpenCV parts (torch only through `encoder`) ----

def embed_slide(img, pbg, pgs, sx, sy, encoder, size=WINDOW, batch=BATCH):
    """(objects, classes, emb, base, clipped) of one slide. objects and classes are gsdet.decode's; emb, base and
    clipped are aligned with them. `encoder` maps a list of size x size x 3 uint8 windows to an N x C x h x w array."""
    import cv2
    import numpy as np
    from kidney.anom import baseline_features, masked_mean
    check_window(size)
    objs, classes = gsdet.decode(pbg, pgs, sx, sy)
    fg = (pbg < gsdet.FG_MAX_BG).astype(np.uint8)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(fg, connectivity=8)
    del fg
    rows = [(int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]), int(stats[i, cv2.CC_STAT_WIDTH]),
             int(stats[i, cv2.CC_STAT_HEIGHT]), int(stats[i, cv2.CC_STAT_AREA]), float(cents[i, 0]),
             float(cents[i, 1])) for i in range(1, n)]
    keep = kept_labels(rows, sx)
    if len(keep) != len(objs):
        raise ValueError("the label pass kept %d regions, decode %d" % (len(keep), len(objs)))
    rgb_img = img[..., :3]
    emb, base, clip = [], [], []
    for s in range(0, len(keep), batch):
        wins, masks = [], []
        for k in keep[s:s + batch]:
            left, top, width, height, _, cx, cy = rows[k]
            wl, wt = gsdet.crop_origin(cx, cy, size)
            win = gsdet.crop(rgb_img, wl, wt, size, 255)
            m = gsdet.crop(labels, wl, wt, size, 0) == (k + 1)
            wins.append(win)
            masks.append(m)
            clip.append(clipped(left, top, width, height, wl, wt, size))
            b = baseline_features(win, m)
            base.append(None if b is None else rounded(b))
        feats = np.asarray(encoder(wins))
        if feats.shape[0] != len(wins):
            raise ValueError("encoder returned %d maps for %d windows" % (feats.shape[0], len(wins)))
        for f, m in zip(feats, masks):
            v = masked_mean(f, m)
            emb.append(None if v is None else rounded(v))
    del labels
    return objs, classes, emb, base, clip


# ---- torch parts ----

def make_encoder(model, mean, std, stage=STAGE):
    """A function: list of uint8 windows -> N x C x h x w numpy array of the model encoder's stage `stage`, with the
    checkpoint's normalisation (no augmentation, no gradients)."""
    import numpy as np
    import torch

    def enc(wins):
        x = (np.stack(wins).astype("float32") / 255.0 - mean) / std
        x = np.ascontiguousarray(x.transpose(0, 3, 1, 2).astype("float32"))
        with torch.no_grad():
            feats = model.encoder(torch.from_numpy(x))
        return feats[stage].numpy()
    return enc


def run_embed(in_dir, model_path, tta=True, size=WINDOW, stage=STAGE, batch=BATCH, delete=False):
    """Embedding document for every .svs in in_dir (local only). Detection is gsdet.run_detect's."""
    from kidney.glom import slide_image, y_scale
    check_window(size)
    model, mean, std, steps = gsdet.load_model3(model_path)
    enc = make_encoder(model, mean, std, stage)
    rows = []
    for fn in sorted(f for f in os.listdir(in_dir) if f.lower().endswith(".svs")):
        t0 = time.time()
        path = os.path.join(in_dir, fn)
        rec = {"slide": os.path.splitext(fn)[0], "ok": False, "errors": []}
        try:
            img, mpp, _, _, size0 = slide_image(path)
            sy = y_scale(mpp, size0, (img.shape[1], img.shape[0]))
            pbg, pgs, used, skipped = gsdet.predict3(img, model, mean, std, tta=tta)
            t1 = time.time()
            objs, classes, emb, base, clip = embed_slide(img, pbg, pgs, mpp, sy, enc, size, batch)
            del img, pbg, pgs
            rec.update(ok=True, mpp=round(mpp, 4), tiles_used=used, tiles_skipped=skipped, objects=objs,
                       classes=classes, emb=emb, base=base, clipped=clip, detect_seconds=round(t1 - t0, 1))
        except Exception as e:  # one bad slide must not stop the folder
            rec["errors"].append(repr(e)[:300])
        if delete and os.path.exists(path):
            os.remove(path)
        rec["seconds"] = round(time.time() - t0, 1)
        rows.append(rec)
    from kidney.anom import BASELINE_NAMES, CODE_VERSION as ANOM_VERSION
    return {"code_version": CODE_VERSION, "gsdet": gsdet.CODE_VERSION, "anom": ANOM_VERSION, "private": True,
            "train_steps": steps, "tta": tta, "fg_max_bg": gsdet.FG_MAX_BG, "window": size, "stage": stage,
            "emb_dim": int(model.encoder.out_channels[stage]), "base_names": list(BASELINE_NAMES), "rows": rows}


# ---- command line ----

def _write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


def cmd_run(a):
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    doc = run_embed(a.in_dir, a.model, tta=not a.no_tta, size=a.window, stage=a.stage, batch=a.batch,
                    delete=a.delete)
    _write(a.out, doc)
    agg = aggregate(doc)
    print(json.dumps(agg))
    return 0 if agg["slides"] and agg["ok"] == agg["slides"] else 1


def cmd_table(a):
    with open(a.emb, encoding="utf-8") as f:
        doc = json.load(f)
    with open(a.groups, encoding="utf-8") as f:
        groups = json.load(f)
    objs, skipped = table(doc, groups, a.kind)
    _write(a.out, {"code_version": CODE_VERSION, "private": True, "kind": a.kind, "objects": objs})
    print(json.dumps({"code_version": CODE_VERSION, "kind": a.kind, "objects": len(objs), "skipped": skipped}))
    return 0 if objs else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Glomerulus detection + per-object embeddings (local outputs only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--in-dir", required=True)
    p.add_argument("--model", required=True, help="3-class checkpoint written by `python -m kidney.gsdet train`")
    p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--window", type=int, default=WINDOW)
    p.add_argument("--stage", type=int, default=STAGE)
    p.add_argument("--batch", type=int, default=BATCH)
    p.add_argument("--no-tta", action="store_true")
    p.add_argument("--delete", action="store_true", help="delete each slide after it is processed")
    p = sub.add_parser("table")
    p.add_argument("--emb", required=True)
    p.add_argument("--groups", required=True, help="JSON object: slide name -> group (e.g. participant)")
    p.add_argument("--kind", choices=KINDS, default="emb")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"run": cmd_run, "table": cmd_table}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
