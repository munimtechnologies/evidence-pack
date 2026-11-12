# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Tests for kidney/slidepass.py (standard library only; a fake clock and fake tools, invented names, no KPMP data)."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from kidney import slidepass as sp


def items(n):
    return [{"slide": "SLIDE%d" % (i + 1), "package": "PKG%d" % (i + 1), "name": "FILE%d_v2.zip" % (i + 1)}
            for i in range(n)]


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Runner:
    """Fake fetch/kmask/emb: each call costs `cost` seconds, returns rcs[(slide, step)] (default 0; None = timed out)
    and writes the output file the real tool writes (nothing when timed out)."""

    def __init__(self, clock, cost=10.0, rcs=None, header=None):
        self.clock, self.cost, self.rcs, self.header = clock, cost, rcs or {}, header or {}
        self.calls = []

    def __call__(self, argv, cwd, timeout):
        step = "kmask" if "kidney.kmask" in argv else ("emb" if "kidney.emb" in argv else "fetch")
        tmp = os.path.dirname(argv[argv.index("--in-dir" if step == "emb" else "--wsi") + 1])
        with open(os.path.join(tmp, "one.json"), encoding="utf-8") as f:
            slide = json.load(f)[0]["slide"]
        self.calls.append((slide, step, timeout))
        self.clock.t += self.cost
        rc = self.rcs.get((slide, step), 0)
        if rc is None:
            return None
        if step == "fetch":
            doc = {slide: {"ok": rc == 0}}
        elif step == "kmask":
            doc = {slide: {"k_objects": {"glom": [], "gs": []}}} if rc == 0 else {}
        else:
            doc = {"code_version": "0.1.0", "gsdet": "0.2.0", "window": 288, "rows": [{"slide": slide, "ok": rc == 0}]}
            doc.update(self.header.get(slide, {}))
        with open(argv[argv.index("--out") + 1], "w", encoding="utf-8") as f:
            json.dump(doc, f)
        return rc


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.out = os.path.join(self.d, "out")
        self.tmp = os.path.join(self.d, "slidepass-t")
        self.clock = Clock()

    def cfg(self, **kw):
        c = {"tmp": self.tmp, "out_dir": self.out, "model": "M.pth", "fetch": "F.py", "repo": self.d, "python": "PY",
             "deadline_minutes": 600, "reserve": 0, "first_guess": 60}
        c.update(kw)
        return c

    def load(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as f:
            return json.load(f)


class TestChecks(Base):
    def test_good_list(self):
        self.assertEqual(sp.check_list(items(3)), [])

    def test_empty(self):
        self.assertEqual(sp.check_list([]), ["the list is empty or not a list"])
        self.assertEqual(sp.check_list({}), ["the list is empty or not a list"])

    def test_reused_name_and_package(self):
        a = items(3)
        a[1]["slide"] = "SLIDE1"
        self.assertEqual(sp.check_list(a), ["item 2 reuses a slide name"])
        b = items(3)
        b[2]["package"] = "PKG1"
        self.assertEqual(sp.check_list(b), ["item 3 repeats a package"])

    def test_unsafe_and_missing(self):
        self.assertEqual(sp.check_list([{"slide": "A/B", "package": "P", "name": "N"}]),
                         ["item 1 has an unsafe slide name"])
        self.assertEqual(sp.check_list([{"slide": "A,B", "package": "P", "name": "N"}]),
                         ["item 1 has an unsafe slide name"])
        self.assertEqual(sp.check_list([{"slide": "A", "package": "P"}, "X"]),
                         ["item 1 lacks slide, package or name", "item 2 lacks slide, package or name"])

    def test_tmp_ok(self):
        j = os.path.join
        self.assertTrue(sp.tmp_ok(j(self.d, "slidepass-1"), j(self.d, "out")))
        self.assertTrue(sp.tmp_ok(j(self.d, "slidepass-1"), j(self.d, "slidepass-10")))
        self.assertFalse(sp.tmp_ok(j(self.d, "tmp"), j(self.d, "out")))
        self.assertFalse(sp.tmp_ok(j(self.d, "slidepass-1"), j(self.d, "slidepass-1", "out")))
        self.assertFalse(sp.tmp_ok(j(self.d, "slidepass-1"), j(self.d, "slidepass-1")))


class TestTiming(unittest.TestCase):
    def test_first_guess(self):
        self.assertTrue(sp.should_start(0, 3600, [], reserve=900, first_guess=1800))
        self.assertFalse(sp.should_start(1000, 3600, [], reserve=900, first_guess=1800))

    def test_longest_slide_times_factor(self):
        self.assertTrue(sp.should_start(2100, 3600, [100, 400], reserve=900))
        self.assertFalse(sp.should_start(2101, 3600, [100, 400], reserve=900))

    def test_step_timeout(self):
        self.assertEqual(sp.step_timeout(100, 3600, 900), 2600)
        self.assertEqual(sp.step_timeout(3500, 3600, 900), 60.0)


class TestCommands(unittest.TestCase):
    def test_commands(self):
        j = os.path.join
        c = {"tmp": "T", "out_dir": "O", "model": "M.pth", "fetch": "F.py", "python": "PY", "threads": 3}
        cmds = sp.commands({"slide": "S1", "package": "P", "name": "N"}, c)
        self.assertEqual([s for s, _ in cmds], ["fetch", "kmask", "emb"])
        self.assertEqual(cmds[0][1], ["PY", "F.py", "--slides", j("T", "one.json"), "--wsi", j("T", "wsi"),
                                      "--masks", j("T", "masks"), "--out", j("O", "fetch", "S1.json")])
        self.assertEqual(cmds[1][1], ["PY", "-m", "kidney.kmask", "--masks", j("T", "masks"), "--wsi", j("T", "wsi"),
                                      "--out", j("O", "k", "S1.json"), "--diag", j("O", "kdiag", "S1.json"),
                                      "--only", "S1"])
        self.assertEqual(cmds[2][1], ["PY", "-m", "kidney.emb", "run", "--in-dir", j("T", "wsi"), "--model", "M.pth",
                                      "--out", j("O", "emb", "S1.json"), "--delete", "--threads", "3"])
        c["threads"] = 0
        self.assertEqual(sp.commands({"slide": "S1", "package": "P", "name": "N"}, c)[2][1][-1], "--delete")


class TestPass(Base):
    def test_all_ok(self):
        run = Runner(self.clock)
        recs, stopped = sp.run_pass(items(3), self.cfg(), runner=run, clock=self.clock)
        self.assertIsNone(stopped)
        self.assertEqual([r["status"] for r in recs], ["ok", "ok", "ok"])
        self.assertEqual([r["seconds"] for r in recs], [30.0, 30.0, 30.0])
        self.assertEqual(recs[0]["rc"], {"fetch": 0, "kmask": 0, "emb": 0})
        self.assertEqual([(s, st) for s, st, _ in run.calls[:4]],
                         [("SLIDE1", "fetch"), ("SLIDE1", "kmask"), ("SLIDE1", "emb"), ("SLIDE2", "fetch")])
        self.assertEqual(run.calls[0][2], 36000.0)
        self.assertEqual(run.calls[1][2], 35990.0)
        self.assertFalse(os.path.exists(self.tmp))
        res = sp.merge_outputs(recs, self.out)
        self.assertEqual(res, {"emb": {"documents": 3, "rows_read": 3, "slides": 3, "slides_ok": 3},
                               "k": {"slides": 3, "conflicts": 0}})
        self.assertEqual([r["slide"] for r in self.load("emb.json")["rows"]], ["SLIDE1", "SLIDE2", "SLIDE3"])
        self.assertEqual(list(self.load("k.json")), ["SLIDE1", "SLIDE2", "SLIDE3"])
        self.assertEqual(sp.undone(items(3), recs), [])

    def test_fetch_failure_skips_later_steps(self):
        run = Runner(self.clock, rcs={("SLIDE2", "fetch"): 1})
        recs, stopped = sp.run_pass(items(3), self.cfg(), runner=run, clock=self.clock)
        self.assertIsNone(stopped)
        self.assertEqual([r["status"] for r in recs], ["ok", "fetch_failed", "ok"])
        self.assertEqual(recs[1]["rc"], {"fetch": 1})
        self.assertEqual([r["seconds"] for r in recs], [30.0, 10.0, 30.0])
        self.assertEqual(sp.undone(items(3), recs), [items(3)[1]])
        res = sp.merge_outputs(recs, self.out)
        self.assertEqual(res["emb"]["slides"], 2)
        self.assertEqual(res["k"], {"slides": 2, "conflicts": 0})

    def test_emb_failure_keeps_its_row(self):
        run = Runner(self.clock, rcs={("SLIDE1", "emb"): 1})
        recs, _ = sp.run_pass(items(2), self.cfg(), runner=run, clock=self.clock)
        self.assertEqual([r["status"] for r in recs], ["emb_failed", "ok"])
        res = sp.merge_outputs(recs, self.out)
        self.assertEqual(res["emb"], {"documents": 2, "rows_read": 2, "slides": 2, "slides_ok": 1})

    def test_deadline(self):
        run = Runner(self.clock, cost=100.0)
        recs, stopped = sp.run_pass(items(5), self.cfg(deadline_minutes=20, first_guess=300), runner=run,
                                    clock=self.clock)
        self.assertEqual(stopped, "deadline")
        self.assertEqual([r["status"] for r in recs], ["ok", "ok", "ok", "not_started", "not_started"])
        self.assertEqual([r["seconds"] for r in recs], [300.0, 300.0, 300.0, None, None])
        self.assertEqual(run.calls[0][2], 1200.0)
        self.assertEqual(run.calls[8][2], 400.0)
        self.assertEqual(len(run.calls), 9)

    def test_timeout_stops(self):
        run = Runner(self.clock, rcs={("SLIDE1", "emb"): None})
        recs, stopped = sp.run_pass(items(3), self.cfg(), runner=run, clock=self.clock)
        self.assertEqual(stopped, "timeout")
        self.assertEqual([r["status"] for r in recs], ["timeout", "not_started", "not_started"])
        self.assertEqual(recs[0]["rc"], {"fetch": 0, "kmask": 0, "emb": None})
        self.assertFalse(os.path.exists(self.tmp))

    def test_fail_streak(self):
        run = Runner(self.clock, rcs={("SLIDE%d" % i, "fetch"): 1 for i in range(1, 6)})
        recs, stopped = sp.run_pass(items(5), self.cfg(), runner=run, clock=self.clock)
        self.assertEqual(stopped, "fail_streak")
        self.assertEqual([r["status"] for r in recs], ["fetch_failed"] * 3 + ["not_started"] * 2)

    def test_streak_resets_on_success(self):
        rcs = {("SLIDE1", "fetch"): 1, ("SLIDE2", "fetch"): 1, ("SLIDE4", "fetch"): 1, ("SLIDE5", "fetch"): 1}
        recs, stopped = sp.run_pass(items(5), self.cfg(), runner=Runner(self.clock, rcs=rcs), clock=self.clock)
        self.assertIsNone(stopped)
        self.assertEqual([r["status"] for r in recs],
                         ["fetch_failed", "fetch_failed", "ok", "fetch_failed", "fetch_failed"])

    def test_mixed_model_settings_refused(self):
        run = Runner(self.clock, header={"SLIDE2": {"window": 256}})
        recs, _ = sp.run_pass(items(2), self.cfg(), runner=run, clock=self.clock)
        res = sp.merge_outputs(recs, self.out)
        self.assertIn("emb_error", res)
        self.assertNotIn("emb", res)
        self.assertFalse(os.path.exists(os.path.join(self.out, "emb.json")))

    def test_save_after_every_slide(self):
        seen = []
        sp.run_pass(items(3), self.cfg(), runner=Runner(self.clock), clock=self.clock,
                    save=lambda recs, stopped: seen.append(len(recs)))
        self.assertEqual(seen, [1, 2, 3])


class TestSummary(unittest.TestCase):
    def test_summary(self):
        recs = [{"slide": "A", "status": "ok", "rc": {}, "seconds": 60.0},
                {"slide": "B", "status": "fetch_failed", "rc": {}, "seconds": 120.0},
                {"slide": "C", "status": "not_started", "rc": {}, "seconds": None}]
        self.assertEqual(sp.summary(recs, "deadline"),
                         {"code_version": sp.CODE_VERSION, "slides": 3,
                          "by_status": {"fetch_failed": 1, "not_started": 1, "ok": 1}, "stopped": "deadline",
                          "minutes": 3.0, "max_slide_minutes": 2.0, "mean_slide_minutes": 1.5})

    def test_empty(self):
        s = sp.summary([], None)
        self.assertEqual((s["slides"], s["by_status"], s["minutes"], s["max_slide_minutes"]), (0, {}, 0.0, None))


class TestMain(Base):
    def write_list(self, lst):
        p = os.path.join(self.d, "list.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(lst, f)
        return p

    def args(self, lst, tmp=None):
        return ["run", "--list", self.write_list(lst), "--model", "M.pth", "--fetch", "F.py",
                "--tmp", tmp or self.tmp, "--out-dir", self.out, "--deadline-minutes", "600",
                "--reserve-minutes", "0", "--first-guess-minutes", "1"]

    def test_ok_run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sp.main(self.args(items(2)), runner=Runner(self.clock), clock=self.clock)
        self.assertEqual(rc, 0)
        self.assertNotIn("SLIDE", buf.getvalue())
        rep = json.loads(buf.getvalue().strip().splitlines()[-1])
        self.assertEqual((rep["by_status"], rep["undone"], rep["minutes"]), ({"ok": 2}, 0, 1.0))
        self.assertEqual(self.load("progress.json")["summary"]["by_status"], {"ok": 2})
        self.assertEqual(self.load("undone.json"), [])
        self.assertEqual(len(self.load("emb.json")["rows"]), 2)

    def test_failed_slide_exits_1(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = sp.main(self.args(items(2)), runner=Runner(self.clock, rcs={("SLIDE2", "kmask"): 1}),
                         clock=self.clock)
        self.assertEqual(rc, 1)
        self.assertEqual(self.load("undone.json"), [items(2)[1]])

    def test_bad_inputs_exit_2(self):
        bad = items(2)
        bad[1]["slide"] = "SLIDE1"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sp.main(self.args(bad), runner=Runner(self.clock), clock=self.clock), 2)
            self.assertEqual(sp.main(self.args(items(1), tmp=os.path.join(self.d, "scratch")),
                                     runner=Runner(self.clock), clock=self.clock), 2)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
