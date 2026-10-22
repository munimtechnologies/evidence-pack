"""claimcheck modules, part 3: R6-b and R7-b, the two modules that read files besides the
package. R6-b runs only with --plans and R7-b only with --jobs.

Coded to plan v5 section 3 (unchanged by v6 and v7). Where the plan leaves a choice open,
the reading taken here is listed in claimcheck/CODING-NOTES.md (49 onwards) and marked
"reading:". Not frozen.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import json
import os
import re
from dataclasses import dataclass

from . import grammar as g
from . import modules as m1
from .modules import Flag, _ev, mask_quotes
from .modules2 import PUNCT, _negated, _section_lines, _wb

# ---------------------------------------------------------------- R6-b plan files (v5)

_PREREG = re.compile(_wb("pre-registered"), re.IGNORECASE)
_PROPOSAL = re.compile(_wb("needed|propose|should|would|will"), re.IGNORECASE)
_SECTION_H = re.compile(r"#+\s+H(?![A-Za-z0-9_])")
_AFTER = re.compile(_wb("written|drafted|planned") + ".*?" + _wb("after") + ".*?"
                    + _wb("results?"), re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def plan_after_results(text):
    """reading: a plan file says it was written after results when one v4 sentence of its
    status note holds "written", "drafted" or "planned", then "after", then "result(s)", in
    that order (any case). The status note is the preamble (the lines before the first
    heading other than a leading "# " title) plus every section whose heading contains
    "status" (any case), each up to the next heading."""
    note, title_seen, preamble, in_status = [], False, True, False
    for line in g.read_lines(text):
        hm = _HEADING.match(line)
        if hm:
            if preamble and len(hm.group(1)) == 1 and not title_seen:
                title_seen = True
                continue
            preamble = False
            in_status = "status" in hm.group(2).lower()
            continue
        if preamble or in_status:
            note.append(line)
    return any(_AFTER.search(g.strip_emphasis(piece))
               for line in note for _, piece in g.split_sentences(line))


def load_plans(path):
    """{file name: written after results} for every .md file directly inside path."""
    out = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if name.endswith(".md") and os.path.isfile(full):
            with open(full, "rb") as fh:
                out[name] = plan_after_results(fh.read().decode("utf-8"))
    return out


def names_file(text, name):
    """reading: the file name appears with no letter, digit, "_", "-" or "." directly before
    it and no letter, digit, "_" or "-" directly after it ("/", "`" and a final "." are fine)."""
    i = text.find(name)
    while i >= 0:
        j = i + len(name)
        before = text[i - 1] if i else ""
        after = text[j] if j < len(text) else ""
        if (not (before.isalnum() or before in ("_", "-", "."))
                and not (after.isalnum() or after in ("_", "-"))):
            return True
        i = text.find(name, i + 1)
    return False


def _cited_plans(doc, text, plans, refs):
    """Plan files a sentence cites: named in the sentence itself, or named in the reference
    entry of one of its [n] citations. Returns (names, reference lines used)."""
    names, lines = {p for p in plans if names_file(text, p)}, set()
    for k in g.cite_keys(text):
        no = refs.get(k)
        if no is None:
            continue
        hit = {p for p in plans if names_file(doc.line(no).text, p)}
        if hit:
            names |= hit
            lines.add(no)
    return sorted(names), lines


def r6_b(doc, plans):
    """R6-b (v5): "pre-registered" in a sentence that cites no plan file, or whose cited plan
    file's status note says it was written after results. plans: {file name: after results}.
    reading: sentences of bullets, paragraphs and table body rows (headings are not
    sentences; reference entries are not read); section H and proposal sentences skipped."""
    if plans is None:
        return []
    section_h = {ln.no for ln in _section_lines(doc, lambda t: bool(_SECTION_H.match(t)))}
    refs = dict(doc.references())
    flags = []
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para", "table_row") or ln.no in section_h:
            continue
        for s in doc.sentences(ln.no):
            masked = mask_quotes(s.text)
            hits = list(_PREREG.finditer(masked))
            if not hits or _PROPOSAL.search(masked):
                continue
            names, lines = _cited_plans(doc, s.text, plans, refs)
            late = [p for p in names if plans[p]]
            for m in hits:
                if not names:
                    flags.append(Flag("R6", "b-no-plan", ln.no, (), m.group(),
                                      "'pre-registered' with no plan file cited"))
                elif late:
                    flags.append(Flag("R6", "b-after", ln.no, _ev(ln.no, lines), m.group(),
                                      "cited plan file says it was written after results",
                                      {"plans": late}))
    return flags


# ---------------------------------------------------------------- R7-b job files (v5)

ITEM_NOUNS = frozenset("row rows estimate estimates comparison comparisons interval intervals "
                       "CI CIs item items label labels tuple tuples result results".split())
_ROW_PMID = re.compile(r"(?<!\d)\d{6,9}(?!\d)")


@dataclass
class Tool:
    name: str                # the tool name as printed in the package
    file: str                # the job file, as written in the manifest
    rows: list               # the file's rows (dicts)
    labels: tuple            # row keys whose values are the labels
    flags: str = ""          # row key holding the row's flag list ("" if none)

    def texts(self, row):
        return [str(row.get(k, "")) for k in self.labels]


def load_manifest(path):
    """reading: the manifest is {"tools": [{"name", "file", "rows", "labels", "flags"}]};
    "file" is relative to the manifest, "rows" is the key of the file's row list, "labels"
    the row keys read as labels and "flags" the row key of its flag list (optional)."""
    with open(path, "rb") as fh:
        man = json.loads(fh.read().decode("utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    tools = []
    for t in man["tools"]:
        with open(os.path.join(base, t["file"]), "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))
        tools.append(Tool(t["name"], t["file"], data[t.get("rows", "rows")],
                          tuple(t.get("labels", ("label",))), t.get("flags", "")))
    return tools


def package_rows(doc, tool):
    """reading: a job file can serve several packages. A row belongs to this package when a
    6-9 digit run in its labels equals a PMID-like run anywhere in the cut text; when no row
    holds such a run, every row belongs."""
    pmids = set()
    for ln in doc.lines:
        pmids.update(m1._PMID_LIKE.findall(ln.text))
    tagged = [(row, set(_ROW_PMID.findall(" ".join(tool.texts(row))))) for row in tool.rows]
    if not any(p for _, p in tagged):
        return list(tool.rows)
    return [row for row, p in tagged if p & pmids]


def file_counts(doc, tool):
    """The counts a stated count may match: the package's rows, and those of them flagged."""
    rows = package_rows(doc, tool)
    counts = {len(rows)}
    if tool.flags:
        counts.add(sum(1 for r in rows if r.get(tool.flags)))
    return counts


def stated_counts(text):
    """reading: an unsigned G1 integer (or one..twenty, any case) followed, with at most 3
    words in between, by a noun of ITEM_NOUNS. Returns [(start, end, value)]."""
    toks = [(m.start(), m.group()) for m in re.finditer(r"\S+", text)]
    ints = {(n.start, n.end): int(n.value) for n in g.numbers(text)
            if not (n.signed or n.pct or n.dollar or n.decimals or n.text.startswith("+"))}
    out = []
    for k, (a, tok) in enumerate(toks):
        core = tok.strip(PUNCT)
        if not core:
            continue
        ca = a + tok.find(core)
        value = g.WORD_VALUE.get(core.lower(), ints.get((ca, ca + len(core))))
        if value is None:
            continue
        if any(t.strip(PUNCT) in ITEM_NOUNS for _, t in toks[k + 1:k + 5]):
            out.append((ca, ca + len(core), value))
    return out


def _letter_bounded(sur):
    return re.compile(r"(?<![^\W\d_])" + re.escape(sur) + r"(?![^\W\d_])", re.IGNORECASE)


def sentence_names(text, surnames):
    """reading: the names of a sentence are the surnames of its R5 author-year candidates,
    plus every reference first-author surname found in it word-bounded (case-sensitive)."""
    names = {c[2] for c in m1.author_year_candidates(text)}
    names.update(s for s in surnames if g.find_word(text, s))
    return sorted(names)


def r7_b(doc, tools):
    """R7-b (v5): in a sentence that names a tool, a name absent from the tool file's labels,
    or a stated count of checked items that matches none of the file's counts. reading:
    sentences of bullets, paragraphs and table body rows; names and counts read with quotes
    masked; a name is absent when no label of any row holds it letter-bounded (any case)."""
    if not tools:
        return []
    surnames = {r.surname for r in m1.references(doc) if r.surname}
    flags = []
    for tool in tools:
        counts = file_counts(doc, tool)
        for ln in doc.lines:
            if ln.kind not in ("bullet", "para", "table_row"):
                continue
            for s in doc.sentences(ln.no):
                text = mask_quotes(s.text)
                if not g.find_word(text, tool.name):
                    continue
                for start, end, value in stated_counts(text):
                    if not _negated(text, start, value) and value not in counts:
                        flags.append(Flag("R7", "b-count", ln.no, (), text[start:end],
                                          "stated count matches no count of the job file",
                                          {"tool": tool.name, "stated": value,
                                           "file_counts": sorted(counts)}))
                for sur in sentence_names(text, surnames):
                    pat = _letter_bounded(sur)
                    if not any(pat.search(t) for row in tool.rows for t in tool.texts(row)):
                        flags.append(Flag("R7", "b-name", ln.no, (), sur,
                                          "name absent from the job file's labels",
                                          {"tool": tool.name, "file": tool.file}))
    return sorted(flags, key=lambda f: (f.line, f.rule, f.span))


def check(doc, plans=None, tools=None):
    """R6-b and R7-b; each returns nothing unless its input is given."""
    return r6_b(doc, plans) + r7_b(doc, tools)
