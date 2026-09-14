"""Atomic, single-attempt ledger for blind NARMA-10 evaluation.

The blind suite may be consumed **once**, by one candidate, in one run. The
inherited v1 implementation recorded the attempt *after* scoring, so a crash —
or a second process — silently bought another look at the blind set. Here the
attempt is consumed **before** any blind data is touched:

1. ``reserve_attempt`` appends a ``reserved`` entry atomically (temp file plus
   ``os.replace``) while holding an exclusive process lock.
2. Scoring runs and checkpoints progress under the reservation's ``run_id``.
3. ``complete_attempt`` flips the same entry to ``completed`` and stores the
   summary.

A crash therefore leaves a ``reserved`` entry. The *only* way forward is
``resume_attempt``: the same candidate, the same ``run_id``, the same lock
content digest and a checkpoint that agrees with all three. Anything else is
refused. Deleting the ledger entry to "retry" is a contract violation, not a
recovery path.

Ledger schema: ``narma10-blind-ledger/2``.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .candidate_lock import BlindEvaluationBlocked, BlindEvaluationTicket

LEDGER_SCHEMA = "narma10-blind-ledger/2"
CHECKPOINT_SCHEMA = "narma10-blind-checkpoint/1"

STATUS_RESERVED = "reserved"
STATUS_COMPLETED = "completed"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- process lock -----------------------------------------------------------

class ProcessLock:
    """Exclusive, advisory lock file. Fail-closed if already held.

    ``O_CREAT | O_EXCL`` is atomic on both POSIX and Windows, so two concurrent
    blind runs cannot both enter the critical section.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._fd: int | None = None

    def __enter__(self) -> "ProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise BlindEvaluationBlocked(
                f"another blind evaluation holds {self.path.name}; "
                "refusing to run two attempts concurrently"
            ) from exc
        os.write(self._fd, f"{os.getpid()} {_utc_now()}\n".encode("utf-8"))
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:  # pragma: no cover - already gone
            pass


def process_lock_path(ledger_path: Path) -> Path:
    return Path(ledger_path).with_suffix(".processlock")


# --- ledger io --------------------------------------------------------------

def _empty_ledger() -> dict:
    return {"schema": LEDGER_SCHEMA, "entries": []}


def read_ledger(ledger_path: Path) -> dict:
    path = Path(ledger_path)
    if not path.exists():
        return _empty_ledger()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BlindEvaluationBlocked(f"ledger unreadable: {exc!r}") from exc
    if not isinstance(data, dict) or data.get("schema") != LEDGER_SCHEMA:
        raise BlindEvaluationBlocked(
            f"unexpected ledger schema {data.get('schema')!r} "
            f"(expected {LEDGER_SCHEMA!r})"
        )
    if not isinstance(data.get("entries"), list):
        raise BlindEvaluationBlocked("ledger entries block is malformed")
    return data


def _write_ledger_atomic(ledger_path: Path, data: dict) -> None:
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def find_entry(ledger_path: Path, candidate_id: str) -> dict | None:
    for entry in read_ledger(ledger_path).get("entries", []):
        if entry.get("candidate_id") == candidate_id:
            return entry
    return None


# --- reservation ------------------------------------------------------------

@dataclass(frozen=True)
class Reservation:
    """A consumed blind attempt. Required to record a result."""

    candidate_id: str
    run_id: str
    lock_sha256: str
    blind_manifest_digest: str
    ledger_path: str
    checkpoint_path: str


def checkpoint_path_for(ledger_path: Path, candidate_id: str) -> Path:
    return Path(ledger_path).parent / f"{candidate_id}.blind-checkpoint.json"


def reserve_attempt(ticket: BlindEvaluationTicket) -> Reservation:
    """Consume the single blind attempt **before** any scoring happens."""
    ledger_path = Path(ticket.ledger_path)
    data = read_ledger(ledger_path)

    if any(e.get("candidate_id") == ticket.candidate_id for e in data["entries"]):
        raise BlindEvaluationBlocked(
            f"candidate {ticket.candidate_id!r} already has a blind attempt; "
            "the ledger is append-only and the suite is single-use"
        )
    completed = [e for e in data["entries"] if e.get("status") == STATUS_COMPLETED]
    if completed:
        raise BlindEvaluationBlocked(
            "the blind suite has already been consumed by candidate "
            f"{completed[0].get('candidate_id')!r}; it cannot be reopened "
            "under a different candidate id"
        )
    reserved = [e for e in data["entries"] if e.get("status") == STATUS_RESERVED]
    if reserved:
        raise BlindEvaluationBlocked(
            "an unfinished blind attempt exists for candidate "
            f"{reserved[0].get('candidate_id')!r}; resume that run instead of "
            "starting a new one"
        )

    run_id = uuid.uuid4().hex
    entry = {
        "candidate_id": ticket.candidate_id,
        "run_id": run_id,
        "status": STATUS_RESERVED,
        "reserved_utc": _utc_now(),
        "blind_manifest_digest": ticket.blind_manifest_digest,
        "lock_sha256": ticket.lock_sha256,
    }
    data["entries"].append(entry)
    _write_ledger_atomic(ledger_path, data)

    return Reservation(
        candidate_id=ticket.candidate_id,
        run_id=run_id,
        lock_sha256=ticket.lock_sha256,
        blind_manifest_digest=ticket.blind_manifest_digest,
        ledger_path=str(ledger_path),
        checkpoint_path=str(checkpoint_path_for(ledger_path, ticket.candidate_id)),
    )


def resume_attempt(ticket: BlindEvaluationTicket, run_id: str) -> Reservation:
    """Resume a crashed run. Same candidate, same run_id, same lock, or refuse."""
    ledger_path = Path(ticket.ledger_path)
    entry = find_entry(ledger_path, ticket.candidate_id)
    if entry is None:
        raise BlindEvaluationBlocked(
            f"no reserved blind attempt for candidate {ticket.candidate_id!r}; "
            "there is nothing to resume"
        )
    if entry.get("status") != STATUS_RESERVED:
        raise BlindEvaluationBlocked(
            f"blind attempt for {ticket.candidate_id!r} is "
            f"{entry.get('status')!r}, not {STATUS_RESERVED!r}"
        )
    if entry.get("run_id") != run_id:
        raise BlindEvaluationBlocked(
            "run_id does not match the reserved attempt; a new run may not "
            "reuse a consumed blind attempt"
        )
    if entry.get("lock_sha256") != ticket.lock_sha256:
        raise BlindEvaluationBlocked(
            "candidate lock changed since the attempt was reserved; "
            "recovery is only allowed for the identical locked package"
        )
    if entry.get("blind_manifest_digest") != ticket.blind_manifest_digest:
        raise BlindEvaluationBlocked(
            "blind manifest digest changed since the attempt was reserved"
        )

    reservation = Reservation(
        candidate_id=ticket.candidate_id,
        run_id=run_id,
        lock_sha256=ticket.lock_sha256,
        blind_manifest_digest=ticket.blind_manifest_digest,
        ledger_path=str(ledger_path),
        checkpoint_path=str(checkpoint_path_for(ledger_path, ticket.candidate_id)),
    )
    # Validate any checkpoint now, so a mismatched one fails before scoring.
    read_checkpoint(reservation)
    return reservation


def complete_attempt(reservation: Reservation, summary: dict) -> dict:
    """Flip the reserved entry to ``completed`` and store the summary."""
    ledger_path = Path(reservation.ledger_path)
    data = read_ledger(ledger_path)

    for entry in data["entries"]:
        if entry.get("candidate_id") != reservation.candidate_id:
            continue
        if entry.get("status") == STATUS_COMPLETED:
            raise BlindEvaluationBlocked(
                f"candidate {reservation.candidate_id!r} already has a completed "
                "blind result; the ledger is append-only"
            )
        if entry.get("run_id") != reservation.run_id:
            raise BlindEvaluationBlocked(
                "run_id does not match the reserved attempt; refusing to record"
            )
        if entry.get("lock_sha256") != reservation.lock_sha256:
            raise BlindEvaluationBlocked(
                "candidate lock changed during the run; refusing to record"
            )
        entry["status"] = STATUS_COMPLETED
        entry["completed_utc"] = _utc_now()
        entry["summary"] = summary
        _write_ledger_atomic(ledger_path, data)
        _discard_checkpoint(reservation)
        return dict(entry)

    raise BlindEvaluationBlocked(
        f"no reserved attempt for candidate {reservation.candidate_id!r}; "
        "refusing to record a result that was never reserved"
    )


# --- checkpoint -------------------------------------------------------------

def write_checkpoint(reservation: Reservation, scores: dict[int, float]) -> None:
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "candidate_id": reservation.candidate_id,
        "run_id": reservation.run_id,
        "lock_sha256": reservation.lock_sha256,
        "blind_manifest_digest": reservation.blind_manifest_digest,
        "updated_utc": _utc_now(),
        "scores": {str(k): float(v) for k, v in sorted(scores.items())},
    }
    path = Path(reservation.checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_checkpoint(reservation: Reservation) -> dict[int, float]:
    """Return already-scored seeds, or ``{}`` when there is no checkpoint.

    A checkpoint that does not belong to this exact run is fatal, not ignorable.
    """
    path = Path(reservation.checkpoint_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BlindEvaluationBlocked(f"blind checkpoint unreadable: {exc!r}") from exc

    if data.get("schema") != CHECKPOINT_SCHEMA:
        raise BlindEvaluationBlocked(
            f"unexpected checkpoint schema {data.get('schema')!r}"
        )
    for field, expected in (
        ("candidate_id", reservation.candidate_id),
        ("run_id", reservation.run_id),
        ("lock_sha256", reservation.lock_sha256),
        ("blind_manifest_digest", reservation.blind_manifest_digest),
    ):
        if data.get(field) != expected:
            raise BlindEvaluationBlocked(
                f"blind checkpoint {field} does not match the reserved attempt; "
                "recovery is only allowed for the identical run and package"
            )

    scores_raw = data.get("scores")
    if not isinstance(scores_raw, dict):
        raise BlindEvaluationBlocked("blind checkpoint scores block is malformed")
    scores: dict[int, float] = {}
    for key, value in scores_raw.items():
        try:
            scores[int(key)] = float(value)
        except (TypeError, ValueError) as exc:
            raise BlindEvaluationBlocked(
                f"blind checkpoint holds a non-numeric score for seed {key!r}"
            ) from exc
    return scores


def _discard_checkpoint(reservation: Reservation) -> None:
    try:
        Path(reservation.checkpoint_path).unlink()
    except FileNotFoundError:
        pass
