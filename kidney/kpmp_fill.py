#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""kpmp_fill: fill the KPMP cache on whichever machine a job lands on.

The compute pool keeps one data volume per machine. kpmp-tbm0-v1 and kpmp-patches-v1 ran where the
kpmp-open-files volume had never been filled, so they found no workbooks (results note
findings/kpmp-patches-results-v1-2026-10-28.md, section 4). Run this step first and a job no longer
depends on the machine.

For every open segmentation package not yet cached, it reads only the members the census keeps
(feature workbooks, OME-XML, README; kidney.kpmp_census KEEP_EXT and KEEP_MAX_BYTES) straight out of
the remote zip with HTTP range requests, and writes the same <package>/record.json the census
writes. Slides and masks are never transferred. If the server does not answer range requests, the
package is skipped (after RANGE_GIVE_UP such answers in a row with nothing filled, the rest are
skipped too) unless --allow-full is given, which falls back to the census's whole-zip download. The
TIV and clinical files are small and are downloaded whole, to the paths kpmp_census3 and kpmp_q2 use.

Writes counts only (out-dir/fill.json). Standard library only. Usage:
  python -m kidney.kpmp_fill --file-list inputs/kpmp-segmentation-files.csv \
      --descriptor-list inputs/kpmp-descriptor-files-20261027.csv \
      --clinical-list inputs/kpmp-clinical-files.csv --data-dir /data --out-dir /out/fill
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter

from kidney import kpmp_census as kc
from kidney import kpmp_census2 as k2
from kidney import kpmp_q2 as q2

CODE_VERSION = "1.0"
UA = "mv2-kpmp-fill/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
BLOCK = 1 << 20
RANGE_GIVE_UP = 5
CONTENT_RANGE = re.compile(r"bytes 0-0/(\d+)$")


class RangeUnsupported(Exception):
    """The server answered a range request with something other than 206."""


def _urlopen(req, timeout):
    return urllib.request.urlopen(req, timeout=timeout)


def http_probe(url, opener=None):
    """((final url, total bytes), "") if a one-byte range request is answered with 206 and a
    Content-Range, else (None, reason). The body of a non-206 answer is never read."""
    opener = opener or _urlopen
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
    try:
        with opener(req, 120) as resp:
            if resp.status != 206:
                return None, "HTTP %d" % resp.status
            cr = (resp.headers.get("Content-Range") or "").strip()
            m = CONTENT_RANGE.match(cr)
            if not m:
                return None, "Content-Range %r" % cr[:80]
            resp.read()
            return (resp.geturl(), int(m.group(1))), ""
    except Exception as e:
        return None, repr(e)[:200]


def http_range(url, start, end, opener=None, tries=3, pause=None):
    """Bytes start..end (inclusive) of url. A non-206 answer raises RangeUnsupported unread."""
    opener, pause = opener or _urlopen, pause or time.sleep
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=%d-%d" % (start, end)})
    for k in range(tries):
        try:
            with opener(req, 300) as resp:
                if resp.status != 206:
                    raise RangeUnsupported("HTTP %d" % resp.status)
                return resp.read()
        except RangeUnsupported:
            raise
        except Exception:
            if k + 1 == tries:
                raise
            pause(5 * (k + 1))
    return b""


class RangeFile:
    """A read-only, seekable file over range reads fetch(url, start, end), one cached block at a time,
    so zipfile can read the central directory and single members without the whole archive."""

    def __init__(self, url, size, fetch, block=BLOCK):
        self.url, self.size, self.fetch, self.block = url, size, fetch, block
        self.pos, self.buf_start, self.buf = 0, 0, b""
        self.requests, self.bytes = 0, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.pos, 2: self.size}[whence]
        if base + offset < 0:
            raise OSError("negative seek position")
        self.pos = base + offset
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        out = []
        while n > 0:
            if not self.buf_start <= self.pos < self.buf_start + len(self.buf):
                end = min(self.size, self.pos + max(n, self.block)) - 1
                self.buf = self.fetch(self.url, self.pos, end)
                self.buf_start = self.pos
                self.requests += 1
                self.bytes += len(self.buf)
                if not self.buf:
                    raise OSError("empty range answer at %d" % self.pos)
            off = self.pos - self.buf_start
            chunk = self.buf[off:off + n]
            out.append(chunk)
            self.pos += len(chunk)
            n -= len(chunk)
        return b"".join(out)

    def close(self):
        pass


def _listed_ok(size, listed):
    try:
        return kc.size_ok(size, listed)
    except (ValueError, KeyError):
        return False


def fill_package(p, cache_root, probe, fetch, block=BLOCK, allow_full=False, tmp_dir=None):
    """Cache one package's small members under cache_root/<package>/ like kc.fetch_package does.
    Returns its record; "via" is "range", "zip" or None, and "cached" is True if it was there."""
    pdir = os.path.join(cache_root, p["package"])
    rec_path = os.path.join(pdir, "record.json")
    if os.path.exists(rec_path):
        with open(rec_path, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("ok"):
            return {"ok": True, "cached": True, "via": old.get("via", "zip")}
    got, why = probe(kc.download_url(p["package"], p["name"]))
    if got is None:
        if allow_full:
            rec = kc.fetch_package(p, cache_root, tmp_dir or tempfile.gettempdir())
            rec["via"] = "zip"
            return rec
        return {"ok": False, "cached": False, "via": None, "range_unsupported": True, "error": why}
    url, size = got
    f = RangeFile(url, size, fetch, block)
    rec = {"ok": False, "cached": False, "via": "range", "size": size, "size_ok": _listed_ok(size, p["listed"]),
           "members": [], "kept": []}
    try:
        os.makedirs(pdir, exist_ok=True)
        with zipfile.ZipFile(f) as z:
            for i in z.infolist():
                if i.is_dir():
                    continue
                base, ext = os.path.basename(i.filename), kc.ext_of(i.filename)
                rec["members"].append({"name": i.filename, "bytes": i.file_size, "ext": ext})
                if ext in kc.KEEP_EXT and i.file_size <= kc.KEEP_MAX_BYTES and base not in rec["kept"]:
                    with z.open(i) as src, open(os.path.join(pdir, base), "wb") as dst:
                        shutil.copyfileobj(src, dst, kc.CHUNK)
                    rec["kept"].append(base)
        rec["ok"] = True
    except Exception as e:
        rec["error"] = repr(e)[:300]
    rec["requests"], rec["bytes_read"] = f.requests, f.bytes
    if rec["ok"]:
        with open(rec_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    return rec


def fill_whole(row, path, get=None, pause=None):
    """Download one small file whole to path unless it is there. Returns "cached", "ok" or an error."""
    if os.path.exists(path):
        return "cached"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = kc.download(kc.download_url(row["package"], row["name"]), path, get=get, pause=pause)
    return "ok" if d["ok"] else "error: " + str(d.get("error"))


def main(argv=None, probe=None, fetch=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-list", required=True)
    ap.add_argument("--descriptor-list", required=True)
    ap.add_argument("--clinical-list", required=True)
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out/fill")
    ap.add_argument("--budget-minutes", type=float, default=120)
    ap.add_argument("--allow-full", action="store_true")
    args = ap.parse_args(argv)
    probe = probe or http_probe
    fetch = fetch or (lambda url, start, end: http_range(url, start, end, pause=pause))
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "kpmp-census")
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="kpmp-fill-")
    order = kc.census_order(kc.load_packages(args.file_list))
    status, errors, bytes_read, requests = Counter(), [], 0, 0
    for p in order:
        if time.time() - t_start > args.budget_minutes * 60:
            status["not_attempted_budget"] += 1
            continue
        if status["range_unsupported"] >= RANGE_GIVE_UP and not status["filled_range"] and not args.allow_full:
            status["not_attempted_no_range"] += 1
            continue
        try:
            rec = fill_package(p, cache, probe, fetch, allow_full=args.allow_full, tmp_dir=tmp)
        except Exception as e:
            rec = {"ok": False, "via": None, "error": repr(e)[:300]}
        if rec.get("cached"):
            status["already_cached"] += 1
        elif rec.get("ok"):
            status["filled_" + str(rec.get("via"))] += 1
        elif rec.get("range_unsupported"):
            status["range_unsupported"] += 1
        else:
            status["failed"] += 1
        if not rec.get("ok") and len(errors) < 10:
            errors.append({"version": p["version"], "error": str(rec.get("error"))[:200]})
        bytes_read += rec.get("bytes_read") or 0
        requests += rec.get("requests") or 0
        if not rec.get("cached"):
            kc.log("%s %s ok=%s via=%s" % (p["version"], p["package"][:8], rec.get("ok"), rec.get("via")))
    shutil.rmtree(tmp, ignore_errors=True)
    whole = {}
    desc = k2.load_descriptor(args.descriptor_list)
    if len(desc) == 1:
        whole["tiv"] = fill_whole(desc[0], os.path.join(cache, "tiv", desc[0]["package"] + ".xlsx"), get, pause)
    clin = q2.load_clinical_list(args.clinical_list)
    if len(clin) == 1:
        whole["clinical"] = fill_whole(clin[0], os.path.join(cache, "clinical", clin[0]["package"] + ".csv"),
                                       get, pause)
    res = {"code_version": CODE_VERSION, "python": sys.version.split()[0],
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_start)),
           "listed": len(order), "status": dict(status), "range_bytes_read": bytes_read,
           "range_requests": requests, "whole_files": whole, "errors": errors,
           "minutes": round((time.time() - t_start) / 60, 1)}
    with open(os.path.join(args.out_dir, "fill.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("listed", "status", "range_bytes_read", "whole_files", "minutes")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
