"""Setup step of ccdi-reach-v1: download, unchanged, this job's probe, tests and
pre-registration from evidence-pack tag v0.9.8, and log SHA-256.

Tag v0.9.8 holds the pre-registration. If it is not public yet, this waits for it (up to
two hours), so the job cannot run before its predictions are published.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import time
import urllib.error
import urllib.request

ROOT = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
FILES = (("v0.9.8/ccdi/filter-reach-v1/README.md", "README.md"),
         ("v0.9.8/ccdi/filter-reach-v1/reachprobe.py", "reachprobe.py"),
         ("v0.9.8/ccdi/filter-reach-v1/test_reachprobe.py", "test_reachprobe.py"))
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
