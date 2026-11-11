#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""anom: building blocks for the planned D2 lane of MV2's open kidney pipeline (NIDDK Kidney AI Discovery
Challenge): rank glomeruli by how unusual they look, then ask whether a participant's share of unusual glomeruli
goes with open clinical fields beyond what the globally sclerotic share already explains.

Made with AI agents (Claude) working in MV2's name. Research code, not a medical device and not for diagnosis.
No D2 analysis has been run and nothing here has been tuned on KPMP output. The D2 readings (k, top share, clinical
fields, thresholds, number of shuffles, seeds) will be fixed in a pre-registration published before any D2 output
exists; this module only provides the pieces, each with tests on synthetic numbers:

- Features per object: `masked_mean` pools an encoder feature map (C x H x W) over the object's mask (area-weighted
  nearest cells), and `baseline_features` gives a cheap hand-crafted baseline from the RGB crop and mask (area,
  extent, bounding-box aspect, per-channel mean and SD, pale fraction). The baseline is the "baseline method" an
  enrichment claim has to beat.
- Score: `standardize` (z-scores per column; a constant column becomes 0) and `knn_scores`: the mean Euclidean
  distance to the k nearest objects from OTHER groups (participants), so an object is never scored against its own
  biopsy. `knn_scores_np` is the same with numpy for large sets. `mahalanobis_np` is the normal-reference
  alternative (distance from a reference set, e.g. glomeruli KPMP labels non-sclerotic, with fixed shrinkage), the
  scoring idea of NoRDeC (Hasko et al., arXiv 2609.19444, 2026), re-implemented here from its description.
- Positive control: `auroc` (Mann-Whitney, ties count one half) of a score for a known abnormal class, e.g.
  KPMP's globally sclerotic label against its non-sclerotic label. A score that cannot find a known lesion should
  not be trusted to find unknown ones.
- Burden: `top_indices` takes the ceil(n * permille / 1000) highest scores (ties by input order, integer
  arithmetic), `burden` is each group's share of its objects in that set, `concentration` the largest share of the
  set from one group (a check that "unusual" is not just one odd slide).
- Association: `spearman`, `partial_spearman` (Spearman of x and y controlling z), `perm_p` (two-sided shuffle
  p-value of the partial correlation, (1 + count) / (1 + n_perm)) and `holm` (Holm step-down adjusted p-values).

Per-object scores and per-group burdens are private (KPMP data use terms): they stay local; only pooled readings may
be published. Standard-library parts run without numpy; numpy parts import it lazily.
Usage (local files only):
  python -m kidney.anom score --in objects.json --k 20 --top-permille 50 --out scores.json
  where objects.json is {"objects": [{"group": "<participant>", "x": [feature, ...]}, ...]}
"""
import argparse
import json
import math
import random

CODE_VERSION = "0.1.0"
K_DEFAULT = 20
TOP_PERMILLE_DEFAULT = 50
PALE_SUM = 600  # a pixel is pale when R + G + B >= 600 (mean >= 200)
BASELINE_NAMES = ("area_px", "extent", "aspect", "mean_r", "mean_g", "mean_b", "sd_r", "sd_g", "sd_b",
                  "pale_fraction")
TIE_EPS = 1e-12


def standardize(rows):
    """Column z-scores with the population SD; a constant column becomes all 0.0. rows: list of equal-length lists."""
    if not rows:
        return []
    n, d = len(rows), len(rows[0])
    if any(len(r) != d for r in rows):
        raise ValueError("rows differ in length")
    means = [sum(r[j] for r in rows) / n for j in range(d)]
    sds = [math.sqrt(sum((r[j] - means[j]) ** 2 for r in rows) / n) for j in range(d)]
    return [[(r[j] - means[j]) / sds[j] if sds[j] > 0 else 0.0 for j in range(d)] for r in rows]


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def knn_scores(rows, groups, k=K_DEFAULT):
    """Mean distance to the k nearest rows of OTHER groups (fewer if fewer exist; None if none). Pure Python, O(n^2)."""
    if len(rows) != len(groups):
        raise ValueError("rows and groups differ in length")
    if k < 1:
        raise ValueError("k must be >= 1")
    out = []
    for i, a in enumerate(rows):
        ds = sorted(_dist(a, b) for j, b in enumerate(rows) if groups[j] != groups[i])
        near = ds[:k]
        out.append(sum(near) / len(near) if near else None)
    return out


def knn_scores_np(rows, groups, k=K_DEFAULT, chunk=256):
    """knn_scores with numpy, in row chunks (same definition; float rounding may differ in the last bits)."""
    import numpy as np
    if len(rows) != len(groups):
        raise ValueError("rows and groups differ in length")
    if k < 1:
        raise ValueError("k must be >= 1")
    x = np.asarray(rows, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("rows must be a 2-D table")
    names = sorted(set(groups))
    code = {g: i for i, g in enumerate(names)}
    gid = np.array([code[g] for g in groups])
    sq = (x * x).sum(axis=1)
    out = []
    for s in range(0, len(x), chunk):
        e = min(s + chunk, len(x))
        d2 = sq[s:e, None] + sq[None, :] - 2.0 * (x[s:e] @ x.T)
        np.maximum(d2, 0.0, out=d2)
        d2[gid[s:e, None] == gid[None, :]] = np.inf
        near = np.sort(d2, axis=1)[:, :k]
        for row in near:
            fin = row[np.isfinite(row)]
            out.append(float(np.sqrt(fin).mean()) if fin.size else None)
    return out


def mahalanobis_np(ref_rows, rows, shrink=0.1):
    """Distance of each row from the reference set: sqrt((x - mu)' S^+ (x - mu)), where mu and C (population
    covariance) come from ref_rows, S = (1 - shrink) C + shrink (trace(C) / d) I, and S^+ is the pseudo-inverse."""
    import numpy as np
    if not 0 <= shrink <= 1:
        raise ValueError("shrink must be in 0..1")
    ref = np.asarray(ref_rows, dtype=np.float64)
    x = np.asarray(rows, dtype=np.float64)
    if ref.ndim != 2 or x.ndim != 2 or ref.shape[1] != x.shape[1] or len(ref) < 2:
        raise ValueError("need >= 2 reference rows and rows of the same width")
    mu = ref.mean(axis=0)
    c = np.atleast_2d(np.cov(ref, rowvar=False, bias=True))
    d = c.shape[0]
    s = (1 - shrink) * c + shrink * (np.trace(c) / d) * np.eye(d)
    inv = np.linalg.pinv(s)
    diff = x - mu
    q = np.einsum("ij,jk,ik->i", diff, inv, diff)
    return [float(v) for v in np.sqrt(np.maximum(q, 0.0))]


def auroc(scores, labels):
    """Area under the ROC curve of `scores` for labels 1 (positive) vs 0 (negative), by the rank-sum formula with
    average ranks (a tie counts one half). Rows with a None score are skipped. None if a class is empty."""
    pairs = [(s, int(l)) for s, l in zip(scores, labels) if s is not None]
    n1 = sum(1 for _, l in pairs if l == 1)
    n0 = sum(1 for _, l in pairs if l == 0)
    if len(pairs) != n1 + n0:
        raise ValueError("labels must be 0 or 1")
    if n1 == 0 or n0 == 0:
        return None
    r = ranks([s for s, _ in pairs])
    pos = sum(rv for rv, (_, l) in zip(r, pairs) if l == 1)
    return (pos - n1 * (n1 + 1) / 2) / (n1 * n0)


def top_indices(scores, permille=TOP_PERMILLE_DEFAULT):
    """Indices of the ceil(n * permille / 1000) highest non-None scores (at least 1 when n > 0); ties keep input
    order. Integer arithmetic, so 5% of 20 objects is exactly 1 object."""
    if not 0 < permille <= 1000:
        raise ValueError("permille must be in 1..1000")
    valid = [(s, i) for i, s in enumerate(scores) if s is not None]
    if not valid:
        return []
    m = max(1, (len(valid) * permille + 999) // 1000)
    valid.sort(key=lambda t: (-t[0], t[1]))
    return sorted(i for _, i in valid[:m])


def burden(scores, groups, permille=TOP_PERMILLE_DEFAULT):
    """Each group's share of its scored objects that fall in the top set. Groups without scored objects are left
    out. PRIVATE per-group values: keep local."""
    top = set(top_indices(scores, permille))
    n, hit = {}, {}
    for i, (s, g) in enumerate(zip(scores, groups)):
        if s is None:
            continue
        n[g] = n.get(g, 0) + 1
        hit[g] = hit.get(g, 0) + (1 if i in top else 0)
    return {g: hit[g] / n[g] for g in n}


def concentration(scores, groups, permille=TOP_PERMILLE_DEFAULT):
    """Largest share of the top set that comes from one group (None if the set is empty)."""
    top = top_indices(scores, permille)
    if not top:
        return None
    c = {}
    for i in top:
        c[groups[i]] = c.get(groups[i], 0) + 1
    return max(c.values()) / len(top)


def ranks(values):
    """1-based ranks; ties get the average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            out[order[t]] = avg
        i = j + 1
    return out


def pearson(x, y):
    """Pearson correlation; None when n < 3 or a side has no variance."""
    n = len(x)
    if n != len(y):
        raise ValueError("x and y differ in length")
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    if vx <= 0 or vy <= 0:
        return None
    return cov / math.sqrt(vx * vy)


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def partial_spearman(x, y, z):
    """Spearman correlation of x and y controlling z: (rxy - rxz * ryz) / sqrt((1 - rxz^2)(1 - ryz^2)). None when a
    correlation is undefined or z explains x or y completely."""
    rxy, rxz, ryz = spearman(x, y), spearman(x, z), spearman(y, z)
    if rxy is None or rxz is None or ryz is None:
        return None
    den = (1 - rxz * rxz) * (1 - ryz * ryz)
    if den <= 0:
        return None
    return (rxy - rxz * ryz) / math.sqrt(den)


def perm_p(x, y, z, n_perm, seed):
    """Two-sided shuffle p-value of partial_spearman(x, y, z): y is shuffled (x and z stay paired), and
    p = (1 + #{|r_perm| >= |r_obs| - 1e-12}) / (1 + n_perm). Shuffles with an undefined r count as not extreme.
    Returns (r_obs, p); (None, None) when r_obs is undefined."""
    r = partial_spearman(x, y, z)
    if r is None:
        return None, None
    rng = random.Random(seed)
    yy = list(y)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(yy)
        rp = partial_spearman(x, yy, z)
        if rp is not None and abs(rp) >= abs(r) - TIE_EPS:
            count += 1
    return r, (1 + count) / (1 + n_perm)


def holm(pvals):
    """Holm step-down adjusted p-values, in input order, capped at 1.0."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    out = [0.0] * m
    run = 0.0
    for rank_, i in enumerate(order):
        run = max(run, min(1.0, (m - rank_) * pvals[i]))
        out[i] = run
    return out


def masked_mean(fmap, mask):
    """Mean of a C x H x W feature map over an object mask (any size, bool). Each feature cell is weighted by the
    fraction of its block of mask pixels that is set (block rows r*Hm//H .. (r+1)*Hm//H - 1, likewise columns), so
    small objects still count. Returns a list of C floats, or None when no cell has any mask pixel."""
    import numpy as np
    f = np.asarray(fmap, dtype=np.float64)
    m = np.asarray(mask, dtype=bool)
    if f.ndim != 3 or m.ndim != 2:
        raise ValueError("fmap must be C x H x W and mask H x W")
    _, hf, wf = f.shape
    hm, wm = m.shape
    w = np.zeros((hf, wf), dtype=np.float64)
    for r in range(hf):
        r0, r1 = r * hm // hf, max((r + 1) * hm // hf, r * hm // hf + 1)
        for c in range(wf):
            c0, c1 = c * wm // wf, max((c + 1) * wm // wf, c * wm // wf + 1)
            block = m[r0:r1, c0:c1]
            w[r, c] = block.mean() if block.size else 0.0
    tot = w.sum()
    if tot <= 0:
        return None
    return [float(v) for v in (f * w[None]).sum(axis=(1, 2)) / tot]


def baseline_features(rgb, mask):
    """Hand-crafted baseline for one object: BASELINE_NAMES in order. rgb is H x W x 3 (uint8 or float), mask H x W
    bool. Returns None for an empty mask."""
    import numpy as np
    a = np.asarray(rgb)
    m = np.asarray(mask, dtype=bool)
    if a.ndim != 3 or a.shape[2] != 3 or a.shape[:2] != m.shape:
        raise ValueError("rgb must be H x W x 3 and mask H x W")
    area = int(m.sum())
    if area == 0:
        return None
    ys, xs = np.nonzero(m)
    h = int(ys.max() - ys.min() + 1)
    w = int(xs.max() - xs.min() + 1)
    px = a[m].astype(np.float64)
    mean = px.mean(axis=0)
    sd = px.std(axis=0)
    pale = float((px.sum(axis=1) >= PALE_SUM).mean())
    return [float(area), area / (h * w), min(h, w) / max(h, w), float(mean[0]), float(mean[1]), float(mean[2]),
            float(sd[0]), float(sd[1]), float(sd[2]), pale]


def score_objects(objects, k=K_DEFAULT, permille=TOP_PERMILLE_DEFAULT, use_numpy=True):
    """Standardize, kNN-score against other groups, and summarize. Returns a PRIVATE document (per-object scores)."""
    rows = standardize([o["x"] for o in objects])
    groups = [o["group"] for o in objects]
    if use_numpy:
        try:
            scores = knn_scores_np(rows, groups, k)
        except ImportError:
            scores = knn_scores(rows, groups, k)
    else:
        scores = knn_scores(rows, groups, k)
    return {"code_version": CODE_VERSION, "private": True, "k": k, "top_permille": permille,
            "n_objects": len(objects), "n_groups": len(set(groups)), "scores": scores,
            "top": top_indices(scores, permille), "burden": burden(scores, groups, permille),
            "concentration": concentration(scores, groups, permille)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="kNN anomaly scores against other participants (local files only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--in", dest="inp", required=True)
    s.add_argument("--k", type=int, default=K_DEFAULT)
    s.add_argument("--top-permille", type=int, default=TOP_PERMILLE_DEFAULT)
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.inp, encoding="utf-8") as f:
        objects = json.load(f)["objects"]
    doc = score_objects(objects, a.k, a.top_permille)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    print(json.dumps({"code_version": CODE_VERSION, "n_objects": doc["n_objects"], "n_groups": doc["n_groups"],
                      "k": a.k, "top_permille": a.top_permille}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
