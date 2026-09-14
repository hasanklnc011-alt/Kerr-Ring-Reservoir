"""G1 environment gate: local subpixel must be provably ON, or we stop.

The inherited failure this gate exists for: an ``n_eff`` that moved by ~3%
with mesh resolution. Without subpixel averaging a cell's material is decided
by a single comparison, so a diagnostic run *without* it cannot settle the
question, and a run that silently fell back would be worse than no run.

Proof here is empirical, not structural: the probe runs the *same* tiny
high-contrast solve twice, once with the flag off and once on, and requires
that the flag demonstrably changes the answer. That works across tidy3d
versions regardless of how the native worker is packaged, and it catches a
flag that is accepted but ignored.
"""

from __future__ import annotations

import importlib
import platform
import sys
from dataclasses import asdict, dataclass

#: Below this the two solves are the same number and the flag did nothing.
MIN_SUBPIXEL_EFFECT = 1e-6


class SubpixelUnavailable(RuntimeError):
    """Local subpixel averaging is not usable in this environment."""


@dataclass(frozen=True)
class EnvironmentReport:
    python: str
    platform: str
    tidy3d: str
    numpy: str
    extras_installed: bool
    extras_version: str | None
    subpixel_available: bool
    subpixel_effect: float | None
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)

    def format_text(self) -> str:
        effect = ("n/a" if self.subpixel_effect is None
                  else f"{self.subpixel_effect:.3e}")
        return "\n".join([
            f"python           {self.python}",
            f"platform         {self.platform}",
            f"tidy3d           {self.tidy3d}",
            f"numpy            {self.numpy}",
            f"tidy3d-extras    {self.extras_version or 'not installed'}",
            f"local subpixel   {'AVAILABLE' if self.subpixel_available else 'UNAVAILABLE'}",
            f"measured effect  {effect} (n_eff difference on the probe solve)",
            f"reason           {self.reason}",
        ])


def _versions() -> tuple[str, str]:
    import numpy
    import tidy3d
    return tidy3d.__version__, numpy.__version__


def _probe_n_eff(subpixel: bool) -> float:
    """A deliberately small, deliberately high-contrast reference solve."""
    import numpy as np
    import tidy3d as td
    from tidy3d.plugins.mode import ModeSolver

    enable_local_subpixel(subpixel)

    wavelength = 1.55
    dl = wavelength / (12 * 3.48)
    core = td.Structure(
        geometry=td.Box(center=(0, 0, 0.11), size=(0.45, td.inf, 0.22)),
        medium=td.Medium(permittivity=3.48 ** 2),
    )
    box = td.Structure(
        geometry=td.Box(center=(0, 0, -2.0), size=(td.inf, td.inf, 4.0)),
        medium=td.Medium(permittivity=1.444 ** 2),
    )
    sim = td.Simulation(
        size=(2.45, 0.0, 2.22), center=(0, 0, 0.11), structures=[box, core],
        grid_spec=td.GridSpec.uniform(dl=dl),
        medium=td.Medium(permittivity=1.444 ** 2),
        boundary_spec=td.BoundarySpec(
            x=td.Boundary.pml(), y=td.Boundary.periodic(), z=td.Boundary.pml()),
        run_time=1e-12, subpixel=True,
    )
    solver = ModeSolver(
        simulation=sim, plane=td.Box(center=(0, 0, 0.11), size=(1.95, 0.0, 1.72)),
        mode_spec=td.ModeSpec(num_modes=1, target_neff=3.48),
        freqs=[td.C_0 / wavelength],
    )
    return float(np.real(solver.solve().n_eff.values).ravel()[0])


def probe_local_subpixel() -> EnvironmentReport:
    """Exercise local subpixel and report what actually happened."""
    td_version, np_version = _versions()

    extras_version: str | None = None
    extras_installed = False
    try:
        extras = importlib.import_module("tidy3d_extras")
        extras_installed = True
        extras_version = getattr(extras, "__version__", "unknown")
    except Exception as exc:
        return _fail(td_version, np_version, False, None,
                     f"tidy3d_extras not importable: {exc!r}")

    try:
        without = _probe_n_eff(False)
    except Exception as exc:
        return _fail(td_version, np_version, extras_installed, extras_version,
                     f"reference solve failed even without subpixel: {exc!r}")

    try:
        with_subpixel = _probe_n_eff(True)
    except Exception as exc:
        return _fail(td_version, np_version, extras_installed, extras_version,
                     f"solve with local subpixel failed: {exc!r}")
    finally:
        enable_local_subpixel(False)

    effect = abs(with_subpixel - without)
    if effect < MIN_SUBPIXEL_EFFECT:
        return _fail(td_version, np_version, extras_installed, extras_version,
                     "the local subpixel flag was accepted but changed nothing "
                     f"(|dn_eff| = {effect:.3e}); treating it as inactive",
                     effect=effect)

    return EnvironmentReport(
        python=sys.version.split()[0], platform=platform.platform(),
        tidy3d=td_version, numpy=np_version,
        extras_installed=extras_installed, extras_version=extras_version,
        subpixel_available=True, subpixel_effect=effect,
        reason="subpixel-averaged solve succeeded and changed the result",
    )


def _fail(td_version: str, np_version: str, extras_installed: bool,
          extras_version: str | None, reason: str,
          effect: float | None = None) -> EnvironmentReport:
    return EnvironmentReport(
        python=sys.version.split()[0], platform=platform.platform(),
        tidy3d=td_version, numpy=np_version,
        extras_installed=extras_installed, extras_version=extras_version,
        subpixel_available=False, subpixel_effect=effect, reason=reason,
    )


def require_local_subpixel() -> EnvironmentReport:
    """Fail closed unless local subpixel is genuinely usable."""
    report = probe_local_subpixel()
    if not report.subpixel_available:
        raise SubpixelUnavailable(report.reason)
    enable_local_subpixel(True)
    return report


def enable_local_subpixel(enabled: bool) -> None:
    """Set the tidy3d flag explicitly. Never called implicitly on failure."""
    import tidy3d as td
    td.config.simulation.use_local_subpixel = bool(enabled)
