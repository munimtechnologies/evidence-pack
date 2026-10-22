"""Setup step of the H-A score job: fetch the scorer exactly as published at tag v0.5.2
(findings/claim-checker/score-job/), before the checker job ran. Nothing else is fetched,
and the run steps have no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import urllib.request

BASE = ("https://raw.githubusercontent.com/munimtechnologies/evidence-pack/v0.5.2/"
        "findings/claim-checker/score-job/")
FILES = ("score.py", "test_score.py")
HERE = os.path.dirname(os.path.abspath(__file__))

for name in FILES:
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite " + path)
    data = urllib.request.urlopen(BASE + name, timeout=60).read()
    with open(path, "wb") as fh:
        fh.write(data)
    print(name, len(data), "bytes", hashlib.sha256(data).hexdigest())
