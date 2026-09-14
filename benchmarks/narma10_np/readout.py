"""Closed-form ridge-regression linear readout.

This is the *baseline* readout for the benchmark skeleton. The photonic
reservoir (future phases) produces a state matrix ``X``; here we fit
``W = argmin ||X W - Y||^2 + alpha ||W||^2`` and evaluate on held-out samples.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config


@dataclass(frozen=True)
class RidgeReadout:
    weights: np.ndarray  # shape (n_features + 1,) — last entry is bias
    alpha: float

    def predict(self, states: np.ndarray) -> np.ndarray:
        x = _with_bias(np.ascontiguousarray(states, dtype=np.float64))
        if x.shape[1] != self.weights.shape[0]:
            raise ValueError(
                f"feature mismatch: readout expects {self.weights.shape[0] - 1} "
                f"features, got {x.shape[1] - 1}"
            )
        return x @ self.weights


def _with_bias(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        x = x[:, None]
    ones = np.ones((x.shape[0], 1), dtype=np.float64)
    return np.hstack([x, ones])


def fit_ridge(states: np.ndarray, targets: np.ndarray,
              alpha: float = config.DEFAULT_RIDGE_ALPHA) -> RidgeReadout:
    x = _with_bias(np.ascontiguousarray(states, dtype=np.float64))
    y = np.ascontiguousarray(targets, dtype=np.float64).ravel()
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"row mismatch: states {x.shape[0]} vs targets {y.shape[0]}")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise FloatingPointError("non-finite values in ridge inputs")
    if alpha < 0:
        raise ValueError("alpha must be non-negative")

    n_features = x.shape[1]
    reg = alpha * np.eye(n_features, dtype=np.float64)
    reg[-1, -1] = 0.0  # do not penalise the bias term
    gram = x.T @ x + reg
    rhs = x.T @ y
    weights = np.linalg.solve(gram, rhs)
    if not np.all(np.isfinite(weights)):
        raise FloatingPointError("ridge solution is non-finite")
    return RidgeReadout(weights=np.ascontiguousarray(weights, dtype=np.float64), alpha=float(alpha))


def delay_embedding(u: np.ndarray, n_delays: int) -> np.ndarray:
    """Feature matrix of ``u`` and its ``n_delays`` past values (zero-padded).

    Column j (0-indexed) holds ``u[t - j]``. Used by the baseline scorer as a
    stand-in for reservoir states.
    """
    u = np.ascontiguousarray(u, dtype=np.float64).ravel()
    if n_delays < 0:
        raise ValueError("n_delays must be non-negative")
    n = u.shape[0]
    feats = np.zeros((n, n_delays + 1), dtype=np.float64)
    for j in range(n_delays + 1):
        if j == 0:
            feats[:, j] = u
        else:
            feats[j:, j] = u[:-j]
    return feats
