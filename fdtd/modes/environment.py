"""G1 environment gate: local subpixel must be provably ON, or we stop.

The inherited failure this gate exists for: an ``n_eff`` that moved by ~3%
with mesh resolution. The leading hypothesis is Yee interface classification
without subpixel averaging. A diagnostic run *without* subpixel therefore
cannot decide the question, and a run that silently fell back to no-subpixel
would be worse than no run at all.

So: :func:`require_local_subpixel` proves the feature works by actually
exercising it, and raises with the concrete reason when it does not. Nothing
in this package enables a silent fallback.
"""

from __future__ import annotations

import importlib
import platform
import sys
from dataclasses import dataclass


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
    reason: str

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def format_text(self) -> str:
        lines = [
            f"python          {self.python}",
            f"platform        {self.platform}",
            f"tidy3d          {self.tidy3d}",
            f"numpy           {self.numpy}",
            f"tidy3d-extras   {self.extras_version or 'not installed'}",
            f"local subpixel  {'AVAILABLE' if self.subpixel_available else 'UNAVAILABLE'}",
            f"reason          {self.reason}",
        ]
        return "\n".join(lines)


def _versions() -> tuple[str, str]:
    import numpy
    import tidy3d
    return tidy3d.__version__, numpy.__version__


def probe_local_subpixel() -> EnvironmentReport:
    """Actually exercise local subpixel and report what happened."""
    td_version, np_version = _versions()

    extras_version: str | None = None
    extras_installed = False
    try:
        extras = importlib.import_module("tidy3d_extras")
        extras_installed = True
        extras_version = getattr(extras, "__version__", "unknown")
    except Exception as exc:
        return EnvironmentReport(
            python=sys.version.split()[0], platform=platform.platform(),
            tidy3d=td_version, numpy=np_version,
            extras_installed=False, extras_version=None,
            subpixel_available=False,
            reason=f"tidy3d_extras not importable: {exc!r}",
        )

    # The native worker is what actually computes the subpixel coefficients.
    # Importing the package is not proof that the worker loads.
    try:
        importlib.import_module("tidy3d_extras._isolated_extension")
    except Exception as exc:
        return EnvironmentReport(
            python=sys.version.split()[0], platform=platform.platform(),
            tidy3d=td_version, numpy=np_version,
            extras_installed=extras_installed, extras_version=extras_version,
            subpixel_available=False,
            reason=(f"tidy3d_extras native worker will not load: {exc!r}; "
                    "local subpixel would fail at solve time"),
        )

    return EnvironmentReport(
        python=sys.version.split()[0], platform=platform.platform(),
        tidy3d=td_version, numpy=np_version,
        extras_installed=extras_installed, extras_version=extras_version,
        subpixel_available=True,
        reason="tidy3d_extras native worker loaded",
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
