#!/usr/bin/env python3
# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""zip_range: list a remote ZIP (ZIP64 too) and extract chosen members with HTTP Range requests only.

MV2 of Munim, Inc. Made with AI agents (Claude) working in MV2's name. Standard library only.
Part of the kidney-glom-check skill: it fetches only the HuBMAP Deepflash2 kidney weights (about 300 MB) from the
16.5 GB trained_models.zip of Zenodo record 7730028.
Use: python zip_range.py --url <zip url> --out-dir <log dir> [--prefix models/x/ --dest <folder>]
It never downloads the whole archive: if the server ignores Range (answers 200), it stops at once.
Each extracted member is checked against the CRC-32 in the archive's central directory.
"""
import argparse
import csv
import json
import os
import struct
import time
import urllib.request
import zlib

UA = "MV2-Munim-research/1.0 (mv2@munimtech.com)"
CHUNK = 8 * 1024 * 1024


class FileSource:
    """Range reads from a local file (tests)."""

    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(path)

    def get(self, start, length):
        with open(self.path, "rb") as f:
            f.seek(start)
            return f.read(length)


class HttpSource:
    """Range reads over HTTP; refuses a server that does not honour Range."""

    def __init__(self, url, tries=4):
        self.url, self.tries = url, tries
        self.requests = 0
        self.bytes = 0
        self.size = None
        self._fetch("bytes=-22")
        if self.size is None:
            raise RuntimeError("no Content-Range total")

    def _fetch(self, rng):
        last = None
        for i in range(self.tries):
            try:
                req = urllib.request.Request(self.url, headers={"Range": rng, "User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    if r.status != 206:
                        raise RuntimeError("server answered %s, not 206: Range not honoured; stopping" % r.status)
                    cr = r.headers.get("Content-Range", "")
                    if "/" in cr and cr.split("/")[-1].strip().isdigit():
                        self.size = int(cr.split("/")[-1])
                    data = r.read()
                self.requests += 1
                self.bytes += len(data)
                return data
            except RuntimeError:
                raise
            except Exception as e:  # network hiccup: retry
                last = e
                time.sleep(5 * (i + 1))
        raise RuntimeError("range %s failed: %r" % (rng, last))

    def get(self, start, length):
        return self._fetch("bytes=%d-%d" % (start, start + length - 1))


def find_eocd(src):
    """(entries, cd_size, cd_offset, zip64) from the end of the archive."""
    n = min(src.size, 65557)
    tail = src.get(src.size - n, n)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise ValueError("no end-of-central-directory record")
    _, _, _, _, entries, cd_size, cd_off, _ = struct.unpack("<4s4H2IH", tail[i:i + 22])
    if entries == 0xFFFF or cd_size == 0xFFFFFFFF or cd_off == 0xFFFFFFFF:
        loc = tail[i - 20:i]
        if loc[:4] != b"PK\x06\x07":
            raise ValueError("ZIP64 locator missing")
        z64_off = struct.unpack("<Q", loc[8:16])[0]
        rec = src.get(z64_off, 56)
        if rec[:4] != b"PK\x06\x06":
            raise ValueError("ZIP64 end record missing")
        entries, cd_size, cd_off = struct.unpack("<3Q", rec[32:56])
        return entries, cd_size, cd_off, True
    return entries, cd_size, cd_off, False


def parse_cd(buf):
    """Central-directory entries: dicts name, method, crc, csize, usize, offset."""
    out, p = [], 0
    while p + 46 <= len(buf) and buf[p:p + 4] == b"PK\x01\x02":
        (_, _, _, flags, method, _, _, crc, csize, usize, nlen, xlen, clen, _, _, _,
         off) = struct.unpack("<4s6H3I5H2I", buf[p:p + 46])
        name = buf[p + 46:p + 46 + nlen].decode("utf-8" if flags & 0x800 else "cp437")
        extra = buf[p + 46 + nlen:p + 46 + nlen + xlen]
        q = 0
        while q + 4 <= len(extra):
            hid, hlen = struct.unpack("<2H", extra[q:q + 4])
            if hid == 0x0001:
                vals, r = extra[q + 4:q + 4 + hlen], 0
                if usize == 0xFFFFFFFF:
                    usize = struct.unpack("<Q", vals[r:r + 8])[0]
                    r += 8
                if csize == 0xFFFFFFFF:
                    csize = struct.unpack("<Q", vals[r:r + 8])[0]
                    r += 8
                if off == 0xFFFFFFFF:
                    off = struct.unpack("<Q", vals[r:r + 8])[0]
            q += 4 + hlen
        out.append({"name": name, "method": method, "crc": crc, "csize": csize, "usize": usize, "offset": off})
        p += 46 + nlen + xlen + clen
    return out


def listing(src):
    entries, cd_size, cd_off, z64 = find_eocd(src)
    members = parse_cd(src.get(cd_off, cd_size))
    if len(members) != entries:
        raise ValueError("central directory has %d entries, end record says %d" % (len(members), entries))
    return members, z64


def extract(src, m, dest_path):
    """Stream one member to dest_path; returns (bytes written, crc ok)."""
    if m["method"] not in (0, 8):
        raise ValueError("unsupported method %d for %s" % (m["method"], m["name"]))
    hdr = src.get(m["offset"], 30)
    if hdr[:4] != b"PK\x03\x04":
        raise ValueError("bad local header for %s" % m["name"])
    nlen, xlen = struct.unpack("<2H", hdr[26:30])
    start = m["offset"] + 30 + nlen + xlen
    dec = zlib.decompressobj(-15) if m["method"] == 8 else None
    crc, written, done = 0, 0, 0
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    tmp = dest_path + ".part"
    with open(tmp, "wb") as f:
        while done < m["csize"]:
            n = min(CHUNK, m["csize"] - done)
            data = src.get(start + done, n)
            if len(data) != n:
                raise ValueError("short read for %s" % m["name"])
            done += n
            if dec is not None:
                data = dec.decompress(data)
            crc = zlib.crc32(data, crc)
            written += len(data)
            f.write(data)
        if dec is not None:
            data = dec.flush()
            crc = zlib.crc32(data, crc)
            written += len(data)
            f.write(data)
    ok = (crc & 0xFFFFFFFF) == m["crc"] and written == m["usize"]
    if ok:
        os.replace(tmp, dest_path)
    return written, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="List a remote ZIP and extract chosen members with HTTP Range requests.")
    ap.add_argument("--url")
    ap.add_argument("--file", help="local zip instead of --url (tests)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--dest", default="")
    ap.add_argument("--max-bytes", type=int, default=600 * 1024 * 1024)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    src = FileSource(a.file) if a.file else HttpSource(a.url)
    members, z64 = listing(src)
    with open(os.path.join(a.out_dir, "listing.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "method", "csize", "usize", "crc32"])
        for m in members:
            w.writerow([m["name"], m["method"], m["csize"], m["usize"], "%08x" % m["crc"]])
    report = {"archive_bytes": src.size, "zip64": z64, "members": len(members),
              "files": sum(1 for m in members if not m["name"].endswith("/")), "extracted": []}
    if a.prefix and a.dest:
        pick = [m for m in members if m["name"].startswith(a.prefix) and not m["name"].endswith("/")]
        total = sum(m["csize"] for m in pick)
        report["selected"], report["selected_bytes"] = len(pick), total
        if total > a.max_bytes:
            raise SystemExit("selection is %d bytes, over --max-bytes %d" % (total, a.max_bytes))
        for m in pick:
            path = os.path.join(a.dest, m["name"])
            if os.path.exists(path) and os.path.getsize(path) == m["usize"]:
                report["extracted"].append({"name": m["name"], "bytes": m["usize"], "crc_ok": None, "cached": True})
                continue
            n, ok = extract(src, m, path)
            report["extracted"].append({"name": m["name"], "bytes": n, "crc_ok": ok, "cached": False})
    report["http_requests"] = getattr(src, "requests", 0)
    report["http_bytes"] = getattr(src, "bytes", 0)
    with open(os.path.join(a.out_dir, "extract.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "extracted"}, indent=1))
    bad = [e for e in report["extracted"] if e["crc_ok"] is False]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
