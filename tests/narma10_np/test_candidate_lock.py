import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as m
from benchmarks.narma10_np.candidate_lock import (
    BANNED_ENTRY_POINTS,
    BlindEvaluationBlocked,
    CandidateLockError,
    LOCK_SCHEMA,
    ReadoutContract,
    guard_blind_evaluation,
    load_lock,
    load_locked_scorer,
    verify_locked_sources,
)

from ._lockfix import BLIND, CandidateFixture, default_readout


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.fx = CandidateFixture(Path(self._tmp.name))

    def tearDown(self):
        self.fx.cleanup()
        self._tmp.cleanup()

    def guard(self):
        return guard_blind_evaluation(self.fx.lock_path, self.fx.blind_manifest,
                                      self.fx.ledger)


class GuardFailClosedTest(_Base):
    def test_no_lock_file_blocks(self):
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_draft_lock_blocks(self):
        self.fx.make_lock(locked=False)
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_happy_path_returns_ticket(self):
        lock = self.fx.make_lock()
        ticket = self.guard()
        self.assertEqual(ticket.candidate_id, "C001")
        self.assertEqual(ticket.blind_manifest_digest,
                         m.load_digest(self.fx.blind_manifest))
        self.assertEqual(ticket.lock_sha256, lock.content_sha256())

    def test_candidate_source_changed_blocks(self):
        self.fx.make_lock()
        self.fx.candidate_py.write_text("# tampered\n", encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_transitive_helper_changed_blocks(self):
        """A change in a file the candidate imports must also block."""
        self.fx.make_lock()
        self.fx.helper_py.write_text("SCALE = 2.0\n", encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked) as ctx:
            self.guard()
        self.assertIn("helper.py", str(ctx.exception))

    def test_source_added_after_lock_blocks(self):
        self.fx.make_lock()
        (self.fx.source_root / "sneaky.py").write_text("X = 1\n", encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked) as ctx:
            self.guard()
        self.assertIn("added after lock", str(ctx.exception))

    def test_source_removed_after_lock_blocks(self):
        self.fx.make_lock()
        self.fx.helper_py.unlink()
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_blind_manifest_digest_mismatch_blocks(self):
        self.fx.make_lock()
        other = config.SeedSpec(BLIND.namespace, 999, 3,
                                washout=10, train_len=30, test_len=15)
        m.write_manifest(other, self.fx.blind_manifest)
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_corrupt_blind_manifest_blocks(self):
        self.fx.make_lock()
        data = json.loads(self.fx.blind_manifest.read_text())
        data["entries"][0]["input_sha256"] = "0" * 64
        self.fx.blind_manifest.write_text(json.dumps(data))
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_malformed_lock_blocks(self):
        self.fx.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.fx.lock_path.write_text("{ not json")
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_missing_lock_fields_blocks(self):
        self.fx.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.fx.lock_path.write_text(json.dumps({"schema": LOCK_SCHEMA,
                                                 "candidate_id": "C001"}))
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()

    def test_v1_lock_is_rejected(self):
        """Inherited v1 locks froze a single file and named no scorer."""
        self.fx.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.fx.lock_path.write_text(json.dumps({
            "schema": "narma10-candidate-lock/1",
            "candidate_id": "C001",
            "description": "legacy",
            "created_utc": "2026-09-10T00:00:00Z",
            "code_path": str(self.fx.candidate_py),
            "code_sha256": "0" * 64,
            "dev_manifest_digest": "x",
            "blind_manifest_digest": "y",
            "locked": True,
        }), encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            self.guard()
        with self.assertRaises(CandidateLockError):
            load_lock(self.fx.lock_path)


class LockCreationTest(_Base):
    def test_refuses_when_manifest_broken(self):
        data = json.loads(self.fx.blind_manifest.read_text())
        data["entries"][0]["target_sha256"] = "0" * 64
        self.fx.blind_manifest.write_text(json.dumps(data))
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock()

    def test_refuses_when_source_root_missing(self):
        for p in sorted(self.fx.source_root.rglob("*")):
            p.unlink()
        self.fx.source_root.rmdir()
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock()

    def test_refuses_baseline_entry_point(self):
        banned = sorted(BANNED_ENTRY_POINTS)[0]
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock(entry_point=banned)

    def test_refuses_entry_point_without_attribute(self):
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock(entry_point="some.module")

    def test_lock_records_every_source_file(self):
        lock = self.fx.make_lock()
        names = {Path(p).name for p, _ in lock.sources}
        self.assertEqual(names, {"__init__.py", "scorer.py", "helper.py"})
        self.assertFalse(verify_locked_sources(lock))

    def test_roundtrip_and_content_digest_stable(self):
        lock = self.fx.make_lock()
        reloaded = load_lock(self.fx.lock_path)
        self.assertEqual(reloaded.content_sha256(), lock.content_sha256())
        self.assertEqual(reloaded.entry_point, lock.entry_point)


class ReadoutContractTest(unittest.TestCase):
    def test_feature_count_must_match(self):
        with self.assertRaises(CandidateLockError):
            ReadoutContract(20, 2, 41, "slot_end", 0, "train_inner_split").validate()

    def test_digital_taps_forbidden(self):
        with self.assertRaises(CandidateLockError):
            ReadoutContract(20, 2, 40, "slot_end", 3, "train_inner_split").validate()

    def test_unknown_ridge_selection_rejected(self):
        with self.assertRaises(CandidateLockError):
            ReadoutContract(20, 2, 40, "slot_end", 0, "test_set_sweep").validate()

    def test_fixed_alpha_requires_value(self):
        with self.assertRaises(CandidateLockError):
            ReadoutContract(20, 2, 40, "slot_end", 0, "fixed_locked_alpha").validate()
        ReadoutContract(20, 2, 40, "slot_end", 0, "fixed_locked_alpha", 1e-6).validate()

    def test_default_is_valid(self):
        default_readout().validate()


class LoadLockedScorerTest(_Base):
    def test_loads_and_runs_the_locked_scorer(self):
        lock = self.fx.make_lock()
        scorer = load_locked_scorer(lock)
        self.assertTrue(callable(scorer))

    def test_refuses_after_source_drift(self):
        lock = self.fx.make_lock()
        self.fx.helper_py.write_text("SCALE = 9.0\n", encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            load_locked_scorer(lock)

    def test_refuses_missing_attribute(self):
        lock = self.fx.make_lock(entry_point=f"{self.fx.pkg_name}.scorer:nope")
        with self.assertRaises(BlindEvaluationBlocked):
            load_locked_scorer(lock)

    def test_refuses_unimportable_module(self):
        lock = self.fx.make_lock(entry_point="no_such_module_xyz:build_scorer")
        with self.assertRaises(BlindEvaluationBlocked):
            load_locked_scorer(lock)

    def test_refuses_when_factory_returns_non_callable(self):
        self.fx.candidate_py.write_text("def build_scorer():\n    return 42\n",
                                        encoding="utf-8")
        lock = self.fx.make_lock()
        with self.assertRaises(BlindEvaluationBlocked):
            load_locked_scorer(lock)

    def test_refuses_alias_of_the_banned_baseline(self):
        """Re-exporting the baseline under another name must not smuggle it in."""
        self.fx.candidate_py.write_text(
            "from benchmarks.narma10_np.evaluate import baseline_delay_scorer "
            "as build_scorer\n",
            encoding="utf-8",
        )
        lock = self.fx.make_lock()
        with self.assertRaises(BlindEvaluationBlocked) as ctx:
            load_locked_scorer(lock)
        self.assertIn("baseline", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
