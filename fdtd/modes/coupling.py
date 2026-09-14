"""Gap -> coupling coefficient, by supermode parity.

Two identical parallel guides support an even and an odd TE supermode. Their
index split gives the amplitude coupling per unit length

    kappa = pi * (n_even - n_odd) / lambda      [1/m]

and a coupler of length ``L`` transfers ``sin^2(kappa * L)`` of the power. The
two are different things and the inherited line conflated them; every function
here says which one it returns.

**The failure this module is written against.** The inherited repository
reported ``kappa`` constant to six digits while the gap went 150 -> 300 nm,
which is impossible: the coupling falls exponentially with gap. The cause was
the selector — it took the two highest ``n_eff`` with no physical test, so on
most meshes it was differencing two modes that were not the even/odd pair at
all, and the difference was numerical noise.

So selection here is by **parity**, measured, not assumed:

    P = Re[ integral Ex(x,z) * conj(Ex(-x,z)) dA ] / integral |Ex|^2 dA

which is +1 for the symmetric (even) supermode and -1 for the antisymmetric
(odd) one. A mode pair that does not separate cleanly raises rather than
returning a number. And :func:`sweep_gaps` refuses a sweep whose ``kappa``
fails to fall with gap, which is exactly the symptom that went unnoticed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .cross_sections import CrossSection
from .solver import SolveSettings

#: A supermode must be this TE-polarised to be admissible.
MIN_TE_FRACTION = 0.8

#: ... and this much of its power must sit inside the two cores.
MIN_CORE_CONFINEMENT = 0.5

#: ... and its parity must be this clean, or the pair is not identified.
MIN_ABS_PARITY = 0.9


class SupermodeError(RuntimeError):
    """The even/odd pair could not be identified. No number is returned."""


@dataclass(frozen=True)
class CouplingPoint:
    gap_um: float
    n_even: float
    n_odd: float
    delta_n: float
    kappa_amplitude_per_m: float
    parity_even: float
    parity_odd: float
    te_even: float
    te_odd: float
    steps_per_wvl: int

    def power_coupling(self, length_um: float) -> float:
        """``sin^2(kappa L)`` — the power fraction transferred."""
        return math.sin(self.kappa_amplitude_per_m * length_um * 1e-6) ** 2

    def coupling_length_um(self) -> float:
        """Length for full transfer, ``pi / (2 kappa)``."""
        return math.pi / (2.0 * self.kappa_amplitude_per_m) * 1e6

    def to_dict(self) -> dict:
        d = asdict(self)
        d["coupling_length_um"] = self.coupling_length_um()
        return d


def build_pair_simulation(cross_section: CrossSection, gap_um: float,
                          settings: SolveSettings):
    """Two identical cores, symmetric about ``x = 0``, on the shared box."""
    import tidy3d as td

    if gap_um <= 0:
        raise ValueError("gap must be positive")

    dl = settings.grid_step_um(cross_section)
    offset = (cross_section.width_um + gap_um) / 2.0
    size_x = 2.0 * offset + cross_section.width_um + 2 * settings.pad_x_um
    size_z = cross_section.height_um + 2 * settings.pad_z_um
    center_z = cross_section.core_center_z

    cores = [
        td.Structure(
            geometry=td.Box(center=(sign * offset, 0.0, center_z),
                            size=(cross_section.width_um, td.inf,
                                  cross_section.height_um)),
            medium=td.Medium(permittivity=cross_section.core_index ** 2),
        )
        for sign in (-1.0, 1.0)
    ]
    box = td.Structure(
        geometry=td.Box(center=(0.0, 0.0, -size_z), size=(td.inf, td.inf, 2 * size_z)),
        medium=td.Medium(permittivity=cross_section.box_index ** 2),
    )

    return td.Simulation(
        size=(size_x, 0.0, size_z), center=(0.0, 0.0, center_z),
        structures=[box] + cores,
        grid_spec=td.GridSpec.uniform(dl=dl),
        medium=td.Medium(permittivity=cross_section.clad_index ** 2),
        boundary_spec=td.BoundarySpec(
            x=td.Boundary.pml(), y=td.Boundary.periodic(), z=td.Boundary.pml()),
        run_time=1e-12, subpixel=True,
    )


def _plane(array, mode_index: int):
    reduced = array.isel(mode_index=mode_index)
    for dim in ("y", "f"):
        if dim in reduced.dims:
            reduced = reduced.isel({dim: 0}, drop=True)
    return reduced


def parity(fields: dict, mode_index: int, n_points: int = 241) -> float:
    """``+1`` for the even supermode, ``-1`` for the odd one."""
    ex = _plane(fields["Ex"], mode_index)
    x = np.asarray(ex.coords["x"], dtype=float)
    z = np.asarray(ex.coords["z"], dtype=float)
    half = min(abs(float(x.min())), abs(float(x.max())))
    grid_x = np.linspace(-half, half, n_points)
    grid_z = np.linspace(float(z.min()), float(z.max()), n_points)

    values = np.nan_to_num(np.asarray(
        ex.interp(x=grid_x, z=grid_z).values, dtype=complex))
    mirrored = values[::-1, :]
    norm = float(np.sum(np.abs(values) ** 2))
    if norm <= 0:
        raise SupermodeError("mode field integrates to zero power")
    return float(np.real(np.sum(values * np.conj(mirrored))) / norm)


def pair_core_confinement(fields: dict, cross_section: CrossSection,
                          gap_um: float) -> np.ndarray:
    """Fraction of ``|E|^2`` inside either core, per mode."""
    offset = (cross_section.width_um + gap_um) / 2.0
    half_w = cross_section.width_um / 2.0
    z_lo, z_hi = 0.0, cross_section.height_um

    total = None
    inside = None
    for comp in ("Ex", "Ey", "Ez"):
        power = (np.abs(fields[comp]) ** 2).squeeze("y", drop=True).squeeze("f", drop=True)
        t = power.sum(dim=("x", "z"))
        left = power.sel(x=slice(-offset - half_w, -offset + half_w),
                         z=slice(z_lo, z_hi)).sum(dim=("x", "z"))
        right = power.sel(x=slice(offset - half_w, offset + half_w),
                          z=slice(z_lo, z_hi)).sum(dim=("x", "z"))
        total = t if total is None else total + t
        inside = (left + right) if inside is None else inside + left + right
    return np.asarray((inside / total).values).ravel()


def solve_gap(cross_section: CrossSection, gap_um: float,
              settings: SolveSettings | None = None) -> CouplingPoint:
    """Solve one gap and return the parity-identified coupling."""
    import tidy3d as td
    from tidy3d.plugins.mode import ModeSolver

    settings = settings or SolveSettings(steps_per_wvl=26, num_modes=6)
    sim = build_pair_simulation(cross_section, gap_um, settings)

    offset = (cross_section.width_um + gap_um) / 2.0
    size_x = 2.0 * offset + cross_section.width_um + 2 * settings.pad_x_um
    size_z = cross_section.height_um + 2 * settings.pad_z_um
    plane = td.Box(
        center=(0.0, 0.0, cross_section.core_center_z),
        size=(size_x - 2 * settings.plane_margin_um, 0.0,
              size_z - 2 * settings.plane_margin_um))

    data = ModeSolver(
        simulation=sim, plane=plane,
        mode_spec=td.ModeSpec(num_modes=settings.num_modes,
                              target_neff=cross_section.core_index),
        freqs=[td.C_0 / settings.wavelength_um],
    ).solve()

    n_eff = np.real(np.asarray(data.n_eff.values)).ravel()
    te = np.asarray(data.pol_fraction["te"].values).ravel()
    fields = {name: getattr(data, name) for name in ("Ex", "Ey", "Ez")}
    confinement = pair_core_confinement(fields, cross_section, gap_um)

    admissible = [i for i in range(len(n_eff))
                  if te[i] >= MIN_TE_FRACTION
                  and confinement[i] >= MIN_CORE_CONFINEMENT]
    if len(admissible) < 2:
        raise SupermodeError(
            f"gap {gap_um * 1e3:.0f} nm: fewer than two TE core modes "
            f"(te={np.round(te, 3).tolist()}, "
            f"core={np.round(confinement, 3).tolist()})")

    parities = {i: parity(fields, i) for i in admissible}
    evens = [i for i, p in parities.items() if p >= MIN_ABS_PARITY]
    odds = [i for i, p in parities.items() if p <= -MIN_ABS_PARITY]
    if not evens or not odds:
        raise SupermodeError(
            f"gap {gap_um * 1e3:.0f} nm: parity does not separate an even/odd "
            f"pair (parities={ {i: round(p, 3) for i, p in parities.items()} }); "
            "refusing to difference two arbitrary modes")

    even = max(evens, key=lambda i: n_eff[i])
    odd = max(odds, key=lambda i: n_eff[i])
    delta_n = n_eff[even] - n_eff[odd]
    if delta_n <= 0:
        raise SupermodeError(
            f"gap {gap_um * 1e3:.0f} nm: even supermode is not the higher "
            f"index one (delta_n = {delta_n:.3e})")

    kappa = math.pi * delta_n / (settings.wavelength_um * 1e-6)
    return CouplingPoint(
        gap_um=gap_um, n_even=float(n_eff[even]), n_odd=float(n_eff[odd]),
        delta_n=float(delta_n), kappa_amplitude_per_m=kappa,
        parity_even=parities[even], parity_odd=parities[odd],
        te_even=float(te[even]), te_odd=float(te[odd]),
        steps_per_wvl=settings.steps_per_wvl,
    )


@dataclass(frozen=True)
class GapFit:
    decay_length_nm: float
    kappa0_per_m: float
    r_squared: float
    relative_change_per_nm: float
    """``|d ln kappa / d gap|`` in units of 1/nm — the P5 axis."""

    def to_dict(self) -> dict:
        return asdict(self)


def fit_exponential(points: list[CouplingPoint]) -> GapFit:
    """Fit ``kappa = kappa0 * exp(-gap / L_d)`` in log space."""
    if len(points) < 3:
        raise SupermodeError("need at least three gaps to fit a decay length")
    gaps_nm = np.array([p.gap_um * 1e3 for p in points], dtype=float)
    log_kappa = np.log(np.array([p.kappa_amplitude_per_m for p in points]))

    slope, intercept = np.polyfit(gaps_nm, log_kappa, 1)
    if slope >= 0:
        raise SupermodeError(
            f"kappa does not fall with gap (slope {slope:+.3e} per nm); "
            "this is the inherited failure signature, not a result")

    predicted = slope * gaps_nm + intercept
    ss_res = float(np.sum((log_kappa - predicted) ** 2))
    ss_tot = float(np.sum((log_kappa - log_kappa.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return GapFit(
        decay_length_nm=float(-1.0 / slope),
        kappa0_per_m=float(np.exp(intercept)),
        r_squared=r2,
        relative_change_per_nm=float(abs(slope)),
    )


def sweep_gaps(cross_section: CrossSection, gaps_um,
               settings: SolveSettings | None = None) -> list[CouplingPoint]:
    """Solve each gap, then refuse a sweep that is not monotone."""
    points = [solve_gap(cross_section, g, settings) for g in sorted(gaps_um)]
    kappas = [p.kappa_amplitude_per_m for p in points]
    for a, b in zip(kappas, kappas[1:]):
        if b >= a:
            raise SupermodeError(
                "kappa did not fall monotonically with gap "
                f"({a:.6e} -> {b:.6e}); the inherited line reported a kappa "
                "that was constant in the gap, which is the same symptom")
    return points
