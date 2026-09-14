"""Deterministic driving signal and NARMA-10 target generation.

Determinism contract
--------------------
* Per-trial seeds are derived from ``(namespace, master_seed, index)`` through
  SHA-256, so they do not depend on NumPy version or platform.
* The RNG is an explicit ``numpy.random.Generator`` built on ``PCG64`` with that
  seed; the bit stream of ``PCG64`` is stable across NumPy releases.
* Arrays are always ``float64`` in C order, so byte-level hashes are stable.
"""

from __future__ import annotations

import hashlib

import numpy as np

from . import config


def derive_seed(namespace: str, master_seed: int, index: int) -> int:
    """Return a stable 64-bit unsigned seed for one trial."""
    if index < 0:
        raise ValueError(f"index must be non-negative, got {index}")
    payload = f"{namespace}|{int(master_seed)}|{int(index)}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


def make_rng(namespace: str, master_seed: int, index: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(derive_seed(namespace, master_seed, index)))


def driving_input(rng: np.random.Generator, length: int) -> np.ndarray:
    """i.i.d. Uniform[INPUT_LOW, INPUT_HIGH] driving signal, shape ``(length,)``."""
    if length <= 0:
        raise ValueError(f"length must be positive, got {length}")
    u = rng.uniform(config.INPUT_LOW, config.INPUT_HIGH, size=int(length))
    return np.ascontiguousarray(u, dtype=np.float64)


def narma10_target(u: np.ndarray) -> np.ndarray:
    """Classic NARMA-10 recurrence driven by ``u``.

    ``y[t]`` is defined as 0 for ``t < ORDER``; the nonlinear recurrence runs for
    ``ORDER <= t < len(u)``. Returns an array the same length as ``u``.
    Raises ``FloatingPointError`` if the response is not finite (the project
    forbids non-finite data).
    """
    u = np.ascontiguousarray(u, dtype=np.float64)
    if u.ndim != 1:
        raise ValueError(f"u must be 1-D, got shape {u.shape}")
    n = u.shape[0]
    order = config.ORDER
    if n <= order:
        raise ValueError(f"need more than ORDER={order} samples, got {n}")

    a, b, g, d = config.ALPHA, config.BETA, config.GAMMA, config.DELTA
    y = np.zeros(n, dtype=np.float64)
    # A minority of driving streams make the classic recurrence diverge; let it
    # overflow to +/-inf quietly and reject it via the finiteness check below.
    with np.errstate(over="ignore", invalid="ignore"):
        for t in range(order, n):
            window = y[t - order:t].sum()
            y[t] = a * y[t - 1] + b * y[t - 1] * window + g * u[t - order] * u[t - 1] + d

    if not np.all(np.isfinite(y)):
        raise FloatingPointError(
            "NARMA-10 response diverged / produced non-finite values; "
            "this input seed is unusable for the benchmark"
        )
    return y


def generate_trial(namespace: str, master_seed: int, index: int,
                   length: int) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(u, y)`` for one deterministic trial."""
    rng = make_rng(namespace, master_seed, index)
    u = driving_input(rng, length)
    y = narma10_target(u)
    return u, y


def sha256_array(arr: np.ndarray) -> str:
    """Stable hex SHA-256 of an array's canonical little-endian float64 bytes."""
    canon = np.ascontiguousarray(arr, dtype="<f8")
    h = hashlib.sha256()
    h.update(str(canon.shape).encode("utf-8"))
    h.update(b"|")
    h.update(canon.tobytes())
    return h.hexdigest()
