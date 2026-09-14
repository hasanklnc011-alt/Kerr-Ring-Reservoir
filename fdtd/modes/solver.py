"""Deterministic local eigenmode solves for the G1 diagnostic.

Two properties matter here and both are deliberate:

* **The grid does not depend on where the structure is.** ``GridSpec.auto``
  snaps to structure boundaries, so a 1e-12 um shift of the geometry could
  change the grid itself and the shift test would no longer be a test of
  interface classification. A uniform grid
  ``dl = lambda0 / (steps_per_wvl * n_core)`` removes that coupling.
* **The structure can be offset by an exact amount on that fixed grid.** That
  is the interface-classification probe: physics must not move, so any
  ``n_eff`` change is numerical.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .cross_sections import CrossSection


@dataclass(frozen=True)
class SolveSettings:
    wavelength_um: float = 1.55
    steps_per_wvl: int = 20
    num_modes: int = 4
    pad_x_um: float = 2.0
    pad_z_um: float = 2.0
    plane_margin_um: float = 0.5
    group_index: bool = True
    grid_mode: str = "uniform"
    """``uniform`` fixes the grid independently of the structure. ``auto`` lets
    tidy3d snap grid lines to structure boundaries -- which puts a grid plane
    exactly on each material interface, the condition under which an
    infinitesimal offset can reclassify a whole row of cells."""

    def grid_step_um(self, cross_section: CrossSection) -> float:
        return self.wavelength_um / (self.steps_per_wvl * cross_section.core_index)


@dataclass
class ModeSolution:
    cross_section: str
    grid_mode: str
    steps_per_wvl: int
    z_offset_um: float
    grid_step_um: float
    n_eff: np.ndarray
    n_group: np.ndarray | None
    te_fraction: np.ndarray
    core_confinement: np.ndarray
    fields: dict = field(repr=False, default_factory=dict)

    def summary_rows(self) -> list[dict]:
        rows = []
        for i in range(len(self.n_eff)):
            rows.append({
                "mode_index": i,
                "n_eff": float(self.n_eff[i]),
                "n_group": None if self.n_group is None else float(self.n_group[i]),
                "te_fraction": float(self.te_fraction[i]),
                "core_confinement": float(self.core_confinement[i]),
            })
        return rows


def build_simulation(cross_section: CrossSection, settings: SolveSettings,
                     z_offset_um: float = 0.0):
    """A 2D (y-invariant) simulation holding the waveguide cross-section."""
    import tidy3d as td

    dl = settings.grid_step_um(cross_section)
    if settings.grid_mode == "uniform":
        grid_spec = td.GridSpec.uniform(dl=dl)
    elif settings.grid_mode == "auto":
        grid_spec = td.GridSpec.auto(min_steps_per_wvl=settings.steps_per_wvl,
                                     wavelength=settings.wavelength_um)
    else:
        raise ValueError(f"unknown grid_mode {settings.grid_mode!r}")
    size_x = cross_section.width_um + 2 * settings.pad_x_um
    size_z = cross_section.height_um + 2 * settings.pad_z_um
    center_z = cross_section.core_center_z

    core = td.Structure(
        geometry=td.Box(
            center=(0.0, 0.0, cross_section.core_center_z + z_offset_um),
            size=(cross_section.width_um, td.inf, cross_section.height_um),
        ),
        medium=td.Medium(permittivity=cross_section.core_index ** 2),
    )
    box = td.Structure(
        geometry=td.Box(
            center=(0.0, 0.0, -size_z + z_offset_um),
            size=(td.inf, td.inf, 2 * size_z),
        ),
        medium=td.Medium(permittivity=cross_section.box_index ** 2),
    )

    return td.Simulation(
        size=(size_x, 0.0, size_z),
        center=(0.0, 0.0, center_z),
        structures=[box, core],
        grid_spec=grid_spec,
        medium=td.Medium(permittivity=cross_section.clad_index ** 2),
        boundary_spec=td.BoundarySpec(
            x=td.Boundary.pml(), y=td.Boundary.periodic(), z=td.Boundary.pml(),
        ),
        run_time=1e-12,
        subpixel=True,
    )


def solve(cross_section: CrossSection, settings: SolveSettings,
          z_offset_um: float = 0.0) -> ModeSolution:
    """Run one local eigenmode solve and package what the gates need."""
    import tidy3d as td
    from tidy3d.plugins.mode import ModeSolver

    sim = build_simulation(cross_section, settings, z_offset_um)
    freq = td.C_0 / settings.wavelength_um

    size_x = cross_section.width_um + 2 * settings.pad_x_um
    size_z = cross_section.height_um + 2 * settings.pad_z_um
    plane = td.Box(
        center=(0.0, 0.0, cross_section.core_center_z),
        size=(size_x - 2 * settings.plane_margin_um, 0.0,
              size_z - 2 * settings.plane_margin_um),
    )
    mode_spec = td.ModeSpec(
        num_modes=settings.num_modes,
        target_neff=cross_section.core_index,
        group_index_step=settings.group_index,
    )
    data = ModeSolver(simulation=sim, plane=plane, mode_spec=mode_spec,
                      freqs=[freq]).solve()

    n_eff = np.real(np.asarray(data.n_eff.values)).ravel()
    n_group = None
    if settings.group_index and getattr(data, "n_group", None) is not None:
        n_group = np.real(np.asarray(data.n_group.values)).ravel()
    te_fraction = np.asarray(data.pol_fraction["te"].values).ravel()

    fields = {name: getattr(data, name) for name in ("Ex", "Ey", "Ez")}
    confinement = core_confinement(fields, cross_section)

    return ModeSolution(
        cross_section=cross_section.name,
        grid_mode=settings.grid_mode,
        steps_per_wvl=settings.steps_per_wvl,
        z_offset_um=z_offset_um,
        grid_step_um=settings.grid_step_um(cross_section),
        n_eff=n_eff,
        n_group=n_group,
        te_fraction=te_fraction,
        core_confinement=confinement,
        fields=fields,
    )


def core_confinement(fields: dict, cross_section: CrossSection) -> np.ndarray:
    """Fraction of ``|E|^2`` inside the core, per mode.

    A guided core mode must actually live in the core; this is the criterion
    the inherited selector lacked.
    """
    (x_lo, x_hi), (z_lo, z_hi) = cross_section.core_bounds()

    total = None
    inside = None
    for comp in ("Ex", "Ey", "Ez"):
        arr = fields[comp]
        power = (np.abs(arr) ** 2).squeeze("y", drop=True).squeeze("f", drop=True)
        t = power.sum(dim=("x", "z"))
        core = power.sel(x=slice(x_lo, x_hi), z=slice(z_lo, z_hi)).sum(dim=("x", "z"))
        total = t if total is None else total + t
        inside = core if inside is None else inside + core

    ratio = (inside / total).values
    return np.asarray(ratio).ravel()
