"""The two cross-sections G1 compares.

The whole point of G1 is a *controlled* comparison: identical solver, identical
grid rule, identical selector, identical gates — only the index contrast
changes. Si/SiO2 has ``dn ~ 2``; Si3N4/SiO2 has ``dn ~ 0.55``. If the inherited
``n_eff`` wobble is Yee interface classification, it must shrink with contrast.

Refractive indices here are standard telecom-band working figures, not values
read from a primary source in this repository. They are enough to decide a
*relative* question (does the wobble track contrast?) and are not accepted
physics for anything else; P1 owns the sourced table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrossSection:
    name: str
    core_index: float
    clad_index: float
    box_index: float
    width_um: float
    height_um: float
    note: str = ""

    @property
    def index_contrast(self) -> float:
        return self.core_index - self.clad_index

    @property
    def core_center_z(self) -> float:
        """Core sits on the BOX, centred at half its height above z=0."""
        return self.height_um / 2.0

    def core_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """(x_min, x_max), (z_min, z_max) of the core in um."""
        return (
            (-self.width_um / 2.0, self.width_um / 2.0),
            (0.0, self.height_um),
        )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        d = asdict(self)
        d["index_contrast"] = self.index_contrast
        return d


#: The cross-section the inherited silicon line stalled on.
SI_450x220 = CrossSection(
    name="Si-450x220",
    core_index=3.48,
    clad_index=1.444,
    box_index=1.444,
    width_um=0.45,
    height_um=0.22,
    note="inherited silicon recovery geometry; dn ~ 2.04",
)

#: A conventional high-confinement Si3N4 waveguide.
SIN_1200x800 = CrossSection(
    name="SiN-1200x800",
    core_index=1.996,
    clad_index=1.444,
    box_index=1.444,
    width_um=1.20,
    height_um=0.80,
    note="conventional thick-film Si3N4; dn ~ 0.55",
)

CROSS_SECTIONS = {cs.name: cs for cs in (SI_450x220, SIN_1200x800)}
