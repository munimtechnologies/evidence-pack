"""Setup step of the CCDI concordance job: fetch, from two public NCI APIs, everything the
analysis reads, and log every request with its status, size and SHA-256.

- CCDI Data Federation Resource (https://federation.ccdi.cancer.gov/api/v1): subject
  summary, per-field subject counts, every page of /subject and of /subject-mapping.
  Unfiltered pages only: no query by participant ID is ever sent.
- NCI Genomic Data Commons (https://api.gdc.cancer.gov/cases): open-access demographic
  and diagnosis fields of every TARGET case.

Raw responses stay inside the job (raw/); only aggregates leave it (see analyze.py).
Requests are sequential, with a pause between pages.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import gzip
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request

FED = "https://federation.ccdi.cancer.gov/api/v1"
GDC = "https://api.gdc.cancer.gov/cases"
UA = "MV2 of Munim, Inc. (mv2@munimtech.com); aggregate data-quality study; sequential requests"
COUNT_FIELDS = ("sex", "race", "ethnicity", "vital_status", "age_at_vital_status", "depositions")
LADDER = (1000, 500, 250, 100)
PAUSE = 2
MAX_PAGES = 1500
GDC_FIELDS = ("submitter_id,project.project_id,demographic.sex_at_birth,demographic.race,"
              "demographic.ethnicity,demographic.vital_status,demographic.days_to_death,"
              "diagnoses.age_at_diagnosis,diagnoses.days_to_last_follow_up,"
              "follow_ups.days_to_follow_up")
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
LOG = []


def get(url, tries=4, wait=30):
    """(status, body). 5xx and network errors are retried; 4xx is returned as is."""
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                status, body = r.status, r.read()
        except urllib.error.HTTPError as err:
            status, body = err.code, err.read()
            if status < 500 or i == tries - 1:
                return status, body, time.time() - t0
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
            if i == tries - 1:
                return -1, str(err).encode(), time.time() - t0
        else:
            return status, body, time.time() - t0
        time.sleep(wait * (i + 1))


def save(rel, url):
    """Fetch url, store the body as raw/<rel>.gz, log it, return (status, parsed or None)."""
    status, body, secs = get(url)
    path = os.path.join(RAW, rel + ".gz")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(body)
    LOG.append({"file": rel, "url": url, "status": status, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 1),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    print(rel, status, len(body), "bytes", round(secs, 1), "s", flush=True)
    try:
        return status, json.loads(body)
    except ValueError:
        return status, None


def write_log():
    with open(os.path.join(RAW, "fetch-log.json"), "w", encoding="utf-8") as fh:
        json.dump(LOG, fh, indent=1)


def fed_url(path, **params):
    return FED + path + ("?" + urllib.parse.urlencode(params) if params else "")


def page_sizes(parsed):
    """{source: (all, n records)} for an aggregated /subject page."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        counts = ((item.get("summary") or {}).get("counts") or {})
        data = item.get("data")
        out[item["source"]] = (counts.get("all"), len(data) if isinstance(data, list) else None)
    return out


def full_page(sizes, per_page):
    """True when every source that returned records returned a full first page."""
    seen = False
    for total, n in sizes.values():
        if n is None or total is None:
            continue
        seen = True
        if n != min(per_page, total):
            return False
    return seen


def fetch_subjects():
    """Pick the largest per_page that every source honours, then walk every page."""
    for per_page in LADDER:
        status, parsed = save("subject/probe-%d.json" % per_page,
                              fed_url("/subject", page=1, per_page=per_page))
        sizes = page_sizes(parsed)
        if status == 200 and full_page(sizes, per_page):
            break
        time.sleep(PAUSE)
    else:
        raise SystemExit("no per_page value gave full first pages")
    alls = [t for t, _ in sizes.values() if t]
    last = math.ceil(max(alls) / per_page) if alls else 1
    with open(os.path.join(RAW, "subject", "chosen.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_page": per_page, "first_page": "probe-%d.json" % per_page,
                   "pages_expected": last}, fh)
    for page in range(2, min(last + 1, MAX_PAGES) + 1):
        time.sleep(PAUSE)
        status, parsed = save("subject/page-%04d.json" % page,
                              fed_url("/subject", page=page, per_page=per_page))
        if status == 200 and all(n == 0 for _, n in page_sizes(parsed).values()):
            break
    return per_page, last


def fetch_mappings(per_page, last):
    """/subject-mapping has no counts, so walk until a page comes back empty."""
    for page in range(1, min(last + 1, MAX_PAGES) + 1):
        status, parsed = save("mapping/page-%04d.json" % page,
                              fed_url("/subject-mapping", page=page, per_page=per_page))
        ids = parsed.get("participant_ids") if isinstance(parsed, dict) else None
        if status == 200 and not ids:
            break
        time.sleep(PAUSE)


def fetch_gdc():
    filters = json.dumps({"op": "in", "content": {"field": "project.program.name",
                                                  "value": ["TARGET"]}})
    start, size = 0, 5000
    while True:
        url = GDC + "?" + urllib.parse.urlencode({"filters": filters, "fields": GDC_FIELDS,
                                                  "size": size, "from": start,
                                                  "format": "json"})
        status, parsed = save("gdc/cases-%05d.json" % start, url)
        if status != 200 or not isinstance(parsed, dict):
            raise SystemExit("GDC fetch failed with status %s" % status)
        total = parsed["data"]["pagination"]["total"]
        start += size
        if start >= total:
            return
        time.sleep(PAUSE)


def main():
    if os.path.exists(RAW):
        raise SystemExit("refusing to overwrite " + RAW)
    os.makedirs(RAW)
    try:
        save("fed/subject-summary.json", fed_url("/subject/summary"))
        for field in COUNT_FIELDS:
            time.sleep(PAUSE)
            save("fed/count-%s.json" % field, fed_url("/subject/by/%s/count" % field))
        save("fed/info.json", fed_url("/info"))
        fetch_gdc()
        per_page, last = fetch_subjects()
        fetch_mappings(per_page, last)
    finally:
        write_log()


if __name__ == "__main__":
    main()
