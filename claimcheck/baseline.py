"""claimcheck keyword baseline (plan v4 section 5; unchanged in v5-v7): the primary
comparison for pass rule P4.

Flags every sentence that contains a module group's trigger words:
  R3: no difference | no effect | lower | less likely | absent | stronger
  R4: years | months | not yet | currently
  R2/R2b: of (nine|ten|N) | all | every | N (records|trials|hits)
  R5/R5b/R6: only | first | most | version | run | gate | pre-registered | registered
  R1/R1b/R7/R8: any number repeated in two sections, any negative SMD/DiD, "all N", "mg/kg"
Readings 45-48 in claimcheck/CODING-NOTES.md. Not frozen.

    python -m claimcheck.baseline <package.md> --json out.json

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import argparse
import json
import os
import re
import sys
import time

from . import grammar as g
from .modules import Flag


def _wb(pat):
    return r"(?<![\w\-.])(?:" + pat + r")(?![\w\-]|\.\S)"


# reading: word-bounded and case-insensitive, the stronger of the two literal readings
# (substring matching would also fire on "small", "overall" or "trunk").
GROUPS = (
    ("R3", re.compile(_wb(r"no difference|no effect|lower|less likely|absent|stronger"), re.I)),
    ("R4", re.compile(_wb(r"years|months|not yet|currently"), re.I)),
    ("R2/R2b", re.compile(_wb(r"of (?:nine|ten|\d+)|all|every|\d+ (?:records|trials|hits)"), re.I)),
    ("R5/R5b/R6", re.compile(_wb(r"only|first|most|version|run|gate|pre-registered|registered"),
                             re.I)),
)
NUMBER_GROUP = "R1/R1b/R7/R8"
_SIGNED_MEASURE = re.compile(_wb(r"SMDs?|DiDs?"))
_ALL_N = re.compile(_wb(r"all \d+"), re.I)
_MG_KG = re.compile(r"mg/kg", re.I)


def _units(doc):
    """(line, section key, sentence text) for every sentence of the cut text. reading: v4
    sentences of bullets, paragraphs, reference entries and table body rows; headings and
    table header rows are not sentences. The section is the ### heading, else the ## one.
    Quoted text is read like any other (v5's quote rule is for the checker, not the baseline)."""
    for ln in doc.lines:
        for s in doc.sentences(ln.no):
            yield ln, ln.h3 or ln.h2, s.text


def _key(n):
    return n.text.lstrip("-+" + g.MINUS)


def baseline(doc):
    """reading: one flag per sentence per trigger group, the group as the flag's module and
    the first trigger found as its span."""
    units = list(_units(doc))
    sections = {}                            # printed number (sign dropped) -> section keys
    for _, key, text in units:
        for n in g.numbers(text):
            sections.setdefault(_key(n), set()).add(key)
    flags = []
    for ln, key, text in units:
        for name, pat in GROUPS:
            m = pat.search(text)
            if m:
                flags.append(Flag(name, "keyword", ln.no, (), m.group(), "baseline trigger"))
        nums = g.numbers(text)
        repeated = [n for n in nums if len(sections[_key(n)]) > 1]
        negative = _SIGNED_MEASURE.search(text) and any(n.signed for n in nums)
        hit = (repeated[0].text if repeated else "negative SMD/DiD" if negative else
               (_ALL_N.search(text) or _MG_KG.search(text) or [None])[0])
        if hit:
            flags.append(Flag(NUMBER_GROUP, "keyword", ln.no, (), hit, "baseline trigger"))
    return flags


def main(argv=None):
    p = argparse.ArgumentParser(prog="claimcheck.baseline")
    p.add_argument("package")
    p.add_argument("--json", required=True)
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    with open(a.package, "rb") as fh:
        doc = g.Doc(fh.read().decode("utf-8"))
    flags = baseline(doc)
    counts = {}
    for f in flags:
        counts[f.module] = counts.get(f.module, 0) + 1
    out = {"package": os.path.basename(a.package), "checker": "keyword baseline",
           "lines_total": doc.total_lines, "lines_cut": doc.cut,
           "flags": [f.as_dict() for f in flags], "counts": counts,
           "runtime_seconds": round(time.perf_counter() - t0, 3)}
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print("%s: %d baseline flags" % (out["package"], len(flags)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
