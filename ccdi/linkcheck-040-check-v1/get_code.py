"""Setup step of linkcheck-040-v1: download, unchanged, LinkCheck 0.4.0 and this job's check from
evidence-pack tag v0.8.9, the census's reader from tag v0.5.5, the paging audit's reader from
tag v0.7.0, and the job code of the second reproduction (adapt() and the snapshot finder) from
tag v0.8.0, and log SHA-256.

Tag v0.8.9 holds the pre-registration. If it is not public yet, this waits for it (up to
two hours), so the job cannot run before its predictions are published.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import time
import urllib.error
import urllib.request

ROOT = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
FILES = (("v0.8.9/ccdi/linkcheck-040-check-v1/README.md", "README.md"),
         ("v0.8.9/ccdi/linkcheck-040-check-v1/check040.py", "check040.py"),
         ("v0.8.9/ccdi/linkcheck-040-check-v1/test_check040.py", "test_check040.py"),
         ("v0.8.9/linkcheck/linkcheck/__init__.py", "linkcheck/__init__.py"),
         ("v0.8.9/linkcheck/linkcheck/core.py", "linkcheck/core.py"),
         ("v0.8.9/linkcheck/linkcheck/__main__.py", "linkcheck/__main__.py"),
         ("v0.8.9/linkcheck/linkcheck/paging.py", "linkcheck/paging.py"),
         ("v0.8.9/linkcheck/linkcheck/ccdi.py", "linkcheck/ccdi.py"),
         ("v0.8.9/linkcheck/test_linkcheck.py", "test_linkcheck.py"),
         ("v0.8.9/linkcheck/test_paging.py", "test_paging.py"),
         ("v0.8.9/linkcheck/test_namespaces.py", "test_namespaces.py"),
         ("v0.8.9/linkcheck/test_paging_body.py", "test_paging_body.py"),
         ("v0.8.9/linkcheck/test_ccdi.py", "test_ccdi.py"),
         ("v0.8.9/linkcheck/examples/records.jsonl", "examples/records.jsonl"),
         ("v0.8.9/linkcheck/examples/links.jsonl", "examples/links.jsonl"),
         ("v0.5.5/ccdi/concordance-v1/analyze.py", "analyze.py"),
         ("v0.7.0/ccdi/paging-audit-v1/ccdi_pages.py", "ccdi_pages.py"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/repro2.py", "repro2.py"),
         ("v0.8.0/ccdi/linkcheck-repro-v2/ensure_snapshot2.py", "ensure_snapshot2.py"))
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
