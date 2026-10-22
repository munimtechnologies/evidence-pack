"""H-A mutation job for the claim-provenance checker (plan v5 sections 4.2-4.3, v7 4.3).

Reads the two hashed H-A base texts, checks their SHA-256 (whole and cut), checks every
hand-listed eligible site in sites.json against the cut text, draws up to 8 mutations per
module with seed 20261021, lays them out in copies under the collision rule, and writes
the mutated copies, the unmutated cut texts, labels.json and a label-free manifest.json
to --out-dir.

It shares no code with claimcheck. The sites were listed by hand from the plan's words,
so a grammar bug in the checker cannot define both the sites and the catches.

Readings (fixed before the job runs; see findings/claim-checker/mutation-notes.md):
- Draw: per module and package, the valid sites sorted by id are shuffled with one
  random.Random(seed), modules and packages in the order sites.json lists them. Each
  package takes up to 4; a package with fewer leaves the rest to the other (plan v4
  section 4); the total is capped at 8. Fewer than 8 valid sites is a shortfall.
- Layout: mutation k of a module goes to copy k. On a collision (or a copy that already
  holds that module), the job redraws from the module's undrawn sites in the same
  package, in shuffled order. If none fits, the drawn site goes to the first other copy
  it fits, or to a new copy. Collisions never drop a mutation; every event is logged.
- Collision: A's mutated line is a primary or expected evidence line of B, or the
  reverse, or both carry the same group.
- A site is invalid (excluded and reported, never repaired) when its line is outside
  the cut, in the reference list, a table header or separator, or its find text does
  not occur exactly once on the line.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

MARKERS = ("## Notes for the submitter", "Submitter notes")
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+\s*$")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _text(line):
    return line.decode("utf-8").rstrip("\r\n")


def cut_count(lines):
    """Kept line count under the plan v4 cut rule (as in hashjob.py)."""
    for i, line in enumerate(lines):
        if _text(line).startswith(MARKERS):
            j = i - 1
            while j >= 0 and _text(lines[j]).strip() == "":
                j -= 1
            if j >= 0 and _text(lines[j]).strip() == "---":
                return j
            return i
    return len(lines)


def load_base(path):
    data = Path(path).read_bytes()
    lines = data.splitlines(keepends=True)
    kept = cut_count(lines)
    cut = lines[:kept]
    return {"sha256_whole": sha256(data), "sha256_cut": sha256(b"".join(cut)),
            "cut_lines": kept, "lines": cut}


def site_problem(site, lines):
    """Why a site is invalid on these cut lines, or None."""
    n = site.get("line")
    if not isinstance(n, int) or not 1 <= n <= len(lines):
        return "line outside the cut text"
    texts = [_text(x) for x in lines]
    refs = next((i + 1 for i, t in enumerate(texts) if t.startswith("## References")), None)
    if refs is not None and n >= refs:
        return "in the reference list"
    text = texts[n - 1]
    if SEPARATOR.match(text):
        return "a table separator row"
    if text.startswith("|") and n < len(texts) and SEPARATOR.match(texts[n]):
        return "a table header row"
    find, replace = site.get("find", ""), site.get("replace")
    if not find or not isinstance(replace, str) or replace == find or "\n" in replace:
        return "find empty, or replace missing, unchanged or multi-line"
    count = text.count(find)
    if count != 1:
        return f"find text occurs {count} times on the line"
    for k in site.get("evidence", []):
        if not isinstance(k, int) or not 1 <= k <= len(lines):
            return "evidence line outside the cut text"
    return None


def draw(sites, modules, packages, rng, target, per_package):
    """Return (drawn, reserve, shortfall); drawn and reserve are keyed (module, package)."""
    drawn, reserve, shortfall = {}, {}, {}
    for m in modules:
        pools = {}
        for p in packages:
            pool = sorted((s for s in sites if s["module"] == m and s["package"] == p),
                          key=lambda s: s["id"])
            rng.shuffle(pool)
            pools[p] = pool
        take = {p: min(per_package, len(pools[p])) for p in packages}
        spare = max(0, target - sum(take.values()))
        for p in packages:
            extra = min(spare, len(pools[p]) - take[p])
            take[p] += extra
            spare -= extra
        for p in packages:
            drawn[(m, p)] = pools[p][:take[p]]
            reserve[(m, p)] = pools[p][take[p]:]
        shortfall[m] = max(0, target - sum(take.values()))
    return drawn, reserve, shortfall


def lines_of(site):
    return {site["line"], *site.get("evidence", [])}


def collides(a, b):
    if a["line"] in lines_of(b) or b["line"] in lines_of(a):
        return True
    return a.get("group") is not None and a.get("group") == b.get("group")


def blockers(site, copy):
    """Ids in this copy that block the site (same module or a collision)."""
    return [x["id"] for x in copy if x["module"] == site["module"] or collides(site, x)]


def layout(drawn, reserve, modules, package, log):
    n = max((len(drawn[(m, package)]) for m in modules), default=0)
    copies = [[] for _ in range(n)]
    for m in modules:
        spare = list(reserve[(m, package)])
        for k, site in enumerate(drawn[(m, package)]):
            hit = blockers(site, copies[k])
            if not hit:
                copies[k].append(site)
                continue
            log.append({"event": "collision", "package": package, "module": m,
                        "copy": k + 1, "site": site["id"], "with": hit})
            swap = next((s for s in spare if not blockers(s, copies[k])), None)
            if swap is not None:
                spare.remove(swap)
                spare.append(site)
                copies[k].append(swap)
                log.append({"event": "redrawn", "package": package, "module": m,
                            "copy": k + 1, "site": swap["id"], "replaces": site["id"]})
                continue
            j = next((i for i, c in enumerate(copies) if not blockers(site, c)), None)
            if j is None:
                copies.append([])
                j = len(copies) - 1
                log.append({"event": "new copy", "package": package, "copy": j + 1})
            copies[j].append(site)
            log.append({"event": "moved", "package": package, "module": m,
                        "copy": j + 1, "site": site["id"]})
    return copies


def apply(lines, sites):
    out = list(lines)
    for s in sites:
        i = s["line"] - 1
        body = out[i].rstrip(b"\r\n")
        end = out[i][len(body):]
        text = body.decode("utf-8")
        if text.count(s["find"]) != 1:
            raise ValueError(f"{s['id']}: find text not unique on line {s['line']}")
        out[i] = text.replace(s["find"], s["replace"]).encode("utf-8") + end
    return out


def label(site, base_lines, mutated_lines):
    i = site["line"] - 1
    return {"id": site["id"], "module": site["module"], "operator": site["operator"],
            "line": site["line"], "evidence": sorted(site.get("evidence", [])),
            "original": _text(base_lines[i]), "mutated": _text(mutated_lines[i]),
            "find": site["find"], "replace": site["replace"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default="sites.json")
    ap.add_argument("--base-dir", default=".")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    sites_bytes = Path(args.sites).read_bytes()
    spec = json.loads(sites_bytes.decode("utf-8"))
    modules, packages = spec["modules"], list(spec["packages"])
    report = {"sites_sha256": sha256(sites_bytes), "seed": spec["seed"], "problems": []}

    bases = {}
    for p in packages:
        info = spec["packages"][p]
        path = Path(args.base_dir) / info["file"]
        if not path.is_file():
            report["problems"].append(f"{p}: {info['file']} missing")
            continue
        base = load_base(path)
        for key in ("sha256_whole", "sha256_cut", "cut_lines"):
            if base[key] != info[key]:
                report["problems"].append(f"{p}: {key} is {base[key]}, expected {info[key]}")
        bases[p] = base
    ids = [s["id"] for s in spec["sites"]]
    if len(ids) != len(set(ids)):
        report["problems"].append("duplicate site ids")
    if report["problems"]:
        (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps(report, indent=1))
        return 2

    valid, invalid = [], []
    for s in spec["sites"]:
        why = "unknown package or module" if (
            s.get("package") not in bases or s.get("module") not in modules) else (
            site_problem(s, bases[s["package"]]["lines"]))
        (invalid if why else valid).append({"id": s["id"], "reason": why} if why else s)

    rng = random.Random(spec["seed"])
    drawn, reserve, shortfall = draw(valid, modules, packages, rng,
                                     spec["target_per_module"], spec["per_package"])
    log, copies_out = [], []
    for p in packages:
        lines = bases[p]["lines"]
        cut_name = f"{p}-cut.md"
        (out / cut_name).write_bytes(b"".join(lines))
        copies_out.append({"file": cut_name, "package": p, "copy": 0,
                           "sha256": sha256(b"".join(lines)), "mutations": []})
        for k, chosen in enumerate(layout(drawn, reserve, modules, p, log), 1):
            mutated = apply(lines, chosen)
            data = b"".join(mutated)
            name = f"{p}-copy{k:02d}.md"
            (out / name).write_bytes(data)
            copies_out.append({"file": name, "package": p, "copy": k, "sha256": sha256(data),
                               "mutations": [label(s, lines, mutated) for s in chosen]})

    planted = {m: {p: 0 for p in packages} for m in modules}
    for c in copies_out:
        for x in c["mutations"]:
            planted[x["module"]][c["package"]] += 1
    labels = {"plan": "findings/claim-checker eval-plan v5 + v6 + v7", "seed": spec["seed"],
              "sites_sha256": report["sites_sha256"],
              "base": {p: {k: bases[p][k] for k in ("sha256_whole", "sha256_cut", "cut_lines")}
                       for p in packages},
              "copies": copies_out, "layout_log": log, "invalid_sites": invalid}
    labels_bytes = (json.dumps(labels, indent=1, ensure_ascii=True) + "\n").encode("ascii")
    (out / "labels.json").write_bytes(labels_bytes)
    manifest = {"copies": [{k: c[k] for k in ("file", "package", "copy", "sha256")}
                           for c in copies_out],
                "base": labels["base"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    report.update({
        "labels_sha256": sha256(labels_bytes),
        "valid_sites": {m: {p: sum(1 for s in valid if s["module"] == m and s["package"] == p)
                            for p in packages} for m in modules},
        "invalid_sites": invalid,
        "planted": planted,
        "planted_total": sum(sum(v.values()) for v in planted.values()),
        "shortfall": shortfall,
        "copies": {p: sum(1 for c in copies_out if c["package"] == p and c["copy"]) for p in packages},
        "layout_events": {e: sum(1 for x in log if x["event"] == e)
                          for e in ("collision", "redrawn", "moved", "new copy")},
        "out_of_scope": spec.get("out_of_scope", {}),
    })
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
