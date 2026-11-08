# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Diagnosis for census M8 v0.1.0: where does the body text of a MEPS Statistical Brief page sit?

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Census M8 (meps/m8text.py 0.1.0) read text only outside HTML tables and reached 17 of 540 briefs (#554-#570).
The suspected cause is that older brief pages wrap their whole body in layout tables. This script measures, for a
fixed list of briefs, how many characters of text and how many figure citations ('(figure 13)') sit
  outside  : outside every table;
  layout   : inside a table whose innermost enclosing table itself contains another table;
  leaf     : inside an innermost table (no table inside it).
It also reports the five largest leaf tables by text length (characters, cells, citations, numeric cells), so a
leaf table that is really a one-cell layout wrapper can be told apart from a figure's data table.
Diagnosis only: nothing here is graded. Stdlib only; robots.txt is checked before every fetch; 3 s between pages.
"""
import argparse
import json
import os
import re
import time
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

VERSION = "0.1.0"
UA = "MV2-evidence-pack/m8-diag (mv2@munimtech.com)"
ROBOTS = "https://meps.ahrq.gov/robots.txt"
URL = "https://meps.ahrq.gov/data_files/publications/st%d/stat%d.shtml"
CITE = re.compile(r"\(\s*(?:see\s+)?fig(?:ure)?s?\.?\s*\d", re.I)
NUMCELL = re.compile(r"^\$?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?\*{0,3}$")
# Briefs spread over the series (fixed before the job runs): the M7 control #536 and older template years.
DEFAULT = [536, 533, 497, 460, 423, 352, 297, 257, 217, 170, 100, 10, 554, 567]


class _Diag(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []      # open table ids, outermost first
        self.tables = {}     # id -> {"nested": bool, "cells": int, "numeric": int, "cell": None or [text]}
        self.pieces = []     # (innermost table id or None, text)
        self.skip = 0
        self.next_id = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "table":
            if self.stack:
                self.tables[self.stack[-1]]["nested"] = True
            tid = self.next_id
            self.next_id += 1
            self.tables[tid] = {"nested": False, "cells": 0, "numeric": 0, "cell": None}
            self.stack.append(tid)
        elif tag in ("td", "th") and self.stack:
            self._close_cell(self.stack[-1])
            self.tables[self.stack[-1]]["cell"] = []
        elif tag == "br":
            self.handle_data(" ")

    def _close_cell(self, tid):
        t = self.tables[tid]
        if t["cell"] is not None:
            txt = "".join("".join(t["cell"]).split())
            t["cells"] += 1
            if txt and NUMCELL.match(txt):
                t["numeric"] += 1
        t["cell"] = None

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th") and self.stack:
            self._close_cell(self.stack[-1])
        elif tag == "table" and self.stack:
            self._close_cell(self.stack[-1])
            self.stack.pop()

    def handle_data(self, data):
        if self.skip:
            return
        if self.stack:
            cell = self.tables[self.stack[-1]]["cell"]
            if cell is not None:
                cell.append(data)
        self.pieces.append((self.stack[-1] if self.stack else None, data))


def diagnose(html_text):
    p = _Diag()
    p.feed(html_text)
    p.close()
    zones = {z: {"chars": 0, "cites": 0} for z in ("outside", "layout", "leaf")}
    per_table = {}
    for tid, data in p.pieces:
        if tid is None:
            zone = "outside"
        elif p.tables[tid]["nested"]:
            zone = "layout"
        else:
            zone = "leaf"
        if tid is not None:
            per_table.setdefault(tid, []).append(data)
        zones[zone]["chars"] += len(" ".join(data.split()))
    text_by_zone = {"outside": [], "layout": [], "leaf": []}
    for tid, data in p.pieces:
        zone = "outside" if tid is None else ("layout" if p.tables[tid]["nested"] else "leaf")
        text_by_zone[zone].append(data)
    for z, parts in text_by_zone.items():
        zones[z]["cites"] = len(CITE.findall(" ".join(" ".join(parts).split())))
    leaves = []
    for tid, parts in per_table.items():
        t = p.tables[tid]
        if t["nested"]:
            continue
        txt = " ".join(" ".join(parts).split())
        leaves.append({"chars": len(txt), "cells": t["cells"], "numeric": t["numeric"],
                       "cites": len(CITE.findall(txt))})
    leaves.sort(key=lambda r: -r["chars"])
    return {"tables": len(p.tables), "layout_tables": sum(1 for t in p.tables.values() if t["nested"]),
            "zones": zones, "top_leaves": leaves[:5]}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefs", default=",".join(str(n) for n in DEFAULT))
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--delay", type=float, default=3)
    a = ap.parse_args(argv)
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(get(ROBOTS).splitlines())
        rp.modified()
        allowed = lambda u: rp.can_fetch(UA, u)  # noqa: E731
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "briefs": {}}
    for i, n in enumerate(int(x) for x in a.briefs.split(",") if x.strip()):
        url = URL % (n, n)
        if not allowed(url):
            out["briefs"][str(n)] = {"error": "disallowed by robots.txt"}
            continue
        if i:
            pause(a.delay)
        try:
            out["briefs"][str(n)] = diagnose(get(url))
        except Exception as e:  # noqa: BLE001
            out["briefs"][str(n)] = {"error": "%s: %s" % (type(e).__name__, e)}
    with open(os.path.join(a.out_dir, "m8-diag.json"), "w") as f:
        json.dump(out, f, indent=1)
    for n, r in out["briefs"].items():
        if "zones" in r:
            z = r["zones"]
            print(n, "tables", r["tables"], "layout", r["layout_tables"],
                  "outside", z["outside"]["chars"], z["outside"]["cites"],
                  "layout", z["layout"]["chars"], z["layout"]["cites"],
                  "leaf", z["leaf"]["chars"], z["leaf"]["cites"], flush=True)
        else:
            print(n, r, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
