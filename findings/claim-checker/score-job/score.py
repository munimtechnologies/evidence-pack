"""H-A scoring for the claim-provenance checker (plan v5 section 6, v7 6.1, mutation-notes
section 4). Written and published before the checker job has run.

Inputs: the mutation job's labels.json and the checker job's out/ folder (summary.json,
checker/<file>.json, baseline/<file>.json); optionally an adjudication file. Writes one
results JSON. It shares no code with claimcheck or the mutation job.

Readings (fixed before any checker output exists; see findings/claim-checker/scoring-notes.md):
- S1: only scored flags count; unscored info flags never count either way.
- S2: a flag's lines are its primary line plus its evidence lines (baseline flags: primary only).
- S3: a mutation is caught when a flag in the same copy has the mutated line among its lines
  (v5 6.0). Catches by the labelled module are reported too. A baseline flag is "of" a module
  when the module is one of its group's names ("R2/R2b").
- S4: secondary match (descriptive): a flag of the labelled module whose lines include the
  mutated line or one of that mutation's expected evidence lines.
- S5: C5's known residual flags (R5 at P5 L248 and L252) count for neither recall nor precision.
- S6: P3 is computed on the mutated copies. A true positive is a distinct (copy, module,
  primary line) whose lines include a mutated line of that copy. A false positive is a
  distinct (package, module, primary line) of every other flag. The cut texts are the 6.1
  prediction, not part of P3.
- S7: adjudication (v4 P3): [package, module, line] entries judged real but unlisted problems
  move from false to true positives. P3 is reported before and after; P4 compares the
  checker and the baseline before adjudication.
- S8: P2 needs ceil(5/8 x planted) catches per labelled module.
- S9: comparisons use exact fractions; printed values are rounded to 4 places.
- S10: nothing is scored unless labels.json has the SHA-256 logged in entry 7, the checker
  summary has no problems and prints claimcheck 1.0.0, and every copy has a checker and a
  baseline JSON whose SHA-256 equals the summary's.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

LABELS_SHA256 = "2b6948969e8145ddfc8494dec4b76a665b122151f9036711475c951ec08f091b"
CHECKER = "claimcheck 1.0.0"
MODULES = ("R1", "R1b", "R2", "R2b", "R3", "R4", "R5", "R5b", "R6", "R7", "R8")
C5 = {("P5", 248), ("P5", 252)}
Z = 1.959963984540054


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def num(x):
    return None if x is None else round(float(x), 4)


def wilson(k, n, z=Z):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def need(n):
    """P2: at least 5/8 of n, rounded up."""
    return (5 * n + 7) // 8


def lines(f):
    return {f["line"], *f.get("evidence", [])}


def of(f, module):
    return module in f["module"].split("/")


def counted(package, flags):
    """S1 and S5."""
    return [f for f in flags if f.get("scored", True)
            and not (of(f, "R5") and (package, f["line"]) in C5)]


def score_set(copies, flags_by_file, real=()):
    """Recall, precision and per-mutation results for one tool (S3-S7)."""
    muts, tp, fp, explained = [], set(), set(), set()
    for c in copies:
        if not c["copy"]:
            continue
        flags = counted(c["package"], flags_by_file[c["file"]])
        mutated = {m["line"] for m in c["mutations"]}
        for m in c["mutations"]:
            near = {m["line"], *m["evidence"]}
            hit = [f for f in flags if m["line"] in lines(f)]
            muts.append({"id": m["id"], "package": c["package"], "copy": c["copy"],
                         "module": m["module"], "operator": m["operator"], "line": m["line"],
                         "caught": bool(hit),
                         "caught_by": sorted({f["module"] for f in hit}),
                         "caught_labelled": any(of(f, m["module"]) for f in hit),
                         "secondary": any(of(f, m["module"]) and lines(f) & near
                                          for f in flags)})
        for f in flags:
            if lines(f) & mutated:
                tp.add((c["file"], f["module"], f["line"]))
                continue
            key = (c["package"], f["module"], f["line"])
            fp.add(key)
            if any(of(f, m["module"]) and lines(f) & set(m["evidence"]) for m in c["mutations"]):
                explained.add(key)
    real = {tuple(r) for r in real} & fp
    caught = sum(m["caught"] for m in muts)
    total = len(tp) + len(fp)
    return {"planted": len(muts), "caught": caught,
            "recall_f": Fraction(caught, len(muts)) if muts else None,
            "caught_labelled": sum(m["caught_labelled"] for m in muts),
            "secondary": sum(m["secondary"] for m in muts),
            "tp_flags": len(tp), "fp_flags": len(fp),
            "precision_f": Fraction(len(tp), total) if total else None,
            "precision_adjudicated_f": Fraction(len(tp) + len(real), total) if total else None,
            "fp_real_unlisted": sorted(real),
            "fp_explained_by_secondary": len(explained),
            "fp_list": sorted(fp), "mutations": muts}


def by_module(muts):
    out = {}
    for mod in MODULES:
        ms = [m for m in muts if m["module"] == mod]
        k = sum(m["caught"] for m in ms)
        out[mod] = {"planted": len(ms), "caught": k,
                    "caught_labelled": sum(m["caught_labelled"] for m in ms),
                    "secondary": sum(m["secondary"] for m in ms),
                    "need": need(len(ms)), "pass": k >= need(len(ms))}
    return out


def by_operator(muts):
    out = {}
    for m in muts:
        row = out.setdefault(m["module"] + " " + m["operator"],
                             {"planted": 0, "caught": 0, "secondary": 0})
        row["planted"] += 1
        row["caught"] += m["caught"]
        row["secondary"] += m["secondary"]
    return dict(sorted(out.items()))


def prediction(copies, flags_by_file):
    """v7 6.1: 0 scored flags on the unmutated cut texts, apart from C5."""
    other, c5 = [], []
    for c in copies:
        if c["copy"]:
            continue
        flags = [f for f in flags_by_file[c["file"]] if f.get("scored", True)]
        keep = counted(c["package"], flags)
        other += [[c["file"], f["module"], f["rule"], f["line"]] for f in keep]
        c5 += [[c["file"], f["module"], f["rule"], f["line"]] for f in flags if f not in keep]
    return {"holds": not other, "other_flags": other, "c5_flags": c5}


def public(s):
    """Drop the Fraction fields, printing their rounded values."""
    out = {k: v for k, v in s.items() if not k.endswith("_f")}
    for k, v in s.items():
        if k.endswith("_f"):
            out[k[:-2]] = num(v)
    return out


def integrity(labels_path, run_dir, labels, expect):
    found = []
    if sha256(labels_path) != expect:
        found.append("labels.json SHA-256 differs from log entry 7")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if summary.get("problems"):
        found.append("the checker job reported problems")
    if summary.get("checker") != CHECKER:
        found.append("the checker summary does not print " + CHECKER)
    rows = {f["file"]: f for f in summary.get("files", [])}
    if set(rows) != {c["file"] for c in labels["copies"]}:
        found.append("the checker summary files differ from the label copies")
    for c in labels["copies"]:
        row = rows.get(c["file"])
        for kind, key in (("checker", "checker_sha256"), ("baseline", "baseline_sha256")):
            path = run_dir / kind / (c["file"] + ".json")
            if not path.is_file():
                found.append(f"{kind}/{c['file']}.json missing")
            elif row is not None and sha256(path) != row[key]:
                found.append(f"{kind}/{c['file']}.json SHA-256 differs from the summary")
    return summary, found


def load_flags(run_dir, kind, copies):
    out = {}
    for c in copies:
        rep = json.loads((run_dir / kind / (c["file"] + ".json")).read_text(encoding="utf-8"))
        if kind == "checker" and rep.get("checker") != CHECKER:
            raise ValueError(c["file"] + ": checker is " + str(rep.get("checker")))
        out[c["file"]] = rep["flags"]
    return out


def run(labels_path, run_dir, real=(), expect=LABELS_SHA256):
    labels_path, run_dir = Path(labels_path), Path(run_dir)
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    summary, problems = integrity(labels_path, run_dir, labels, expect)
    if problems:
        return {"problems": problems}
    copies = labels["copies"]
    cf, bf = load_flags(run_dir, "checker", copies), load_flags(run_dir, "baseline", copies)
    ck, bl = score_set(copies, cf, real), score_set(copies, bf)
    modules = by_module(ck["mutations"])
    cr, br = ck["recall_f"], bl["recall_f"]
    cp, bp = ck["precision_f"], bl["precision_f"] or Fraction(0)
    return {
        "problems": [], "checker": CHECKER, "labels_sha256": expect,
        "plan": "findings/claim-checker eval-plan v5 + v6 + v7; scoring-notes S1-S10",
        "P1": {"planted": ck["planted"], "caught": ck["caught"], "recall": num(cr),
               "wilson95": wilson(ck["caught"], ck["planted"]),
               "caught_labelled": ck["caught_labelled"],
               "pass": cr is not None and cr >= Fraction(4, 5)},
        "P2": {"modules": modules, "pass": all(v["pass"] for v in modules.values())},
        "P3": {"tp_flags": ck["tp_flags"], "fp_flags": ck["fp_flags"],
               "precision": num(cp), "precision_adjudicated": num(ck["precision_adjudicated_f"]),
               "fp_real_unlisted": ck["fp_real_unlisted"], "fp_list": ck["fp_list"],
               "fp_explained_by_secondary": ck["fp_explained_by_secondary"],
               "pass": cp is not None and cp >= Fraction(1, 2),
               "pass_adjudicated": (ck["precision_adjudicated_f"] is not None
                                    and ck["precision_adjudicated_f"] >= Fraction(1, 2))},
        "P4": {"checker_precision": num(cp), "baseline_precision": num(bp),
               "checker_recall": num(cr), "baseline_recall": num(br),
               "precision_ok": cp is not None and cp >= 2 * bp,
               "recall_ok": cr is not None and br is not None and cr >= br - Fraction(1, 10),
               "pass": (cp is not None and cp >= 2 * bp and cr is not None
                        and br is not None and cr >= br - Fraction(1, 10))},
        "P6": {"max_checker_seconds": summary.get("max_checker_seconds"),
               "pass": summary.get("max_checker_seconds") is not None
               and summary["max_checker_seconds"] < 60},
        "prediction_6_1": prediction(copies, cf),
        "secondary": {"checker": ck["secondary"], "baseline": bl["secondary"]},
        "by_operator": by_operator(ck["mutations"]),
        "baseline": public({k: v for k, v in bl.items() if k != "mutations"}),
        "mutations": ck["mutations"], "baseline_mutations": bl["mutations"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--checker-out", required=True)
    ap.add_argument("--adjudication", help="JSON list of [package, module, line] judged real")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    real = []
    if a.adjudication:
        real = json.loads(Path(a.adjudication).read_text(encoding="utf-8"))
    res = run(a.labels, a.checker_out, real)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("mutations", "baseline_mutations", "by_operator")}, indent=1))
    return 2 if res["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
