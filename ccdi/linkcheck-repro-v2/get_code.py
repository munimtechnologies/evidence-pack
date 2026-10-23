"""Setup step of linkcheck-repro-v2: download, unchanged, the census code from evidence-pack tag
v0.5.5, the paging-audit reader from tag v0.7.0, and LinkCheck 0.3.0 plus the reproduction
code from tag v0.8.0, and log SHA-256.

Tag v0.8.0 holds the pre-registration. If it is not public yet, this waits for it (up to
two hours), so the job cannot run before its predictions are published.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import time
import urllib.error
import urllib.request

ROOT = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
FILES = (("v0.5.5/ccdi/concordance-v1/analyze.py", "analyze.py"),
         ("v0.5.5/ccdi/concordance-v1/fetch_ccdi.py", "fetch_ccdi.py"),
         ("v0.7.0/ccdi/paging-audit-v1/ccdi_pages.py", "ccdi_pages.py"),
         ("v0.8.0/linkcheck/linkcheck/__init__.py", "linkcheck/__init__.py"),
         ("v0.8.0/linkcheck/linkcheck/core.py", "linkcheck/core.py"),
         ("v0.8.0/linkcheck/linkcheck/__main__.py", "linkcheck/__main__.py"),
         ("v0.8.0/linkcheck/linkcheck/paging.py", "linkcheck/paging.py"),
         ("v0.8.0/linkcheck/test_linkcheck.py", "test_linkcheck.py"),
         ("v0.8.0/linkcheck/test_paging.py", "test_paging.py"),
         ("v0.8.0/linkcheck/test_namespaces.py", "test_namespaces.py"),
         ("v0.8.0/linkcheck/examples/records.jsonl", "examples/records.jsonl"),
         ("v0.8.0/linkcheck/examples/links.jsonl", "examples/links.jsonl"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/repro2.py", "repro2.py"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/test_repro2.py", "test_repro2.py"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/ensure_snapshot2.py", "ensure_snapshot2.py"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/fetch_robust.py", "fetch_robust.py"))
HERE = os.path.dirname(os.path.abspath(__file__))
TRIES, WAIT = 24, 300


def download(url):
    for n in range(1, TRIES + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "MV2 of Munim, Inc."})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 404 or n == TRIES:
                raise
            print("not public yet (404), try %d of %d: %s" % (n, TRIES, url), flush=True)
            time.sleep(WAIT)


def main():
    for path, name in FILES:
        body = download(ROOT + path)
        if name.endswith(".py") and not body.startswith(b'"""'):
            raise SystemExit("unexpected content for " + path)
        dest = os.path.join(HERE, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(body)
        print(path, len(body), "bytes sha256", hashlib.sha256(body).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
