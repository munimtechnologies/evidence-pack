"""Setup step of linkcheck-repro: on a machine without the kept second snapshot, take a fresh
one with the census's own fetch_ccdi.py (tag v0.5.5, unchanged; about 3.5 hours, into raw/).

The kept snapshot's data volume exists on only one of the machines that run sealed jobs, and
a job cannot choose its machine. repro.py grades P5-P6 only on the kept snapshot.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import os
import subprocess
import sys

KEPT = "/data/ccdi-raw-snapshot2"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    kept = argv[0] if argv else KEPT
    if os.path.exists(os.path.join(kept, "subject", "chosen.json")):
        print("kept snapshot found under " + kept + "; nothing to fetch", flush=True)
        return 0
    print("kept snapshot not found under " + kept + "; taking a fresh snapshot", flush=True)
    code = subprocess.call([sys.executable, "fetch_ccdi.py"])
    print("fetch_ccdi.py exited with " + str(code), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
