# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M8: does the text of a MEPS Statistical Brief print a number that its cited figure does not hold, where
the figure holds a number one digit away?

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m8-text-prereg-v1-2026-11-07.md (evidence-pack). Brief pages live under
meps.ahrq.gov/data_files/publications/, which meps.ahrq.gov/robots.txt does not disallow; robots.txt is checked in
code before every fetch, and no data file is ever downloaded. Stdlib only. Research information about published
statistics, not medical advice.

For every text block outside tables (paragraphs, list items, headings), the figures (or tables) it cites are the ones
named in the block ('(figure 13)', '(figures 11 and 12)', '(figures 6-9)'), or else the ones named in the nearest
heading-like block above it. Each number with a decimal point in the block is compared with the cells of those
figures (read with census M3's parser, meps/brief_tables.py):
  match     a cell equals it within half a unit of its last printed digit;
  derived   100 minus a cell, or the difference of two cells in one row or one column, equals it (same tolerance);
  unmatched otherwise.
An unmatched number is flagged when some cell, printed at the text's decimals, differs from it in exactly one digit
or by one swap of two adjacent digits, and that cell's value is not itself printed in the block.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

VERSION = "0.1.0"
UA = "MV2-evidence-pack/m8-text (mv2@munimtech.com)"
DASHES = "-" + chr(0x2013) + chr(0x2014)
REF = re.compile(r"\b(fig(?:ure)?s?\.?|tables?|exhibits?)\s+(\d+[a-z]?(?:\s*(?:,|and|&|to|through|[" + DASHES +
                 r"])\s*(?:and\s+)?\d+[a-z]?)*)", re.I)
TOK = re.compile(r"\d+[a-z]?|through|to|and|&|,|[" + DASHES + r"]", re.I)
DEC = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)(?!\d|\.\d|[A-Za-z])")
LABEL = re.compile(r"^(Figure|Table|Exhibit|Chart)\s+(\d+)", re.I)
BLOCK_TAGS = {"p", "li", "div", "dd", "dt", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
HEAD_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# Positive controls found by hand in census M7 (findings/meps-m7-totals-results-v1-2026-11-07.md):
# (brief, text number) -> figure cell printed at the text's decimals.
CONTROLS = {(567, "0.9"): "1.9", (536, "89.2"): "86.2"}
SAMPLE = 30


def parse_refs(text):
    """Sorted (kind, number) pairs cited in text; kind 'f' figure, 't' table, 'e' exhibit."""
    out = set()
    for m in REF.finditer(text or ""):
        kind = m.group(1)[0].lower()
        prev, rng = None, False
        for tok in TOK.findall(m.group(2)):
            low = tok.lower()
            if low in ("to", "through") or tok in DASHES:
                rng = True
                continue
            if low in (",", "and", "&"):
                rng = False
                continue
            n = int(re.match(r"\d+", tok).group(0))
            if rng and prev is not None and prev < n <= prev + 30:
                for k in range(prev + 1, n + 1):
                    out.add((kind, k))
            else:
                out.add((kind, n))
            prev, rng = n, False
    return sorted(out)


def numbers(text):
    """Every number with a decimal point: dicts text, value, decimals, digits."""
    out = []
    for m in DEC.finditer(text or ""):
        ip, dp = m.group(1).replace(",", ""), m.group(2)
        out.append({"text": m.group(0), "value": float(ip + "." + dp), "decimals": len(dp), "digits": ip + dp})
    return out


def heading_like(tag, text, nums):
    return tag in HEAD_TAGS or (len(text.split()) <= 15 and not nums)


def near_miss(a, b):
    """True if digit strings a and b have the same length and differ in one digit or one adjacent swap."""
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(diff) == 1:
        return True
    return (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]]
            and a[diff[1]] == b[diff[0]])


def _fmt(v, d):
    return "%.*f" % (d, v)


def _digits(s):
    return "".join(ch for ch in s if ch.isdigit())


def classify(num, cells, printed):
    """(verdict, near) for one text number against the cells of its cited figures."""
    t, d = num["value"], num["decimals"]
    tol = 0.5 * 10 ** -d + 1e-9
    if any(abs(c["value"] - t) <= tol for c in cells):
        return "match", []
    if any(abs(100.0 - c["value"] - t) <= tol for c in cells):
        return "derived", []
    groups = {}
    for c in cells:
        groups.setdefault(("r", c["tindex"], c["row"]), []).append(c["value"])
        groups.setdefault(("c", c["tindex"], c["section"], c["col"]), []).append(c["value"])
    for vals in groups.values():
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                if abs(abs(vals[i] - vals[j]) - t) <= tol:
                    return "derived", []
    near = []
    for c in cells:
        if c["decimals"] < d:
            continue
        s = _fmt(c["value"], d)
        if s in printed or s in near:
            continue
        if near_miss(num["digits"], _digits(s)):
            near.append(s)
    return "unmatched", near


class _TextParser(HTMLParser):
    """Text blocks outside tables, scripts and styles, in page order: (tag, text)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.buf, self.tag = [], "text"
        self.table = 0
        self.skip = 0

    def _flush(self):
        t = " ".join("".join(self.buf).split())
        if t:
            self.blocks.append((self.tag, t))
        self.buf, self.tag = [], "text"

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            if not self.table:
                self._flush()
            self.table += 1
        elif tag in ("script", "style"):
            self.skip += 1
        elif tag == "br":
            self.buf.append(" ")
        elif tag in BLOCK_TAGS and not self.table:
            self._flush()
            self.tag = tag

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "table":
            self.table = max(0, self.table - 1)
        elif tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS and not self.table:
            self._flush()

    def handle_data(self, data):
        if not self.table and not self.skip:
            self.buf.append(data)


def text_blocks(html_text):
    p = _TextParser()
    p.feed(html_text)
    p.close()
    p._flush()
    return p.blocks


def figure_cells(html_text):
    """{(kind, number): [cells]} from census M3's table parser (imported here so that the pure functions above
    can be tested without it)."""
    from meps import brief_tables as bt
    out = {}
    for t in bt.parse_page(html_text):
        m = LABEL.match(t["label"] or "")
        if not m:
            continue
        key = (m.group(1)[0].lower(), int(m.group(2)))
        for c in t["cells"]:
            out.setdefault(key, []).append(dict(c, tindex=t["index"], label=t["label"]))
    return out


def check_page(html_text):
    """(rows, stats): one row per number in a block whose cited figures have cells."""
    figs = figure_cells(html_text)
    rows, ctx = [], []
    stats = {"blocks": 0, "numbers": 0, "checked": 0}
    for i, (tag, text) in enumerate(text_blocks(html_text)):
        stats["blocks"] += 1
        refs = parse_refs(text)
        nums = numbers(text)
        stats["numbers"] += len(nums)
        if heading_like(tag, text, nums):
            ctx = refs
            continue
        use = refs or ctx
        cells = [c for r in use for c in figs.get(r, [])]
        if not nums or not cells:
            continue
        printed = set(_fmt(n["value"], n["decimals"]) for n in nums)
        for n in nums:
            verdict, near = classify(n, cells, printed)
            stats["checked"] += 1
            k = text.find(n["text"])
            rows.append({"block": i, "refs": ";".join("%s%d" % r for r in use), "text": n["text"],
                         "value": n["value"], "decimals": n["decimals"], "verdict": verdict, "near": "|".join(near),
                         "context": text[max(0, k - 90):k + len(n["text"]) + 60]})
    return rows, stats


def load_numbers(path):
    """{brief number: year} from census M3's tables.csv."""
    years = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                years[int(r["number"])] = r.get("year", "")
            except (KeyError, ValueError):
                continue
    return years


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as f:
        return f.read()


def _decode(raw):
    if isinstance(raw, str):
        return raw, raw.encode("utf-8")
    try:
        return raw.decode("utf-8"), raw
    except UnicodeDecodeError:
        return raw.decode("latin-1"), raw


ROBOTS = "https://meps.ahrq.gov/robots.txt"
URL = "https://meps.ahrq.gov/data_files/publications/st%d/stat%d.shtml"


def run(numbers_, get=None, pause=None, allowed=None, delay=3):
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(_decode(get(ROBOTS))[0].splitlines())
        rp.modified()
        allowed = lambda u: rp.can_fetch(UA, u)  # noqa: E731
    results, errors, sha = {}, {}, {}
    for i, n in enumerate(numbers_):
        url = URL % (n, n)
        if not allowed(url):
            errors[n] = "disallowed by robots.txt"
            continue
        if i:
            pause(delay)
        last = None
        for attempt in range(2):
            try:
                text, raw = _decode(get(url))
                sha[n] = hashlib.sha256(raw).hexdigest()
                results[n] = check_page(text)
                last = None
                break
            except Exception as e:  # noqa: BLE001
                last = "%s: %s" % (type(e).__name__, e)
                if attempt == 0:
                    pause(30)
        if last:
            errors[n] = last
    return results, errors, sha


def summarise(results, years, errors, sample=SAMPLE):
    rows, flags = [], []
    tot = {"blocks": 0, "numbers": 0, "checked": 0}
    briefs_checked = 0
    for n in sorted(results):
        page_rows, st = results[n]
        for k in tot:
            tot[k] += st[k]
        if page_rows:
            briefs_checked += 1
        for r in page_rows:
            r = dict(r, number=n, year=years.get(n, ""))
            rows.append(r)
            if r["verdict"] == "unmatched" and r["near"]:
                flags.append(r)
    for f in flags:
        f["key"] = hashlib.sha256(("m8|%d|%d|%s" % (f["number"], f["block"], f["text"])).encode()).hexdigest()
        want = CONTROLS.get((f["number"], f["text"]))
        f["control"] = want is not None and want in f["near"].split("|")
    flags.sort(key=lambda f: f["key"])
    rank = 0
    for f in flags:
        if f["control"]:
            f["check_rank"], f["in_sample"] = "", False
            continue
        rank += 1
        f["check_rank"], f["in_sample"] = rank, rank <= sample
    by = {"match": 0, "derived": 0, "unmatched": 0}
    for r in rows:
        by[r["verdict"]] += 1
    checked = len(rows)
    summary = {
        "version": VERSION, "briefs": len(years), "fetched": len(results), "errors": {str(k): v for k, v in
                                                                                       sorted(errors.items())},
        "briefs_with_checked_numbers": briefs_checked, "blocks": tot["blocks"], "numbers_in_text": tot["numbers"],
        "numbers_checked": checked, "by_verdict": by,
        "matched_share": round((by["match"] + by["derived"]) / checked, 4) if checked else None,
        "flags": len(flags), "flagged_briefs": len(set(f["number"] for f in flags)),
        "sample_size": sum(1 for f in flags if f["in_sample"]),
        "controls": {str(k[0]): any(f["control"] and f["number"] == k[0] for f in flags) for k in CONTROLS}}
    return summary, rows, flags


def write_outputs(out_dir, summary, rows, flags):
    cols = ["number", "year", "block", "refs", "text", "value", "decimals", "verdict", "near", "context"]
    with open(os.path.join(out_dir, "m8-numbers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    fcols = ["check_rank", "in_sample", "control"] + cols
    with open(os.path.join(out_dir, "m8-flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fcols)
        for r in flags:
            w.writerow([r[c] for c in fcols])
    with open(os.path.join(out_dir, "m8-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", default="findings/meps-brief-tables-v1/tables.csv")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--delay", type=float, default=3)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    years = load_numbers(a.tables)
    results, errors, sha = run(sorted(years), get=get, pause=pause, allowed=allowed, delay=a.delay)
    summary, rows, flags = summarise(results, years, errors)
    summary["sha256"] = {str(k): v for k, v in sorted(sha.items())}
    write_outputs(a.out_dir, summary, rows, flags)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sha256", "errors")}, indent=1))
    print(json.dumps({"errors": len(summary["errors"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
