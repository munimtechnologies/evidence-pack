# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M8 v0.2: does the text of a MEPS Statistical Brief print a number that its cited figure does not hold,
where the figure holds a number one digit away?

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m8-text-prereg-v2-2026-11-08.md (evidence-pack). Version 0.1.0 (meps/m8text.py)
stays as it was graded. Brief pages live under meps.ahrq.gov/data_files/publications/, which
meps.ahrq.gov/robots.txt does not disallow; robots.txt is checked in code before every fetch, and no data file is
ever downloaded. Stdlib only. Research information about published statistics, not medical advice.

Changes from 0.1.0 (each fixed before this version ran on any page outside the 0.1.0 run and the m8diag run):
  1. Text is read outside tables AND inside layout tables (a table that contains another table). Text inside an
     innermost table (a data table) is still skipped. Cells of layout tables and two <br> in a row end a block.
  2. Numbers are compared with the absolute value of each cell ('declined by 16.1%' vs a cell printed -16.1).
  3. A figure list cannot run into a decimal number ('figure 5, 7.7' cites figure 5 only).
  4. A block is checked against the figures it names AND those named in the nearest heading-like block above it.
  5. The sum of two cells in one row counts as derived (Fair 13.0 + Poor 4.7 = 17.7).
  6. A number right after 'less than', 'more than', 'fewer than' or 'greater than' is not checked, and blocks are not
     checked from a heading 'Definitions', 'Data source(s)', 'About MEPS(-HC)', 'References' or 'Suggested
     citation' until the next h1-h6 heading with another name.
  7. Coverage gate: 14 fixed development briefs are scanned first. The full census runs only if at least 9 of the
     12 older-template ones (#10-#536) have at least one checked number.
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

VERSION = "0.2.0"
UA = "MV2-evidence-pack/m8-text2 (mv2@munimtech.com)"
DASHES = "-" + chr(0x2013) + chr(0x2014)
NUM = r"\d+(?!\d|\.\d)[a-z]?"
REF = re.compile(r"\b(fig(?:ure)?s?\.?|tables?|exhibits?)\s+(" + NUM + r"(?:\s*(?:,|and|&|to|through|[" + DASHES +
                 r"])\s*(?:and\s+)?" + NUM + r")*)", re.I)
TOK = re.compile(r"\d+[a-z]?|through|to|and|&|,|[" + DASHES + r"]", re.I)
DEC = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)(?!\d|\.\d|[A-Za-z])")
BOUND = re.compile(r"(?:less|more|fewer|greater)\s+than\s+(?:about\s+|approximately\s+)?\$?$", re.I)
LABEL = re.compile(r"^(Figure|Table|Exhibit|Chart)\s+(\d+)", re.I)
BLOCK_TAGS = {"p", "li", "div", "dd", "dt", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
CELL_TAGS = {"td", "th", "tr"}
HEAD_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
STOP_HEADS = {"definitions", "data source", "data sources", "about meps", "about meps-hc", "references",
              "suggested citation"}
BR = chr(0)
BR_SPLIT = re.compile(BR + r"\s*" + BR + r"[\s" + BR + r"]*")
# Positive controls found by hand in census M7 (findings/meps-m7-totals-results-v1-2026-11-07.md):
# (brief, text number) -> figure cell printed at the text's decimals.
CONTROLS = {(567, "0.9"): "1.9", (536, "89.2"): "86.2"}
# Development briefs (the m8diag list, 2026-11-08): scanned first; the gate counts the older-template ones.
DEV = [536, 533, 497, 460, 423, 352, 297, 257, 217, 170, 100, 10, 554, 567]
DEV_OLD = [536, 533, 497, 460, 423, 352, 297, 257, 217, 170, 100, 10]
GATE_MIN = 9
NEW_TEMPLATE_FROM = 554
SAMPLE = 20


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
    """Every number with a decimal point: dicts text, value, decimals, digits, bound."""
    text = text or ""
    out = []
    for m in DEC.finditer(text):
        ip, dp = m.group(1).replace(",", ""), m.group(2)
        pre = text[max(0, m.start() - 40):m.start()]
        out.append({"text": m.group(0), "value": float(ip + "." + dp), "decimals": len(dp), "digits": ip + dp,
                    "bound": bool(BOUND.search(pre))})
    return out


def heading_like(tag, text, nums):
    return tag in HEAD_TAGS or (len(text.split()) <= 15 and not nums)


def stop_heading(text):
    return " ".join(text.split()).rstrip(":").strip().lower() in STOP_HEADS


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
    if any(abs(abs(c["value"]) - t) <= tol for c in cells):
        return "match", []
    if any(abs(100.0 - abs(c["value"]) - t) <= tol for c in cells):
        return "derived", []
    groups = {}
    for c in cells:
        groups.setdefault(("r", c["tindex"], c["row"]), []).append(c["value"])
        groups.setdefault(("c", c["tindex"], c["section"], c["col"]), []).append(c["value"])
    for key, vals in groups.items():
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                if abs(abs(vals[i] - vals[j]) - t) <= tol:
                    return "derived", []
                if key[0] == "r" and abs(abs(vals[i] + vals[j]) - t) <= tol:
                    return "derived", []
    near = []
    for c in cells:
        if c["decimals"] < d:
            continue
        s = _fmt(abs(c["value"]), d)
        if s in printed or s in near:
            continue
        if near_miss(num["digits"], _digits(s)):
            near.append(s)
    return "unmatched", near


class _Nest(HTMLParser):
    """First pass: for each table in start order, does it contain another table?"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.nested = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.stack:
                self.nested[self.stack[-1]] = True
            self.stack.append(len(self.nested))
            self.nested.append(False)

    def handle_endtag(self, tag):
        if tag == "table" and self.stack:
            self.stack.pop()


class _TextParser(HTMLParser):
    """Second pass: text blocks outside tables or inside layout tables, in page order: (tag, text)."""

    def __init__(self, nested):
        super().__init__(convert_charrefs=True)
        self.nested = nested
        self.blocks = []
        self.buf, self.tag = [], "text"
        self.stack = []
        self.n = 0
        self.skip = 0

    def _reading(self):
        if not self.stack:
            return True
        tid = self.stack[-1]
        return tid < len(self.nested) and self.nested[tid]

    def _flush(self):
        raw = "".join(self.buf)
        for part in BR_SPLIT.split(raw):
            t = " ".join(part.replace(BR, " ").split())
            if t:
                self.blocks.append((self.tag, t))
        self.buf, self.tag = [], "text"

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self._reading():
                self._flush()
            self.stack.append(self.n)
            self.n += 1
        elif tag in ("script", "style"):
            self.skip += 1
        elif not self._reading():
            return
        elif tag == "br":
            self.buf.append(BR)
        elif tag in BLOCK_TAGS or tag in CELL_TAGS:
            self._flush()
            if tag in BLOCK_TAGS:
                self.tag = tag

    def handle_endtag(self, tag):
        if tag == "table":
            if self.stack:
                if self._reading():
                    self._flush()
                self.stack.pop()
        elif tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif not self._reading():
            return
        elif tag in BLOCK_TAGS or tag in CELL_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._reading() and not self.skip:
            self.buf.append(data)


def text_blocks(html_text):
    n = _Nest()
    n.feed(html_text)
    n.close()
    p = _TextParser(n.nested)
    p.feed(html_text)
    p.close()
    p._flush()
    return p.blocks


def figure_cells(html_text):
    """{(kind, number): [cells]} from census M3's table parser (imported here so that the functions above can be
    tested without it)."""
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


def check_page(html_text, figs=None):
    """(rows, stats): one row per checked number in a block whose cited figures have cells."""
    figs = figure_cells(html_text) if figs is None else figs
    rows, ctx = [], []
    stats = {"blocks": 0, "numbers": 0, "checked": 0, "bounds": 0, "stopped": 0}
    stopping = False
    for i, (tag, text) in enumerate(text_blocks(html_text)):
        stats["blocks"] += 1
        refs = parse_refs(text)
        nums = numbers(text)
        if heading_like(tag, text, nums):
            if stop_heading(text):
                stopping = True
                stats["stopped"] = 1
                continue
            if stopping and tag not in HEAD_TAGS:
                continue
            stopping = False
            ctx = refs
            continue
        if stopping:
            continue
        stats["numbers"] += len(nums)
        use = sorted(set(refs) | set(ctx))
        cells = [c for r in use for c in figs.get(r, [])]
        if not nums or not cells:
            continue
        printed = set(_fmt(n["value"], n["decimals"]) for n in nums)
        for n in nums:
            if n["bound"]:
                stats["bounds"] += 1
                continue
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


def robots_check(get):
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(_decode(get(ROBOTS))[0].splitlines())
    rp.modified()
    return lambda u: rp.can_fetch(UA, u)


def run(numbers_, get=None, pause=None, allowed=None, delay=3):
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        allowed = robots_check(get)
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


def gate_check(results):
    have = [n for n in DEV_OLD if n in results and results[n][0]]
    return {"old_dev_briefs": len(DEV_OLD), "with_checked_numbers": len(have), "min": GATE_MIN,
            "without": [n for n in DEV_OLD if n not in have], "passed": len(have) >= GATE_MIN}


def _share(rows):
    if not rows:
        return None
    return round(sum(1 for r in rows if r["verdict"] in ("match", "derived")) / len(rows), 4)


def summarise(results, years, errors, sample=SAMPLE):
    rows, flags = [], []
    tot = {"blocks": 0, "numbers": 0, "checked": 0, "bounds": 0, "stopped": 0}
    briefs_checked = 0
    for n in sorted(results):
        page_rows, st = results[n]
        for k in tot:
            tot[k] += st.get(k, 0)
        if page_rows:
            briefs_checked += 1
        for r in page_rows:
            r = dict(r, number=n, year=years.get(n, ""))
            rows.append(r)
            if r["verdict"] == "unmatched" and r["near"]:
                flags.append(r)
    for f in flags:
        f["key"] = hashlib.sha256(("m8v2|%d|%d|%s" % (f["number"], f["block"], f["text"])).encode()).hexdigest()
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
    summary = {
        "version": VERSION, "briefs": len(years), "fetched": len(results),
        "errors": {str(k): v for k, v in sorted(errors.items())},
        "briefs_with_checked_numbers": briefs_checked,
        "coverage": round(briefs_checked / len(results), 4) if results else None,
        "blocks": tot["blocks"], "numbers_in_text": tot["numbers"], "bounds_skipped": tot["bounds"],
        "briefs_with_stop_heading": tot["stopped"], "numbers_checked": len(rows), "by_verdict": by,
        "matched_share": _share(rows),
        "matched_share_old": _share([r for r in rows if r["number"] < NEW_TEMPLATE_FROM]),
        "matched_share_new": _share([r for r in rows if r["number"] >= NEW_TEMPLATE_FROM]),
        "flags": len(flags), "flagged_briefs": len(set(f["number"] for f in flags)),
        "sample_size": sum(1 for f in flags if f["in_sample"]),
        "controls": {str(k[0]): any(f["control"] and f["number"] == k[0] for f in flags) for k in CONTROLS}}
    return summary, rows, flags


def write_outputs(out_dir, summary, rows, flags):
    cols = ["number", "year", "block", "refs", "text", "value", "decimals", "verdict", "near", "context"]
    with open(os.path.join(out_dir, "m8v2-numbers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    fcols = ["check_rank", "in_sample", "control"] + cols
    with open(os.path.join(out_dir, "m8v2-flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fcols)
        for r in flags:
            w.writerow([r[c] for c in fcols])
    with open(os.path.join(out_dir, "m8v2-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", default="findings/meps-brief-tables-v1/tables.csv")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--delay", type=float, default=3)
    ap.add_argument("--sample", type=int, default=SAMPLE)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        allowed = robots_check(get)
    years = load_numbers(a.tables)
    dev = [n for n in DEV if n in years]
    results, errors, sha = run(dev, get=get, pause=pause, allowed=allowed, delay=a.delay)
    gate = gate_check(results)
    print(json.dumps({"gate": gate}), flush=True)
    if gate["passed"]:
        rest = [n for n in sorted(years) if n not in set(dev)]
        if rest:
            pause(a.delay)
        r2, e2, s2 = run(rest, get=get, pause=pause, allowed=allowed, delay=a.delay)
        results.update(r2)
        errors.update(e2)
        sha.update(s2)
    summary, rows, flags = summarise(results, years, errors, sample=a.sample)
    summary["gate"] = gate
    summary["sha256"] = {str(k): v for k, v in sorted(sha.items())}
    write_outputs(a.out_dir, summary, rows, flags)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sha256", "errors")}, indent=1))
    print(json.dumps({"errors": len(summary["errors"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
