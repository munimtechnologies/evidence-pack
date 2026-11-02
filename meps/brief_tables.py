# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M3: read the accessible data tables that MEPS Statistical Briefs print under their figures, and turn
every published number in them into one machine-readable row.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-brief-tables-prereg-v1-2026-11-02.md (evidence-pack). Brief pages live under
meps.ahrq.gov/data_files/publications/, which meps.ahrq.gov/robots.txt does not disallow; robots.txt is checked
in code before every fetch, and no data file is ever downloaded. Stdlib only. Research information about
published statistics, not medical advice.
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
ROBOTS = "https://meps.ahrq.gov/robots.txt"
URL = "https://meps.ahrq.gov/data_files/publications/st%d/stat%d.shtml"
UA = "MV2-evidence-pack/brief-tables (mv2@munimtech.com)"

NUM = re.compile(r"^(\$)?(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?)(%)?\*{0,3}$")
LABEL = re.compile(r"\b(Figure|Table|Exhibit|Chart)\s+(\d+[A-Za-z]?)\b", re.I)
YEAR = re.compile(r"^(19[89]\d|20[0-3]\d)$")

# Gate G1: Brief #569's eight figure tables, in page order, as transcribed by hand for check R1
# (meps/r569.py CELLS + MSA_CELLS) and read again with WebFetch on 2026-11-02.
G569 = [21.5, 9.2, 33.8, 42.8, 24.8, 67.6, 27.9, 17.4, 69.4, 72.4, 45.8, 30.7, 45.3, 25.4, 47.7, 37.1, 30.4,
        44.1, 43.9, 42.1, 41.7, 43.3, 42.7, 37.5, 38.9, 47.6]
# Gate G2: Brief #491's three figure tables (5 x 3, 5 x 6, 5 x 3 numbers; WebFetch read 2026-11-02).
G491 = [15, 30, 15]
# Check R2's eligible set (findings/meps-r2-prereg-v1-2026-11-02.md).
R2_ELIGIBLE = [491, 493, 496, 497, 506, 507, 521, 533, 540, 554, 558]


def number(text):
    """(value, decimals) if a cell is one published number ('42.8', '$1,234', '12 %', '45.3*'), else None."""
    t = "".join((text or "").split())
    m = NUM.match(t)
    if not m:
        return None
    return float(m.group(2).replace(",", "")), len(m.group(3) or "")


class _Parser(HTMLParser):
    """Collects innermost tables (rows of cells with colspan) and the page text that precedes each table."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.done = []
        self.text = []

    def _ctx(self):
        return " ".join(" ".join(self.text[-400:]).split())[-3000:]

    def _close_cell(self, t):
        c = t["cell"]
        if c is not None:
            if t["row"] is None:
                t["row"] = []
            t["row"].append({"text": " ".join("".join(c["parts"]).split()), "th": c["th"], "span": c["span"]})
            t["cell"] = None

    def _close_row(self, t):
        self._close_cell(t)
        if t["row"]:
            t["rows"].append(t["row"])
        t["row"] = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "br":
            self.handle_data(" ")
            return
        if tag == "table":
            if self.stack:
                self.stack[-1]["nested"] = True
            self.stack.append({"rows": [], "row": None, "cell": None, "nested": False, "context": self._ctx(),
                               "caption": [], "in_caption": False})
            return
        if not self.stack:
            return
        t = self.stack[-1]
        if tag == "tr":
            self._close_row(t)
            t["row"] = []
        elif tag in ("td", "th"):
            self._close_cell(t)
            span = 1
            for k, v in attrs:
                if k == "colspan":
                    try:
                        span = max(1, min(50, int(v)))
                    except (TypeError, ValueError):
                        span = 1
            t["cell"] = {"parts": [], "th": tag == "th", "span": span}
        elif tag == "caption":
            t["in_caption"] = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self.stack:
            return
        t = self.stack[-1]
        if tag in ("td", "th"):
            self._close_cell(t)
        elif tag == "tr":
            self._close_row(t)
        elif tag == "caption":
            t["in_caption"] = False
        elif tag == "table":
            self._close_row(t)
            self.stack.pop()
            if not t["nested"]:
                self.done.append(t)

    def handle_data(self, data):
        self.text.append(data)
        if self.stack:
            t = self.stack[-1]
            if t["in_caption"]:
                t["caption"].append(data)
            elif t["cell"] is not None:
                t["cell"]["parts"].append(data)


def _expand(row):
    out = []
    for c in row:
        out.append(dict(c, dup=False))
        for _ in range(c["span"] - 1):
            out.append(dict(c, dup=True))
    return out


def _is_label_row(r, top):
    vals = [c["text"] for c in r[1:] if not c["dup"] and c["text"]]
    if not vals:
        return True
    if all(number(v) is None for v in vals):
        return True
    return top and all(YEAR.match(v) for v in vals)


def _banner(h):
    """A header row that is one cell spanning the whole row (a title inside the table)."""
    return len(h) > 1 and h[0]["span"] == len(h) and all(c["dup"] for c in h[1:])


def _label_title(t, head=()):
    cap = " ".join("".join(t["caption"]).split())
    inner = " ".join(c["text"] for h in head for c in h if not c["dup"] and c["text"])
    for src in (cap, inner):
        ms = list(LABEL.finditer(src))
        if ms:
            m = ms[0]
            return "%s %s" % (m.group(1).title(), m.group(2)), src[m.start():m.start() + 200]
    ctx = t["context"]
    ms = list(LABEL.finditer(ctx))
    if ms:
        m = ms[-1]
        return "%s %s" % (m.group(1).title(), m.group(2)), ctx[m.start():m.start() + 200]
    return "", cap[:200]


def sum_check(rec):
    """Exploratory: in a table whose title says 'distribution', do all columns (within a section) or all rows
    sum to 100 within the rounding the printed decimals allow? Cells printed as exactly 100 are left out."""
    if "distribution" not in rec["title"].lower():
        return None

    def ok(groups):
        res = []
        for cs in groups.values():
            cs = [c for c in cs if c["value"] != 100.0]
            if len(cs) < 2:
                continue
            s = sum(c["value"] for c in cs)
            tol = sum(0.5 * 10 ** -c["decimals"] for c in cs) + 1e-9
            res.append(abs(s - 100.0) <= tol)
        return res

    by_col, by_row = {}, {}
    for c in rec["cells"]:
        by_col.setdefault((c["section"], c["col"]), []).append(c)
        by_row.setdefault(c["row"], []).append(c)
    rc, rr = ok(by_col), ok(by_row)
    passed = (bool(rc) and all(rc)) or (bool(rr) and all(rr))
    return {"cols_ok": sum(rc), "cols": len(rc), "rows_ok": sum(rr), "rows": len(rr), "passed": passed}


def table_record(t):
    rows = [_expand(r) for r in t["rows"]]
    head, body = [], []
    for r in rows:
        if not body and _is_label_row(r, True):
            head.append(r)
        else:
            body.append(r)
    label, title = _label_title(t, head)
    cells, section = [], ""
    for i, r in enumerate(body):
        if _is_label_row(r, False):
            section = " ".join(c["text"] for c in r if c["text"] and not c["dup"])
            continue
        row_label = r[0]["text"] if r else ""
        for j in range(1, len(r)):
            c = r[j]
            if c["dup"]:
                continue
            v = number(c["text"])
            if v is None:
                continue
            col = " / ".join(h[j]["text"] for h in head if j < len(h) and h[j]["text"] and not _banner(h))
            cells.append({"row": i, "col": j, "section": section, "row_label": row_label, "col_label": col,
                          "text": c["text"], "value": v[0], "decimals": v[1]})
    rec = {"label": label, "title": title, "n_rows": len(rows), "n_cols": max([len(r) for r in rows] or [0]),
           "n_numeric": len(cells), "cells": cells}
    rec["sum_check"] = sum_check(rec)
    return rec


def parse_page(html_text):
    """Data tables (innermost tables with at least one numeric cell), in page order, numbered from 1."""
    p = _Parser()
    p.feed(html_text)
    p.close()
    out = []
    for t in p.done:
        rec = table_record(t)
        if rec["n_numeric"]:
            rec["index"] = len(out) + 1
            out.append(rec)
    return out


def gate(pages):
    t569 = [t for t in (pages.get(569) or []) if t["label"]]
    v569 = [c["value"] for t in t569 for c in t["cells"]]
    ok569 = [t["label"] for t in t569] == ["Figure %d" % i for i in range(1, 9)] and v569 == G569
    t491 = [t for t in (pages.get(491) or []) if t["label"]]
    ok491 = ([t["label"] for t in t491] == ["Figure 1", "Figure 2", "Figure 3"]
             and [t["n_numeric"] for t in t491] == G491)
    return {"passed": ok569 and ok491, "G1_569": ok569, "G1_values_read": len(v569), "G2_491": ok491,
            "G2_counts": [t["n_numeric"] for t in t491]}


def has_table(recs):
    return bool(recs) and any(t["label"] and t["n_numeric"] for t in recs)


def grade(pages, years):
    recent = [n for n, recs in pages.items() if recs is not None and years.get(n, 0) >= 2016]
    with_t = [n for n in recent if has_table(pages[n])]
    share = len(with_t) / len(recent) if recent else 0.0
    g = {"P1": {"n_2016_on": len(recent), "with_table": len(with_t), "share": round(share, 4),
                "grade": "held" if recent and share >= 0.9 else "failed"}}
    missing = [n for n in R2_ELIGIBLE if not has_table(pages.get(n))]
    g["P2"] = {"r2_without_table": missing, "grade": "held" if not missing else "failed"}
    return g


def load_briefs(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    years = {}
    for r in rows:
        try:
            n, y = int(r["number"]), int(r["year"] or 0)
        except (KeyError, ValueError):
            continue
        if r.get("status") == "ok":
            years[n] = y
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


def build(numbers, get=None, pause=None, allowed=None, delay=3):
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(_decode(get(ROBOTS))[0].splitlines())
        rp.modified()
        allowed = lambda u: rp.can_fetch(UA, u)  # noqa: E731
    pages, errors, sha = {}, {}, {}
    for i, n in enumerate(numbers):
        url = URL % (n, n)
        if not allowed(url):
            errors[n] = "disallowed by robots.txt"
            pages[n] = None
            continue
        if i:
            pause(delay)
        last = None
        for attempt in range(2):
            try:
                text, raw = _decode(get(url))
                sha[n] = hashlib.sha256(raw).hexdigest()
                pages[n] = parse_page(text)
                last = None
                break
            except Exception as e:  # noqa: BLE001
                last = "%s: %s" % (type(e).__name__, e)
                if attempt == 0:
                    pause(30)
        if last:
            errors[n] = last
            pages[n] = None
    return pages, errors, sha


def write_outputs(out_dir, pages, years):
    cdir = os.path.join(out_dir, "cells")
    os.makedirs(cdir, exist_ok=True)
    with open(os.path.join(out_dir, "tables.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "year", "index", "label", "title", "n_rows", "n_cols", "n_numeric",
                    "sum_check_passed"])
        for n in sorted(pages):
            for t in pages[n] or []:
                sc = t["sum_check"]
                w.writerow([n, years.get(n, ""), t["index"], t["label"], t["title"], t["n_rows"], t["n_cols"],
                            t["n_numeric"], "" if sc is None else sc["passed"]])
    chunks = {}
    for n in sorted(pages):
        for t in pages[n] or []:
            for c in t["cells"]:
                chunks.setdefault(n // 100, []).append(
                    [n, t["index"], t["label"], c["row"], c["col"], c["section"], c["row_label"], c["col_label"],
                     c["text"], c["value"], c["decimals"]])
    for k, rows in sorted(chunks.items()):
        name = "st%03d-%03d.csv" % (k * 100, k * 100 + 99)
        with open(os.path.join(cdir, name), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["number", "table", "label", "row", "col", "section", "row_label", "col_label", "text",
                        "value", "decimals"])
            w.writerows(rows)
    return sorted("st%03d-%03d.csv" % (k * 100, k * 100 + 99) for k in chunks)


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefs", default="/work/briefs.csv")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--delay", type=float, default=3)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "error": None}
    try:
        years = load_briefs(a.briefs)
        numbers = sorted(years)
        pages, errors, sha = build(numbers, get=get, pause=pause, allowed=allowed, delay=a.delay)
        out["n_briefs"] = len(numbers)
        out["n_fetched"] = sum(1 for v in pages.values() if v is not None)
        out["errors"] = {str(k): v for k, v in errors.items()}
        out["gate"] = gate(pages)
        out["grades"] = grade(pages, years)
        out["per_brief"] = {str(n): {"year": years.get(n), "sha256": sha.get(n),
                                     "tables": None if pages[n] is None else len(pages[n]),
                                     "labelled": None if pages[n] is None else sum(1 for t in pages[n] if t["label"]),
                                     "cells": None if pages[n] is None else sum(t["n_numeric"] for t in pages[n])}
                            for n in sorted(pages)}
        flags = []
        n_dist = 0
        for n in sorted(pages):
            for t in pages[n] or []:
                if t["sum_check"] is not None:
                    n_dist += 1
                    if not t["sum_check"]["passed"]:
                        flags.append(dict(t["sum_check"], number=n, index=t["index"], label=t["label"],
                                          title=t["title"]))
        out["sum_check"] = {"distribution_tables": n_dist, "flagged": flags}
        out["totals"] = {"tables": sum(len(v) for v in pages.values() if v),
                         "cells": sum(t["n_numeric"] for v in pages.values() if v for t in v),
                         "briefs_with_table": sum(1 for v in pages.values() if has_table(v))}
        out["cell_files"] = write_outputs(a.out_dir, pages, years)
    except Exception as e:  # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(a.out_dir, "brief-tables.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out.get(k) for k in ("n_briefs", "n_fetched", "gate", "grades", "totals", "error")},
                     indent=1))
    print(json.dumps({"distribution_tables": (out.get("sum_check") or {}).get("distribution_tables"),
                      "flagged": len((out.get("sum_check") or {}).get("flagged") or [])}, indent=1))
    return 0 if out["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
