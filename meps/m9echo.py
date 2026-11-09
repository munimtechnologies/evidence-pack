# Copyright 2026 Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Census M9: two kinds of slip in MEPS Statistical Briefs that census M8 cannot see.

MV2 of Munim, Inc. Made by AI agents (Claude) working in MV2's name.
Pre-registration: findings/meps-m9-prereg-v1-2026-11-09.md (evidence-pack). Stdlib only. Brief pages live under
meps.ahrq.gov/data_files/publications/, which meps.ahrq.gov/robots.txt does not disallow; robots.txt is checked in
code before every fetch, and no data file is ever downloaded. Research information about published statistics, not
medical advice.

Census M8 compared the numbers in a brief's text with the figures the text cites. It cannot see:
  1. Echoes: the same sentence printed twice in one brief (for example once in Highlights and once in Findings)
     with one number different. A sentence is reduced to its skeleton (lower-case words, every number replaced by
     '#', figure and table references removed, '%' read as 'percent'). Two sentences in different text blocks of
     one brief with the same skeleton of at least ECHO_MIN tokens are an echo flag if exactly one of their numbers
     differs and both differing numbers have a decimal point.
  2. Count-percent pairs whose implied base is impossible: 'P percent ... (N million ...)' or
     'N million ... (P percent ...)'. With N and P read at their printed rounding, the base N / P x 100 lies in an
     interval. A pair is flagged 'over' if the whole interval is above CEILING million (more people than the U.S.
     has had in any MEPS year), and 'population' if the percent is stated 'of the population' (with no qualifier)
     and the interval misses POP_LO to POP_HI million.
Text is read everywhere on the page, inside and outside tables (each cell is its own block), except from a heading
'Definitions', 'Data source(s)', 'About MEPS(-HC)', 'References' or 'Suggested citation' until the next h1-h6
heading with another name (the stop rule of census M8 v0.2, reused from meps/m8text2.py).
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

from meps import m8text2 as m8

VERSION = "0.1.0"
UA = "MV2-evidence-pack/m9 (mv2@munimtech.com)"
ROBOTS = "https://meps.ahrq.gov/robots.txt"
URL = "https://meps.ahrq.gov/data_files/publications/st%d/stat%d.shtml"

ECHO_MIN = 8
CEILING = 345.0
POP_LO = 250.0
POP_HI = 345.0
SAMPLE = 40
FETCH_MIN = 530
CAP = 12

NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
WORD = re.compile(r"[a-z]+|#")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")
LEAD = r"(?:(?:about|approximately|nearly|roughly|almost|an\s+estimated)\s+)?"
GAP = r"((?:(?!percent|million|%)[^()]){0,80}?)"
PAIR_A = re.compile(r"(?<![\d.,])(\d+(?:\.\d+)?)\s*(?:percent\b|%)" + GAP + r"\(\s*" + LEAD +
                    r"(\d+(?:\.\d+)?)\s+million\b", re.I)
PAIR_B = re.compile(r"(?<![\d.,$])(\d+(?:\.\d+)?)\s+million\b" + GAP + r"\(\s*" + LEAD +
                    r"(\d+(?:\.\d+)?)\s*(?:percent\b|%)([^()]{0,60})\)", re.I)
CROSS = re.compile(r"[!?;]|(?<![A-Z])\.\s")
POP = re.compile(r"^\s*of\s+(?:the\s+)?(?:(?:u\.\s?s\.|us|nation'?s|civilian|noninstitutionalized|total|overall|"
                 r"entire|whole)\s+)*population(?:\s+in\s+\d{4})?\s*,?\s*$", re.I)
VALID = re.compile(r"(?:0|[1-9]\d*)(?:\.\d+)?")
# Controls (findings/meps-m8-flag-audit-results-v1-2026-11-09.md, exploratory slip found by eye in audit A8):
# Brief #450's Findings print 67.2 percent where its Highlights and Figure 2 print 7.2 (22.5 million people).
CONTROL_BRIEF = 450


def _val(t):
    return float(t.replace(",", ""))


def _digits(s):
    return "".join(ch for ch in s if ch.isdigit())


def _dec(t):
    return len(t.split(".")[1]) if "." in t else 0


def _half(t):
    return 0.5 * 10 ** -_dec(t)


def sentences(text):
    return [s.strip() for s in SENT.split(text or "") if s.strip()]


def skeleton(sentence):
    """(tokens, numbers): lower-case words with every number as '#', figure/table references removed."""
    s = m8.REF.sub(" ", (sentence or "").replace("%", " percent "))
    nums = NUM.findall(s)
    toks = tuple(WORD.findall(NUM.sub(" # ", s).lower()))
    return toks, nums


def edit_kind(a, b):
    """How the digit strings of two number texts differ: point, substitution, swap, extra digit or other."""
    da, db = _digits(a), _digits(b)
    if da == db:
        return "point"
    if len(da) == len(db):
        diff = [i for i in range(len(da)) if da[i] != db[i]]
        if len(diff) == 1:
            return "substitution"
        if (len(diff) == 2 and diff[1] == diff[0] + 1 and da[diff[0]] == db[diff[1]]
                and da[diff[1]] == db[diff[0]]):
            return "swap"
        return "other"
    s, l = (da, db) if len(da) < len(db) else (db, da)
    if len(l) - len(s) == 1 and any(l[:i] + l[i + 1:] == s for i in range(len(l))):
        return "extra digit"
    return "other"


def echoes(sents):
    """Echo flags from (block, sentence) pairs of one brief."""
    groups = {}
    for b, s in sents:
        toks, nums = skeleton(s)
        if len(toks) < ECHO_MIN or not nums:
            continue
        groups.setdefault(toks, []).append((b, s, nums))
    out = []
    for items in groups.values():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (b1, s1, n1), (b2, s2, n2) = items[i], items[j]
                if b1 == b2 or len(n1) != len(n2):
                    continue
                diff = [k for k in range(len(n1)) if _val(n1[k]) != _val(n2[k])]
                if len(diff) != 1:
                    continue
                a, c = n1[diff[0]], n2[diff[0]]
                if "." not in a or "." not in c:
                    continue
                out.append({"kind": "echo", "block": b1, "block2": b2, "a": a, "b": c, "edit": edit_kind(a, c),
                            "context": s1[:240], "context2": s2[:240]})
    out.sort(key=lambda r: (r["block"], r["block2"], r["a"], r["b"]))
    return out


def base_interval(n_txt, p_txt):
    """(lo, hi) in millions for the base N / P x 100, with N and P at their printed rounding."""
    n, p = float(n_txt), float(p_txt)
    hn, hp = _half(n_txt), _half(p_txt)
    lo = (n - hn) / (p + hp) * 100.0
    hi = (n + hn) / (p - hp) * 100.0 if p - hp > 0 else float("inf")
    return lo, hi


def pair_flags(n_txt, p_txt, pop):
    lo, hi = base_interval(n_txt, p_txt)
    kinds = []
    if lo > CEILING:
        kinds.append("over")
    if pop and (hi < POP_LO or lo > POP_HI):
        kinds.append("population")
    return kinds


def edits(t):
    """Every number text one digit edit away from t (substitute, delete or insert a digit, swap two adjacent ones)."""
    out = set()
    for i, ch in enumerate(t):
        if ch.isdigit():
            for d in "0123456789":
                if d != ch:
                    out.add(t[:i] + d + t[i + 1:])
            out.add(t[:i] + t[i + 1:])
            if i + 1 < len(t) and t[i + 1].isdigit() and t[i + 1] != ch:
                out.add(t[:i] + t[i + 1] + ch + t[i + 2:])
    for i in range(len(t) + 1):
        for d in "0123456789":
            out.add(t[:i] + d + t[i:])
    return sorted(s for s in out if s != t and VALID.fullmatch(s))


def repairs(n_txt, p_txt, pop):
    """(percent edits, count edits) that would clear every flag of the pair."""
    rp = [e for e in edits(p_txt) if 0 < float(e) <= 100 and not pair_flags(n_txt, e, pop)]
    rn = [e for e in edits(n_txt) if float(e) > 0 and not pair_flags(e, p_txt, pop)]
    return rp, rn


def find_pairs(text):
    """(pairs, skipped): count-percent pairs in one block; skipped counts pairs whose gap crosses a sentence."""
    text = text or ""
    out, skipped = [], 0
    for form, rx in (("A", PAIR_A), ("B", PAIR_B)):
        for m in rx.finditer(text):
            if form == "A":
                pct, gap, count = m.group(1), m.group(2), m.group(3)
                tail = gap
            else:
                count, gap, pct, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if CROSS.search(gap):
                skipped += 1
                continue
            if not 0 < float(pct) <= 100 or float(count) <= 0:
                continue
            pop = bool(POP.match(tail))
            lo, hi = base_interval(count, pct)
            flags = pair_flags(count, pct, pop)
            rp, rn = repairs(count, pct, pop) if flags else ([], [])
            out.append({"form": form, "pct": pct, "count": count, "pop": pop, "lo": lo, "hi": hi, "flags": flags,
                        "repairs_p": rp, "repairs_n": rn, "start": m.start(),
                        "context": text[max(0, m.start() - 60):m.end() + 40]})
    out.sort(key=lambda r: r["start"])
    return out, skipped


def all_blocks(html_text):
    """Text blocks in page order, reading inside every table too (each cell is its own block)."""
    n = m8._Nest()
    n.feed(html_text)
    n.close()
    p = m8._TextParser([True] * len(n.nested))
    p.feed(html_text)
    p.close()
    p._flush()
    return p.blocks


def check_page(html_text):
    """({'pairs': [...], 'echoes': [...]}, stats) for one brief page."""
    sents, pairs = [], []
    stats = {"blocks": 0, "sentences": 0, "pairs_skipped": 0, "stopped": 0}
    stopping = False
    for i, (tag, text) in enumerate(all_blocks(html_text)):
        nums = m8.numbers(text)
        if m8.heading_like(tag, text, nums):
            if m8.stop_heading(text):
                stopping = True
                stats["stopped"] = 1
                continue
            if stopping and tag not in m8.HEAD_TAGS:
                continue
            stopping = False
        elif stopping:
            continue
        stats["blocks"] += 1
        ss = sentences(text)
        stats["sentences"] += len(ss)
        sents.extend((i, s) for s in ss)
        found, skipped = find_pairs(text)
        stats["pairs_skipped"] += skipped
        for r in found:
            r["block"] = i
            pairs.append(r)
    return {"pairs": pairs, "echoes": echoes(sents)}, stats


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as f:
        return f.read()


def robots_check(get):
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(m8._decode(get(ROBOTS))[0].splitlines())
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
                text, raw = m8._decode(get(url))
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


def _is_control(f):
    if f["number"] != CONTROL_BRIEF:
        return False
    if f["kind"] == "echo":
        return {f["a"], f["b"]} == {"67.2", "7.2"}
    return f["a"] == "67.2" and f["b"] == "22.5"


def summarise(results, years, errors, sample=SAMPLE, fetch_min=FETCH_MIN):
    pair_rows, flags = [], []
    tot = {"blocks": 0, "sentences": 0, "pairs_skipped": 0, "stopped": 0}
    for n in sorted(results):
        res, st = results[n]
        for k in tot:
            tot[k] += st.get(k, 0)
        for p in res["pairs"]:
            r = dict(p, number=n, year=years.get(n, ""))
            pair_rows.append(r)
            if p["flags"]:
                flags.append(dict(r, kind="pair:" + "+".join(p["flags"]), a=p["pct"], b=p["count"]))
        for e in res["echoes"]:
            flags.append(dict(e, number=n, year=years.get(n, "")))
    for f in flags:
        f["key"] = hashlib.sha256(("m9|%s|%d|%d|%s|%s" % (f["kind"], f["number"], f["block"], f["a"], f["b"]))
                                  .encode()).hexdigest()
        f["control"] = _is_control(f)
    flags.sort(key=lambda f: f["key"])
    rank = 0
    for f in flags:
        if f["control"]:
            f["check_rank"], f["in_sample"] = "", False
            continue
        rank += 1
        f["check_rank"], f["in_sample"] = rank, rank <= sample
    p450 = [r for r in pair_rows if r["number"] == CONTROL_BRIEF]
    controls = {
        "pair_450": any(f["control"] and f["kind"].startswith("pair") and "population" in f["kind"]
                        and "7.2" in f["repairs_p"] for f in flags),
        "echo_450": any(f["control"] and f["kind"] == "echo" for f in flags),
        "neg_450_parsed": any(r["pct"] == "1.5" and r["count"] == "4.8" for r in p450),
        "neg_450_unflagged": any(r["pct"] == "1.5" and r["count"] == "4.8" and not r["flags"] for r in p450),
        "scope_181_flagged": any(f["number"] == 181 and f["kind"] == "echo" and {f["a"], f["b"]} == {"61.1", "61.6"}
                                 for f in flags)}
    ok = controls["pair_450"] and controls["echo_450"] and controls["neg_450_parsed"] and controls["neg_450_unflagged"]
    real = [f for f in flags if not f["control"]]
    kinds, edits_ = {}, {}
    for f in real:
        if f["kind"] == "echo":
            edits_[f["edit"]] = edits_.get(f["edit"], 0) + 1
        else:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    summary = {
        "version": VERSION, "briefs": len(years), "fetched": len(results),
        "errors": {str(k): v for k, v in sorted(errors.items())},
        "blocks": tot["blocks"], "sentences": tot["sentences"], "briefs_with_stop_heading": tot["stopped"],
        "pairs": len(pair_rows), "pairs_population": sum(1 for r in pair_rows if r["pop"]),
        "pairs_skipped_cross": tot["pairs_skipped"], "briefs_with_pairs": len(set(r["number"] for r in pair_rows)),
        "pair_flags": sum(1 for f in real if f["kind"] != "echo"), "pair_flag_kinds": kinds,
        "echo_flags": sum(1 for f in real if f["kind"] == "echo"), "echo_edits": edits_,
        "flagged_briefs": len(set(f["number"] for f in real)),
        "sample_size": sum(1 for f in flags if f["in_sample"]), "controls": controls,
        "gate": {"fetched": len(results), "min": fetch_min, "controls_ok": ok,
                 "passed": len(results) >= fetch_min and ok}}
    return summary, pair_rows, flags


def _cell(v):
    if isinstance(v, list):
        return "|".join(str(x) for x in v[:CAP])
    if isinstance(v, float):
        return "inf" if v == float("inf") else "%.1f" % v
    return v


def write_outputs(out_dir, summary, pair_rows, flags):
    pcols = ["number", "year", "block", "form", "pct", "count", "pop", "lo", "hi", "flags", "repairs_p", "repairs_n",
             "context"]
    with open(os.path.join(out_dir, "m9-pairs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(pcols)
        for r in pair_rows:
            w.writerow([_cell(r.get(c, "")) for c in pcols])
    fcols = ["check_rank", "in_sample", "control", "kind", "number", "year", "block", "block2", "a", "b", "edit",
             "lo", "hi", "repairs_p", "repairs_n", "context", "context2"]
    with open(os.path.join(out_dir, "m9-flags.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fcols)
        for r in flags:
            w.writerow([_cell(r.get(c, "")) for c in fcols])
    with open(os.path.join(out_dir, "m9-summary.json"), "w") as f:
        json.dump(summary, f, indent=1)


def main(argv=None, get=None, pause=None, allowed=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", default="findings/meps-brief-tables-v1/tables.csv")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--delay", type=float, default=3)
    ap.add_argument("--sample", type=int, default=SAMPLE)
    ap.add_argument("--fetch-min", type=int, default=FETCH_MIN)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    get = get or _get
    pause = pause or time.sleep
    if allowed is None:
        allowed = robots_check(get)
    years = m8.load_numbers(a.tables)
    results, errors, sha = run(sorted(years), get=get, pause=pause, allowed=allowed, delay=a.delay)
    summary, pair_rows, flags = summarise(results, years, errors, sample=a.sample, fetch_min=a.fetch_min)
    summary["sha256"] = {str(k): v for k, v in sorted(sha.items())}
    write_outputs(a.out_dir, summary, pair_rows, flags)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sha256", "errors")}, indent=1))
    print(json.dumps({"errors": len(summary["errors"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
