"""The one blind evaluation path.

Order of operations is the contract (G0):

1. ``guard_blind_evaluation`` — read-only preconditions.
2. exclusive process lock — no two concurrent attempts.
3. ``reserve_attempt`` / ``resume_attempt`` — the attempt is consumed
   **before** any blind trial is generated or scored.
4. the *locked* scorer is imported from the frozen package and run; progress is
   checkpointed after every seed.
5. ``complete_attempt`` — the reserved entry becomes the recorded result.

The baseline scorer is banned here by construction: the only scorer that can
run is the one named by the lock's ``entry_point``, and
:data:`candidate_lock.BANNED_ENTRY_POINTS` rejects the baseline at lock time,
at guard time and again at import time.
"""

from __future__ import annotations

from pathlib import Path

from . import config
from . import blind_ledger
from .blind_ledger import ProcessLock, Reservation, process_lock_path
from .candidate_lock import (
    BlindEvaluationBlocked,
    BlindEvaluationTicket,
    guard_blind_evaluation,
    load_lock,
    load_locked_scorer,
)
from .dataset import build_all
from .evaluate import SpecScore, TrialScore


def score_blind_with_checkpoint(reservation: Reservation, scorer) -> SpecScore:
    """Score every blind seed, checkpointing after each one."""
    spec = config.blind_spec()
    done = blind_ledger.read_checkpoint(reservation)
    scores = dict(done)

    for trial in build_all(spec):
        if trial.index in scores:
            continue
        scores[trial.index] = float(scorer(trial))
        blind_ledger.write_checkpoint(reservation, scores)

    ordered = [TrialScore(index=i, test_nmse=scores[i]) for i in sorted(scores)]
    return SpecScore(namespace=spec.namespace, scores=ordered)


def summarize(result: SpecScore) -> dict:
    return {
        "median_test_nmse": result.median,
        "n_under_target": result.n_under_target,
        "n_seeds": len(result.scores),
        "per_seed": {str(s.index): s.test_nmse for s in result.scores},
        "meets_acceptance": result.meets_acceptance(),
    }


def run_blind_evaluation(
    lock_path: Path,
    blind_manifest_path: Path,
    ledger_path: Path,
    *,
    resume_run_id: str | None = None,
    repo_root: Path | None = None,
) -> dict:
    """Run the single blind evaluation for the locked candidate.

    Returns the recorded ledger entry. Raises
    :class:`~.candidate_lock.BlindEvaluationBlocked` on any contract violation.
    """
    ticket: BlindEvaluationTicket
    lock = load_lock(Path(lock_path))

    with ProcessLock(process_lock_path(Path(ledger_path))):
        if resume_run_id is None:
            ticket = guard_blind_evaluation(
                Path(lock_path), Path(blind_manifest_path), Path(ledger_path),
                repo_root=repo_root,
            )
            reservation = blind_ledger.reserve_attempt(ticket)
        else:
            # The guard refuses once an attempt exists, which is exactly the
            # state a crashed run leaves behind. Rebuild the ticket directly and
            # let resume_attempt enforce identity of candidate, run and package.
            ticket = _resume_ticket(lock, Path(lock_path), Path(blind_manifest_path),
                                    Path(ledger_path), repo_root=repo_root)
            reservation = blind_ledger.resume_attempt(ticket, resume_run_id)

        scorer = load_locked_scorer(lock, repo_root=repo_root)
        result = score_blind_with_checkpoint(reservation, scorer)
        return blind_ledger.complete_attempt(reservation, summarize(result))


def _resume_ticket(lock, lock_path: Path, blind_manifest_path: Path,
                   ledger_path: Path, *, repo_root: Path | None) -> BlindEvaluationTicket:
    """Re-check everything the guard checks, except the no-attempt-yet rule."""
    from . import manifest as manifest_mod
    from .candidate_lock import check_entry_point, verify_locked_sources

    if not lock.locked:
        raise BlindEvaluationBlocked(
            f"candidate {lock.candidate_id!r} lock is present but not locked"
        )
    problems = verify_locked_sources(lock, repo_root=repo_root)
    if problems:
        raise BlindEvaluationBlocked(
            "locked candidate sources changed: " + "; ".join(problems)
        )
    check_entry_point(lock.entry_point)
    lock.readout.validate()

    verify = manifest_mod.verify_manifest(blind_manifest_path)
    if not verify.ok:
        raise BlindEvaluationBlocked(
            "blind manifest does not verify: " + "; ".join(verify.mismatches)
        )
    current = manifest_mod.load_digest(blind_manifest_path)
    if current != lock.blind_manifest_digest:
        raise BlindEvaluationBlocked(
            "blind manifest digest differs from the locked value "
            f"({current} != {lock.blind_manifest_digest})"
        )

    return BlindEvaluationTicket(
        candidate_id=lock.candidate_id,
        blind_manifest_digest=lock.blind_manifest_digest,
        lock_sha256=lock.content_sha256(),
        lock_path=str(lock_path),
        ledger_path=str(ledger_path),
    )
