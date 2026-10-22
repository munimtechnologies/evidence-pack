"""claimcheck modules, part 1: R1, R1b, R5 and R6-a.

Coded to the evaluation plan in findings/claim-checker/: v5 section 3 as amended by v6
(G1-G5 CI tuples, R1 by position, R1b-b value attribution, R5 mapping and author-year
candidates) and v7 (G1 governs every number). Where the plans leave a choice open, the
reading taken here is listed in claimcheck/CODING-NOTES.md and marked "reading:".
R2, R2b, R3, R4, R5b, R6-b, R7 and R8 come in part 2. Not frozen.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import re
from dataclasses import dataclass, field

from . import grammar as g

APOS = "'" + chr(0x2019)


@dataclass
class Flag:
    module: str
    rule: str
    line: int                # primary line
    evidence: tuple = ()     # every other line the finding relies on, sorted
    span: str = ""
    reason: str = ""
    data: dict = field(default_factory=dict)
    scored: bool = True

    def as_dict(self):
        return {"module": self.module, "rule": self.rule, "line": self.line,
                "evidence": list(self.evidence), "span": self.span, "reason": self.reason,
                "data": self.data, "scored": self.scored}


def _ev(primary, lines):
    return tuple(sorted(set(lines) - {primary}))


def mask_quotes(s):
    """v5 text read: quoted text is never read for triggers. reading: the quoted characters
    become spaces; straight quotes toggle, curly quotes open and close."""
    out, quoted = [], False
    for c in s:
        if c == '"':
            quoted = not quoted
        elif c == g.LDQUO:
            quoted = True
        elif c == g.RDQUO:
            quoted = False
        elif quoted:
            c = " "
        out.append(c)
    return "".join(out)


# ---------------------------------------------------------------- CI tuples in place

@dataclass(frozen=True)
class Placed:
    """A CI tuple and where it was read."""
    line: int
    table: int               # index into Doc.tables, -1 in prose
    cell: int                # column index in a table row, -1 in prose
    text: str                # the sentence or cell (emphasis removed) it was read from
    t: g.CITuple


def placed_tuples(doc):
    """Every CI tuple of the cut text, in reading order. Prose is read sentence by sentence
    (bullets, paragraphs, reference entries; reading: headings hold no sentences), tables
    cell by cell."""
    out = []
    for ln in doc.lines:
        if ln.kind == "table_row":
            for c, cell in enumerate(g.split_cells(ln.raw)):
                text = g.strip_emphasis(cell)
                out.extend(Placed(ln.no, ln.table, c, text, t) for t in g.ci_tuples(text))
        elif ln.kind in ("bullet", "para", "ref"):
            for s in doc.sentences(ln.no):
                out.extend(Placed(ln.no, -1, -1, s.text, t) for t in g.ci_tuples(s.text))
    return out


def _tuple_text(p):
    return p.text[p.t.est.start:p.t.hi.end]


def _abs3(p):
    return (abs(p.t.est.value), abs(p.t.lo.value), abs(p.t.hi.value))


# ---------------------------------------------------------------- R1, R1b-a

def r1(doc, tuples=None):
    """R1 (v6): two tuples outside one table that share two of their three values, compared
    position by position as absolute values, and differ in the third."""
    tuples = placed_tuples(doc) if tuples is None else tuples
    flags = []
    for i, a in enumerate(tuples):
        va = _abs3(a)
        for b in tuples[i + 1:]:
            if a.table >= 0 and a.table == b.table:
                continue
            same = [x == y for x, y in zip(va, _abs3(b))]
            if sum(same) != 2:
                continue
            what = ("estimate", "first bound", "second bound")[same.index(False)]
            flags.append(Flag("R1", "twin", b.line, _ev(b.line, [a.line]), _tuple_text(b),
                              "CI tuple shares two values with line %d but its %s differs"
                              % (a.line, what),
                              {"earlier": _tuple_text(a), "later": _tuple_text(b)}))
    return flags


def r1b_a(doc, tuples=None):
    """R1b-a: a CI tuple whose signed estimate lies outside its own signed interval."""
    tuples = placed_tuples(doc) if tuples is None else tuples
    flags = []
    for p in tuples:
        lo, hi = sorted((p.t.lo.value, p.t.hi.value))
        if not lo <= p.t.est.value <= hi:
            flags.append(Flag("R1b", "a", p.line, (), _tuple_text(p),
                              "estimate lies outside its own interval"))
    return flags


# ---------------------------------------------------------------- R1b-b

MEASURES = (                 # (name, ((token, ignore case), ...)); abbreviations case-sensitive
    ("SMD", (("SMD", False),)),
    ("MD", (("MD", False),)),
    ("DiD", (("DiD", False), ("DiDs", False), ("difference-in-difference", True),
             ("difference-in-differences", True))),
    ("log ratio", (("log ratio", True),)),
    ("risk difference", (("risk difference", True),)),
)
_CONVENTION = re.compile(r"(negative|positive)( \w+){0,2} (=|favou?rs?|means?|for benefit)"
                         r"|sign convention|signs are as printed", re.IGNORECASE)


def _hits(text, tokens):
    out = []
    for tok, ic in tokens:
        out.extend((i, i + len(tok)) for i in g.find_word(text, tok, ignore_case=ic))
    return out


def _measure_values(text, tokens, named):
    """G1 numbers of one sentence or cell that are values of one measure (v6 attribution):
    (i) the estimate and bounds of a CI tuple when the measure is named in the tuple's clause
    (or named is True: the parent bullet, the cell or its column header names it);
    (ii) a number directly after the measure's token, optionally after "about"."""
    hits = _hits(text, tokens)
    vals = []
    for t in g.ci_tuples(text):
        a, b = g.clause_span(text, t.est.start)    # reading: the clause holding the estimate
        if named or any(a <= i and j <= b for i, j in hits):
            vals.extend((t.est, t.lo, t.hi))
    starts = {n.start: n for n in g.numbers(text)}
    for _, j in hits:
        if text.startswith(" about ", j):
            p = j + 7
        elif text.startswith(" ", j):
            p = j + 1
        else:
            continue
        if p in starts:
            vals.append(starts[p])
    return vals


def _parent_bullet(doc, ln):
    """reading: the nearest earlier bullet with a smaller indent, not crossing a heading."""
    if ln.kind != "bullet" or ln.indent == 0:
        return None
    for no in range(ln.no - 1, 0, -1):
        p = doc.line(no)
        if p.kind == "heading":
            return None
        if p.kind == "bullet" and p.indent < ln.indent:
            return p
    return None


def _line_values(doc, ln, tokens):
    if ln.kind == "table_row":
        header = doc.tables[ln.table].header
        vals = []
        for c, cell in enumerate(g.split_cells(ln.raw)):
            text = g.strip_emphasis(cell)
            head = g.strip_emphasis(header[c]) if c < len(header) else ""
            vals += _measure_values(text, tokens, bool(_hits(text, tokens) or _hits(head, tokens)))
        return vals
    parent = _parent_bullet(doc, ln)
    named = bool(parent and _hits(parent.text, tokens))
    vals = []
    for s in doc.sentences(ln.no):
        vals += _measure_values(s.text, tokens, named)
    return vals


def _section_key(parents):
    """reading: a line's section is its ### heading; else its ## (or #) heading when that
    section has no ### child; else None (a parent's text before its first ### is not checked
    for values)."""
    def key(ln):
        if ln.h3:
            return ln.h3
        return None if ln.h2 in parents else ln.h2
    return key


def r1b_b(doc):
    """R1b-b: a section printing negative and positive values of one measure with no
    convention sentence in it or in its parent ## section before it."""
    parents = {ln.h2 for ln in doc.lines if ln.h3}
    key = _section_key(parents)
    found = {}
    for ln in doc.lines:
        k = key(ln)
        if k is None or ln.kind not in ("bullet", "para", "table_row"):
            continue
        for name, tokens in MEASURES:
            for n in _line_values(doc, ln, tokens):
                if n.value == 0:
                    continue
                d = found.setdefault((k, name), ({"neg": set(), "pos": set()}))
                d["neg" if n.signed else "pos"].add(ln.no)
    flags = []
    for (k, name), d in sorted(found.items()):
        if not (d["neg"] and d["pos"]) or _has_convention(doc, k, key):
            continue
        lines = d["neg"] | d["pos"]
        primary = k or min(lines)              # reading: the section heading is the primary line
        flags.append(Flag("R1b", "b", primary, _ev(primary, lines), name,
                          "section prints negative and positive %s values and states no sign "
                          "convention" % name,
                          {"negative_lines": sorted(d["neg"]), "positive_lines": sorted(d["pos"])}))
    return flags


def _has_convention(doc, k, key):
    """reading: every non-blank line in scope is searched, headings included; for a ###
    section the scope adds its parent ## section's lines above the ### heading."""
    if k and doc.line(k).level == 3:
        h2 = doc.line(k).h2
        scope = [ln for ln in doc.lines if key(ln) == k or (ln.h2 == h2 and ln.no < k)]
    else:
        scope = [ln for ln in doc.lines if key(ln) == k]
    return any(_CONVENTION.search(ln.text) for ln in scope if ln.kind != "blank")


# ---------------------------------------------------------------- R5 citations

MONTHS = frozenset("January February March April May June July August September October "
                   "November December Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec".split())

# Frozen with the code (v5/v6): RWE, RCT and every all-caps registry or database name.
ACRONYM_STOPLIST = frozenset((
    "RWE RCT "
    "NCT ISRCTN ANZCTR ACTRN DRKS IRCT JPRN EUCTR CTIS CTR CTRI PACTR REBEC RPCEC SLCTR TCTR "
    "LBCTR ITMCTR ICTRP WHO PROSPERO "
    "NIH NLM NCBI PMC PMID DOI FDA EMA MEDLINE EMBASE CINAHL CENTRAL FAERS VAERS "
    "NHANES NHIRD NSDUH BRFSS NHIS MEPS CPRD SEER MIMIC OHDSI OMOP KPMP OAI ARIC MESA TCGA GEO"
).split())

_NAME = r"[^\W\d_][\w" + APOS + r"\-]*"
_TAIL = (r"(?: (?P<ini>[A-Z]{1,3}))?(?: et al\.?| (?:and|&) " + _NAME + r"(?: [A-Z]{1,3})?)?"
         r",? (?P<year>(?:19|20)\d\d)(?!\d)(?!-\d)(?:[" + APOS + r"]s)?")
_TAIL_RE = re.compile(r"(?:[" + APOS + r"]s)?" + _TAIL)
_CAND_RE = re.compile(r"(?<![\w" + APOS + r"\-])(?P<sur>" + _NAME + r")" + _TAIL)
_POSSESSIVE = re.compile("[" + APOS + "]s$")
_CITE_AFTER = re.compile(r" ?(\[[^\[\]]*\])")
_ACRONYM = re.compile(r"(?<![\w\-.])([A-Z]{3,}) (?:trial|study)(?![\w\-])")
_PMID_LIKE = re.compile(r"(?<![\w.])\d{6,9}(?!\d)")

_REF_PREFIX = re.compile(r"^\d+[a-z]?\.\s+")
_SEG_END = re.compile(r",|;|\(| et al\b|\.(?=\s|$)")
_PERSON = re.compile(r"^(?P<sur>.+?) (?P<ini>[A-Z]{1,3})(?: (?:Jr|Sr|2nd|3rd|[4-9]th))?$")
_YEAR = re.compile(r"(?<![\w./\-])(?:19|20)\d\d(?![\w\-])")
_PMID = re.compile(r"PMID:?\s*(\d+)")
_DOI = re.compile(r"10\.\d{4,9}/[^\s;]+")


@dataclass
class Ref:
    key: str
    line: int
    text: str
    surname: str = ""        # first author (a person)
    initials: str = ""
    org: str = ""            # organisation author
    org_initials: str = ""
    years: frozenset = frozenset()
    pmids: frozenset = frozenset()
    dois: frozenset = frozenset()
    ids: frozenset = frozenset()


def parse_reference(key, no, raw):
    """reading: the author field is the entry's text up to the first ",", ";", "(", " et al"
    or "." before a space. It is a person when it ends in 1-3 capital initials (optionally
    Jr, Sr, 2nd, 3rd, 4th-9th) after a surname holding a lower-case letter; otherwise an
    organisation. The years are every 19xx/20xx token not glued to a letter, digit, ".", "/"
    or "-" (so no dates, DOIs or IDs)."""
    text = _REF_PREFIX.sub("", g.strip_emphasis(raw), count=1)
    m = _SEG_END.search(text)
    seg = (text[:m.start()] if m else text).strip()
    r = Ref(key, no, text)
    pm = _PERSON.match(seg)
    if pm and pm.group("sur")[:1].isupper() and any(c.islower() for c in pm.group("sur")):
        r.surname, r.initials = pm.group("sur"), pm.group("ini")
    else:
        r.org = seg
        r.org_initials = "".join(w[0] for w in seg.split() if w != "of" and w[:1].isupper())
    r.years = frozenset(y.group() for y in _YEAR.finditer(text))
    r.pmids = frozenset(_PMID.findall(text))
    r.dois = frozenset(d.rstrip(".,)").lower() for d in _DOI.findall(text))
    r.ids = frozenset(x[2] for x in g.registry_ids(text))
    return r


def references(doc):
    return [parse_reference(k, no, doc.line(no).raw) for k, no in doc.references()]


def _cite_follows(text, end):
    m = _CITE_AFTER.match(text, end)
    return bool(m and g.cite_keys(m.group(1)))


def author_year_candidates(text):
    """v6 flag-side candidates: [(start, end, surname, initials, year, resolved by [n])]."""
    out = []
    for m in _CAND_RE.finditer(text):
        sur = _POSSESSIVE.sub("", m.group("sur"))
        if not sur[:1].isupper() or not any(c.islower() for c in sur) or sur in MONTHS:
            continue
        before = text[:m.start()]
        if before.endswith(" ") and before.strip():
            prev = before.split()[-1]
            if prev[-1].isdigit() or (prev[0].isupper() and re.fullmatch(_NAME, prev)):
                continue
        out.append((m.start(), m.end(), sur, m.group("ini") or "", m.group("year"),
                    _cite_follows(text, m.end())))
    return out


def _maps(refs, sur, ini, year):
    out = []
    for r in refs:
        if year not in r.years:
            continue
        if r.surname and r.surname == sur and (not ini or r.initials.startswith(ini)):
            out.append(r)
        elif r.org and sur in (r.org, r.org_initials):
            out.append(r)
    return out


def _names_ref(text, r):
    """Cite-side author-year for one reference: the first author's full surname directly
    before one of its years (any preceding word allowed), or an organisation's name or
    initials + year. An author-year directly followed by [n] is resolved by the [n] instead."""
    if r.surname:
        for i in g.find_word(text, r.surname):
            m = _TAIL_RE.match(text, i + len(r.surname))
            if (m and m.group("year") in r.years
                    and (not m.group("ini") or r.initials.startswith(m.group("ini")))
                    and not _cite_follows(text, m.end())):
                return True
        return False
    for form in {r.org, r.org_initials} - {""}:
        for y in r.years:
            if g.find_word(text, form + " " + y) or g.find_word(text, form + ", " + y):
                return True
    return False


def cited_keys(doc, refs):
    """Keys of the references cited anywhere in the cut text outside the reference list
    (reading: headings and table cells included; reference entries never cite each other)."""
    cited = set()
    keys = {r.key for r in refs}
    for ln in doc.lines:
        if ln.kind in ("ref", "blank"):
            continue
        text = ln.text
        cited.update(k for k in g.cite_keys(text) if k in keys)
        digits = set(_PMID_LIKE.findall(text))
        low = text.lower()
        ids = {x[2] for x in g.registry_ids(text)}
        acronyms = {m.group(1) for m in _ACRONYM.finditer(text)}
        for r in refs:
            if r.key in cited:
                continue
            if (r.pmids & digits or any(d in low for d in r.dois) or r.ids & ids
                    or any(g.find_word(r.text, a) for a in acronyms) or _names_ref(text, r)):
                cited.add(r.key)
    return cited


def r5(doc, refs=None):
    refs = references(doc) if refs is None else refs
    flags = []
    cited = cited_keys(doc, refs)
    for r in refs:
        if r.key not in cited:
            flags.append(Flag("R5", "never-cited", r.line, (), "[%s]" % r.key,
                              "reference is never cited in the text"))
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para", "table_row"):
            continue
        text = ln.text
        for start, end, sur, ini, year, resolved in author_year_candidates(text):
            if resolved:
                continue
            hit = _maps(refs, sur, ini, year)
            if len(hit) == 1:
                continue
            rule = "author-year-none" if not hit else "author-year-ambiguous"
            flags.append(Flag("R5", rule, ln.no, _ev(ln.no, [r.line for r in hit]),
                              text[start:end],
                              "author-year matches %d references" % len(hit),
                              {"keys": [r.key for r in hit]}))
    for ln in doc.lines:
        if ln.kind in ("ref", "blank"):
            continue
        for m in _ACRONYM.finditer(mask_quotes(ln.text)):
            tok = m.group(1)
            if tok in ACRONYM_STOPLIST or any(g.find_word(r.text, tok) for r in refs):
                continue
            flags.append(Flag("R5", "acronym", ln.no, (), tok,
                              "named trial or study with no reference whose title contains it"))
    return flags


# ---------------------------------------------------------------- R6-a

_R6_TOKEN = re.compile(r"(?<![\w\-.])(?:version \d+|v\d+|run \d+|gate \d+)")
_R6_BEFORE = re.compile(r"(?:\bAPI|\brelease|\bversion of|\blast)\s*$", re.IGNORECASE)


def r6_a(doc):
    """R6-a: internal workflow tokens outside the reference list (reading: tokens are
    case-sensitive as printed in the plan; headings and table cells are read)."""
    flags = []
    for ln in doc.lines:
        if ln.kind in ("ref", "blank"):
            continue
        text = mask_quotes(ln.text)
        for m in _R6_TOKEN.finditer(text):
            j = m.end()
            if j < len(text):
                c = text[j]
                if c.isalnum() or c in "-_" or (c == "." and j + 1 < len(text) and text[j + 1] != " "):
                    continue
            if _R6_BEFORE.search(text[:m.start()]) or re.match(r"-\d\d-\d\d", text[j:]):
                continue
            flags.append(Flag("R6", "a", ln.no, (), m.group(),
                              "internal workflow label in judge-facing text"))
    return flags


# ---------------------------------------------------------------- all part-1 modules

def check(doc):
    """Flags of the modules coded so far, sorted by line, module, rule and span."""
    tuples = placed_tuples(doc)
    refs = references(doc)
    flags = (r1(doc, tuples) + r1b_a(doc, tuples) + r1b_b(doc) + r5(doc, refs) + r6_a(doc))
    return sorted(flags, key=lambda f: (f.line, f.module, f.rule, f.span))
