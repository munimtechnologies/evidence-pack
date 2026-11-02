# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check R2, step 1: draw 5 MEPS Statistical Briefs at random for reproduction from their named public file.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-r2-prereg-v1-2026-11-02.md (evidence-pack). The eligible set comes from census
M1 (findings/meps-census-v1/briefs.csv). The seed comes from a public random value that did not exist when the
pre-registration was published: the NIST Randomness Beacon (chain 2) pulse stamped 2026-11-02T10:00:00.000Z.
Stdlib only. Research information about published statistics, not medical advice.
"""
import argparse
import csv
import json
import os
import random
import time
import urllib.request

VERSION = "0.1.0"

# Full Year Consolidated public-use files, 2013-2024 (MEPS data-file search, read 2026-11-02).
FYC = {"H163": 2013, "H171": 2014, "H181": 2015, "H192": 2016, "H201": 2017, "H209": 2018, "H216": 2019,
       "H224": 2020, "H233": 2021, "H243": 2022, "H251": 2023, "H256": 2024}
MIN_YEAR = 2016
EXCLUDE = {569}  # already reproduced in check R1
K = 5
PULSE_MS = 1793613600000
PULSE_ISO = "2026-11-02T10:00:00.000Z"
BEACON = "https://beacon.nist.gov/beacon/2.0/pulse/time/%d"


def eligible(rows):
    """Sorted list of (brief number, file id) meeting the pre-registered rule."""
    out = []
    for r in rows:
        try:
            num, year, n_ids = int(r["number"]), int(r["year"]), int(r["n_ids"])
        except (KeyError, ValueError):
            continue
        fid = (r.get("file_ids") or "").strip()
        if (r.get("status") == "ok" and r.get("cls") == "PUF" and n_ids == 1 and year >= MIN_YEAR
                and fid in FYC and num not in EXCLUDE):
            out.append((num, fid))
    return sorted(out)


def seed_from(output_value):
    """First 16 hex digits of the pulse's outputValue as an integer."""
    h = output_value.strip()[:16]
    if len(h) != 16:
        raise ValueError("outputValue too short")
    return int(h, 16)


def draw(numbers, seed, k=K):
    """Draw order matters only for the record; the sample is the set."""
    return random.Random(seed).sample(sorted(numbers), k)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MV2-evidence-pack/r2-draw (mv2@munimtech.com)"})
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.loads(f.read().decode("utf-8"))


def fetch_pulse(get=None, pause=None, tries=40, wait=300):
    """Poll until the pre-registered pulse exists; accept it only if its timeStamp matches exactly."""
    get = get or _get
    pause = pause or time.sleep
    last = None
    for i in range(tries):
        try:
            p = get(BEACON % PULSE_MS).get("pulse", {})
            if p.get("timeStamp") == PULSE_ISO and p.get("outputValue"):
                return {k: p.get(k) for k in ("uri", "chainIndex", "pulseIndex", "timeStamp", "outputValue")}
            last = "timeStamp %r" % p.get("timeStamp")
        except Exception as e:  # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, e)
        if i < tries - 1:
            pause(wait)
    raise RuntimeError("pulse %s not available: %s" % (PULSE_ISO, last))


def main(argv=None, get=None, pause=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefs", default="/work/briefs.csv")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "error": None}
    try:
        with open(a.briefs, newline="", encoding="utf-8") as f:
            el = eligible(csv.DictReader(f))
        out["eligible"] = [{"number": n, "file": fid, "data_year": FYC[fid]} for n, fid in el]
        out["n_eligible"] = len(el)
        pulse = fetch_pulse(get=get, pause=pause)
        out["pulse"] = pulse
        seed = seed_from(pulse["outputValue"])
        out["seed"] = seed
        files = dict(el)
        sample = draw([n for n, _ in el], seed)
        out["sample"] = [{"order": i + 1, "number": n, "file": files[n], "data_year": FYC[files[n]],
                          "url": "https://meps.ahrq.gov/data_files/publications/st%d/stat%d.shtml" % (n, n)}
                         for i, n in enumerate(sample)]
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "r2-draw.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"n_eligible": out.get("n_eligible"), "sample": out.get("sample"),
                      "error": out["error"]}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
