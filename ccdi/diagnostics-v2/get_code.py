"""Setup step of ccdi-diag2: download the published census and diagnostics code, unchanged,
from evidence-pack tags v0.5.5 (census) and v0.5.6 (diagnostics v1), and log SHA-256.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import urllib.request

ROOT = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
FILES = (("v0.5.5/ccdi/concordance-v1/", "analyze.py"),
         ("v0.5.5/ccdi/concordance-v1/", "fetch_ccdi.py"),
         ("v0.5.6/ccdi/diagnostics-v1/", "diag.py"))
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    for base, name in FILES:
        req = urllib.request.Request(ROOT + base + name, headers={"User-Agent": "MV2 of Munim, Inc."})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        if not body.startswith(b'"""'):
            raise SystemExit("unexpected content for " + name)
        with open(os.path.join(HERE, name), "wb") as fh:
            fh.write(body)
        print(base + name, len(body), "bytes sha256", hashlib.sha256(body).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
