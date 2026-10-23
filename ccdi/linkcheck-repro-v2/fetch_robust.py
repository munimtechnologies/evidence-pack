"""Take a fresh CCDI Data Federation snapshot that a transient empty page cannot cut short.

The census's fetcher (fetch_ccdi.py, tag v0.5.5) walks /subject and /subject-mapping until a
page comes back empty. In the third snapshot (linkcheck-repro-v1, 2026-10-23), page 345 of
/subject-mapping came back empty with HTTP 200 for a moment, so the walk stopped there and
29,435 Participant Index entries were never fetched. This module runs fetch_ccdi.py's own
main() and request code unchanged, with two changes:
  1  both walks go on to the page after the last one the largest source's total needs
     (pages_expected + 1), whatever they get on the way;
  2  a page before that which comes back empty with HTTP 200 is fetched again, up to
     RETRIES times with growing waits; the last answer is the one kept, and every attempt
     is in fetch-log.json.
A page where only some sources answer with an error object is not retried: that is what
the paging audit measures. The snapshot goes into the folder given on the command line
(for example /data/ccdi-raw-fresh-<UTC time>), with retries.json, and complete.json once
the whole fetch has finished, so a later job on the same machine can reuse it.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import math
import os
import sys
import time

import fetch_ccdi

RETRIES, RETRY_WAIT = 3, 60


def empty_subject(parsed):
    """An aggregated /subject page where no source returned a record list with entries."""
    return all(n == 0 for _, n in fetch_ccdi.page_sizes(parsed).values())


def empty_mapping(parsed):
    return not (parsed.get("participant_ids") if isinstance(parsed, dict) else None)


def walk(kind, endpoint, first, last, per_page, empty, get=None, pause=None):
    """Fetch pages first..last+1 of an endpoint into raw/<kind>/. Returns the pages that
    were fetched again: [{"page", "retries", "empty_after"}]."""
    save = get or fetch_ccdi.save
    gap = fetch_ccdi.PAUSE if pause is None else pause
    wait = RETRY_WAIT if pause is None else pause
    retried = []
    for page in range(first, min(last + 1, fetch_ccdi.MAX_PAGES) + 1):
        rel = "%s/page-%04d.json" % (kind, page)
        url = fetch_ccdi.fed_url(endpoint, page=page, per_page=per_page)
        status, parsed = save(rel, url)
        tries = 0
        while page <= last and status == 200 and empty(parsed) and tries < RETRIES:
            tries += 1
            time.sleep(wait * tries)
            status, parsed = save(rel, url)
        if tries:
            retried.append({"page": page, "retries": tries,
                            "empty_after": status == 200 and empty(parsed)})
        if page > last and status == 200 and empty(parsed):
            break
        time.sleep(gap)
    return retried


def fetch_subjects(retried):
    """fetch_ccdi.fetch_subjects, with the walk above."""
    for per_page in fetch_ccdi.LADDER:
        status, parsed = fetch_ccdi.save("subject/probe-%d.json" % per_page,
                                         fetch_ccdi.fed_url("/subject", page=1,
                                                            per_page=per_page))
        sizes = fetch_ccdi.page_sizes(parsed)
        if status == 200 and fetch_ccdi.full_page(sizes, per_page):
            break
        time.sleep(fetch_ccdi.PAUSE)
    else:
        raise SystemExit("no per_page value gave full first pages")
    alls = [t for t, _ in sizes.values() if t]
    last = math.ceil(max(alls) / per_page) if alls else 1
    with open(os.path.join(fetch_ccdi.RAW, "subject", "chosen.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"per_page": per_page, "first_page": "probe-%d.json" % per_page,
                   "pages_expected": last}, fh)
    retried["subject"] = walk("subject", "/subject", 2, last, per_page, empty_subject)
    return per_page, last


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: python fetch_robust.py <target folder>")
    target = argv[0]
    retried = {}
    fetch_ccdi.RAW = target
    fetch_ccdi.fetch_subjects = lambda: fetch_subjects(retried)
    fetch_ccdi.fetch_mappings = lambda per_page, last: retried.__setitem__(
        "mapping", walk("mapping", "/subject-mapping", 1, last, per_page, empty_mapping))
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fetch_ccdi.main()
    with open(os.path.join(target, "retries.json"), "w", encoding="utf-8") as fh:
        json.dump(retried, fh, indent=1, sort_keys=True)
    with open(os.path.join(target, "complete.json"), "w", encoding="utf-8") as fh:
        json.dump({"started_at": started,
                   "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "requests": len(fetch_ccdi.LOG)}, fh, indent=1)
    print("snapshot complete in " + target, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
