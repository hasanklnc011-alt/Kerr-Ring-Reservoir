import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as m
from benchmarks.narma10_np.candidate_lock import (
    BlindEvaluationBlocked,
    CandidateLockError,
    create_lock,
    guard_blind_evaluation,
    ledger_has_candidate,
    record_blind_result,
)

DEV = config.SeedSpec("narma10/lock-dev", 11, 2, washout=10, train_len=30, test_len=15)
BLIND = config.SeedSpec("narma10/lock-blind", 22, 3, washout=10, train_len=30, test_len=15)


class _Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.dev_manifest = root / "dev.json"
        self.blind_manifest = root / "blind.json"
        self.code = root / "candidate.py"
        self.lock = root / "cand" / "C001.lock.json"
        self.ledger = root / "ledger.json"
        m.write_manifest(DEV, self.dev_manifest)
        m.write_manifest(BLIND, self.blind_manifest)
        self.code.write_text("# candidate architecture spec\nRESERVOIR = 'v1'\n")

    def make_lock(self, *, locked=True):
        return create_lock(
            candidate_id="C001", description="unit-test candidate",
            code_path=self.code, dev_manifest_path=self.dev_manifest,
            blind_manifest_path=self.blind_manifest, lock_path=self.lock,
            locked=locked,
        )

    def guard(self):
        return guard_blind_evaluation(self.lock, self.blind_manifest, self.ledger)


class GuardFailClosedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.fx = _Fixture(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_lock_file_blocks(self):
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_draft_lock_blocks(self):
        self.fx.make_lock(locked=False)
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_happy_path_returns_ticket(self):
        self.fx.make_lock()
        ticket = self.fx.guard()
        self.assertEqual(ticket.candidate_id, "C001")
        self.assertEqual(ticket.blind_manifest_digest,
                         m.load_digest(self.fx.blind_manifest))

    def test_second_evaluation_blocks(self):
        self.fx.make_lock()
        ticket = self.fx.guard()
        record_blind_result(ticket, {"median_test_nmse": 0.9})
        self.assertTrue(ledger_has_candidate(self.fx.ledger, "C001"))
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_record_twice_blocks(self):
        self.fx.make_lock()
        ticket = self.fx.guard()
        record_blind_result(ticket, {"median_test_nmse": 0.9})
        with self.assertRaises(BlindEvaluationBlocked):
            record_blind_result(ticket, {"median_test_nmse": 0.4})

    def test_code_changed_after_lock_blocks(self):
        self.fx.make_lock()
        self.fx.code.write_text("# tampered after lock\nRESERVOIR = 'v2'\n")
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_blind_manifest_digest_mismatch_blocks(self):
        self.fx.make_lock()
        # Rewrite the blind manifest with a different (still self-consistent) spec.
        other = config.SeedSpec(BLIND.namespace, 999, 3,
                                washout=10, train_len=30, test_len=15)
        m.write_manifest(other, self.fx.blind_manifest)
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_corrupt_blind_manifest_blocks(self):
        self.fx.make_lock()
        data = json.loads(self.fx.blind_manifest.read_text())
        data["entries"][0]["input_sha256"] = "0" * 64
        self.fx.blind_manifest.write_text(json.dumps(data))
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_malformed_lock_blocks(self):
        self.fx.lock.parent.mkdir(parents=True, exist_ok=True)
        self.fx.lock.write_text("{ not json")
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()

    def test_missing_lock_fields_blocks(self):
        self.fx.lock.parent.mkdir(parents=True, exist_ok=True)
        self.fx.lock.write_text(json.dumps({"candidate_id": "C001"}))
        with self.assertRaises(BlindEvaluationBlocked):
            self.fx.guard()


class CreateLockGuardsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.fx = _Fixture(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_refuses_when_manifest_broken(self):
        data = json.loads(self.fx.blind_manifest.read_text())
        data["entries"][0]["target_sha256"] = "0" * 64
        self.fx.blind_manifest.write_text(json.dumps(data))
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock()

    def test_refuses_when_artifact_missing(self):
        self.fx.code.unlink()
        with self.assertRaises(CandidateLockError):
            self.fx.make_lock()


if __name__ == "__main__":
    unittest.main()
