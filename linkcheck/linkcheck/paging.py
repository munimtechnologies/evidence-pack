"""LinkCheck paging audit: entries a paged endpoint lost, with or without an error.

Some endpoints serve several sources side by side: page p of the response holds page p of
every source. A source can then lose entries on a page in two ways: its part of the page is
an error object, or it is simply shorter than it should be, with no error at all. MV2's
diagnostics of NCI's CCDI Data Federation found both (evidence-pack tag v0.5.12,
ccdi/diagnostics-v3). A client that checks only for error objects misses the second.

The audit counts entries per source on every page and compares each page with what the
source's total says it should hold: on page p, a source with total T should have
min(per_page, max(0, T - (p - 1) * per_page)) entries. Without a total, every page before the
source's last page with entries should be full, and later pages cannot be judged. It reports:
  1  loss flags: error pages, short pages and over-full pages where entries were expected;
  2  error pages past a source's end (some servers answer an exhausted source with an error
     object; nothing is lost there);
  3  page numbers missing from the walk, and pages that failed as a whole;
  4  per source: served, total, entries lost by kind, excess, and what is left unexplained;
  5  with totals, the last page the walk had to reach, and the pages a walker should have
     fetched again instead of stopping (0.3.1).

No entries is not the end (0.3.1). The CCDI aggregation layer answers every paging request
with HTTP 200, sends no link header, and serves a failed upstream call as a small error
object with no entries (evidence-pack tag v0.8.4, ccdi/aggregator-reading-v1). A client that
stops at the first page without entries stops early whenever that happens. With totals, a
walk is over only after the last page the largest total needs; before it, a page that failed
as a whole or holds no entries must be fetched again. body_counts() turns a parsed page body
into the counts the audit reads, and error_messages() says which error a page carried.

Counts in, counts out: no record ids. Standard library only.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import collections
import json
import sys

from . import core


def is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def expected(page, per_page, total):
    """Entries page `page` should hold for a source with `total` entries in all."""
    return min(per_page, max(0, total - (page - 1) * per_page))


def clean(pages):
    """Check the input and give every source name as a string."""
    out = {}
    for n, counts in pages.items():
        if not is_count(n) or n == 0:
            raise ValueError("page numbers must be positive integers")
        if counts is None:
            out[n] = None
            continue
        if not isinstance(counts, dict):
            raise ValueError("page %d: counts must be an object or null" % n)
        row = {}
        for src, c in counts.items():
            if c is not None and not is_count(c):
                raise ValueError("page %d: entries of %s must be a count or null" % (n, src))
            row[str(src)] = c
        out[n] = row
    return out


def clean_totals(totals):
    """{source: total} with sources as strings; null totals are left out."""
    totals = {str(s): t for s, t in (totals or {}).items() if t is not None}
    for s, t in totals.items():
        if not is_count(t):
            raise ValueError("the total of %s must be a count" % s)
    return totals


# ---------- page bodies ----------

def body_counts(body, source_key="source", data_key="data"):
    """Counts for one page of a side-by-side endpoint, from its parsed JSON body.

    A body that is a list holds one item per source, {source_key: name, data_key: [...]}; the
    source's count is the length of its list, or None when the item has no list (an error
    object). A body that is an object with an "errors" list is a page that failed as a whole:
    None. Anything else is rejected, never guessed."""
    if isinstance(body, dict) and isinstance(body.get("errors"), list):
        return None
    if not isinstance(body, list):
        raise ValueError("a page body must be a list of source items or an error object")
    counts = {}
    for item in body:
        if not isinstance(item, dict) or source_key not in item:
            raise ValueError("every item of a page body must name its source")
        src = str(item[source_key])
        if src in counts:
            raise ValueError("source %s appears twice on one page" % src)
        data = item.get(data_key)
        counts[src] = len(data) if isinstance(data, list) else None
    return counts


def error_messages(body):
    """Every error a parsed page body carries, as "kind: message", in body order: from a
    whole-page error object, or from the source items of a list body. [] if there is none."""
    items = [body] if isinstance(body, dict) else body if isinstance(body, list) else []
    out = []
    for item in items:
        errs = item.get("errors") if isinstance(item, dict) else None
        for e in errs if isinstance(errs, list) else []:
            if isinstance(e, dict):
                out.append("%s: %s" % (e.get("kind", ""), e.get("message", "")))
            else:
                out.append(str(e))
    return out


# ---------- where a walk ends ----------

def last_page(totals, per_page):
    """The last page a walk must reach: the page holding the last entry of the source with
    the largest total (0 if there are no entries at all)."""
    if not is_count(per_page) or per_page == 0:
        raise ValueError("per_page must be a positive integer")
    return max(((t + per_page - 1) // per_page for t in clean_totals(totals).values()),
               default=0)


def refetch_pages(pages, per_page, totals):
    """Pages up to last_page(totals) that were not walked, failed as a whole, or hold no
    entries from any source. A walk that stops at an empty page stops early at each of
    these; fetch them again instead."""
    pages = clean(pages)
    end = last_page(totals, per_page)
    return [n for n in range(1, end + 1)
            if n not in pages or pages[n] is None or not any(pages[n].values())]


# ---------- the audit ----------

def audit(pages, per_page, totals=None):
    """pages: {page number: {source: entries on that page, or None if the source's part of
    the page was an error}}. A page whose value is None failed as a whole: every source
    counts as an error there. A source absent from a page has 0 entries on it.
    totals: {source: expected total}, optional. Returns the aggregate report."""
    if not is_count(per_page) or per_page == 0:
        raise ValueError("per_page must be a positive integer")
    pages = clean(pages)
    totals = clean_totals(totals)
    numbers = sorted(pages)
    last = numbers[-1] if numbers else 0
    missing = [n for n in range(1, last + 1) if n not in pages]
    sources = sorted({s for n in numbers if pages[n] is not None for s in pages[n]}
                     | set(totals))
    flags, out = [], {}
    for src in sources:
        total = totals.get(src)
        got = {n: (None if pages[n] is None else pages[n].get(src, 0)) for n in numbers}
        end = max((n for n in numbers if got[n]), default=0)

        def want(n):
            if total is not None:
                return expected(n, per_page, total)
            return per_page if n < end else None

        row = {"total": total, "served": sum(c for c in got.values() if c),
               "pages_with_entries": sum(1 for c in got.values() if c),
               "error_pages": [], "short_pages": [], "over_pages": [],
               "errors_past_end": 0, "not_judged": 0, "errors_not_judged": 0,
               "lost": {"error_pages": 0, "short_pages": 0, "missing_pages": 0,
                        "pages_not_walked": 0},
               "excess": 0, "unexplained": None}
        for n in numbers:
            c, w = got[n], want(n)
            if w is None:
                if c is not None and c > per_page:
                    w = per_page
                else:
                    row["not_judged"] += 1
                    row["errors_not_judged"] += c is None
                    continue
            if c is None:
                if w == 0:
                    row["errors_past_end"] += 1
                    continue
                row["error_pages"].append(n)
                row["lost"]["error_pages"] += w
                kind = "error"
            elif c < w:
                row["short_pages"].append([n, w - c])
                row["lost"]["short_pages"] += w - c
                kind = "short"
            elif c > w:
                row["over_pages"].append([n, c - w])
                row["excess"] += c - w
                kind = "over"
            else:
                continue
            flags.append({"page": n, "source": src, "kind": kind, "entries": c, "expected": w})
        row["lost"]["missing_pages"] = sum(want(n) or 0 for n in missing)
        if total is not None:
            row["lost"]["pages_not_walked"] = max(0, total - last * per_page)
            row["unexplained"] = (total - row["served"] - sum(row["lost"].values())
                                  + row["excess"])
        out[src] = row
    flags.sort(key=lambda f: (f["page"], f["source"]))
    return {"tool": "linkcheck paging " + core.__version__, "per_page": per_page,
            "pages": len(numbers), "last_page": last, "missing_pages": missing,
            "whole_page_failures": [n for n in numbers if pages[n] is None],
            "required_last_page": last_page(totals, per_page) if totals else None,
            "refetch_pages": refetch_pages(pages, per_page, totals) if totals else [],
            "flags": flags,
            "flag_counts": dict(sorted(collections.Counter(f["kind"] for f in flags).items())),
            "sources": out}


# ---------- files ----------

def read_pages(path):
    """JSON Lines, one line per page: {"page": 3, "counts": {"A": 100, "B": null}}."""
    pages = {}
    for row in core.read_jsonl(path):
        if not isinstance(row, dict) or "page" not in row or "counts" not in row:
            raise ValueError("every line needs a page number and counts")
        n = row["page"]
        if not is_count(n) or n == 0:
            raise ValueError("page numbers must be positive integers")
        if n in pages:
            raise ValueError("page %d appears twice" % n)
        pages[n] = row["counts"]
    return pages


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="linkcheck.paging",
        description="Entries a paged multi-source endpoint lost, with or without an error.")
    ap.add_argument("--pages", required=True,
                    help='JSON Lines, one line per page: {"page": 3, "counts": {"A": 100, '
                         '"B": null}}. null for a source: its part of the page was an error; '
                         '"counts": null: the whole page failed')
    ap.add_argument("--per-page", type=int, required=True, help="page size the walk asked for")
    ap.add_argument("--totals", help="JSON object {source: total}, e.g. from a summary endpoint")
    ap.add_argument("--out", required=True, help="aggregate report (JSON)")
    args = ap.parse_args(argv)
    totals = None
    if args.totals:
        with open(args.totals, encoding="utf-8") as fh:
            totals = json.load(fh)
        if not isinstance(totals, dict):
            raise ValueError("--totals must hold a JSON object")
    report = audit(read_pages(args.pages), args.per_page, totals)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(json.dumps({"flag_counts": report["flag_counts"],
                      "refetch_pages": report["refetch_pages"],
                      "unexplained": {s: r["unexplained"] for s, r in report["sources"].items()}},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
