"""Setup step of ccdi-diag: download the published v1 census code, unchanged, from the
evidence-pack tag v0.5.5, so this job reuses exactly what ccdi-concord-v1 ran.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/v0.5.5/ccdi/concordance-v1/"
FILES = ("analyze.py", "fetch_ccdi.py")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    for name in FILES:
        req = urllib.request.Request(BASE + name, headers={"User-Agent": "MV2 of Munim, Inc."})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        if not body.startswith(b'"""'):
            raise SystemExit("unexpected content for " + name)
        with open(os.path.join(HERE, name), "wb") as fh:
            fh.write(body)
        print(name, len(body), "bytes sha256", hashlib.sha256(body).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
