#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""fetch_deps: download the two unchanged modules that the v1.1 lookup code imports from
evidence-pack main (doi_hygiene.py, pubmed_commentin.py) into the current folder, and record the
commit in <out>/provenance.json. The v1.1 files themselves come with the job, not from main.

Usage: python fetch_deps.py /out
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

REPO = "munimtechnologies/evidence-pack"
UA = "mv2-lookup-v11/1.0 (MV2 of Munim, Inc.; mailto:mv2@munimtech.com)"
FROM_MAIN = ("doi_hygiene.py", "pubmed_commentin.py")
LOCAL = ("integrity_check.py", "commentin_check.py", "test_integrity_check.py", "test_commentin_check.py",
         "test_lookup_v11.py", "validate_v11.py")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main(out):
    os.makedirs(out, exist_ok=True)
    try:
        sha = json.loads(get(f"https://api.github.com/repos/{REPO}/commits/main"))["sha"]
    except Exception as e:
        print(f"commit not resolved ({e!r}); using main")
        sha = "main"
    files = {}
    for path in FROM_MAIN:
        data = get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{path}")
        with open(path, "wb") as f:
            f.write(data)
        files[path] = {"ref": sha, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    for path in LOCAL:
        with open(path, "rb") as f:
            data = f.read()
        files[path] = {"ref": "job", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    prov = {"main": sha, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": files}
    with open(os.path.join(out, "provenance.json"), "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=1)
    print(json.dumps({"main": sha, "files": len(files), "fetched_at": prov["fetched_at"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/out"))
