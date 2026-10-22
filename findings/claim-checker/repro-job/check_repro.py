"""Run step of the H-A public reproduction job (no network). Check that the files published at
tag v0.5.4 are byte for byte the sealed jobs' files, re-run the scorer as published at tag
v0.5.2 on them, and compare its output with the published results.

Expected hashes are copied from the sealed jobs' own output: labels and site file from
ha-mutate-v1 (log entry 7), report hashes from ha-check-v1 out/summary.json (log entry 8).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

LABELS_SHA256 = "2b6948969e8145ddfc8494dec4b76a665b122151f9036711475c951ec08f091b"
SITES_SHA256 = "ebc12371c04e30136bd1c0e5367bfe46ad10bc18cb52564485d833038b89d5b3"
MAX_SECONDS = 0.564
# file: (checker_sha256, baseline_sha256)
REPORTS = {
    "P4-cut.md": ("5519f0e5ec754cff2b882f4b78131255c318367befe8bee7ccc4c5e28bad2247",
                  "0bfd7680edadd40b2d6e91e43c1f28a89a3c2e502671b403a565a6b3a00ccca9"),
    "P4-copy01.md": ("8135a9bf2b674e9886db6a9db5fcf0b536bf24a3e643149ac9c6556511308544",
                     "60163214cf9f0292fe36a40517c6a8c7771e56eb586dbf57f3bbc75d8e56ce6c"),
    "P4-copy02.md": ("69c7664ef0f1cad2b2391a21f20d6c094d95a42daeed3e01f639ebe4d568958b",
                     "aa421bdcd9fa7b8ee54caf5482ec47d6ed8b45a31207b99979d0321e2b5c7519"),
    "P4-copy03.md": ("74363cee6a8c6709f84ddae72d84b50a6f621d5d00e3ba1be13962ed107c4569",
                     "ecd889f87df768193c6ee953ec20a1a2d3f39e4f1ccbd35668fe997aa84f1a08"),
    "P4-copy04.md": ("2a0bbcb37451ccff701c5074297f082198a48239a2eb066f310020a1e4b0f886",
                     "15e31180f402e1da370612f797782df5fac565ddd5e7c664a689c214b1bc2f96"),
    "P4-copy05.md": ("dd492afecbd91edcf0af4bc01ca7da12c33dcf6f3f5ef9a9663d4151158a8550",
                     "cb1d4d497e62f5c2366a66d734e9d2a072ac4217e18303368faef11ee5c0f15b"),
    "P4-copy06.md": ("a73858475a28a40dfe2fd849db131d74a3cfc1d7ec49289b970fe8d72e2ee673",
                     "d73b2edd734e46e14e626041d80f7ae6038d0c16e444f9f4375dfcecfaace63b"),
    "P4-copy07.md": ("2b1945556fdd860174037b90fad1d746b767c7da04d9f6e55c9dfd60a75ca20c",
                     "033ff351fef715197d37e67c88a95ba9d804171959c8bd56be29163dc86c4e37"),
    "P4-copy08.md": ("4f0d93c28d01277ded41801795463857731e180e0cf2c76ad4e2e6c85f276443",
                     "4ecf9570f1ea687198a2525eb49b5625189fb72328f37fe3fb47e69031206fd6"),
    "P5-cut.md": ("e182df49fda2079bdc22bf66f3e33200f2dbd7369a66d0e0ee51502282b0863e",
                  "c5029326a23ce45d49ea3e5f60cbd1af8a5418242d91520181b1734f0d60d2d6"),
    "P5-copy01.md": ("4aea3076568df8760792bb424825c431cb1dc7446be08c3c5b1161f1e6cff09a",
                     "93bfa40a9873e1c07cd7c1d713b04471a1cd01cb7eed6dc0d7e21fd22b482274"),
    "P5-copy02.md": ("31d230f7f22561d124d684501eac6a028d7cb65b70bf159be66c78f1954f5282",
                     "7cbb6a18cda1b8d5958abe7caf5fad4377801c555f0b9de46787e7eb57bafdf7"),
    "P5-copy03.md": ("133372795aa75621372d0581d717f4d51b05f3695aaa5febff15c14a256be8a0",
                     "ffa7bf84ed43e0398be773941196990b89ad0883b8550180b089206c4289958c"),
    "P5-copy04.md": ("96bc73a9ae8e041840f154866193d634a9c3167b834387e4adb9bccd1b00d21d",
                     "285768dd99a3884f6e01464470e4a47c04de9eb910b0fb413a8b19bf57c6d2ea"),
    "P5-copy05.md": ("8533208384dc341d00bfa1a97763a9f67a0a9d447cfca30f1bea53c67b3a0e04",
                     "14bff6b5079ec7cdd1e8fdc192790cb37934cf64da10291f5cd113406184b1b3"),
    "P5-copy06.md": ("1374e3f3c836c8b8f1f0e8c252c2ef85f1b64abc561f42fb9e4633c6443429b9",
                     "31345a6432a4be419e212cdfd8d6c1eeac41f784f011c3c3cb9c15b9aacf8ffc"),
    "P5-copy07.md": ("7ad170a8615e1cef61c141fef2ad546ed8cda4a5ec193a8ae4cb5d8b89ca9a6b",
                     "5f6235ba94e8287e48f9f43fd3a1ab179c7af76f7179d5b4a77a7cb6c573ff92"),
    "P5-copy08.md": ("b1c8b149264688a56ae4ecbec931a5776dac42d8c62bc7b44f3fdf2df09ce4c2",
                     "256a5d763f77da83f8d1e1bc1e57dfd6bc820342673402d04883eab33fa7b943"),
    "P5-copy09.md": ("26d8d23f3d1c71a562f78917178c80d98a32463756a28763c7bff38eacdb2ee4",
                     "9a41d3ddf9055ce4be7da670e8ad20e7e3ecd94af353231582b040abd6a321ce"),
    "P5-copy10.md": ("c3f0e44214701f86b800d1d61887f3fd3171e9b2fa87bc47bad3eb6566f258d5",
                     "05dd07cf774a2722920b493dc8d41704b8f845e3382fda52c56f805353875685"),
}
RUNS = (("results.json", False), ("results-adjudicated.json", True))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_files(pub):
    """Return a list of problems; empty when every published file is the sealed jobs' file."""
    pub = Path(pub)
    problems = []
    for name, want in (("labels.json", LABELS_SHA256), ("sites.json", SITES_SHA256)):
        if not (pub / name).is_file():
            problems.append(name + " missing")
        elif sha256(pub / name) != want:
            problems.append(name + " SHA-256 differs from log entry 7")
    summary = read_json(pub / "checker-out" / "summary.json")
    rows = {f["file"]: f for f in summary.get("files", [])}
    if set(rows) != set(REPORTS):
        problems.append("checker summary files differ from the 20 H-A texts")
    if summary.get("max_checker_seconds") != MAX_SECONDS:
        problems.append("checker summary max_checker_seconds differs from log entry 8")
    for name, (chk, base) in sorted(REPORTS.items()):
        row = rows.get(name, {})
        if row and (row.get("checker_sha256") != chk or row.get("baseline_sha256") != base):
            problems.append(name + ": summary hashes differ from the sealed job's")
        for kind, want in (("checker", chk), ("baseline", base)):
            path = pub / "checker-out" / kind / (name + ".json")
            if not path.is_file():
                problems.append(kind + "/" + name + ".json missing")
            elif sha256(path) != want:
                problems.append(kind + "/" + name + ".json SHA-256 differs from the sealed job's")
    if (pub / "labels.json").is_file() and (pub / "mutation-manifest.json").is_file():
        labels = read_json(pub / "labels.json")
        manifest = read_json(pub / "mutation-manifest.json")
        want = {c["file"]: c["sha256"] for c in labels.get("copies", [])}
        got = {c["file"]: c["sha256"] for c in manifest.get("copies", [])}
        if want != got:
            problems.append("mutation manifest copy hashes differ from labels.json")
    return problems


def compare(published, rerun):
    """Top-level keys whose values differ."""
    return [k for k in sorted(set(published) | set(rerun)) if published.get(k) != rerun.get(k)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pub", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pub, out = Path(a.pub), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    problems = check_files(pub)
    report = {"tag": "v0.5.4", "scorer_tag": "v0.5.2", "problems": problems, "runs": {}}
    if not problems:
        score = Path(__file__).resolve().parent / "score.py"
        for name, adjudicated in RUNS:
            target = out / ("rerun-" + name)
            cmd = [sys.executable, str(score), "--labels", str(pub / "labels.json"),
                   "--checker-out", str(pub / "checker-out")]
            if adjudicated:
                cmd += ["--adjudication", str(pub / "adjudication.json")]
            cmd += ["--out", str(target)]
            code = subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode
            published = pub / "results" / name
            if target.is_file():
                diff = compare(read_json(published), read_json(target))
                same = target.read_bytes() == published.read_bytes()
            else:
                diff, same = ["(no output)"], False
            report["runs"][name] = {"exit": code, "differing_keys": diff, "same_bytes": same}
            if code != 0 or diff:
                problems.append(name + ": the re-run differs from the published file")
    (out / "repro-check.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
