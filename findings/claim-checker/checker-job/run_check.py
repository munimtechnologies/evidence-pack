"""H-A checker job: run the frozen claimcheck 1.0.0 and its keyword baseline on every mutated
copy and on both unmutated cut texts (plan v5 section 8 step 5).

Inputs, in ./inputs: the mutation job's manifest.json, every file it lists, and recheck.json
(output of the job rwe-recheck-v1). labels.json must not be anywhere in the job folder.
The plan files are in ./plans and the frozen code in ./claimcheck (fetch_frozen.py).
Writes /out/checker/<file>.json, /out/baseline/<file>.json and /out/summary.json.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

from claimcheck import __version__, baseline, cli

TOOLS = {"tools": [{"name": "rwe_recheck", "file": "recheck.json", "rows": "rows",
                    "labels": ["label", "source"], "flags": "flags"}]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def problems_with(inputs, plans):
    found = []
    if __version__ != "1.0.0":
        found.append("claimcheck version is " + __version__)
    if any(Path(".").rglob("labels.json")):
        found.append("labels.json is in the job folder")
    if not (inputs / "recheck.json").is_file():
        found.append("inputs/recheck.json missing")
    if len(list(plans.glob("*.md"))) != 3:
        found.append("plans/ does not hold exactly 3 plan files")
    manifest = json.loads((inputs / "manifest.json").read_text(encoding="utf-8"))
    for c in manifest["copies"]:
        path = inputs / c["file"]
        if not path.is_file():
            found.append(c["file"] + " missing")
        elif sha256(path) != c["sha256"]:
            found.append(c["file"] + " SHA-256 differs from the manifest")
    return manifest, found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default="inputs")
    ap.add_argument("--plans", default="plans")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    inputs, plans, out = Path(a.inputs), Path(a.plans), Path(a.out_dir)
    manifest, problems = problems_with(inputs, plans)
    summary = {"checker": "claimcheck " + __version__, "problems": problems,
               "recheck_sha256": sha256(inputs / "recheck.json") if (inputs / "recheck.json").is_file() else None,
               "plans": {p.name: sha256(p) for p in sorted(plans.glob("*.md"))}, "files": []}
    out.mkdir(parents=True, exist_ok=True)
    if problems:
        (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(json.dumps(summary, indent=1))
        return 2
    (out / "checker").mkdir(exist_ok=True)
    (out / "baseline").mkdir(exist_ok=True)
    tools = inputs / "tools.json"
    tools.write_text(json.dumps(TOOLS, indent=1) + "\n")
    for c in manifest["copies"]:
        src = str(inputs / c["file"])
        cj = out / "checker" / (c["file"] + ".json")
        bj = out / "baseline" / (c["file"] + ".json")
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main([src, "--jobs", str(tools), "--plans", str(plans), "--json", str(cj)])
            baseline.main([src, "--json", str(bj)])
        cr = json.loads(cj.read_text(encoding="utf-8"))
        br = json.loads(bj.read_text(encoding="utf-8"))
        summary["files"].append({
            "file": c["file"], "package": c["package"], "copy": c["copy"],
            "checker_scored": cr["scored"], "checker_info": cr["info"],
            "checker_counts": cr["counts"], "checker_seconds": cr["runtime_seconds"],
            "baseline_flags": len(br["flags"]), "baseline_seconds": br["runtime_seconds"],
            "checker_sha256": sha256(cj), "baseline_sha256": sha256(bj)})
    summary["max_checker_seconds"] = max(f["checker_seconds"] for f in summary["files"])
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
