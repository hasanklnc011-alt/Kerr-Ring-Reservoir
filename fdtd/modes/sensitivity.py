"""How far fabrication error moves the resonance, in linewidths.

A ring's resonance follows ``m*lambda = n_eff * L``, so a geometry error shifts
it by ``dlambda/lambda = dn_eff/n_g``. What matters operationally is that shift
measured against the linewidth ``lambda/Q_L``: a device whose resonance lands
tens of linewidths away from where it was designed cannot be used without
trimming, however good its Q is.

This is a P5 input (scenario design), not a P5 result. It fixes no physics and
passes no gate; it tells the robustness study where to put its axes and tells
P1 which process tolerances have to be sourced.

Derivatives are central differences on the G1-validated local solver, with
local subpixel averaging required — the same gate that
:mod:`fdtd.modes.diagnose` closes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .alignment import DEFAULT_OFFSETS, measure_averaged
from .cross_sections import CrossSection
from .selection import SelectionCriteria, select_te_core_mode
from .solver import SolveSettings, solve

#: Central-difference half-step on the geometry, in microns.
DEFAULT_HALF_STEP_UM = 1e-3


@dataclass(frozen=True)
class Sensitivity:
    cross_section: str
    steps_per_wvl: int
    half_step_nm: float
    n_eff: float
    n_group: float
    dn_eff_d_width_per_um: float
    dn_eff_d_height_per_um: float
    dlambda_d_width_pm_per_nm: float
    dlambda_d_height_pm_per_nm: float
    offset_averaged: bool = False
    alignment_swing: float = float("nan")
    """Peak-to-peak sub-cell spread of ``n_eff`` at the nominal geometry.

    With ``offset_averaged`` false this is the size of the artefact sitting on
    top of the derivative; the derivative is then only a diagnostic."""

    def linewidth_pm(self, q_loaded: float, wavelength_nm: float = 1550.0) -> float:
        """FWHM in picometres: ``lambda / Q_L``."""
        return wavelength_nm / q_loaded * 1000.0

    def width_linewidths_per_nm(self, q_loaded: float,
                                wavelength_nm: float = 1550.0) -> float:
        return abs(self.dlambda_d_width_pm_per_nm) / self.linewidth_pm(
            q_loaded, wavelength_nm)

    def height_linewidths_per_nm(self, q_loaded: float,
                                 wavelength_nm: float = 1550.0) -> float:
        return abs(self.dlambda_d_height_pm_per_nm) / self.linewidth_pm(
            q_loaded, wavelength_nm)

    def to_dict(self) -> dict:
        return asdict(self)


def _n_eff(cs: CrossSection, settings: SolveSettings,
           criteria: SelectionCriteria,
           *, averaged: bool = False, offsets=DEFAULT_OFFSETS) -> tuple[float, float]:
    """One geometry point: either a single alignment or the offset average."""
    if averaged:
        result = measure_averaged(cs, settings, offsets=offsets, criteria=criteria)
        return result.n_eff, result.n_group
    selected = select_te_core_mode(solve(cs, settings), criteria)
    return selected.n_eff, selected.n_group


def measure(cross_section: CrossSection,
            settings: SolveSettings | None = None,
            *,
            half_step_um: float = DEFAULT_HALF_STEP_UM,
            criteria: SelectionCriteria | None = None,
            offset_averaged: bool = True,
            offsets=DEFAULT_OFFSETS) -> Sensitivity:
    """Central-difference geometry derivatives for one cross-section.

    ``offset_averaged`` defaults to true: a single-alignment derivative carries
    a sub-cell artefact comparable to the derivative itself (see
    :mod:`fdtd.modes.alignment`).
    """
    settings = settings or SolveSettings(steps_per_wvl=26)
    criteria = criteria or SelectionCriteria()
    if half_step_um <= 0:
        raise ValueError("half_step_um must be positive")

    swing = float("nan")
    if offset_averaged:
        nominal = measure_averaged(cross_section, settings, offsets=offsets,
                                   criteria=criteria)
        n_eff, n_group, swing = nominal.n_eff, nominal.n_group, nominal.swing
    else:
        n_eff, n_group = _n_eff(cross_section, settings, criteria)

    def at(cs):
        return _n_eff(cs, settings, criteria,
                      averaged=offset_averaged, offsets=offsets)[0]

    wide = at(replace(cross_section, width_um=cross_section.width_um + half_step_um))
    narrow = at(replace(cross_section, width_um=cross_section.width_um - half_step_um))
    tall = at(replace(cross_section, height_um=cross_section.height_um + half_step_um))
    short = at(replace(cross_section, height_um=cross_section.height_um - half_step_um))

    dn_dw = (wide - narrow) / (2.0 * half_step_um)
    dn_dh = (tall - short) / (2.0 * half_step_um)

    # dlambda/dx = (lambda / n_g) * dn_eff/dx.
    # lambda in um and dn/dx per um give pm per nm directly:
    #   (um * 1e6 pm/um) / (1e3 nm/um) = 1e3, cancelling against per-um -> per-nm.
    scale = settings.wavelength_um / n_group * 1e3
    return Sensitivity(
        cross_section=cross_section.name,
        steps_per_wvl=settings.steps_per_wvl,
        half_step_nm=half_step_um * 1e3,
        n_eff=n_eff,
        n_group=n_group,
        dn_eff_d_width_per_um=dn_dw,
        dn_eff_d_height_per_um=dn_dh,
        dlambda_d_width_pm_per_nm=scale * dn_dw,
        dlambda_d_height_pm_per_nm=scale * dn_dh,
        offset_averaged=offset_averaged,
        alignment_swing=swing,
    )


def trim_range_nm(sensitivity: Sensitivity, geometry_tolerance_nm: float,
                  tuning_pm_per_unit: float | None) -> float | None:
    """Trim range needed to undo a geometry error, in the tuner's own units.

    ``tuning_pm_per_unit`` is the tuner's efficiency (e.g. pm per kelvin for a
    thermal trim). It is unresolved until P1 sources it, and this returns
    ``None`` rather than inventing one.
    """
    if tuning_pm_per_unit is None or tuning_pm_per_unit == 0:
        return None
    shift = abs(sensitivity.dlambda_d_width_pm_per_nm) * geometry_tolerance_nm
    return shift / abs(tuning_pm_per_unit)
