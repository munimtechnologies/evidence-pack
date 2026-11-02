# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Variable inventory of the MEPS Full Year Consolidated public-use files, 2011-2024, from AHRQ's online
codebook pages (one page per file; allowed by meps.ahrq.gov/robots.txt, checked in code before each fetch).

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-inventory-prereg-v1-2026-11-02.md (evidence-pack). Lets a reader check whether
a file a publication names carries every variable a figure needs. Never downloads data files. Stdlib only.
Research information about published statistics, not medical advice.
"""
import argparse
import csv
import html
import json
import os
import re
import time
import urllib.request
import urllib.robotparser

VERSION = "0.1.0"

FILES = {"H147": 2011, "H155": 2012, "H163": 2013, "H171": 2014, "H181": 2015, "H192": 2016, "H201": 2017,
         "H209": 2018, "H216": 2019, "H224": 2020, "H233": 2021, "H243": 2022, "H251": 2023, "H256": 2024}
URL = "https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_codebook.jsp?PUFId=%s"
ROBOTS = "https://meps.ahrq.gov/robots.txt"
UA = "MV2-evidence-pack/inventory (mv2@munimtech.com)"

ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
VAR = re.compile(r"varName=([A-Za-z0-9_]+)")
TAG = re.compile(r"<[^>]+>")
MSA_DESC = re.compile(r"\b(MSA|METRO\w*)\b")
GEO_DESC = re.compile(r"\b(MSA|METRO\w*|CBSA|COUNTY|COUNTIES|FIPS|URBAN\w*|RURAL\w*|ZIP\w*|STATE|STATES)\b")

# Gate on HC-243: the Stata file read in check R1 had 1,420 variables.
H243_N = 1420
H243_HAS = ("SAQWT22F", "ADOSTP42", "REGION53", "PERWT22F")
H243_NOT = ("PSAQWT22F", "MSA22")


def clean(s):
    return " ".join(html.unescape(TAG.sub(" ", s)).split())


def parse(text):
    """List of {name, start, end, description} from a codebook variable-list page."""
    out = []
    seen = set()
    for row in ROW.findall(text):
        m = VAR.search(row)
        if not m:
            continue
        name = m.group(1).upper()
        if name in seen:
            continue
        seen.add(name)
        cells = [clean(c) for c in CELL.findall(row)]
        rec = {"name": name, "start": None, "end": None, "description": ""}
        if len(cells) >= 4:
            rec["start"], rec["end"], rec["description"] = cells[1], cells[2], cells[3]
        out.append(rec)
    if not out:  # fallback: names only
        for m in VAR.finditer(text):
            name = m.group(1).upper()
            if name not in seen:
                seen.add(name)
                out.append({"name": name, "start": None, "end": None, "description": ""})
    return out


def is_msa(rec):
    n = rec["name"]
    return n.startswith("MSA") or "METRO" in n or bool(MSA_DESC.search(rec["description"].upper()))


def is_geo(rec):
    return is_msa(rec) or bool(GEO_DESC.search(rec["description"].upper()))


def controls(fid, names):
    """Positive controls present in every FYC file: PERWTyyF, REGIONyy, VARSTR, VARPSU."""
    yy = "%02d" % (FILES[fid] % 100)
    want = ["PERWT%sF" % yy, "REGION%s" % yy, "VARSTR", "VARPSU"]
    return {w: (w in names) for w in want}


def gate(inv):
    recs = inv.get("H243") or []
    names = set(r["name"] for r in recs)
    ok = (len(recs) == H243_N and all(h in names for h in H243_HAS) and not any(h in names for h in H243_NOT))
    return {"passed": ok, "n": len(recs), "has": {h: h in names for h in H243_HAS},
            "not": {h: h in names for h in H243_NOT}}


def grade(inv):
    msa = {fid: [r["name"] for r in recs if is_msa(r)] for fid, recs in inv.items()}
    late = [fid for fid in inv if FILES[fid] >= 2013 and inv[fid]]  # "read" = at least one variable parsed
    early = [fid for fid in ("H147", "H155") if inv.get(fid)]
    g = {"msa_by_file": msa}
    g["P1"] = {"grade": "held" if late and all(not msa[f] for f in late) and len(late) == 12 else "failed",
               "files_2013_2024_read": len(late), "with_msa": [f for f in late if msa[f]]}
    g["P2"] = {"grade": "held" if len(early) == 2 and all(msa[f] for f in early) else "failed",
               "files_2011_2012_read": len(early)}
    return g


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as f:
        return f.read().decode("utf-8", errors="replace")


def build(get=None, pause=None, allowed=None, delay=10):
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(get(ROBOTS).splitlines())
        rp.modified()
        allowed = lambda u: rp.can_fetch(UA, u)  # noqa: E731
    inv, errors = {}, {}
    for i, fid in enumerate(FILES):
        url = URL % fid
        if not allowed(url):
            errors[fid] = "disallowed by robots.txt"
            continue
        if i:
            pause(delay)
        try:
            inv[fid] = parse(get(url))
        except Exception as e:  # noqa: BLE001
            errors[fid] = "%s: %s" % (type(e).__name__, e)
    return inv, errors


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    d = os.path.join(a.out_dir, "inventory")
    os.makedirs(d, exist_ok=True)
    out = {"version": VERSION, "error": None}
    try:
        inv, errors = build(get=get, pause=pause, allowed=allowed)
        out["errors"] = errors
        out["n_by_file"] = {fid: len(recs) for fid, recs in inv.items()}
        out["controls"] = {fid: controls(fid, set(r["name"] for r in recs)) for fid, recs in inv.items()}
        out["gate"] = gate(inv)
        out["grades"] = grade(inv)
        geo = []
        for fid, recs in inv.items():
            with open(os.path.join(d, "%s.csv" % fid), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["file", "data_year", "name", "start", "end", "description"])
                for r in recs:
                    w.writerow([fid, FILES[fid], r["name"], r["start"], r["end"], r["description"]])
                    if is_geo(r):
                        geo.append([fid, FILES[fid], r["name"], r["description"], is_msa(r)])
        with open(os.path.join(a.out_dir, "geo-candidates.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "data_year", "name", "description", "msa_rule"])
            w.writerows(geo)
        out["geo_candidates"] = len(geo)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "inventory.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out.get(k) for k in ("n_by_file", "errors", "gate", "error")}, indent=1))
    print(json.dumps({k: v for k, v in (out.get("grades") or {}).items() if k != "msa_by_file"}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
