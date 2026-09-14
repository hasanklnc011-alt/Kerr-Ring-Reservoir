"""Fail-closed candidate lock (schema v2) for blind NARMA-10 evaluation.

Project rule (``const.md``): *"Kör test sonucu tuning için geri beslenemez."*
Blind seeds may only be evaluated **after** a candidate is frozen, and each
candidate may be scored on the blind set **exactly once**.

A v2 lock freezes the whole candidate *package*, not a single file:

* ``entry_point`` — ``"module:attr"``, a zero-argument factory returning the
  scorer that will be run against the blind spec. The locked scorer is the
  only thing blind evaluation may call; the baseline is explicitly banned.
* ``sources`` — content hash of every file under ``source_root``, so a change
  anywhere in the package (including transitively imported helpers) is caught.
* ``readout`` — slot count, port count, feature count, sampling point, digital
  tap count and the ridge-selection protocol. The CLI cannot override these.
* the dev and blind manifest digests at lock time.

v1 locks are not accepted: they froze one file and carried no entry point, so
they cannot pin what actually runs. See
``docs/decisions/2026-09-14-repo-migration.md`` (G0).

Consumption of the single blind attempt lives in :mod:`.blind_ledger`;
:func:`guard_blind_evaluation` here is read-only and safe for preflight.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from . import manifest as manifest_mod

LOCK_SCHEMA = "narma10-candidate-lock/2"

#: Entry points that must never be locked or run as a blind scorer. The
#: baseline exists to exercise the pipeline; scoring the blind set with it
#: would consume the single attempt on a known-failing linear control.
BANNED_ENTRY_POINTS = frozenset({
    "benchmarks.narma10_np.evaluate:baseline_delay_scorer",
    "narma10_np.evaluate:baseline_delay_scorer",
})

#: Ridge alpha must be picked inside the training window only.
ALLOWED_RIDGE_SELECTION = frozenset({"train_inner_split", "fixed_locked_alpha"})

_SKIP_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".venv"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}


class CandidateLockError(RuntimeError):
    """Base class for candidate-lock failures."""


class BlindEvaluationBlocked(CandidateLockError):
    """Raised (fail-closed) whenever blind evaluation must not proceed."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_source_files(source_root: Path) -> Iterable[Path]:
    """Yield every content file under ``source_root``, deterministically."""
    root = Path(source_root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        if path.suffix in _SKIP_SUFFIXES:
            continue
        yield path


@dataclass(frozen=True)
class ReadoutContract:
    """The measurement contract frozen with the candidate."""

    slots: int
    ports: int
    n_features: int
    sampling: str
    digital_taps: int
    ridge_selection: str
    ridge_alpha: float | None = None

    def validate(self) -> None:
        if self.slots <= 0 or self.ports <= 0:
            raise CandidateLockError("readout slots and ports must be positive")
        if self.n_features != self.slots * self.ports:
            raise CandidateLockError(
                f"readout n_features ({self.n_features}) must equal "
                f"slots*ports ({self.slots * self.ports})"
            )
        if self.digital_taps != 0:
            raise CandidateLockError(
                "inter-symbol digital taps are not allowed "
                f"(digital_taps={self.digital_taps})"
            )
        if self.ridge_selection not in ALLOWED_RIDGE_SELECTION:
            raise CandidateLockError(
                f"ridge_selection {self.ridge_selection!r} not in "
                f"{sorted(ALLOWED_RIDGE_SELECTION)}"
            )
        if self.ridge_selection == "fixed_locked_alpha" and self.ridge_alpha is None:
            raise CandidateLockError("fixed_locked_alpha requires ridge_alpha")

    @classmethod
    def from_dict(cls, data: dict) -> "ReadoutContract":
        if not isinstance(data, dict):
            raise CandidateLockError("readout block is not an object")
        missing = {f for f in cls.__dataclass_fields__} - set(data) - {"ridge_alpha"}
        if missing:
            raise CandidateLockError(f"readout missing fields: {sorted(missing)}")
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass(frozen=True)
class CandidateLock:
    schema: str
    candidate_id: str
    description: str
    created_utc: str
    entry_point: str
    source_root: str
    sources: tuple[tuple[str, str], ...]
    readout: ReadoutContract
    environment: dict
    dev_manifest_digest: str
    blind_manifest_digest: str
    locked: bool

    def to_payload(self) -> dict:
        data = asdict(self)
        data["sources"] = [{"path": p, "sha256": h} for p, h in self.sources]
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), indent=2, sort_keys=True) + "\n"

    def content_sha256(self) -> str:
        """Digest binding a blind reservation to this exact lock content."""
        return sha256_text(json.dumps(self.to_payload(), sort_keys=True,
                                      separators=(",", ":")))

    @classmethod
    def from_dict(cls, data: dict) -> "CandidateLock":
        missing = {f for f in cls.__dataclass_fields__} - set(data)
        if missing:
            raise CandidateLockError(f"lock file missing fields: {sorted(missing)}")
        sources_raw = data["sources"]
        if not isinstance(sources_raw, list) or not sources_raw:
            raise CandidateLockError("lock has an empty or malformed sources block")
        sources: list[tuple[str, str]] = []
        for item in sources_raw:
            if not isinstance(item, dict) or "path" not in item or "sha256" not in item:
                raise CandidateLockError("malformed entry in sources block")
            sources.append((str(item["path"]), str(item["sha256"])))
        return cls(
            schema=data["schema"],
            candidate_id=data["candidate_id"],
            description=data["description"],
            created_utc=data["created_utc"],
            entry_point=data["entry_point"],
            source_root=data["source_root"],
            sources=tuple(sorted(sources)),
            readout=ReadoutContract.from_dict(data["readout"]),
            environment=data["environment"],
            dev_manifest_digest=data["dev_manifest_digest"],
            blind_manifest_digest=data["blind_manifest_digest"],
            locked=bool(data["locked"]),
        )


def _environment_block() -> dict:
    try:
        import numpy  # noqa: PLC0415 - recorded on purpose
        numpy_version = numpy.__version__
    except Exception:  # pragma: no cover - numpy is a hard dependency
        numpy_version = "unavailable"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": numpy_version,
    }


def check_entry_point(entry_point: str) -> None:
    if ":" not in entry_point:
        raise CandidateLockError(
            f"entry_point {entry_point!r} must be 'module:attribute'"
        )
    if entry_point in BANNED_ENTRY_POINTS:
        raise CandidateLockError(
            f"entry_point {entry_point!r} is the baseline control and is banned "
            "from blind evaluation"
        )


def create_lock(
    candidate_id: str,
    description: str,
    entry_point: str,
    source_root: Path,
    readout: ReadoutContract,
    dev_manifest_path: Path,
    blind_manifest_path: Path,
    lock_path: Path,
    *,
    locked: bool = True,
    repo_root: Path | None = None,
) -> CandidateLock:
    """Freeze a candidate package against the current dev + blind manifests."""
    root = Path(source_root)
    if not root.exists():
        raise CandidateLockError(f"candidate source root not found: {root}")

    check_entry_point(entry_point)
    readout.validate()

    base = Path(repo_root) if repo_root is not None else manifest_mod.REPO_ROOT
    files = list(iter_source_files(root))
    if not files:
        raise CandidateLockError(f"candidate source root has no files: {root}")

    sources = tuple(sorted(
        (_relpath(p, base), sha256_file(p)) for p in files
    ))

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
        entry_point=entry_point,
        source_root=_relpath(root, base),
        sources=sources,
        readout=readout,
        environment=_environment_block(),
        dev_manifest_digest=manifest_mod.load_digest(Path(dev_manifest_path)),
        blind_manifest_digest=manifest_mod.load_digest(Path(blind_manifest_path)),
        locked=bool(locked),
    )
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(lock.to_json(), encoding="utf-8")
    return lock


def _relpath(path: Path, base: Path) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(Path(base).resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def load_lock(lock_path: Path) -> CandidateLock:
    path = Path(lock_path)
    if not path.exists():
        raise CandidateLockError(f"no candidate lock at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CandidateLockError("lock file is not an object")
    schema = data.get("schema")
    if schema != LOCK_SCHEMA:
        raise CandidateLockError(
            f"unexpected lock schema {schema!r}; only {LOCK_SCHEMA!r} may be "
            "used for blind evaluation"
        )
    return CandidateLock.from_dict(data)


def verify_locked_sources(lock: CandidateLock,
                          repo_root: Path | None = None) -> list[str]:
    """Return a list of mismatches between the lock and the files on disk.

    Catches changed, missing **and newly added** files under ``source_root``,
    so a transitive helper added after lock time cannot slip in.
    """
    base = Path(repo_root) if repo_root is not None else manifest_mod.REPO_ROOT
    problems: list[str] = []
    locked_map = dict(lock.sources)

    root = base / lock.source_root
    if not root.exists():
        return [f"locked source root missing: {lock.source_root}"]

    on_disk: dict[str, str] = {}
    for path in iter_source_files(root):
        on_disk[_relpath(path, base)] = sha256_file(path)

    for rel, expected in sorted(locked_map.items()):
        actual = on_disk.get(rel)
        if actual is None:
            problems.append(f"locked source missing: {rel}")
        elif actual != expected:
            problems.append(f"locked source changed: {rel}")

    for rel in sorted(set(on_disk) - set(locked_map)):
        problems.append(f"source added after lock: {rel}")

    return problems


def load_locked_scorer(lock: CandidateLock,
                       repo_root: Path | None = None) -> Callable[[Any], float]:
    """Import and build the scorer this lock froze.

    Fail-closed: source drift, a banned entry point, an unimportable module or
    a non-callable factory all raise :class:`BlindEvaluationBlocked`.
    """
    problems = verify_locked_sources(lock, repo_root=repo_root)
    if problems:
        raise BlindEvaluationBlocked(
            "locked candidate sources changed: " + "; ".join(problems)
        )

    try:
        check_entry_point(lock.entry_point)
    except CandidateLockError as exc:
        raise BlindEvaluationBlocked(str(exc)) from exc

    module_name, _, attr = lock.entry_point.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise BlindEvaluationBlocked(
            f"cannot import locked entry point module {module_name!r}: {exc!r}"
        ) from exc

    factory = getattr(module, attr, None)
    if factory is None:
        raise BlindEvaluationBlocked(
            f"locked entry point {lock.entry_point!r} not found"
        )
    if not callable(factory):
        raise BlindEvaluationBlocked(
            f"locked entry point {lock.entry_point!r} is not callable"
        )

    resolved = f"{getattr(factory, '__module__', module_name)}:" \
               f"{getattr(factory, '__qualname__', attr)}"
    if resolved in BANNED_ENTRY_POINTS:
        raise BlindEvaluationBlocked(
            f"locked entry point resolves to the banned baseline ({resolved})"
        )

    try:
        scorer = factory()
    except Exception as exc:
        raise BlindEvaluationBlocked(
            f"locked scorer factory {lock.entry_point!r} raised: {exc!r}"
        ) from exc

    if not callable(scorer):
        raise BlindEvaluationBlocked(
            f"locked scorer factory {lock.entry_point!r} did not return a callable"
        )
    return scorer


@dataclass(frozen=True)
class BlindEvaluationTicket:
    """Proof that the read-only guard passed. Required to reserve an attempt."""

    candidate_id: str
    blind_manifest_digest: str
    lock_sha256: str
    lock_path: str
    ledger_path: str


def guard_blind_evaluation(
    lock_path: Path,
    blind_manifest_path: Path,
    ledger_path: Path,
    *,
    repo_root: Path | None = None,
) -> BlindEvaluationTicket:
    """Return a ticket iff blind evaluation is allowed; otherwise raise.

    Read-only and side-effect free: this may be called from preflight. The
    single attempt is consumed later, by :func:`blind_ledger.reserve_attempt`.
    """
    from . import blind_ledger  # local import: blind_ledger imports this module

    try:
        lock = load_lock(Path(lock_path))

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

        existing = blind_ledger.find_entry(Path(ledger_path), lock.candidate_id)
        if existing is not None:
            raise BlindEvaluationBlocked(
                f"candidate {lock.candidate_id!r} already has a blind attempt "
                f"(status={existing.get('status')!r}); re-evaluation would feed "
                "the blind set back into selection"
            )

    except BlindEvaluationBlocked:
        raise
    except Exception as exc:  # fail-closed on anything unexpected
        raise BlindEvaluationBlocked(f"blind evaluation blocked: {exc!r}") from exc

    return BlindEvaluationTicket(
        candidate_id=lock.candidate_id,
        blind_manifest_digest=lock.blind_manifest_digest,
        lock_sha256=lock.content_sha256(),
        lock_path=str(lock_path),
        ledger_path=str(ledger_path),
    )
