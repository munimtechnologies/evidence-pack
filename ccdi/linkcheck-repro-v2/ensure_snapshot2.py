"""Setup step of linkcheck-repro-v2: make sure there is a snapshot to read, and keep it.

  1  the kept second snapshot (/data/ccdi-raw-snapshot2), if this machine holds it;
  2  else the newest complete fresh snapshot under /data (a folder ccdi-raw-fresh-<UTC
     time> holding complete.json), kept by an earlier job on this machine;
  3  else a new fresh snapshot, taken by fetch_robust.py into /data/ccdi-raw-fresh-<UTC
     time> (about 3.5 hours), kept for later jobs on this machine.

A job cannot choose its machine, and each machine has its own data volume. The first
reproduction took its fresh snapshot inside the job's own folder, where it was lost when
the job ended (linkcheck-repro-v1).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import glob
import os
import subprocess
import sys
import time

KEPT, ROOT, PREFIX = "/data/ccdi-raw-snapshot2", "/data", "ccdi-raw-fresh-"


def complete(root):
    """Complete fresh snapshots under root, oldest first."""
    return sorted(p for p in glob.glob(os.path.join(root, PREFIX + "*"))
                  if os.path.exists(os.path.join(p, "complete.json")))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    kept = argv[0] if argv else KEPT
    root = argv[1] if len(argv) > 1 else ROOT
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        print("kept second snapshot found under " + kept + "; nothing to fetch", flush=True)
        return 0
    found = complete(root)
    if found:
        print("kept fresh snapshot found: " + found[-1] + "; nothing to fetch", flush=True)
        return 0
    target = os.path.join(root, PREFIX + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    print("no kept snapshot; taking a fresh one into " + target, flush=True)
    code = subprocess.call([sys.executable, "fetch_robust.py", target])
    print("fetch_robust.py exited with " + str(code), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
