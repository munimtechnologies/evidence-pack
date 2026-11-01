# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M2: which MEPS Household Component Statistical Briefs report results by metropolitan (MSA)
status, and on which data years, given that the public Full Year Consolidated files stopped carrying
the MSA variable after 2012.

Pre-registered in findings/meps-geo-prereg-v1-2026-11-01.md (evidence-pack).
MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name. Standard library only.
Reads only public web pages that meps.ahrq.gov/robots.txt does not disallow (brief .shtml pages and
codebook .jsp pages) plus MV2's own briefs.csv from GitHub. Research information, not medical advice.

Usage: python -m meps.meps_geo --out-dir out
"""
import argparse
import collections
import csv
import hashlib
import html.parser
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

VERSION = "0.1.0"
BASE = "https://meps.ahrq.gov"
BRIEFS_URL = ("https://raw.githubusercontent.com/munimtechnologies/evidence-pack/v0.9.33/"
              "findings/meps-census-v1/briefs.csv")
BRIEF_URL = BASE + "/data_files/publications/st{n}/stat{n}.shtml"
CODEBOOK_URL = BASE + "/mepsweb/data_stats/download_data_files_codebook.jsp?PUFId={puf}&varName={var}"
UA = "MV2-Munim-meps-geo/" + VERSION + " (mailto:mv2@munimtech.com)"
NBSP = chr(160)
HC = ("PUF", "NONPUBLIC", "NOID")
BOILERPLATE_SHARE = 0.5
MAX_SNIPPETS = 8
SNIPPET_CHARS = 300

# Full Year Consolidated file number -> data year (MEPS PUF search, read 2026-11-01).
FYC = {"H12": 1996, "H20": 1997, "H28": 1998, "H38": 1999, "H50": 2000, "H60": 2001, "H70": 2002,
       "H79": 2003, "H89": 2004, "H97": 2005, "H105": 2006, "H113": 2007, "H121": 2008, "H129": 2009,
       "H138": 2010, "H147": 2011, "H155": 2012, "H163": 2013, "H171": 2014, "H181": 2015, "H192": 2016,
       "H201": 2017, "H209": 2018, "H216": 2019, "H224": 2020, "H233": 2021, "H243": 2022, "H251": 2023,
       "H256": 2024}
CUTOFF = 2013          # first data year without MSA on the public FYC file (hand check, 2026-11-01)
CODEBOOK_YEARS = list(range(2011, 2025))
CONTROL_BRIEFS = (569, 549)

BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "tr", "td", "th",
         "table", "section", "article", "header", "footer", "blockquote", "dt", "dd", "caption", "title"}

MSA_RX = [re.compile(r"\b(?:non-?)?MSAs?\b"), re.compile(r"\b(?:non-?)?metropolitan\b", re.I)]
UR_RX = [re.compile(r"\b(?:urban|rural)\b", re.I)]


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_lines(page):
    """Visible text of an HTML page, one non-empty line per block."""
    p = _Text()
    p.feed(page)
    p.close()
    text = "".join(p.parts).replace(NBSP, " ")
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]


def fyc_years(file_ids):
    """Data years of the Full Year Consolidated files among a space-separated ID list."""
    return sorted(set(FYC[i] for i in (file_ids or "").split() if i in FYC))


def anchor(file_ids):
    """'post' if any named FYC is from CUTOFF on, 'pre' if FYCs are named but all earlier, else 'none'."""
    ys = fyc_years(file_ids)
    if not ys:
        return "none"
    return "post" if max(ys) >= CUTOFF else "pre"


def hits(lines, rxs):
    """Lines matching any regex."""
    return [ln for ln in lines if any(rx.search(ln) for rx in rxs)]


def boilerplate(pages_lines, share=BOILERPLATE_SHARE):
    """Lines that appear on at least `share` of pages (site navigation and footers)."""
    c = collections.Counter()
    for lines in pages_lines:
        c.update(set(lines))
    k = len(pages_lines)
    if k == 0:
        return set()
    return set(ln for ln, v in c.items() if v / k >= share)


def codebook_status(page):
    """'present' if the MSA value label is on the codebook page, 'absent' if the page is a codebook page
    without it, 'unknown' otherwise."""
    lines = html_lines(page)
    if any("NON-MSA" in ln for ln in lines):
        return "present"
    if any("CODEBOOK" in ln.upper() for ln in lines):
        return "absent"
    return "unknown"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            cs = r.headers.get_content_charset() or "utf-8"
            try:
                return r.status, raw.decode(cs, errors="replace")
            except LookupError:
                return r.status, raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def fetch(url, get=None, pause=None, tries=3):
    """('ok', body), ('404', '') or (error status, '') after `tries` attempts."""
    get = get or _get
    pause = pause or time.sleep
    status = "error"
    for k in range(tries):
        try:
            code, body = get(url)
        except Exception:  # noqa: BLE001
            code, body = None, ""
        if code == 200:
            return "ok", body
        if code == 404:
            return "404", ""
        status = "http%s" % code if code else "error"
        pause(5 * (k + 1))
    return status, ""


def read_briefs(text):
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        out.append({"number": int(r["number"]), "year": int(r["year"]) if r.get("year") else None,
                    "cls": r.get("cls", ""), "file_ids": r.get("file_ids", ""), "url": r.get("url", "")})
    return out


def grade(rows, codebook):
    """Automatic grades for P2-P4. P1 is graded by hand from candidates (post-anchored PUF, MSA hit)."""
    g = {}
    by_n = {r["number"]: r for r in rows}
    ctl = {n: (by_n[n]["msa_hits"] > 0 if n in by_n and by_n[n]["status"] == "ok" else None)
           for n in CONTROL_BRIEFS}
    if any(v is None for v in ctl.values()):
        g["P2"] = {"grade": "untestable", "controls": ctl}
    else:
        g["P2"] = {"grade": "held" if all(ctl.values()) else "failed", "controls": ctl}
    st = {y: codebook.get(y, {}).get("status") for y in range(2011, 2024)}
    if any(v not in ("present", "absent") for v in st.values()):
        g["P3"] = {"grade": "untestable", "status": st}
    else:
        ok = st[2011] == "present" and st[2012] == "present" and all(
            st[y] == "absent" for y in range(2013, 2024))
        g["P3"] = {"grade": "held" if ok else "failed", "status": st}
    puf = [r for r in rows if r["cls"] == "PUF" and r["status"] == "ok"]
    post = [r for r in puf if r["anchor"] == "post"]
    pre = [r for r in puf if r["anchor"] == "pre"]
    p4 = {"n_post": len(post), "n_pre": len(pre)}
    if len(post) >= 10 and len(pre) >= 10:
        sp = sum(1 for r in post if r["msa_hits"] > 0) / len(post)
        sr = sum(1 for r in pre if r["msa_hits"] > 0) / len(pre)
        p4.update(share_post=round(sp, 4), share_pre=round(sr, 4), grade="held" if sp < sr else "failed")
    else:
        p4["grade"] = "untestable"
    g["P4"] = p4
    cands = sorted(r["number"] for r in post if r["msa_hits"] > 0)
    g["P1_candidates"] = cands
    g["P1"] = {"grade": "hand", "candidates": len(cands),
               "rule": "held if >= 3 candidates (including 569) are confirmed by hand to show an estimate "
                       "for an MSA/non-MSA (metropolitan/nonmetropolitan) group for a data year >= 2013"}
    return g


def run(out_dir, get=None, pause=None, delay=2.0, briefs_text=None):
    pause = pause or time.sleep
    out = {"version": VERSION, "cutoff": CUTOFF, "error": None}
    if briefs_text is None:
        st, briefs_text = fetch(BRIEFS_URL, get, pause)
        if st != "ok":
            raise RuntimeError("briefs.csv: %s" % st)
    out["briefs_csv"] = {"url": BRIEFS_URL, "sha256": hashlib.sha256(briefs_text.encode("utf-8")).hexdigest()}
    briefs = [b for b in read_briefs(briefs_text) if b["cls"] in HC]

    codebook = {}
    for y in CODEBOOK_YEARS:
        puf = [k for k, v in FYC.items() if v == y][0]
        var = "MSA%02d" % (y % 100)
        url = CODEBOOK_URL.format(puf=puf, var=var)
        st, page = fetch(url, get, pause)
        pause(delay)
        codebook[y] = {"puf": puf, "var": var, "fetch": st,
                       "status": codebook_status(page) if st == "ok" else "unknown"}

    pages = {}
    for b in briefs:
        st, page = fetch(BRIEF_URL.format(n=b["number"]), get, pause)
        pause(delay)
        pages[b["number"]] = (st, html_lines(page) if st == "ok" else [])
    bp = boilerplate([v[1] for v in pages.values() if v[0] == "ok"])

    rows, snippets = [], []
    for b in briefs:
        st, lines = pages[b["number"]]
        body = [ln for ln in lines if ln not in bp]
        mh = hits(body, MSA_RX)
        uh = hits(body, UR_RX)
        r = {"number": b["number"], "year": b["year"], "cls": b["cls"], "file_ids": b["file_ids"],
             "fyc_years": " ".join(str(y) for y in fyc_years(b["file_ids"])), "anchor": anchor(b["file_ids"]),
             "status": st, "msa_hits": len(mh), "ur_hits": len(uh), "url": BRIEF_URL.format(n=b["number"])}
        rows.append(r)
        if mh or uh:
            snippets.append({"number": b["number"], "anchor": r["anchor"], "cls": b["cls"],
                             "msa": [ln[:SNIPPET_CHARS] for ln in mh[:MAX_SNIPPETS]],
                             "urban_rural": [ln[:SNIPPET_CHARS] for ln in uh[:MAX_SNIPPETS]]})

    os.makedirs(out_dir, exist_ok=True)
    fields = ["number", "year", "cls", "file_ids", "fyc_years", "anchor", "status", "msa_hits", "ur_hits", "url"]
    with open(os.path.join(out_dir, "geo-briefs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_dir, "snippets.jsonl"), "w", encoding="utf-8") as f:
        for s in snippets:
            f.write(json.dumps(s, ensure_ascii=True) + "\n")
    tab = collections.Counter((r["cls"], r["anchor"], r["msa_hits"] > 0) for r in rows if r["status"] == "ok")
    out.update({
        "n_hc_briefs": len(briefs),
        "n_fetched": sum(1 for r in rows if r["status"] == "ok"),
        "n_boilerplate_lines": len(bp),
        "boilerplate_msa_lines": sorted(ln for ln in bp if any(rx.search(ln) for rx in MSA_RX + UR_RX)),
        "codebook": {str(k): v for k, v in codebook.items()},
        "table": [{"cls": k[0], "anchor": k[1], "msa_hit": k[2], "briefs": v} for k, v in sorted(tab.items())],
        "grades": grade(rows, codebook),
    })
    with open(os.path.join(out_dir, "geo.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args(argv)
    try:
        out = run(a.out_dir, delay=a.delay)
    except Exception as e:  # noqa: BLE001
        os.makedirs(a.out_dir, exist_ok=True)
        out = {"version": VERSION, "error": "%s: %s" % (type(e).__name__, e)}
        with open(os.path.join(a.out_dir, "geo.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
    print(json.dumps({k: out.get(k) for k in ("error", "n_hc_briefs", "n_fetched", "codebook", "grades")},
                     indent=1))
    return 0 if out.get("error") is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
