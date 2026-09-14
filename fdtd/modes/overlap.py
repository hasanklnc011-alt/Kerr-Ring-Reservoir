"""Field-shape overlap between two mode solutions.

    O = |integral E1* . E2 dA|^2 / ( integral |E1|^2 dA * integral |E2|^2 dA )

All three complex components are carried to a common physical grid by linear
interpolation over the *shared* region only — no extrapolation. ``O`` is
invariant under a global phase and under scaling, so it answers "is this the
same mode shape?" and nothing more.

It is a positive L2 similarity, **not** power orthogonality and not an
independent physics check. Two solutions of the same wrong model agree
perfectly.
"""

from __future__ import annotations

import numpy as np

COMPONENTS = ("Ex", "Ey", "Ez")


def _as_plane(array, mode_index: int):
    """Reduce a mode field to a complex 2D (x, z) xarray."""
    reduced = array.isel(mode_index=mode_index)
    for dim in ("y", "f"):
        if dim in reduced.dims:
            reduced = reduced.isel({dim: 0}, drop=True)
    return reduced


def common_axis(a: np.ndarray, b: np.ndarray, n_points: int) -> np.ndarray:
    lo = max(float(a.min()), float(b.min()))
    hi = min(float(a.max()), float(b.max()))
    if not hi > lo:
        raise ValueError("solutions share no common region on this axis")
    return np.linspace(lo, hi, n_points)


def field_overlap(fields_a: dict, mode_a: int, fields_b: dict, mode_b: int,
                  *, n_points: int = 201) -> float:
    """Return ``O`` in [0, 1] for two mode solutions."""
    first_a = _as_plane(fields_a["Ex"], mode_a)
    first_b = _as_plane(fields_b["Ex"], mode_b)

    x = common_axis(np.asarray(first_a.coords["x"]),
                    np.asarray(first_b.coords["x"]), n_points)
    z = common_axis(np.asarray(first_a.coords["z"]),
                    np.asarray(first_b.coords["z"]), n_points)

    cross = 0.0 + 0.0j
    norm_a = 0.0
    norm_b = 0.0
    for comp in COMPONENTS:
        ea = _as_plane(fields_a[comp], mode_a).interp(x=x, z=z).values
        eb = _as_plane(fields_b[comp], mode_b).interp(x=x, z=z).values
        ea = np.nan_to_num(np.asarray(ea, dtype=complex))
        eb = np.nan_to_num(np.asarray(eb, dtype=complex))
        cross += np.sum(np.conj(ea) * eb)
        norm_a += float(np.sum(np.abs(ea) ** 2))
        norm_b += float(np.sum(np.abs(eb) ** 2))

    if norm_a <= 0.0 or norm_b <= 0.0:
        raise ValueError("a mode field integrates to zero power")
    return float(abs(cross) ** 2 / (norm_a * norm_b))
