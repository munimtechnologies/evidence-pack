#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""slidepass: the one-slide-at-a-time driver of the D1/D2 slide pass in MV2's open entry for the NIDDK Kidney AI
Discovery Challenge (findings/kidney-d2-prereg-v1-2026-11-12.md, "Pipeline (fixed)", step 2: "one slide downloaded,
processed and deleted at a time, in the file list's order, split into compute jobs of at most 12 hours that all use
the same code tag"). It changes no pre-registered number and no model setting: it only runs the published tools in
order, per slide, and keeps the job inside its time limit.

Made with AI agents (Claude) working in MV2's name; no human has reviewed it yet. Research code, not a medical device,
not for diagnosis or patient care. Standard library only (the tools it calls need numpy, OpenCV, tifffile and torch).

Per slide of a download list ([{"slide", "package", "name"}, ...], for example a batch-NN.json of `kidney.prep plan`),
in list order:
  1. a fresh temporary folder holding one.json (this slide only);
  2. fetch:  python <fetch.py> --slides one.json --wsi TMP/wsi --masks TMP/masks --out OUT/fetch/<slide>.json
  3. kmask:  python -m kidney.kmask --masks TMP/masks --wsi TMP/wsi --out OUT/k/<slide>.json
             --diag OUT/kdiag/<slide>.json --only <slide>          (KPMP's objects; reads the .svs, so it runs first)
  4. emb:    python -m kidney.emb run --in-dir TMP/wsi --model M --out OUT/emb/<slide>.json --delete [--threads T]
  5. the temporary folder is deleted.
A failed step skips the slide's later steps. Before each slide the driver checks that FACTOR x the longest slide so
far (FIRST_GUESS_S before any) still fits before the deadline minus RESERVE_S; otherwise it stops and leaves the rest
for a later job. Each step gets a time limit that ends at that same point; a step that hits it stops the pass. After
MAX_FAIL_STREAK failed slides in a row it stops too (for example a checkpoint that does not load).

Outputs (PRIVATE, local only under KPMP's data use terms; never published): OUT/emb.json and OUT/k.json (all slides
merged with kidney.prep merge-det / merge-k), OUT/progress.json (per-slide status and seconds, rewritten after every
slide) and OUT/undone.json (the list items not finished, in download-list form, for the next job). The command line
prints totals only.
Usage:
  python -m kidney.slidepass run --list batch-01.json --model gs.pth --fetch /work/fetch.py --tmp /tmp/slidepass-1 \\
      --out-dir /out/pass --deadline-minutes 640 [--threads 3] [--repo /tmp/ep]
Exit 0 when every slide of the list is done, 1 when some are not (see undone.json), 2 for an unusable list or folder.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

from kidney import prep

CODE_VERSION = "0.1.0"
RESERVE_S = 900.0
FACTOR = 1.5
FIRST_GUESS_S = 1800.0
MAX_FAIL_STREAK = 3
MIN_STEP_TIMEOUT_S = 60.0
TMP_PREFIX = "slidepass"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
OUT_SUBDIRS = ("fetch", "k", "kdiag", "emb")


# ---- checks ----

def check_list(items):
    """Problems with a download list (strings without slide names or ids); empty when it can be run. Every item needs
    a non-empty "slide", "package" and "name"; slide names must be unique and safe in a path and in kmask's --only;
    a package may appear once."""
    if not isinstance(items, list) or not items:
        return ["the list is empty or not a list"]
    probs, names, pkgs = [], set(), set()
    for i, it in enumerate(items):
        if not isinstance(it, dict) or not all(isinstance(it.get(k), str) and it.get(k)
                                               for k in ("slide", "package", "name")):
            probs.append("item %d lacks slide, package or name" % (i + 1))
            continue
        if not NAME_RE.match(it["slide"]):
            probs.append("item %d has an unsafe slide name" % (i + 1))
        if it["slide"] in names:
            probs.append("item %d reuses a slide name" % (i + 1))
        if it["package"] in pkgs:
            probs.append("item %d repeats a package" % (i + 1))
        names.add(it["slide"])
        pkgs.add(it["package"])
    return probs


def tmp_ok(tmp, out_dir):
    """True when `tmp` may be deleted and recreated by the driver: its own folder name starts with TMP_PREFIX and the
    output folder is not inside it (nor the same)."""
    t = os.path.abspath(tmp)
    o = os.path.abspath(out_dir)
    if not os.path.basename(t).startswith(TMP_PREFIX):
        return False
    return not (o == t or o.startswith(t + os.sep))


# ---- timing ----

def should_start(elapsed, deadline, done_seconds, reserve=RESERVE_S, factor=FACTOR, first_guess=FIRST_GUESS_S):
    """True when one more slide is expected to end by deadline - reserve (all in seconds). Expected length: factor x
    the longest slide so far, or first_guess before any slide."""
    expect = factor * max(done_seconds) if done_seconds else first_guess
    return elapsed + expect <= deadline - reserve


def step_timeout(elapsed, deadline, reserve=RESERVE_S, floor=MIN_STEP_TIMEOUT_S):
    """Seconds a step may run: up to deadline - reserve, but never less than `floor`."""
    return max(floor, deadline - reserve - elapsed)


# ---- commands ----

def out_paths(out_dir, slide):
    return {"fetch": os.path.join(out_dir, "fetch", slide + ".json"),
            "k": os.path.join(out_dir, "k", slide + ".json"),
            "kdiag": os.path.join(out_dir, "kdiag", slide + ".json"),
            "emb": os.path.join(out_dir, "emb", slide + ".json")}


def commands(item, cfg):
    """[(step, argv), ...] for one list item, in the order they run."""
    s = item["slide"]
    t = cfg["tmp"]
    one, wsi, masks = os.path.join(t, "one.json"), os.path.join(t, "wsi"), os.path.join(t, "masks")
    o = out_paths(cfg["out_dir"], s)
    py = cfg.get("python") or sys.executable
    emb = [py, "-m", "kidney.emb", "run", "--in-dir", wsi, "--model", cfg["model"], "--out", o["emb"], "--delete"]
    if cfg.get("threads"):
        emb += ["--threads", str(cfg["threads"])]
    return [("fetch", [py, cfg["fetch"], "--slides", one, "--wsi", wsi, "--masks", masks, "--out", o["fetch"]]),
            ("kmask", [py, "-m", "kidney.kmask", "--masks", masks, "--wsi", wsi, "--out", o["k"],
                       "--diag", o["kdiag"], "--only", s]),
            ("emb", emb)]


def run_cmd(argv, cwd, timeout):
    """Return code of argv run in cwd, or None when it ran past `timeout` seconds (it is then killed)."""
    try:
        return subprocess.run(argv, cwd=cwd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return None


def fresh_tmp(path, create=True):
    if os.path.isdir(path):
        shutil.rmtree(path)
    if create:
        os.makedirs(path)


# ---- the pass ----

def summary(recs, stopped):
    """Totals only (no slide names): slides, count per status, why the pass stopped early (None if it did not),
    total, longest and mean minutes of the slides that started."""
    by = {}
    for r in recs:
        by[r["status"]] = by.get(r["status"], 0) + 1
    secs = [r["seconds"] for r in recs if r["seconds"] is not None]
    return {"code_version": CODE_VERSION, "slides": len(recs), "by_status": dict(sorted(by.items())),
            "stopped": stopped, "minutes": round(sum(secs) / 60.0, 1),
            "max_slide_minutes": round(max(secs) / 60.0, 1) if secs else None,
            "mean_slide_minutes": round(sum(secs) / len(secs) / 60.0, 1) if secs else None}


def run_pass(items, cfg, runner=None, clock=time.monotonic, save=None):
    """(records, stopped). One record per list item, in list order: {"slide", "status", "rc", "seconds"}, status one of
    ok, fetch_failed, kmask_failed, emb_failed, timeout, not_started. stopped: None, "deadline", "timeout" or
    "fail_streak". save(records, stopped) is called after every slide that started."""
    runner = runner or run_cmd
    deadline = float(cfg["deadline_minutes"]) * 60.0
    reserve = float(cfg.get("reserve", RESERVE_S))
    first_guess = float(cfg.get("first_guess", FIRST_GUESS_S))
    max_streak = int(cfg.get("max_fail_streak", MAX_FAIL_STREAK))
    for sub in OUT_SUBDIRS:
        os.makedirs(os.path.join(cfg["out_dir"], sub), exist_ok=True)
    t_start = clock()
    recs, done, streak, stopped = [], [], 0, None
    for it in items:
        rec = {"slide": it["slide"], "status": "not_started", "rc": {}, "seconds": None}
        recs.append(rec)
        if stopped:
            continue
        if not should_start(clock() - t_start, deadline, done, reserve, FACTOR, first_guess):
            stopped = "deadline"
            continue
        t0 = clock()
        fresh_tmp(cfg["tmp"])
        with open(os.path.join(cfg["tmp"], "one.json"), "w", encoding="utf-8") as f:
            json.dump([it], f)
        rec["status"] = "ok"
        for step, argv in commands(it, cfg):
            rc = runner(argv, cfg.get("repo", "."), step_timeout(clock() - t_start, deadline, reserve))
            rec["rc"][step] = rc
            if rc is None:
                rec["status"] = "timeout"
                stopped = "timeout"
                break
            if rc != 0:
                rec["status"] = step + "_failed"
                break
        fresh_tmp(cfg["tmp"], create=False)
        rec["seconds"] = round(clock() - t0, 1)
        done.append(rec["seconds"])
        streak = 0 if rec["status"] == "ok" else streak + 1
        if not stopped and streak >= max_streak:
            stopped = "fail_streak"
        if save:
            save(recs, stopped)
    return recs, stopped


def merge_outputs(recs, out_dir):
    """Merge the per-slide emb and k files of every slide that started into OUT/emb.json and OUT/k.json (list order).
    Returns totals: {"emb": prep.merge_det stats} or {"emb_error": ...}, and {"k": {"slides", "conflicts"}}."""
    emb_docs, k_docs = [], []
    for r in recs:
        if r["status"] == "not_started":
            continue
        p = out_paths(out_dir, r["slide"])
        if os.path.exists(p["emb"]):
            emb_docs.append(_load(p["emb"]))
        if os.path.exists(p["k"]):
            k_docs.append(_load(p["k"]))
    res = {}
    if emb_docs:
        try:
            doc, st = prep.merge_det(emb_docs)
            _write(os.path.join(out_dir, "emb.json"), doc)
            res["emb"] = st
        except ValueError as e:
            res["emb_error"] = str(e)
    if k_docs:
        doc, conflicts = prep.merge_k(k_docs)
        _write(os.path.join(out_dir, "k.json"), doc)
        res["k"] = {"slides": len(doc), "conflicts": conflicts}
    return res


def undone(items, recs):
    """The list items whose slide did not end "ok", in list order."""
    status = {r["slide"]: r["status"] for r in recs}
    return [it for it in items if status.get(it["slide"]) != "ok"]


# ---- command line ----

def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


def main(argv=None, runner=None, clock=time.monotonic):
    ap = argparse.ArgumentParser(description="One-slide-at-a-time D1/D2 slide pass (local outputs only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--list", required=True, help="download list: [{slide, package, name}, ...]")
    p.add_argument("--model", required=True, help="3-class checkpoint written by `python -m kidney.gsdet train`")
    p.add_argument("--fetch", required=True, help="the job's fetch.py")
    p.add_argument("--tmp", required=True, help="scratch folder named %s*, deleted after every slide" % TMP_PREFIX)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--deadline-minutes", type=float, required=True,
                   help="minutes from the driver's start by which it must be done (leave room for setup)")
    p.add_argument("--reserve-minutes", type=float, default=RESERVE_S / 60.0)
    p.add_argument("--first-guess-minutes", type=float, default=FIRST_GUESS_S / 60.0)
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--repo", default=".", help="folder the kidney package is run from")
    a = ap.parse_args(argv)
    rep = {"code_version": CODE_VERSION, "cmd": a.cmd}
    items = _load(a.list)
    probs = check_list(items)
    if not tmp_ok(a.tmp, a.out_dir):
        probs.append("--tmp must be a folder named %s* that does not hold --out-dir" % TMP_PREFIX)
    if probs:
        rep["problems"] = probs
        print(json.dumps(rep))
        return 2
    os.makedirs(a.out_dir, exist_ok=True)
    cfg = {"tmp": a.tmp, "out_dir": a.out_dir, "model": a.model, "fetch": a.fetch, "repo": a.repo,
           "threads": a.threads, "deadline_minutes": a.deadline_minutes, "reserve": a.reserve_minutes * 60.0,
           "first_guess": a.first_guess_minutes * 60.0}
    prog = os.path.join(a.out_dir, "progress.json")

    def save(recs, stopped):
        _write(prog, {"summary": summary(recs, stopped), "slides": recs})

    recs, stopped = run_pass(items, cfg, runner=runner, clock=clock, save=save)
    summ = summary(recs, stopped)
    summ["merge"] = merge_outputs(recs, a.out_dir)
    _write(prog, {"summary": summ, "slides": recs})
    left = undone(items, recs)
    _write(os.path.join(a.out_dir, "undone.json"), left)
    summ["undone"] = len(left)
    rep.update(summ)
    print(json.dumps(rep))
    sys.stdout.flush()
    return 0 if not left and "emb_error" not in summ["merge"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
