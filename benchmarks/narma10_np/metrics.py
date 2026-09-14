"""Error metrics with strict finiteness guards."""

from __future__ import annotations

import numpy as np


def _as_finite_1d(name: str, arr: np.ndarray) -> np.ndarray:
    a = np.ascontiguousarray(arr, dtype=np.float64).ravel()
    if a.size == 0:
        raise ValueError(f"{name} is empty")
    if not np.all(np.isfinite(a)):
        raise FloatingPointError(f"{name} contains non-finite values")
    return a


def nmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Normalised mean squared error: MSE(y_true, y_pred) / Var(y_true).

    Uses the population variance of ``y_true``. Raises if ``y_true`` is constant.
    """
    t = _as_finite_1d("y_true", y_true)
    p = _as_finite_1d("y_pred", y_pred)
    if t.shape != p.shape:
        raise ValueError(f"shape mismatch: y_true {t.shape} vs y_pred {p.shape}")
    var = float(np.var(t))
    if var <= 0.0:
        raise ValueError("y_true has zero variance; NMSE undefined")
    return float(np.mean((t - p) ** 2) / var)


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Square root of :func:`nmse`."""
    return float(np.sqrt(nmse(y_true, y_pred)))


def median_nmse(values: list[float]) -> float:
    v = _as_finite_1d("nmse values", np.asarray(values, dtype=np.float64))
    return float(np.median(v))
