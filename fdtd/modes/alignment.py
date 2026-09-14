"""Sub-cell alignment: the axis that mesh refinement does not fix.

Moving the structure by a fraction of a cell, on a fixed grid, with local
subpixel averaging **on**, changes ``n_eff``. The dependence is periodic in the
cell size (an offset of exactly one cell returns the original value to 5e-7),
so it is a grid-registration effect, not a physics one.

Measured on Si 450x220 (``reports/g1/alignment-study.json``):

=====  =========  ==============  ===============
spw    dl (nm)    swing           offset mean
=====  =========  ==============  ===============
16     27.84      2.2605e-02      2.361706285
20     22.27      1.7850e-02      2.360669532
26     17.13      1.4169e-02      2.359786178
32     13.92      1.2268e-02      2.359656154
40     11.14      1.2086e-02      2.359156604
=====  =========  ==============  ===============

Two things follow, and they decide how this solver may be used:

* **Mesh refinement does not fix it.** The swing falls by only 1.87x while
  ``dl`` falls 2.5x, and the last refinement (32 -> 40) buys 1.8e-4 — the
  apparent convergence order collapses from 1.06 to 0.07. A single-alignment
  ``n_eff`` is uncertain at the 1e-2 level no matter how fine the mesh.
* **Averaging over offsets does fix it.** The offset mean moves by 5.0e-4
  between the last two meshes, inside the 1e-3 convergence gate.

So a production ``n_eff`` is an **offset-averaged** value, and its honest
uncertainty is the swing, not the mesh-to-mesh difference. A single-offset
number is a diagnostic, never an input.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .cross_sections import CrossSection
from .selection import SelectionCriteria, select_te_core_mode
from .solver import SolveSettings, solve

#: Sub-cell offsets sampled, as fractions of one cell.
DEFAULT_OFFSETS = (0.0, 0.25, 0.5, 0.75)


@dataclass(frozen=True)
class AveragedMode:
    """A mode quantity averaged over sub-cell placements."""

    cross_section: str
    steps_per_wvl: int
    grid_step_um: float
    offsets: tuple[float, ...]
    n_eff_values: tuple[float, ...]
    n_group_values: tuple[float, ...]
    n_eff: float
    n_group: float
    swing: float
    """Peak-to-peak spread over the offsets: the honest uncertainty."""

    @property
    def half_swing(self) -> float:
        return self.swing / 2.0

    def to_dict(self) -> dict:
        return asdict(self)


def measure_averaged(cross_section: CrossSection,
                     settings: SolveSettings | None = None,
                     *,
                     offsets=DEFAULT_OFFSETS,
                     criteria: SelectionCriteria | None = None) -> AveragedMode:
    """Solve at each sub-cell offset and average."""
    settings = settings or SolveSettings(steps_per_wvl=26)
    criteria = criteria or SelectionCriteria()
    if len(offsets) < 2:
        raise ValueError("averaging needs at least two offsets")

    dl = settings.grid_step_um(cross_section)
    n_effs: list[float] = []
    n_groups: list[float] = []
    for fraction in offsets:
        selected = select_te_core_mode(
            solve(cross_section, settings, z_offset_um=fraction * dl), criteria)
        n_effs.append(selected.n_eff)
        n_groups.append(selected.n_group if selected.n_group is not None
                        else float("nan"))

    return AveragedMode(
        cross_section=cross_section.name,
        steps_per_wvl=settings.steps_per_wvl,
        grid_step_um=dl,
        offsets=tuple(offsets),
        n_eff_values=tuple(n_effs),
        n_group_values=tuple(n_groups),
        n_eff=sum(n_effs) / len(n_effs),
        n_group=sum(n_groups) / len(n_groups),
        swing=max(n_effs) - min(n_effs),
    )
