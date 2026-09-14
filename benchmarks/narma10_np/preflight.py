"""Deterministic, read-only preflight for the canonical NARMA-10 benchmark.

The preflight answers, without touching the blind set or mutating any file,
"is the benchmark in a state a reviewer can trust?". It reports and validates:

* **Provenance** — Python / NumPy versions, and whether *this* interpreter
  regenerates the committed manifests bit-for-bit (the meaningful, version-proof
  environment check: the SHA-256-derived seeds and the ``PCG64`` stream are
  supposed to be platform independent).
* **Manifests** — dev and blind manifests exist, ``verify_manifest`` passes,
  the stored ``spec`` / entry hashes still match ``config`` (drift detection),
  and the two ``manifest_digest`` values are distinct.
* **Seed blocks** — dev has :data:`config.N_DEV_SEEDS` trials, blind has
  :data:`config.N_BLIND_SEEDS`, every ``u`` / ``y`` is finite, and no target
  exceeds the sanity magnitude bound the dataset tests already use.
* **Candidate lock** — presence and status of every ``*.lock.json`` under
  ``manifests/narma10/candidates`` (there should be none yet).
* **Blind evaluation** — whether :func:`candidate_lock.guard_blind_evaluation`
  still refuses to run (the expected safe state until Astra ratifies and locks
  a candidate).

Nothing here creates a lock, writes a manifest, runs blind evaluation, or calls
the network. ``run_preflight`` is pure with respect to the filesystem.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import config
from . import manifest as manifest_mod
from .candidate_lock import (
    BlindEvaluationBlocked,
    CandidateLockError,
    guard_blind_evaluation,
    load_lock,
)
from .dataset import build_all

REPO_ROOT = manifest_mod.REPO_ROOT
LOCK_DIR = REPO_ROOT / "manifests" / "narma10" / "candidates"
LEDGER_PATH = REPO_ROOT / "manifests" / "narma10" / "blind_results_ledger.json"

# Same target-magnitude sanity bound the dataset tests assert (test_dataset.py).
FINITE_ABS_BOUND: float = 1e3

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_INFO = "INFO"

_EXPECTED_SEED_COUNT = {"dev": config.N_DEV_SEEDS, "blind": config.N_BLIND_SEEDS}


@dataclass
class Check:
    """One preflight line item."""

    name: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.status == STATUS_FAIL

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": list(self.details),
        }


@dataclass
class PreflightReport:
    checks: list[Check]

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.failed]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "n_checks": len(self.checks),
            "n_failed": len(self.failed),
            "checks": [c.to_dict() for c in self.checks],
        }

    def format_text(self) -> str:
        lines: list[str] = []
        for c in self.checks:
            lines.append(f"[{c.status}] {c.name}: {c.summary}")
            lines.extend(f"       {d}" for d in c.details)
        lines.append("")
        if self.ok:
            lines.append(f"PREFLIGHT OK ({len(self.checks)} checks)")
        else:
            names = ", ".join(c.name for c in self.failed)
            lines.append(f"PREFLIGHT FAILED ({len(self.failed)} check(s): {names})")
        return "\n".join(lines)


def _rel(path: Path) -> str:
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _check_provenance() -> Check:
    impl = platform.python_implementation()
    pyver = platform.python_version()
    details = [
        f"python_implementation = {impl}",
        f"python_version = {pyver}",
        f"numpy_version = {np.__version__}",
        "note = per signals.py the seed derivation (SHA-256) and PCG64 stream "
        "are platform/version independent; the manifest checks below are the "
        "authoritative environment validation",
    ]
    return Check(
        "environment.provenance",
        STATUS_INFO,
        f"{impl} {pyver} / NumPy {np.__version__}",
        details,
    )


def _config_drift(stored: dict, recomputed: dict) -> list[str]:
    """Fields where a committed manifest disagrees with the current ``config``."""
    problems: list[str] = []
    if stored.get("schema") != recomputed["schema"]:
        problems.append(
            f"schema {stored.get('schema')!r} != {recomputed['schema']!r}"
        )
    if stored.get("spec") != recomputed["spec"]:
        problems.append("spec block differs from config.py")
    stored_by_index = {e.get("index"): e for e in stored.get("entries", [])}
    rec_by_index = {e["index"]: e for e in recomputed["entries"]}
    if set(stored_by_index) != set(rec_by_index):
        problems.append(
            f"entry indices {sorted(stored_by_index)} != {sorted(rec_by_index)}"
        )
    for index in sorted(set(stored_by_index) & set(rec_by_index)):
        s, r = stored_by_index[index], rec_by_index[index]
        for f in ("seed", "length", "input_sha256", "target_sha256"):
            if s.get(f) != r.get(f):
                problems.append(
                    f"entry {index} {f}: {s.get(f)!r} != recomputed {r.get(f)!r}"
                )
    return problems


def _check_manifest(spec: config.SeedSpec, label: str) -> Check:
    name = f"manifest.{label}"
    path = manifest_mod.default_path(spec)
    if not path.exists():
        return Check(name, STATUS_FAIL, f"missing manifest file {_rel(path)}")

    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Check(name, STATUS_FAIL, f"manifest unreadable: {exc}", [f"path = {_rel(path)}"])

    recomputed = manifest_mod.build_manifest(spec)
    committed_digest = stored.get("manifest_digest")
    recomputed_digest = recomputed["manifest_digest"]
    n_entries = len(stored.get("entries", []))
    expected = _EXPECTED_SEED_COUNT[label]
    details = [
        f"path = {_rel(path)}",
        f"committed_digest = {committed_digest}",
        f"recomputed_digest = {recomputed_digest}",
        f"entries = {n_entries} (expected {expected})",
    ]

    result = manifest_mod.verify_manifest(path)
    if not result.ok:
        details.extend(f"mismatch: {m}" for m in result.mismatches)
        return Check(name, STATUS_FAIL, "verify_manifest reported mismatches", details)

    drift = _config_drift(stored, recomputed)
    if drift:
        details.extend(f"drift: {d}" for d in drift)
        return Check(name, STATUS_FAIL, "committed manifest has drifted from config.py", details)

    if committed_digest != recomputed_digest:
        return Check(name, STATUS_FAIL, "recomputed digest differs from committed digest", details)

    if n_entries != expected:
        return Check(name, STATUS_FAIL, f"entry count {n_entries} != expected {expected}", details)

    return Check(name, STATUS_PASS, f"verified; digest {committed_digest[:16]}...", details)


def _check_digests_distinct() -> Check:
    name = "manifest.digests_distinct"
    try:
        dev = manifest_mod.load_digest(manifest_mod.default_path(config.dev_spec()))
        blind = manifest_mod.load_digest(manifest_mod.default_path(config.blind_spec()))
    except (OSError, ValueError, KeyError) as exc:
        return Check(name, STATUS_FAIL, f"could not read both digests: {exc}")
    if dev == blind:
        return Check(name, STATUS_FAIL, "dev and blind manifest digests are identical",
                     [f"digest = {dev}"])
    return Check(name, STATUS_PASS, "dev and blind digests differ",
                 [f"dev = {dev}", f"blind = {blind}"])


def _check_seed_block(spec: config.SeedSpec, label: str) -> Check:
    name = f"seeds.{label}"
    expected = _EXPECTED_SEED_COUNT[label]
    details = [f"namespace = {spec.namespace}", f"expected_count = {expected}"]

    if spec.count != expected:
        return Check(name, STATUS_FAIL,
                     f"config spec count {spec.count} != expected {expected}", details)

    try:
        trials = build_all(spec)
    except FloatingPointError as exc:
        details.append(f"error = {exc}")
        return Check(name, STATUS_FAIL, "trial generation produced non-finite data", details)

    n_finite = sum(
        1 for t in trials
        if bool(np.all(np.isfinite(t.u))) and bool(np.all(np.isfinite(t.y)))
    )
    max_abs = max(float(np.max(np.abs(t.y))) for t in trials)
    details.append(f"generated_trials = {len(trials)}")
    details.append(f"finite_trials = {n_finite}")
    details.append(f"max_abs_target = {max_abs:.6g}")

    if len(trials) != expected or n_finite != len(trials):
        return Check(name, STATUS_FAIL, "seed block miscounted or not fully finite", details)
    if max_abs >= FINITE_ABS_BOUND:
        return Check(name, STATUS_FAIL,
                     f"max|y| {max_abs:.4g} >= sanity bound {FINITE_ABS_BOUND}", details)

    return Check(name, STATUS_PASS,
                 f"{len(trials)} finite trials, max|y| = {max_abs:.4g}", details)


def _find_locks(lock_dir: Path | None = None) -> list[Path]:
    d = Path(lock_dir) if lock_dir is not None else LOCK_DIR
    if not d.exists():
        return []
    return sorted(d.glob("*.lock.json"))


def _check_candidate_lock(lock_dir: Path) -> Check:
    name = "candidate_lock"
    locks = _find_locks(lock_dir)
    scanned = f"scanned = {_rel(lock_dir)}"
    if not locks:
        return Check(name, STATUS_INFO, "absent - no candidate lock present",
                     [scanned, "count = 0"])
    details = [scanned, f"count = {len(locks)}"]
    for lp in locks:
        rel = _rel(lp)
        try:
            lk = load_lock(lp)
        except (CandidateLockError, ValueError, OSError) as exc:
            details.append(f"{rel}: UNREADABLE ({exc})")
            continue
        code_present = Path(lk.code_path).exists()
        details.append(
            f"{rel}: id={lk.candidate_id!r} locked={lk.locked} "
            f"code_present={code_present} "
            f"blind_manifest_digest={lk.blind_manifest_digest[:16]}..."
        )
    return Check(name, STATUS_INFO, f"{len(locks)} candidate lock file(s) present", details)


def _check_blind_evaluation(lock_dir: Path, ledger_path: Path,
                            *, strict: bool) -> Check:
    name = "blind_evaluation.blocked"
    blind_path = manifest_mod.default_path(config.blind_spec())
    locks = _find_locks(lock_dir)

    if not locks:
        return Check(name, STATUS_PASS,
                     "blocked - no candidate lock, blind evaluation is unreachable",
                     ["guard_blind_evaluation has no lock to admit"])

    details: list[str] = []
    unblocked: list[str] = []
    for lp in locks:
        rel = _rel(lp)
        try:
            ticket = guard_blind_evaluation(lp, blind_path, ledger_path)
        except BlindEvaluationBlocked as exc:
            details.append(f"{rel}: BLOCKED ({exc})")
            continue
        except Exception as exc:  # pragma: no cover - guard is already fail-closed
            details.append(f"{rel}: BLOCKED (unexpected {exc!r})")
            continue
        unblocked.append(rel)
        details.append(f"{rel}: NOT BLOCKED - guard admitted candidate {ticket.candidate_id!r}")

    if not unblocked:
        return Check(name, STATUS_PASS, "blocked for every candidate lock", details)

    status = STATUS_FAIL if strict else STATUS_INFO
    return Check(name, status,
                 f"blind evaluation is NOT blocked for: {', '.join(unblocked)}", details)


def run_preflight(*, strict_blind: bool = True,
                  lock_dir: Path | None = None,
                  ledger_path: Path | None = None) -> PreflightReport:
    """Run every preflight check and return the collected report.

    ``strict_blind`` - when true (default) an unblocked blind evaluation is a
    ``FAIL``; when false it is downgraded to ``INFO`` (for a supervised run
    Astra has explicitly authorised).
    ``lock_dir`` / ``ledger_path`` override the scanned locations (tests only).
    """
    ld = Path(lock_dir) if lock_dir is not None else LOCK_DIR
    lg = Path(ledger_path) if ledger_path is not None else LEDGER_PATH
    checks = [
        _check_provenance(),
        _check_manifest(config.dev_spec(), "dev"),
        _check_manifest(config.blind_spec(), "blind"),
        _check_digests_distinct(),
        _check_seed_block(config.dev_spec(), "dev"),
        _check_seed_block(config.blind_spec(), "blind"),
        _check_candidate_lock(ld),
        _check_blind_evaluation(ld, lg, strict=strict_blind),
    ]
    return PreflightReport(checks)
