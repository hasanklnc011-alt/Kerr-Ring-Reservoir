"""SHA-256 seed and data manifests.

A manifest pins, for one :class:`~benchmarks.narma10.config.SeedSpec`:

* the derived per-trial integer seed,
* the SHA-256 of the driving input ``u`` and of the NARMA-10 target ``y``,
* the sequence layout,

plus a single ``manifest_digest`` over the whole canonical structure. Committing
the manifest file is what "locks" the benchmark data — later runs recompute the
hashes and must match byte-for-byte.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import config
from .signals import derive_seed, generate_trial, sha256_array

MANIFEST_SCHEMA = "narma10-manifest/1"

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "manifests" / "narma10"


def _spec_payload(spec: config.SeedSpec) -> dict:
    return {
        "namespace": spec.namespace,
        "master_seed": int(spec.master_seed),
        "count": int(spec.count),
        "order": config.ORDER,
        "coefficients": {
            "alpha": config.ALPHA, "beta": config.BETA,
            "gamma": config.GAMMA, "delta": config.DELTA,
        },
        "input_range": [config.INPUT_LOW, config.INPUT_HIGH],
        "washout": spec.washout,
        "train_len": spec.train_len,
        "test_len": spec.test_len,
        "sequence_length": spec.sequence_length,
    }


def build_manifest(spec: config.SeedSpec) -> dict:
    """Compute a manifest dict for ``spec`` (regenerates all trial data)."""
    entries = []
    for index in range(spec.count):
        u, y = generate_trial(spec.namespace, spec.master_seed, index,
                              spec.sequence_length)
        entries.append({
            "index": index,
            "seed": derive_seed(spec.namespace, spec.master_seed, index),
            "length": int(u.shape[0]),
            "input_sha256": sha256_array(u),
            "target_sha256": sha256_array(y),
            "target_first": float(y[config.ORDER]),
            "target_last": float(y[-1]),
        })
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "spec": _spec_payload(spec),
        "entries": entries,
    }
    manifest["manifest_digest"] = manifest_digest(manifest)
    return manifest


def _canonical_bytes(manifest: dict) -> bytes:
    without_digest = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    return json.dumps(without_digest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_digest(manifest: dict) -> str:
    return hashlib.sha256(_canonical_bytes(manifest)).hexdigest()


def write_manifest(spec: config.SeedSpec, path: Path | None = None) -> Path:
    path = Path(path) if path is not None else default_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(spec)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def default_path(spec: config.SeedSpec) -> Path:
    slug = spec.namespace.split("/")[-1]
    return MANIFEST_DIR / f"{slug}_seeds.sha256.json"


@dataclass(frozen=True)
class VerifyResult:
    path: Path
    ok: bool
    mismatches: list[str]

    def raise_for_status(self) -> None:
        if not self.ok:
            raise ManifestMismatch(
                f"{self.path}: " + "; ".join(self.mismatches)
            )


class ManifestMismatch(RuntimeError):
    """Raised when a stored manifest no longer matches recomputed data."""


def _spec_from_manifest(manifest: dict) -> config.SeedSpec:
    s = manifest["spec"]
    return config.SeedSpec(
        namespace=s["namespace"],
        master_seed=int(s["master_seed"]),
        count=int(s["count"]),
        washout=int(s["washout"]),
        train_len=int(s["train_len"]),
        test_len=int(s["test_len"]),
    )


def verify_manifest(path: Path) -> VerifyResult:
    """Recompute data for the stored spec and compare every hash."""
    path = Path(path)
    mismatches: list[str] = []
    stored = json.loads(path.read_text(encoding="utf-8"))

    if stored.get("schema") != MANIFEST_SCHEMA:
        mismatches.append(f"schema {stored.get('schema')!r} != {MANIFEST_SCHEMA!r}")

    if manifest_digest(stored) != stored.get("manifest_digest"):
        mismatches.append("manifest_digest does not match manifest body")

    try:
        spec = _spec_from_manifest(stored)
    except (KeyError, TypeError, ValueError) as exc:  # malformed manifest -> fail
        mismatches.append(f"unreadable spec: {exc}")
        return VerifyResult(path=path, ok=False, mismatches=mismatches)

    recomputed = build_manifest(spec)
    rec_by_index = {e["index"]: e for e in recomputed["entries"]}
    stored_by_index = {e["index"]: e for e in stored.get("entries", [])}

    if set(rec_by_index) != set(stored_by_index):
        mismatches.append(
            f"entry indices differ: stored {sorted(stored_by_index)} "
            f"vs recomputed {sorted(rec_by_index)}"
        )

    for index in sorted(set(rec_by_index) & set(stored_by_index)):
        r, s = rec_by_index[index], stored_by_index[index]
        for field in ("seed", "length", "input_sha256", "target_sha256"):
            if r[field] != s.get(field):
                mismatches.append(
                    f"trial {index} field {field}: stored {s.get(field)!r} "
                    f"!= recomputed {r[field]!r}"
                )

    if recomputed["manifest_digest"] != stored.get("manifest_digest"):
        mismatches.append("recomputed manifest_digest differs from stored value")

    return VerifyResult(path=path, ok=not mismatches, mismatches=mismatches)


def load_digest(path: Path) -> str:
    return json.loads(Path(path).read_text(encoding="utf-8"))["manifest_digest"]
