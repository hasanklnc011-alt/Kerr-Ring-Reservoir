"""Fail-closed candidate-lock guard for blind NARMA-10 evaluation.

Project rule (``const.md``): *"Kör test sonucu tuning için geri beslenemez."*
Blind seeds may only be evaluated **after** a candidate architecture is frozen,
and each candidate may be scored on the blind set **exactly once**.

This module enforces that with a guard that is *fail-closed*: unless every
precondition is explicitly satisfied it raises :class:`BlindEvaluationBlocked`
and the blind data is never touched.

Preconditions checked before blind evaluation is allowed:

1. A lock file exists, is well-formed, and has ``locked is True``.
2. The lock records a ``blind_manifest_digest`` that matches the *current*
   verified blind manifest (so the blind data cannot have changed after lock,
   and the candidate was locked against this exact blind set).
3. The candidate's ``code_sha256`` matches the artifact it claims to lock.
4. The results ledger does not already contain a blind entry for this
   ``candidate_id`` (no re-runs, no feedback loop).

Any exception during these checks is converted into ``BlindEvaluationBlocked``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import manifest as manifest_mod

LOCK_SCHEMA = "narma10-candidate-lock/1"
LEDGER_SCHEMA = "narma10-blind-ledger/1"


class CandidateLockError(RuntimeError):
    """Base class for candidate-lock failures."""


class BlindEvaluationBlocked(CandidateLockError):
    """Raised (fail-closed) whenever blind evaluation must not proceed."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class CandidateLock:
    schema: str
    candidate_id: str
    description: str
    created_utc: str
    code_path: str
    code_sha256: str
    dev_manifest_digest: str
    blind_manifest_digest: str
    locked: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict) -> "CandidateLock":
        missing = {f for f in cls.__dataclass_fields__} - set(data)
        if missing:
            raise CandidateLockError(f"lock file missing fields: {sorted(missing)}")
        return cls(**{k: data[k] for k in cls.__dataclass_fields__})


def create_lock(
    candidate_id: str,
    description: str,
    code_path: Path,
    dev_manifest_path: Path,
    blind_manifest_path: Path,
    lock_path: Path,
    *,
    locked: bool = True,
) -> CandidateLock:
    """Freeze a candidate against the current dev + blind manifests.

    Both manifests must verify (recomputed hashes match) or this raises.
    """
    code_path = Path(code_path)
    if not code_path.exists():
        raise CandidateLockError(f"candidate artifact not found: {code_path}")

    for name, mpath in (("dev", dev_manifest_path), ("blind", blind_manifest_path)):
        result = manifest_mod.verify_manifest(Path(mpath))
        if not result.ok:
            raise CandidateLockError(
                f"{name} manifest does not verify, refusing to lock: "
                + "; ".join(result.mismatches)
            )

    lock = CandidateLock(
        schema=LOCK_SCHEMA,
        candidate_id=candidate_id,
        description=description,
        created_utc=_utc_now(),
        code_path=str(code_path),
        code_sha256=sha256_file(code_path),
        dev_manifest_digest=manifest_mod.load_digest(Path(dev_manifest_path)),
        blind_manifest_digest=manifest_mod.load_digest(Path(blind_manifest_path)),
        locked=bool(locked),
    )
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(lock.to_json(), encoding="utf-8")
    return lock


def load_lock(lock_path: Path) -> CandidateLock:
    path = Path(lock_path)
    if not path.exists():
        raise CandidateLockError(f"no candidate lock at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    lock = CandidateLock.from_dict(data)
    if lock.schema != LOCK_SCHEMA:
        raise CandidateLockError(f"unexpected lock schema {lock.schema!r}")
    return lock


def _read_ledger(ledger_path: Path) -> dict:
    path = Path(ledger_path)
    if not path.exists():
        return {"schema": LEDGER_SCHEMA, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != LEDGER_SCHEMA:
        raise CandidateLockError(f"unexpected ledger schema {data.get('schema')!r}")
    return data


def ledger_has_candidate(ledger_path: Path, candidate_id: str) -> bool:
    data = _read_ledger(Path(ledger_path))
    return any(e.get("candidate_id") == candidate_id for e in data.get("entries", []))


@dataclass(frozen=True)
class BlindEvaluationTicket:
    """Proof that the guard passed. Required to record a blind result."""

    candidate_id: str
    blind_manifest_digest: str
    lock_path: str
    ledger_path: str


def guard_blind_evaluation(
    lock_path: Path,
    blind_manifest_path: Path,
    ledger_path: Path,
) -> BlindEvaluationTicket:
    """Return a ticket iff blind evaluation is allowed; otherwise raise.

    Fail-closed: *any* problem -> :class:`BlindEvaluationBlocked`.
    """
    try:
        lock = load_lock(Path(lock_path))

        if not lock.locked:
            raise BlindEvaluationBlocked(
                f"candidate {lock.candidate_id!r} lock is present but not locked"
            )

        if not Path(lock.code_path).exists():
            raise BlindEvaluationBlocked(
                f"locked artifact missing: {lock.code_path}"
            )
        current_code_hash = sha256_file(Path(lock.code_path))
        if current_code_hash != lock.code_sha256:
            raise BlindEvaluationBlocked(
                "locked artifact changed since lock "
                f"({current_code_hash} != {lock.code_sha256})"
            )

        result = manifest_mod.verify_manifest(Path(blind_manifest_path))
        if not result.ok:
            raise BlindEvaluationBlocked(
                "blind manifest does not verify: " + "; ".join(result.mismatches)
            )
        current_blind_digest = manifest_mod.load_digest(Path(blind_manifest_path))
        if current_blind_digest != lock.blind_manifest_digest:
            raise BlindEvaluationBlocked(
                "blind manifest digest differs from the locked value "
                f"({current_blind_digest} != {lock.blind_manifest_digest})"
            )

        if ledger_has_candidate(Path(ledger_path), lock.candidate_id):
            raise BlindEvaluationBlocked(
                f"candidate {lock.candidate_id!r} already has a blind result; "
                "re-evaluation would feed the blind set back into selection"
            )

    except BlindEvaluationBlocked:
        raise
    except Exception as exc:  # fail-closed on anything unexpected
        raise BlindEvaluationBlocked(f"blind evaluation blocked: {exc!r}") from exc

    return BlindEvaluationTicket(
        candidate_id=lock.candidate_id,
        blind_manifest_digest=lock.blind_manifest_digest,
        lock_path=str(lock_path),
        ledger_path=str(ledger_path),
    )


def record_blind_result(ticket: BlindEvaluationTicket, summary: dict) -> dict:
    """Append a blind result to the ledger exactly once (append-only).

    Refuses if the candidate already has an entry (double-check against races).
    """
    ledger_path = Path(ticket.ledger_path)
    data = _read_ledger(ledger_path)
    if any(e.get("candidate_id") == ticket.candidate_id for e in data["entries"]):
        raise BlindEvaluationBlocked(
            f"candidate {ticket.candidate_id!r} already recorded; ledger is append-only"
        )
    entry = {
        "candidate_id": ticket.candidate_id,
        "recorded_utc": _utc_now(),
        "blind_manifest_digest": ticket.blind_manifest_digest,
        "summary": summary,
    }
    data["entries"].append(entry)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry
