"""Pre-registered probe of how the CCDI Data Federation's aggregation layer answers paging
requests (ccdi/aggregator-reading-v1; predictions A1-A6 in README.md).

Seven sequential GET requests: /info, and pages 1, 35 and 600 of /subject and of
/subject-mapping at per_page 100. Unfiltered pages only; no query by participant ID is ever
sent. Only aggregates leave the job: status, size, SHA-256, header names, the link header if
any, entry counts per source or domain, and whether a body is one of the aggregator's two
fixed /subject-mapping error objects. No response body is written out.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FED = "https://federation.ccdi.cancer.gov/api/v1"
UA = "MV2 of Munim, Inc. (mv2@munimtech.com); aggregate data-quality study; sequential requests"
PAUSE = 2
PER_PAGE = 100


def cpi_error(message):
    """The aggregator's fixed /subject-mapping error object (app/utils/cpiUtils.js)."""
    return {"errors": [{"kind": "NotFound", "method": "GET", "route": "/subject-mapping",
                        "message": message}]}


SERVER_ERROR = cpi_error("Server Error.")
NOT_FOUND = cpi_error("Participants IDs are not found.")
REQUESTS = (("info", "/info", None),
            ("subject-1", "/subject", 1),
            ("mapping-1", "/subject-mapping", 1),
            ("subject-35", "/subject", 35),
            ("mapping-35", "/subject-mapping", 35),
            ("subject-600", "/subject", 600),
            ("mapping-600", "/subject-mapping", 600))
LINK = re.compile(r'<([^>]*)>\s*;\s*rel\s*=\s*"?([^";,]+)"?')


def compact(obj):
    """Bytes of obj as JavaScript's JSON.stringify writes it (no spaces)."""
    return json.dumps(obj, separators=(",", ":")).encode()


def url_of(path, page):
    if page is None:
        return FED + path
    return FED + path + "?" + urllib.parse.urlencode({"page": page, "per_page": PER_PAGE})


def get(url, tries=3, wait=30):
    """(status, [(header, value)], body, seconds). 5xx and network errors are retried."""
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.status, list(r.headers.items()), r.read(), time.time() - t0
        except urllib.error.HTTPError as err:
            if err.code < 500 or i == tries - 1:
                return err.code, list(err.headers.items()), err.read(), time.time() - t0
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
            if i == tries - 1:
                return -1, [], str(err).encode(), time.time() - t0
        time.sleep(wait * (i + 1))


def link_rels(value):
    """{rel: page number or None} of a Link header value."""
    out = {}
    for target, rel in LINK.findall(value or ""):
        page = urllib.parse.parse_qs(urllib.parse.urlsplit(target).query).get("page")
        out[rel.strip().lower()] = int(page[0]) if page and page[0].isdigit() else None
    return out


def fixed_error(body):
    """'server_error' or 'not_found' when body is one of the aggregator's fixed
    /subject-mapping error objects, else None."""
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    if parsed == SERVER_ERROR:
        return "server_error"
    if parsed == NOT_FOUND:
        return "not_found"
    return None


def subject_sources(parsed):
    """{source: {"entries": n or None, "error": bool}} for an aggregated /subject page."""
    out = {}
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict) or "source" not in item:
            continue
        data = item.get("data")
        out[str(item["source"])] = {"entries": len(data) if isinstance(data, list) else None,
                                    "error": "errors" in item}
    return out


def mapping_domains(parsed):
    """{domain_name: entries} for a /subject-mapping page."""
    out = {}
    ids = parsed.get("participant_ids") if isinstance(parsed, dict) else None
    for e in ids if isinstance(ids, list) else []:
        if isinstance(e, dict):
            dom = str(e.get("domain_name"))
            out[dom] = out.get(dom, 0) + 1
    return out


def versions(obj, prefix=""):
    """[[path, value]] of every scalar whose key mentions 'version' (for /info). List items
    that name a source are labelled by it."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = prefix + "/" + str(k)
            if isinstance(v, (dict, list)):
                out += versions(v, p)
            elif "version" in str(k).lower():
                out.append([p, v])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            seg = str(v["source"]) if isinstance(v, dict) and "source" in v else str(i)
            out += versions(v, prefix + "/" + seg)
    return out[:100]


def header(headers, name):
    return next((v for k, v in headers if k.lower() == name), None)


def describe(name, path, page, status, headers, body, secs):
    """The aggregate record of one response."""
    links = [v for k, v in headers if k.lower() == "link"]
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    rec = {"name": name, "path": path, "page": page, "per_page": PER_PAGE if page else None,
           "status": status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
           "seconds": round(secs, 1), "header_names": sorted({k.lower() for k, _ in headers}),
           "content_type": header(headers, "content-type"),
           "content_length": header(headers, "content-length"),
           "link": links, "link_rels": link_rels(", ".join(links)),
           "fixed_error": fixed_error(body)}
    if path == "/subject":
        rec["sources"] = subject_sources(parsed)
        rec["entries"] = sum(s["entries"] or 0 for s in rec["sources"].values())
    elif path == "/subject-mapping":
        rec["domains"] = mapping_domains(parsed)
        rec["entries"] = sum(rec["domains"].values())
    else:
        rec["info_versions"] = versions(parsed)
    return rec


def grade(recs):
    """A1-A6 exactly as pre-registered in README.md."""
    r = {x["name"]: x for x in recs}
    paged = [x for x in recs if x["path"] != "/info"]
    s35, m35, s600, m600 = (r["subject-35"], r["mapping-35"], r["subject-600"],
                            r["mapping-600"])
    pcdc = [v for k, v in s35["sources"].items() if k.lower() == "pcdc"]
    g = {"A1": not any(x["link"] for x in recs),
         "A2": all(x["status"] == 200 for x in paged),
         "A3": (m600["status"] == 200 and m600["fixed_error"] == "not_found"
                and m600["bytes"] == len(compact(NOT_FOUND))),
         "A4": (s35["status"] == 200 and len(pcdc) == 1 and pcdc[0]["entries"] is None
                and pcdc[0]["error"]),
         "A5": m35["status"] == 200 and s35["entries"] > 0 and m35["entries"] == s35["entries"],
         "A6": s600["status"] == 200 and bool(s600["sources"]) and s600["entries"] == 0}
    return {k: "pass" if v else "fail" for k, v in g.items()}


def main(argv=None, fetch=None, pause=PAUSE):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    fetch = fetch or get
    recs = []
    for i, (name, path, page) in enumerate(REQUESTS):
        if i:
            time.sleep(pause)
        status, headers, body, secs = fetch(url_of(path, page))
        recs.append(describe(name, path, page, status, headers, body, secs))
        print(name, status, len(body), "bytes", round(secs, 1), "s", flush=True)
    out = {"probe": "ccdi/aggregator-reading-v1",
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "expected_error_bytes": {"server_error": len(compact(SERVER_ERROR)),
                                    "not_found": len(compact(NOT_FOUND))},
           "grades": grade(recs), "requests": recs}
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "probe1.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out["grades"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
