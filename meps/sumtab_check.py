# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Check of the sample sizes behind suppression in AHRQ's MEPS-HC summary tables:
do mean and median expenditure per person with an expense carry the count of
persons with an expense, as AHRQ's precision standard asks?

Pre-registered in findings/meps-sumtab-prereg-v1-2026-10-31.md (check S1).
Made by AI agents (Claude) working in MV2's name, MV2 of Munim, Inc.
Standard library only. Reads AHRQ's public GitHub repository HHS-AHRQ/MEPS-summary-tables.

Usage: python -m meps.sumtab_check --out-dir out
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

VERSION = "0.1.0"
REPO = "HHS-AHRQ/MEPS-summary-tables"
API = "https://api.github.com/repos/" + REPO
RAW = "https://raw.githubusercontent.com/" + REPO + "/{sha}/{path}"
MEDIA = "https://media.githubusercontent.com/media/" + REPO + "/{sha}/{path}"
APP = "formatted_tables/hc_use"
CODE = "functions_format.R"
UA = "MV2-Munim-sumtab-check/" + VERSION + " (mailto:mv2@munimtech.com)"
KEY = ("row_group", "row_var", "rowLevels", "col_group", "col_var", "colLevels")
POP, PCT = "totPOP", "pctEXP"
EXP = ("meanEXP", "medEXP")
KEEP = (POP, PCT) + EXP
BELOW_ALL = 0.999
MIN_CELLS = 100
MIN_YEARS = 20
SHARE = 0.99
EST_LIMIT = 50
CODE_RX = re.compile(r"sample_size|suppress|special_pct|asterisk|RSE")
BUG_TEXT = 'value %in% c("meanEXP","medEXP")'
YEAR_RX = re.compile(r"^DY(\d{4})\.csv$")


def to_float(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def scan(text):
    """(cells, stat_vars, rows) for one formatted table CSV.

    cells[key][stat] = [set of sample sizes, list of values (None if empty)]
    """
    cells, stats, n = {}, set(), 0
    for row in csv.DictReader(io.StringIO(text)):
        n += 1
        st = row.get("stat_var") or ""
        stats.add(st)
        if st not in KEEP:
            continue
        key = tuple(row.get(k) or "" for k in KEY)
        slot = cells.setdefault(key, {}).setdefault(st, [set(), []])
        ss = (row.get("sample_size") or "").strip()
        if ss:
            slot[0].add(ss)
        slot[1].append(to_float(row.get("value")))
    return cells, stats, n


def _one_int(s):
    """The single sample size in set s as an int, else None."""
    if len(s) != 1:
        return None
    v = to_float(next(iter(s)))
    return int(round(v)) if v is not None else None


def _one_value(vals):
    vs = set(v for v in vals if v is not None)
    return vs.pop() if len(vs) == 1 else None


def pct_scale(cells):
    """100 if pctEXP values are written as percents, 1 if as fractions."""
    vals = [v for c in cells.values() for v in c.get(PCT, [set(), []])[1] if v is not None]
    return 100.0 if vals and max(vals) > 1.5 else 1.0


def compare(cells):
    """Sample-size comparisons for one table, and published low-n cells (P5)."""
    scale = pct_scale(cells)
    res = {"pct_scale": scale, "control": {"cells": 0, "equal": 0, "ambiguous": 0}}
    for s in EXP:
        res[s] = {"cells": 0, "equal": 0, "less": 0, "greater": 0, "ambiguous": 0}
    examples = []
    for key, c in cells.items():
        pct = c.get(PCT)
        if pct is None:
            continue
        n_pct = _one_int(pct[0])
        pop = c.get(POP)
        if pop is not None:
            n_pop = _one_int(pop[0])
            if n_pct is None or n_pop is None:
                res["control"]["ambiguous"] += 1
            else:
                res["control"]["cells"] += 1
                res["control"]["equal"] += int(n_pop == n_pct)
        v = _one_value(pct[1])
        if n_pct is None or v is None or v / scale >= BELOW_ALL:
            continue
        frac = v / scale
        for s in EXP:
            e = c.get(s)
            if e is None:
                continue
            n_e = _one_int(e[0])
            if n_e is None:
                res[s]["ambiguous"] += 1
                continue
            r = res[s]
            r["cells"] += 1
            if n_e == n_pct:
                r["equal"] += 1
            elif n_e < n_pct:
                r["less"] += 1
            else:
                r["greater"] += 1
            ev = _one_value(e[1])
            est = n_pct * frac
            if ev is not None and n_e >= 60 and est < EST_LIMIT:
                examples.append(dict(zip(KEY, key), stat_var=s, sample_size=n_e, pct_exp=round(frac, 4),
                                     est_persons_with_expense=round(est, 1), value=ev))
    for r in [res["control"]] + [res[s] for s in EXP]:
        r["share_equal"] = round(r["equal"] / r["cells"], 4) if r["cells"] else None
    res["low_n_published"] = len(examples)
    return res, examples


def _share_grade(r):
    if r["cells"] < MIN_CELLS:
        return {"grade": "untestable", "cells": r["cells"],
                "reason": "fewer than %d comparable cells" % MIN_CELLS}
    v = r["equal"] / r["cells"]
    return {"value": round(v, 4), "cells": r["cells"], "grade": "held" if v >= SHARE else "failed"}


def grade(per_year, primary):
    """Grades P1-P5 exactly as pre-registered."""
    p = per_year.get(primary)
    if p is None:
        return {k: {"grade": "untestable", "reason": "no primary table"} for k in ("P1", "P2", "P3", "P4", "P5")}
    g = {"P1": _share_grade(p["meanEXP"]), "P2": _share_grade(p["medEXP"])}
    q = [y for y, r in per_year.items() if r["meanEXP"]["cells"] >= MIN_CELLS]
    bad = sorted(y for y in q if per_year[y]["meanEXP"]["equal"] / per_year[y]["meanEXP"]["cells"] < SHARE)
    if len(q) < MIN_YEARS:
        g["P3"] = {"grade": "untestable", "years": len(q), "reason": "fewer than %d qualifying years" % MIN_YEARS}
    else:
        g["P3"] = {"years": len(q), "years_below": bad, "grade": "failed" if bad else "held"}
    g["P4"] = _share_grade(p["control"])
    if g["P1"]["grade"] != "held":
        g["P5"] = {"grade": "not graded", "reason": "P1 did not hold"}
    else:
        n = p["low_n_published"]
        g["P5"] = {"value": n, "grade": "held" if n >= 1 else "failed"}
    return g


def code_lines(text):
    """[(line number, line)] of suppression-related lines, and whether the tested line is present."""
    lines = [(i, ln.rstrip()) for i, ln in enumerate(text.splitlines(), 1) if CODE_RX.search(ln)]
    found = re.sub(r"\s+", "", BUG_TEXT) in re.sub(r"\s+", "", text)
    return lines, found


def is_lfs(body):
    return body.startswith(b"version https://git-lfs")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def fetch(url, get=None, pause=None, tries=3):
    """('ok', body), ('404', b'') or (error status, b'') after `tries` attempts."""
    get = get or _get
    pause = pause or time.sleep
    status = "error"
    for k in range(tries):
        try:
            code, body = get(url)
        except Exception:
            code, body = None, b""
        if code == 200:
            return "ok", body
        if code == 404:
            return "404", b""
        status = "http%s" % code if code else "error"
        pause(10 * (k + 1))
    return status, b""


def run(out_dir, get=None, pause=None, delay=1.0):
    pause = pause or time.sleep
    os.makedirs(out_dir, exist_ok=True)
    out = {"version": VERSION, "repo": REPO, "app": APP}
    st, body = fetch(API + "/commits/main", get, pause)
    if st != "ok":
        out["error"] = "commit lookup " + st
        return _write(out_dir, out, [], [])
    sha = json.loads(body.decode("utf-8"))["sha"]
    out["sha"] = sha
    st, body = fetch(API + "/contents/" + APP + "?ref=" + sha, get, pause)
    if st != "ok":
        out["error"] = "folder listing " + st
        return _write(out_dir, out, [], [])
    names = sorted(x["name"] for x in json.loads(body.decode("utf-8")) if YEAR_RX.match(x.get("name", "")))
    st, body = fetch(RAW.format(sha=sha, path=CODE), get, pause)
    lines, found = code_lines(body.decode("utf-8", errors="replace")) if st == "ok" else ([], False)
    out["code"] = {"file": CODE, "status": st, "sha256": hashlib.sha256(body).hexdigest() if st == "ok" else "",
                   "tested_line": BUG_TEXT, "tested_line_found": found, "n_lines": len(lines)}

    files, per_year, examples = [], {}, []
    for name in names:
        path = APP + "/" + name
        pause(delay)
        st, body = fetch(RAW.format(sha=sha, path=path), get, pause)
        lfs = st == "ok" and is_lfs(body)
        if lfs:
            st, body = fetch(MEDIA.format(sha=sha, path=path), get, pause)
        info = {"file": name, "status": st, "lfs": lfs, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if st == "ok" else ""}
        files.append(info)
        if st != "ok":
            continue
        cells, stats, n = scan(body.decode("utf-8-sig", errors="replace"))
        res, ex = compare(cells)
        year = int(YEAR_RX.match(name).group(1))
        info.update(rows=n, cells=len(cells), stat_vars=sorted(stats))
        per_year[year] = res
        examples += [dict(e, year=year) for e in ex]
    out["files"] = files
    out["primary_year"] = max(per_year) if per_year else None
    out["per_year"] = {str(y): per_year[y] for y in sorted(per_year)}
    out["grades"] = grade(per_year, out["primary_year"])
    return _write(out_dir, out, examples, lines)


def _write(out_dir, out, examples, lines):
    with open(os.path.join(out_dir, "sumtab.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    rows = []
    for y, r in sorted(out.get("per_year", {}).items()):
        for part in ("control",) + EXP:
            rows.append(dict(year=y, part=part, **{k: r[part].get(k, "") for k in
                                                   ("cells", "equal", "less", "greater", "ambiguous", "share_equal")}))
    with open(os.path.join(out_dir, "per-year.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "part", "cells", "equal", "less", "greater", "ambiguous",
                                          "share_equal"])
        w.writeheader()
        w.writerows(rows)
    fields = ["year", "stat_var"] + list(KEY) + ["sample_size", "pct_exp", "est_persons_with_expense", "value"]
    with open(os.path.join(out_dir, "low-n-published.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(examples)
    with open(os.path.join(out_dir, "code-lines.txt"), "w", encoding="utf-8") as f:
        for i, ln in lines:
            f.write("%d: %s\n" % (i, ln))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args(argv)
    o = run(a.out_dir, delay=a.delay)
    print(json.dumps({k: o.get(k) for k in ("sha", "primary_year", "code", "grades", "error")}, indent=1))


if __name__ == "__main__":
    main()
