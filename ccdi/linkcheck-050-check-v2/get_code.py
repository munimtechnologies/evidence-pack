"""Setup step of linkcheck-050-v2: download, unchanged, this job's corrected check from
evidence-pack tag v0.9.2, LinkCheck 0.5.0 from tag v0.9.1, LinkCheck 0.4.0 (into old/) from tag
v0.8.9, and the snapshot finder from tag v0.8.0, and log SHA-256.

Every file from v0.9.1, v0.8.9 and v0.8.0 must have the SHA-256 that job linkcheck-050-v1 logged
on 2026-10-24 (compete-results/linkcheck-050-v1/stdout.txt), so the code under test is the
code that v1 tested; a mismatch stops the job. The v0.9.2 files are new and only logged.

Tag v0.9.2 holds the corrected grader. If it is not public yet, this waits for it (up to two
hours), so the job cannot run before the grader is published.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import time
import urllib.error
import urllib.request

ROOT = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
# (tag path, local name, SHA-256 logged by linkcheck-050-v1, or None for a new file)
FILES = (
    ("v0.9.2/ccdi/linkcheck-050-check-v2/README.md", "README.md", None),
    ("v0.9.2/ccdi/linkcheck-050-check-v2/check050.py", "check050.py", None),
    ("v0.9.2/ccdi/linkcheck-050-check-v2/test_check050.py", "test_check050.py", None),
    ("v0.9.1/ccdi/linkcheck-050-check-v1/README.md", "prereg/README-v1.md",
     "104c3a055d6cb1742ba4bf09d48bb24c3dfa21c2c36ad56ae893ad8f954d5313"),
    ("v0.9.1/linkcheck/linkcheck/__init__.py", "linkcheck/__init__.py",
     "7f05d67603cdd1dfeef8d75fbe5db95813f573c8e097241c1857aebff45c3941"),
    ("v0.9.1/linkcheck/linkcheck/core.py", "linkcheck/core.py",
     "e456b3f95df36a004a173a130bec174f2238dc464ff447b2f5d345b4a2421118"),
    ("v0.9.1/linkcheck/linkcheck/__main__.py", "linkcheck/__main__.py",
     "e2b8644394a1faab223697fed38719e0590363c4e9643c78ec27bc10fb44ae32"),
    ("v0.9.1/linkcheck/linkcheck/paging.py", "linkcheck/paging.py",
     "4e1c58edb7a502bcea76645932ce9e403a33ac593194d44aa820fc7d59be271f"),
    ("v0.9.1/linkcheck/linkcheck/ccdi.py", "linkcheck/ccdi.py",
     "d641847f074209ea38eb93936e628a96f21fc56554cc7201f196cfa719549de0"),
    ("v0.9.1/linkcheck/test_linkcheck.py", "test_linkcheck.py",
     "6d37a04355edcdab41a4f9331b9609594387c6be8781110a436222b177e8c0a4"),
    ("v0.9.1/linkcheck/test_paging.py", "test_paging.py",
     "5bd21b202e79be7a797c799991f3a27426f96595f2a3227fb2fd35429078f124"),
    ("v0.9.1/linkcheck/test_namespaces.py", "test_namespaces.py",
     "df35164228f3108f55b286607545c0cbdc8ab25cab427f285001bf21ea40e696"),
    ("v0.9.1/linkcheck/test_paging_body.py", "test_paging_body.py",
     "0678b3f820d32fae57f98bbad56506e8dd79bcfb8275b045707a97c7bd3af80f"),
    ("v0.9.1/linkcheck/test_ccdi.py", "test_ccdi.py",
     "88b82114d6261e9c88fb1e5ed35109e552b1df1ee8efe7c1130b2e41a59b4441"),
    ("v0.9.1/linkcheck/test_standards.py", "test_standards.py",
     "8fae5ea6054c8b4a29185100f9d3917b905b8f113f73348673ed7945558df220"),
    ("v0.9.1/linkcheck/examples/records.jsonl", "examples/records.jsonl",
     "b4071fc0526b1af1e4a03ca9d92a80d7314280f1f5f6b87f5de0e86e2617d3ff"),
    ("v0.9.1/linkcheck/examples/links.jsonl", "examples/links.jsonl",
     "55faed2e36ffaa9b34b9e48f08a0b340449b2a59de7ad1d4f115b8a058f5abbf"),
    ("v0.8.9/linkcheck/linkcheck/__init__.py", "old/linkcheck/__init__.py",
     "7f05d67603cdd1dfeef8d75fbe5db95813f573c8e097241c1857aebff45c3941"),
    ("v0.8.9/linkcheck/linkcheck/core.py", "old/linkcheck/core.py",
     "2233aa3b48d9a1f474dc069b6d425f4832fa3c84c3814723ff8cd4f23b63dbbf"),
    ("v0.8.9/linkcheck/linkcheck/__main__.py", "old/linkcheck/__main__.py",
     "709e0513dc5de1788aa67b68d0ca8f3d2ac391c1c689fac15ddca4eff31f9498"),
    ("v0.8.9/linkcheck/linkcheck/paging.py", "old/linkcheck/paging.py",
     "4e1c58edb7a502bcea76645932ce9e403a33ac593194d44aa820fc7d59be271f"),
    ("v0.8.9/linkcheck/linkcheck/ccdi.py", "old/linkcheck/ccdi.py",
     "22f046a2a3f41d83ce151e323fc65fb0ffe0e17141fbc2b51d8562244497bdeb"),
    ("v0.8.0/ccdi/linkcheck-repro-v2/ensure_snapshot2.py", "ensure_snapshot2.py",
     "edd42a221d2915d236dbfd70499b6d1a2fb5e29efa2f1a9bfceb1ae0f5db1a2d"))
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
    for path, name, pinned in FILES:
        body = download(ROOT + path)
        if name.endswith(".py") and not body.startswith(b'"""'):
            raise SystemExit("unexpected content for " + path)
        digest = hashlib.sha256(body).hexdigest()
        if pinned is not None and digest != pinned:
            raise SystemExit("SHA-256 of %s is %s, not the %s that linkcheck-050-v1 logged"
                             % (path, digest, pinned))
        dest = os.path.join(HERE, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(body)
        print(path, len(body), "bytes sha256", digest,
              "(as in v1)" if pinned else "(new)", flush=True)


if __name__ == "__main__":
    main()
