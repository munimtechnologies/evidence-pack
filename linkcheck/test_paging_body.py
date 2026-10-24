"""Tests for LinkCheck 0.3.1's page-body counts, error messages and refetch rule, on made-up
page bodies only (no network).

Every expected number below was worked out by hand from the bodies in this file before the
tests were first run.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
import unittest

from linkcheck import paging


def server_error(message):
    return {"errors": [{"kind": "NotFound", "method": "GET", "route": "/subject-mapping",
                        "message": message}]}


# One page of a side-by-side endpoint: A serves 3, B is an error object, C is past its end.
BODY = [{"source": "A", "data": [1, 2, 3]},
        {"source": "B", "errors": [{"kind": "NotFound", "message": "no page 4"}]},
        {"source": "C", "data": []}]


def flag(page, source, kind, entries, want):
    return {"page": page, "source": source, "kind": kind, "entries": entries, "expected": want}


class BodyCounts(unittest.TestCase):
    def test_list_body(self):
        self.assertEqual(paging.body_counts(BODY), {"A": 3, "B": None, "C": 0})

    def test_other_keys(self):
        body = [{"node": "X", "rows": [0, 0]}, {"node": "Y"}]
        self.assertEqual(paging.body_counts(body, source_key="node", data_key="rows"),
                         {"X": 2, "Y": None})

    def test_whole_page_error(self):
        self.assertIsNone(paging.body_counts(server_error("Server Error.")))
        self.assertIsNone(paging.body_counts({"errors": []}))

    def test_bad_bodies(self):
        for body in ("text", None, {"data": []}, {"errors": "x"}, [{"data": []}], ["A"],
                     [{"source": "A", "data": []}, {"source": "A", "data": [1]}]):
            with self.assertRaises(ValueError):
                paging.body_counts(body)


class ErrorMessages(unittest.TestCase):
    def test_messages(self):
        self.assertEqual(paging.error_messages(server_error("Server Error.")),
                         ["NotFound: Server Error."])
        self.assertEqual(paging.error_messages(BODY), ["NotFound: no page 4"])
        self.assertEqual(paging.error_messages([{"source": "A", "errors": ["boom"]}]), ["boom"])
        self.assertEqual(paging.error_messages([{"source": "A", "data": []}]), [])
        self.assertEqual(paging.error_messages("text"), [])


class LastPage(unittest.TestCase):
    def test_last_page(self):
        self.assertEqual(paging.last_page({"A": 25, "B": 12}, 10), 3)
        self.assertEqual(paging.last_page({"A": 100}, 100), 1)
        self.assertEqual(paging.last_page({"A": 101}, 100), 2)
        self.assertEqual(paging.last_page({"A": None, "B": 5}, 10), 1)
        self.assertEqual(paging.last_page({"A": 0}, 10), 0)
        self.assertEqual(paging.last_page({}, 10), 0)

    def test_bad_input(self):
        for args in (({"A": 5}, 0), ({"A": -1}, 10), ({"A": True}, 10)):
            with self.assertRaises(ValueError):
                paging.last_page(*args)


class Refetch(unittest.TestCase):
    def test_empty_page_is_not_the_end(self):
        # The walk stopped after page 2 came back with no entries; the totals need page 4.
        pages = {1: {"A": 10, "B": 10}, 2: {}}
        self.assertEqual(paging.refetch_pages(pages, 10, {"A": 35, "B": 12}), [2, 3, 4])
        report = paging.audit(pages, 10, {"A": 35, "B": 12})
        self.assertEqual((report["last_page"], report["missing_pages"],
                          report["required_last_page"], report["refetch_pages"]),
                         (2, [], 4, [2, 3, 4]))
        a, b = report["sources"]["A"], report["sources"]["B"]
        self.assertEqual((a["short_pages"], a["lost"]["pages_not_walked"], a["unexplained"]),
                         ([[2, 10]], 15, 0))
        self.assertEqual((b["short_pages"], b["lost"]["pages_not_walked"], b["unexplained"]),
                         ([[2, 2]], 0, 0))

    def test_failed_and_all_error_pages(self):
        pages = {1: {"A": 10, "B": 10}, 2: None, 3: {"A": 10, "B": None},
                 4: {"A": 5, "B": None}, 5: {"A": 0, "B": None}}
        self.assertEqual(paging.refetch_pages(pages, 10, {"A": 35, "B": 12}), [2])
        self.assertEqual(paging.refetch_pages({1: {"A": None, "B": None}}, 10, {"A": 5}), [1])

    def test_gaps(self):
        report = paging.audit({1: {"E": 12}, 2: None, 4: {"E": 10}}, 10, {"E": 50})
        self.assertEqual((report["required_last_page"], report["refetch_pages"]),
                         (5, [2, 3, 5]))

    def test_without_totals(self):
        report = paging.audit({1: {"A": 3}}, 10)
        self.assertEqual((report["required_last_page"], report["refetch_pages"]), (None, []))


class FromBodies(unittest.TestCase):
    def test_bodies_to_audit(self):
        bodies = {1: [{"source": "A", "data": [0] * 10}, {"source": "B", "data": [0] * 10}],
                  2: [{"source": "A", "errors": [{"kind": "X", "message": "y"}]},
                      {"source": "B", "data": [0] * 2}],
                  3: server_error("Participants IDs are not found.")}
        pages = {n: paging.body_counts(b) for n, b in bodies.items()}
        self.assertEqual(pages, {1: {"A": 10, "B": 10}, 2: {"A": None, "B": 2}, 3: None})
        report = paging.audit(pages, 10, {"A": 15, "B": 12})
        self.assertEqual(report["flags"], [flag(2, "A", "error", None, 5)])
        self.assertEqual(report["whole_page_failures"], [3])
        self.assertEqual((report["required_last_page"], report["refetch_pages"]), (2, []))
        a, b = report["sources"]["A"], report["sources"]["B"]
        self.assertEqual((a["served"], a["lost"]["error_pages"], a["errors_past_end"],
                          a["unexplained"]), (10, 5, 1, 0))
        self.assertEqual((b["served"], b["errors_past_end"], b["unexplained"]), (12, 1, 0))


if __name__ == "__main__":
    unittest.main()
