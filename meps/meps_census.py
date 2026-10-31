# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census of AHRQ MEPS Statistical Briefs: which data files each brief's
Data Source section names, and whether it says it used non-public data.

Pre-registered in findings/meps-census-prereg-v1-2026-10-31.md (census M1).
Made by AI agents (Claude) working in MV2's name, MV2 of Munim, Inc.
Standard library only.

Usage: python -m meps.meps_census --out-dir out
"""
import argparse
import collections
import csv
import html.parser
import json
import os
import random
import re
import time
import urllib.error
import urllib.request

VERSION = "0.1.0"
BASE = "https://meps.ahrq.gov"
LIST_URL = BASE + "/data_stats/Pub_ProdLookup_Results.jsp?ProductType=Statistical+Brief&startAt={start}"
BRIEF_URL = BASE + "/data_files/publications/st{n}/stat{n}.shtml"
UA = "MV2-Munim-meps-census/" + VERSION + " (mailto:mv2@munimtech.com)"
SEED = 20261031
SAMPLE = 20
MAX_SECTION = 8000
NBSP = chr(160)

BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "tr", "td", "th",
         "table", "section", "article", "header", "footer", "blockquote", "dt", "dd", "caption", "title"}

DS_HEAD = re.compile(r"^Data Sources?\b", re.I)
DS_INLINE = re.compile(r"^Data Sources?\s*[:.]\s*(.+)$", re.I)
STOP_HEAD = re.compile(r"^(Definitions?|About MEPS|References|Suggested [Cc]itation|Footnotes?|Notes?|"
                       r"Technical [Nn]otes?|Methods?|Acknowledg|Glossary|For [Mm]ore [Ii]nformation)\b")
FILE_ID = re.compile(r"\bHC[- ]?\d{2,3}[A-Z]{0,3}\d?\b|\bH\d{2,3}[A-Z]{0,3}\d?\b")
IC = re.compile(r"MEPS[- ]IC\b|Insurance Component", re.I)
NONPUBLIC = [
    ("internal", r"\binternal\b"),
    ("confidential", r"\bconfidential\b"),
    ("restricted", r"\brestricted\b"),
    ("data_center", r"\bdata cent(?:er|re)s?\b"),
    ("special_computation", r"\bspecial (?:computation|tabulation)s?\b"),
    ("not_public", r"\bnot (?:publicly|publically) (?:available|released)\b|\bnon-?public\b"),
    ("model", r"\bKIDSIM\b|\bsimulation model\b|\bmicrosimulation\b"),
]
MONTH_YEAR = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|"
                        r"November|December),? ((?:19|20)\d\d)\b")
LIST_ROW = re.compile(r"publications/st(\d+)/stat\1\.(?:shtml|pdf)", re.I)
LIST_TOTAL = re.compile(r"\b\d+\s+to\s+\d+\s+of\s+(\d+)\b")
CLASSES = ["NOPAGE", "NOSECTION", "IC", "NONPUBLIC", "PUF", "NOID"]
HC = ("PUF", "NONPUBLIC", "NOID")


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


def data_source_section(lines):
    """Text of the Data Source section, or None if the page has none."""
    start, first = None, ""
    for i, ln in enumerate(lines):
        if DS_HEAD.match(ln) and len(ln) <= 40:
            start = i + 1
            break
    if start is None:
        for i, ln in enumerate(lines):
            m = DS_INLINE.match(ln)
            if m:
                start, first = i + 1, m.group(1)
                break
    if start is None:
        return None
    out = [first] if first else []
    for ln in lines[start:]:
        if len(ln) <= 60 and STOP_HEAD.match(ln):
            break
        out.append(ln)
    return " ".join(out)[:MAX_SECTION]


def norm_id(s):
    m = re.match(r"HC?[- ]?(\d+)(.*)$", s)
    return "H%d%s" % (int(m.group(1)), m.group(2))


def classify(section):
    """(class, file IDs, marker names) for one Data Source section."""
    if section is None:
        return "NOSECTION", [], []
    ids = sorted(set(norm_id(m.group(0)) for m in FILE_ID.finditer(section)))
    markers = [name for name, rx in NONPUBLIC if re.search(rx, section, re.I)]
    if IC.search(section) and not ids:
        return "IC", ids, markers
    if markers:
        return "NONPUBLIC", ids, markers
    if ids:
        return "PUF", ids, markers
    return "NOID", ids, markers


def brief_year(lines):
    """Year of the first 'Month YYYY' before the Highlights heading (or in the first 60 lines)."""
    head = lines[:60]
    for i, ln in enumerate(lines):
        if re.match(r"^Highlights\b", ln):
            head = lines[:i]
            break
    for ln in head:
        m = MONTH_YEAR.search(ln)
        if m:
            return int(m.group(1))
    return None


def parse_listing(page):
    """{brief number: year on its listing row or None} for one results page."""
    out = {}
    for seg in re.split(r"Pub_ProdResults_Details\.jsp", page)[1:]:
        m = LIST_ROW.search(seg)
        if not m:
            continue
        y = re.search(r">\s*((?:19|20)\d\d)\s*<", seg)
        out.setdefault(int(m.group(1)), int(y.group(1)) if y else None)
    return out


def parse_total(page):
    m = LIST_TOTAL.search(page)
    return int(m.group(1)) if m else None


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
        except Exception:
            code, body = None, ""
        if code == 200:
            return "ok", body
        if code == 404:
            return "404", ""
        status = "http%s" % code if code else "error"
        pause(5 * (k + 1))
    return status, ""


def _g(value, ok):
    return {"value": round(value, 4), "grade": "held" if ok else "failed"}


def grade(rows, total_listed):
    """Grades P1-P5 exactly as pre-registered."""
    c = collections.Counter(r["cls"] for r in rows)
    found = sum(v for k, v in c.items() if k not in ("NOPAGE", "NOSECTION"))
    hc = [r for r in rows if r["cls"] in HC]
    g = {}
    if total_listed:
        v = found / total_listed
        g["P1"] = _g(v, v >= 0.90)
    else:
        g["P1"] = {"grade": "untestable", "reason": "no listing total"}
    if hc:
        v = sum(1 for r in hc if r["n_ids"] > 0) / len(hc)
        g["P2"] = _g(v, v >= 0.80)
        v = sum(1 for r in hc if r["cls"] == "NONPUBLIC") / len(hc)
        g["P3"] = _g(v, 0.05 <= v <= 0.40)
    else:
        g["P2"] = g["P3"] = {"grade": "untestable", "reason": "no HC briefs"}
    new = [r for r in hc if r["year"] and r["year"] >= 2016]
    old = [r for r in hc if r["year"] and r["year"] <= 2015]
    p4 = {"n_2016_on": len(new), "n_to_2015": len(old)}
    if len(new) >= 30 and len(old) >= 30:
        vn = sum(1 for r in new if r["cls"] == "NONPUBLIC") / len(new)
        vo = sum(1 for r in old if r["cls"] == "NONPUBLIC") / len(old)
        p4.update(value_2016_on=round(vn, 4), value_to_2015=round(vo, 4), grade="held" if vn > vo else "failed")
    else:
        p4["grade"] = "untestable"
    g["P4"] = p4
    if found:
        v = c["IC"] / found
        g["P5"] = _g(v, 0.10 <= v <= 0.30)
    else:
        g["P5"] = {"grade": "untestable", "reason": "no sections"}
    return g


def _period(year):
    if not year:
        return "unknown"
    return ">=2016" if year >= 2016 else "<=2015"


def run(out_dir, get=None, pause=None, delay=2.0, max_number=600, min_listing=100):
    pause = pause or time.sleep
    listed, total, start = {}, None, 1
    while start <= 2000:
        st, page = fetch(LIST_URL.format(start=start), get, pause)
        pause(delay)
        if st != "ok":
            break
        total = total or parse_total(page)
        got = parse_listing(page)
        new = [n for n in got if n not in listed]
        for n in got:
            listed.setdefault(n, got[n])
        if not new:
            break
        start += 100
    in_listing = set(listed)
    frame = "listing"
    if len(listed) < min_listing or (total and len(listed) < 0.9 * total):
        frame = "listing+probe"
        for n in range(1, max_number + 1):
            listed.setdefault(n, None)

    rows, sections = [], []
    for n in sorted(listed):
        url = BRIEF_URL.format(n=n)
        st, page = fetch(url, get, pause)
        pause(delay)
        if st != "ok":
            if n in in_listing or st != "404":
                rows.append({"number": n, "year": listed[n], "year_source": "listing" if listed[n] else "",
                             "status": st, "cls": "NOPAGE", "n_ids": 0, "file_ids": "", "markers": "",
                             "section_chars": 0, "in_listing": n in in_listing, "url": url})
            continue
        lines = html_lines(page)
        section = data_source_section(lines)
        cls, ids, markers = classify(section)
        year, ysrc = brief_year(lines), "page"
        if year is None:
            year, ysrc = listed[n], ("listing" if listed[n] else "")
        rows.append({"number": n, "year": year, "year_source": ysrc, "status": st, "cls": cls,
                     "n_ids": len(ids), "file_ids": " ".join(ids), "markers": " ".join(markers),
                     "section_chars": len(section or ""), "in_listing": n in in_listing, "url": url})
        sections.append({"number": n, "section": section})

    os.makedirs(out_dir, exist_ok=True)
    fields = ["number", "year", "year_source", "status", "cls", "n_ids", "file_ids", "markers",
              "section_chars", "in_listing", "url"]
    with open(os.path.join(out_dir, "briefs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_dir, "sections.jsonl"), "w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(s, ensure_ascii=True) + "\n")
    ok = sorted(r["number"] for r in rows if r["status"] == "ok")
    sample = sorted(random.Random(SEED).sample(ok, min(SAMPLE, len(ok))))
    with open(os.path.join(out_dir, "validation-sample.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "numbers": sample}, f, indent=1)
    by_period = {}
    for r in rows:
        by_period.setdefault(_period(r["year"]), collections.Counter())[r["cls"]] += 1
    marker_counts = collections.Counter(m for r in rows for m in r["markers"].split())
    id_counts = collections.Counter(i for r in rows for i in r["file_ids"].split())
    census = {
        "version": VERSION, "seed": SEED, "frame": frame, "total_listed": total,
        "n_listed": len(in_listing), "n_rows": len(rows),
        "counts": {k: sum(1 for r in rows if r["cls"] == k) for k in CLASSES},
        "by_period": {k: dict(v) for k, v in sorted(by_period.items())},
        "markers": dict(marker_counts),
        "top_file_ids": id_counts.most_common(25),
        "year_disagreements": sum(1 for r in rows if r["year_source"] == "page" and listed.get(r["number"])
                                  and listed[r["number"]] != r["year"]),
        "grades": grade(rows, total),
        "validation_sample": sample,
    }
    with open(os.path.join(out_dir, "census.json"), "w", encoding="utf-8") as f:
        json.dump(census, f, indent=1)
    return census


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args(argv)
    c = run(a.out_dir, delay=a.delay)
    print(json.dumps({k: c[k] for k in ("frame", "total_listed", "n_listed", "counts", "grades")}, indent=1))


if __name__ == "__main__":
    main()
