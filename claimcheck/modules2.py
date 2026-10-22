"""claimcheck modules, part 2: R2, R2b, R3, R4, R5b, R7-a and R8.

Coded to the evaluation plan in findings/claim-checker/: v4 section 3 (R2b, and R5b's where
and flag rules), v5 section 3 (R3, R5b items, R8 sources, and R4 as defined in section 3 of
the run-146 note) and v7 section 3 (R2, R7-a, R8 dose; G1 governs every number). Where the
plans leave a choice open, the reading taken here is listed in claimcheck/CODING-NOTES.md
(27 onwards) and marked "reading:". R6-b and R7-b (they run only with --plans / --jobs),
the command line and the keyword baseline come next. Not frozen.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from . import grammar as g
from . import modules as m1
from .modules import Flag, _ev, mask_quotes

DEADLINE = date(2027, 3, 26)
PUNCT = "()[]\"'*,.;:`" + g.LDQUO + g.RDQUO
NUMBER_WORDS = "|".join(g.NUMBER_WORDS)


def _wb(pat):
    """v4 word boundary around a regex (reading 3: a "." directly before a word is not one)."""
    return r"(?<![\w\-.])(?:" + pat + r")(?![\w\-]|\.\S)"


# ---------------------------------------------------------------- shared helpers

def _close(text, p):
    """Offset of the ")" matching the "(" at p, or None."""
    depth = 0
    for i in range(p, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def _top_split(s, seps):
    """Split s on any of seps at parenthesis depth 0 and outside quotation marks."""
    out, depth, quoted, start, i = [], 0, False, 0, 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c == '"':
            quoted = not quoted
        elif c == g.LDQUO:
            quoted = True
        elif c == g.RDQUO:
            quoted = False
        elif depth == 0 and not quoted:
            hit = next((x for x in seps if s.startswith(x, i)), None)
            if hit:
                out.append(s[start:i])
                i += len(hit)
                start = i
                continue
        i += 1
    out.append(s[start:])
    return out


def _int_at(text, start, end):
    """A number word (any case), or a G1 integer with no sign, "%", "$" or decimals, spanning
    exactly text[start:end]; else None."""
    word = text[start:end].lower()
    if word in g.WORD_VALUE:
        return g.WORD_VALUE[word]
    for n in g.numbers(text):
        if (n.start, n.end) == (start, end):
            plain = not (n.signed or n.pct or n.dollar or n.decimals or n.text.startswith("+"))
            return int(n.value) if plain else None
    return None


def _negated(text, start, value):
    """v4: a count preceded by "no", "none", "0" or "zero" is never flagged. reading: the
    whitespace token directly before the number (punctuation ignored, any case), or a count
    whose own value is 0."""
    if value == 0:
        return True
    before = text[:start].split()
    return bool(before) and before[-1].strip(PUNCT).lower() in ("no", "none", "0", "zero")


def _sentences(doc, ln):
    """Sentence texts of one line. reading: a reference entry's own number is not read."""
    if ln.kind != "ref":
        return [s.text for s in doc.sentences(ln.no)]
    raw = m1._REF_PREFIX.sub("", ln.raw, count=1)
    texts = (g.strip_emphasis(piece).strip() for _, piece in g.split_sentences(raw))
    return [t for t in texts if t]


def _heading_above(doc, ln):
    for no in range(ln.no - 1, 0, -1):
        if doc.line(no).kind == "heading":
            return doc.line(no)
    return None


def _block_lead(doc, ln):
    """Run-146 note: the governing block lead of a bullet. reading: walk up over bullets and
    blank lines; the first other line is the block lead when it is a paragraph with a bold
    lead whose whole text ends with ":"."""
    if ln.kind != "bullet":
        return None
    for no in range(ln.no - 1, 0, -1):
        p = doc.line(no)
        if p.kind in ("bullet", "blank"):
            continue
        if p.kind == "para" and p.lead and p.text.rstrip().endswith(":"):
            return p
        return None
    return None


def _section_lines(doc, pred):
    """The first heading whose text matches pred, and every line after it up to the next
    heading of the same or a higher level."""
    for ln in doc.lines:
        if ln.kind == "heading" and pred(ln.text):
            out = [ln]
            for no in range(ln.no + 1, len(doc.lines) + 1):
                p = doc.line(no)
                if p.kind == "heading" and p.level <= ln.level:
                    break
                out.append(p)
            return out
    return []


# ---------------------------------------------------------------- R2 tables (v7)

_R2_IGNORED = frozenset("vs per of and or the n".split())
_HEADER_WORD = re.compile(r"[^\W_][\w\-]*")
_RANGE_JOIN = ("-", " to ")
_IN_K = re.compile(r" in (\d+|" + NUMBER_WORDS + r")(?: of (\d+|" + NUMBER_WORDS + r"))? "
                   r"(?!of(?![\w\-]))[^\W\d_][\w\-]*", re.IGNORECASE)
_NOFM = re.compile(r"(?<![\w\-.])(\d+|" + NUMBER_WORDS + r") of (?:the )?(\d+|" + NUMBER_WORDS
                   + r")(?![\w\-]|\.\d)", re.IGNORECASE)
_PREDICATES = (     # v5 fixed predicates: (text, needs a CI, test on (estimate, (low, high)))
    ("CI below 1", True, lambda est, ci: ci is not None and ci[1] < 1),
    ("CI above 1", True, lambda est, ci: ci is not None and ci[0] > 1),
    ("CI includes 1", True, lambda est, ci: ci is not None and ci[0] <= 1 <= ci[1]),
    ("below 1", False, lambda est, ci: est is not None and est < 1),
    ("above 1", False, lambda est, ci: est is not None and est > 1),
)
_PRED_RES = tuple((re.compile(_wb(re.escape(p)), re.IGNORECASE), ci, test)
                  for p, ci, test in _PREDICATES)


@dataclass
class Column:
    table: int
    index: int
    header: str
    words: frozenset
    values: list             # every cell value: G1 numbers, or a CI tuple cell's estimate
    rows: list               # per body row: (estimate or None, (low, high) or None)
    lines: tuple             # the table's header and body lines

    @property
    def has_ci(self):
        return any(ci is not None for _, ci in self.rows)


def _header_words(head):
    """v7: header words; G2 labels and vs, per, of, and, or, the, n are ignored."""
    text = g.strip_emphasis(head)
    for a, b, _ in reversed(g.label_spans(text)):
        text = text[:a] + " " + text[b:]
    return frozenset(w for w in _HEADER_WORD.findall(text) if w.lower() not in _R2_IGNORED)


def columns(doc):
    """{table index: [Column]}. reading: a cell holding CI tuples gives its first tuple's
    estimate (and interval); other cells give every G1 number, and their first number is the
    row's estimate."""
    out = {}
    for ti, tab in enumerate(doc.tables):
        lines = (tab.header_line,) + tuple(no for no, _ in tab.rows)
        cols = []
        for c, head in enumerate(tab.header):
            values, rows = [], []
            for _, cells in tab.rows:
                text = g.strip_emphasis(cells[c]) if c < len(cells) else ""
                tuples = g.ci_tuples(text)
                if tuples:
                    t = tuples[0]
                    values.append(t.est)
                    rows.append((t.est.value, tuple(sorted((t.lo.value, t.hi.value)))))
                else:
                    nums = g.numbers(text)
                    values.extend(nums)
                    rows.append((nums[0].value if nums else None, None))
            cols.append(Column(ti, c, head, _header_words(head), values, rows, lines))
        out[ti] = cols
    return out


def _rounds_to(v, ep):
    """v7: the cell value rounded to the endpoint's decimals equals the endpoint."""
    q = Decimal(1).scaleb(-ep.decimals)
    a = Decimal(repr(v.value)).quantize(q, rounding=ROUND_HALF_UP)
    return a == Decimal(repr(ep.value)).quantize(q, rounding=ROUND_HALF_UP)


def ranges(text):
    """v7 ranges of one sentence: [(first, second, percentages)]. Interval pairs (a CI
    tuple's interval, a pair directly after a G2 label or after "<number>, ") are not ranges."""
    nums = g.numbers(text)
    intervals = {(t.lo.start, t.hi.start) for t in g.ci_tuples(text)}
    label_ends = {b for _, b, _ in g.label_spans(text)}
    ends = {n.end for n in nums}
    out = []
    for n1, n2 in zip(nums, nums[1:]):
        if text[n1.end:n2.start] not in _RANGE_JOIN or (n1.start, n2.start) in intervals:
            continue
        if n1.start - 1 in label_ends and text[n1.start - 1:n1.start] == " ":
            continue
        if n1.start >= 2 and text[n1.start - 2:n1.start] == ", " and n1.start - 2 in ends:
            continue
        out.append((n1, n2, n1.pct or n2.pct))
    return out


def _range_fails(col, n1, n2, pct):
    return not all(any(v.pct == pct and _rounds_to(v, ep) for v in col.values) for ep in (n1, n2))


def _in_k_fails(col, n1, n2, pct, k, total):
    lo, hi = sorted((n1.value, n2.value))
    inside = sum(1 for v in col.values if v.pct == pct and lo <= v.value <= hi)
    return inside != k or (total is not None and total != len(col.rows))


def _n_of_m_fails(col, n, total, test):
    return total != len(col.rows) or n != sum(1 for est, ci in col.rows if test(est, ci))


def _predicate(text, start, clause_start, nofm_starts):
    """v7: the nearest fixed predicate before an N-of-M in its clause, at most 8 words before,
    with no other N-of-M in between; at one end, the longest wins."""
    best = None
    for pat, ci, test in _PRED_RES:
        for pm in pat.finditer(text, clause_start, start):
            if len(text[pm.end():start].split()) > 8:
                continue
            if any(pm.end() <= s < start for s in nofm_starts):
                continue
            key = (pm.end(), pm.end() - pm.start())
            if best is None or key > best[0]:
                best = (key, pm.group(), ci, test)
    return best


def r2(doc):
    """R2 (v7): ranges, range-in-K and N-of-M in lines linked to a table, checked against the
    candidate columns; a claim is flagged only when it fails in every candidate column."""
    cols = columns(doc)
    flags = []
    for ln in doc.lines:
        linked = doc.linked_tables(ln.no)
        if not linked:
            continue
        pool = [c for t in linked for c in cols[t]]
        for s in doc.sentences(ln.no):
            text = mask_quotes(s.text)
            cands = [c for c in pool
                     if any(g.find_word(text, w, ignore_case=True) for w in c.words)]
            claims, info = [], []        # claims: (rule, span, candidate columns, failure test)
            for n1, n2, pct in ranges(text):
                claims.append(("range", text[n1.start:n2.end], cands,
                               lambda c, n1=n1, n2=n2, pct=pct: _range_fails(c, n1, n2, pct)))
                k = _IN_K.match(text, n2.end)
                if not k:
                    continue
                kv = _int_at(text, *k.span(1))
                tv = _int_at(text, *k.span(2)) if k.group(2) else None
                if kv is not None and (tv is not None or not k.group(2)):
                    claims.append(("range-in-K", text[n1.start:k.end()], cands,
                                   lambda c, n1=n1, n2=n2, pct=pct, kv=kv, tv=tv:
                                   _in_k_fails(c, n1, n2, pct, kv, tv)))
            found = list(_NOFM.finditer(text))
            starts = [f.start() for f in found]
            for f in found:
                n = _int_at(text, *f.span(1))
                total = _int_at(text, *f.span(2))
                if n is None or total is None:
                    continue
                a, _ = g.clause_span(text, f.start())
                pred = _predicate(text, f.start(), a, starts)
                if pred is None:
                    info.append(Flag("R2", "no-predicate", ln.no, (), f.group(),
                                     "N-of-M with no fixed predicate: out of scope", scored=False))
                    continue
                _, ptext, ci, test = pred
                claims.append(("N-of-M", ptext + " ... " + f.group(),
                               [c for c in cands if c.has_ci or not ci],
                               lambda c, n=n, total=total, test=test:
                               _n_of_m_fails(c, n, total, test)))
            for rule, span, cc, fails in claims:
                if not cc:
                    info.append(Flag("R2", "out-of-scope", ln.no, (), span,
                                     "%s claim shares no word with a linked column header" % rule,
                                     scored=False))
                elif all(fails(c) for c in cc):
                    lines = {no for c in cc for no in c.lines}
                    flags.append(Flag("R2", rule, ln.no, _ev(ln.no, lines), span,
                                      "%s claim fails in every candidate column" % rule,
                                      {"columns": [[c.table, c.index, c.header] for c in cc]}))
            flags.extend(info)
    return flags


# ---------------------------------------------------------------- R2b (v4)

ALL_KEYS = frozenset(("NCT", "ChiCTR", "ISRCTN", "EUCTR", "CTIS", "ACTRN", "DRKS", "IRCT",
                      "JPRN", "jRCT"))
_SCOPE_WORDS = re.compile(_wb(r"below|as follows|listed|accounted for"), re.IGNORECASE)


def _regs(text):
    """Registries named in text; names that map to the same patterns are one registry."""
    return {frozenset(g.REGISTRY_NAMES[n]) for _, n in g.registry_names(text)
            if n in g.REGISTRY_NAMES}


def _registry_keys(clause, sentence):
    """v4 registry choice: the clause first, then the sentence. One registry -> its patterns;
    two or more -> all. reading: an all-patterns term counts only when the sentence names no
    registry (v4 shared definitions)."""
    sentence_regs = _regs(sentence)
    for text in (clause, sentence):
        regs = _regs(text)
        if len(regs) == 1:
            return next(iter(regs))
        if regs:
            return ALL_KEYS
        terms = any(n in g.ALL_PATTERN_TERMS for _, n in g.registry_names(text))
        if terms and not sentence_regs:
            return ALL_KEYS
    return ALL_KEYS


def _gated(masked, raw):
    """v4 gate: names a registry or an all-patterns term (quotes masked), or holds an ID."""
    return bool(g.registry_names(masked) or g.registry_ids(raw))


def _scope_lines(doc, ln, sentence):
    """v4 scope: when the sentence says below, as follows, listed or accounted for, or ends
    with ":", the lines after it up to the next heading or the next unindented paragraph that
    is not a bullet. reading: blank lines are skipped; table rows and numbered reference
    entries are inside the run."""
    if not (_SCOPE_WORDS.search(sentence) or sentence.rstrip().endswith(":")):
        return []
    out = []
    for no in range(ln.no + 1, len(doc.lines) + 1):
        p = doc.line(no)
        if p.kind == "heading" or (p.kind == "para" and not p.raw[:1].isspace()):
            break
        if p.kind != "blank":
            out.append(no)
    return out


def r2b(doc):
    """R2b (v4): a gated count phrase vs the distinct in-scope registry IDs."""
    flags = []
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para", "ref"):
            continue
        for s in _sentences(doc, ln):
            text = mask_quotes(s)
            phrases = g.count_phrases(text)
            if not phrases or not _gated(text, s):
                continue
            scope = _scope_lines(doc, ln, text)
            ids = {x[2]: x[3] for x in g.registry_ids(s)}
            for no in scope:
                for x in g.registry_ids(doc.line(no).text):
                    ids.setdefault(x[2], x[3])
            for start, end, value in phrases:
                if _negated(text, start, value):
                    continue
                a, b = g.clause_span(text, start)
                keys = _registry_keys(text[a:b], text)
                inside = sorted(i for i, k in ids.items() if k in keys)
                if value != len(inside):
                    flags.append(Flag(
                        "R2b", "count", ln.no, _ev(ln.no, scope), text[start:end],
                        "stated count %d, distinct in-scope registry IDs %d" % (value, len(inside)),
                        {"stated": value, "in_scope": inside,
                         "out_of_scope": sorted(i for i, k in ids.items() if k not in keys)}))
    return flags


# ---------------------------------------------------------------- R5b (v4 + v5)

_DESIGN_NOUN = re.compile(_wb(r"trials?|stud(?:y|ies)|records?|registrations?"), re.IGNORECASE)
_LEAD_NOUN = re.compile(r"trial|studies|records", re.IGNORECASE)
_VERB = re.compile(_wb("are") + "|:")
_NEGATION = re.compile(r"(?:no|none)(?![\w\-])", re.IGNORECASE)


def _pieces(s):
    """v4 items: split at top level on ";", "," and a final " and ". reading: the last piece is
    split at its last top-level " and "; a final "." is dropped."""
    s = s.strip()
    if s.endswith("."):
        s = s[:-1]
    parts = _top_split(s, (";", ","))
    last = _top_split(parts[-1], (" and ",))
    parts[-1:] = [" and ".join(last[:-1]), last[-1]] if len(last) > 1 else last
    return [p.strip() for p in parts if p.strip()]


def r5b(doc):
    """R5b: every enumerated item without a registry ID, in (i) a gated sentence with a count
    phrase and (ii) a bullet whose bold lead names trials, studies or records."""
    flags, seen = [], set()

    def flag(ln, piece, form, count):
        if (ln.no, piece) not in seen:
            seen.add((ln.no, piece))
            flags.append(Flag("R5b", form, ln.no, (), piece,
                              "enumerated item without a registry ID", {"count": count}))

    for ln in doc.lines:
        if ln.kind not in ("bullet", "para"):
            continue
        for s in doc.sentences(ln.no):
            text = mask_quotes(s.text)
            phrases = g.count_phrases(text)
            if not phrases or not _gated(text, s.text):
                continue
            v = _VERB.search(text, phrases[0][1])
            if not v:
                continue
            for piece in _pieces(s.text[v.end():]):
                if g.registry_ids(piece) or _NEGATION.match(piece):
                    continue
                if _DESIGN_NOUN.search(mask_quotes(piece)) or piece.startswith("("):
                    flag(ln, piece, "item", phrases[0][2])
        if ln.kind == "bullet" and ln.lead.rstrip().endswith(":") and _LEAD_NOUN.search(ln.lead):
            gate = [ln.lead] + [x.text for x in (_heading_above(doc, ln), _block_lead(doc, ln)) if x]
            if any(_gated(mask_quotes(t), t) for t in gate):
                rest = ln.raw[ln.body:]
                for piece in _pieces(g.strip_emphasis(rest[rest.find("**", 2) + 2:])):
                    if not g.registry_ids(piece):
                        flag(ln, piece, "lead", None)
    return flags


# ---------------------------------------------------------------- R3 directional wording (v5)

_R3_TRIGGER = re.compile(_wb(r"no differen\w*|no benefit|no interaction|lower risk|higher risk"
                             r"|less likely|more likely|stronger|weaker|absent|no effect"),
                         re.IGNORECASE)
_R3_NO_CI = ("no differen", "no benefit", "no interaction")
_R3_EXEMPT = re.compile(r" (?:given|reported|printed|stated)(?![\w\-])")
_RATIO = (re.compile(_wb(r"a?HRs?|sHRs?|a?ORs?|a?RRs?|IRRs?")),
          re.compile(_wb(r"(?:hazard|odds|risk|rate) ratios?"), re.IGNORECASE))


def _is_ratio(before, head):
    """reading: a ratio measure is named in the clause before the estimate or in the column
    header; otherwise the tuple is a difference."""
    return any(r.search(x) for r in _RATIO for x in (before, head))


def _r3_units(doc):
    """(line, text, column header): prose sentences, and table body cells one by one."""
    for ln in doc.lines:
        if ln.kind in ("bullet", "para"):
            for s in doc.sentences(ln.no):
                yield ln, s.text, ""
        elif ln.kind == "table_row":
            header = doc.tables[ln.table].header
            for c, cell in enumerate(g.split_cells(ln.raw)):
                head = g.strip_emphasis(header[c]) if c < len(header) else ""
                yield ln, g.strip_emphasis(cell), head


def r3(doc):
    """R3 (v5): directional wording beside a same-clause CI that includes the null; and
    "no differen*/no benefit/no interaction" in a clause with no CI."""
    flags = []
    for ln, text, head in _r3_units(doc):
        masked = mask_quotes(text)
        tuples = g.ci_tuples(text)
        for m in _R3_TRIGGER.finditer(masked):
            a, b = g.clause_span(masked, m.start())
            inside = [t for t in tuples if a <= t.est.start < b]
            if inside:
                for t in inside:
                    null = 1 if _is_ratio(text[a:t.est.start], head) else 0
                    lo, hi = sorted((t.lo.value, t.hi.value))
                    if lo <= null <= hi:
                        flags.append(Flag("R3", "ci-includes-null", ln.no, (), m.group(),
                                          "directional wording beside a CI that includes the null",
                                          {"ci": text[t.est.start:t.hi.end], "null": null}))
                        break
            elif (m.group().lower().startswith(_R3_NO_CI)
                  and not _R3_EXEMPT.match(masked, m.end())):
                flags.append(Flag("R3", "no-ci", ln.no, (), m.group(),
                                  "no-difference wording in a clause with no CI"))
    return flags


# ---------------------------------------------------------------- R4 dates (run-146 note)

MONTHS_FULL = ("January February March April May June July August September October "
               "November December").split()
_DATE = re.compile(r"(?<![\w\-])(?:(\d{4})-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?"
                   r"|([1-9]|[12]\d|3[01]) (" + "|".join(MONTHS_FULL) + r") (\d{4}))(?![\w\-])")
_ANCHOR_LEAD = re.compile(r"(?<![\w\-.])(?:as of|as read|rechecked|checked|searched|accessed"
                          r"|unchanged on) $", re.IGNORECASE)
_ON = re.compile(r"(?<![\w\-.])on $", re.IGNORECASE)
_REREAD = re.compile(_wb("re-read"), re.IGNORECASE)
_R4_VERB = re.compile(_wb(r"registered|posted|published|recruiting|exists?"), re.IGNORECASE)
_R4_LIMIT = re.compile(_wb(r"no|none|not|only|currently|still|exactly"), re.IGNORECASE)
_R4_UNREPORTED = re.compile(_wb("unreported"), re.IGNORECASE)
_EXACT_NUM = re.compile(r" (?:\d+|" + NUMBER_WORDS + r")(?![\w\-])", re.IGNORECASE)
_SPAN = re.compile(r"(?<![\w\-.])(?:(about|nearly|almost|over|more than) )?(\S+) "
                   r"(days|weeks|months|years) (after|since|ago|on the (?:US )?market)(?![\w\-])",
                   re.IGNORECASE)
_OVERVIEW = re.compile(r"(?<![\w\-])Overview(?![\w\-])", re.IGNORECASE)
EVENTS = {"completion": ("completion",), "market": ("approved", "approval", "marketed")}


def _dates(text):
    """[(start, end, date)] for YYYY-MM-DD, YYYY-MM (reading: day 1) and "D Month YYYY"."""
    out = []
    for m in _DATE.finditer(text):
        try:
            if m.group(1):
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
            else:
                d = date(int(m.group(6)), MONTHS_FULL.index(m.group(5)) + 1, int(m.group(4)))
        except ValueError:
            continue
        out.append((m.start(), m.end(), d))
    return out


def anchors(text):
    """Anchor dates: a date directly preceded by as of, as read, rechecked, checked, searched,
    accessed, unchanged on, or "re-read ... on" (case-insensitive)."""
    out = []
    for a, b, d in _dates(text):
        before = text[:a]
        if _ANCHOR_LEAD.search(before) or (_ON.search(before) and _REREAD.search(before)):
            out.append((a, b, d))
    return out


def _anchored(doc, ln, sentence):
    """Anchor scope: the sentence, the line's own bold lead and the governing block lead
    (reading: the block lead's whole line)."""
    if anchors(sentence) or anchors(ln.lead):
        return True
    lead = _block_lead(doc, ln)
    return bool(lead and anchors(mask_quotes(lead.text)))


def _limited(text, a, v):
    for m in _R4_LIMIT.finditer(text, a, v):
        if m.group().lower() != "exactly" or _EXACT_NUM.match(text, m.end()):
            return True
    return False


def _add_months(d, k):
    y, mo = divmod(d.month - 1 + k, 12)
    y += d.year
    return date(y, mo + 1, min(d.day, calendar.monthrange(y, mo + 1)[1]))


def _months_between(d1, d2):
    """Calendar months from d1 to d2 plus the remaining days / 30.44."""
    if d2 < d1:
        return -_months_between(d2, d1)
    k = (d2.year - d1.year) * 12 + d2.month - d1.month
    while k > 0 and _add_months(d1, k) > d2:
        k -= 1
    return k + (d2 - _add_months(d1, k)).days / 30.44


def _length(d1, d2, unit):
    unit = unit.lower()
    if unit == "days":
        return (d2 - d1).days
    if unit == "weeks":
        return (d2 - d1).days / 7
    x = _months_between(d1, d2)
    return x / 12 if unit == "years" else x


def _holds(qualifier, n, x):
    q = (qualifier or "").lower()
    if q in ("nearly", "almost"):
        return n - 1 <= x < n
    if q == "about":
        return abs(x - n) <= max(1, 0.1 * n)
    if q in ("over", "more than"):
        return x > n
    return abs(x - n) < 1


def _start_candidates(texts, event):
    """Distinct dates whose 4 preceding words hold the event word."""
    found = set()
    for text in texts:
        for a, _, d in _dates(text):
            words = [w.strip(PUNCT).lower() for w in text[:a].split()[-4:]]
            if any(w in EVENTS[event] for w in words):
                found.add(d)
    return found


def _bullet_block(doc, ln):
    """reading: the top-level bullet at or above the line and every deeper bullet directly
    after it; a paragraph's block is itself."""
    if ln.kind != "bullet":
        return [ln]
    top = ln.no
    while top > 1 and doc.line(top).indent > 0 and doc.line(top - 1).kind == "bullet":
        top -= 1
    block, no = [doc.line(top)], top + 1
    while no <= len(doc.lines) and doc.line(no).kind == "bullet" and doc.line(no).indent > 0:
        block.append(doc.line(no))
        no += 1
    return block


def _r4_a(doc, ln, text, deadline, overview):
    flags = []
    for m in _SPAN.finditer(text):
        n = _int_at(text, *m.span(2))
        if n is None:
            continue
        if m.group(4).lower().startswith("on the"):
            event = "market"
        elif any(w.strip(PUNCT).lower() == "completion" for w in text[m.end():].split()[:4]):
            event = "completion"
        else:
            event = None
        start = None
        if event:
            levels = ([text], [mask_quotes(p.text) for p in _bullet_block(doc, ln)],
                      [mask_quotes(p.text) for p in overview])
            for level in levels:
                found = _start_candidates(level, event)
                if len(found) == 1:
                    start = found.pop()
                    break
        if start is None:
            flags.append(Flag("R4", "a-unbound", ln.no, (), m.group(),
                              "elapsed span with no single start date: info only", scored=False))
            continue
        ends = anchors(text)
        end = ends[0][2] if ends else deadline
        x = _length(start, end, m.group(3))
        if not _holds(m.group(1), n, x):
            flags.append(Flag("R4", "a", ln.no, (), m.group(), "elapsed span breaks its qualifier",
                              {"start": start.isoformat(), "end": end.isoformat(),
                               "length": round(x, 2)}))
    return flags


def r4(doc, deadline=DEADLINE):
    """R4: R4-b status claims with no anchor in scope, and R4-a elapsed spans recomputed from
    their bound start date to a same-sentence anchor or the deadline."""
    overview = _section_lines(doc, lambda t: bool(_OVERVIEW.search(t)))
    flags = []
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para"):
            continue
        for s in doc.sentences(ln.no):
            text = mask_quotes(s.text)
            claims = [v for v in _R4_VERB.finditer(text)
                      if _limited(text, g.clause_span(text, v.start())[0], v.start())]
            claims += list(_R4_UNREPORTED.finditer(text))
            if claims and not _anchored(doc, ln, text):
                for c in sorted(claims, key=lambda x: x.start()):
                    flags.append(Flag("R4", "b", ln.no, (), c.group(),
                                      "status claim with no as-of anchor in scope"))
            flags += _r4_a(doc, ln, text, deadline, overview)
    return flags


# ---------------------------------------------------------------- R7-a count vs its own list (v7)

def _is_name(piece):
    """v7: the first character, after markdown and opening quotes are removed, is an
    upper-case letter, or the piece starts with a registry ID. reading: backticks and leading
    spaces are removed too."""
    p = g.strip_emphasis(piece).lstrip(" `\"'" + g.LDQUO)
    ids = g.registry_ids(p)
    return bool(p[:1].isupper() or (ids and ids[0][0] == 0))


def _bare_sum(pieces):
    """Reading (C): every ";" piece is a name followed by a bare number; their sum, else None."""
    total = 0
    for p in pieces:
        nums = g.numbers(p)
        if not _is_name(p) or not nums:
            return None
        n, head = nums[0], p[:nums[0].start]
        if ("(" in head or any(c.isdigit() for c in head) or n.signed or n.pct or n.dollar
                or n.decimals or n.text.startswith("+")):
            return None
        total += int(n.value)
    return total


def _list_after(text, e):
    """v7: the parenthesis directly after the phrase, else the rest of the sentence after the
    first ":" that follows it. reading: one optional space before the "("."""
    m = re.match(r" ?\(", text[e:])
    if m:
        p = e + m.end() - 1
        q = _close(text, p)
        if q is not None:
            return text[p + 1:q]
    c = text.find(":", e)
    return text[c + 1:] if c >= 0 else None


def r7_a(doc):
    """R7-a (v7): a count phrase in prose vs the names of its own list, under readings A-C."""
    flags = []
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para"):
            continue
        for s in doc.sentences(ln.no):
            text = mask_quotes(s.text)
            for start, end, value in g.count_phrases(text, g1=True):
                if _negated(text, start, value):
                    continue
                e = end
                while e > start and text[e - 1] in PUNCT:
                    e -= 1
                lst = _list_after(s.text, e)
                if lst is None:
                    continue
                semis = _top_split(lst, (";",))
                first = _top_split(semis[0], (",", " and "))
                if not any(_is_name(p) for p in first + semis):
                    continue
                readings = {"A": sum(1 for p in first if _is_name(p)),
                            "B": sum(1 for p in semis if _is_name(p))}
                c = _bare_sum(semis)
                if c is not None:
                    readings["C"] = c
                if value not in readings.values():
                    flags.append(Flag("R7", "a", ln.no, (), text[start:end],
                                      "stated count matches no reading of its own list",
                                      {"stated": value, "readings": readings}))
    return flags


# ---------------------------------------------------------------- R8 dose (v7) and sources (v5)

_SPECIES = re.compile(_wb(r"mouse|mice|rats?"), re.IGNORECASE)
FACTOR = {"mouse": 3 / 37, "mice": 3 / 37, "rat": 6 / 37, "rats": 6 / 37}
_BSA = ("body-surface-area", "body surface area")
_TOTAL_UNIT = re.compile(r" (mg|g)(?:/day)?(?![\w/])")
_ABOUT = re.compile(r"(?<![\w\-.])about $", re.IGNORECASE)
_TO_HUMAN = re.compile(r"(?<![\w\-.])to a human $", re.IGNORECASE)
_LEAD_KG = re.compile(r"(?<![\w\-.])(\d+(?:\.\d+)?) kg(?![\w\-])")
_PLAIN = re.compile(r"\d+(?:\.\d+)?")


def _species(doc, ln, text, n):
    """v7 species of an animal dose D: after D in its clause, else before D in the sentence,
    else the line's bold lead, else the nearest earlier line of the same section. reading:
    the first one after, the nearest one before; a section is the line's ### (or ##) section."""
    _, b = g.clause_span(text, n.start)
    m = _SPECIES.search(text, n.end, b)
    if not m:
        before = list(_SPECIES.finditer(text, 0, n.start))
        m = before[-1] if before else _SPECIES.search(ln.lead)
    if not m:
        for no in range(ln.no - 1, 0, -1):
            p = doc.line(no)
            if (p.h2, p.h3) != (ln.h2, ln.h3):
                break
            m = _SPECIES.search(p.text)
            if m:
                break
    return FACTOR[m.group().lower()] if m else None


def _weight(text, n, lead):
    """v7: "for W kg" within the 4 words after T, else "W kg" in the bold lead. reading: the
    4 whitespace tokens after T's unit."""
    words = text[n.end:].split()[1:5]
    for i in range(len(words) - 2):
        if (words[i] == "for" and _PLAIN.fullmatch(words[i + 1])
                and words[i + 2].strip(PUNCT) == "kg"):
            return float(words[i + 1])
    m = _LEAD_KG.search(lead)
    return float(m.group(1)) if m else None


def r8_dose(doc):
    """R8 dose (v7): HEDs and human totals recomputed from the species factor and weight."""
    flags, checked = [], []
    for ln in doc.lines:
        if ln.kind not in ("bullet", "para") or not any(x in ln.text.lower() for x in _BSA):
            continue
        since_hed, prev_pair = [], []
        for s in doc.sentences(ln.no):
            text, since_t = s.text, []
            for n in g.numbers(text):
                before, after = text[:n.start], text[n.end:]
                if after.startswith(" mg/kg"):
                    if not _ABOUT.search(before):
                        d = (n, _species(doc, ln, text, n))
                        since_hed.append(d)
                        since_t.append(d)
                        continue
                    for d, f in since_hed:
                        if f is not None and n.value and abs(d.value * f - n.value) / n.value > 0.10:
                            flags.append(Flag("R8", "hed", ln.no, (), "%s -> %s" % (d.text, n.text),
                                              "animal dose x factor is more than 10% off the HED",
                                              {"dose": d.value, "factor": f, "hed": n.value}))
                    since_hed = []
                    continue
                u = _TOTAL_UNIT.match(after)
                if not (u and (_ABOUT.search(before) or _TO_HUMAN.search(before))):
                    continue
                pair = since_t or prev_pair
                w = _weight(text, n, ln.lead)
                total = n.value * (1000 if u.group(1) == "g" else 1)
                pairs = [(d, f) for d, f in pair if f is not None]
                if w is not None and pairs and total:
                    for d, f in pairs:
                        if abs(d.value * f * w - total) / total > 0.10:
                            flags.append(Flag("R8", "total", ln.no, (), "%s -> %s" % (d.text, n.text),
                                              "dose x factor x weight is more than 10% off the total",
                                              {"dose": d.value, "factor": f, "weight": w,
                                               "total_mg": total}))
                    if checked and checked[0][1] != w:
                        flags.append(Flag("R8", "weight", ln.no, _ev(ln.no, [checked[0][0]]),
                                          "%g kg" % w, "conversions in one package use different "
                                          "body weights", {"weights": [checked[0][1], w]}))
                    checked.append((ln.no, w))
                prev_pair, since_t, since_hed = pair, [], []
    return flags


SOURCES = (
    ("PubMed", ("PubMed",)), ("NCBI E-utilities", ("NCBI E-utilities",)), ("PMC", ("PMC",)),
    ("Europe PMC", ("Europe PMC",)), ("Crossref", ("Crossref",)),
    ("ClinicalTrials.gov", ("ClinicalTrials.gov",)), ("WHO ICTRP", ("WHO ICTRP", "ICTRP")),
    ("ChiCTR", ("ChiCTR",)), ("openFDA", ("openFDA",)), ("DailyMed", ("DailyMed",)),
    ("Drugs@FDA", ("Drugs@FDA",)), ("Orange Book", ("Orange Book",)),
)
_E6 = re.compile(r"#+\s+E\.6(?!\d)")


def _names_source(text, forms):
    for form in forms:
        for i in g.find_word(text, form):
            if form == "PMC" and text[:i].endswith("Europe "):
                continue
            if not g._in_url(text, i, i + len(form)):
                return True
    return False


def r8_sources(doc):
    """R8 sources (v5): a vocabulary source named outside section E.6 but missing from E.6."""
    e6 = _section_lines(doc, lambda t: bool(_E6.match(t)))
    if not e6:
        return []
    inside = {ln.no for ln in e6}
    e6_lines = [ln.no for ln in e6 if ln.kind != "blank"]
    flags = []
    for name, forms in SOURCES:
        if any(_names_source(mask_quotes(ln.text), forms) for ln in e6):
            continue
        used = [ln.no for ln in doc.lines if ln.no not in inside and ln.kind != "blank"
                and _names_source(mask_quotes(ln.text), forms)]
        if used:
            flags.append(Flag("R8", "source", used[0], _ev(used[0], used[1:] + e6_lines), name,
                              "source named in the package but missing from E.6"))
    return flags


def r8(doc):
    return r8_dose(doc) + r8_sources(doc)


# ---------------------------------------------------------------- parts 1 and 2

def check(doc, deadline=DEADLINE):
    """Flags of every module coded so far, sorted by line, module, rule and span."""
    flags = (m1.check(doc) + r2(doc) + r2b(doc) + r3(doc) + r4(doc, deadline) + r5b(doc)
             + r7_a(doc) + r8(doc))
    return sorted(flags, key=lambda f: (f.line, f.module, f.rule, f.span))
