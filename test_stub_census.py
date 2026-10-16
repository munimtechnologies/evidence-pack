# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Offline tests: no network.
import json
import unittest
import urllib.parse

import stub_census as st

# Reference shapes copied from Crossref deposits read on 2026-10-16
WILEY_BMJOPEN = {"key": "e_1_2_11_3_1", "doi-asserted-by": "publisher", "DOI": "10.1136/bmjopen‐2016‐012545"}
WILEY_LANCET = {"key": "e_1_2_12_58_1", "doi-asserted-by": "publisher", "DOI": "10.1016/S0140‐6736(11)61817‐5"}
SAGE_LANCET = {"key": "bibr18-17456916221141374", "doi-asserted-by": "publisher", "DOI": "10.1016/S0140-6736(18)31130-9"}
MDPI_LANCET = {"key": "ref_1", "doi-asserted-by": "crossref", "first-page": "1490", "DOI": "10.1016/S0140-6736(13)61649-9"}
UNRELATED = {"key": "ref_2", "DOI": "10.1001/jama.2020.1234"}


def fake_fetch(pages):
    """Serves canned OpenAlex responses keyed by the 'filter' parameter; records the URLs asked for."""
    asked = []

    def f(url):
        asked.append(url)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        body = pages.get(q.get("filter"))
        return None if body is None else json.dumps(body).encode()

    f.asked = asked
    return f


class Stems(unittest.TestCase):
    def test_lancet_gives_dash_and_paren_stems(self):
        self.assertEqual(st.stubs_of("https://doi.org/10.1016/S0140-6736(13)62361-2"),
                         [("10.1016/s0140", "dash"), ("10.1016/s0140-6736", "paren")])

    def test_bmj_open_and_bmc(self):
        self.assertEqual(st.stubs_of("10.1136/bmjopen-2019-012345"), [("10.1136/bmjopen", "dash")])
        self.assertEqual(st.stubs_of("10.1186/1471-2458-12-345"), [("10.1186/1471", "dash")])

    def test_no_breaker_no_stem(self):
        self.assertEqual(st.stubs_of("10.1001/jama.2020.1234"), [])
        self.assertEqual(st.stubs_of("10.1016/j.physbeh.2017.03.040"), [])
        self.assertEqual(st.stubs_of(""), [])
        self.assertEqual(st.stubs_of("not a doi"), [])

    def test_too_short_or_unsafe_stems_dropped(self):
        self.assertEqual(st.stubs_of("10.1002/(sici)1097-0258(19990115)18:1<1::aid-sim1>3.0.co;2-x"), [])
        self.assertEqual(st.stubs_of("10.1234/a-b"), [])

    def test_kind_of_pilot(self):
        self.assertEqual(st.kind_of("10.1016/s0140-6736"), "paren")
        self.assertEqual(st.kind_of("10.1136/bmjopen"), "dash")
        self.assertEqual(sum(1 for s in st.PILOT if st.kind_of(s) == "paren"), 1)


class Labels(unittest.TestCase):
    def test_unicode_cut(self):
        self.assertEqual(st.ref_label(WILEY_BMJOPEN["DOI"], "10.1136/bmjopen"), "cut_at_unicode_dash")
        self.assertEqual(st.ref_label(WILEY_LANCET["DOI"], "10.1016/s0140"), "cut_at_unicode_dash")

    def test_unicode_inside_paren_stem(self):
        self.assertEqual(st.ref_label(WILEY_LANCET["DOI"], "10.1016/s0140-6736"), "has_unicode_dash")

    def test_ascii_and_exact_and_other(self):
        self.assertEqual(st.ref_label(SAGE_LANCET["DOI"], "10.1016/s0140"), "intact_ascii")
        self.assertEqual(st.ref_label("10.1136/BMJOPEN", "10.1136/bmjopen"), "exact")
        self.assertIsNone(st.ref_label(UNRELATED["DOI"], "10.1016/s0140"))
        self.assertIsNone(st.ref_label(None, "10.1016/s0140"))

    def test_read_citer_picks_strongest(self):
        r = st.read_citer("10.1111/bcp.15970", "10.1016/s0140", {"reference": [UNRELATED, SAGE_LANCET, WILEY_LANCET]})
        self.assertEqual(r["label"], "cut_at_unicode_dash")
        self.assertTrue(r["wiley"])
        self.assertEqual(r["n_journal_refs"], 2)
        self.assertEqual(r["asserted_by"], "publisher")

    def test_read_citer_statuses(self):
        self.assertEqual(st.read_citer("10.3390/x", "s", None)["status"], "not_in_crossref")
        self.assertEqual(st.read_citer("10.3390/x", "s", {"reference": []})["status"], "no_reference_list")
        r = st.read_citer("10.3390/jcm13010040", "10.1016/s0140", {"reference": [MDPI_LANCET]})
        self.assertEqual((r["label"], r["wiley"]), ("intact_ascii", False))
        r = st.read_citer("10.3390/jcm13010040", "10.1136/bmjopen", {"reference": [MDPI_LANCET]})
        self.assertEqual(r["label"], "absent")


class Groups(unittest.TestCase):
    PUB = {"meta": {"count": 1089}, "group_by": [
        {"key": "P1", "key_display_name": "Wiley", "count": 1045},
        {"key": "P2", "key_display_name": "Springer Nature", "count": 32},
        {"key": "P3", "key_display_name": "Elsevier BV", "count": 6}]}
    YEARS = {"meta": {"count": 10}, "group_by": [
        {"key": "1970", "key_display_name": "1970", "count": 7},
        {"key": "2012", "key_display_name": "2012", "count": 2},
        {"key": "2023", "key_display_name": "2023", "count": 1}]}

    def test_wiley_share(self):
        self.assertAlmostEqual(st.wiley_share(self.PUB), 1045 / 1089)
        self.assertIsNone(st.wiley_share(None))
        self.assertIsNone(st.wiley_share({"meta": {"count": 0}, "group_by": []}))

    def test_earlier_citers(self):
        self.assertEqual(st.earlier_citers(self.YEARS, 2013), 9)
        self.assertEqual(st.earlier_citers(self.YEARS, None), 0)


class Lookup(unittest.TestCase):
    def test_only_exact_stub_records_kept_and_batched(self):
        stubs = ["10.1136/bmjopen", "10.1016/s0140", "10.1007/s00125"]
        filt = "doi:" + "|".join(stubs[:2])
        body = {"meta": {"count": 2}, "results": [
            {"id": "https://openalex.org/W4288364210", "doi": "https://doi.org/10.1136/bmjopen", "cited_by_count": 2230},
            {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1136/bmjopen-2016-012545"}]}
        f = fake_fetch({filt: body})
        recs, done = st.lookup(stubs, fetch=f, budget=st.Budget(10), batch=2)
        self.assertEqual([st.short_id(r["id"]) for r in recs], ["W4288364210"])
        self.assertFalse(done)  # the second batch had no canned answer
        self.assertEqual(len(f.asked), 2)

    def test_budget_refuses_past_cap(self):
        b = st.Budget(1)
        f = fake_fetch({})
        st.lookup(["10.1/aa", "10.1/bb"], fetch=f, budget=b, batch=1)
        self.assertEqual((b.calls, b.refused, b.failed), (1, 1, 1))


class Scoring(unittest.TestCase):
    def test_h1(self):
        v, new = st.score_h1(["10.1136/bmjopen", "10.1/a1", "10.1/a2", "10.1/a3", "10.1/a4"])
        self.assertEqual((v, len(new)), ("not supported", 4))
        v, new = st.score_h1(["10.1/a%d" % i for i in range(5)])
        self.assertEqual(v, "supported")

    def test_h2(self):
        reads = [{"kind": "dash", "status": "found", "wiley": True, "label": "cut_at_unicode_dash"}] * 9
        self.assertEqual(st.score_h2(reads)[0], "untestable")
        reads = reads + [{"kind": "dash", "status": "found", "wiley": True, "label": "intact_ascii"}]
        v, d = st.score_h2(reads + [{"kind": "paren", "status": "found", "wiley": True, "label": "absent"}])
        self.assertEqual((v, d["n"], d["k"]), ("supported", 10, 9))
        reads = reads + [{"kind": "dash", "status": "found", "wiley": True, "label": "absent"}] * 2
        self.assertEqual(st.score_h2(reads)[0], "not supported")

    def test_h3(self):
        rows = [{"kind": "dash", "citers": 2230, "wiley_share": 0.90},
                {"kind": "dash", "citers": 22520, "wiley_share": 0.18},
                {"kind": "dash", "citers": 712, "wiley_share": 0.37},
                {"kind": "dash", "citers": 19, "wiley_share": 0.0},
                {"kind": "paren", "citers": 11875, "wiley_share": 0.0}]
        v, d = st.score_h3(rows, 0.05)
        self.assertEqual((v, d["n"], d["above"]), ("supported", 3, 3))
        v, d = st.score_h3(rows, 0.10)
        self.assertEqual((v, d["above"]), ("not supported", 2))
        self.assertEqual(st.score_h3(rows, None)[0], "untestable")

    def test_wilson(self):
        p, lo, hi = st.wilson(9, 10)
        self.assertAlmostEqual(p, 0.9)
        self.assertTrue(0.55 < lo < 0.6 and 0.98 < hi <= 1.0)
        self.assertEqual(st.wilson(0, 0), (None, None, None))


if __name__ == "__main__":
    unittest.main()
