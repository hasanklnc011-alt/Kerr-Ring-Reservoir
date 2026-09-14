"""G0: the blind path consumes its attempt before scoring, runs only the
locked scorer, refuses concurrent runs and recovers only the identical run."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np import blind_ledger, blind_run, config
from benchmarks.narma10_np.blind_ledger import (
    ProcessLock,
    STATUS_COMPLETED,
    STATUS_RESERVED,
    process_lock_path,
)
from benchmarks.narma10_np.candidate_lock import (
    BlindEvaluationBlocked,
    guard_blind_evaluation,
)

from ._lockfix import CandidateFixture


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.fx = CandidateFixture(Path(self._tmp.name), use_real_manifests=True)
        self.fx.make_lock()

    def tearDown(self):
        self.fx.cleanup()
        self._tmp.cleanup()

    def ticket(self):
        return guard_blind_evaluation(self.fx.lock_path, self.fx.blind_manifest,
                                      self.fx.ledger)

    def run_blind(self, **kw):
        return blind_run.run_blind_evaluation(
            self.fx.lock_path, self.fx.blind_manifest, self.fx.ledger, **kw
        )

    def ledger_entries(self):
        return blind_ledger.read_ledger(self.fx.ledger)["entries"]


class ReservationOrderTest(_Base):
    def test_attempt_is_consumed_before_scoring(self):
        """A scorer that blows up must still have consumed the attempt."""
        self.fx.candidate_py.write_text(
            "def build_scorer():\n"
            "    def _score(trial):\n"
            "        raise RuntimeError('boom')\n"
            "    return _score\n",
            encoding="utf-8",
        )
        self.fx.make_lock()

        with self.assertRaises(RuntimeError):
            self.run_blind()

        entries = self.ledger_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], STATUS_RESERVED)
        self.assertEqual(entries[0]["candidate_id"], "C001")

        # And the consumed attempt cannot be restarted from scratch.
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind()

    def test_reserve_then_complete(self):
        ticket = self.ticket()
        reservation = blind_ledger.reserve_attempt(ticket)
        self.assertEqual(self.ledger_entries()[0]["status"], STATUS_RESERVED)

        entry = blind_ledger.complete_attempt(reservation, {"median_test_nmse": 0.9})
        self.assertEqual(entry["status"], STATUS_COMPLETED)
        self.assertEqual(self.ledger_entries()[0]["status"], STATUS_COMPLETED)

    def test_second_reservation_blocks(self):
        ticket = self.ticket()
        blind_ledger.reserve_attempt(ticket)
        with self.assertRaises(BlindEvaluationBlocked):
            blind_ledger.reserve_attempt(ticket)

    def test_completing_twice_blocks(self):
        reservation = blind_ledger.reserve_attempt(self.ticket())
        blind_ledger.complete_attempt(reservation, {"median_test_nmse": 0.9})
        with self.assertRaises(BlindEvaluationBlocked):
            blind_ledger.complete_attempt(reservation, {"median_test_nmse": 0.4})

    def test_completing_without_reservation_blocks(self):
        reservation = blind_ledger.Reservation(
            candidate_id="C001", run_id="deadbeef", lock_sha256="x",
            blind_manifest_digest="y", ledger_path=str(self.fx.ledger),
            checkpoint_path=str(self.fx.ledger) + ".cp",
        )
        with self.assertRaises(BlindEvaluationBlocked):
            blind_ledger.complete_attempt(reservation, {"median_test_nmse": 0.1})

    def test_foreign_run_id_cannot_record(self):
        real = blind_ledger.reserve_attempt(self.ticket())
        impostor = blind_ledger.Reservation(
            candidate_id=real.candidate_id, run_id="not-the-same-run",
            lock_sha256=real.lock_sha256,
            blind_manifest_digest=real.blind_manifest_digest,
            ledger_path=real.ledger_path, checkpoint_path=real.checkpoint_path,
        )
        with self.assertRaises(BlindEvaluationBlocked):
            blind_ledger.complete_attempt(impostor, {"median_test_nmse": 0.0})


class SuiteIsSingleUseTest(_Base):
    def test_different_candidate_id_cannot_reopen(self):
        entry = self.run_blind()
        self.assertEqual(entry["status"], STATUS_COMPLETED)

        # Freeze a second candidate against the same blind manifest.
        second_lock = self.fx.root / "candidates" / "C002.lock.json"
        from benchmarks.narma10_np.candidate_lock import create_lock
        from ._lockfix import default_readout
        create_lock(
            candidate_id="C002", description="second candidate",
            entry_point=self.fx.entry_point, source_root=self.fx.source_root,
            readout=default_readout(), dev_manifest_path=self.fx.dev_manifest,
            blind_manifest_path=self.fx.blind_manifest, lock_path=second_lock,
        )
        with self.assertRaises(BlindEvaluationBlocked) as ctx:
            blind_run.run_blind_evaluation(second_lock, self.fx.blind_manifest,
                                           self.fx.ledger)
        self.assertIn("already been consumed", str(ctx.exception))

    def test_same_candidate_cannot_run_twice(self):
        self.run_blind()
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind()


class ScorerIdentityTest(_Base):
    def test_runs_the_locked_scorer_not_the_baseline(self):
        """The baseline and the locked candidate must not agree by accident."""
        from benchmarks.narma10_np.evaluate import baseline_delay_scorer, score_spec

        entry = self.run_blind()
        locked_scores = entry["summary"]["per_seed"]

        baseline = score_spec(config.blind_spec(), baseline_delay_scorer())
        baseline_scores = {str(s.index): s.test_nmse for s in baseline.scores}

        self.assertEqual(set(locked_scores), set(baseline_scores))
        self.assertNotEqual(locked_scores, baseline_scores)

    def test_ledger_entry_records_the_full_summary(self):
        entry = self.run_blind()
        self.assertEqual(entry["candidate_id"], "C001")
        self.assertEqual(entry["summary"]["n_seeds"], config.N_BLIND_SEEDS)
        self.assertIn("median_test_nmse", entry["summary"])
        self.assertIn("meets_acceptance", entry["summary"])


class ConcurrencyTest(_Base):
    def test_process_lock_refuses_a_second_holder(self):
        path = process_lock_path(self.fx.ledger)
        with ProcessLock(path):
            with self.assertRaises(BlindEvaluationBlocked):
                with ProcessLock(path):
                    pass  # pragma: no cover - must not be reached

    def test_process_lock_is_released(self):
        path = process_lock_path(self.fx.ledger)
        with ProcessLock(path):
            self.assertTrue(path.exists())
        self.assertFalse(path.exists())

    def test_blind_run_refuses_while_lock_is_held(self):
        with ProcessLock(process_lock_path(self.fx.ledger)):
            with self.assertRaises(BlindEvaluationBlocked) as ctx:
                self.run_blind()
        self.assertIn("concurrently", str(ctx.exception))
        self.assertEqual(self.ledger_entries(), [])


class RecoveryTest(_Base):
    def _crash_midway(self):
        """Reserve an attempt and checkpoint two seeds, then 'crash'."""
        reservation = blind_ledger.reserve_attempt(self.ticket())
        blind_ledger.write_checkpoint(reservation, {0: 0.11, 1: 0.22})
        return reservation

    def test_resume_completes_the_same_run(self):
        reservation = self._crash_midway()
        entry = self.run_blind(resume_run_id=reservation.run_id)
        self.assertEqual(entry["status"], STATUS_COMPLETED)
        self.assertEqual(entry["run_id"], reservation.run_id)
        self.assertEqual(entry["summary"]["n_seeds"], config.N_BLIND_SEEDS)
        # Checkpointed seeds are kept, not rescored.
        self.assertAlmostEqual(entry["summary"]["per_seed"]["0"], 0.11)

    def test_resume_with_wrong_run_id_blocks(self):
        self._crash_midway()
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind(resume_run_id="0" * 32)

    def test_resume_after_lock_change_blocks(self):
        reservation = self._crash_midway()
        self.fx.helper_py.write_text("SCALE = 3.0\n", encoding="utf-8")
        self.fx.make_lock()  # relock: different content digest
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind(resume_run_id=reservation.run_id)

    def test_resume_with_foreign_checkpoint_blocks(self):
        reservation = self._crash_midway()
        path = Path(reservation.checkpoint_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["run_id"] = "9" * 32
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind(resume_run_id=reservation.run_id)

    def test_resume_without_reservation_blocks(self):
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind(resume_run_id="1" * 32)

    def test_resume_after_completion_blocks(self):
        entry = self.run_blind()
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind(resume_run_id=entry["run_id"])

    def test_checkpoint_is_discarded_after_completion(self):
        reservation = self._crash_midway()
        self.run_blind(resume_run_id=reservation.run_id)
        self.assertFalse(Path(reservation.checkpoint_path).exists())


class LedgerIntegrityTest(_Base):
    def test_unknown_ledger_schema_blocks(self):
        self.fx.ledger.write_text(json.dumps({"schema": "narma10-blind-ledger/1",
                                              "entries": []}), encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            blind_ledger.read_ledger(self.fx.ledger)

    def test_corrupt_ledger_blocks(self):
        self.fx.ledger.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(BlindEvaluationBlocked):
            self.run_blind()

    def test_ledger_write_is_atomic_replace(self):
        """No partial ledger is ever visible: writes go through os.replace."""
        reservation = blind_ledger.reserve_attempt(self.ticket())
        leftovers = list(self.fx.ledger.parent.glob(self.fx.ledger.name + ".tmp.*"))
        self.assertEqual(leftovers, [])
        self.assertEqual(blind_ledger.read_ledger(self.fx.ledger)["entries"][0]["run_id"],
                         reservation.run_id)


if __name__ == "__main__":
    unittest.main()
