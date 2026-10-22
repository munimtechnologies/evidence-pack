"""Setup step of the H-A public reproduction job: fetch, from tag v0.5.4 of the public
repository, the published H-A labels, site file, mutation manifest, checker reports and
results, plus the scorer exactly as published at tag v0.5.2. Nothing else is fetched, and
the run steps have no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import hashlib
import os
import time
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/"
TAG = "v0.5.4"
CC = "findings/claim-checker/"
COPIES = (["P4-cut.md"] + ["P4-copy%02d.md" % i for i in range(1, 9)]
          + ["P5-cut.md"] + ["P5-copy%02d.md" % i for i in range(1, 11)])
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "pub")


def wanted():
    """(url, local path) pairs, labels.json first."""
    data = RAW + TAG + "/" + CC + "ha-data/"
    pairs = [(data + "labels.json", os.path.join(PUB, "labels.json")),
             (data + "sites.json", os.path.join(PUB, "sites.json")),
             (data + "mutation-manifest.json", os.path.join(PUB, "mutation-manifest.json")),
             (data + "checker-out/summary.json", os.path.join(PUB, "checker-out", "summary.json"))]
    for kind in ("checker", "baseline"):
        for c in COPIES:
            pairs.append((data + "checker-out/%s/%s.json" % (kind, c),
                          os.path.join(PUB, "checker-out", kind, c + ".json")))
    for name in ("results.json", "results-adjudicated.json"):
        pairs.append((RAW + TAG + "/" + CC + "ha-results/" + name,
                      os.path.join(PUB, "results", name)))
    pairs.append((RAW + TAG + "/" + CC + "score-job/adjudication.json",
                  os.path.join(PUB, "adjudication.json")))
    for name in ("score.py", "test_score.py"):
        pairs.append((RAW + "v0.5.2/" + CC + "score-job/" + name, os.path.join(HERE, name)))
    return pairs


def get(url, tries, wait=30):
    """The tag may not exist yet when the job starts, so the first file waits for it."""
    for i in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            if i == tries - 1:
                raise SystemExit("could not fetch %s: %s" % (url, err))
            time.sleep(wait)


for n, (url, path) in enumerate(wanted()):
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite " + path)
    data = get(url, 40 if n == 0 else 3)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    print(os.path.relpath(path, HERE).replace(os.sep, "/"), len(data), "bytes",
          hashlib.sha256(data).hexdigest())
