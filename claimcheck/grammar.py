"""Shared reading rules for claimcheck v1.

Implements the shared definitions of the claim-checker evaluation plan
(findings/claim-checker/): v4 section 3 (sentence, clause, name matching,
registry IDs and names, count phrase), v5 section 3 (text read, word
boundary), v6 section 3 (G1 numbers, G2 labels, G3-G5 CI tuples) and v7
section 3 (linked tables). Where the plans leave a choice open, the reading
taken here is listed in claimcheck/CODING-NOTES.md and marked "reading:".

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import re
from dataclasses import dataclass, field

MINUS = chr(0x2212)
NDASH = chr(0x2013)
MIDDOT = chr(0x00B7)
LDQUO = chr(0x201C)
RDQUO = chr(0x201D)

CUT_MARKERS = ("## Notes for the submitter", "Submitter notes")
NUMBER_WORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen "
                "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
WORD_VALUE = {w: i + 1 for i, w in enumerate(NUMBER_WORDS)}
COUNT_NOUNS = ("records", "trials", "hits", "studies", "registrations")
G2_LABELS = ("95% confidence interval", "95% CIs", "95% CI", "CI")

_PUNCT = "()[]\"'*,.;:" + LDQUO + RDQUO


# ---------------------------------------------------------------- lines and cut

def read_lines(text):
    """Split like bytes.splitlines(): on CRLF, CR and LF only."""
    lines = re.split(r"\r\n|\r|\n", text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def cut_count(lines):
    """Lines kept by the v4 cut rule (the same rule as basetext-hash-v1)."""
    for i, line in enumerate(lines):
        if line.startswith(CUT_MARKERS):
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0 and lines[j].strip() == "---":
                return j
            return i
    return len(lines)


_UNDERSCORE = re.compile(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])")


def strip_emphasis(s):
    """Remove markdown emphasis. reading: "_" only at a word edge, so rwe_recheck stays."""
    return _UNDERSCORE.sub("", s.replace("**", "").replace("*", ""))


# ---------------------------------------------------------------- name matching

def _boundary_before(text, i):
    if i == 0:
        return True
    c = text[i - 1]
    # A "." is a boundary only when followed by a space or a line end; here the word follows it.
    return not (c.isalnum() or c in "-_.")


def _boundary_after(text, j):
    if j >= len(text):
        return True
    c = text[j]
    if c == ".":
        return j + 1 >= len(text) or text[j + 1] == " "
    return not (c.isalnum() or c in "-_")


def find_word(text, word, ignore_case=False):
    """Start offsets of word-bounded matches of word (v4 name matching)."""
    pat = re.compile(re.escape(word), re.IGNORECASE if ignore_case else 0)
    out, pos = [], 0
    while True:
        m = pat.search(text, pos)
        if not m:
            return out
        if _boundary_before(text, m.start()) and _boundary_after(text, m.end()):
            out.append(m.start())
        pos = m.start() + 1


_ID_PATTERNS = (
    ("NCT", r"NCT\d{8}(?!\d)"),
    ("ChiCTR", r"ChiCTR\d+"),
    ("ISRCTN", r"ISRCTN\d+"),
    ("EUCTR", r"EUCTR[\d-]+"),
    ("CTIS", r"CTIS \d{4}-\d+-\d+-\d+"),
    ("ACTRN", r"ACTRN\d+"),
    ("DRKS", r"DRKS\d+"),
    ("IRCT", r"IRCT\w+"),
    ("JPRN", r"JPRN-\w+"),
    ("jRCT", r"jRCT\w+"),
)
_ID_RES = tuple((k, re.compile(r"(?<![A-Za-z0-9])" + p)) for k, p in _ID_PATTERNS)

REGISTRY_NAMES = {
    "ClinicalTrials.gov": ("NCT",),
    "ChiCTR": ("ChiCTR",),
    "ISRCTN": ("ISRCTN",),
    "ANZCTR": ("ACTRN",),
    "EU CTR": ("EUCTR", "CTIS"),
    "CTIS": ("EUCTR", "CTIS"),
    "DRKS": ("DRKS",),
    "IRCT": ("IRCT",),
    "jRCT": ("JPRN", "jRCT"),
    "JPRN": ("JPRN", "jRCT"),
}
ALL_PATTERN_TERMS = ("ICTRP", "WHO", "registry", "registered")


def registry_ids(text):
    """[(start, end, id, pattern key)] for v4's registry ID patterns, left to right."""
    found = []
    for key, pat in _ID_RES:
        found.extend((m.start(), m.end(), m.group(), key) for m in pat.finditer(text))
    found.sort()
    out = []
    for item in found:
        if not out or item[0] >= out[-1][1]:
            out.append(item)
    return out


_URLISH = re.compile(r"\.[A-Za-z]")


def _in_url(text, i, j):
    """reading: a name is inside a URL when its non-space run holds "://", when "/" or "."
    touches it, or when the run outside the name still has a "." followed by a letter."""
    a = i
    while a > 0 and not text[a - 1].isspace():
        a -= 1
    b = j
    while b < len(text) and not text[b].isspace():
        b += 1
    if "://" in text[a:b]:
        return True
    if (i > 0 and text[i - 1] in "./") or (j < len(text) and text[j] == "/"):
        return True
    left = text[a:i].lstrip(_PUNCT)
    right = text[j:b].rstrip(_PUNCT)
    return bool(_URLISH.search(left) or _URLISH.search(right))


def registry_names(text):
    """[(start, name)] for registry names and all-patterns terms (case-sensitive, v4)."""
    ids = registry_ids(text)
    out = []
    for name in list(REGISTRY_NAMES) + list(ALL_PATTERN_TERMS):
        for i in find_word(text, name):
            j = i + len(name)
            if any(a < j and i < b for a, b, _, _ in ids) or _in_url(text, i, j):
                continue
            out.append((i, name))
    out.sort()
    return out


# ---------------------------------------------------------------- sentences and clauses

def split_sentences(raw):
    """v4 sentence rule on one physical line: [(offset, piece)]. Split after ". " when the
    next character is upper-case, "*" or "(", never inside parentheses or quotation marks."""
    out, start, depth, quoted = [], 0, 0, False
    for i, c in enumerate(raw):
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c == '"':
            quoted = not quoted
        elif c == LDQUO:
            quoted = True
        elif c == RDQUO:
            quoted = False
        elif (c == "." and depth == 0 and not quoted and raw[i + 1:i + 2] == " "
              and i + 2 < len(raw) and (raw[i + 2].isupper() or raw[i + 2] in "*(")):
            out.append((start, raw[start:i + 1]))
            start = i + 2
    if raw[start:].strip():
        out.append((start, raw[start:]))
    return out


def clause_span(s, pos):
    """v4 clause holding offset pos: the innermost parenthesis pair enclosing it (or the
    whole string), split on ";" at that pair's own depth. Returns (start, end)."""
    stack, pairs = [], []
    for i, c in enumerate(s):
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            pairs.append((stack.pop(), i))
    lo, hi, best = 0, len(s), None
    for a, b in pairs:
        if a < pos < b and (best is None or a > best[0]):
            best = (a, b)
    if best:
        lo, hi = best[0] + 1, best[1]
    cuts, depth, quoted = [lo - 1], 0, False
    for i in range(lo, hi):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c == '"':
            quoted = not quoted
        elif c == LDQUO:
            quoted = True
        elif c == RDQUO:
            quoted = False
        elif c == ";" and depth == 0 and not quoted:
            cuts.append(i)
    cuts.append(hi)
    for k in range(len(cuts) - 1):
        a, b = cuts[k] + 1, cuts[k + 1]
        if a <= pos < b:
            return a, b
    return lo, hi


# ---------------------------------------------------------------- G1 numbers, G2 labels

@dataclass(frozen=True)
class Num:
    start: int
    end: int
    text: str
    value: float
    signed: bool     # printed with "-" or the minus sign
    pct: bool
    dollar: bool
    decimals: int


_NUM_RE = re.compile("([-+" + MINUS + r"])?(\$)?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(%)?")
_DATE_RE = re.compile(r"(?<!\d)\d{4}-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?(?!\d)")
_BRACKET_RE = re.compile(r"\[[^\[\]]*\]")
_GLUE = "/:" + MIDDOT


def label_spans(text):
    """[(start, end, label)] for G2 labels; these are never numbers."""
    spans = []
    for lab in G2_LABELS:
        for i in find_word(text, lab):
            j = i + len(lab)
            if not any(a < j and i < b for a, b, _ in spans):
                spans.append((i, j, lab))
    return sorted(spans)


def numbers(text):
    """G1 numbers of text, left to right."""
    masked = [m.span() for m in _DATE_RE.finditer(text)]
    masked += [m.span() for m in _BRACKET_RE.finditer(text)]
    masked += [(a, b) for a, b, _ in label_spans(text)]
    out = []
    for m in _NUM_RE.finditer(text):
        sign, dollar, body, pct = m.groups()
        start, end = m.start(), m.end()
        if sign == "-" and start > 0 and (text[start - 1].isdigit() or text[start - 1] == "%"):
            sign, start = None, start + 1          # a "-" between two numbers separates them
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        nxt = text[end + 1] if end + 1 < len(text) else ""
        if before and (before.isalnum() or before in "_." + _GLUE):
            continue
        if after and (after.isalnum() or after == "_" or after in _GLUE):
            continue
        if (after == "-" and nxt.isalpha()) or (after == "." and nxt.isdigit()):
            continue
        if any(a < end and start < b for a, b in masked):
            continue
        signed = sign in ("-", MINUS)
        value = float(body.replace(",", ""))
        decimals = len(body.split(".", 1)[1]) if "." in body else 0
        out.append(Num(start, end, text[start:end], -value if signed else value,
                       signed, bool(pct), bool(dollar), decimals))
    return out


# ---------------------------------------------------------------- G3-G5 CI tuples

@dataclass(frozen=True)
class CITuple:
    est: Num
    lo: Num
    hi: Num
    form: str        # "G4" or "G5"
    paren: int       # offset of the "("


_WORD_CLOSE = re.compile(r" [^\s\d()]+\)")


def _paren_pairs(text):
    stack, pairs = [], {}
    for i, c in enumerate(text):
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            pairs[stack.pop()] = i
    return pairs


def _after_label(text, i, labels):
    end = labels.get(i)
    if end is not None and text[end:end + 1] == " ":
        return end + 1
    return i


def _pair_at(text, i, by_start, joiners):
    n1 = by_start.get(i)
    if n1 is None:
        return None
    for j in joiners:
        if text.startswith(j, n1.end):
            n2 = by_start.get(n1.end + len(j))
            return (n1, n2) if n2 else None
    return None


def _estimate_before(text, p, nums):
    prev = [n for n in nums if n.end <= p]
    if not prev:
        return None
    est = prev[-1]
    gap = text[est.end:p]
    if ")" in gap or ";" in gap or "|" in gap or len(gap.split()) > 6:
        return None
    return est


def ci_tuples(text):
    """CI tuples of one sentence or one table cell (v6 G3-G5)."""
    nums = numbers(text)
    by_start = {n.start: n for n in nums}
    labels = {a: b for a, b, _ in label_spans(text)}
    pairs = _paren_pairs(text)
    out = []
    for p, c in enumerate(text):
        if c != "(":
            continue
        # G4: the parenthesis opens with the pair, after an optional label.
        pair = _pair_at(text, _after_label(text, p + 1, labels), by_start, (" to ", "-", ", "))
        if pair:
            rest = text[pair[1].end:]
            if rest[:1] in (")", ";", ",") or _WORD_CLOSE.match(rest):
                est = _estimate_before(text, p, nums)
                if est is not None:
                    out.append(CITuple(est, pair[0], pair[1], "G4", p))
                    continue
        # G5: x, then ", ", an optional label, then the pair, inside one parenthesis.
        q = pairs.get(p)
        inside = [n for n in nums if n.start > p and q is not None and n.end <= q]
        if not inside or not text.startswith(", ", inside[0].end):
            continue
        x = inside[0]
        pair = _pair_at(text, _after_label(text, x.end + 2, labels), by_start, (" to ", "-"))
        if pair and text[pair[1].end:pair[1].end + 1] in (")", ";", ","):
            out.append(CITuple(x, pair[0], pair[1], "G5", p))
    return out


# ---------------------------------------------------------------- count phrases, citations

def count_phrases(text, g1=False):
    """v4 count phrase: a number (digits, or one..twenty in any case) followed, with at most
    3 words in between, by records|trials|hits|studies|registrations.
    With g1=True the digits must be a G1 integer with no sign, "%" or "$" (v7 R7-a).
    Returns [(start of number, end of noun, value)]."""
    toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]
    g1_ints = {}
    if g1:
        for n in numbers(text):
            if not (n.signed or n.pct or n.dollar or n.decimals or n.text.startswith("+")):
                g1_ints[(n.start, n.end)] = int(n.value)
    out = []
    for k, (a, b, tok) in enumerate(toks):
        core = tok.strip(_PUNCT)
        ca = a + tok.find(core) if core else a
        value = WORD_VALUE.get(core.lower())
        if value is None:
            if g1:
                value = g1_ints.get((ca, ca + len(core)))
            elif re.fullmatch(r"\d+", core):
                value = int(core)
        if value is None:
            continue
        for m in range(k + 1, min(k + 5, len(toks))):
            if toks[m][2].strip(_PUNCT) in COUNT_NOUNS:
                out.append((ca, toks[m][1], value))
                break
    return out


_CITE_RE = re.compile(r"\[(\d+[a-z]?(?:\s*[,;" + NDASH + r"-]\s*\d+[a-z]?)*)\]")
_CITE_SPLIT = re.compile(r"\s*([,;" + NDASH + r"-])\s*")


def cite_keys(text):
    """Reference keys of the bracket citations in text, in order; ranges count each number."""
    keys = []
    for m in _CITE_RE.finditer(text):
        parts = _CITE_SPLIT.split(m.group(1))
        items, seps = parts[0::2], parts[1::2]
        keys.append(items[0])
        for prev, sep, k in zip(items, seps, items[1:]):
            if sep in ("-", NDASH) and prev.isdigit() and k.isdigit() and int(prev) < int(k):
                keys.extend(str(x) for x in range(int(prev) + 1, int(k) + 1))
            else:
                keys.append(k)
    return keys


# ---------------------------------------------------------------- document structure

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
_REF = re.compile(r"^(\d+[a-z]?)\.\s")
_SEP_CELL = re.compile(r"^:?-{3,}:?$")


def split_cells(raw):
    s = raw.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


@dataclass
class Line:
    no: int                  # 1-based line number
    raw: str
    kind: str                # blank heading table_header table_sep table_row bullet para ref
    level: int = 0           # heading level
    h2: int = 0              # line number of the governing "#"/"##" heading (0: none)
    h3: int = 0              # line number of the governing "###" heading (0: none)
    table: int = -1          # index into Doc.tables
    lead: str = ""           # bold lead, emphasis removed
    ref: str = ""            # reference key for reference-list entries
    indent: int = 0
    body: int = 0            # offset where the line's text starts (after a bullet marker)

    @property
    def text(self):
        return strip_emphasis(self.raw)


@dataclass
class Table:
    header_line: int
    header: list
    rows: list               # [(line number, [cells])]
    heading_line: int        # nearest heading above the table (0: none)
    cites: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Sentence:
    line: int
    start: int               # offset of the raw piece in the raw line
    raw: str
    text: str                # emphasis removed, outer spaces stripped


class Doc:
    """A cut evidence package: lines, sections, tables and the reference list."""

    def __init__(self, text):
        raw = read_lines(text)
        self.total_lines = len(raw)
        self.cut = cut_count(raw)
        raw = raw[:self.cut]
        self.lines, self.tables = [], []
        in_table = [False] * len(raw)
        i = 0
        while i < len(raw):
            if raw[i].lstrip().startswith("|"):
                j = i
                while j < len(raw) and raw[j].lstrip().startswith("|"):
                    j += 1
                if j - i >= 2 and all(_SEP_CELL.match(c) for c in split_cells(raw[i + 1])):
                    for k in range(i, j):
                        in_table[k] = True
                i = j
            else:
                i += 1
        h2 = h3 = last_heading = 0
        in_refs = False
        for idx, line in enumerate(raw):
            no = idx + 1
            hm = _HEADING.match(line)
            if in_table[idx]:
                if idx == 0 or not in_table[idx - 1]:
                    self.tables.append(Table(no, split_cells(line), [], last_heading))
                    kind = "table_header"
                elif self.tables[-1].header_line == no - 1:
                    kind = "table_sep"
                else:
                    kind = "table_row"
                    self.tables[-1].rows.append((no, split_cells(line)))
                self.lines.append(Line(no, line, kind, h2=h2, h3=h3, table=len(self.tables) - 1))
                continue
            if hm:
                level = len(hm.group(1))
                if level <= 2:
                    h2, h3 = no, 0
                elif level == 3:
                    h3 = no
                last_heading = no
                in_refs = hm.group(2).strip().lower().startswith("references")
                self.lines.append(Line(no, line, "heading", level=level, h2=h2, h3=h3))
                continue
            if line.strip() == "":
                self.lines.append(Line(no, line, "blank", h2=h2, h3=h3))
                continue
            rm = _REF.match(line) if in_refs else None
            bm = _BULLET.match(line)
            if rm:
                kind, ref, body, indent = "ref", rm.group(1), 0, 0
            elif bm:
                kind, ref, body, indent = "bullet", "", bm.end(), len(bm.group(1))
            else:
                kind, ref, body, indent = "para", "", len(line) - len(line.lstrip()), 0
            lead = ""
            rest = line[body:]
            if rest.startswith("**"):
                close = rest.find("**", 2)
                if close > 2:
                    lead = strip_emphasis(rest[2:close])
            self.lines.append(Line(no, line, kind, h2=h2, h3=h3, lead=lead, ref=ref,
                                   indent=indent, body=body))
        for t in self.tables:
            keys = set()
            if t.heading_line:
                keys.update(cite_keys(self.line(t.heading_line).raw))
            for cell in t.header:
                keys.update(cite_keys(cell))
            for _, cells in t.rows:
                for cell in cells:
                    keys.update(cite_keys(cell))
            t.cites = frozenset(keys)

    def line(self, no):
        return self.lines[no - 1]

    def sentences(self, no):
        """Sentences of a bullet, paragraph, reference or table-body line (none for headings,
        table header and separator rows, and blank lines)."""
        ln = self.line(no)
        if ln.kind in ("blank", "heading", "table_header", "table_sep"):
            return []
        out = []
        for off, piece in split_sentences(ln.raw[ln.body:]):
            text = strip_emphasis(piece).strip()
            if text:
                out.append(Sentence(no, ln.body + off, piece, text))
        return out

    def linked_tables(self, no):
        """v7: indices of tables whose [n] citations this non-table line also carries."""
        ln = self.line(no)
        if ln.kind not in ("bullet", "para"):
            return []
        keys = set(cite_keys(ln.raw))
        return [i for i, t in enumerate(self.tables) if keys & t.cites]

    def references(self):
        """[(key, line number)] of the reference-list entries."""
        return [(ln.ref, ln.no) for ln in self.lines if ln.kind == "ref"]
