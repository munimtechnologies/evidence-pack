"""LinkCheck: completeness, conflict and over-count report for linked records.

Given records from several sources (one person may have a record in more than one) and
links that say two records belong to the same person, LinkCheck:
  1  resolves every link with documented rules (the exact id, an id the source serves as
     an alternate, the part of an id after its last underscore) and says what each looser
     rule adds: a new pair, a pair already linked, a self-reference or a same-source link;
  2  counts, per source, the records that carry an informative value for each field;
  3  counts, per source pair, how often linked records agree, disagree or cannot be
     compared; an unknown value is never a conflict;
  4  joins linked records into persons and counts how much a naive union over-counts,
     with exact links only and with every chosen rule;
  5  builds a de-duplicated, conflict-aware cohort table: one row per person, each field
     resolved by a stated rule, conflicts carried as flags instead of hidden;
  6  (0.5.0) says which OMB race/ethnicity convention each record follows: 1997 (race and
     a separate Hispanic-or-Latino question) or 2024 (one combined list that includes
     "Hispanic or Latino" and "Middle Eastern or North African"), and reads Hispanic or
     Latino origin under both, so linked records written under different conventions
     can be compared. Sections 1-5 are unchanged: the 1997 reading stays as it was.

A record may name its namespace (for example the study it was submitted under). Records
are then keyed by (source, id, namespace), so two namespaces of one source may serve the
same id. A link end that names a namespace resolves to that record only; one that does not
resolves only if exactly one record of the source has the id, and is otherwise counted as
ambiguous, never guessed (0.3.0; 0.1.0-0.2.0 kept the first record).

The rules and comparisons are those of MV2's pre-registered CCDI census (evidence-pack
tag v0.5.5, ccdi/concordance-v1/analyze.py) and its post-hoc link diagnostics (tag
v0.5.10, ccdi/diagnostics-v2). Standard library only; the same input gives the same output.
The paging audit of the endpoints the records come from is in paging.py; reading a saved
CCDI Data Federation snapshot into records, links and page counts is in ccdi.py (0.4.0).

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import collections
import csv
import json

__version__ = "0.5.0"

RULES = ("exact", "alt_id", "suffix")
RACES = {"white": "White", "black or african american": "Black or African American",
         "asian": "Asian", "american indian or alaska native": "American Indian or Alaska Native",
         "native hawaiian or other pacific islander": "Native Hawaiian or other Pacific Islander"}
FIELDS = (("sex", "sex"), ("race", "race"), ("ethnicity", "ethnicity"),
          ("vital_status", "vital"), ("age_at_vital_status", "age"))
COHORT_FIELDS = ("person", "n_records", "sources", "records", "sex", "sex_conflict", "race",
                 "race_conflict", "ethnicity", "ethnicity_conflict", "vital_consensus",
                 "vital_latest", "vital_priority", "vital_conflict",
                 "hispanic", "hispanic_conflict", "race_standard")

# OMB SPD 15 as revised in 2024: seven minimum categories in one combined question. The 2024
# text drops "Other" from the Pacific Islander category; both spellings are read.
HISPANIC = "Hispanic or Latino"
MENA = "Middle Eastern or North African"
ONLY_2024 = frozenset({HISPANIC, MENA})
RACES_2024 = dict(RACES, **{"native hawaiian or pacific islander":
                            "Native Hawaiian or other Pacific Islander",
                            "hispanic or latino": HISPANIC,
                            "middle eastern or north african": MENA})
CONVENTIONS = ("1997", "2024")
STANDARDS = ("1997", "2024", "both", "contradictory", "declared_1997", "declared_2024",
             "undetermined", "no_value")


# ---------- normalising ----------

def norm_sex(v):
    return {"m": "M", "male": "M", "f": "F", "female": "F"}.get(str(v or "").strip().lower())


def norm_race(values, table=RACES):
    if values is None:
        return frozenset()
    if not isinstance(values, (list, tuple)):
        values = [values]
    return frozenset(r for r in (table.get(str(v or "").strip().lower()) for v in values) if r)


def norm_race_2024(values):
    """The race values a 2024-style combined list can hold, including Hispanic or Latino and
    Middle Eastern or North African. A value that is several categories joined by commas
    ("White, Hispanic or Latino") is read as those categories if every part is one; no
    category name contains a comma. The 1997 reading (norm_race) does not split."""
    if values is None:
        return frozenset()
    if not isinstance(values, (list, tuple)):
        values = [values]
    out = set()
    for v in values:
        s = str(v or "").strip().lower()
        if s in RACES_2024:
            out.add(RACES_2024[s])
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) > 1 and all(p in RACES_2024 for p in parts):
            out.update(RACES_2024[p] for p in parts)
    return frozenset(out)


def norm_eth(v):
    return {"hispanic or latino": "H",
            "not hispanic or latino": "NH"}.get(str(v or "").strip().lower())


def norm_vital(v):
    return {"alive": "Alive", "living": "Alive", "dead": "Dead",
            "deceased": "Dead"}.get(str(v or "").strip().lower())


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def informative(v):
    return bool(v) if isinstance(v, frozenset) else v is not None


def text(v):
    return "" if v in (None, "") else str(v)


def key_of(source, ident, namespace=""):
    """A record's key: (source, id), or (source, id, namespace) when it names one."""
    return (source, ident, namespace) if namespace else (source, ident)


def make_record(raw):
    if not isinstance(raw, dict) or raw.get("source") in (None, "") or raw.get("id") in (None, ""):
        raise ValueError("every record needs a source and an id")
    return {"source": str(raw["source"]), "id": str(raw["id"]),
            "namespace": text(raw.get("namespace")),
            "alt_ids": sorted({str(a) for a in raw.get("alt_ids") or [] if a not in (None, "")}),
            "sex": norm_sex(raw.get("sex")), "race": norm_race(raw.get("race")),
            "ethnicity": norm_eth(raw.get("ethnicity")),
            "vital": norm_vital(raw.get("vital_status")),
            "age": num(raw.get("age_at_vital_status")),
            "race_2024": norm_race_2024(raw.get("race"))}


def parse_declared(spec):
    """'A=2024,B=1997' -> {'A': '2024', 'B': '1997'}; '' -> {}."""
    out = {}
    for part in (p.strip() for p in str(spec or "").split(",")):
        if not part:
            continue
        source, sep, conv = part.rpartition("=")
        if not sep or not source or conv not in CONVENTIONS:
            raise ValueError("--declare takes SOURCE=1997 or SOURCE=2024, comma-separated")
        out[source] = conv
    return out


# ---------- OMB conventions ----------

def race_standard(r, declared=None):
    """Which OMB convention one record follows, from its own values:
    '2024'           its race list holds a 2024-only category (Hispanic or Latino, or
                     Middle Eastern or North African) and it gives no separate ethnicity;
    '1997'           it answers the separate ethnicity question and holds no 2024-only category;
    'both'           both of the above, and they do not contradict each other;
    'contradictory'  its race list says Hispanic or Latino and its ethnicity says Not Hispanic;
    'undetermined'   only categories both standards share, and no ethnicity answer;
    'no_value'       neither race nor ethnicity.
    A convention declared for the record's source ('1997' or '2024') replaces 'undetermined'
    only, as 'declared_1997' or 'declared_2024'; the record's own values always come first."""
    race, eth = r["race_2024"], r["ethnicity"]
    if HISPANIC in race and eth == "NH":
        return "contradictory"
    if race & ONLY_2024:
        return "both" if eth else "2024"
    if eth:
        return "1997"
    if race:
        return "declared_" + declared if declared in CONVENTIONS else "undetermined"
    return "no_value"


def hispanic(r, standard):
    """Hispanic or Latino origin under the record's convention: 'H', 'NH', 'NH_implied' (a
    2024-style combined list with categories but without Hispanic or Latino, which under
    that standard means not Hispanic or Latino) or None (unknown, or contradictory)."""
    if standard == "contradictory":
        return None
    if r["ethnicity"] == "H" or HISPANIC in r["race_2024"]:
        return "H"
    if r["ethnicity"] == "NH":
        return "NH"
    if standard in ("2024", "declared_2024"):
        return "NH_implied"
    return None


def origin(h):
    """'NH_implied' compares as 'NH'."""
    return "NH" if h == "NH_implied" else h


def readings(index, declared=None):
    """{record key: (standard, hispanic)} for every record."""
    declared = declared or {}
    out = {}
    for k, r in index.records.items():
        s = race_standard(r, declared.get(r["source"]))
        out[k] = (s, hispanic(r, s))
    return out


# ---------- resolving links ----------

class Index:
    """Records by key, first copy kept; the records serving each (source, id); ids served as
    alternates by (source, alt)."""

    def __init__(self, records):
        self.records, self.repeats = {}, collections.Counter()
        for raw in records:
            r = make_record(raw)
            key = key_of(r["source"], r["id"], r["namespace"])
            if key in self.records:
                self.repeats[r["source"]] += 1
            else:
                self.records[key] = r
        self.by_id, self.alt = collections.defaultdict(list), collections.defaultdict(list)
        for key, r in self.records.items():
            self.by_id[(r["source"], r["id"])].append(key)
            for a in r["alt_ids"]:
                if a != r["id"]:
                    self.alt[(r["source"], a)].append(key)

    def find(self, source, ident, namespace=""):
        """(record key, None) or (None, why not), by the exact id."""
        if namespace:
            key = (source, ident, namespace)
            return (key, None) if key in self.records else (None, "unresolved")
        hits = self.by_id.get((source, ident), [])
        if len(hits) == 1:
            return hits[0], None
        return None, ("ambiguous_id" if hits else "unresolved")

    def resolve(self, source, ident, rules, namespace=""):
        """(record key, rule) or (None, why not)."""
        source, ident = str(source), str(ident)
        key, why = self.find(source, ident, text(namespace))
        if key is not None:
            return key, "exact"
        if why == "ambiguous_id":
            return None, why
        if "alt_id" in rules:
            hits = self.alt.get((source, ident), [])
            if len(hits) == 1:
                return hits[0], "alt_id"
            if len(hits) > 1:
                return None, "ambiguous_alt_id"
        if "suffix" in rules and "_" in ident:
            short, _ = self.find(source, ident.rsplit("_", 1)[1])
            if short is not None:
                return short, "suffix"
        return None, "unresolved"

    def shared_ids(self):
        """Per source: ids that two or more namespaces serve, and the records serving them."""
        out = collections.defaultdict(lambda: {"ids": 0, "records": 0})
        for (src, _), keys in self.by_id.items():
            if len(keys) > 1:
                out[src]["ids"] += 1
                out[src]["records"] += len(keys)
        return dict(sorted(out.items()))


def link_ends(raw):
    try:
        return ((str(raw["a_source"]), str(raw["a_id"]), text(raw.get("a_namespace"))),
                (str(raw["b_source"]), str(raw["b_id"]), text(raw.get("b_namespace"))))
    except (KeyError, TypeError, AttributeError):
        raise ValueError("every link needs a_source, a_id, b_source and b_id")


def place(pairs, ka, kb, rule):
    if ka == kb:
        return "self_reference"
    if ka[0] == kb[0]:
        return "same_source"
    pair = tuple(sorted((ka, kb)))
    if pair in pairs:
        return "already_linked"
    pairs[pair] = rule
    return "new_pair"


def resolve_links(index, links, rules=RULES):
    """Two passes, so a looser rule never claims a pair an exact link makes. Pass 1 uses
    exact ids only; pass 2 retries what pass 1 could not resolve with the chosen rules.
    Returns (pairs, counts): pairs maps a sorted key pair to the rule that made it."""
    pairs, counts, retry = {}, collections.Counter(), []
    for raw in links:
        a, b = link_ends(raw)
        ka, _ = index.resolve(a[0], a[1], ("exact",), a[2])
        kb, _ = index.resolve(b[0], b[1], ("exact",), b[2])
        if ka is None or kb is None:
            retry.append((a, b))
            continue
        counts["exact: " + place(pairs, ka, kb, "exact")] += 1
    for a, b in retry:
        ka, ra = index.resolve(a[0], a[1], rules, a[2])
        kb, rb = index.resolve(b[0], b[1], rules, b[2])
        if ka is None or kb is None:
            counts["unresolved: " + (ra if ka is None else rb)] += 1
            continue
        rule = "+".join(sorted({ra, rb} - {"exact"}))
        counts[rule + ": " + place(pairs, ka, kb, rule)] += 1
    return pairs, dict(sorted(counts.items()))


# ---------- comparing ----------

def cmp_scalar(a, b):
    if a is None or b is None:
        return "uninformative"
    return "agree" if a == b else "disagree"


def cmp_race(a, b):
    if not a or not b:
        return "uninformative"
    if a == b:
        return "agree"
    return "overlap" if a & b else "disagree"


def cmp_vital(av, aa, bv, ba):
    """Vital status of one person in two records, each with the age (days) it refers to."""
    if av is None or bv is None:
        return "uninformative"
    if av == bv:
        return "both_alive" if av == "Alive" else "both_dead"
    alive_age, dead_age = (aa, ba) if av == "Alive" else (ba, aa)
    if alive_age is None or dead_age is None:
        return "alive_dead_no_ages"
    return "alive_then_dead" if alive_age <= dead_age + 1 else "alive_after_death"


def cmp_death_age(a, b):
    if a["vital"] != "Dead" or b["vital"] != "Dead" or a["age"] is None or b["age"] is None:
        return None
    d = abs(a["age"] - b["age"])
    return "within_1_day" if d <= 1 else ("within_30_days" if d <= 30 else "over_30_days")


def tally(pairs):
    out = {"pairs": 0, "sex": collections.Counter(), "race": collections.Counter(),
           "ethnicity": collections.Counter(), "vital_status": collections.Counter(),
           "age_at_death": collections.Counter()}
    for a, b in pairs:
        out["pairs"] += 1
        out["sex"][cmp_scalar(a["sex"], b["sex"])] += 1
        out["race"][cmp_race(a["race"], b["race"])] += 1
        out["ethnicity"][cmp_scalar(a["ethnicity"], b["ethnicity"])] += 1
        out["vital_status"][cmp_vital(a["vital"], a["age"], b["vital"], b["age"])] += 1
        d = cmp_death_age(a, b)
        if d:
            out["age_at_death"][d] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, collections.Counter) else v)
            for k, v in out.items()}


# ---------- sections ----------

def completeness(index):
    by_src = collections.defaultdict(list)
    for r in index.records.values():
        by_src[r["source"]].append(r)
    out = {}
    for src in sorted(set(by_src) | set(index.repeats)):
        rs = by_src.get(src, [])
        out[src] = {"records": len(rs), "repeated_records": index.repeats.get(src, 0),
                    "informative": {name: sum(1 for r in rs if informative(r[key]))
                                    for name, key in FIELDS}}
    return out


def conflicts(index, pair_keys):
    by_pair = collections.defaultdict(list)
    for ka, kb in pair_keys:
        a, b = index.records[ka], index.records[kb]
        by_pair[" | ".join(sorted([a["source"], b["source"]]))].append((a, b))
    return {"by_source_pair": {k: tally(v) for k, v in sorted(by_pair.items())},
            "all": tally([p for k in sorted(by_pair) for p in by_pair[k]])}


def persons(index, pair_keys):
    """Every record grouped into persons by the links (union-find); sorted, deterministic."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ka, kb in pair_keys:
        ra, rb = find(ka), find(kb)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups = collections.defaultdict(list)
    for key in index.records:
        groups[find(key) if key in parent else key].append(key)
    return sorted(sorted(g) for g in groups.values())


def overcount(index, groups):
    linked = [g for g in groups if len(g) > 1]
    return {"records": len(index.records), "records_in_links": sum(len(g) for g in linked),
            "linked_persons": len(linked), "persons": len(groups),
            "naive_overcount": len(index.records) - len(groups),
            "persons_with_2plus_records_in_one_source":
                sum(1 for g in linked if len({k[0] for k in g}) < len(g)),
            "largest_person": max((len(g) for g in groups), default=0)}


def standards_by_source(index, read):
    out = collections.defaultdict(lambda: {"records": 0, "convention": collections.Counter(),
                                           "hispanic": collections.Counter(),
                                           "hispanic_in_race_list": 0,
                                           "values_2024_only": collections.Counter()})
    for k, r in index.records.items():
        s, h = read[k]
        row = out[r["source"]]
        row["records"] += 1
        row["convention"][s] += 1
        row["hispanic"][h or "unknown"] += 1
        row["hispanic_in_race_list"] += int(HISPANIC in r["race_2024"])
        for v in sorted(r["race_2024"] & ONLY_2024):
            row["values_2024_only"][v] += 1
    return {src: {k: (dict(sorted(v.items())) if isinstance(v, collections.Counter) else v)
                  for k, v in row.items()} for src, row in sorted(out.items())}


def standards_tally(index, read, pairs):
    """Linked pairs read under both conventions: Hispanic or Latino origin compared with
    'NH_implied' as 'NH'; race compared on the 2024 categories other than Hispanic or Latino;
    the pair of conventions; and, where exactly one record's 'not Hispanic' is only implied
    by a 2024 reading, what the other record says when it answers the question itself."""
    out = {"pairs": 0, "hispanic": collections.Counter(), "race_2024": collections.Counter(),
           "conventions": collections.Counter(), "implied_nh_vs_stated": collections.Counter()}
    for ka, kb in pairs:
        (sa, ha), (sb, hb) = read[ka], read[kb]
        ra = index.records[ka]["race_2024"] - {HISPANIC}
        rb = index.records[kb]["race_2024"] - {HISPANIC}
        out["pairs"] += 1
        out["hispanic"][cmp_scalar(origin(ha), origin(hb))] += 1
        out["race_2024"][cmp_race(ra, rb)] += 1
        out["conventions"][" | ".join(sorted([sa, sb]))] += 1
        for mine, other in ((ha, hb), (hb, ha)):
            if mine == "NH_implied" and other in ("H", "NH"):
                out["implied_nh_vs_stated"][other] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, collections.Counter) else v)
            for k, v in out.items()}


def standards_pairs(index, read, pair_keys):
    by_pair = collections.defaultdict(list)
    for ka, kb in pair_keys:
        by_pair[" | ".join(sorted([ka[0], kb[0]]))].append((ka, kb))
    return {"by_source_pair": {k: standards_tally(index, read, v)
                               for k, v in sorted(by_pair.items())},
            "all": standards_tally(index, read, [p for k in sorted(by_pair)
                                                 for p in by_pair[k]])}


def hispanic_conflicts(read, groups):
    """Persons whose records say both Hispanic or Latino and not ('NH_implied' as 'NH')."""
    return sum(1 for g in groups if len(g) > 1
               and {"H", "NH"} <= {origin(read[k][1]) for k in g})


def standards(index, declared, exact, every, groups_exact, groups_all):
    read = readings(index, declared)
    return {"declared": dict(sorted((declared or {}).items())),
            "by_source": standards_by_source(index, read),
            "pairs": {"exact": standards_pairs(index, read, exact),
                      "with_rules": standards_pairs(index, read, every)},
            "persons_hispanic_conflict": {"exact": hispanic_conflicts(read, groups_exact),
                                          "with_rules": hispanic_conflicts(read, groups_all)}}


# ---------- cohort ----------

def consensus(values):
    """(value, conflict): the single informative value, or (None, True) if they differ."""
    vals = {v for v in values if informative(v)}
    if not vals:
        return None, False
    if len(vals) == 1:
        return next(iter(vals)), False
    return None, True


def vital_latest(recs):
    """Death is final: Dead wins, unless a record says Alive at an age more than one day
    after the latest age at death (alive after death), which is a conflict."""
    dead = [r for r in recs if r["vital"] == "Dead"]
    alive = [r for r in recs if r["vital"] == "Alive"]
    if not dead:
        return ("Alive" if alive else None), False
    dead_ages = [r["age"] for r in dead if r["age"] is not None]
    if dead_ages and any(r["age"] is not None and r["age"] > max(dead_ages) + 1 for r in alive):
        return None, True
    return "Dead", False


def vital_priority(recs, priority):
    """The first informative value in the stated source order; unlisted sources come
    after the listed ones, in name order."""
    rank = {s: i for i, s in enumerate(priority)}
    for r in sorted(recs, key=lambda r: (rank.get(r["source"], len(rank)), r["source"],
                                         r["id"], r["namespace"])):
        if r["vital"]:
            return r["vital"]
    return None


def shown(value, conflict):
    if conflict:
        return "conflict"
    if isinstance(value, frozenset):
        return ";".join(sorted(value))
    return value or ""


def cohort(index, groups, priority=(), declared=None):
    read = readings(index, declared)
    rows = []
    for n, g in enumerate(groups, 1):
        recs = [index.records[k] for k in g]
        row = {"person": "P%06d" % n, "n_records": len(recs),
               "sources": ";".join(sorted({r["source"] for r in recs})),
               "records": ";".join(":".join(k) for k in g)}
        for name, key in (("sex", "sex"), ("race", "race"), ("ethnicity", "ethnicity")):
            value, conflict = consensus(r[key] for r in recs)
            row[name] = shown(value, conflict)
            row[name + "_conflict"] = int(conflict)
        row["vital_consensus"] = shown(*consensus(r["vital"] for r in recs))
        row["vital_latest"] = shown(*vital_latest(recs))
        row["vital_priority"] = vital_priority(recs, priority) or ""
        row["vital_conflict"] = int({"Alive", "Dead"} <= {r["vital"] for r in recs})
        value, conflict = consensus(origin(read[k][1]) for k in g)
        row["hispanic"] = shown(value, conflict)
        row["hispanic_conflict"] = int(conflict)
        row["race_standard"] = ";".join(sorted({read[k][0] for k in g}))
        rows.append(row)
    return rows


def cohort_summary(rows):
    out = {"persons": len(rows)}
    for col in ("vital_consensus", "vital_latest", "vital_priority"):
        out[col] = dict(sorted(collections.Counter(r[col] or "missing" for r in rows).items()))
    for col in ("sex_conflict", "race_conflict", "ethnicity_conflict", "vital_conflict"):
        out[col] = sum(r[col] for r in rows)
    return out


# ---------- the whole check ----------

def check(records, links, rules=RULES, priority=(), declared=None):
    """(aggregate report, person-level cohort rows). Only the report is aggregate.
    declared: {source: '1997' or '2024'}, the OMB convention a source is known to follow,
    used only for records whose own values cannot tell (see race_standard)."""
    unknown = sorted(set(rules) - set(RULES))
    if unknown:
        raise ValueError("unknown rule(s): " + ", ".join(unknown))
    declared = dict(declared or {})
    bad = sorted(s for s, c in declared.items() if c not in CONVENTIONS)
    if bad:
        raise ValueError("declared convention must be 1997 or 2024 for: " + ", ".join(bad))
    rules = tuple(r for r in RULES if r in rules or r == "exact")
    index = Index(records)
    links = list(links)
    pairs, link_counts = resolve_links(index, links, rules)
    exact = sorted(p for p, r in pairs.items() if r == "exact")
    every = sorted(pairs)
    groups_exact, groups_all = persons(index, exact), persons(index, every)
    rows = cohort(index, groups_all, priority, declared)
    report = {"tool": "linkcheck " + __version__, "rules": list(rules),
              "priority": list(priority),
              "completeness": completeness(index),
              "shared_ids": index.shared_ids(),
              "links": {"rows": len(links), "resolution": link_counts,
                        "pairs_exact": len(exact), "pairs_with_rules": len(every),
                        "pairs_added_by_rule": dict(sorted(collections.Counter(
                            r for r in pairs.values() if r != "exact").items()))},
              "conflicts": {"exact": conflicts(index, exact),
                            "with_rules": conflicts(index, every)},
              "overcount": {"exact": overcount(index, groups_exact),
                            "with_rules": overcount(index, groups_all)},
              "cohort_summary": cohort_summary(rows),
              "standards": standards(index, declared, exact, every, groups_exact, groups_all)}
    return report, rows


def suppress(obj, k):
    """Show every count from 1 to k-1 as '<k' (small-cell protection); k <= 1 is off."""
    if k <= 1:
        return obj
    if isinstance(obj, dict):
        return {key: suppress(v, k) for key, v in obj.items()}
    if isinstance(obj, list):
        return [suppress(v, k) for v in obj]
    if isinstance(obj, int) and not isinstance(obj, bool) and 0 < obj < k:
        return "<%d" % k
    return obj


# ---------- files ----------

def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                raise ValueError("%s line %d is not JSON" % (path, n))
    return out


def write_cohort(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COHORT_FIELDS)
        w.writeheader()
        w.writerows(rows)
