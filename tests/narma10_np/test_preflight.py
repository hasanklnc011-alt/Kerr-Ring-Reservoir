import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np import cli
from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as m
from benchmarks.narma10_np import preflight
from benchmarks.narma10_np.candidate_lock import create_lock

CHECK_NAMES = (
    "environment.provenance",
    "manifest.dev",
    "manifest.blind",
    "manifest.digests_distinct",
    "seeds.dev",
    "seeds.blind",
    "candidate_lock",
    "blind_evaluation.blocked",
)


class RepoPreflightTest(unittest.TestCase):
    """The preflight must be green against the benchmark as committed."""

    @classmethod
    def setUpClass(cls):
        cls.report = preflight.run_preflight()
        cls.by_name = {c.name: c for c in cls.report.checks}

    def test_all_expected_checks_present_in_order(self):
        self.assertEqual(tuple(c.name for c in self.report.checks), CHECK_NAMES)

    def test_overall_ok_and_no_failures(self):
        self.assertTrue(self.report.ok, self.report.format_text())
        self.assertEqual(self.report.failed, [])

    def test_provenance_is_info_and_reports_numpy(self):
        c = self.by_name["environment.provenance"]
        self.assertEqual(c.status, preflight.STATUS_INFO)
        import numpy as np
        self.assertIn(np.__version__, " ".join(c.details))

    def test_manifest_checks_pass_with_matching_digests(self):
        for label, spec in (("dev", config.dev_spec()), ("blind", config.blind_spec())):
            c = self.by_name[f"manifest.{label}"]
            self.assertEqual(c.status, preflight.STATUS_PASS, c.details)
            committed = m.load_digest(m.default_path(spec))
            joined = " ".join(c.details)
            self.assertIn(f"committed_digest = {committed}", joined)
            self.assertIn(f"recomputed_digest = {committed}", joined)

    def test_seed_blocks_have_expected_finite_counts(self):
        self.assertEqual(self.by_name["seeds.dev"].status, preflight.STATUS_PASS)
        self.assertEqual(self.by_name["seeds.blind"].status, preflight.STATUS_PASS)
        self.assertIn(f"generated_trials = {config.N_DEV_SEEDS}",
                      " ".join(self.by_name["seeds.dev"].details))
        self.assertIn(f"finite_trials = {config.N_BLIND_SEEDS}",
                      " ".join(self.by_name["seeds.blind"].details))

    def test_candidate_lock_absent(self):
        c = self.by_name["candidate_lock"]
        self.assertEqual(c.status, preflight.STATUS_INFO)
        self.assertIn("absent", c.summary)

    def test_blind_evaluation_reported_blocked(self):
        c = self.by_name["blind_evaluation.blocked"]
        self.assertEqual(c.status, preflight.STATUS_PASS)
        self.assertIn("blocked", c.summary)

    def test_report_is_deterministic(self):
        self.assertEqual(preflight.run_preflight().to_dict(),
                         preflight.run_preflight().to_dict())

    def test_to_dict_shape(self):
        d = self.report.to_dict()
        self.assertEqual(d["n_checks"], len(CHECK_NAMES))
        self.assertEqual(d["n_failed"], 0)
        self.assertTrue(d["ok"])
        self.assertEqual({c["name"] for c in d["checks"]}, set(CHECK_NAMES))


class _LockFixture:
    """A synthetic candidate lock in a throwaway dir, built against the real
    committed manifests (mirrors tests/narma10_np/test_candidate_lock.py)."""

    def __init__(self, root: Path, *, locked: bool = True):
        self.lock_dir = root / "candidates"
        self.ledger = root / "ledger.json"
        self.code = root / "candidate.py"
        self.code.write_text("# synthetic candidate\nRESERVOIR = 'vX'\n", encoding="utf-8")
        create_lock(
            candidate_id="C999",
            description="synthetic preflight fixture",
            code_path=self.code,
            dev_manifest_path=m.default_path(config.dev_spec()),
            blind_manifest_path=m.default_path(config.blind_spec()),
            lock_path=self.lock_dir / "C999.lock.json",
            locked=locked,
        )


class PreflightWithLockTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, **kw):
        fx_dir = self.root / "candidates"
        return preflight.run_preflight(
            lock_dir=fx_dir, ledger_path=self.root / "ledger.json", **kw
        ), fx_dir

    def test_unblocked_lock_fails_preflight_by_default(self):
        _LockFixture(self.root, locked=True)
        report, _ = self._run()
        c = {x.name: x for x in report.checks}["blind_evaluation.blocked"]
        self.assertEqual(c.status, preflight.STATUS_FAIL)
        self.assertFalse(report.ok)

    def test_unblocked_lock_is_info_when_allowed(self):
        _LockFixture(self.root, locked=True)
        report, _ = self._run(strict_blind=False)
        c = {x.name: x for x in report.checks}["blind_evaluation.blocked"]
        self.assertEqual(c.status, preflight.STATUS_INFO)
        self.assertTrue(report.ok)

    def test_draft_lock_keeps_blind_blocked(self):
        _LockFixture(self.root, locked=False)
        report, _ = self._run()
        checks = {x.name: x for x in report.checks}
        self.assertEqual(checks["candidate_lock"].status, preflight.STATUS_INFO)
        self.assertIn("1 candidate lock", checks["candidate_lock"].summary)
        self.assertEqual(checks["blind_evaluation.blocked"].status, preflight.STATUS_PASS)
        self.assertTrue(report.ok)

    def test_malformed_lock_keeps_blind_blocked(self):
        lock_dir = self.root / "candidates"
        lock_dir.mkdir(parents=True)
        (lock_dir / "bad.lock.json").write_text("{ not json", encoding="utf-8")
        report, _ = self._run()
        checks = {x.name: x for x in report.checks}
        self.assertEqual(checks["blind_evaluation.blocked"].status, preflight.STATUS_PASS)
        self.assertTrue(report.ok)


class PreflightCliTest(unittest.TestCase):
    def _capture(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def test_cli_text_ok(self):
        code, out = self._capture(["preflight"])
        self.assertEqual(code, 0)
        self.assertIn("PREFLIGHT OK", out)

    def test_cli_json_ok_and_parseable(self):
        code, out = self._capture(["preflight", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["n_checks"], len(CHECK_NAMES))

    def test_cli_parser_registers_preflight(self):
        args = cli.build_parser().parse_args(["preflight"])
        self.assertIs(args.func, cli.cmd_preflight)
        self.assertFalse(args.allow_blind_unblocked)


if __name__ == "__main__":
    unittest.main()
