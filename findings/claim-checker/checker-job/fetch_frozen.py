"""Setup step of the H-A checker job: fetch the frozen claimcheck 1.0.0 (tag v0.5.0) and the
three plan files the base texts cite (CODING-NOTES "H-A inputs") from the public repository.
Nothing else is fetched, and the run steps have no network.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import os
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/evidence-pack/v0.5.0/"
CODE = ("__init__.py", "__main__.py", "cli.py", "baseline.py", "grammar.py", "modules.py",
        "modules2.py", "modules3.py", "test_grammar.py", "test_modules.py",
        "test_modules2.py", "test_part3.py")
PLANS = ("spironolactone-nhanes-prereg-2026-10-15.md",
         "spironolactone-nhanes-followup-prereg-2026-10-15.md",
         "trinetx-consistency-prereg-6-results-2026-10-15.md")
HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(url, path):
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite " + path)
    data = urllib.request.urlopen(url, timeout=60).read()
    with open(path, "wb") as fh:
        fh.write(data)
    print(os.path.relpath(path, HERE), len(data), "bytes")


os.makedirs(os.path.join(HERE, "claimcheck"))
os.makedirs(os.path.join(HERE, "plans"))
for name in CODE:
    fetch(BASE + "claimcheck/" + name, os.path.join(HERE, "claimcheck", name))
for name in PLANS:
    fetch(BASE + "findings/" + name, os.path.join(HERE, "plans", name))
